import re
import io
import logging
import time
from typing import List, Dict, Any, Optional
import pdfplumber
from docx import Document

from app.backend.services.metrics import RESUME_PARSE_DURATION

logger = logging.getLogger(__name__)

try:
    import fitz as pymupdf   # PyMuPDF
    _HAS_PYMUPDF = True
except ImportError:
    _HAS_PYMUPDF = False

try:
    from unidecode import unidecode as _unidecode
    _HAS_UNIDECODE = True
except ImportError:
    _HAS_UNIDECODE = False


# ─── spaCy NER singleton for name extraction (Tier 0) ────────────────────────

_spacy_nlp = None

def _get_spacy_model():
    """Lazy-load spaCy model once; return None if unavailable."""
    global _spacy_nlp
    if _spacy_nlp is None:
        try:
            import spacy
            _spacy_nlp = spacy.load("en_core_web_sm")
        except (ImportError, OSError):
            _spacy_nlp = False  # Mark as unavailable to avoid repeated attempts
    return _spacy_nlp if _spacy_nlp is not False else None


def _extract_name_ner(raw_text: str) -> str | None:
    """Tier 0: Extract candidate name using spaCy NER on first 50 lines."""
    nlp = _get_spacy_model()
    if nlp is None:
        return None
    
    # Only process first 50 lines (header area of resume)
    lines = raw_text.strip().split('\n')[:50]
    header_text = '\n'.join(lines)
    
    doc = nlp(header_text)
    
    # Find first PERSON entity
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            name = ent.text.strip()
            # Basic validation: 1-5 words, no digits, reasonable length
            words = name.split()
            if 1 <= len(words) <= 5 and not any(c.isdigit() for c in name) and len(name) <= 60:
                return name
    
    return None


# ─── JD text extractor (multi-format, lenient) ───────────────────────────────

def extract_jd_text(file_bytes: bytes, filename: str) -> str:
    """
    Extract plain text from a Job Description file.

    Supports: PDF, DOCX, DOC (legacy binary), TXT, RTF, HTML/HTM, ODT,
    Markdown, and any plain-text file regardless of extension.

    Unlike parse_resume(), this function only needs raw text — it does NOT
    return structured data and is intentionally permissive about format.
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    # ── PDF ──────────────────────────────────────────────────────────────────
    if ext == "pdf":
        try:
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                text = "\n".join(page.extract_text() or "" for page in pdf.pages)
            if text.strip():
                return text
        except Exception as e:
            logger.warning("Non-critical: PDF extraction failed for %s, falling back to plain text: %s", filename, e)
    
    # ── DOCX (modern Word .docx / Office Open XML) ───────────────────────────
    if ext == "docx":
        try:
            doc = Document(io.BytesIO(file_bytes))
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            # Also grab text from tables
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        if cell.text.strip():
                            paragraphs.append(cell.text.strip())
            text = "\n".join(paragraphs)
            if text.strip():
                return text
        except Exception as e:
            logger.warning("Non-critical: DOCX extraction failed for %s, falling back to plain text: %s", filename, e)
    
    # ── DOC (legacy binary Word) — best-effort ASCII extraction ──────────────
    if ext == "doc":
        try:
            raw = file_bytes.decode("latin-1", errors="ignore")
            # Remove non-printable characters except newline/tab
            cleaned = re.sub(r"[^\x20-\x7E\n\t]", " ", raw)
            # Collapse multiple spaces but keep newlines
            cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
            lines = [l.strip() for l in cleaned.splitlines() if len(l.strip()) > 4]
            text = "\n".join(lines)
            if text.strip():
                return text
        except Exception as e:
            logger.warning("Non-critical: DOC extraction failed for %s, falling back to plain text: %s", filename, e)
    
    # ── RTF ───────────────────────────────────────────────────────────────────
    if ext == "rtf":
        try:
            raw = file_bytes.decode("latin-1", errors="ignore")
            # Strip RTF control words, groups, and backslash escapes
            text = re.sub(r"\\[a-z]+\-\d*\s?", " ", raw)
            text = re.sub(r"\{[^{}]*\}", " ", text)
            text = re.sub(r"[{}\\]", " ", text)
            text = re.sub(r"\s+", " ", text)
            if text.strip():
                return text.strip()
        except Exception as e:
            logger.warning("Non-critical: RTF extraction failed for %s, falling back to plain text: %s", filename, e)
    
    # ── HTML / HTM ────────────────────────────────────────────────────────────
    if ext in ("html", "htm"):
        try:
            raw = file_bytes.decode("utf-8", errors="ignore")
            text = re.sub(r"<[^>]+>", " ", raw)
            text = re.sub(r"\s+", " ", text)
            if text.strip():
                return text.strip()
        except Exception as e:
            logger.warning("Non-critical: HTML extraction failed for %s, falling back to plain text: %s", filename, e)
    
    # ── ODT (Open Document Text) — it's a ZIP; extract content.xml ───────────
    if ext == "odt":
        try:
            import zipfile
            with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
                with z.open("content.xml") as f:
                    xml = f.read().decode("utf-8", errors="ignore")
            text = re.sub(r"<[^>]+>", " ", xml)
            text = re.sub(r"\s+", " ", text)
            if text.strip():
                return text.strip()
        except Exception as e:
            logger.warning("Non-critical: ODT extraction failed for %s, falling back to plain text: %s", filename, e)

    # ── Plain text fallback (TXT, MD, CSV, unknown, or any failed attempt) ───
    for encoding in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
        try:
            text = file_bytes.decode(encoding)
            if text.strip():
                return text
        except (UnicodeDecodeError, LookupError):
            continue

    raise ValueError(
        f"Could not extract readable text from '{filename}'. "
        "Supported formats: PDF, DOCX, DOC, TXT, RTF, HTML, ODT."
    )


class ResumeParser:
    def __init__(self):
        # Order: more specific / common CV formats first (year-to-present is very common).
        self.date_patterns = [
            r'(\d{4})\s*[-–—]\s*(present|current|now)',
            r'(\d{1,2}/\d{4})\s*[-–—]\s*(present|current|now)',
            r'(\w+\s+\d{4})\s*[-–—]\s*(present|current|now)',
            r'(\w+\s+\d{4})\s*[-–—]\s*(\w+\s+\d{4}|present|current|now)',
            r'(\d{1,2}/\d{4})\s*[-–—]\s*(\d{1,2}/\d{4}|present|current|now)',
            r'(\d{4})\s*[-–—]\s*(\d{4}|present|current|now)',
        ]

    def extract_text(self, file_bytes: bytes, filename: str) -> str:
        if filename.lower().endswith('.pdf'):
            return self._extract_pdf(file_bytes)
        elif filename.lower().endswith(('.docx', '.doc')):
            return self._extract_docx(file_bytes)
        elif filename.lower().endswith('.txt'):
            return file_bytes.decode('utf-8')
        else:
            raise ValueError(f"Unsupported file format: {filename}")

    def _extract_pdf(self, file_bytes: bytes) -> str:
        """PyMuPDF primary (handles multi-column, correct reading order); pdfplumber fallback."""
        text = ""

        if _HAS_PYMUPDF:
            try:
                doc = pymupdf.open(stream=file_bytes, filetype="pdf")
                pages_text = []
                for page in doc:
                    pages_text.append(page.get_text("text"))
                doc.close()
                text = "\n".join(pages_text)
            except Exception as e:
                logger.warning("PyMuPDF extraction failed, falling back to pdfplumber: %s", e)
                text = ""

        # pdfplumber fallback if PyMuPDF unavailable or returned empty
        if not text.strip():
            logger.info("Using pdfplumber fallback for PDF extraction (PyMuPDF unavailable or empty result)")
            try:
                with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                    text = "\n".join(page.extract_text() or "" for page in pdf.pages)
            except Exception as e:
                logger.warning("pdfplumber fallback also failed: %s", e)
                text = ""

        # Scanned-PDF guard — raise early with actionable message
        if len(text.strip()) < 100:
            raise ValueError(
                "This PDF appears to be a scanned image and cannot be read automatically. "
                "Please upload a text-based PDF (exported from Word/Google Docs) rather than "
                "a scanned or photographed document."
            )

        # Normalise Unicode characters (e.g. résumé → resume, accented skill names)
        if _HAS_UNIDECODE:
            text = _unidecode(text)

        return text

    def _extract_docx(self, file_bytes: bytes) -> str:
        doc = Document(io.BytesIO(file_bytes))
        return "\n".join([para.text for para in doc.paragraphs])

    def parse_resume(self, file_bytes: bytes, filename: str) -> Dict[str, Any]:
        text = self.extract_text(file_bytes, filename)

        return {
            "raw_text": text,
            "work_experience": self._extract_work_experience(text),
            "skills": self._extract_skills(text),
            "education": self._extract_education(text),
            "contact_info": self._extract_contact_info(text)
        }

    def _extract_work_experience(self, text: str) -> List[Dict[str, Any]]:
        jobs = []

        lines = text.split('\n')
        current_job = None
        # When dates sit on their own line ("2018 – Present"), company/title are often on the line above.
        last_role_line: Optional[str] = None
        _section_hdr = re.compile(
            r'^(WORK|EXPERIENCE|EMPLOYMENT|PROFESSIONAL\s+EXPERIENCE|CAREER|HISTORY|EDUCATION|SKILLS|PROJECTS)\b',
            re.IGNORECASE,
        )

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Look for date ranges that indicate work experience
            date_match = None
            for pattern in self.date_patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    date_match = match
                    break

            if date_match:
                # If we have a current job being built, save it
                if current_job and (current_job.get('company') or current_job.get('title')):
                    jobs.append(current_job)

                # Start a new job entry
                start_date = date_match.group(1)
                end_date = date_match.group(2).lower()
                if end_date in ['present', 'current', 'now']:
                    end_date = 'present'

                # Try to extract company and title from the same line or previous lines
                parts = line[:date_match.start()].strip()
                if not parts and last_role_line:
                    parts = last_role_line
                last_role_line = None

                if '|' in parts:
                    split_parts = parts.split('|', 1)
                    company = split_parts[0].strip()
                    title = split_parts[1].strip()
                elif ',' in parts:
                    split_parts = parts.split(',', 1)
                    company = split_parts[0].strip()
                    title = split_parts[1].strip()
                elif ' at ' in parts:
                    split_parts = parts.split(' at ', 1)
                    title = split_parts[0].strip()
                    company = split_parts[1].strip()
                else:
                    company = parts
                    title = ""

                current_job = {
                    'company': company,
                    'title': title,
                    'start_date': start_date,
                    'end_date': end_date,
                    'description': ''
                }
            elif current_job is not None:
                # Accumulate job description
                if len(line) > 20:  # Likely a description line
                    current_job['description'] += line + ' '
            else:
                # Between jobs: remember short lines as possible role/company headers
                if len(line) < 120 and not _section_hdr.match(line) and not line.startswith(('-', '•', '*', '·', '▸')):
                    last_role_line = line

        # Don't forget the last job
        if current_job and (current_job.get('company') or current_job.get('title')):
            jobs.append(current_job)

        return jobs

    # Broad list used for full-text fallback when no skills section is found
    KNOWN_SKILLS_BROAD = [
        # Languages
        "python", "java", "javascript", "typescript", "c++", "c#", "c", "golang",
        "rust", "scala", "kotlin", "swift", "ruby", "php", "r", "matlab", "ada",
        "assembly", "bash", "powershell", "perl",
        # Web / frameworks
        "react", "vue", "angular", "node", "django", "flask", "fastapi", "spring",
        ".net", "qt", "boost", "opencv", "grpc",
        # Databases
        "sql", "postgresql", "mysql", "mongodb", "redis", "oracle", "sqlite",
        "elasticsearch", "cassandra", "dynamodb",
        # Cloud / DevOps
        "aws", "azure", "gcp", "docker", "kubernetes", "terraform", "ansible",
        "jenkins", "git", "linux", "unix", "nginx", "ci/cd", "devops",
        # Architecture / design
        "uml", "ooad", "design patterns", "microservices", "soa", "rest",
        "system design", "software architecture", "requirement engineering",
        # Embedded / systems
        "embedded", "rtos", "qnx", "vxworks", "freertos", "embedded linux",
        "microcontroller", "fpga", "arm", "tcp/ip", "can bus", "modbus",
        "uart", "spi", "i2c", "ipc", "multithreading", "firmware", "bsp",
        "device driver", "bootloader", "real-time",
        # Safety standards
        "sil4", "do-178", "iso 26262", "misra", "functional safety",
        # Data / AI
        "machine learning", "deep learning", "ai", "nlp", "data analysis",
        "spark", "hadoop", "kafka", "tableau", "power bi", "excel",
        # Project / leadership
        "agile", "scrum", "kanban", "jira", "project management",
        "leadership", "mentoring", "management", "communication",
        # Testing
        "unit testing", "tdd", "cmake", "code review", "ci/cd",
    ]

    def _extract_skills(self, text: str) -> List[str]:
        skills = []

        # ── Step 1: skills section extraction ──────────────────────────────────
        skill_headers = [
            r'SKILLS?\s*:?\s*\n',
            r'TECHNICAL\s+SKILLS?\s*:?\s*\n',
            r'KEY\s+SKILLS?\s*:?\s*\n',
            r'CORE\s+(?:SKILLS?|COMPETENCIES?)\s*:?\s*\n',
            r'COMPETENCIES?\s*:?\s*\n',
            r'EXPERTISE\s*:?\s*\n',
            r'TECHNICAL\s+EXPERTISE\s*:?\s*\n',
            r'TECHNOLOGIES?\s*:?\s*\n',
            r'TECH(?:NICAL)?\s+STACK\s*:?\s*\n',
            r'PROGRAMMING\s+LANGUAGES?\s*:?\s*\n',
            r'TOOLS\s+(?:AND|&)?\s*TECHNOLOGIES?\s*:?\s*\n',
            r'PROFICIENCIES?\s*:?\s*\n',
            r'CAPABILITIES?\s*:?\s*\n',
            r'AREAS?\s+OF\s+EXPERTISE\s*:?\s*\n',
            r'TECHNICAL\s+PROFICIENCY\s*:?\s*\n',
        ]
        skills_section = ""
        for header in skill_headers:
            match = re.search(
                header + r'(.*?)(?:\n\n|\n[A-Z][A-Z\s]+\n|$)',
                text, re.DOTALL | re.IGNORECASE
            )
            if match:
                skills_section = match.group(1)
                break

        if skills_section:
            raw_skills = re.split(r'[,;|•\-\n]', skills_section)
            skills = [s.strip() for s in raw_skills if 1 < len(s.strip()) < 60]

        # ── Step 2: full-text scan with flashtext (MASTER_SKILLS) ────────────
        try:
            from app.backend.services.hybrid_pipeline import skills_registry
            processor = skills_registry.get_processor()
            if processor:
                scanned = processor.extract_keywords(text)
                # Merge — prefer section-extracted, then add scanned extras
                existing = {s.lower() for s in skills}
                skills.extend(s for s in scanned if s.lower() not in existing)
            else:
                raise ImportError
        except Exception as e:
            # Final fallback: original KNOWN_SKILLS_BROAD list
            logger.warning("Skills registry unavailable, using fallback KNOWN_SKILLS_BROAD list: %s", e)
            if not skills:
                text_lower = text.lower()
                skills.extend(s for s in self.KNOWN_SKILLS_BROAD if s in text_lower)

        return list(dict.fromkeys(skills))  # deduplicate, preserve order

    def _extract_education(self, text: str) -> List[Dict[str, str]]:
        education = []

        # Look for education section
        edu_headers = [r'EDUCATION\s*:?\s*\n', r'ACADEMIC\s+BACKGROUND\s*:?\s*\n', r'QUALIFICATIONS\s*:?\s*\n']

        edu_section = ""
        for header in edu_headers:
            match = re.search(header + r'(.*?)(?:\n\n[A-Z][A-Z\s]+\n|\Z)', text, re.DOTALL | re.IGNORECASE)
            if match:
                edu_section = match.group(1)
                break

        if edu_section:
            lines = edu_section.strip().split('\n')
            for line in lines:
                line = line.strip()
                if len(line) < 10:
                    continue

                # Look for degree patterns
                degree_match = re.search(r'(Bachelor|Master|PhD|Doctorate|B\.S\.|M\.S\.|B\.A\.|M\.A\.|MBA|BE|ME|BTech|MTech)', line, re.IGNORECASE)
                if degree_match:
                    university = ""
                    field = ""
                    year = ""

                    # Try to extract year
                    year_match = re.search(r'\b(19|20)\d{2}\b', line)
                    if year_match:
                        year = year_match.group(0)

                    # Try to extract university (often after "from" or before degree)
                    uni_match = re.search(r'(?:from\s+|at\s+|,?\s*)([A-Z][A-Za-z\s]+(?:University|College|Institute|School))', line)
                    if uni_match:
                        university = uni_match.group(1).strip()

                    education.append({
                        'degree': degree_match.group(0),
                        'field': field,
                        'university': university,
                        'year': year
                    })

        return education

    def _extract_name(self, text: str) -> str:
        """
        Extract candidate name from the top of the resume.
        Names are typically the first prominent line: 1-5 capitalised words,
        not a common section header.

        Note: older logic rejected any line containing a hyphen in a character class,
        which incorrectly skipped hyphenated names (e.g. Mary-Jane Smith). We now
        split on | / • and treat phone/email segments separately.
        """
        SKIP_WORDS = {
            'resume', 'curriculum', 'vitae', 'cv', 'profile', 'summary',
            'objective', 'contact', 'address', 'details', 'information',
            'page', 'updated', 'date',
        }
        lines = text.strip().split('\n')
        for line in lines[:15]:
            line = line.strip()
            if not line or len(line) < 3:
                continue
            name = self._name_from_header_line(line, SKIP_WORDS)
            if name:
                return name
        return ''

    def _name_from_header_line(self, line: str, skip_words: set) -> str:
        """Try to read a person name from one header line (possibly 'Name | phone | city')."""
        segments = re.split(r'\s*[|•]\s*', line)
        for seg in segments:
            seg = seg.strip()
            if not seg or len(seg) < 2:
                continue
            if '@' in seg or re.search(r'linkedin\.com/', seg, re.IGNORECASE):
                continue
            if sum(1 for c in seg if c.isdigit()) > 2:
                continue
            if re.search(r'\+?\d[\d\s().\-]{8,}\d', seg):
                continue
            words = seg.split()
            if not (1 <= len(words) <= 5):
                continue
            if any(w.lower() in skip_words for w in words):
                continue
            cap_count = sum(1 for w in words if w and w[0].isupper())
            if cap_count >= max(1, len(words) - 1):
                return seg
        return ''

    def _extract_contact_info(self, text: str) -> Dict[str, str]:
        info = {}

        # Name — extracted first so we can use it in the result
        name = self._extract_name(text)
        if name:
            info['name'] = name

        # Email
        email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
        if email_match:
            info['email'] = email_match.group(0)

        # Phone
        phone_match = re.search(r'[\+]?[(]?[0-9]{1,4}[)]?[-\s\.]?[0-9]{1,4}[-\s\.]?[0-9]{1,9}', text)
        if phone_match:
            info['phone'] = phone_match.group(0)

        # LinkedIn
        linkedin_match = re.search(r'linkedin\.com/in/[A-Za-z0-9\-_%]+', text, re.IGNORECASE)
        if linkedin_match:
            info['linkedin'] = linkedin_match.group(0)

        return info


def _name_from_email(email: str) -> str:
    """john.doe@x.com → 'John Doe' when local part has two+ alpha tokens."""
    if not email or "@" not in email:
        return ""
    local = email.split("@", 1)[0].strip().lower()
    if not local:
        return ""
    tokens = [t for t in re.split(r"[._+\-]+", local) if t.isalpha() and len(t) >= 2]
    if len(tokens) < 2:
        return ""
    return " ".join(t.capitalize() for t in tokens[:4])


def _extract_name_relaxed(text: str) -> str:
    """
    Fallback when strict header heuristics miss (e.g. title line before name, odd layout).
    """
    skip = {
        "resume", "curriculum", "vitae", "cv", "profile", "summary",
        "objective", "contact", "address", "details", "information",
        "page", "updated", "date", "experience", "education", "skills",
        "employment", "work", "projects", "references",
    }
    title_case_name = re.compile(r"^([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\s*$")
    for line in text.strip().split("\n")[:35]:
        line = line.strip()
        if len(line) < 4 or len(line) > 80:
            continue
        if "@" in line or re.search(r"linkedin\.com/", line, re.IGNORECASE):
            continue
        if re.search(r"\+?\d[\d\s().\-]{8,}\d", line):
            continue
        if title_case_name.match(line):
            words = line.split()
            if any(w.lower() in skip for w in words):
                continue
            return line
    return ""


def enrich_parsed_resume(data: Dict[str, Any]) -> None:
    """Fill gaps in parser output in-place (name from NER / email / relaxed header scan)."""
    contact = data.setdefault("contact_info", {})
    raw = (data.get("raw_text") or "").strip()
    if (contact.get("name") or "").strip():
        return
    
    # Tier 0: Try spaCy NER first (most accurate for diverse formats)
    guess = None
    if raw:
        guess = _extract_name_ner(raw)
    
    # Tier 1: Fallback to email-based extraction
    if not guess:
        email = (contact.get("email") or "").strip()
        guess = _name_from_email(email)
    
    # Tier 2: Final fallback to relaxed header scan
    if not guess and raw:
        guess = _extract_name_relaxed(raw)
    
    if guess:
        contact["name"] = guess


def parse_resume(file_bytes: bytes, filename: str) -> Dict[str, Any]:
    start = time.monotonic()
    parser = ResumeParser()
    out = parser.parse_resume(file_bytes, filename)
    enrich_parsed_resume(out)
    RESUME_PARSE_DURATION.observe(time.monotonic() - start)
    return out

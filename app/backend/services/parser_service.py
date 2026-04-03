import re
import io
from typing import List, Dict, Any
import pdfplumber
from docx import Document


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
        except Exception:
            pass

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
        except Exception:
            pass

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
        except Exception:
            pass

    # ── RTF ───────────────────────────────────────────────────────────────────
    if ext == "rtf":
        try:
            raw = file_bytes.decode("latin-1", errors="ignore")
            # Strip RTF control words, groups, and backslash escapes
            text = re.sub(r"\\[a-z]+\-?\d*\s?", " ", raw)
            text = re.sub(r"\{[^{}]*\}", " ", text)
            text = re.sub(r"[{}\\]", " ", text)
            text = re.sub(r"\s+", " ", text)
            if text.strip():
                return text.strip()
        except Exception:
            pass

    # ── HTML / HTM ────────────────────────────────────────────────────────────
    if ext in ("html", "htm"):
        try:
            raw = file_bytes.decode("utf-8", errors="ignore")
            text = re.sub(r"<[^>]+>", " ", raw)
            text = re.sub(r"\s+", " ", text)
            if text.strip():
                return text.strip()
        except Exception:
            pass

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
        except Exception:
            pass

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
        self.date_patterns = [
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
        text = ""
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
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

        # Don't forget the last job
        if current_job and (current_job.get('company') or current_job.get('title')):
            jobs.append(current_job)

        return jobs

    def _extract_skills(self, text: str) -> List[str]:
        skills = []

        # Common section headers for skills
        skill_headers = [
            r'SKILLS?\s*:?\s*\n',
            r'TECHNICAL\s+SKILLS?\s*:?\s*\n',
            r'KEY\s+SKILLS?\s*:?\s*\n',
            r'COMPETENCIES?\s*:?\s*\n',
            r'EXPERTISE\s*:?\s*\n'
        ]

        # Find skills section
        skills_section = ""
        for header in skill_headers:
            match = re.search(header + r'(.*?)(?:\n\n|\n[A-Z][A-Z\s]+\n|$)', text, re.DOTALL | re.IGNORECASE)
            if match:
                skills_section = match.group(1)
                break

        if skills_section:
            # Split by common delimiters
            raw_skills = re.split(r'[,;|•\-]', skills_section)
            skills = [s.strip() for s in raw_skills if len(s.strip()) > 1 and len(s.strip()) < 50]

        return skills

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

    def _extract_contact_info(self, text: str) -> Dict[str, str]:
        info = {}

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


def parse_resume(file_bytes: bytes, filename: str) -> Dict[str, Any]:
    parser = ResumeParser()
    return parser.parse_resume(file_bytes, filename)

"""Resume enrichment service.

Provides minor enhancement features:
- Social profile URL validation and extraction (LinkedIn, GitHub, etc.)
- Salary expectation parsing from resume text
- Structured education parsing (GPA, graduation year, institution)
- International date parsing patterns (DD/MM/YYYY, etc.)
"""

import re
import logging
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Social Profile Validation
# ─────────────────────────────────────────────────────────────────────────────

SOCIAL_PROFILE_PATTERNS = {
    "linkedin": {
        "patterns": [
            r'(?:https?://)?(?:www\.)?linkedin\.com/in/([A-Za-z0-9_\-%]+)',
            r'(?:https?://)?(?:www\.)?linkedin\.com/pub/([A-Za-z0-9_\-%/]+)',
        ],
        "validate": lambda url: "linkedin.com" in url.lower(),
    },
    "github": {
        "patterns": [
            r'(?:https?://)?(?:www\.)?github\.com/([A-Za-z0-9_\-]+)',
        ],
        "validate": lambda url: "github.com" in url.lower(),
    },
    "twitter": {
        "patterns": [
            r'(?:https?://)?(?:www\.)?(?:twitter|x)\.com/([A-Za-z0-9_]+)',
        ],
        "validate": lambda url: "twitter.com" in url.lower() or "x.com" in url.lower(),
    },
    "portfolio": {
        "patterns": [
            r'(?:https?://)?([A-Za-z0-9\-]+\.[A-Za-z]{2,})',
        ],
        "validate": lambda url: True,  # Any URL is potentially a portfolio
    },
    "behance": {
        "patterns": [
            r'(?:https?://)?(?:www\.)?behance\.net/([A-Za-z0-9_]+)',
        ],
        "validate": lambda url: "behance.net" in url.lower(),
    },
    "dribbble": {
        "patterns": [
            r'(?:https?://)?(?:www\.)?dribbble\.com/([A-Za-z0-9_]+)',
        ],
        "validate": lambda url: "dribbble.com" in url.lower(),
    },
    "medium": {
        "patterns": [
            r'(?:https?://)?(?:www\.)?medium\.com/@([A-Za-z0-9_]+)',
        ],
        "validate": lambda url: "medium.com" in url.lower(),
    },
    "stackoverflow": {
        "patterns": [
            r'(?:https?://)?(?:www\.)?stackoverflow\.com/users/(\d+)/([A-Za-z0-9_]+)',
        ],
        "validate": lambda url: "stackoverflow.com" in url.lower(),
    },
    "kaggle": {
        "patterns": [
            r'(?:https?://)?(?:www\.)?kaggle\.com/([A-Za-z0-9_]+)',
        ],
        "validate": lambda url: "kaggle.com" in url.lower(),
    },
    "orcid": {
        "patterns": [
            r'(?:https?://)?(?:www\.)?orcid\.org/(\d{4}-\d{4}-\d{4}-\d{4})',
        ],
        "validate": lambda url: "orcid.org" in url.lower(),
    },
}


def extract_social_profiles(resume_text: str) -> Dict[str, str]:
    """Extract and validate social profile URLs from resume text.

    Args:
        resume_text: Resume text.

    Returns:
        Dict mapping platform name to validated URL.
    """
    if not resume_text:
        return {}

    profiles = {}
    for platform, config in SOCIAL_PROFILE_PATTERNS.items():
        for pattern in config["patterns"]:
            match = re.search(pattern, resume_text, re.IGNORECASE)
            if match:
                url = match.group(0)
                # Normalize to full URL
                if not url.startswith("http"):
                    url = "https://" + url
                if config["validate"](url):
                    profiles[platform] = url
                    break

    return profiles


def validate_url(url: str) -> bool:
    """Validate that a URL is well-formed and has a valid domain."""
    try:
        parsed = urlparse(url)
        return bool(parsed.scheme) and bool(parsed.netloc)
    except Exception:
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Salary Expectation Parsing
# ─────────────────────────────────────────────────────────────────────────────

SALARY_PATTERNS = [
    # "Expected salary: $120,000"
    r'(?:expected|desired|target|salary)\s*(?:expectation\s*)?(?:rate\s*)?[:\s]+\$?([\d,]+)\s*(?:k|K|/yr|per\s+year|annually)?',
    # "$120k expected"
    r'\$([\d,]+)\s*k\s*(?:expected|desired|target|negotiable)',
    # "Salary expectation: 120,000 - 140,000"
    r'(?:salary|compensation)\s*(?:expectation|range|requirement)\s*[:\s]+\$?([\d,]+)\s*[-–to]+\s*\$?([\d,]+)',
    # "Looking for 120-140k"
    r'(?:looking\s+for|seeking)\s+\$?([\d,]+)\s*[-–]\s*\$?([\d,]+)\s*k',
    # "CTC: 15 LPA" (Indian format)
    r'(?:ctc|current\s+ctc|expected\s+ctc)\s*[:\s]+([\d.]+)\s*(?:lpa|lakhs?)',
    # "€60,000" or "£50,000"
    r'[€£]\s*([\d,]+)\s*(?:per\s+annum|annually|/yr)?',
]

SALARY_RANGES = [
    # "Salary range: $100,000 - $130,000"
    r'(?:salary|compensation)\s*(?:range|expectation)\s*[:\s]+\$?([\d,]+)\s*[-–to]+\s*\$?([\d,]+)',
]


def parse_salary_expectation(resume_text: str) -> Optional[Dict[str, Any]]:
    """Parse salary expectation from resume text.

    Args:
        resume_text: Resume text.

    Returns:
        Dict with min, max, currency, and raw text, or None if not found.
    """
    if not resume_text:
        return None

    text = resume_text

    # Detect currency
    currency = "USD"
    if "€" in text:
        currency = "EUR"
    elif "£" in text:
        currency = "GBP"
    elif "₹" in text or re.search(r'\b(?:lpa|lakhs?|inr)\b', text, re.IGNORECASE):
        currency = "INR"

    # Try range patterns first
    for pattern in SALARY_RANGES:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            min_val = int(match.group(1).replace(",", ""))
            max_val = int(match.group(2).replace(",", ""))
            return {
                "min": min_val,
                "max": max_val,
                "currency": currency,
                "raw": match.group(0).strip(),
            }

    # Try single value patterns
    for pattern in SALARY_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            val_str = match.group(1).replace(",", "")
            try:
                val = int(val_str)
                # Handle "k" suffix (e.g. "120k" = 120000)
                if re.search(r'\b' + re.escape(val_str) + r'\s*k\b', text, re.IGNORECASE):
                    val *= 1000
                # Handle Indian LPA format
                if currency == "INR" and re.search(r'\b(?:lpa|lakhs?)\b', text, re.IGNORECASE):
                    val = int(val * 100000)  # Convert lakhs to absolute

                return {
                    "min": val,
                    "max": val,
                    "currency": currency,
                    "raw": match.group(0).strip(),
                }
            except ValueError:
                continue

    return None


# ─────────────────────────────────────────────────────────────────────────────
# Structured Education Parsing
# ─────────────────────────────────────────────────────────────────────────────

GPA_PATTERN = r'(?:gpa|grade\s+point\s+average)\s*[:\s]+([\d.]+)\s*(?:/?\s*([\d.]+))?'

GRADUATION_YEAR_PATTERN = r'(?:graduated|graduation|class\s+of|expected\s+graduation)\s*[:\s]+(\d{4})'

# Also match "2020-2024" or "2021 - 2025" patterns in education section
YEAR_RANGE_PATTERN = r'(\d{4})\s*[-–]\s*(\d{4}|present|current)'

# Known top-tier institutions for ranking
TOP_TIER_INSTITUTIONS = {
    "mit", "massachusetts institute of technology",
    "stanford", "stanford university",
    "harvard", "harvard university",
    "yale", "yale university",
    "princeton", "princeton university",
    "caltech", "california institute of technology",
    "columbia", "columbia university",
    "university of chicago", "uchicago",
    "oxford", "university of oxford",
    "cambridge", "university of cambridge",
    "eth zurich", "eth",
    "tsinghua", "tsinghua university",
    "iit", "indian institute of technology",
    "nus", "national university of singapore",
    "imperial", "imperial college london",
    "uc berkeley", "university of california berkeley",
    "cmu", "carnegie mellon university",
    "georgia tech", "georgia institute of technology",
}

SECOND_TIER_INSTITUTIONS = {
    "ucla", "university of california los angeles",
    "university of michigan", "umich",
    "university of texas", "ut austin",
    "university of washington", "uw seattle",
    "university of illinois", "uiuc",
    "purdue", "purdue university",
    "university of wisconsin",
    "university of pennsylvania", "upenn",
    "cornell", "cornell university",
    "duke", "duke university",
    "johns hopkins", "jhu",
    "northwestern", "northwestern university",
    "rice", "rice university",
    "usc", "university of southern california",
    "nyu", "new york university",
    "lse", "london school of economics",
    "ucl", "university college london",
    "edinburgh", "university of edinburgh",
    "iim", "indian institute of management",
    "iisc", "indian institute of science",
    "bits", "bits pilani",
    "isb", "indian school of business",
}


def parse_education_details(resume_text: str) -> List[Dict[str, Any]]:
    """Parse structured education information from resume text.

    Args:
        resume_text: Resume text.

    Returns:
        List of education entries with degree, field, institution,
        gpa, graduation_year, and institution_tier.
    """
    if not resume_text:
        return []

    results = []

    # Find education section
    edu_section_match = re.search(
        r'(?:education|academic\s+background|qualifications)\b[:\s]*(.*?)(?=experience|employment|work|skills|certification|project|activities|$)',
        resume_text, re.DOTALL | re.IGNORECASE
    )

    edu_text = edu_section_match.group(1) if edu_section_match else resume_text

    # Split into entries (typically separated by newlines or degree keywords)
    entries = re.split(r'\n(?=[A-Z])', edu_text)

    for entry in entries:
        if len(entry.strip()) < 10:
            continue

        entry_lower = entry.lower()
        info: Dict[str, Any] = {}

        # Parse GPA
        gpa_match = re.search(GPA_PATTERN, entry, re.IGNORECASE)
        if gpa_match:
            try:
                gpa_val = float(gpa_match.group(1))
                max_gpa = float(gpa_match.group(2)) if gpa_match.group(2) else 4.0
                info["gpa"] = gpa_val
                info["gpa_max"] = max_gpa
                info["gpa_normalized"] = round(gpa_val / max_gpa, 3) if max_gpa > 0 else None
            except ValueError:
                pass

        # Parse graduation year
        grad_match = re.search(GRADUATION_YEAR_PATTERN, entry, re.IGNORECASE)
        if grad_match:
            info["graduation_year"] = int(grad_match.group(1))
        else:
            year_range_match = re.search(YEAR_RANGE_PATTERN, entry)
            if year_range_match:
                start_year = int(year_range_match.group(1))
                end = year_range_match.group(2)
                if end.isdigit():
                    info["graduation_year"] = int(end)
                elif end.lower() in ("present", "current"):
                    info["graduation_year"] = None
                    info["expected_graduation"] = True

        # Detect institution tier
        institution_tier = "standard"
        for inst in TOP_TIER_INSTITUTIONS:
            if inst in entry_lower:
                institution_tier = "top_tier"
                info["institution"] = entry.strip().split("\n")[0]
                break
        if institution_tier == "standard":
            for inst in SECOND_TIER_INSTITUTIONS:
                if inst in entry_lower:
                    institution_tier = "second_tier"
                    info["institution"] = entry.strip().split("\n")[0]
                    break

        info["institution_tier"] = institution_tier

        if len(info) > 1:  # More than just institution_tier
            info["raw_text"] = entry.strip()[:200]
            results.append(info)

    return results


# ─────────────────────────────────────────────────────────────────────────────
# International Date Parsing
# ─────────────────────────────────────────────────────────────────────────────

# Extended date patterns for international formats
INTERNATIONAL_DATE_PATTERNS = [
    # DD/MM/YYYY (European, Indian, Australian)
    (r'\b(\d{1,2})/(\d{1,2})/(\d{4})\b', "dmy"),
    # DD-MM-YYYY
    (r'\b(\d{1,2})-(\d{1,2})-(\d{4})\b', "dmy"),
    # DD.MM.YYYY (German, Russian)
    (r'\b(\d{1,2})\.(\d{1,2})\.(\d{4})\b', "dmy"),
    # YYYY/MM/DD (ISO, Japanese)
    (r'\b(\d{4})/(\d{1,2})/(\d{1,2})\b', "ymd"),
    # YYYY-MM-DD (ISO 8601)
    (r'\b(\d{4})-(\d{1,2})-(\d{1,2})\b', "ymd"),
    # MM/YYYY (already supported, but included for completeness)
    (r'\b(\d{1,2})/(\d{4})\b', "my"),
    # Month YYYY (e.g. "January 2020")
    (r'\b(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{4})\b', "month_name"),
    (r'\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s+(\d{4})\b', "month_abbr"),
    # YYYY年MM月 (Japanese)
    (r'(\d{4})年(\d{1,2})月', "ymd_jp"),
    # YYYY年MM月DD日 (Japanese full date)
    (r'(\d{4})年(\d{1,2})月(\d{1,2})日', "ymd_jp_full"),
    # DD de Month de YYYY (Spanish)
    (r'(\d{1,2})\s+de\s+(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+de\s+(\d{4})', "dmy_es"),
    # DD mois YYYY (French)
    (r'(\d{1,2})\s+(?:janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+(\d{4})', "dmy_fr"),
    # DD. Month YYYY (German)
    (r'(\d{1,2})\.\s+(?:januar|februar|märz|april|mai|juni|juli|august|september|oktober|november|dezember)\s+(\d{4})', "dmy_de"),
]

MONTH_NAMES = {
    "january": 1, "jan": 1, "enero": 1, "janvier": 1, "januar": 1,
    "february": 2, "feb": 2, "febrero": 2, "février": 2, "februar": 2,
    "march": 3, "mar": 3, "marzo": 3, "mars": 3, "märz": 3,
    "april": 4, "apr": 4, "abril": 4, "avril": 4,
    "may": 5, "mayo": 5, "mai": 5,
    "june": 6, "jun": 6, "junio": 6, "juin": 6, "juni": 6,
    "july": 7, "jul": 7, "julio": 7, "juillet": 7, "juli": 7,
    "august": 8, "aug": 8, "agosto": 8, "août": 8,
    "september": 9, "sep": 9, "sept": 9, "septiembre": 9, "septembre": 9,
    "october": 10, "oct": 10, "octubre": 10, "octobre": 10, "oktober": 10,
    "november": 11, "nov": 11, "noviembre": 11, "novembre": 11,
    "december": 12, "dec": 12, "diciembre": 12, "décembre": 12, "dezember": 12,
}


def parse_international_dates(text: str) -> List[Dict[str, Any]]:
    """Parse dates from text in various international formats.

    Args:
        text: Text to parse.

    Returns:
        List of parsed dates with original text, normalized date, and format type.
    """
    if not text:
        return []

    results = []

    for pattern, fmt_type in INTERNATIONAL_DATE_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            raw = match.group(0)
            groups = match.groups()

            parsed: Dict[str, Any] = {
                "raw": raw,
                "format_type": fmt_type,
            }

            try:
                if fmt_type == "dmy":
                    day, month, year = int(groups[0]), int(groups[1]), int(groups[2])
                    if day <= 31 and month <= 12:
                        parsed["day"] = day
                        parsed["month"] = month
                        parsed["year"] = year
                        parsed["normalized"] = f"{year:04d}-{month:02d}-{day:02d}"

                elif fmt_type == "ymd":
                    year, month, day = int(groups[0]), int(groups[1]), int(groups[2])
                    if day <= 31 and month <= 12:
                        parsed["day"] = day
                        parsed["month"] = month
                        parsed["year"] = year
                        parsed["normalized"] = f"{year:04d}-{month:02d}-{day:02d}"

                elif fmt_type == "my":
                    month, year = int(groups[0]), int(groups[1])
                    if month <= 12:
                        parsed["month"] = month
                        parsed["year"] = year
                        parsed["normalized"] = f"{year:04d}-{month:02d}"

                elif fmt_type in ("month_name", "month_abbr"):
                    year = int(groups[0])
                    month_name = raw.split()[0].lower()
                    month = MONTH_NAMES.get(month_name, 1)
                    parsed["month"] = month
                    parsed["year"] = year
                    parsed["normalized"] = f"{year:04d}-{month:02d}"

                elif fmt_type in ("ymd_jp", "ymd_jp_full"):
                    year = int(groups[0])
                    month = int(groups[1])
                    parsed["year"] = year
                    parsed["month"] = month
                    if len(groups) > 2:
                        parsed["day"] = int(groups[2])
                        parsed["normalized"] = f"{year:04d}-{month:02d}-{int(groups[2]):02d}"
                    else:
                        parsed["normalized"] = f"{year:04d}-{month:02d}"

                elif fmt_type in ("dmy_es", "dmy_fr", "dmy_de"):
                    day = int(groups[0])
                    year = int(groups[-1])
                    parsed["day"] = day
                    parsed["year"] = year
                    parsed["normalized"] = f"{year:04d}-XX-{day:02d}"

            except (ValueError, IndexError):
                continue

            if "normalized" in parsed:
                results.append(parsed)

    return results


def enrich_resume(resume_text: str) -> Dict[str, Any]:
    """Run all enrichment features on resume text.

    Args:
        resume_text: Full resume text.

    Returns:
        Dict with social_profiles, salary_expectation, education_details,
        and parsed_dates.
    """
    return {
        "social_profiles": extract_social_profiles(resume_text),
        "salary_expectation": parse_salary_expectation(resume_text),
        "education_details": parse_education_details(resume_text),
        "parsed_dates": parse_international_dates(resume_text),
    }

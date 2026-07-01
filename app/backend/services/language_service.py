"""Language detection and multi-language support service.

Detects the language of resume/JD text and provides language-aware
prompt construction for LLM calls. Supports English, Spanish, French,
German, Portuguese, and Mandarin Chinese.
"""

import logging
import re
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

try:
    from langdetect import detect as _langdetect_detect, DetectorFactory
    DetectorFactory.seed = 42  # Deterministic results
    _HAS_LANGDETECT = True
except ImportError:
    _HAS_LANGDETECT = False
    logger.info("langdetect not installed — language detection unavailable")

try:
    import langid
    _HAS_LANGID = True
except ImportError:
    _HAS_LANGID = False


# Supported languages with their ISO 639-1 codes
SUPPORTED_LANGUAGES: Dict[str, Dict[str, str]] = {
    "en": {"name": "English", "native_name": "English", "llm_instruction": "Respond in English."},
    "es": {"name": "Spanish", "native_name": "Español", "llm_instruction": "Responde en español."},
    "fr": {"name": "French", "native_name": "Français", "llm_instruction": "Répondez en français."},
    "de": {"name": "German", "native_name": "Deutsch", "llm_instruction": "Antworten Sie auf Deutsch."},
    "pt": {"name": "Portuguese", "native_name": "Português", "llm_instruction": "Responda em português."},
    "zh": {"name": "Chinese", "native_name": "中文", "llm_instruction": "用中文回答。"},
    "it": {"name": "Italian", "native_name": "Italiano", "llm_instruction": "Rispondi in italiano."},
    "nl": {"name": "Dutch", "native_name": "Nederlands", "llm_instruction": "Antwoord in het Nederlands."},
    "ja": {"name": "Japanese", "native_name": "日本語", "llm_instruction": "日本語で回答してください。"},
    "ko": {"name": "Korean", "native_name": "한국어", "llm_instruction": "한국어로 답변하세요."},
}

# Quick heuristic detection via character sets and common words
_HEURISTIC_PATTERNS: Dict[str, List[str]] = {
    "zh": [r'[\u4e00-\u9fff]'],
    "ja": [r'[\u3040-\u309f]', r'[\u30a0-\u30ff]'],
    "ko": [r'[\uac00-\ud7af]'],
}

_HEURISTIC_WORDS: Dict[str, List[str]] = {
    "es": ["experiencia", "educación", "habilidades", "trabajo", "empresa", "universidad",
           "responsabilidades", "proyecto", "desarrollo", "sistemas"],
    "fr": ["expérience", "éducation", "compétences", "travail", "entreprise", "université",
           "responsabilités", "projet", "développement", "systèmes"],
    "de": ["erfahrung", "bildung", "fähigkeiten", "arbeit", "unternehmen", "universität",
           "verantwortung", "projekt", "entwicklung", "systeme"],
    "pt": ["experiência", "educação", "habilidades", "trabalho", "empresa", "universidade",
           "responsabilidades", "projeto", "desenvolvimento", "sistemas"],
    "it": ["esperienza", "istruzione", "competenze", "lavoro", "azienda", "università",
           "responsabilità", "progetto", "sviluppo", "sistemi"],
    "nl": ["ervaring", "opleiding", "vaardigheden", "werk", "bedrijf", "universiteit",
           "verantwoordelijkheden", "project", "ontwikkeling", "systemen"],
    "en": ["experience", "education", "skills", "work", "company", "university",
           "responsibilities", "project", "development", "systems"],
}


def detect_language(text: str) -> str:
    """Detect the language of the given text.

    Uses langdetect or langid if available, with a heuristic fallback.
    Returns ISO 639-1 code (e.g. 'en', 'es', 'fr'). Defaults to 'en'.
    """
    if not text or len(text.strip()) < 20:
        return "en"

    # Check for Japanese-specific characters (hiragana/katakana) before Chinese
    # since Japanese also uses kanji which overlap with Chinese range
    for lang, patterns in _HEURISTIC_PATTERNS.items():
        if lang == "zh":
            continue  # Check zh last (kanji overlap)
        for pattern in patterns:
            if re.search(pattern, text):
                return lang
    # Now check Chinese (kanji only, no hiragana/katakana = likely Chinese)
    for pattern in _HEURISTIC_PATTERNS.get("zh", []):
        if re.search(pattern, text):
            return "zh"

    # Try langdetect
    if _HAS_LANGDETECT:
        try:
            lang = _langdetect_detect(text)
            if lang in SUPPORTED_LANGUAGES:
                return lang
            # langdetect may return 'pt-br' etc.
            base = lang.split("-")[0]
            if base in SUPPORTED_LANGUAGES:
                return base
        except Exception as e:
            logger.debug("langdetect failed: %s", e)

    # Try langid
    if _HAS_LANGID:
        try:
            lang, _ = langid.classify(text)
            if lang in SUPPORTED_LANGUAGES:
                return lang
            base = lang.split("-")[0]
            if base in SUPPORTED_LANGUAGES:
                return base
        except Exception as e:
            logger.debug("langid failed: %s", e)

    # Heuristic fallback: count common words per language
    text_lower = text.lower()
    best_lang = "en"
    best_score = 0
    for lang, words in _HEURISTIC_WORDS.items():
        score = sum(1 for w in words if w in text_lower)
        if score > best_score:
            best_score = score
            best_lang = lang

    return best_lang


def get_llm_language_instruction(lang_code: str) -> str:
    """Get the LLM instruction for responding in the detected language.

    Returns empty string for English (default) to avoid unnecessary tokens.
    """
    lang_info = SUPPORTED_LANGUAGES.get(lang_code, SUPPORTED_LANGUAGES["en"])
    if lang_code == "en":
        return ""
    return " " + lang_info["llm_instruction"]


def is_language_supported(lang_code: str) -> bool:
    """Check if a language code is supported."""
    return lang_code in SUPPORTED_LANGUAGES


def get_language_name(lang_code: str) -> str:
    """Get the English name for a language code."""
    return SUPPORTED_LANGUAGES.get(lang_code, {}).get("name", "Unknown")


def get_resume_language_context(resume_text: str) -> Dict[str, str]:
    """Detect resume language and return context for downstream processing.

    Returns dict with:
        - language: ISO 639-1 code
        - language_name: English name
        - llm_instruction: Instruction string for LLM prompts
    """
    lang = detect_language(resume_text)
    return {
        "language": lang,
        "language_name": get_language_name(lang),
        "llm_instruction": get_llm_language_instruction(lang),
    }

"""O*NET occupation-aware skill validation service.

Provides lightweight skill validation against official O*NET occupational
data.  Gracefully degrades when the local O*NET cache is unavailable.
"""

import logging
import os
from typing import List, Dict, Optional

from app.backend.services.onet.onet_cache import ONETCache

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = os.path.join("data", "onet", "db", "onet_cache.db")


class ONETValidator:
    """Occupation-aware skill validation using O*NET data."""

    def __init__(self, db_path: Optional[str] = None):
        """Initialize validator.

        If *db_path* is None, uses the default project-relative path.
        If the database does not exist or is empty, runs in degraded mode.
        """
        self._cache: Optional[ONETCache] = None
        self._available = False

        db_path = db_path or DEFAULT_DB_PATH
        try:
            if os.path.exists(db_path):
                cache = ONETCache(db_path)
                if cache.is_populated():
                    self._cache = cache
                    self._available = True
                    version = cache.get_version()
                    logger.info(
                        "O*NET validator ready (version=%s, db=%s)",
                        version or "unknown",
                        db_path,
                    )
                else:
                    logger.info("O*NET cache exists but is empty (%s)", db_path)
            else:
                logger.info("O*NET cache not found (%s) — running in degraded mode", db_path)
        except Exception as e:
            logger.warning("O*NET validator init failed: %s — degraded mode", e)

    @property
    def available(self) -> bool:
        """Whether O*NET data is available for validation."""
        return self._available

    def resolve_occupation(self, job_title: str) -> Optional[Dict]:
        """Map a job title to the best-matching O*NET SOC code.

        Returns a dict with keys ``soc_code``, ``title``, ``confidence``,
        or ``None`` if no match is found or O*NET is unavailable.
        """
        if not self._available or not job_title:
            return None

        matches = self._cache.find_soc_by_title(job_title)
        if not matches:
            return None

        # If multiple SOC codes match, prefer the one with the most technology skills
        best = None
        best_skill_count = -1
        for soc_code, title, score in matches:
            skills = self._cache.get_skills_for_occupation(soc_code)
            skill_count = len(skills)
            if score > (best[2] if best else 0):
                # Prefer higher match score; break ties by skill count
                if best is None or score > best[2] or (score == best[2] and skill_count > best_skill_count):
                    best = (soc_code, title, score)
                    best_skill_count = skill_count
            elif best is not None and score == best[2] and skill_count > best_skill_count:
                best = (soc_code, title, score)
                best_skill_count = skill_count

        if best is None:
            return None

        return {
            "soc_code": best[0],
            "title": best[1],
            "confidence": best[2],
        }

    def get_expected_skills(self, soc_code: str) -> List[Dict]:
        """Get technology skills expected for an occupation.

        Returns a list of dicts with keys:
        ``skill_name``, ``commodity_code``, ``commodity_title``,
        ``is_hot_technology``, ``is_in_demand``.
        """
        if not self._available or not soc_code:
            return []
        return self._cache.get_skills_for_occupation(soc_code)

    def validate_skill(self, skill_name: str, soc_code: str) -> Dict:
        """Check if a skill is recognized for this occupation.

        Returns a dict with keys:
        ``valid`` (bool), ``is_hot`` (bool), ``is_in_demand`` (bool),
        ``commodity`` (str or None).
        """
        if not self._available or not skill_name or not soc_code:
            return {"valid": False, "is_hot": False, "is_in_demand": False, "commodity": None}

        norm = skill_name.strip().lower()

        # Exact match first
        skills = self._cache.get_skills_for_occupation(soc_code)
        for s in skills:
            if s["skill_name"].lower() == norm:
                return {
                    "valid": True,
                    "is_hot": bool(s["is_hot_technology"]),
                    "is_in_demand": bool(s["is_in_demand"]),
                    "commodity": s["commodity_title"],
                }

        # LIKE fallback via the cache helper
        if self._cache.skill_exists_for_occupation(norm, soc_code):
            # We know it exists but need the full record; re-scan
            for s in skills:
                if norm in s["skill_name"].lower():
                    return {
                        "valid": True,
                        "is_hot": bool(s["is_hot_technology"]),
                        "is_in_demand": bool(s["is_in_demand"]),
                        "commodity": s["commodity_title"],
                    }

        return {"valid": False, "is_hot": False, "is_in_demand": False, "commodity": None}

    def validate_skills_batch(self, skills: List[str], job_title: str) -> Dict:
        """Validate a batch of skills against a job title's expected skill set.

        Returns a dict with keys:
        ``soc_code``, ``occupation_title``, ``validated``,
        ``occupation_match_ratio``.
        """
        if not self._available or not skills or not job_title:
            return {
                "soc_code": None,
                "occupation_title": None,
                "validated": [],
                "occupation_match_ratio": 0.0,
            }

        occ = self.resolve_occupation(job_title)
        if occ is None:
            return {
                "soc_code": None,
                "occupation_title": None,
                "validated": [],
                "occupation_match_ratio": 0.0,
            }

        soc_code = occ["soc_code"]
        occ_skills = self._cache.get_skills_for_occupation(soc_code)
        occ_skill_names = {s["skill_name"].lower() for s in occ_skills}

        validated = []
        recognized_count = 0
        for skill in skills:
            if not skill or not isinstance(skill, str):
                validated.append(
                    {
                        "skill": skill,
                        "recognized": False,
                        "is_hot": False,
                        "is_in_demand": False,
                    }
                )
                continue

            norm = skill.strip().lower()
            matched = None
            for s in occ_skills:
                if s["skill_name"].lower() == norm or norm in s["skill_name"].lower():
                    matched = s
                    break

            if matched:
                recognized_count += 1
                validated.append(
                    {
                        "skill": skill,
                        "recognized": True,
                        "is_hot": bool(matched["is_hot_technology"]),
                        "is_in_demand": bool(matched["is_in_demand"]),
                    }
                )
            else:
                validated.append(
                    {
                        "skill": skill,
                        "recognized": False,
                        "is_hot": False,
                        "is_in_demand": False,
                    }
                )

        match_ratio = recognized_count / max(len(skills), 1)

        # Dict-indexed form for downstream filtering (e.g., high-collision guard)
        skill_validations = {
            v["skill"]: {
                "valid": v["recognized"],
                "is_hot": v["is_hot"],
                "is_in_demand": v["is_in_demand"],
            }
            for v in validated
        }

        return {
            "soc_code": soc_code,
            "occupation_title": occ["title"],
            "validated": validated,
            "skill_validations": skill_validations,
            "occupation_match_ratio": round(match_ratio, 4),
        }

    def get_hot_technologies(self) -> List[str]:
        """Return all hot/in-demand technologies across occupations."""
        if not self._available:
            return []
        return self._cache.get_all_hot_technologies()

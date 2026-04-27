"""
Single source of truth for all scoring constants, thresholds, and domain configuration.
All services MUST import from this module instead of defining local copies.
"""

from typing import Dict, List, Tuple


# --- Recommendation Thresholds ---
RECOMMENDATION_THRESHOLDS = {
    "shortlist": 72,
    "consider": 45,
    "reject": 0,
}


# --- Seniority Ranges ---
# (min_years_inclusive, max_years_exclusive)
SENIORITY_RANGES = {
    "intern": (0, 1),
    "junior": (0, 2),
    "mid": (2, 5),
    "senior": (5, 10),
    "lead": (7, 15),
    "principal": (10, 25),
    "staff": (8, 20),
    "architect": (10, 25),
    "director": (12, 30),
}


# --- Default Scoring Weights ---
# Used by hybrid_pipeline.py and agent_pipeline.py
DEFAULT_WEIGHTS = {
    "skills":       0.30,
    "experience":   0.20,
    "architecture": 0.15,
    "education":    0.10,
    "timeline":     0.10,
    "domain":       0.10,
    "risk":         0.15,
}


# --- Domain Keywords ---
DOMAIN_KEYWORDS: Dict[str, List[str]] = {
    "backend":      ["fastapi", "django", "flask", "spring", "rest api", "grpc",
                     "postgresql", "mysql", "redis", "microservices", "golang", "node.js",
                     "express", "api development", "backend", "server side", "database design",
                     "sqlalchemy", "orm", "celery", "message queue"],
    "frontend":     ["react", "vue", "angular", "next.js", "nuxt", "tailwind", "html", "css",
                     "webpack", "vite", "typescript", "ui development", "frontend", "responsive",
                     "web components", "ssr", "spa", "pwa", "accessibility", "figma"],
    "fullstack":    ["full stack", "fullstack", "full-stack", "frontend and backend",
                     "end-to-end", "mern", "mean", "lamp", "jamstack"],
    "data_science": ["pandas", "numpy", "sklearn", "scikit", "jupyter", "data analysis",
                     "statistics", "tableau", "power bi", "data pipeline", "etl",
                     "feature engineering", "regression", "classification", "clustering",
                     "time series", "sql", "bigquery", "snowflake", "dbt"],
    "ml_ai":        ["machine learning", "deep learning", "neural network", "nlp", "pytorch",
                     "tensorflow", "transformers", "llm", "computer vision", "reinforcement learning",
                     "mlops", "model training", "fine-tuning", "hugging face", "langchain",
                     "rag", "vector database", "embeddings", "generative ai"],
    "devops":       ["kubernetes", "docker", "terraform", "ansible", "jenkins", "ci/cd", "helm",
                     "argo", "prometheus", "grafana", "infrastructure as code", "sre",
                     "linux", "bash", "monitoring", "observability", "cloud", "gitops",
                     "deployment", "devops"],
    "embedded":     ["embedded", "firmware", "rtos", "microcontroller", "fpga", "uart",
                     "can bus", "i2c", "spi", "arm cortex", "device driver", "bsp",
                     "real-time", "baremetal", "freertos", "yocto", "iso 26262", "misra",
                     "embedded linux", "bootloader"],
    "mobile":       ["ios", "android", "react native", "flutter", "swift", "kotlin",
                     "xcode", "mobile app", "jetpack compose", "swiftui", "app store",
                     "mobile development", "push notification"],
    "management":   ["product manager", "engineering manager", "team lead", "delivery manager",
                     "scrum master", "agile coach", "roadmap", "stakeholder", "okr",
                     "program manager", "pmo", "budget", "hiring"],
}


# --- Degree Scores ---
DEGREE_SCORES: Dict[str, int] = {
    "phd": 100, "ph.d": 100, "doctorate": 100, "doctor of": 100,
    "master": 85, "msc": 85, "m.sc": 85, "mba": 82, "mca": 85,
    "mtech": 85, "m.tech": 85, "m.e.": 85, "ms ": 85, "m.s.": 85,
    "me ": 85, "post graduate": 82, "postgraduate": 82, "pg diploma": 75,
    "bachelor": 70, "bsc": 70, "b.sc": 70, "be ": 70, "b.e.": 70,
    "btech": 70, "b.tech": 70, "bs ": 70, "b.s.": 70, "ba ": 65,
    "b.a.": 65, "bca": 65, "bba": 62,
    "diploma": 50, "associate": 48, "hnd": 45,
    "certif": 38, "bootcamp": 35, "course": 30,
}


# --- Field Relevance ---
FIELD_RELEVANCE: Dict[str, List[str]] = {
    "backend":      ["computer science", "computer engineering", "software engineering",
                     "information technology", "cse", "it", "bca", "mca", "electronics"],
    "frontend":     ["computer science", "software engineering", "web", "human computer interaction",
                     "hci", "interaction design", "information technology"],
    "fullstack":    ["computer science", "software engineering", "information technology",
                     "cse", "mca", "bca"],
    "data_science": ["data science", "statistics", "mathematics", "computer science",
                     "analytics", "information systems", "operations research", "economics"],
    "ml_ai":        ["artificial intelligence", "machine learning", "computer science",
                     "computational", "data science", "statistics", "mathematics"],
    "devops":       ["computer science", "computer engineering", "information technology",
                     "systems", "networking", "telecommunications"],
    "embedded":     ["electronics", "electrical", "computer engineering", "embedded",
                     "vlsi", "instrumentation", "mechatronics", "robotics", "avionics"],
    "mobile":       ["computer science", "software engineering", "information technology",
                     "mobile computing"],
    "management":   ["business", "management", "mba", "project management", "administration",
                     "operations", "strategy"],
    "other":        ["computer", "information", "engineering", "technology", "science",
                     "mathematics", "systems"],
}


# --- Risk Severity Penalties ---
RISK_SEVERITY_PENALTIES = {
    "high": 20,
    "medium": 10,
    "low": 4,
}


# --- Weight Mapper Schemas ---
# Legacy 4-weight schema (for backward compatibility)
LEGACY_WEIGHTS = {
    "skills": 0.40,
    "experience": 0.35,
    "stability": 0.15,
    "education": 0.10,
}

# New universal-adaptive weight schema
NEW_DEFAULT_WEIGHTS = {
    "core_competencies": 0.30,
    "experience": 0.20,
    "domain_fit": 0.20,
    "education": 0.10,
    "career_trajectory": 0.10,
    "role_excellence": 0.10,
    "risk": -0.10,
}

# Old backend schema (7 tech-centric weights)
OLD_BACKEND_WEIGHTS = {
    "skills": 0.30,
    "experience": 0.20,
    "architecture": 0.15,
    "education": 0.10,
    "timeline": 0.10,
    "domain": 0.10,
    "risk": 0.15,
}

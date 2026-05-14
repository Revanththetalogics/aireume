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


# ============================================================================
# ENTERPRISE-GRADE JOB FUNCTION TAXONOMY (Phase 1 Enhancement)
# ============================================================================

# Job Function Skill Taxonomy: Maps job functions to core, adjacent, and irrelevant skills
# This enables context-aware skill validation during matching
JOB_FUNCTION_SKILL_TAXONOMY: Dict[str, Dict[str, List[str]]] = {
    "account_based_marketing": {
        "core_skills": [
            "account-based marketing", "abm", "demand generation", "lead generation",
            "marketing automation", "salesforce", "marketing analytics", "segment",
            "target account identification", "personalization", "multi-channel campaigns"
        ],
        "adjacent_skills": [
            "content marketing", "seo", "sem", "social media marketing",
            "email marketing", "crm", "customer journey mapping", "attribution modeling",
            "marketing strategy", "b2b marketing", "data analysis", "communication"
        ],
        "irrelevant_skills": [
            "python", "java", "kubernetes", "react", "sql", "machine learning",
            "embedded systems", "mobile development", "devops"
        ],
        "core_responsibilities": [
            "develop abm strategies", "identify target accounts", "create personalized campaigns",
            "collaborate with sales", "analyze campaign performance", "manage marketing automation",
            "track account engagement", "optimize marketing funnel"
        ]
    },
    "backend_engineering": {
        "core_skills": [
            "python", "java", "go", "node.js", "fastapi", "django", "spring boot",
            "express", "postgresql", "mysql", "redis", "mongodb", "api development",
            "rest api", "graphql", "microservices", "system design"
        ],
        "adjacent_skills": [
            "docker", "kubernetes", "ci/cd", "aws", "gcp", "azure", "terraform",
            "graphql", "grpc", "message queues", "caching", "database optimization",
            "testing", "agile", "communication", "collaboration"
        ],
        "irrelevant_skills": [
            "photoshop", "illustrator", "abm", "marketing automation", "salesforce",
            "financial modeling", "hr management", "graphic design"
        ],
        "core_responsibilities": [
            "design and implement apis", "build scalable backend systems", "optimize database queries",
            "ensure system reliability", "write clean maintainable code", "collaborate with frontend",
            "implement security best practices", "monitor system performance"
        ]
    },
    "frontend_engineering": {
        "core_skills": [
            "react", "vue", "angular", "typescript", "javascript", "html", "css",
            "next.js", "responsive design", "web accessibility", "state management",
            "webpack", "vite", "tailwind", "sass"
        ],
        "adjacent_skills": [
            "figma", "ui/ux design", "testing", "performance optimization", "seo",
            "progressive web apps", "git", "agile", "communication", "collaboration"
        ],
        "irrelevant_skills": [
            "python backend", "database administration", "network security",
            "financial analysis", "hr policies", "marketing strategy"
        ],
        "core_responsibilities": [
            "build responsive user interfaces", "implement pixel-perfect designs",
            "optimize frontend performance", "ensure cross-browser compatibility",
            "write reusable components", "collaborate with designers", "implement accessibility standards"
        ]
    },
    "data_science": {
        "core_skills": [
            "python", "sql", "pandas", "numpy", "scikit-learn", "data analysis",
            "statistics", "machine learning", "data visualization", "tableau",
            "power bi", "feature engineering", "hypothesis testing"
        ],
        "adjacent_skills": [
            "big data", "spark", "hadoop", "cloud platforms", "deep learning",
            "nlp", "etl", "data engineering", "communication", "storytelling",
            "business acumen", "a/b testing"
        ],
        "irrelevant_skills": [
            "react", "angular", "mobile development", "graphic design",
            "marketing automation", "sales management", "hr policies"
        ],
        "core_responsibilities": [
            "analyze complex datasets", "build predictive models", "extract actionable insights",
            "create data visualizations", "present findings to stakeholders", "design experiments",
            "collaborate with engineering", "ensure data quality"
        ]
    },
    "devops_engineering": {
        "core_skills": [
            "docker", "kubernetes", "terraform", "ansible", "jenkins", "ci/cd",
            "aws", "gcp", "azure", "linux", "bash", "monitoring", "prometheus",
            "grafana", "infrastructure as code"
        ],
        "adjacent_skills": [
            "python", "go", "git", "networking", "security", "database administration",
            "scripting", "automation", "agile", "collaboration", "incident response"
        ],
        "irrelevant_skills": [
            "react", "marketing automation", "financial modeling", "graphic design",
            "content writing", "sales strategy", "hr management"
        ],
        "core_responsibilities": [
            "manage cloud infrastructure", "implement ci/cd pipelines", "ensure system reliability",
            "automate deployment processes", "monitor system performance", "respond to incidents",
            "optimize infrastructure costs", "implement security best practices"
        ]
    },
    "product_management": {
        "core_skills": [
            "product strategy", "roadmap planning", "user research", "agile", "scrum",
            "stakeholder management", "data analysis", "a/b testing", "user stories",
            "prioritization", "market research", "competitive analysis"
        ],
        "adjacent_skills": [
            "sql", "analytics tools", "wireframing", "communication", "leadership",
            "project management", "technical understanding", "design thinking",
            "customer development", "go-to-market strategy"
        ],
        "irrelevant_skills": [
            "python programming", "database administration", "network configuration",
            "graphic design tools", "video editing", "accounting"
        ],
        "core_responsibilities": [
            "define product vision", "prioritize features", "gather user requirements",
            "collaborate with engineering", "analyze product metrics", "conduct user research",
            "manage stakeholder expectations", "drive product launches"
        ]
    },
    "sales": {
        "core_skills": [
            "sales strategy", "crm", "salesforce", "pipeline management", "negotiation",
            "lead generation", "account management", "b2b sales", "closing deals",
            "sales forecasting", "prospecting", "relationship building"
        ],
        "adjacent_skills": [
            "marketing", "communication", "presentation skills", "data analysis",
            "social selling", "email outreach", "linkedin", "customer success",
            "contract negotiation", "territory management"
        ],
        "irrelevant_skills": [
            "python", "react", "kubernetes", "database design", "machine learning",
            "graphic design", "video production", "accounting"
        ],
        "core_responsibilities": [
            "drive revenue growth", "build client relationships", "manage sales pipeline",
            "conduct product demos", "negotiate contracts", "exceed sales targets",
            "collaborate with marketing", "provide market feedback"
        ]
    }
}

# Job Function Detection Keywords (maps JD keywords to job functions)
JOB_FUNCTION_KEYWORDS: Dict[str, List[str]] = {
    "account_based_marketing": [
        "abm", "account-based marketing", "demand generation marketer",
        "b2b marketer", "growth marketer", "field marketer"
    ],
    "backend_engineering": [
        "backend engineer", "backend developer", "server-side developer",
        "api developer", "software engineer backend", "platform engineer"
    ],
    "frontend_engineering": [
        "frontend engineer", "frontend developer", "ui engineer",
        "ui developer", "web developer", "javascript developer"
    ],
    "data_science": [
        "data scientist", "data analyst", "machine learning engineer",
        "analytics engineer", "business intelligence", "bi analyst"
    ],
    "devops_engineering": [
        "devops engineer", "site reliability engineer", "sre",
        "platform engineer", "infrastructure engineer", "cloud engineer"
    ],
    "product_management": [
        "product manager", "senior product manager", "director of product",
        "vp product", "head of product", "technical product manager"
    ],
    "sales": [
        "account executive", "sales representative", "sales manager",
        "business development", "ae", "sdr", "bdr", "sales director"
    ]
}

# Generic Soft Skills (should NOT be in must-have unless explicitly emphasized)
GENERIC_SOFT_SKILLS = {
    "communication", "collaboration", "teamwork", "leadership", "problem solving",
    "analytical thinking", "creativity", "adaptability", "time management",
    "attention to detail", "critical thinking", "interpersonal skills",
    "organizational skills", "multitasking", "work ethic", "initiative"
}

# Linguistic Cues for Skill Importance
MUST_HAVE_CUES = [
    "must have", "must-have", "required", "essential", "mandatory",
    "non-negotiable", "critical", "core requirement", "key requirement",
    "qualifications:", "requirements:", "must possess", "should have"
]

NICE_TO_HAVE_CUES = [
    "nice to have", "nice-to-have", "preferred", "bonus", "plus",
    "good to have", "desirable", "ideal candidate", "would be great",
    "beneficial", "advantageous", "a plus"
]

# Enterprise Skill Classification Settings
MAX_REQUIRED_SKILLS = 12
MAX_NICE_TO_HAVE_SKILLS = 8
MIN_REQUIRED_SKILLS = 3
SOFT_SKILL_THRESHOLD = 0.30  # Max 30% of required skills can be soft skills

# Confidence Thresholds
HIGH_CONFIDENCE = 0.85
MEDIUM_CONFIDENCE = 0.70
LOW_CONFIDENCE_THRESHOLD = 0.70


# --- Skill Synonyms (variant/abbreviation → canonical form) ---
SKILL_SYNONYMS = {
    # Language abbreviations
    "js": "javascript", "ts": "typescript", "py": "python",
    "rb": "ruby", "cs": "csharp", "c#": "csharp", "c++": "cpp",
    "cpp": "cpp", "go": "golang", "rs": "rust",

    # Framework variants
    "react.js": "react", "reactjs": "react", "react native": "react native",
    "vue.js": "vue", "vuejs": "vue",
    "angular.js": "angularjs", "angularjs": "angularjs",
    "node.js": "nodejs", "node": "nodejs",
    "next.js": "nextjs", "nuxt.js": "nuxtjs",
    "express.js": "express", "expressjs": "express",
    "nest.js": "nestjs", "nestjs": "nestjs",

    # Database variants
    "postgres": "postgresql", "pg": "postgresql",
    "mongo": "mongodb", "mongodb": "mongodb",
    "ms sql": "mssql", "sql server": "mssql",
    "mysql": "mysql", "maria": "mariadb", "mariadb": "mariadb",
    "dynamodb": "dynamodb", "dynamo": "dynamodb",
    "redis": "redis", "memcache": "memcached",

    # Cloud/DevOps
    "k8s": "kubernetes", "kube": "kubernetes",
    "aws": "aws", "amazon web services": "aws",
    "gcp": "google cloud platform", "google cloud": "google cloud platform",
    "azure": "microsoft azure", "ms azure": "microsoft azure",
    "tf": "terraform", "gh actions": "github actions",
    "ci/cd": "cicd", "ci cd": "cicd",

    # Tools
    "git": "git", "github": "github", "gitlab": "gitlab",
    "vscode": "visual studio code", "vs code": "visual studio code",
    "docker compose": "docker-compose",
    "rabbitmq": "rabbitmq", "rabbit": "rabbitmq",
    "kafka": "apache kafka",
    "elasticsearch": "elasticsearch", "elastic": "elasticsearch", "es": "elasticsearch",

    # Data/ML
    "ml": "machine learning", "ai": "artificial intelligence",
    "dl": "deep learning", "nlp": "natural language processing",
    "cv": "computer vision",
    "pytorch": "pytorch", "torch": "pytorch",
    "sklearn": "scikit-learn", "scikit learn": "scikit-learn",
    "pandas": "pandas", "numpy": "numpy",

    # Mobile
    "rn": "react native", "ios": "ios", "android": "android",
    "flutter": "flutter", "swift": "swift", "kotlin": "kotlin",
    "objective-c": "objective-c", "objc": "objective-c",

    # Testing
    "jest": "jest", "mocha": "mocha", "pytest": "pytest",
    "junit": "junit", "cypress": "cypress", "selenium": "selenium",

    # Messaging/API
    "rest": "rest api", "restful": "rest api", "rest api": "rest api",
    "graphql": "graphql", "grpc": "grpc",
    "websocket": "websockets", "ws": "websockets",

    # Methodologies
    "agile": "agile", "scrum": "scrum", "kanban": "kanban",
    "tdd": "test driven development", "bdd": "behavior driven development",
    "oop": "object oriented programming",

    # Frontend
    "html5": "html", "css3": "css",
    "sass": "sass", "scss": "sass", "less": "less",
    "tailwind": "tailwindcss", "tailwind css": "tailwindcss",
    "bootstrap": "bootstrap", "material ui": "material-ui", "mui": "material-ui",

    # Others
    "linux": "linux", "unix": "unix", "bash": "bash", "shell": "shell scripting",
    "powershell": "powershell", "ps": "powershell",
    "nginx": "nginx", "apache": "apache http server",
}


# --- Skill Hierarchy (child skill → parent + category) ---
SKILL_HIERARCHY = {
    # Frontend Frameworks → Language
    "react": {"parent": "javascript", "category": "frontend_framework"},
    "vue": {"parent": "javascript", "category": "frontend_framework"},
    "angular": {"parent": "typescript", "category": "frontend_framework"},
    "svelte": {"parent": "javascript", "category": "frontend_framework"},
    "nextjs": {"parent": "react", "category": "fullstack_framework"},
    "nuxtjs": {"parent": "vue", "category": "fullstack_framework"},

    # Backend Frameworks → Language
    "django": {"parent": "python", "category": "backend_framework"},
    "fastapi": {"parent": "python", "category": "backend_framework"},
    "flask": {"parent": "python", "category": "backend_framework"},
    "spring": {"parent": "java", "category": "backend_framework"},
    "spring boot": {"parent": "java", "category": "backend_framework"},
    "express": {"parent": "nodejs", "category": "backend_framework"},
    "nestjs": {"parent": "typescript", "category": "backend_framework"},
    "rails": {"parent": "ruby", "category": "backend_framework"},
    "laravel": {"parent": "php", "category": "backend_framework"},
    "asp.net": {"parent": "csharp", "category": "backend_framework"},
    "gin": {"parent": "golang", "category": "backend_framework"},
    "actix": {"parent": "rust", "category": "backend_framework"},

    # Container/Orchestration
    "kubernetes": {"parent": "docker", "category": "container_orchestration"},
    "docker-compose": {"parent": "docker", "category": "container_orchestration"},
    "helm": {"parent": "kubernetes", "category": "package_management"},

    # Cloud Services → Platform
    "lambda": {"parent": "aws", "category": "serverless"},
    "ec2": {"parent": "aws", "category": "compute"},
    "s3": {"parent": "aws", "category": "storage"},
    "rds": {"parent": "aws", "category": "database"},
    "cloud functions": {"parent": "google cloud platform", "category": "serverless"},
    "azure functions": {"parent": "microsoft azure", "category": "serverless"},

    # Data/ML → Foundation
    "tensorflow": {"parent": "python", "category": "ml_framework"},
    "pytorch": {"parent": "python", "category": "ml_framework"},
    "scikit-learn": {"parent": "python", "category": "ml_library"},
    "pandas": {"parent": "python", "category": "data_library"},
    "numpy": {"parent": "python", "category": "data_library"},
    "spark": {"parent": "python", "category": "big_data"},

    # Testing → Language
    "jest": {"parent": "javascript", "category": "testing_framework"},
    "pytest": {"parent": "python", "category": "testing_framework"},
    "junit": {"parent": "java", "category": "testing_framework"},
    "cypress": {"parent": "javascript", "category": "e2e_testing"},

    # Mobile
    "react native": {"parent": "react", "category": "mobile_framework"},
    "flutter": {"parent": "dart", "category": "mobile_framework"},
    "swiftui": {"parent": "swift", "category": "ui_framework"},
    "jetpack compose": {"parent": "kotlin", "category": "ui_framework"},

    # IaC
    "terraform": {"parent": "infrastructure as code", "category": "iac"},
    "cloudformation": {"parent": "aws", "category": "iac"},
    "ansible": {"parent": "infrastructure as code", "category": "configuration_management"},

    # Databases → Category
    "postgresql": {"parent": "sql", "category": "relational_database"},
    "mysql": {"parent": "sql", "category": "relational_database"},
    "mssql": {"parent": "sql", "category": "relational_database"},
    "mongodb": {"parent": "nosql", "category": "document_database"},
    "redis": {"parent": "nosql", "category": "key_value_store"},
    "elasticsearch": {"parent": "nosql", "category": "search_engine"},
}

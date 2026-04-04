"""
Hybrid Analysis Pipeline — Python-first, single LLM call for narrative.

Architecture:
  Phase 1 (Python, ~1-2s): parse_jd_rules → parse_resume_rules → match_skills_rules
                            → score_education/experience/domain → compute_fit_score
  Phase 2 (LLM, ~40s):     explain_with_llm (generates strengths, weaknesses,
                            rationale, interview questions)
  Fallback:                 if LLM times out, _build_fallback_narrative returns
                            deterministic text — result is ALWAYS returned.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from typing import AsyncGenerator, Dict, Any, List, Optional

log = logging.getLogger("aria.hybrid")

# ─── Semaphore — 2 concurrent LLM calls per worker ───────────────────────────
_LLM_SEMAPHORE: Optional[asyncio.Semaphore] = None


def _get_semaphore() -> asyncio.Semaphore:
    global _LLM_SEMAPHORE
    if _LLM_SEMAPHORE is None:
        _LLM_SEMAPHORE = asyncio.Semaphore(2)
    return _LLM_SEMAPHORE


# ─── LLM singleton ───────────────────────────────────────────────────────────
_REASONING_LLM = None


def _get_llm():
    global _REASONING_LLM
    if _REASONING_LLM is None:
        try:
            from langchain_ollama import ChatOllama
            _REASONING_LLM = ChatOllama(
                model=os.getenv("OLLAMA_MODEL", "gemma4:26b"),
                base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
                temperature=0.1,
                format="json",
                num_predict=1500,
                num_ctx=4096,
            )
        except Exception as e:
            log.warning("LLM init failed: %s", e)
    return _REASONING_LLM


# ═══════════════════════════════════════════════════════════════════════════════
# SKILLS REGISTRY
# ═══════════════════════════════════════════════════════════════════════════════

MASTER_SKILLS: List[str] = [
    # ── Programming languages ──────────────────────────────────────────────────
    "python", "java", "javascript", "typescript", "c++", "c#", "c", "golang", "go",
    "rust", "scala", "kotlin", "swift", "ruby", "php", "r", "matlab", "perl",
    "haskell", "erlang", "elixir", "clojure", "f#", "lua", "dart", "zig", "ada",
    "assembly", "bash", "powershell", "groovy", "cobol", "fortran", "vba",
    # ── Web frameworks ─────────────────────────────────────────────────────────
    "react", "vue.js", "vue", "angular", "next.js", "nuxt.js", "svelte", "astro",
    "remix", "gatsby", "ember.js", "backbone.js", "jquery", "bootstrap", "tailwind",
    "material ui", "chakra ui", "ant design", "storybook",
    "node.js", "express.js", "fastapi", "django", "flask", "tornado", "aiohttp",
    "starlette", "litestar", "spring boot", "spring", "quarkus", "micronaut",
    "nestjs", "koa", "hapi", "feathers", "strapi", "rails", "sinatra", "laravel",
    "symfony", "codeigniter", "gin", "fiber", "echo", "chi", "actix", "axum", "rocket",
    # ── Databases ──────────────────────────────────────────────────────────────
    "postgresql", "mysql", "sqlite", "mariadb", "oracle", "microsoft sql server",
    "mongodb", "redis", "elasticsearch", "cassandra", "dynamodb", "couchdb",
    "neo4j", "influxdb", "timescaledb", "cockroachdb", "planetscale",
    "snowflake", "bigquery", "redshift", "databricks", "clickhouse",
    "supabase", "firebase", "firestore", "realm", "fauna", "deno kv",
    "sqlalchemy", "hibernate", "prisma", "typeorm", "sequelize", "drizzle",
    "mongoose", "redis om",
    # ── Cloud platforms ────────────────────────────────────────────────────────
    "amazon web services", "aws", "google cloud platform", "gcp", "microsoft azure",
    "azure", "digital ocean", "linode", "vultr", "hetzner", "oracle cloud",
    "ibm cloud", "alibaba cloud", "cloudflare", "vercel", "netlify", "heroku",
    "fly.io", "render", "railway",
    # ── AWS services ───────────────────────────────────────────────────────────
    "ec2", "s3", "lambda", "ecs", "eks", "rds", "aurora", "elasticache",
    "api gateway", "cloudfront", "route53", "iam", "cloudwatch", "sns", "sqs",
    "kinesis", "glue", "athena", "emr", "sagemaker", "bedrock",
    # ── DevOps & infrastructure ────────────────────────────────────────────────
    "docker", "kubernetes", "helm", "terraform", "ansible", "puppet", "chef",
    "vagrant", "packer", "jenkins", "github actions", "gitlab ci", "circleci",
    "travis ci", "bitbucket pipelines", "argo cd", "flux", "spinnaker", "tekton",
    "prometheus", "grafana", "datadog", "new relic", "dynatrace", "splunk",
    "elk stack", "loki", "jaeger", "zipkin", "opentelemetry",
    "nginx", "apache", "traefik", "envoy", "istio", "linkerd", "consul",
    "vault", "linux", "unix", "ubuntu", "centos", "rhel", "debian",
    "ci/cd", "devops", "sre", "infrastructure as code", "gitops",
    # ── AI / ML ────────────────────────────────────────────────────────────────
    "machine learning", "deep learning", "neural networks", "natural language processing",
    "nlp", "computer vision", "reinforcement learning", "generative ai",
    "large language models", "llm", "transformers", "bert", "gpt",
    "pytorch", "tensorflow", "keras", "jax", "mxnet", "caffe",
    "scikit-learn", "xgboost", "lightgbm", "catboost", "statsmodels",
    "hugging face", "langchain", "llamaindex", "ollama", "openai",
    "anthropic", "cohere", "vector database", "rag", "fine-tuning",
    "mlflow", "wandb", "optuna", "ray", "kubeflow", "vertex ai",
    "opencv", "pillow", "albumentations",
    # ── Data science & analytics ───────────────────────────────────────────────
    "pandas", "numpy", "scipy", "matplotlib", "seaborn", "plotly", "bokeh",
    "jupyter", "jupyter notebook", "colab", "dask", "polars", "vaex",
    "apache spark", "pyspark", "hadoop", "hive", "pig", "flink",
    "apache kafka", "rabbitmq", "celery", "airflow", "prefect", "dagster",
    "dbt", "fivetran", "airbyte", "stitch", "etl", "data pipeline",
    "tableau", "power bi", "looker", "metabase", "superset", "grafana",
    "excel", "google sheets", "data analysis", "statistics", "a/b testing",
    # ── Embedded / systems ─────────────────────────────────────────────────────
    "embedded", "rtos", "freertos", "zephyr", "vxworks", "qnx", "embedded linux",
    "microcontroller", "fpga", "arm", "arm cortex", "avr", "pic",
    "uart", "spi", "i2c", "can bus", "modbus", "ethernet",
    "tcp/ip", "udp", "mqtt", "coap", "ble", "zigbee", "lorawan",
    "device driver", "bsp", "bootloader", "firmware", "real-time",
    "ipc", "multithreading", "multiprocessing", "posix",
    "cmake", "makefile", "openocd", "jtag", "gdb",
    "iso 26262", "misra", "do-178", "sil4", "functional safety",
    # ── Mobile ─────────────────────────────────────────────────────────────────
    "ios", "android", "react native", "flutter", "xamarin", "ionic", "capacitor",
    "swift", "swiftui", "objective-c", "kotlin", "jetpack compose",
    "xcode", "android studio", "expo", "firebase", "appcenter",
    # ── Testing ────────────────────────────────────────────────────────────────
    "unit testing", "integration testing", "e2e testing", "tdd", "bdd",
    "pytest", "unittest", "jest", "vitest", "mocha", "jasmine", "cypress",
    "playwright", "selenium", "appium", "postman", "insomnia",
    "k6", "locust", "jmeter", "gatling",
    "sonarqube", "codecov", "coveralls", "code review",
    # ── Architecture & design ──────────────────────────────────────────────────
    "microservices", "monolith", "event-driven", "cqrs", "event sourcing",
    "domain driven design", "ddd", "hexagonal architecture", "clean architecture",
    "rest api", "graphql", "grpc", "websocket", "mqtt", "openapi", "swagger",
    "system design", "distributed systems", "high availability", "scalability",
    "design patterns", "solid", "ooad", "uml", "soa",
    # ── Security ───────────────────────────────────────────────────────────────
    "oauth2", "jwt", "saml", "ldap", "iam", "rbac",
    "tls", "ssl", "cryptography", "penetration testing", "owasp",
    "soc2", "gdpr", "hipaa", "pci dss",
    # ── Project management ─────────────────────────────────────────────────────
    "agile", "scrum", "kanban", "safe", "lean",
    "jira", "confluence", "linear", "asana", "trello", "notion",
    "git", "github", "gitlab", "bitbucket", "svn",
    "project management", "product management", "technical lead",
    "team lead", "engineering manager",
    # ── Design & UX ───────────────────────────────────────────────────────────
    "figma", "sketch", "adobe xd", "invision", "zeplin",
    "ui/ux", "user research", "wireframing", "prototyping",
    "accessibility", "wcag", "responsive design",
    # ── Blockchain ─────────────────────────────────────────────────────────────
    "blockchain", "solidity", "ethereum", "web3", "smart contracts",
    "defi", "nft", "hyperledger", "polkadot",
    # ── Misc ──────────────────────────────────────────────────────────────────
    "webscraping", "beautifulsoup", "scrapy", "selenium",
    "celery", "redis queue", "bull", "sidekiq",
    "protobuf", "avro", "json schema",
    "regex", "xml", "yaml", "toml",
    "rest", "soap", "graphql", "webhook", "api design",
    "seo", "analytics", "google analytics", "segment", "mixpanel",
    "communication", "leadership", "mentoring", "documentation",
    "technical writing", "code review", "pair programming",
]

SKILL_ALIASES: Dict[str, List[str]] = {
    # Languages
    "javascript":              ["js", "ecmascript", "es6", "es2015", "es2020", "es2022"],
    "typescript":              ["ts"],
    "python":                  ["py", "python3", "python 3"],
    "golang":                  ["go", "go lang", "go language"],
    "c++":                     ["cpp", "c plus plus", "cplusplus"],
    "c#":                      ["csharp", "c sharp", ".net c#", "dotnet c#"],
    "kotlin":                  ["kotlin jvm"],
    "ruby":                    ["rb", "ruby on rails"],
    # Web frameworks
    "react":                   ["reactjs", "react.js", "react js"],
    "vue.js":                  ["vue", "vuejs", "vue 3", "vue3"],
    "angular":                 ["angularjs", "angular 2+", "angular js"],
    "next.js":                 ["nextjs", "next js", "nextjs 13", "nextjs 14"],
    "nuxt.js":                 ["nuxt", "nuxtjs"],
    "node.js":                 ["node", "nodejs", "express", "express.js"],
    "fastapi":                 ["fast api"],
    "django":                  ["django rest framework", "drf", "django 4"],
    "spring boot":             ["spring", "spring framework", "spring mvc", "spring cloud"],
    "tailwind":                ["tailwind css", "tailwindcss"],
    # Databases
    "postgresql":              ["postgres", "psql", "pg", "postgre"],
    "mongodb":                 ["mongo", "mongo db", "mongoose"],
    "elasticsearch":           ["elastic search", "elk", "opensearch", "elastic"],
    "microsoft sql server":    ["mssql", "sql server", "t-sql", "tsql"],
    "redis":                   ["redis cache", "redis queue"],
    "dynamodb":                ["dynamo", "aws dynamodb"],
    "bigquery":                ["google bigquery", "bq"],
    "snowflake":               ["snowflake db"],
    # Cloud
    "amazon web services":     ["aws", "amazon aws"],
    "google cloud platform":   ["gcp", "google cloud"],
    "microsoft azure":         ["azure", "az", "azure cloud"],
    # DevOps
    "kubernetes":              ["k8s", "kube", "k8"],
    "docker":                  ["dockerfile", "docker compose", "docker swarm", "container"],
    "github actions":          ["gh actions", "github ci", "github workflows"],
    "terraform":               ["tf", "iac", "infrastructure as code", "hcl"],
    "ansible":                 ["ansible playbook"],
    "jenkins":                 ["jenkins ci", "jenkins pipeline"],
    "continuous integration":  ["ci", "ci/cd", "cicd"],
    "nginx":                   ["nginx web server"],
    "prometheus":              ["prometheus monitoring"],
    "grafana":                 ["grafana dashboard"],
    "elk stack":               ["elk", "elastic stack", "elasticsearch kibana logstash"],
    # AI/ML
    "machine learning":        ["ml", "supervised learning", "unsupervised learning", "classification"],
    "deep learning":           ["dl", "neural networks", "neural network"],
    "natural language processing": ["nlp", "text processing", "language models", "text mining"],
    "pytorch":                 ["torch", "pytorch lightning"],
    "tensorflow":              ["tf", "keras", "tensorflow keras"],
    "scikit-learn":            ["sklearn", "scikit learn"],
    "computer vision":         ["cv", "image processing", "object detection"],
    "large language models":   ["llm", "llms", "foundation models"],
    "hugging face":            ["huggingface", "transformers library"],
    "langchain":               ["lang chain"],
    # Data
    "pandas":                  ["pd", "pandas dataframe"],
    "apache spark":            ["spark", "pyspark", "databricks spark"],
    "apache kafka":            ["kafka", "kafka streams"],
    "apache airflow":          ["airflow"],
    # Embedded
    "freertos":                ["free rtos", "free-rtos"],
    "embedded linux":          ["buildroot", "yocto"],
    "can bus":                 ["can", "canopen", "j1939"],
    "iso 26262":               ["iso26262", "functional safety automotive"],
    "firmware":                ["bare metal"],
    # Mobile
    "react native":            ["rn", "react-native"],
    "flutter":                 ["flutter sdk", "dart flutter"],
    "swiftui":                 ["swift ui"],
    "jetpack compose":         ["compose", "android compose"],
    # Testing
    "end to end testing":      ["e2e", "e2e testing"],
    "test driven development": ["tdd"],
    "behavior driven development": ["bdd"],
    # Architecture
    "rest api":                ["rest", "restful", "restful api"],
    "graphql":                 ["graph ql"],
    "microservices":           ["microservice", "micro services"],
    "domain driven design":    ["ddd"],
    "event-driven":            ["event driven", "event driven architecture", "eda"],
    # Cloud services
    "ec2":                     ["aws ec2", "amazon ec2"],
    "s3":                      ["aws s3", "amazon s3"],
    "lambda":                  ["aws lambda", "serverless"],
    "sagemaker":               ["aws sagemaker"],
    # Security
    "oauth2":                  ["oauth", "oauth 2.0"],
    "jwt":                     ["json web token", "json web tokens"],
    # Tools
    "git":                     ["version control", "vcs"],
    "github":                  ["github.com"],
    "jira":                    ["atlassian jira"],
    "power bi":                ["powerbi", "ms power bi", "microsoft power bi"],
    "tableau":                 ["tableau desktop", "tableau server"],
    "figma":                   ["figma design"],
    "ci/cd":                   ["cicd", "continuous delivery", "continuous deployment", "continuous integration"],
}

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

# ═══════════════════════════════════════════════════════════════════════════════
# SKILLS REGISTRY CLASS
# ═══════════════════════════════════════════════════════════════════════════════

class SkillsRegistry:
    """
    DB-backed skills registry with in-memory flashtext processor.
    Falls back to MASTER_SKILLS if DB is unavailable.
    """

    def __init__(self):
        self._processor = None
        self._skills: List[str] = []
        self._loaded = False

    def _build_processor(self, skills: List[str]):
        """Build flashtext KeywordProcessor from a skills list."""
        try:
            from flashtext import KeywordProcessor
            kp = KeywordProcessor(case_sensitive=False)
            kp.add_keywords_from_list(skills)
            # Also add all known aliases
            for canonical, aliases in SKILL_ALIASES.items():
                for alias in aliases:
                    kp.add_keyword(alias, canonical)
            self._processor = kp
            self._skills = skills
        except ImportError:
            self._processor = None
            self._skills = skills

    def seed_if_empty(self, db) -> None:
        """Seed the skills table from MASTER_SKILLS if it is empty. Call at startup."""
        try:
            from app.backend.models.db_models import Skill
            count = db.query(Skill).count()
            if count == 0:
                _domain_map = _build_domain_skill_map()
                bulk = []
                for skill in MASTER_SKILLS:
                    aliases = ",".join(SKILL_ALIASES.get(skill, []))
                    domain = _domain_map.get(skill, "general")
                    bulk.append(Skill(name=skill, aliases=aliases, domain=domain,
                                      status="active", source="seed"))
                db.bulk_save_objects(bulk)
                db.commit()
                log.info("Skills registry seeded with %d skills", len(bulk))
        except Exception as e:
            log.warning("Skills seed failed (non-fatal): %s", e)

    def load(self, db=None) -> None:
        """Load active skills from DB into the in-memory processor."""
        skills = []
        if db is not None:
            try:
                from app.backend.models.db_models import Skill
                rows = db.query(Skill).filter(Skill.status == "active").all()
                if rows:
                    for row in rows:
                        skills.append(row.name)
                        if row.aliases:
                            skills.extend(a.strip() for a in row.aliases.split(",") if a.strip())
            except Exception as e:
                log.warning("Skills load from DB failed (using hardcoded): %s", e)
        if not skills:
            skills = list(MASTER_SKILLS)
        self._build_processor(skills)
        self._loaded = True
        log.info("SkillsRegistry loaded %d skills", len(self._skills))

    def rebuild(self, db=None) -> None:
        """Hot-reload skills without restarting the app."""
        self._loaded = False
        self.load(db)

    def get_processor(self):
        """Return the flashtext processor, lazy-loading if needed."""
        if not self._loaded:
            self.load()
        return self._processor

    def get_all_skills(self) -> List[str]:
        if not self._loaded:
            self.load()
        return self._skills


# Module-level singleton
skills_registry = SkillsRegistry()


def _build_domain_skill_map() -> Dict[str, str]:
    """Map each MASTER_SKILL to its primary domain for seeding."""
    skill_to_domain: Dict[str, str] = {}
    for domain, keywords in DOMAIN_KEYWORDS.items():
        for kw in keywords:
            skill_to_domain[kw] = domain
    return skill_to_domain


# ═══════════════════════════════════════════════════════════════════════════════
# COMPONENT 1: JD PARSER
# ═══════════════════════════════════════════════════════════════════════════════

YEARS_PATTERNS = [
    r'(\d+)\+\s*years?',
    r'minimum\s+(?:of\s+)?(\d+)\s*years?',
    r'at\s+least\s+(\d+)\s*years?',
    r'(\d+)\s*[-–]\s*\d+\s*years?',
    r'(\d+)\s+to\s+\d+\s*years?',
    r'(\d+)\s*years?\s+(?:of\s+)?experience',
    r'experience\s+(?:of\s+)?(\d+)\s*years?',
]

_NICE_TO_HAVE_RE = re.compile(
    r'(?:nice[\s\-]to[\s\-]have|preferred|bonus|plus|advantageous|desirable|'
    r'would be (?:a\s+)?(?:great|nice)|not required|optional|good to have)',
    re.IGNORECASE,
)

_TITLE_RE = re.compile(
    r'\b(?:senior|sr\.?|junior|jr\.?|lead|principal|staff|associate|mid[-\s]?level|'
    r'entry[\s\-]level)?\s*[\w/\.]+\s+'
    r'(?:engineer|developer|architect|analyst|scientist|manager|consultant|specialist|'
    r'designer|lead|director|officer|head|vp|president|intern|associate|researcher)',
    re.IGNORECASE,
)


def parse_jd_rules(jd_text: str) -> Dict[str, Any]:
    """Parse a job description purely with Python rules. Returns structured dict."""
    text_lower = jd_text.lower()

    # ── Role title ──────────────────────────────────────────────────────────
    role_title = ""
    lines = [l.strip() for l in jd_text.split("\n") if l.strip()]
    for line in lines[:8]:
        if re.search(r'[@|:/\(\)#\d]{2,}', line):
            continue
        if len(line.split()) > 10:
            continue
        if re.search(r'\b(?:engineer|developer|analyst|architect|manager|scientist|'
                     r'designer|consultant|specialist|lead|officer|director)\b', line, re.I):
            role_title = line.strip()
            break
    if not role_title:
        m = _TITLE_RE.search(jd_text[:500])
        if m:
            role_title = m.group(0).strip()

    # ── Years required ───────────────────────────────────────────────────────
    required_years = 0
    for pat in YEARS_PATTERNS:
        m = re.search(pat, text_lower)
        if m:
            try:
                required_years = int(m.group(1))
                break
            except (ValueError, IndexError):
                pass

    # ── Domain classification ────────────────────────────────────────────────
    domain_hits: Dict[str, int] = {}
    for domain, keywords in DOMAIN_KEYWORDS.items():
        hits = sum(1 for kw in keywords if kw in text_lower)
        if hits:
            domain_hits[domain] = hits
    domain = max(domain_hits, key=domain_hits.get) if domain_hits else "other"

    # ── Seniority ────────────────────────────────────────────────────────────
    title_lower = role_title.lower()
    if any(w in title_lower for w in ("principal", "staff", "distinguished", "fellow")):
        seniority = "lead"
    elif any(w in title_lower for w in ("senior", "sr.", "sr ", "lead", "architect", "head of")):
        seniority = "senior"
    elif any(w in title_lower for w in ("junior", "jr.", "jr ", "associate", "graduate", "entry")):
        seniority = "junior"
    elif any(w in jd_text[:500].lower() for w in ("lead ", "staff ", "principal ")):
        seniority = "lead"
    elif required_years >= 8:
        seniority = "lead"
    elif required_years >= 5:
        seniority = "senior"
    elif required_years >= 2:
        seniority = "mid"
    elif required_years > 0:
        seniority = "junior"
    else:
        seniority = "mid"

    # ── Skill extraction (required vs nice-to-have split) ───────────────────
    nice_start = len(jd_text)
    m_nice = _NICE_TO_HAVE_RE.search(jd_text)
    if m_nice:
        nice_start = m_nice.start()

    required_text   = jd_text[:nice_start]
    nice_have_text  = jd_text[nice_start:]

    required_skills  = _extract_skills_from_text(required_text)
    nice_have_skills = _extract_skills_from_text(nice_have_text)
    # Remove overlap
    nice_have_skills = [s for s in nice_have_skills if s not in required_skills]

    # ── Key responsibilities (first 5 bullet lines starting with verbs) ─────
    resp_lines = []
    for line in lines:
        line_s = line.lstrip("-•*·▸▹►→ ").strip()
        if len(line_s) > 30 and re.match(r'^[A-Z][a-z]', line_s):
            resp_lines.append(line_s)
        if len(resp_lines) >= 6:
            break

    return {
        "role_title":        role_title or "Not specified",
        "domain":            domain,
        "seniority":         seniority,
        "required_skills":   required_skills,
        "required_years":    required_years,
        "nice_to_have_skills": nice_have_skills,
        "key_responsibilities": resp_lines,
    }


def _extract_skills_from_text(text: str) -> List[str]:
    """Extract skills from text using flashtext processor or regex fallback."""
    processor = skills_registry.get_processor()
    if processor:
        found = processor.extract_keywords(text)
        return list(dict.fromkeys(found))   # deduplicate, preserve order
    # Regex fallback
    text_lower = text.lower()
    return [s for s in skills_registry.get_all_skills() if re.search(r'\b' + re.escape(s) + r'\b', text_lower)]


# ═══════════════════════════════════════════════════════════════════════════════
# COMPONENT 2: RESUME PROFILE BUILDER
# ═══════════════════════════════════════════════════════════════════════════════

def parse_resume_rules(parsed_data: Dict[str, Any], gap_analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Build a structured candidate profile from parser output and gap analysis."""
    contact      = parsed_data.get("contact_info", {})
    work_exp     = parsed_data.get("work_experience", [])
    raw_text     = parsed_data.get("raw_text", "")

    # Skills — from parser + full-text scan
    parser_skills = [str(s).strip() for s in parsed_data.get("skills", []) if s]
    scanned_skills = _extract_skills_from_text(raw_text)
    # Merge deduplicating by normalized name
    all_skills = list(dict.fromkeys(parser_skills + scanned_skills))

    total_years = gap_analysis.get("total_years", 0.0)
    current_role    = work_exp[0].get("title", "")    if work_exp else ""
    current_company = work_exp[0].get("company", "")  if work_exp else ""

    career_summary = _build_career_summary(current_role, current_company, total_years)

    return {
        "name":                  contact.get("name", ""),
        "email":                 contact.get("email", ""),
        "phone":                 contact.get("phone", ""),
        "skills_identified":     all_skills,
        "education":             parsed_data.get("education", []),
        "work_experience":       work_exp,
        "career_summary":        career_summary,
        "total_effective_years": total_years,
        "current_role":          current_role,
        "current_company":       current_company,
    }


def _build_career_summary(role: str, company: str, years: float) -> str:
    parts = []
    if role and company:
        parts.append(f"{role} at {company}")
    elif role:
        parts.append(role)
    if years:
        parts.append(f"{years} year{'s' if years != 1 else ''} total experience")
    return " — ".join(parts) if parts else "No career summary available"


# ═══════════════════════════════════════════════════════════════════════════════
# COMPONENT 3: SKILL MATCHING ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

def _normalize_skill(s: str) -> str:
    s = s.strip()
    # Special-case skills that must not be normalized
    if s.lower() in ("c++", "c#"):
        return s.lower()
    s = s.lower()
    s = re.sub(r'[.\-/\\]', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def _expand_skill(skill: str) -> List[str]:
    """Return skill + all its aliases, all normalized."""
    n = _normalize_skill(skill)
    aliases = [_normalize_skill(a) for a in SKILL_ALIASES.get(n, [])]
    # Also check the original unnormalized form
    raw_aliases = SKILL_ALIASES.get(skill.lower(), [])
    aliases += [_normalize_skill(a) for a in raw_aliases]
    return list(dict.fromkeys([n] + aliases))


def match_skills_rules(
    candidate_profile: Dict[str, Any],
    jd_analysis: Dict[str, Any],
    raw_text: str,
) -> Dict[str, Any]:
    required_skills  = jd_analysis.get("required_skills", [])
    nice_have_skills = jd_analysis.get("nice_to_have_skills", [])
    candidate_skills = candidate_profile.get("skills_identified", [])

    # Build candidate skill set (all aliases included)
    cand_normalized: List[str] = []
    for s in candidate_skills:
        cand_normalized.extend(_expand_skill(s))
    cand_set = set(cand_normalized)

    # Also scan raw text with flashtext for skills the parser may have missed
    scanned = _extract_skills_from_text(raw_text)
    for s in scanned:
        cand_set.update(_expand_skill(s))

    matched  = []
    missing  = []

    for req in required_skills:
        req_variants = _expand_skill(req)
        found = False

        # Exact / alias match
        if any(v in cand_set for v in req_variants):
            found = True

        # Substring match: "React Native" in "React" or vice-versa
        if not found:
            req_norm = _normalize_skill(req)
            for c in cand_set:
                if req_norm in c or c in req_norm:
                    found = True
                    break

        # Fuzzy fallback (rapidfuzz, threshold 88)
        if not found:
            try:
                from rapidfuzz import fuzz
                req_norm = _normalize_skill(req)
                for c in list(cand_set)[:200]:  # cap for performance
                    if fuzz.token_sort_ratio(req_norm, c) >= 88:
                        found = True
                        break
            except ImportError:
                pass

        if found:
            matched.append(req)
        else:
            missing.append(req)

    # Adjacent (nice-to-have) matches
    adjacent = []
    for s in nice_have_skills:
        s_variants = _expand_skill(s)
        if any(v in cand_set for v in s_variants):
            adjacent.append(s)

    total_req  = max(len(required_skills), 1)
    skill_score = round(len(matched) / total_req * 100) if required_skills else 50
    skill_score = min(100, skill_score)

    return {
        "matched_skills":   matched,
        "missing_skills":   missing,
        "adjacent_skills":  adjacent,
        "skill_score":      skill_score,
        "required_count":   len(required_skills),
        "matched_count":    len(matched),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# COMPONENT 4: EDUCATION SCORING
# ═══════════════════════════════════════════════════════════════════════════════

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


def score_education_rules(candidate_profile: Dict[str, Any], jd_domain: str) -> int:
    """Return a 0-100 education score."""
    education = candidate_profile.get("education", [])
    if not education:
        return 60  # neutral default — no penalty for missing education data

    best_score = 0
    best_field = ""

    for edu in education:
        degree = str(edu.get("degree", "")).lower()
        field  = str(edu.get("field", "") or edu.get("degree", "")).lower()

        for key, pts in DEGREE_SCORES.items():
            if key in degree:
                if pts > best_score:
                    best_score = pts
                    best_field = field
                break

    if best_score == 0:
        return 60

    # Field relevance multiplier
    relevant_fields = FIELD_RELEVANCE.get(jd_domain, FIELD_RELEVANCE["other"])
    multiplier = 0.70
    for rf in relevant_fields:
        if rf in best_field:
            multiplier = 1.0
            break
        if any(word in best_field for word in rf.split()):
            multiplier = max(multiplier, 0.85)

    return round(best_score * multiplier)


# ═══════════════════════════════════════════════════════════════════════════════
# COMPONENT 5: EXPERIENCE & TIMELINE SCORING
# ═══════════════════════════════════════════════════════════════════════════════

def score_experience_rules(
    candidate_profile: Dict[str, Any],
    jd_analysis: Dict[str, Any],
    gap_analysis: Dict[str, Any],
) -> Dict[str, Any]:
    """Return experience_score, timeline_score, and a text timeline summary."""
    actual_years   = candidate_profile.get("total_effective_years", 0.0)
    required_years = jd_analysis.get("required_years", 0)

    # ── Fallback: if dates couldn't be parsed but work entries exist, estimate ─
    # Avoids showing 0% experience when the resume has jobs but ambiguous dates.
    if actual_years == 0.0:
        work_exp = candidate_profile.get("work_experience", [])
        if work_exp:
            # Conservative: 1.5 years per listed job role, capped at 15 years
            actual_years = float(min(15, len(work_exp) * 1.5))

    # ── Experience score ──────────────────────────────────────────────────────
    if required_years == 0:
        exp_score = min(100, int(actual_years * 10))
    elif actual_years >= required_years:
        exp_score = min(100, 70 + int((actual_years - required_years) * 5))
    else:
        exp_score = int((actual_years / required_years) * 70)
    exp_score = max(0, exp_score)

    # ── Timeline score (gap deductions) ──────────────────────────────────────
    t_score = 85
    employment_gaps = gap_analysis.get("employment_gaps", [])
    for gap in employment_gaps:
        severity = gap.get("severity", "negligible")
        if severity == "minor":     t_score -= 5
        elif severity == "moderate": t_score -= 12
        elif severity == "critical": t_score -= 22
    for _ in gap_analysis.get("short_stints", []):    t_score -= 5
    for _ in gap_analysis.get("overlapping_jobs", []): t_score -= 8
    t_score = max(10, min(100, t_score))

    # ── Timeline summary text ─────────────────────────────────────────────────
    if not employment_gaps:
        timeline_text = "Continuous employment — no significant gaps."
    else:
        n = len(employment_gaps)
        longest = max(g.get("duration_months", 0) for g in employment_gaps)
        severities = [g.get("severity", "") for g in employment_gaps]
        worst = (
            "critical" if "critical" in severities else
            "moderate" if "moderate" in severities else
            "minor"
        )
        timeline_text = (
            f"Career includes {n} gap{'s' if n > 1 else ''}: "
            f"{longest} month{'s' if longest > 1 else ''} longest. {worst.capitalize()} pattern."
        )

    return {
        "exp_score":       exp_score,
        "timeline_score":  t_score,
        "timeline_text":   timeline_text,
        "actual_years":    actual_years,
        "required_years":  required_years,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# COMPONENT 6: DOMAIN & ARCHITECTURE SCORING
# ═══════════════════════════════════════════════════════════════════════════════

ARCHITECTURE_SIGNALS = [
    "designed", "architected", "led design", "technical lead", "system design",
    "microservices", "distributed system", "scalable", "high availability",
    "event-driven", "message queue", "kafka", "rabbitmq", "tech lead",
    "principal engineer", "staff engineer", "engineering manager", "mentored",
    "technical decision", "proof of concept", "rfc", "adr", "design review",
    "led team", "drove", "established", "built from scratch", "greenfield",
]


def domain_architecture_rules(
    raw_text: str,
    jd_domain: str,
    current_role: Optional[str],
) -> Dict[str, Any]:
    """Return domain_score and architecture_score."""
    text_lower = raw_text.lower()

    # ── Domain fit score ──────────────────────────────────────────────────────
    domain_keywords = DOMAIN_KEYWORDS.get(jd_domain, [])
    hits = sum(1 for kw in domain_keywords if kw in text_lower)

    if   hits >= 8: domain_score = 90
    elif hits >= 5: domain_score = 75
    elif hits >= 3: domain_score = 60
    elif hits >= 1: domain_score = 45
    else:           domain_score = 30

    # Bonus/penalty from current role title
    if current_role:
        role_lower = current_role.lower()
        if any(kw in role_lower for kw in domain_keywords[:5]):
            domain_score = min(100, domain_score + 10)
        elif not any(w in role_lower for w in ("engineer", "developer", "analyst", "architect")):
            domain_score = max(0, domain_score - 5)

    # ── Architecture score ────────────────────────────────────────────────────
    arch_hits = sum(1 for sig in ARCHITECTURE_SIGNALS if sig in text_lower)
    arch_score = min(100, 40 + arch_hits * 8)

    return {
        "domain_score":     domain_score,
        "arch_score":       arch_score,
        "domain_hits":      hits,
        "arch_hits":        arch_hits,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# COMPONENT 7: FIT SCORE & RISK SIGNALS
# ═══════════════════════════════════════════════════════════════════════════════

_DEFAULT_WEIGHTS = {
    "skills":       0.30,
    "experience":   0.20,
    "architecture": 0.15,
    "education":    0.10,
    "timeline":     0.10,
    "domain":       0.10,
    "risk":         0.15,
}


def compute_fit_score(scores: Dict[str, Any], scoring_weights: Optional[Dict] = None) -> Dict[str, Any]:
    """Compute weighted fit score, risk signals, and recommendation."""
    w = {**_DEFAULT_WEIGHTS, **(scoring_weights or {})}

    skill_score    = scores.get("skill_score",    50)
    exp_score      = scores.get("exp_score",       50)
    arch_score     = scores.get("arch_score",      50)
    edu_score      = scores.get("edu_score",       60)
    timeline_score = scores.get("timeline_score",  85)
    domain_score   = scores.get("domain_score",    60)
    actual_years   = scores.get("actual_years",    0)
    required_years = scores.get("required_years",  0)
    matched_skills = scores.get("matched_skills",  [])
    missing_skills = scores.get("missing_skills",  [])
    required_count = scores.get("required_count",  0)
    employment_gaps = scores.get("employment_gaps", [])
    short_stints    = scores.get("short_stints",   [])

    # ── Risk signals (deterministic Python — not LLM) ─────────────────────────
    risk_signals = []

    has_critical_gap = any(g.get("severity") == "critical" for g in employment_gaps)
    if has_critical_gap:
        risk_signals.append({"type": "gap",           "severity": "high",
                              "description": "Critical employment gap detected (12+ months)"})

    skill_miss_pct = (len(missing_skills) / max(required_count, 1)) * 100
    if skill_miss_pct >= 50:
        risk_signals.append({"type": "skill_gap",     "severity": "high",
                              "description": f"Missing {len(missing_skills)}/{required_count} required skills"})
    elif skill_miss_pct >= 30:
        risk_signals.append({"type": "skill_gap",     "severity": "medium",
                              "description": f"Missing {len(missing_skills)}/{required_count} required skills"})

    if domain_score < 40:
        risk_signals.append({"type": "domain_mismatch", "severity": "medium",
                              "description": "Candidate domain does not closely match role requirements"})

    if len(short_stints) >= 3:
        risk_signals.append({"type": "stability",     "severity": "medium",
                              "description": f"{len(short_stints)} short stints (<6 months) detected"})
    elif len(short_stints) >= 2:
        risk_signals.append({"type": "stability",     "severity": "low",
                              "description": f"{len(short_stints)} short stints detected"})

    if required_years > 0 and actual_years > required_years * 2:
        risk_signals.append({"type": "overqualified",  "severity": "low",
                              "description": f"Candidate has {actual_years}y experience vs {required_years}y required"})

    # ── Risk penalty ──────────────────────────────────────────────────────────
    risk_penalty = sum(
        {"high": 20, "medium": 10, "low": 4}.get(r.get("severity", "low"), 0)
        for r in risk_signals
    )

    # ── Fit score ──────────────────────────────────────────────────────────────
    fit_score = round(
        skill_score    * w["skills"]       +
        exp_score      * w["experience"]   +
        arch_score     * w["architecture"] +
        edu_score      * w["education"]    +
        timeline_score * w["timeline"]     +
        domain_score   * w["domain"]       -
        risk_penalty   * w["risk"]
    )
    fit_score = max(0, min(100, fit_score))

    # ── Recommendation ────────────────────────────────────────────────────────
    if fit_score >= 72:
        recommendation = "Shortlist"
        risk_level = "Low"
    elif fit_score >= 45:
        recommendation = "Consider"
        risk_level = "Medium" if risk_signals else "Low"
    else:
        recommendation = "Reject"
        risk_level = "High" if any(r["severity"] == "high" for r in risk_signals) else "Medium"

    return {
        "fit_score":            fit_score,
        "final_recommendation": recommendation,
        "risk_level":           risk_level,
        "risk_signals":         risk_signals,
        "risk_penalty":         risk_penalty,
        "score_breakdown": {
            "skill_match":      skill_score,
            "experience_match": exp_score,
            "stability":        timeline_score,
            "education":        edu_score,
            "architecture":     arch_score,
            "domain_fit":       domain_score,
            "timeline":         timeline_score,
            "risk_penalty":     risk_penalty,
        },
    }


def _assess_quality(candidate_profile: Dict[str, Any]) -> str:
    """Assess how complete the parsed resume data is."""
    skills_count = len(candidate_profile.get("skills_identified", []))
    exp_years    = candidate_profile.get("total_effective_years", 0)
    has_edu      = bool(candidate_profile.get("education"))
    if skills_count == 0 and exp_years == 0:
        return "low"
    if skills_count < 3 or (exp_years == 0 and not has_edu):
        return "medium"
    return "high"


# ═══════════════════════════════════════════════════════════════════════════════
# COMPONENT 8: LLM NARRATIVE (single call)
# ═══════════════════════════════════════════════════════════════════════════════

async def explain_with_llm(context: Dict[str, Any]) -> Dict[str, Any]:
    """Single LLM call to generate narrative. Raises on failure for caller to handle."""
    llm = _get_llm()
    if llm is None:
        raise RuntimeError("LLM not available")

    jd       = context.get("jd_analysis", {})
    profile  = context.get("candidate_profile", {})
    scores   = context.get("scores", {})
    skill_a  = context.get("skill_analysis", {})

    prompt = f"""You are a recruitment analyst. Output ONLY valid JSON, no markdown, no explanation.

ROLE: {jd.get("role_title")} | domain={jd.get("domain")} | seniority={jd.get("seniority")}
CANDIDATE: {profile.get("name") or "Unknown"} | {profile.get("total_effective_years", 0)}y exp | current: {profile.get("current_role") or "N/A"} at {profile.get("current_company") or "N/A"}
SCORES: skill={scores.get("skill_score",0)}/100 exp={scores.get("exp_score",0)}/100 edu={scores.get("edu_score",0)}/100 timeline={scores.get("timeline_score",0)}/100 fit={scores.get("fit_score",0)}/100
RECOMMENDATION: {scores.get("final_recommendation","Pending")}
MATCHED SKILLS: {", ".join(skill_a.get("matched_skills", [])[:15])}
MISSING SKILLS: {", ".join(skill_a.get("missing_skills", [])[:10])}
CAREER SUMMARY: {profile.get("career_summary","")}

OUTPUT JSON SCHEMA (return exactly this structure):
{{"strengths":[],"weaknesses":[],"recommendation_rationale":"","explainability":{{"skill_rationale":"","experience_rationale":"","overall_rationale":""}},"interview_questions":{{"technical_questions":[],"behavioral_questions":[],"culture_fit_questions":[]}}}}

Rules: 3-5 strengths (evidence-based), 2-4 constructive weaknesses, 2-sentence rationale, 5 technical questions targeting missing skills, 3 STAR behavioral questions, 2 culture/motivation questions."""

    from langchain_core.messages import HumanMessage
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    raw = response.content if hasattr(response, "content") else str(response)

    # Parse JSON
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        if m:
            data = json.loads(m.group(0))
        else:
            raise ValueError("LLM returned non-JSON response")

    return {
        "strengths":              _ensure_str_list(data.get("strengths", [])),
        "weaknesses":             _ensure_str_list(data.get("weaknesses", [])),
        "recommendation_rationale": str(data.get("recommendation_rationale", "")),
        "explainability":         data.get("explainability", {}),
        "interview_questions": {
            "technical_questions":   _ensure_str_list(data.get("interview_questions", {}).get("technical_questions", [])),
            "behavioral_questions":  _ensure_str_list(data.get("interview_questions", {}).get("behavioral_questions", [])),
            "culture_fit_questions": _ensure_str_list(data.get("interview_questions", {}).get("culture_fit_questions", [])),
        },
    }


def _ensure_str_list(v) -> List[str]:
    if not isinstance(v, list):
        return []
    return [item if isinstance(item, str) else str(item) for item in v]


def _build_fallback_narrative(python_result: Dict[str, Any], skill_analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Deterministic narrative when LLM is unavailable or timed out."""
    matched  = skill_analysis.get("matched_skills", [])
    missing  = skill_analysis.get("missing_skills", [])
    score    = python_result.get("fit_score", 0)
    req      = skill_analysis.get("required_count", 0)
    actual_y = python_result.get("score_breakdown", {}).get("experience_match", 0)
    req_y    = python_result.get("_required_years", 0)

    strengths = []
    if matched:
        strengths.append(f"Matches {len(matched)} required skills: {', '.join(matched[:4])}")
    if actual_y >= 70:
        strengths.append("Strong experience background")
    if not strengths:
        strengths.append("Profile submitted for review")

    weaknesses = []
    if missing:
        weaknesses.append(f"Missing key skills: {', '.join(missing[:4])}")
    if not weaknesses:
        weaknesses.append("Manual review recommended for full assessment")

    tech_q = [f"Can you describe your experience with {s}?" for s in missing[:5]] or \
             ["Describe a complex technical challenge you solved."]
    behavioral_q = [
        "Tell me about a time you led a difficult project. What was the outcome?",
        "Describe a situation where you had to learn a new technology quickly.",
        "Give an example of a time you resolved a conflict in a team.",
    ]
    culture_q = [
        "What motivates you to apply for this role?",
        "How do you keep up with new developments in your field?",
    ]

    return {
        "strengths":  strengths,
        "weaknesses": weaknesses,
        "recommendation_rationale": (
            f"Candidate scored {score}/100. {len(matched)}/{req} required skills matched. "
            f"Automated narrative unavailable — manual review recommended."
        ),
        "explainability": {
            "skill_rationale":      f"Matched {len(matched)} of {req} required skills.",
            "experience_rationale": "Based on parsed employment timeline.",
            "overall_rationale":    f"Overall fit score: {score}/100.",
        },
        "interview_questions": {
            "technical_questions":   tech_q,
            "behavioral_questions":  behavioral_q,
            "culture_fit_questions": culture_q,
        },
    }


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN ORCHESTRATORS
# ═══════════════════════════════════════════════════════════════════════════════

def _run_python_phase(
    resume_text: str,
    job_description: str,
    parsed_data: Dict[str, Any],
    gap_analysis: Dict[str, Any],
    scoring_weights: Optional[Dict],
    jd_analysis: Optional[Dict],
) -> Dict[str, Any]:
    """Execute all deterministic Python components. Returns a rich result dict."""
    jd       = jd_analysis or parse_jd_rules(job_description)
    profile  = parse_resume_rules(parsed_data, gap_analysis)
    skill_a  = match_skills_rules(profile, jd, resume_text)
    edu_s    = score_education_rules(profile, jd["domain"])
    exp_r    = score_experience_rules(profile, jd, gap_analysis)
    dom_r    = domain_architecture_rules(resume_text, jd["domain"], profile.get("current_role"))

    all_scores = {
        "skill_score":    skill_a["skill_score"],
        "exp_score":      exp_r["exp_score"],
        "arch_score":     dom_r["arch_score"],
        "edu_score":      edu_s,
        "timeline_score": exp_r["timeline_score"],
        "domain_score":   dom_r["domain_score"],
        "actual_years":   exp_r["actual_years"],
        "required_years": exp_r["required_years"],
        "matched_skills": skill_a["matched_skills"],
        "missing_skills": skill_a["missing_skills"],
        "required_count": skill_a["required_count"],
        "employment_gaps": gap_analysis.get("employment_gaps", []),
        "short_stints":    gap_analysis.get("short_stints", []),
        "fit_score": 0,
    }

    fit_r = compute_fit_score(all_scores, scoring_weights)
    all_scores["fit_score"] = fit_r["fit_score"]
    all_scores["final_recommendation"] = fit_r["final_recommendation"]

    quality = _assess_quality(profile)

    return {
        "jd_analysis":         jd,
        "candidate_profile":   profile,
        "skill_analysis":      skill_a,
        "edu_timeline_analysis": {
            "education_score":  edu_s,
            "timeline_text":    exp_r["timeline_text"],
            "employment_gaps":  gap_analysis.get("employment_gaps", []),
            "overlapping_jobs": gap_analysis.get("overlapping_jobs", []),
            "short_stints":     gap_analysis.get("short_stints", []),
        },
        # Top-level fields for AnalysisResponse schema
        "fit_score":            fit_r["fit_score"],
        "job_role":             jd["role_title"],
        "final_recommendation": fit_r["final_recommendation"],
        "risk_level":           fit_r["risk_level"],
        "risk_signals":         fit_r["risk_signals"],
        "score_breakdown":      fit_r["score_breakdown"],
        "matched_skills":       skill_a["matched_skills"],
        "missing_skills":       skill_a["missing_skills"],
        "adjacent_skills":      skill_a["adjacent_skills"],
        "required_skills_count": skill_a["required_count"],
        "work_experience":      parsed_data.get("work_experience", []),
        "contact_info":         parsed_data.get("contact_info", {}),
        "employment_gaps":      gap_analysis.get("employment_gaps", []),
        "education_analysis":   None,
        "analysis_quality":     quality,
        "narrative_pending":    False,
        "pipeline_errors":      [],
        # Internal — used by fallback
        "_required_years":      exp_r["required_years"],
        "_scores":              all_scores,
    }


def _merge_llm_into_result(python_result: Dict[str, Any], llm_result: Dict[str, Any]) -> Dict[str, Any]:
    """Merge LLM narrative into the Python result dict."""
    merged = dict(python_result)
    merged.update({
        "strengths":              llm_result.get("strengths", []),
        "weaknesses":             llm_result.get("weaknesses", []),
        "recommendation_rationale": llm_result.get("recommendation_rationale", ""),
        "explainability":         llm_result.get("explainability", {}),
        "interview_questions":    llm_result.get("interview_questions"),
        "education_analysis":     llm_result.get("explainability", {}).get("skill_rationale"),
    })
    # Remove internal keys
    merged.pop("_required_years", None)
    merged.pop("_scores", None)
    return merged


async def run_hybrid_pipeline(
    resume_text: str,
    job_description: str,
    parsed_data: Dict[str, Any],
    gap_analysis: Dict[str, Any],
    scoring_weights: Optional[Dict] = None,
    jd_analysis: Optional[Dict] = None,
) -> Dict[str, Any]:
    """
    Non-streaming version. Returns full result dict.
    Always returns — LLM timeout produces fallback narrative, never an exception.
    """
    python_result = _run_python_phase(
        resume_text, job_description, parsed_data, gap_analysis, scoring_weights, jd_analysis
    )

    llm_context = {
        "jd_analysis":       python_result["jd_analysis"],
        "candidate_profile": python_result["candidate_profile"],
        "skill_analysis":    python_result["skill_analysis"],
        "scores": {
            **python_result["_scores"],
            "fit_score":            python_result["fit_score"],
            "final_recommendation": python_result["final_recommendation"],
        },
    }

    # Timeout: 150s to survive gemma4:26b cold-start on CPU (first load ~2 min).
    # Subsequent requests are served from the hot model and typically finish in 30-60s.
    _LLM_TIMEOUT = float(os.getenv("LLM_NARRATIVE_TIMEOUT", "150"))

    try:
        async with _get_semaphore():
            llm_result = await asyncio.wait_for(explain_with_llm(llm_context), timeout=_LLM_TIMEOUT)
        log.info("LLM narrative succeeded for fit_score=%s", python_result.get("fit_score"))
    except asyncio.TimeoutError:
        log.warning(
            "LLM explain timed out after %.0fs — using fallback narrative. "
            "Model may still be loading. Consider increasing LLM_NARRATIVE_TIMEOUT env var.",
            _LLM_TIMEOUT,
        )
        llm_result = _build_fallback_narrative(python_result, python_result["skill_analysis"])
        python_result["narrative_pending"] = True
    except Exception as e:
        log.warning(
            "LLM explain failed (%s: %s) — using fallback narrative",
            type(e).__name__, str(e)[:200],
        )
        llm_result = _build_fallback_narrative(python_result, python_result["skill_analysis"])
        python_result["narrative_pending"] = True

    return _merge_llm_into_result(python_result, llm_result)


async def astream_hybrid_pipeline(
    resume_text: str,
    job_description: str,
    parsed_data: Dict[str, Any],
    gap_analysis: Dict[str, Any],
    scoring_weights: Optional[Dict] = None,
    jd_analysis: Optional[Dict] = None,
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    SSE streaming version.

    Yields:
      {"stage": "parsing",  "result": {all Python scores}}  — within 2s
      {"stage": "scoring",  "result": {LLM narrative}}       — after ~40s
      {"stage": "complete", "result": {full merged result}}
    """
    # Phase 1 — Python (instant)
    python_result = _run_python_phase(
        resume_text, job_description, parsed_data, gap_analysis, scoring_weights, jd_analysis
    )
    # Strip internal keys for the SSE payload
    parsing_payload = {k: v for k, v in python_result.items()
                       if not k.startswith("_")}
    yield {"stage": "parsing", "result": parsing_payload}

    llm_context = {
        "jd_analysis":       python_result["jd_analysis"],
        "candidate_profile": python_result["candidate_profile"],
        "skill_analysis":    python_result["skill_analysis"],
        "scores": {
            **python_result["_scores"],
            "fit_score":            python_result["fit_score"],
            "final_recommendation": python_result["final_recommendation"],
        },
    }

    # Phase 2 — LLM with heartbeat pings to keep Cloudflare/Nginx alive
    llm_queue: asyncio.Queue = asyncio.Queue()

    _LLM_TIMEOUT_STREAM = float(os.getenv("LLM_NARRATIVE_TIMEOUT", "150"))

    async def _llm_task():
        try:
            async with _get_semaphore():
                result = await asyncio.wait_for(explain_with_llm(llm_context), timeout=_LLM_TIMEOUT_STREAM)
            log.info("LLM stream narrative succeeded")
            await llm_queue.put(("ok", result))
        except asyncio.TimeoutError:
            log.warning(
                "LLM stream timed out after %.0fs — using fallback. "
                "Increase LLM_NARRATIVE_TIMEOUT if model is still loading.",
                _LLM_TIMEOUT_STREAM,
            )
            fallback = _build_fallback_narrative(python_result, python_result["skill_analysis"])
            python_result["narrative_pending"] = True
            await llm_queue.put(("fallback", fallback))
        except Exception as e:
            log.warning(
                "LLM stream failed (%s: %s) — using fallback",
                type(e).__name__, str(e)[:200],
            )
            fallback = _build_fallback_narrative(python_result, python_result["skill_analysis"])
            python_result["narrative_pending"] = True
            await llm_queue.put(("fallback", fallback))

    task = asyncio.create_task(_llm_task())
    llm_result = None
    try:
        while True:
            try:
                status, llm_result = await asyncio.wait_for(llm_queue.get(), timeout=5.0)
                break
            except asyncio.TimeoutError:
                yield ": ping\n\n"  # SSE comment — keeps connection alive during LLM wait
    finally:
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, Exception):
            pass

    yield {"stage": "scoring", "result": llm_result or {}}

    final = _merge_llm_into_result(python_result, llm_result or {})
    yield {"stage": "complete", "result": final}

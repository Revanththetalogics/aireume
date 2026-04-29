"""
Shared skill matcher — single source of truth for skill matching.
"""

import logging
import re
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# O*NET OCCUPATION-AWARE VALIDATION (OPTIONAL)
# ═══════════════════════════════════════════════════════════════════════════════

_onet_validator = None


def _get_onet_validator():
    """Lazy singleton for ONETValidator."""
    global _onet_validator
    if _onet_validator is None:
        try:
            from app.backend.services.onet import ONETValidator
            _onet_validator = ONETValidator()
        except Exception as e:
            logger.warning("ONETValidator init failed: %s", e)
            _onet_validator = None
    return _onet_validator


def match_skills_with_onet(
    candidate_skills, jd_skills, jd_text="", jd_nice_to_have=None, job_title=None,
    structured_skills=None, text_scanned_skills=None
):
    """Enhanced skill matching with O*NET occupation context.

    Falls back to standard :func:`match_skills` if O*NET data is unavailable
    or no *job_title* is provided.

    .. deprecated:: jd_text
        Kept for backward compatibility (agent_pipeline.py). Ignored internally.
        Use *text_scanned_skills* instead.
    """
    result = match_skills(candidate_skills, jd_skills, jd_nice_to_have,
                          structured_skills=structured_skills,
                          text_scanned_skills=text_scanned_skills)

    validator = _get_onet_validator()
    if validator is not None and validator.available and job_title:
        try:
            onet_result = validator.validate_skills_batch(
                [m for m in result.get("matched_skills", [])],
                job_title,
            )
            result["onet_validation"] = onet_result

            # Filter: remove high-collision skills that O*NET says are NOT valid for this occupation
            if onet_result.get("skill_validations"):
                invalid_high_collision = set()
                for skill_name, validation in onet_result["skill_validations"].items():
                    norm = _normalize_skill(skill_name)
                    if norm in HIGH_COLLISION_SKILLS and not validation.get("valid", True):
                        invalid_high_collision.add(skill_name)
                if invalid_high_collision:
                    result["matched_skills"] = [s for s in result["matched_skills"]
                                                if s not in invalid_high_collision]
                    result["onet_filtered"] = list(invalid_high_collision)
        except Exception as e:
            logger.warning("O*NET validation failed (non-fatal): %s", e)

    return result

# ═══════════════════════════════════════════════════════════════════════════════
# MASTER SKILLS LIST
# ═══════════════════════════════════════════════════════════════════════════════

MASTER_SKILLS: List[str] = [
    # ── Programming languages ──────────────────────────────────────────────────
    "python", "java", "javascript", "typescript", "c++", "c#", "c", "golang", "go",
    "rust", "scala", "kotlin", "swift", "ruby", "php", "r", "matlab", "perl",
    "haskell", "erlang", "elixir", "clojure", "f#", "lua", "dart", "zig", "ada",
    "assembly", "bash", "powershell", "groovy", "cobol", "fortran", "vba",
    "nim", "crystal", "julia", "ocaml", "reasonml", "purescript", "elm",
    "solidity", "vyper", "move", "cairo",
    # ── Web frameworks ─────────────────────────────────────────────────────────
    "react", "vue.js", "vue", "angular", "next.js", "nuxt.js", "svelte", "astro",
    "remix", "gatsby", "ember.js", "backbone.js", "jquery", "bootstrap", "tailwind",
    "material ui", "chakra ui", "ant design", "storybook",
    "node.js", "express.js", "fastapi", "django", "flask", "tornado", "aiohttp",
    "starlette", "litestar", "spring boot", "spring", "quarkus", "micronaut",
    "nestjs", "koa", "hapi", "feathers", "strapi", "rails", "sinatra", "laravel",
    "symfony", "codeigniter", "gin", "fiber", "echo", "chi", "actix", "axum", "rocket",
    "htmx", "alpine.js", "lit", "stencil", "solid.js", "qwik", "preact",
    "blazor", "asp.net", "asp.net core", "dotnet", ".net", "wpf", "winforms",
    # ── Databases ──────────────────────────────────────────────────────────────
    "postgresql", "mysql", "sqlite", "mariadb", "oracle", "microsoft sql server",
    "mongodb", "redis", "elasticsearch", "cassandra", "dynamodb", "couchdb",
    "neo4j", "influxdb", "timescaledb", "cockroachdb", "planetscale",
    "snowflake", "bigquery", "redshift", "databricks", "clickhouse",
    "supabase", "firebase", "firestore", "realm", "fauna", "deno kv",
    "sqlalchemy", "hibernate", "prisma", "typeorm", "sequelize", "drizzle",
    "mongoose", "redis om", "entity framework", "dapper",
    "db2", "informix", "sybase", "teradata", "greenplum",
    # ── Cloud platforms ────────────────────────────────────────────────────────
    "amazon web services", "aws", "google cloud platform", "gcp", "microsoft azure",
    "azure", "digital ocean", "linode", "vultr", "hetzner", "oracle cloud",
    "ibm cloud", "alibaba cloud", "cloudflare", "vercel", "netlify", "heroku",
    "fly.io", "render", "railway", "supabase", "firebase", "appwrite", "pocketbase",
    "cloudfoundry", "openshift", "rancher", "nomad", "hashicorp",
    # ── AWS services ───────────────────────────────────────────────────────────
    "ec2", "s3", "lambda", "ecs", "eks", "rds", "aurora", "elasticache",
    "api gateway", "cloudfront", "route53", "iam", "cloudwatch", "sns", "sqs",
    "kinesis", "glue", "athena", "emr", "sagemaker", "bedrock",
    "dynamodb", "step functions", "eventbridge", "sqs", "ses", "sns",
    "vpc", "alb", "nlb", "autoscaling", "cloudformation", "elastic beanstalk",
    # ── DevOps & infrastructure ────────────────────────────────────────────────
    "docker", "kubernetes", "helm", "terraform", "ansible", "puppet", "chef",
    "vagrant", "packer", "jenkins", "github actions", "gitlab ci", "circleci",
    "travis ci", "bitbucket pipelines", "argo cd", "flux", "spinnaker", "tekton",
    "prometheus", "grafana", "datadog", "new relic", "dynatrace", "splunk",
    "elk stack", "loki", "jaeger", "zipkin", "opentelemetry",
    "nginx", "apache", "traefik", "envoy", "istio", "linkerd", "consul",
    "vault", "linux", "unix", "ubuntu", "centos", "rhel", "debian",
    "ci/cd", "devops", "sre", "infrastructure as code", "gitops",
    "pulumi", "crossplane", "backstage", "kustomize", "skaffold", "tilt",
    "bazel", "buck", "nix", "guix", "chocolatey", "homebrew",
    # ── AI / ML ────────────────────────────────────────────────────────────────
    "machine learning", "deep learning", "neural networks", "natural language processing",
    "nlp", "computer vision", "reinforcement learning", "generative ai",
    "large language models", "llm", "transformers", "bert", "gpt",
    "pytorch", "tensorflow", "keras", "jax", "mxnet", "caffe",
    "scikit-learn", "xgboost", "lightgbm", "catboost", "statsmodels",
    "hugging face", "langchain", "llamaindex", "ollama", "openai",
    "anthropic", "cohere", "vector database", "rag", "fine-tuning",
    "mlflow", "wandb", "optuna", "ray", "kubeflow", "vertex ai",
    "opencv", "pillow", "albumentations", "detectron", "yolo",
    "stable diffusion", "midjourney", "comfyui", "diffusers",
    "spacy", "nltk", "gensim", "fasttext", "word2vec", "doc2vec",
    "tensorflow lite", "onnx", "tensorrt", "openvino", "coreml",
    "automl", "feature store", "feast", "tecton",
    # ── Data science & analytics ───────────────────────────────────────────────
    "pandas", "numpy", "scipy", "matplotlib", "seaborn", "plotly", "bokeh",
    "jupyter", "jupyter notebook", "colab", "dask", "polars", "vaex",
    "apache spark", "pyspark", "hadoop", "hive", "pig", "flink",
    "apache kafka", "rabbitmq", "celery", "airflow", "prefect", "dagster",
    "dbt", "fivetran", "airbyte", "stitch", "etl", "data pipeline",
    "tableau", "power bi", "looker", "metabase", "superset", "grafana",
    "excel", "google sheets", "data analysis", "statistics", "a/b testing",
    "data warehousing", "data lake", "data mesh", "data governance",
    "feature engineering", "data mining", "predictive modeling", "time series analysis",
    "sas", "spss", "minitab", "stata",
    # ── Embedded / systems ─────────────────────────────────────────────────────
    "embedded", "rtos", "freertos", "zephyr", "vxworks", "qnx", "embedded linux",
    "microcontroller", "fpga", "arm", "arm cortex", "avr", "pic",
    "uart", "spi", "i2c", "can bus", "modbus", "ethernet",
    "tcp/ip", "udp", "mqtt", "coap", "ble", "zigbee", "lorawan",
    "device driver", "bsp", "bootloader", "firmware", "real-time",
    "ipc", "multithreading", "multiprocessing", "posix",
    "cmake", "makefile", "openocd", "jtag", "gdb",
    "iso 26262", "misra", "do-178", "sil4", "functional safety",
    "plc", "ladder logic", "scada", "industrial automation", "hart",
    # ── Mobile ─────────────────────────────────────────────────────────────────
    "ios", "android", "react native", "flutter", "xamarin", "ionic", "capacitor",
    "swift", "swiftui", "objective-c", "kotlin", "jetpack compose",
    "xcode", "android studio", "expo", "firebase", "appcenter",
    "cordova", "phonegap", "titanium", "unity mobile",
    # ── Testing ────────────────────────────────────────────────────────────────
    "unit testing", "integration testing", "e2e testing", "tdd", "bdd",
    "pytest", "unittest", "jest", "vitest", "mocha", "jasmine", "cypress",
    "playwright", "selenium", "appium", "postman", "insomnia",
    "k6", "locust", "jmeter", "gatling",
    "sonarqube", "codecov", "coveralls", "code review",
    "mutation testing", "property based testing", "fuzz testing",
    # ── Architecture & design ──────────────────────────────────────────────────
    "microservices", "monolith", "event-driven", "cqrs", "event sourcing",
    "domain driven design", "ddd", "hexagonal architecture", "clean architecture",
    "rest api", "graphql", "grpc", "websocket", "mqtt", "openapi", "swagger",
    "system design", "distributed systems", "high availability", "scalability",
    "design patterns", "solid", "ooad", "uml", "soa",
    "api gateway", "service mesh", "sidecar", "circuit breaker", "bulkhead",
    "saga pattern", "outbox pattern", "inbox pattern", "strangler fig",
    "twelve-factor app", "cap theorem", "acid", "base",
    # ── Security ───────────────────────────────────────────────────────────────
    "oauth2", "jwt", "saml", "ldap", "iam", "rbac",
    "tls", "ssl", "cryptography", "penetration testing", "owasp",
    "soc2", "gdpr", "hipaa", "pci dss",
    "zero trust", "siem", "soar", "edr", "xdr", "mdr",
    "vulnerability scanning", "threat modeling", "bug bounty",
    "pkcs", "x.509", "aes", "rsa", "ecc", "sha", "md5",
    # ── Project management ─────────────────────────────────────────────────────
    "agile", "scrum", "kanban", "safe", "lean",
    "jira", "confluence", "linear", "asana", "trello", "notion",
    "git", "github", "gitlab", "bitbucket", "svn",
    "project management", "product management", "technical lead",
    "team lead", "engineering manager",
    "program management", "portfolio management", "release management",
    "change management", "itil", "cobit", "ppm",
    # ── Design & UX ───────────────────────────────────────────────────────────
    "figma", "sketch", "adobe xd", "invision", "zeplin",
    "ui/ux", "user research", "wireframing", "prototyping",
    "accessibility", "wcag", "responsive design",
    "design system", "component library", "storybook",
    "adobe creative suite", "photoshop", "illustrator", "after effects",
    "blender", "cinema 4d", "maya", "3ds max",
    "motion design", "interaction design", "information architecture",
    "usability testing", "heuristic evaluation", "card sorting",
    # ── Blockchain ─────────────────────────────────────────────────────────────
    "blockchain", "solidity", "ethereum", "web3", "smart contracts",
    "defi", "nft", "hyperledger", "polkadot",
    "bitcoin", "cosmos", "tendermint", "avalanche", "solana", "cardano",
    "chainlink", "the graph", "ipfs", "filecoin",
    "zero knowledge", "zk-snarks", "zk-starks", "rollups", "layer 2",
    # ── Gaming / AR / VR ───────────────────────────────────────────────────────
    "unity", "unreal engine", "godot", "cryengine", "game maker",
    "cocos2d", "phaser", "babylon.js", "three.js", "webgl", "webgpu",
    "openxr", "arkit", "arcore", "vuforia", "metaverse",
    "shader programming", "hlsl", "glsl", "compute shaders",
    # ── Networking ─────────────────────────────────────────────────────────────
    "networking", "tcp/ip", "udp", "http", "http/2", "http/3", "quic",
    "dns", "dhcp", "vpn", "ipsec", "wireguard", "openvpn",
    "load balancing", "cdn", "reverse proxy", "waf", "ddos protection",
    "bgp", "ospf", "mpls", "sdn", "nfv", "vlan", "vxlan",
    "firewall", "ids", "ips", "network security", "packet analysis",
    # ── Operating systems ──────────────────────────────────────────────────────
    "windows", "windows server", "linux", "macos", "unix",
    "freebsd", "openbsd", "netbsd", "solaris", "aix",
    "embedded linux", "android os", "ios", "chrome os",
    "active directory", "group policy", "ldap", "kerberos",
    # ── CRM / ERP / Business ───────────────────────────────────────────────────
    "salesforce", "hubspot", "zoho", "pipedrive", "freshsales",
    "sap", "oracle erp", "dynamics 365", "netsuite", "workday",
    "servicenow", "jira service management", "freshdesk", "zendesk",
    "sharepoint", "power platform", "power apps", "power automate",
    "outsystems", "mendix", "appian", " Salesforce apex", "visualforce",
    "business analysis", "business intelligence", "data modeling",
    "process modeling", "bpmn", "uml", "enterprise architecture",
    "togaf", "archimate", "zachman",
    # ── Soft skills & non-technical ────────────────────────────────────────────
    "communication", "leadership", "mentoring", "documentation",
    "technical writing", "code review", "pair programming",
    "problem solving", "critical thinking", "analytical thinking",
    "creativity", "innovation", "adaptability", "flexibility",
    "time management", "prioritization", "organization",
    "collaboration", "teamwork", "cross-functional collaboration",
    "stakeholder management", "client management", "customer success",
    "conflict resolution", "negotiation", "persuasion",
    "public speaking", "presentation skills", "storytelling",
    "emotional intelligence", "empathy", "cultural awareness",
    "decision making", "strategic thinking", "vision",
    "coaching", "feedback", "performance management",
    "hiring", "recruiting", "talent acquisition", "onboarding",
    "budget management", "financial planning", "roi analysis",
    "vendor management", "contract negotiation", "procurement",
    "compliance", "risk management", "business continuity",
    "change management", "organizational development",
    "quality assurance", "process improvement", "six sigma", "lean manufacturing",
    "root cause analysis", "fishbone diagram", "5 whys",
    "technical support", "customer support", "help desk", "it support",
    "training", "knowledge management", "wiki", "confluence",
    "event planning", "workshop facilitation", "sprint planning",
    "daily standups", "retrospectives", "demos", "backlog grooming",
    "user stories", "acceptance criteria", "definition of done",
    "market research", "competitive analysis", "product strategy",
    "go-to-market", "pricing strategy", "revenue modeling",
    "sales engineering", "solution architecture", "presales",
    "account management", "relationship management", "partnerships",
    "content strategy", "content marketing", "seo", "sem",
    "social media marketing", "email marketing", "marketing automation",
    "brand management", "public relations", "copywriting",
    "video editing", "audio editing", "podcasting", "streaming",
    "data entry", "transcription", "translation", "localization",
    # ── Misc ──────────────────────────────────────────────────────────────────
    "webscraping", "beautifulsoup", "scrapy", "selenium",
    "celery", "redis queue", "bull", "sidekiq",
    "protobuf", "avro", "json schema", "thrift", "grpc",
    "regex", "xml", "yaml", "toml", "json", "csv",
    "rest", "soap", "graphql", "webhook", "api design",
    "seo", "analytics", "google analytics", "segment", "mixpanel",
    "amplitude", "hotjar", "fullstory", "crazy egg", "optimizely",
    "ab testing", "multivariate testing", "conversion rate optimization",
    "latex", "markdown", "asciidoc", "restructuredtext",
    "vim", "emacs", "vscode", "intellij", "pycharm", "webstorm",
    "eclipse", "netbeans", "visual studio", "rider", "clion",
    "postman", "insomnia", "swagger ui", "hoppscotch",
    "git", "gitflow", "trunk based development", "monorepo", "turborepo", "nx",
    "dependabot", "snyk", "black duck", "whitesource", " FOSSA",
    "swagger", "openapi", "postman", "graphql playground",
    "diagrams", "mermaid", "plantuml", "draw.io", "lucidchart",
    "chatgpt", "claude", "copilot", "cursor", "codeium", "tabnine",
    "notion", "obsidian", "roam research", "logseq", "evernote",
    "slack", "microsoft teams", "discord", "zoom", "webex", "google meet",
    "loom", "gitpitch", "canva", "gamma",
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


# ═══════════════════════════════════════════════════════════════════════════════
# DOMAIN-CLUSTERED SKILL TAXONOMY
# SKILL_TAXONOMY is the authoritative source for skill domain classification.
# MASTER_SKILLS is kept for backward compatibility (FlashText processor, DB seeding).
# ═══════════════════════════════════════════════════════════════════════════════

SKILL_TAXONOMY = {
    "programming_languages": {
        "core_imperative": [
            "python", "java", "c++", "c#", "c", "golang", "go", "rust", "kotlin",
            "swift", "ruby", "php", "perl", "ada", "cobol", "fortran", "vba",
            "pascal", "assembly", "nim", "zig", "crystal", "dart"
        ],
        "functional": [
            "haskell", "erlang", "elixir", "clojure", "f#", "lisp", "scheme",
            "ocaml", "reasonml", "purescript", "elm", "scala"
        ],
        "scripting": [
            "bash", "powershell", "groovy", "lua", "perl"
        ],
        "specialized": [
            "r", "matlab", "julia", "sas", "spss", "minitab", "stata"
        ],
        "blockchain": [
            "solidity", "vyper", "move", "cairo"
        ]
    },
    "web_frontend": {
        "frameworks": [
            "react", "vue.js", "vue", "angular", "next.js", "nuxt.js", "svelte",
            "astro", "remix", "gatsby", "ember.js", "backbone.js", "qwik", "solid.js"
        ],
        "libraries": ["jquery", "lit", "stencil", "preact"],
        "css_frameworks": ["tailwind", "bootstrap", "material ui", "chakra ui", "ant design"],
        "tools": ["storybook", "webpack", "vite", "parcel", "rollup"],
        "markup": ["html", "xml", "htmx", "alpine.js"]
    },
    "web_backend": {
        "nodejs": ["node.js", "express.js", "nestjs", "koa", "hapi", "feathers", "strapi"],
        "python": ["fastapi", "django", "flask", "tornado", "aiohttp", "starlette", "litestar"],
        "java": ["spring boot", "spring", "quarkus", "micronaut"],
        "golang": ["gin", "fiber", "echo", "chi"],
        "rust": ["actix", "axum", "rocket", "warp"],
        "ruby": ["rails", "sinatra"],
        "elixir": ["phoenix"],
        "php": ["laravel", "symfony", "codeigniter"],
        "dotnet": ["asp.net", "asp.net core", "dotnet", ".net", "blazor", "wpf", "winforms"]
    },
    "databases": {
        "relational": [
            "postgresql", "mysql", "sqlite", "mariadb", "oracle", "microsoft sql server",
            "db2", "informix", "sybase", "teradata", "greenplum"
        ],
        "nosql_document": ["mongodb", "couchdb", "firebase", "firestore", "realm", "fauna"],
        "nosql_kv": ["redis", "memcached"],
        "search_timeseries": ["elasticsearch", "cassandra", "influxdb", "timescaledb", "clickhouse"],
        "graph_specialized": ["neo4j", "dynamodb"],
        "cloud_managed": ["snowflake", "bigquery", "redshift", "databricks", "supabase", "planetscale"],
        "orms": [
            "sqlalchemy", "hibernate", "prisma", "typeorm", "sequelize", "drizzle",
            "mongoose", "entity framework", "dapper"
        ]
    },
    "cloud_platforms": {
        "hyperscalers": ["amazon web services", "aws", "google cloud platform", "gcp", "microsoft azure", "azure"],
        "regional": ["digital ocean", "linode", "vultr", "hetzner", "oracle cloud", "ibm cloud", "alibaba cloud"],
        "deployment_platforms": ["vercel", "netlify", "heroku", "fly.io", "render", "railway"],
        "backend_as_service": ["supabase", "firebase", "appwrite", "pocketbase"],
        "orchestration": ["cloudfoundry", "openshift", "rancher", "nomad"]
    },
    "aws_services": {
        "compute": ["ec2", "lambda", "ecs", "eks", "elastic beanstalk"],
        "storage": ["s3", "ebs", "efs"],
        "database": ["rds", "aurora", "dynamodb"],
        "networking": ["vpc", "api gateway", "cloudfront", "route53"],
        "messaging": ["sqs", "sns", "kinesis", "eventbridge"],
        "analytics": ["glue", "athena", "emr", "sagemaker"],
        "management": ["cloudformation", "iam", "cloudwatch", "step functions"]
    },
    "devops_infrastructure": {
        "containers": ["docker", "docker swarm"],
        "orchestration": ["kubernetes", "k8s", "helm", "kustomize"],
        "iac": ["terraform", "ansible", "puppet", "chef", "vagrant", "packer", "pulumi"],
        "ci_cd": [
            "jenkins", "github actions", "gitlab ci", "circleci", "travis ci",
            "bitbucket pipelines", "argo cd", "flux", "spinnaker"
        ],
        "monitoring": [
            "prometheus", "grafana", "datadog", "new relic", "dynatrace", "splunk",
            "elk stack", "loki", "jaeger", "zipkin", "opentelemetry"
        ],
        "networking_proxy": ["nginx", "apache", "traefik", "envoy"],
        "secrets": ["vault", "consul"]
    },
    "embedded_systems": {
        "rtos_os": ["embedded", "rtos", "freertos", "zephyr", "vxworks", "qnx", "embedded linux", "baremetal"],
        "hardware": ["microcontroller", "fpga", "arm", "arm cortex", "avr", "pic"],
        "protocols": ["uart", "spi", "i2c", "can bus", "modbus", "mqtt", "coap", "ble", "zigbee", "lorawan"],
        "tools": ["openocd", "jtag", "gdb"],
        "standards": ["iso 26262", "misra", "do-178", "functional safety"],
        "firmware": ["firmware", "bsp", "bootloader", "device driver"],
        "industrial": ["plc", "ladder logic", "scada", "industrial automation"]
    },
    "mobile": {
        "ios": ["ios", "swift", "swiftui", "objective-c", "xcode"],
        "android": ["android", "kotlin", "jetpack compose", "android studio"],
        "crossplatform": ["react native", "flutter", "xamarin", "ionic", "capacitor", "cordova"]
    },
    "ai_ml": {
        "core": [
            "machine learning", "deep learning", "neural networks", "reinforcement learning",
            "generative ai", "computer vision", "natural language processing", "nlp"
        ],
        "frameworks": ["pytorch", "tensorflow", "keras", "jax", "scikit-learn", "xgboost", "lightgbm"],
        "llm": ["transformers", "hugging face", "langchain", "llamaindex", "rag", "fine-tuning", "ollama", "openai"],
        "tools": ["mlflow", "wandb", "kubeflow", "vertex ai"],
        "vision": ["opencv", "yolo", "stable diffusion"]
    },
    "data_engineering": {
        "processing": ["apache spark", "spark", "pyspark", "hadoop", "hive", "flink"],
        "messaging": ["apache kafka", "kafka", "rabbitmq"],
        "orchestration": ["apache airflow", "airflow", "prefect", "dagster"],
        "transformation": ["dbt", "fivetran", "airbyte"],
        "concepts": ["etl", "data pipeline", "data warehousing", "data lake", "data mesh", "data governance"]
    },
    "data_science_analytics": {
        "core_libraries": ["pandas", "numpy", "scipy", "polars"],
        "visualization": ["matplotlib", "seaborn", "plotly"],
        "bi": ["tableau", "power bi", "looker", "metabase"],
        "tools": ["jupyter", "excel", "google analytics"]
    },
    "architecture_design": {
        "patterns": [
            "microservices", "event-driven", "cqrs", "event sourcing", "saga pattern",
            "domain driven design", "ddd", "clean architecture"
        ],
        "api": ["rest api", "graphql", "grpc", "websocket", "openapi", "swagger"]
    },
    "security": {
        "auth": ["oauth2", "jwt", "saml", "ldap", "rbac"],
        "crypto": ["tls", "ssl", "cryptography"],
        "compliance": ["soc2", "gdpr", "hipaa", "pci dss"],
        "practices": ["penetration testing", "owasp", "zero trust"]
    },
    "testing": {
        "types": ["unit testing", "integration testing", "e2e testing", "tdd", "bdd"],
        "frameworks": ["pytest", "jest", "vitest", "mocha", "cypress", "playwright", "selenium"],
        "performance": ["k6", "locust", "jmeter"],
        "coverage": ["sonarqube", "codecov"]
    },
    "blockchain": {
        "platforms": ["ethereum", "bitcoin", "solana", "cardano", "polkadot"],
        "concepts": ["blockchain", "web3", "smart contracts", "defi", "nft"],
        "tools": ["hyperledger", "chainlink", "ipfs"]
    },
    "gaming_graphics": {
        "engines": ["unity", "unreal engine", "godot"],
        "web": ["three.js", "babylon.js", "webgl", "webgpu"]
    },
    "networking": {
        "protocols": ["tcp/ip", "udp", "http", "dns", "vpn"],
        "infrastructure": ["load balancing", "cdn", "reverse proxy", "firewall"]
    },
    "project_management": {
        "methodologies": ["agile", "scrum", "kanban", "safe", "lean"],
        "tools": ["jira", "confluence", "linear", "asana", "trello", "notion"],
        "vcs": ["git", "github", "gitlab", "bitbucket"]
    },
    "business_erp": {
        "crm": ["salesforce", "hubspot", "zoho"],
        "erp": ["sap", "oracle erp", "dynamics 365", "netsuite", "workday"],
        "service": ["servicenow", "freshdesk", "zendesk"],
        "low_code": ["power platform", "power apps", "outsystems", "mendix"]
    },
    "design_ux": {
        "tools": ["figma", "sketch", "adobe xd"],
        "concepts": ["ui/ux", "wireframing", "prototyping", "accessibility", "responsive design"]
    },
    "soft_skills": {
        "communication": ["communication", "technical writing", "public speaking"],
        "leadership": ["leadership", "mentoring", "coaching"],
        "analytical": ["problem solving", "critical thinking", "analytical thinking"]
    }
}


# ═══════════════════════════════════════════════════════════════════════════════
# NORMALIZATION HELPERS
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


def normalize_skill_name(skill: str) -> str:
    """Normalize a skill name using SKILL_ALIASES.

    Returns the canonical form if an alias exists, otherwise returns
    the original (stripped).  When the input already *is* the canonical
    form (case-insensitive), the original casing is preserved so that
    "Python" stays "Python" rather than becoming "python".

    This is the public API for parser_service and any other consumer
    that needs to collapse alias variants at extraction time.

    Examples
    --------
    >>> normalize_skill_name("nodejs")
    'node.js'
    >>> normalize_skill_name("react.js")
    'react'
    >>> normalize_skill_name("Python")
    'Python'
    """
    if not skill:
        return skill
    stripped = skill.strip()
    lower = stripped.lower()

    # Special-case: preserve c++ / c# casing from SKILL_ALIASES keys
    if lower in ("c++", "c#"):
        for canonical in SKILL_ALIASES:
            if canonical.lower() == lower:
                return canonical
        return stripped

    # Normalize punctuation for lookup (e.g. "react.js" -> "react js")
    norm = _normalize_skill(stripped)

    # Check if the normalised form matches a canonical key
    for canonical, aliases in SKILL_ALIASES.items():
        if norm == _normalize_skill(canonical):
            # Input IS the canonical form (possibly different casing/punctuation).
            # If only casing differs (lowered input == canonical key), preserve
            # original casing — e.g. "Python" stays "Python".
            # If punctuation/spacing differs (e.g. "node js" vs "node.js"),
            # return the canonical form.
            if lower == canonical.lower():
                return stripped
            return canonical
        for alias in aliases:
            if norm == _normalize_skill(alias):
                # Input is an alias — map to canonical form.
                return canonical

    # No alias match — return original stripped form
    return stripped


# ═══════════════════════════════════════════════════════════════════════════════
# HIGH-COLLISION SKILLS
# Skills that are common English words — require domain co-occurrence validation
# when extracted from raw text (not from structured skills sections)
# ═══════════════════════════════════════════════════════════════════════════════

def _build_collision_skills():
    """Auto-detect skills appearing in 2+ domains plus known English-word homonyms."""
    multi_domain = set()
    # Find skills that exist in multiple top-level domains
    skill_domains = {}  # norm_skill -> set of domain names
    for domain_name, subcats in SKILL_TAXONOMY.items():
        for subcat_name, skill_list in subcats.items():
            for s in skill_list:
                norm = _normalize_skill(s)
                if norm not in skill_domains:
                    skill_domains[norm] = set()
                skill_domains[norm].add(domain_name)
    
    for norm, domains in skill_domains.items():
        if len(domains) >= 2:
            multi_domain.add(norm)
    
    # Known English-word homonyms that could appear in non-technical context
    ENGLISH_HOMONYMS = {
        "go", "r", "c", "swift", "ruby", "rust", "dart",
        "scala", "spark", "rocket", "phoenix", "julia",
        "nim", "elixir", "erlang", "embedded", "railway",
        "rtos", "communication", "assembly",
    }
    return multi_domain | ENGLISH_HOMONYMS

HIGH_COLLISION_SKILLS = _build_collision_skills()


def _get_skill_domains(skill: str) -> set:
    """Return set of top-level domain names this skill belongs to in SKILL_TAXONOMY."""
    norm = _normalize_skill(skill)
    domains = set()
    for domain_name, subcategories in SKILL_TAXONOMY.items():
        for subcat_skills in subcategories.values():
            if norm in {_normalize_skill(s) for s in subcat_skills}:
                domains.add(domain_name)
    return domains


def _get_skill_subcategory_keys(skill: str) -> set:
    """Return set of (domain, subcategory) tuples for a skill in SKILL_TAXONOMY.

    More granular than _get_skill_domains — used for two-pass validation
    to avoid false positives where a skill shares a top-level domain but
    belongs to a completely different subcategory (e.g. 'aws' in
    cloud_platforms.hyperscalers should not validate 'railway' in
    cloud_platforms.deployment_platforms).
    """
    norm = _normalize_skill(skill)
    keys = set()
    for domain_name, subcategories in SKILL_TAXONOMY.items():
        for subcat_name, skill_list in subcategories.items():
            if norm in {_normalize_skill(s) for s in skill_list}:
                keys.add((domain_name, subcat_name))
    return keys


def _flatten_taxonomy() -> set:
    """Derive flat skill set from SKILL_TAXONOMY for backward compatibility."""
    skills = set()
    for subcategories in SKILL_TAXONOMY.values():
        for skill_list in subcategories.values():
            skills.update(_normalize_skill(s) for s in skill_list)
    return skills


def _expand_skill(skill: str) -> List[str]:
    """Return skill + all its aliases, all normalized."""
    n = _normalize_skill(skill)
    aliases = [_normalize_skill(a) for a in SKILL_ALIASES.get(n, [])]
    # Also check the original unnormalized form
    raw_aliases = SKILL_ALIASES.get(skill.lower(), [])
    aliases += [_normalize_skill(a) for a in raw_aliases]
    return list(dict.fromkeys([n] + aliases))


# ═══════════════════════════════════════════════════════════════════════════════
# SKILLS REGISTRY
# ═══════════════════════════════════════════════════════════════════════════════

def _build_domain_skill_map() -> Dict[str, str]:
    """Map each MASTER_SKILL to its primary domain for seeding."""
    from app.backend.services.constants import DOMAIN_KEYWORDS
    skill_to_domain: Dict[str, str] = {}
    for domain, keywords in DOMAIN_KEYWORDS.items():
        for kw in keywords:
            skill_to_domain[kw] = domain
    return skill_to_domain


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
        """Upsert MASTER_SKILLS into the skills table — safe to call on every startup.

        Uses INSERT … ON CONFLICT (name) DO NOTHING so re-deploys never crash
        on duplicate keys, and new skills added to MASTER_SKILLS are picked up
        automatically without manual DB intervention.
        """
        try:
            from sqlalchemy.dialects.postgresql import insert as pg_insert
            from app.backend.models.db_models import Skill

            _domain_map = _build_domain_skill_map()
            rows = [
                {
                    "name":    skill,
                    "aliases": ",".join(SKILL_ALIASES.get(skill, [])),
                    "domain":  _domain_map.get(skill, "general"),
                    "status":  "active",
                    "source":  "seed",
                    "frequency": 0,
                }
                for skill in MASTER_SKILLS
            ]
            stmt = pg_insert(Skill).values(rows).on_conflict_do_nothing(index_elements=["name"])
            db.execute(stmt)
            db.commit()
            logger.info("Skills upsert complete (%d definitions)", len(rows))
        except Exception as e:
            db.rollback()
            logger.warning("Skills seed failed (non-fatal): %s", e)

    def load(self, db=None) -> None:
        """Load active skills from DB into the in-memory processor.

        Always uses a fresh query — never reuses a session that may have been
        poisoned by a previous exception.
        """
        skills = []
        if db is not None:
            try:
                # Explicitly begin a clean transaction in case the caller's
                # session was rolled back by seed_if_empty above.
                db.rollback()
                from app.backend.models.db_models import Skill
                rows = db.query(Skill).filter(Skill.status == "active").all()
                if rows:
                    for row in rows:
                        skills.append(row.name)
                        if row.aliases:
                            skills.extend(a.strip() for a in row.aliases.split(",") if a.strip())
            except Exception as e:
                logger.warning("Skills load from DB failed (using hardcoded): %s", e)
        if not skills:
            skills = list(MASTER_SKILLS)
        self._build_processor(skills)
        self._loaded = True
        logger.info("SkillsRegistry loaded %d skills", len(self._skills))

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
# MAIN SKILL MATCHING FUNCTION
# ═══════════════════════════════════════════════════════════════════════════════

def match_skills(candidate_skills, jd_skills, jd_nice_to_have=None,
                 structured_skills=None, text_scanned_skills=None) -> dict:
    """Unified skill matching — single source of truth.

    Args:
        candidate_skills: List of skills identified from the candidate.
        jd_skills: List of required skills from the job description.
        jd_nice_to_have: Optional list of nice-to-have skills.
        structured_skills: Tier 0 skills (parser output, high confidence).
        text_scanned_skills: Tier 2 skills (text-scanned, low confidence).
            These are promoted into the candidate set only if they pass
            strict domain-context validation.

    Returns dict with:
    - core_match_ratio: float (0-1)
    - secondary_match_ratio: float (0-1)
    - matched_skills: list
    - missing_skills: list
    - skill_score: float (0-100)
    - adjacent_skills: list
    - required_count: int
    - matched_count: int
    """
    if not isinstance(candidate_skills, list):
        candidate_skills = list(candidate_skills) if candidate_skills else []
    if not isinstance(jd_skills, list):
        jd_skills = list(jd_skills) if jd_skills else []
    if jd_nice_to_have is None:
        jd_nice_to_have = []

    # Step 1: Build candidate set from structured candidate_skills ONLY
    cand_normalized: List[str] = []
    for s in candidate_skills:
        if s and isinstance(s, str):
            cand_normalized.extend(_expand_skill(s))
    cand_set = set(cand_normalized)

    # Step 2: Build domain context from structured skills
    context_subcats = {}
    for s in (structured_skills or candidate_skills):
        norm = _normalize_skill(s)
        for key in _get_skill_subcategory_keys(norm):
            context_subcats[key] = context_subcats.get(key, 0) + 1

    # Step 3: Promote text-scanned skills WITH strict validation
    promoted = []
    for s in (text_scanned_skills or []):
        s_norm = _normalize_skill(s)
        # Skip if already in candidate set (from structured)
        if s_norm in cand_set:
            continue

        subcats = _get_skill_subcategory_keys(s_norm)

        if s_norm in HIGH_COLLISION_SKILLS or not subcats:
            # High-collision or unknown-domain: require 2+ context skills from same subcategory
            has_strong_context = any(context_subcats.get(k, 0) >= 2 for k in subcats)
            if not has_strong_context:
                continue  # REJECT
        else:
            # Non-collision: require 1+ context skill from same domain
            skill_domains = {k[0] for k in subcats}
            context_domains = {k[0] for k in context_subcats}
            if not (skill_domains & context_domains):
                continue  # REJECT (different domain entirely)

        promoted.append(s)
        cand_set.update(_expand_skill(s))

    matched = []
    missing = []

    for req in jd_skills:
        if not req or not isinstance(req, str):
            continue
        req_variants = _expand_skill(req)
        found = False

        # Exact / alias match
        if any(v in cand_set for v in req_variants):
            found = True

        # Substring match: "React Native" in "React" or vice-versa
        if not found:
            req_norm = _normalize_skill(req)
            if len(req_norm) > 3:  # Skip very short skills for substring matching
                for c in cand_set:
                    if len(c) > 3 and (req_norm in c or c in req_norm):
                        # High-collision skills require same subcategory
                        if req_norm in HIGH_COLLISION_SKILLS:
                            req_subcats = _get_skill_subcategory_keys(req_norm)
                            c_subcats = _get_skill_subcategory_keys(c)
                            if not (req_subcats & c_subcats):
                                continue  # Different domains, skip
                        found = True
                        break

        # Fuzzy fallback (rapidfuzz, threshold 88)
        if not found:
            req_norm = _normalize_skill(req)
            if req_norm not in HIGH_COLLISION_SKILLS:  # Skip fuzzy for ambiguous skills
                try:
                    from rapidfuzz import fuzz
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
    for s in jd_nice_to_have:
        if not s or not isinstance(s, str):
            continue
        s_variants = _expand_skill(s)
        if any(v in cand_set for v in s_variants):
            adjacent.append(s)

    total_req = max(len(jd_skills), 1)
    skill_score = round(len(matched) / total_req * 100) if jd_skills else 50
    skill_score = min(100, skill_score)

    core_match_ratio = len(matched) / total_req
    secondary_match_ratio = len(adjacent) / max(len(jd_nice_to_have), 1)

    return {
        "core_match_ratio": core_match_ratio,
        "secondary_match_ratio": secondary_match_ratio,
        "matched_skills": matched,
        "missing_skills": missing,
        "skill_score": skill_score,
        "adjacent_skills": adjacent,
        "required_count": len(jd_skills),
        "matched_count": len(matched),
    }


def validate_skills_against_text(skills: List[str], text: str) -> List[str]:
    """Filter out skills not found in the original text (hallucination guard)."""
    if not skills or not text:
        return []

    text_lower = text.lower()
    validated = []

    for skill in skills:
        if not skill or not isinstance(skill, str):
            continue

        skill_lower = skill.lower()

        # Direct substring match
        if skill_lower in text_lower:
            validated.append(skill)
            continue

        # Check aliases from the skill registry
        aliases = SKILL_ALIASES.get(skill_lower, [])
        if any(alias.lower() in text_lower for alias in aliases):
            validated.append(skill)
            continue

        # Multi-word skill: check if any significant word (3+ chars) matches
        words = [w for w in skill_lower.split() if len(w) > 2]
        if words and any(word in text_lower for word in words):
            validated.append(skill)
            continue

    return validated

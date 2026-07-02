"""
JD Templates Service - Pre-built job description templates for common roles.

These templates help recruiters write JDs that the system can parse effectively,
improving accuracy for non-technical roles.
"""

from typing import Dict, List, Any, Optional


JD_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "hr_manager": {
        "title": "HR Manager",
        "category": "Human Resources",
        "description": "Lead our people operations and drive employee engagement initiatives.",
        "requirements": [
            "5+ years HR experience",
            "SHRM-CP or PHR certification preferred",
            "Experience with Workday, BambooHR",
            "Strong knowledge of employment law",
        ],
        "nice_to_have": [
            "SAP SuccessFactors",
            "ADP Workforce Now",
            "International HR experience",
        ],
        "required_skills": ["employee relations", "performance management", "hris"],
        "domain": "hr",
    },
    "recruiter": {
        "title": "Technical Recruiter",
        "category": "Human Resources",
        "description": "Source and hire top technical talent for our engineering team.",
        "requirements": [
            "3+ years technical recruiting experience",
            "Experience with LinkedIn Recruiter, Greenhouse",
            "Strong sourcing and screening skills",
            "Track record of meeting hiring targets",
        ],
        "nice_to_have": [
            "Experience hiring for specific tech stacks",
            "Boolean search expertise",
            "ATS administration experience",
        ],
        "required_skills": ["recruitment", "sourcing", "ats", "interview scheduling"],
        "domain": "hr",
    },
    "account_executive": {
        "title": "Account Executive",
        "category": "Sales",
        "description": "Drive revenue growth by managing key client relationships.",
        "requirements": [
            "3+ years B2B sales experience",
            "Experience with Salesforce CRM",
            "Strong negotiation and closing skills",
            "Track record of meeting quota",
        ],
        "nice_to_have": [
            "Experience in our industry",
            "Enterprise sales experience",
            "Sales methodology training (MEDDIC, SPIN)",
        ],
        "required_skills": ["crm", "pipeline management", "negotiation", "b2b sales"],
        "domain": "sales",
    },
    "financial_analyst": {
        "title": "Financial Analyst",
        "category": "Finance",
        "description": "Analyze financial data and provide insights for business decisions.",
        "requirements": [
            "3+ years financial analysis experience",
            "CPA or CFA preferred",
            "Experience with QuickBooks, Excel",
            "Knowledge of GAAP",
        ],
        "nice_to_have": [
            "Experience with NetSuite",
            "Financial modeling expertise",
            "FP&A experience",
        ],
        "required_skills": ["financial analysis", "excel", "gaap", "financial modeling"],
        "domain": "finance",
    },
    "accountant": {
        "title": "Staff Accountant",
        "category": "Finance",
        "description": "Handle day-to-day accounting operations and financial reporting.",
        "requirements": [
            "2+ years accounting experience",
            "CPA preferred",
            "Experience with QuickBooks or similar",
            "Knowledge of accounts payable/receivable",
        ],
        "nice_to_have": [
            "Bookkeeping certification",
            "Payroll experience",
            "Non-profit accounting",
        ],
        "required_skills": ["accounting", "bookkeeping", "quickbooks", "reconciliation"],
        "domain": "finance",
    },
    "registered_nurse": {
        "title": "Registered Nurse",
        "category": "Healthcare",
        "description": "Provide patient care in our healthcare facility.",
        "requirements": [
            "Current RN license",
            "2+ years clinical experience",
            "BLS certification",
            "Epic or Cerner experience preferred",
        ],
        "nice_to_have": [
            "Specialty certification",
            "BSN degree",
            "Telehealth experience",
        ],
        "required_skills": ["patient care", "nursing", "electronic health records", "hipaa"],
        "domain": "healthcare",
    },
    "medical_assistant": {
        "title": "Medical Assistant",
        "category": "Healthcare",
        "description": "Support physicians with clinical and administrative tasks.",
        "requirements": [
            "Medical assistant certification",
            "1+ years clinical experience",
            "Knowledge of medical terminology",
            "Experience with EHR systems",
        ],
        "nice_to_have": [
            "Phlebotomy certification",
            "Bilingual",
            "Specialty clinic experience",
        ],
        "required_skills": ["medical terminology", "vital signs", "ehr", "clinical assessment"],
        "domain": "healthcare",
    },
    "paralegal": {
        "title": "Paralegal",
        "category": "Legal",
        "description": "Support attorneys with legal research and case preparation.",
        "requirements": [
            "3+ years paralegal experience",
            "Paralegal certification preferred",
            "Experience with Westlaw, LexisNexis",
            "Strong legal research skills",
        ],
        "nice_to_have": [
            "Litigation support experience",
            "Corporate law background",
            "Contract management experience",
        ],
        "required_skills": ["legal research", "litigation support", "document management"],
        "domain": "legal",
    },
    "marketing_manager": {
        "title": "Marketing Manager",
        "category": "Marketing",
        "description": "Lead marketing initiatives and drive brand awareness.",
        "requirements": [
            "4+ years marketing experience",
            "Experience with HubSpot, Google Analytics",
            "SEO/SEM knowledge",
            "Content marketing experience",
        ],
        "nice_to_have": [
            "Marketing automation experience",
            "Brand management background",
            "B2B marketing experience",
        ],
        "required_skills": ["digital marketing", "seo", "google analytics", "content marketing"],
        "domain": "marketing",
    },
    "operations_manager": {
        "title": "Operations Manager",
        "category": "Operations",
        "description": "Oversee daily operations and process improvement initiatives.",
        "requirements": [
            "5+ years operations experience",
            "Experience with process improvement",
            "Knowledge of supply chain management",
            "Six Sigma preferred",
        ],
        "nice_to_have": [
            "Lean manufacturing experience",
            "Project management certification",
            "ERP system experience",
        ],
        "required_skills": ["operations management", "process improvement", "supply chain"],
        "domain": "operations_admin",
    },
    "project_manager": {
        "title": "Project Manager",
        "category": "Operations",
        "description": "Lead cross-functional projects from initiation to delivery.",
        "requirements": [
            "3+ years project management experience",
            "PMP certification preferred",
            "Experience with Jira, Confluence",
            "Agile methodology experience",
        ],
        "nice_to_have": [
            "Scrum Master certification",
            "Risk management experience",
            "Vendor management experience",
        ],
        "required_skills": ["project management", "agile", "jira", "stakeholder management"],
        "domain": "management",
    },
    "customer_success_manager": {
        "title": "Customer Success Manager",
        "category": "Sales",
        "description": "Drive customer satisfaction and retention through proactive engagement.",
        "requirements": [
            "3+ years customer success or account management experience",
            "Experience with Salesforce or similar CRM",
            "Strong communication skills",
            "Track record of improving customer metrics",
        ],
        "nice_to_have": [
            "SaaS experience",
            "Renewal management experience",
            "Upselling/cross-selling experience",
        ],
        "required_skills": ["customer success", "crm", "account management", "stakeholder management"],
        "domain": "sales",
    },
}


def get_all_templates() -> List[Dict[str, Any]]:
    """Get all available JD templates."""
    return [
        {
            "id": key,
            "title": template["title"],
            "category": template["category"],
            "description": template["description"],
        }
        for key, template in JD_TEMPLATES.items()
    ]


def get_template(template_id: str) -> Optional[Dict[str, Any]]:
    """Get a specific JD template by ID."""
    return JD_TEMPLATES.get(template_id)


def generate_jd_from_template(template_id: str, customizations: Optional[Dict] = None) -> str:
    """Generate a full JD text from a template with optional customizations.

    Args:
        template_id: ID of the template to use
        customizations: Optional dict with custom values (company_name, etc.)

    Returns:
        Formatted JD text
    """
    template = JD_TEMPLATES.get(template_id)
    if not template:
        return ""

    customizations = customizations or {}
    company_name = customizations.get("company_name", "[Company Name]")
    location = customizations.get("location", "[Location]")

    jd_parts = [
        f"# {template['title']}",
        f"## About Us",
        f"{company_name} is seeking a {template['title']} to join our team in {location}.",
        f"",
        f"## Role Overview",
        template["description"],
        f"",
        f"## Requirements",
    ]

    for req in template.get("requirements", []):
        jd_parts.append(f"- {req}")

    nice_to_have = template.get("nice_to_have", [])
    if nice_to_have:
        jd_parts.append("")
        jd_parts.append("## Nice to Have")
        for item in nice_to_have:
            jd_parts.append(f"- {item}")

    return "\n".join(jd_parts)


def get_templates_by_category(category: str) -> List[Dict[str, Any]]:
    """Get templates filtered by category."""
    return [
        {"id": key, "title": template["title"], "description": template["description"]}
        for key, template in JD_TEMPLATES.items()
        if template.get("category", "").lower() == category.lower()
    ]


def get_categories() -> List[str]:
    """Get all unique template categories."""
    return list(set(t["category"] for t in JD_TEMPLATES.values()))

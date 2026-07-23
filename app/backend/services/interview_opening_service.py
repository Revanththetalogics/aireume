"""Tenant-scoped custom interview opening scripts (voice + live screen)."""
from __future__ import annotations

import re
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.backend.models.db_models import Tenant, VoiceTenantConfig

PLACEHOLDER_PATTERN = re.compile(r"\{(\w+)\}")
ALLOWED_PLACEHOLDERS = frozenset(
    {"candidate_first_name", "role_title", "company_name", "bot_name"}
)
MAX_OPENING_SCRIPT_LEN = 1200

DEFAULT_OPENING_TEMPLATE = (
    "Hi, is this {candidate_first_name}? This is {bot_name} calling from "
    "{company_name} about the {role_title} position. "
    "Do you have a few minutes for a quick interview call?"
)

DEFAULT_CONSENT_TEMPLATE = (
    "Great, thanks {candidate_first_name}. This call is being recorded for "
    "evaluation purposes. Do you consent to proceed?"
)

SUGGEST_OPENING_PROMPT = """Write a single spoken phone-screen opening for a recruiter AI bot.

Requirements:
- 2-4 sentences, natural for a phone call
- Introduce the bot by name and company
- Mention the role title
- Ask if the candidate has a few minutes
- Do NOT mention recording or consent (that comes in a separate step)
- Use exactly these placeholders where appropriate: {candidate_first_name}, {role_title}, {company_name}, {bot_name}
- English only

Company: {company_name}
Bot name: {bot_name}
About the company (optional): {company_about}
Tone: {tone}

Return ONLY the opening script text, no quotes or markdown."""


def resolve_company_name(tenant: Tenant | None) -> str:
    if tenant is None:
        return "the company"
    return (tenant.brand_name or tenant.name or "the company").strip() or "the company"


def candidate_first_name(full_name: str | None) -> str:
    if not full_name or not str(full_name).strip():
        return "there"
    return str(full_name).strip().split()[0]


def validate_opening_template(template: str | None) -> list[str]:
    if not template or not str(template).strip():
        return ["Opening script cannot be empty when custom opening is enabled."]
    text = str(template).strip()
    if len(text) > MAX_OPENING_SCRIPT_LEN:
        return [f"Opening script must be at most {MAX_OPENING_SCRIPT_LEN} characters."]
    unknown = [
        m.group(0)
        for m in PLACEHOLDER_PATTERN.finditer(text)
        if m.group(1) not in ALLOWED_PLACEHOLDERS
    ]
    if unknown:
        return [f"Unknown placeholder(s): {', '.join(sorted(set(unknown)))}"]
    return []


def render_interview_opening(template: str, **variables: str) -> str:
    """Replace allowed placeholders; leave unknown braces untouched."""

    def _replace(match: re.Match[str]) -> str:
        key = match.group(1)
        if key in ALLOWED_PLACEHOLDERS:
            return str(variables.get(key, match.group(0)))
        return match.group(0)

    return PLACEHOLDER_PATTERN.sub(_replace, template.strip())


def build_opening_context(
    *,
    candidate_name: str | None,
    role_title: str | None,
    company_name: str | None,
    bot_name: str | None,
) -> dict[str, str]:
    return {
        "candidate_first_name": candidate_first_name(candidate_name),
        "role_title": (role_title or "open role").strip() or "open role",
        "company_name": (company_name or "the company").strip() or "the company",
        "bot_name": (bot_name or "ARIA").strip() or "ARIA",
    }


def default_opening_text(
    *,
    candidate_name: str | None = None,
    role_title: str | None = None,
    company_name: str | None = None,
    bot_name: str | None = None,
) -> str:
    ctx = build_opening_context(
        candidate_name=candidate_name,
        role_title=role_title,
        company_name=company_name,
        bot_name=bot_name,
    )
    return render_interview_opening(DEFAULT_OPENING_TEMPLATE, **ctx)


def default_consent_text(**variables: str) -> str:
    ctx = build_opening_context(
        candidate_name=variables.get("candidate_name") or variables.get("candidate_first_name"),
        role_title=variables.get("role_title"),
        company_name=variables.get("company_name"),
        bot_name=variables.get("bot_name"),
    )
    return render_interview_opening(DEFAULT_CONSENT_TEMPLATE, **ctx)


def load_tenant_opening_config(db: Session, tenant_id: int) -> dict[str, Any]:
    row = db.execute(
        select(VoiceTenantConfig, Tenant)
        .join(Tenant, Tenant.id == VoiceTenantConfig.tenant_id)
        .where(VoiceTenantConfig.tenant_id == tenant_id)
    ).first()
    if row is None:
        tenant = db.get(Tenant, tenant_id)
        return {
            "use_custom_interview_opening": False,
            "interview_opening_script": None,
            "company_about_blurb": None,
            "bot_name": "ARIA",
            "consent_script": None,
            "company_name": resolve_company_name(tenant),
        }

    config, tenant = row
    return {
        "use_custom_interview_opening": bool(config.use_custom_interview_opening),
        "interview_opening_script": config.interview_opening_script,
        "company_about_blurb": config.company_about_blurb,
        "bot_name": config.bot_name or "ARIA",
        "consent_script": config.consent_script,
        "company_name": resolve_company_name(tenant),
    }


def resolve_opening_for_call(
    opening_config: dict[str, Any],
    *,
    candidate_name: str | None,
    role_title: str | None,
) -> str:
    ctx = build_opening_context(
        candidate_name=candidate_name,
        role_title=role_title,
        company_name=opening_config.get("company_name"),
        bot_name=opening_config.get("bot_name"),
    )
    if opening_config.get("use_custom_interview_opening") and opening_config.get("interview_opening_script"):
        return render_interview_opening(str(opening_config["interview_opening_script"]), **ctx)
    return default_opening_text(
        candidate_name=candidate_name,
        role_title=role_title,
        company_name=opening_config.get("company_name"),
        bot_name=opening_config.get("bot_name"),
    )


def resolve_consent_for_call(
    opening_config: dict[str, Any],
    *,
    candidate_name: str | None,
    role_title: str | None,
) -> str:
    if opening_config.get("consent_script"):
        ctx = build_opening_context(
            candidate_name=candidate_name,
            role_title=role_title,
            company_name=opening_config.get("company_name"),
            bot_name=opening_config.get("bot_name"),
        )
        return render_interview_opening(str(opening_config["consent_script"]), **ctx)
    return default_consent_text(
        candidate_name=candidate_name,
        role_title=role_title,
        company_name=opening_config.get("company_name"),
        bot_name=opening_config.get("bot_name"),
    )


def apply_tenant_opening_to_kit(
    kit: dict[str, Any],
    db: Session,
    tenant_id: int,
    *,
    candidate_name: str | None = None,
    role_title: str | None = None,
) -> dict[str, Any]:
    """When enabled, replace kit open.script for live screen parity with voice."""
    opening_config = load_tenant_opening_config(db, tenant_id)
    if not opening_config.get("use_custom_interview_opening"):
        return kit

    script_template = opening_config.get("interview_opening_script")
    if not script_template or not str(script_template).strip():
        return kit

    rendered = resolve_opening_for_call(
        opening_config,
        candidate_name=candidate_name,
        role_title=role_title,
    )
    open_block = dict(kit.get("open") or {})
    open_block["script"] = rendered
    open_block["recruiter_owned"] = False
    kit["open"] = open_block
    return kit


async def suggest_interview_opening_draft(
    *,
    company_name: str,
    bot_name: str,
    company_about: Optional[str] = None,
    tone: str = "professional",
) -> str:
    from app.backend.services.app_llm_client import generate_app_llm

    prompt = SUGGEST_OPENING_PROMPT.format(
        company_name=company_name or "the company",
        bot_name=bot_name or "ARIA",
        company_about=(company_about or "Not provided").strip()[:800],
        tone=tone or "professional",
    )
    text = await generate_app_llm(prompt, log_label="suggest_interview_opening")
    script = (text or "").strip().strip('"').strip("'")
    issues = validate_opening_template(script)
    if issues:
        return default_opening_text(
            candidate_name="there",
            role_title="open role",
            company_name=company_name,
            bot_name=bot_name,
        )
    return script


OPENING_ADMIN_FIELDS = frozenset(
    {"interview_opening_script", "use_custom_interview_opening", "company_about_blurb"}
)


def guard_opening_admin_fields(user, update_data: dict) -> None:
    from fastapi import HTTPException

    if OPENING_ADMIN_FIELDS.intersection(update_data) and getattr(user, "role", None) != "admin":
        raise HTTPException(status_code=403, detail="Admin access required to edit interview opening settings")

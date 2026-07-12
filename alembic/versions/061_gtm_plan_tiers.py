"""GTM plan tiers: Starter, Growth, Agency, Business, Enterprise with feature entitlements."""

import json
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = "061_gtm_plan_tiers"
down_revision = "060_enterprise_suite"
branch_labels = None
depends_on = None

NEW_FLAGS = [
    ("requisitions", "Requisitions"),
    ("pipeline", "Pipeline / Kanban"),
    ("compare", "Candidate Compare"),
    ("analytics", "Analytics Hub"),
    ("ai_interviews", "AI Interviews"),
    ("white_label", "White-label Branding"),
    ("hm_workflow", "Hiring Manager Workflow"),
]

PLAN_LIMITS = {
    "starter": {
        "analyses_per_month": 30,
        "batch_size": 10,
        "team_members": 2,
        "storage_gb": 1,
        "api_access": False,
        "custom_weights": False,
        "priority_support": False,
        "dedicated_support": False,
        "custom_integrations": False,
        "sso": False,
        "requisitions": False,
        "pipeline": False,
        "compare": False,
        "analytics": False,
        "ai_interviews": False,
        "video_analysis": False,
        "export_excel": False,
        "transcript_analysis": False,
        "email_generation": False,
        "white_label": False,
        "hm_workflow": False,
    },
    "growth": {
        "analyses_per_month": 200,
        "batch_size": 20,
        "team_members": 5,
        "storage_gb": 10,
        "api_access": False,
        "custom_weights": False,
        "priority_support": True,
        "dedicated_support": False,
        "custom_integrations": False,
        "sso": False,
        "requisitions": True,
        "pipeline": True,
        "compare": True,
        "analytics": False,
        "ai_interviews": False,
        "video_analysis": False,
        "export_excel": True,
        "transcript_analysis": False,
        "email_generation": True,
        "white_label": False,
        "hm_workflow": True,
    },
    "agency": {
        "analyses_per_month": 1000,
        "batch_size": 50,
        "team_members": 15,
        "storage_gb": 25,
        "api_access": True,
        "custom_weights": False,
        "priority_support": True,
        "dedicated_support": False,
        "custom_integrations": False,
        "sso": False,
        "requisitions": True,
        "pipeline": True,
        "compare": True,
        "analytics": True,
        "ai_interviews": False,
        "video_analysis": False,
        "export_excel": True,
        "transcript_analysis": False,
        "email_generation": True,
        "white_label": False,
        "hm_workflow": True,
    },
    "business": {
        "analyses_per_month": 500,
        "batch_size": 30,
        "team_members": 25,
        "storage_gb": 50,
        "api_access": True,
        "custom_weights": True,
        "priority_support": True,
        "dedicated_support": False,
        "custom_integrations": False,
        "sso": False,
        "requisitions": True,
        "pipeline": True,
        "compare": True,
        "analytics": True,
        "ai_interviews": True,
        "video_analysis": True,
        "export_excel": True,
        "transcript_analysis": True,
        "email_generation": True,
        "white_label": True,
        "hm_workflow": True,
    },
    "enterprise": {
        "analyses_per_month": -1,
        "batch_size": 100,
        "team_members": 999,
        "storage_gb": 100,
        "api_access": True,
        "custom_weights": True,
        "priority_support": True,
        "dedicated_support": True,
        "custom_integrations": True,
        "sso": True,
        "requisitions": True,
        "pipeline": True,
        "compare": True,
        "analytics": True,
        "ai_interviews": True,
        "video_analysis": True,
        "export_excel": True,
        "transcript_analysis": True,
        "email_generation": True,
        "white_label": True,
        "hm_workflow": True,
    },
}

PLAN_META = {
    "starter": {
        "display_name": "Starter",
        "description": "Screen resumes against a JD. Perfect for trying ARIA.",
        "price_monthly": 0,
        "price_yearly": 0,
        "sort_order": 1,
        "features": [
            "30 resume analyses / month",
            "Batch up to 10 resumes",
            "2 team members",
            "Core AI fit scoring",
        ],
    },
    "growth": {
        "display_name": "Growth",
        "description": "For growing recruiting teams — requisitions, pipeline, and compare.",
        "price_monthly": 4900,
        "price_yearly": 47000,
        "sort_order": 2,
        "features": [
            "200 analyses / month",
            "Requisitions & pipeline",
            "Hiring Manager portal & workflows",
            "Compare up to 5 candidates",
            "5 team members",
            "Export to Excel",
        ],
    },
    "agency": {
        "display_name": "Agency",
        "description": "High-volume screening for staffing firms and RPOs.",
        "price_monthly": 12900,
        "price_yearly": 131000,
        "sort_order": 3,
        "features": [
            "1,000 analyses / month",
            "Batch up to 50 resumes",
            "15 team members",
            "API access & analytics",
            "Export & email tools",
        ],
    },
    "business": {
        "display_name": "Business",
        "description": "Collaborative hiring with HM workflows, interviews, and branding.",
        "price_monthly": 19900,
        "price_yearly": 191000,
        "sort_order": 4,
        "features": [
            "500 analyses / month",
            "AI interviews & video analysis",
            "Custom scoring weights",
            "White-label branding",
            "25 team members",
        ],
    },
    "enterprise": {
        "display_name": "Enterprise",
        "description": "Unlimited scale, SSO, SLA, and dedicated support.",
        "price_monthly": 0,
        "price_yearly": 0,
        "sort_order": 5,
        "features": [
            "Unlimited analyses",
            "SSO & custom integrations",
            "Dedicated support & SLA",
            "Everything in Business",
        ],
    },
}


def _upsert_plan(conn, name: str, limits: dict, meta: dict):
    row = conn.execute(
        text("SELECT id FROM subscription_plans WHERE name = :name"),
        {"name": name},
    ).fetchone()
    payload = {
        "name": name,
        "display_name": meta["display_name"],
        "description": meta["description"],
        "limits": json.dumps(limits),
        "price_monthly": meta["price_monthly"],
        "price_yearly": meta["price_yearly"],
        "currency": "USD",
        "features": json.dumps(meta["features"]),
        "is_active": True,
        "sort_order": meta["sort_order"],
    }
    if row:
        conn.execute(
            text("""
                UPDATE subscription_plans SET
                    display_name = :display_name,
                    description = :description,
                    limits = :limits,
                    price_monthly = :price_monthly,
                    price_yearly = :price_yearly,
                    currency = :currency,
                    features = :features,
                    is_active = :is_active,
                    sort_order = :sort_order
                WHERE name = :name
            """),
            payload,
        )
    else:
        conn.execute(
            text("""
                INSERT INTO subscription_plans
                    (name, display_name, description, limits, price_monthly, price_yearly,
                     currency, features, is_active, sort_order)
                VALUES
                    (:name, :display_name, :description, :limits, :price_monthly, :price_yearly,
                     :currency, :features, :is_active, :sort_order)
            """),
            payload,
        )


def upgrade() -> None:
    conn = op.get_bind()

    # New feature flags
    for key, display in NEW_FLAGS:
        existing = conn.execute(
            text("SELECT id FROM feature_flags WHERE key = :key"),
            {"key": key},
        ).fetchone()
        if not existing:
            conn.execute(
                text(
                    "INSERT INTO feature_flags (key, display_name, enabled_globally) "
                    "VALUES (:key, :display, false)"
                ),
                {"key": key, "display": display},
            )

    # Lock down global defaults — plan limits control access per tenant
    gated = [
        "video_analysis", "batch_analysis", "custom_weights", "api_access",
        "export_excel", "transcript_analysis", "email_generation",
        "requisitions", "pipeline", "compare", "analytics", "ai_interviews",
        "white_label", "hm_workflow",
    ]
    for key in gated:
        conn.execute(
            text("UPDATE feature_flags SET enabled_globally = false WHERE key = :key"),
            {"key": key},
        )

    # Rename legacy plans
    conn.execute(text("UPDATE subscription_plans SET name = 'starter' WHERE name = 'free'"))
    conn.execute(text("UPDATE subscription_plans SET name = 'growth' WHERE name = 'pro'"))

    for plan_name, limits in PLAN_LIMITS.items():
        _upsert_plan(conn, plan_name, limits, PLAN_META[plan_name])

    # Deactivate any leftover legacy names
    conn.execute(
        text("UPDATE subscription_plans SET is_active = false WHERE name IN ('free', 'pro')")
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(text("UPDATE subscription_plans SET name = 'free' WHERE name = 'starter'"))
    conn.execute(text("UPDATE subscription_plans SET name = 'pro' WHERE name = 'growth'"))
    for key, _ in NEW_FLAGS:
        conn.execute(text("DELETE FROM feature_flags WHERE key = :key"), {"key": key})

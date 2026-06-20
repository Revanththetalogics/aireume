"""
Staging seed script — creates a ready-to-use tenant + admin user.
Run inside the backend container:
  docker exec -it staging-backend python -m app.backend.scripts.seed_staging
"""
import json
import sys
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger("seed_staging")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext

# ─── Config ──────────────────────────────────────────────────────────────────────
import os

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://aria_staging:Itslogical1.@postgres:5432/aria_staging_db",
)

TENANT_NAME = "ThetaLogics"
TENANT_SLUG = "thetalogics"
ADMIN_EMAIL = "revanth.a@thetalogics.com"
ADMIN_PASSWORD = "Admin@123"
ADMIN_ROLE = "admin"

# ─── Subscription plans ──────────────────────────────────────────────────────────
SUBSCRIPTION_PLANS = [
    {
        "name": "free",
        "display_name": "Free",
        "description": "Free tier",
        "limits": json.dumps({
            "analyses_per_month": 5,
            "batch_size": 3,
            "team_members": 1,
            "storage_gb": 1,
            "api_access": False,
            "custom_weights": False,
        }),
        "price_monthly": 0,
        "price_yearly": 0,
        "currency": "USD",
        "features": json.dumps(["5 analyses", "1 team member"]),
        "is_active": True,
        "sort_order": 1,
    },
    {
        "name": "pro",
        "display_name": "Pro",
        "description": "Pro tier",
        "limits": json.dumps({
            "analyses_per_month": 100,
            "batch_size": 20,
            "team_members": 5,
            "storage_gb": 10,
            "api_access": True,
            "custom_weights": True,
        }),
        "price_monthly": 4900,
        "price_yearly": 47000,
        "currency": "USD",
        "features": json.dumps(["100 analyses", "5 team members", "API access"]),
        "is_active": True,
        "sort_order": 2,
    },
    {
        "name": "enterprise",
        "display_name": "Enterprise",
        "description": "Enterprise tier",
        "limits": json.dumps({
            "analyses_per_month": -1,
            "batch_size": 100,
            "team_members": 25,
            "storage_gb": 100,
            "api_access": True,
            "custom_weights": True,
            "dedicated_support": True,
        }),
        "price_monthly": 19900,
        "price_yearly": 191000,
        "currency": "USD",
        "features": json.dumps(["Unlimited analyses", "25 team members", "Dedicated support"]),
        "is_active": True,
        "sort_order": 3,
    },
]


def main():
    # Import models after DB URL is set
    from app.backend.models.db_models import Tenant, User, SubscriptionPlan

    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    try:
        # ── 1. Subscription Plans ────────────────────────────────────────────
        existing_plans = db.query(SubscriptionPlan).count()
        if existing_plans == 0:
            log.info("Seeding subscription plans...")
            for plan_data in SUBSCRIPTION_PLANS:
                db.add(SubscriptionPlan(**plan_data))
            db.commit()
            log.info(f"  Created {len(SUBSCRIPTION_PLANS)} subscription plans")
        else:
            log.info(f"  Subscription plans already exist ({existing_plans} found), skipping")

        # ── 2. Tenant ────────────────────────────────────────────────────────
        tenant = db.query(Tenant).filter(Tenant.slug == TENANT_SLUG).first()
        if not tenant:
            log.info(f"Creating tenant '{TENANT_NAME}' (slug: {TENANT_SLUG})...")

            # Get the pro plan for assignment
            pro_plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.name == "pro").first()

            tenant = Tenant(
                name=TENANT_NAME,
                slug=TENANT_SLUG,
                plan_id=pro_plan.id if pro_plan else None,
                onboarding_completed=True,
                onboarding_completed_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
                subscription_status="active",
                metadata_json=json.dumps({
                    "industry": "technology",
                    "company_size": "11-50",
                }),
            )
            db.add(tenant)
            db.flush()
            log.info(f"  Tenant created (id={tenant.id})")
        else:
            log.info(f"  Tenant '{TENANT_SLUG}' already exists (id={tenant.id}), skipping")

        # ── 3. Admin User ────────────────────────────────────────────────────
        user = db.query(User).filter(User.email == ADMIN_EMAIL).first()
        if not user:
            log.info(f"Creating admin user '{ADMIN_EMAIL}'...")
            user = User(
                tenant_id=tenant.id,
                email=ADMIN_EMAIL,
                hashed_password=pwd_context.hash(ADMIN_PASSWORD),
                role=ADMIN_ROLE,
                email_verified=True,
            )
            db.add(user)
            db.commit()
            log.info(f"  Admin user created (id={user.id})")
        else:
            log.info(f"  User '{ADMIN_EMAIL}' already exists (id={user.id}), skipping")

        # ── 4. Summary ───────────────────────────────────────────────────────
        log.info("")
        log.info("=" * 60)
        log.info("  SEED COMPLETE")
        log.info("=" * 60)
        log.info(f"  Workspace : {TENANT_NAME} ({TENANT_SLUG})")
        log.info(f"  Email     : {ADMIN_EMAIL}")
        log.info(f"  Password  : {ADMIN_PASSWORD}")
        log.info(f"  Plan      : Pro")
        log.info(f"  Verified  : Yes")
        log.info("=" * 60)
        log.info("")

    except Exception as e:
        db.rollback()
        log.error(f"Seed failed: {e}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()

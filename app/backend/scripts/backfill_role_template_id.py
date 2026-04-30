"""
One-time script to backfill role_template_id on ScreeningResults
by matching jd_text against RoleTemplate entries.

Uses raw SQL to avoid ORM column-mismatch errors on DBs that
haven't run all Alembic migrations yet.

Usage:
    # Local dev (SQLite):
    set DATABASE_URL=sqlite:///app/backend/resume_screener.db
    python -m app.backend.scripts.backfill_role_template_id

    # Production (PostgreSQL — DATABASE_URL already set in environment):
    python -m app.backend.scripts.backfill_role_template_id
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from sqlalchemy import text, inspect
from app.backend.db.database import SessionLocal, engine


def backfill():
    # Pre-flight: verify the screening_results table has required columns
    inspector = inspect(engine)
    sr_columns = {col["name"] for col in inspector.get_columns("screening_results")}
    required = {"tenant_id", "role_template_id", "jd_text"}
    missing = required - sr_columns
    if missing:
        print(f"ERROR: screening_results table is missing columns: {missing}")
        print("Run Alembic migrations first:  alembic upgrade head")
        return

    # Also verify role_templates table exists and has jd_text
    rt_columns = {col["name"] for col in inspector.get_columns("role_templates")}
    if "jd_text" not in rt_columns:
        print("ERROR: role_templates table is missing 'jd_text' column")
        return

    session = SessionLocal()

    try:
        # Build template lookup using raw SQL: (tenant_id, jd_text_stripped) -> id
        template_rows = session.execute(
            text("SELECT id, tenant_id, jd_text FROM role_templates")
        ).fetchall()

        template_lookup = {}
        for row in template_rows:
            key = (row.tenant_id, row.jd_text.strip() if row.jd_text else "")
            if key not in template_lookup:
                template_lookup[key] = row.id

        # Find all results with NULL role_template_id using raw SQL
        null_results = session.execute(
            text(
                "SELECT id, tenant_id, jd_text "
                "FROM screening_results "
                "WHERE role_template_id IS NULL"
            )
        ).fetchall()

        print(f"Found {len(null_results)} results with NULL role_template_id")
        print(f"Found {len(template_rows)} role templates for matching")

        if not null_results:
            print("Nothing to backfill. Exiting.")
            return

        updated = 0
        no_jd_text = 0
        no_match = 0

        for result in null_results:
            jd_text = (result.jd_text or "").strip()
            if not jd_text:
                no_jd_text += 1
                continue

            # Try exact match first
            key = (result.tenant_id, jd_text)
            if key in template_lookup:
                session.execute(
                    text(
                        "UPDATE screening_results "
                        "SET role_template_id = :tid "
                        "WHERE id = :id"
                    ),
                    {"tid": template_lookup[key], "id": result.id},
                )
                updated += 1
                continue

            # Try prefix match (first 200 chars) — handles truncation differences
            matched = False
            for (tid, ttext), tmpl_id in template_lookup.items():
                if tid != result.tenant_id:
                    continue
                if not ttext:
                    continue
                if ttext[:200] == jd_text[:200]:
                    session.execute(
                        text(
                            "UPDATE screening_results "
                            "SET role_template_id = :tid "
                            "WHERE id = :id"
                        ),
                        {"tid": tmpl_id, "id": result.id},
                    )
                    updated += 1
                    matched = True
                    break

            if not matched:
                no_match += 1

        session.commit()
        print(f"\n=== Backfill Results ===")
        print(f"Updated:    {updated}")
        print(f"No JD text: {no_jd_text}")
        print(f"No match:   {no_match}")
        print(f"Total:      {len(null_results)}")

    except Exception as e:
        session.rollback()
        print(f"Error: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    backfill()

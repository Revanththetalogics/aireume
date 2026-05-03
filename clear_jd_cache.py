"""Clear JD cache so stale skill extractions are re-parsed with fixed code."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.backend.db.database import SessionLocal
from sqlalchemy import text

def main():
    db = SessionLocal()
    try:
        result = db.execute(text("DELETE FROM jd_cache"))
        db.commit()
        print(f"Cleared {result.rowcount} JD cache entries.")
        print("Next analysis will re-parse the JD with the fixed skill extractor.")
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    main()

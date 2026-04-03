from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

DATABASE_URL = os.getenv("DATABASE_URL", "./resume_screener.db")

# Normalize SQLite paths; leave PostgreSQL URLs unchanged
if not DATABASE_URL.startswith(("postgresql://", "postgres://")):
    if DATABASE_URL.startswith("./") or DATABASE_URL.startswith("/"):
        DATABASE_URL = f"sqlite:///{DATABASE_URL}"
    elif not DATABASE_URL.startswith("sqlite:///"):
        DATABASE_URL = f"sqlite:///{DATABASE_URL}"

# asyncpg-style postgres:// → postgresql:// for SQLAlchemy 2.x
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

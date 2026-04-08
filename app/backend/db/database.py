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

# Detect if using PostgreSQL
_is_postgres = DATABASE_URL.startswith("postgresql")

# Pool settings only for PostgreSQL (SQLite doesn't support pool settings)
_pool_kwargs = {}
if _is_postgres:
    _pool_kwargs = {
        "pool_size": 10,
        "max_overflow": 20,
        "pool_recycle": 3600,
    }

connect_args = {"check_same_thread": False} if not _is_postgres else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
    **_pool_kwargs
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()


def _create_db_engine():
    try:
        connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
        eng = create_engine(settings.database_url, pool_pre_ping=True, connect_args=connect_args)
        with eng.connect() as conn:
            pass
        return eng
    except Exception:
        fallback_url = "sqlite:///./renewai.db"
        return create_engine(fallback_url, connect_args={"check_same_thread": False})


engine = _create_db_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

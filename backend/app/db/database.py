from sqlalchemy import create_engine, inspect, text
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


def ensure_plants_schema() -> None:
    """Add capacity columns that later migrations introduced without dropping legacy ones."""
    inspector = inspect(engine)
    if "plants" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("plants")}
    with engine.begin() as connection:
        if "installed_capacity_mw" not in columns:
            connection.execute(text("ALTER TABLE plants ADD COLUMN installed_capacity_mw FLOAT"))
        if "export_limit_mw" not in columns:
            connection.execute(text("ALTER TABLE plants ADD COLUMN export_limit_mw FLOAT"))
        if "capacity_mw" not in columns:
            connection.execute(text("ALTER TABLE plants ADD COLUMN capacity_mw FLOAT"))
        connection.execute(
            text(
                "UPDATE plants SET installed_capacity_mw = capacity_mw "
                "WHERE installed_capacity_mw IS NULL AND capacity_mw IS NOT NULL"
            )
        )
        connection.execute(
            text(
                "UPDATE plants SET capacity_mw = installed_capacity_mw "
                "WHERE capacity_mw IS NULL AND installed_capacity_mw IS NOT NULL"
            )
        )


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

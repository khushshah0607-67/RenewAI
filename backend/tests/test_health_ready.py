from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.db.database import Base, get_db
from app.main import app

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def override_get_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides.clear()
app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def test_health_returns_200():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_does_not_require_database_access():
    response = client.get("/health")
    assert response.status_code == 200
    assert "database" not in response.text.lower()


def test_ready_returns_200_when_database_is_available():
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_ready_returns_503_when_database_is_unavailable(monkeypatch):
    def fail_db(*args, **kwargs):
        raise RuntimeError("database unavailable")

    monkeypatch.setattr("sqlalchemy.orm.Session.execute", fail_db)
    response = client.get("/ready")

    assert response.status_code == 503
    payload = response.json()
    assert payload["status"] == "error"
    assert payload["error"]["code"] == "SERVICE_NOT_READY"
    assert payload["error"]["message"] == "Database is unavailable"
    assert "database unavailable" not in response.text.lower()
    assert "sqlite" not in response.text.lower()


def test_health_and_ready_do_not_expose_secret_details():
    settings = get_settings()
    secret_text = settings.database_url
    health_response = client.get("/health")
    ready_response = client.get("/ready")

    assert secret_text not in health_response.text
    assert secret_text not in ready_response.text
    assert "password" not in ready_response.text.lower()

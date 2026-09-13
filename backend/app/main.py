import sys
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.api.financial import router as financial_router
from app.api.explanation import router as explanation_router
from app.api.forecast import router as forecast_router
from app.api.plants import router as plants_router
from app.api.recommendation import router as recommendation_router
from app.api.risk import router as risk_router
from app.api.simulation import router as simulation_router
from app.api.weather import router as weather_router
from app.core.config import get_settings
from app.core.errors import AppException, error_response, normalize_http_exception
from app.db.database import get_db

settings = get_settings()

from contextlib import asynccontextmanager
import math
from datetime import datetime, timedelta, timezone

from app.db.database import Base, SessionLocal, engine
from app.db.models.historical_generation import HistoricalGeneration
from app.db.models.plant import Plant


def init_db_and_seed():
    try:
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        try:
            if db.query(Plant).count() == 0:
                plant1 = Plant(
                    name="Bhadla Solar Park",
                    plant_type="SOLAR",
                    latitude=27.53,
                    longitude=71.91,
                    installed_capacity_mw=500.0,
                    export_limit_mw=450.0,
                    timezone="Asia/Kolkata",
                )
                plant2 = Plant(
                    name="Muppandal Wind Farm",
                    plant_type="WIND",
                    latitude=8.26,
                    longitude=77.53,
                    installed_capacity_mw=300.0,
                    export_limit_mw=280.0,
                    timezone="Asia/Kolkata",
                )
                db.add_all([plant1, plant2])
                db.commit()
                db.refresh(plant1)
                db.refresh(plant2)

                now = datetime.now(timezone.utc)
                start_time = now - timedelta(hours=100)
                records = []
                for i in range(100):
                    ts = start_time + timedelta(hours=i)
                    hour = ts.hour
                    if 6 <= hour <= 18:
                        sin_val = math.sin((hour - 6) / 12.0 * math.pi)
                        gen_mw = round(sin_val * 420.0 + (i % 5) * 2.0, 2)
                    else:
                        gen_mw = 0.0
                    records.append(
                        HistoricalGeneration(plant_id=plant1.id, timestamp=ts, generation_mw=gen_mw)
                    )
                db.add_all(records)
                db.commit()
        finally:
            db.close()
    except Exception:
        pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db_and_seed()
    yield


app = FastAPI(title="RenewAI API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(plants_router, prefix="/api")
app.include_router(weather_router, prefix="/api")
app.include_router(forecast_router, prefix="/api")
app.include_router(risk_router, prefix="/api")
app.include_router(financial_router, prefix="/api")
app.include_router(recommendation_router, prefix="/api")
app.include_router(explanation_router, prefix="/api")
app.include_router(simulation_router, prefix="/api")


@app.exception_handler(AppException)
async def app_exception_handler(_: Request, exc: AppException) -> JSONResponse:
    return error_response(exc.status_code, exc.code, exc.message, exc.details)


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    return normalize_http_exception(exc)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    details = [
        {"loc": list(error.get("loc", [])), "msg": error.get("msg"), "type": error.get("type")}
        for error in exc.errors()
    ]
    return error_response(
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        "VALIDATION_ERROR",
        "Request validation failed",
        details,
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    return error_response(
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        "INTERNAL_SERVER_ERROR",
        "An unexpected server error occurred",
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
def ready(db: Session = Depends(get_db)) -> dict[str, str]:
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception as exc:  # pragma: no cover - runtime dependency check
        raise AppException(
            status_code=503,
            code="SERVICE_NOT_READY",
            message="Database is unavailable",
        ) from exc


@app.get("/db-health")
def db_health(db: Session = Depends(get_db)) -> dict[str, str]:
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as exc:  # pragma: no cover - runtime dependency check
        raise HTTPException(
            status_code=503,
            detail=f"Database connection failed: {exc}",
        ) from exc

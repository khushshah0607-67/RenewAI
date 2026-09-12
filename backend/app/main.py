from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

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

app = FastAPI(title="RenewAI API")
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

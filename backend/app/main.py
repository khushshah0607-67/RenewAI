from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.financial import router as financial_router
from app.api.explanation import router as explanation_router
from app.api.financial import router as financial_router
from app.api.forecast import router as forecast_router
from app.api.plants import router as plants_router
from app.api.recommendation import router as recommendation_router
from app.api.risk import router as risk_router
from app.api.simulation import router as simulation_router
from app.api.weather import router as weather_router
from app.db.database import get_db

app = FastAPI(title="RenewAI API")
app.include_router(plants_router, prefix="/api")
app.include_router(weather_router, prefix="/api")
app.include_router(forecast_router, prefix="/api")
app.include_router(risk_router, prefix="/api")
app.include_router(financial_router, prefix="/api")
app.include_router(recommendation_router, prefix="/api")
app.include_router(explanation_router, prefix="/api")
app.include_router(simulation_router, prefix="/api")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


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

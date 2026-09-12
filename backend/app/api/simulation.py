from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.simulation import SimulationResponse, SimulationScenario
from app.services.plant_service import PlantService
from app.services.simulation.what_if_simulation_service import SimulationControls, WhatIfSimulationService

router = APIRouter(prefix="/plants", tags=["simulation"])


@router.post("/{plant_id}/simulation", response_model=SimulationResponse)
def simulate_plant_scenario(
    plant_id: int,
    scenario: SimulationScenario,
    db: Session = Depends(get_db),
) -> dict:
    plant_service = PlantService(db)
    plant = plant_service.get_plant(plant_id)
    if plant is None:
        raise HTTPException(status_code=404, detail="Plant not found")

    service = WhatIfSimulationService(db)
    controls = SimulationControls(
        battery_reserve_target=scenario.battery_reserve_target,
        backup_availability=scenario.backup_availability,
        flexible_load_availability=scenario.flexible_load_availability,
        curtailment_allowance=scenario.curtailment_allowance,
        energy_price_inr_per_mwh=scenario.energy_price_inr_per_mwh,
    )
    return service.simulate(plant, controls)

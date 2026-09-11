from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.ml.predict_forecaster import FreightForecaster

router = APIRouter()
forecaster = FreightForecaster()


class ForecastRequest(BaseModel):
    current_rate: float = Field(default=22.50, gt=0)
    bunker_fuel: float = Field(default=620.00, gt=0)
    cargo_demand: float = Field(default=105.0, gt=0)
    vessel_avail: float = Field(default=92.0, gt=0)
    congestion_days: float = Field(default=2.5, ge=0)
    historical_rates: Optional[List[float]] = None


@router.post("/predict")
def predict_freight_rate(payload: ForecastRequest):
    try:
        return forecaster.predict_30d_rate(
            current_rate=payload.current_rate,
            bunker_fuel=payload.bunker_fuel,
            cargo_demand=payload.cargo_demand,
            vessel_avail=payload.vessel_avail,
            congestion_days=payload.congestion_days,
            historical_rates=payload.historical_rates,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

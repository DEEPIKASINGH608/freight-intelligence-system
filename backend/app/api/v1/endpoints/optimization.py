from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any

from app.optimization.vessel_solver import VesselOptimizationSolver
from app.optimization.procurement_solver import optimize_procurement


router = APIRouter()

# Create the vessel optimization solver once and reuse it
vessel_solver = VesselOptimizationSolver()


# VESSEL OPTIMIZATION

class VesselOptimizationRequest(BaseModel):
    """
    Request model for vessel chartering optimization.
    """

    cargo_required_tons: float = 75000.0

    available_vessels: List[Dict[str, Any]] = Field(
        default_factory=list
    )

    route_distance_nm: float = 3850.0

    fuel_price_usd_ton: float = 620.0

    delivery_deadline_days: float = 30.0

    port_congestion_days: float = 2.5

    # Port and cargo constraints
    port_name: str = "Paradip"

    cargo_type: str = "iron_ore"


@router.post("/vessels")
def optimize_vessels(payload: VesselOptimizationRequest):
    """
    Optimize vessel selection using:

    1. Port compatibility constraints
    2. Cargo capacity
    3. Delivery deadline
    4. Voyage cost
    5. OR-Tools MILP optimization

    The vessel solver internally calls the port constraint
    validator before optimization.
    """

    try:
        result = vessel_solver.solve_vessel_chartering(
            cargo_required_tons=payload.cargo_required_tons,
            available_vessels=payload.available_vessels,
            route_distance_nm=payload.route_distance_nm,
            fuel_price_usd_ton=payload.fuel_price_usd_ton,
            delivery_deadline_days=payload.delivery_deadline_days,
            port_congestion_days=payload.port_congestion_days,
            port_name=payload.port_name,
            cargo_type=payload.cargo_type,
        )

        return result

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Vessel optimization failed: {str(e)}"
        )


# PROCUREMENT OPTIMIZATION

class ProcurementOptimizationRequest(BaseModel):
    """
    Request model for bulk cargo procurement optimization.
    """

    target_demand_tons: float = 75000.0

    suppliers: List[Dict[str, Any]] = Field(
        default_factory=list
    )


@router.post("/procurement")
def optimize_procurement_endpoint(
    payload: ProcurementOptimizationRequest
):
    """
    Optimize procurement allocation across suppliers.
    """

    try:
        result = optimize_procurement(
            target_demand_tons=payload.target_demand_tons,
            suppliers=payload.suppliers,
        )

        return result

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Procurement optimization failed: {str(e)}"
        )
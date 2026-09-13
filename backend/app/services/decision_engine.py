from typing import Dict, Any

import json
import os

from app.ml.predict_forecaster import FreightForecaster
from app.ml.risk_engine import RiskEvaluator
from app.optimization.vessel_solver import VesselOptimizationSolver
from app.optimization.procurement_solver import optimize_procurement


def load_vessel_fleet():
    """
    Load the available vessel fleet from the project's data directory.
    """
    file_path = os.path.join(
        os.path.dirname(__file__),
        "../data/vessel_fleet.json"
    )

    file_path = os.path.abspath(file_path)

    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    return []


class DecisionEngine:
    """
    Central decision engine.

    Combines:
    1. ML freight forecasting
    2. Route risk evaluation
    3. Vessel charter optimization
    4. Procurement optimization
    5. Financial scenario analysis
    """

    def __init__(self):
        """
        Initialize the real decision-system components once.
        """
        self.forecaster = FreightForecaster()
        self.risk_evaluator = RiskEvaluator()
        self.vessel_solver = VesselOptimizationSolver()

    def synthesize_decision(
        self,
        payload: Any
    ) -> Dict[str, Any]:

        try:
            # 1. STANDARDIZE PAYLOAD
        # ============================================================

            if isinstance(payload, dict):
                data = payload

            elif hasattr(payload, "model_dump"):
                data = payload.model_dump()

            elif hasattr(payload, "dict"):
                data = payload.dict()

            else:
                data = dict(payload)

            # 2. EXTRACT INPUTS

            cargo_qty = float(data.get("cargo_qty", 75000))
            current_rate = float(data.get("current_rate", 22.50))
            fuel_price = float(data.get("bunker_fuel", 620.0))
            cargo_demand_index = float(data.get("cargo_demand", 105.0))
            vessel_availability_index = float(data.get("vessel_availability", 92.0))
            congestion_days = float(data.get("congestion_days", 2.5))
            weather_risk = float(data.get("weather_index", 1.1))
            destination_port = data.get("destination", "Paradip")
            cargo_type = data.get("cargo_type", "iron_ore")
            delivery_deadline_days = float(data.get("delivery_deadline_days", 25.0))
            route_distance_nm = float(data.get("distance_nm", 3850.0))
            historical_rates = data.get("historical_rates", [])
            # 3. REAL ML FREIGHT FORECAST

            forecast_result = self.forecaster.predict_30d_rate(
                current_rate=current_rate,
                bunker_fuel=fuel_price,
                cargo_demand=cargo_demand_index,
                vessel_avail=vessel_availability_index,
                congestion_days=congestion_days,
                historical_rates=historical_rates
            )

            forecasted_rate = float(
                forecast_result[
                    "predicted_30d_rate_usd"
                ]
            )

            rate_delta_pct = float(
                forecast_result[
                    "percentage_change"
                ]
            )

            # 4. REAL ROUTE RISK EVALUATION

            risk_result = (
                self.risk_evaluator.evaluate_route_risk(
                    port_congestion_days=congestion_days,
                    weather_risk_index=weather_risk,
                    vessel_availability_index=(
                        vessel_availability_index
                    ),
                    distance_nautical_miles=(
                        route_distance_nm
                    )
                )
            )

            risk_score = float(
                risk_result["risk_score"]
            )

            risk_level = risk_result[
                "risk_level"
            ]

            # 5. VESSEL CHARTER OPTIMIZATION

            fleet_dataset = data.get(
                "available_vessels",
                load_vessel_fleet()
            )

            vessel_optimization_result = (
                self.vessel_solver.solve_vessel_chartering(
                    cargo_required_tons=cargo_qty,
                    available_vessels=fleet_dataset,
                    route_distance_nm=route_distance_nm,
                    fuel_price_usd_ton=fuel_price,
                    delivery_deadline_days=(
                        delivery_deadline_days
                    ),
                    port_congestion_days=congestion_days,
                    port_name=destination_port,
                    cargo_type=cargo_type
                )
            )

            # 6. PROCUREMENT OPTIMIZATION

            suppliers = data.get(
                "suppliers",
                []
            )

            if suppliers:
                procurement_result = optimize_procurement(
                    target_demand_tons=cargo_qty,
                    suppliers=suppliers
                )

            else:
                procurement_result = {
                    "status": "NOT_RUN",
                    "message": (
                        "No supplier data was provided "
                        "for procurement optimization."
                    ),
                    "allocations": []
                }

            # 7. FINANCIAL SCENARIO ANALYSIS

            spot_total_usd = (
                cargo_qty *
                current_rate
            )

            forecast_total_usd = (
                cargo_qty *
                forecasted_rate
            )

            # Existing project conversion assumption.
            # Keep this centralized so it can later be
            # replaced by a live FX input.

            usd_to_inr = 83.0

            scenario_book_now = round(
                (
                    spot_total_usd *
                    usd_to_inr
                ) / 10_000_000,
                2
            )

            scenario_wait_30d = round(
                (
                    forecast_total_usd *
                    usd_to_inr
                ) / 10_000_000,
                2
            )

            exposure_delta = round(
                scenario_wait_30d -
                scenario_book_now,
                2
            )
# 8. RISK-AWARE DECISION LOGIC

            # Strong forecast increase:
            # LOW risk    -> CHARTERNOW
            # MEDIUM risk -> WATCH unless increase is exceptionally strong
            # HIGH risk   -> WATCH
            #
            # Forecast decrease -> WAIT
            # Otherwise -> WATCH

            if rate_delta_pct >= 5.0:

                if risk_level == "HIGH":

                    recommended_action = "WATCH"

                    risk_adjustment = (
                        "Chartering signal overridden by high route risk."
                    )

                elif risk_level == "MEDIUM":

                    if rate_delta_pct >= 10.0:

                        recommended_action = "CHARTERNOW"

                        risk_adjustment = (
                            "Medium route risk accepted because the "
                            "forecast increase is exceptionally strong."
                        )

                    else:

                        recommended_action = "WATCH"

                        risk_adjustment = (
                            "Chartering signal moderated because "
                            "route risk is MEDIUM."
                        )

                else:

                    recommended_action = "CHARTERNOW"

                    risk_adjustment = (
                        "Low route risk supports immediate chartering."
                    )

            elif rate_delta_pct <= -5.0:

                recommended_action = "WAIT"

                risk_adjustment = (
                    "Forecast indicates declining freight rates; "
                    "waiting is preferred."
                )

            else:

                recommended_action = "WATCH"

                risk_adjustment = (
                    "Forecast movement is not strong enough "
                    "for immediate action."
                )

            # Vessel feasibility override

            if (
                vessel_optimization_result.get(
                    "status"
                ) == "INFEASIBLE"
            ):

                recommended_action = "WATCH"

                risk_adjustment = (
                    "Immediate chartering is blocked because "
                    "no feasible vessel combination satisfies "
                    "the current operational constraints."
                )

            # 9. DECISION REASONING

            reasons = []

            # Forecast reason

            if rate_delta_pct >= 5.0:

                reasons.append(
                    f"Freight is forecast to increase by "
                    f"{rate_delta_pct:.1f}% over 30 days."
                )

            elif rate_delta_pct <= -5.0:

                reasons.append(
                    f"Freight is forecast to decrease by "
                    f"{abs(rate_delta_pct):.1f}% over 30 days."
                )

            else:

                reasons.append(
                    "Forecasted freight movement is within "
                    "the watch range."
                )

            # Risk reason

            reasons.append(
                f"Route risk is {risk_level} "
                f"with a score of "
                f"{risk_score:.1f}/100."
            )

            # Risk adjustment reason

            reasons.append(
                risk_adjustment
            )

            # Risk drivers

            risk_drivers = risk_result.get(
                "key_drivers",
                []
            )

            if risk_drivers:

                reasons.append(
                    "Risk drivers: " +
                    "; ".join(risk_drivers)
                )

            # Vessel reason

            vessel_status = (
                vessel_optimization_result.get(
                    "status"
                )
            )

            if vessel_status == "OPTIMAL":

                reasons.append(
                    "At least one vessel satisfies the "
                    "port, capacity and delivery constraints."
                )

            elif vessel_status == "INFEASIBLE":

                # Do not repeat the exact same sentence when
                # it is already the risk adjustment.

                if risk_adjustment != (
                    "Immediate chartering is blocked because "
                    "no feasible vessel combination satisfies "
                    "the current operational constraints."
                ):

                    reasons.append(
                        "No feasible vessel combination satisfies "
                        "the current operational constraints."
                    )

            else:

                reasons.append(
                    "Vessel optimization did not return "
                    "an optimal solution."
                )

            # Procurement reason

            procurement_status = (
                procurement_result.get("status")
            )

            if procurement_status == "success":

                reasons.append(
                    "Procurement optimization successfully "
                    "allocated the required cargo across "
                    "available suppliers."
                )

            elif procurement_status == "infeasible":

                shortfall = procurement_result.get(
                    "shortfall_tons",
                    0
                )

                reasons.append(
                    f"Procurement is infeasible because "
                    f"supplier availability leaves a "
                    f"{shortfall:,.0f} MT cargo shortfall."
                )

            elif procurement_status == "NOT_RUN":

                reasons.append(
                    "Procurement optimization was not run "
                    "because supplier data was not provided."
                )

            # 10. BUILD FINAL DECISION RESPONSE

            return {

                # PRIMARY DECISION

                "recommended_action":
                    recommended_action,

                "reasoning":
                    " ".join(reasons),

                "risk_adjustment":
                    risk_adjustment,

                # DECISION FACTORS

                "decision_factors": {

                    "forecast_rate_change_pct":
                        rate_delta_pct,

                    "risk_score":
                        risk_score,

                    "risk_level":
                        risk_level,

                    "risk_adjustment":
                        risk_adjustment,

                    "risk_drivers":
                        risk_drivers,

                    "vessel_optimization_status":
                        vessel_status,

                    "procurement_optimization_status":
                        procurement_status
                },

                # REAL ML FORECAST MODULE

                "forecast_module":
                    forecast_result,

                # REAL RISK MODULE

                "risk_module":
                    risk_result,

                # FINANCIAL SCENARIOS

                "scenario_analysis": {

                    "scenario_book_now_inr_cr":
                        scenario_book_now,

                    "scenario_wait_30d_inr_cr":
                        scenario_wait_30d,

                    "exposure_delta_inr_cr":
                        exposure_delta,

                    "basis":
                        "Actual 30-Day ML Forecast"
                },

                # FINANCIAL SUMMARY

                "financial_summary": {

                    "current_spot_rate_usd":
                        current_rate,

                    "forecast_rate_usd_ton":
                        forecasted_rate,

                    "rate_change_pct":
                        rate_delta_pct,

                    "cargo_quantity_tons":
                        cargo_qty,

                    "spot_total_usd":
                        round(
                            spot_total_usd,
                            2
                        ),

                    "forecast_total_usd":
                        round(
                            forecast_total_usd,
                            2
                        ),

                    "usd_to_inr_assumption":
                        usd_to_inr
                },

                # PORT / ROUTE MODULE

                "port_constraints_module": {

                    "origin":
                        data.get(
                            "origin",
                            "Australia (Port Hedland)"
                        ),

                    "destination":
                        destination_port,

                    "cargo_type":
                        cargo_type,

                    "route_distance_nm":
                        route_distance_nm,

                    "delivery_deadline_days":
                        delivery_deadline_days,

                    "port_congestion_days":
                        congestion_days
                },

                # CHARTER OPTIMIZATION MODULE

                "charter_optimization_module":
                    vessel_optimization_result,

                # PROCUREMENT OPTIMIZATION MODULE

                "procurement_optimization":
                    procurement_result
            }

        except Exception as e:

            raise RuntimeError(
                "Decision Engine evaluation failure: "
                f"{str(e)}"
            )

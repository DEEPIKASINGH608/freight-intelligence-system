from ortools.linear_solver import pywraplp

from app.optimization.port_constraints import (
    validate_vessel_port_compatibility,
    get_port_constraints,
)


class VesselOptimizationSolver:
    """
    Vessel chartering optimization engine.

    Optimization flow:

        Fleet
          |
          v
        Availability
          |
          v
        Port Compatibility
          |
          v
        Delivery Deadline
          |
          v
        Cargo Capacity
          |
          v
        Voyage Cost
          |
          v
        OR-Tools MILP
          |
          v
        Best Feasible Vessel Combination

    Important:
    - Port compatibility is a hard constraint.
    - Availability ETA is a hard constraint.
    - Delivery deadline is a hard constraint.
    - Vessel position is reported for decision transparency.
    - No artificial repositioning distance is assumed because
      the fleet data does not contain vessel-to-port distances.
    """

    def __init__(self):
        pass

    # ================================================================
    # HELPER: STANDARD INVALID RESPONSE
    # ================================================================

    def _invalid_response(
        self,
        message: str,
        cargo_required_tons: float,
    ) -> dict:

        return {
            "status": "INVALID_INPUT",
            "message": message,
            "selected_vessels": [],
            "rejected_vessels": [],
            "total_selected_capacity_tons": 0.0,
            "cargo_required_tons": cargo_required_tons,
            "capacity_utilization_pct": 0.0,
            "total_cost_usd": 0.0,
            "total_cost_inr_cr": 0.0,
            "max_delivery_days": None,
            "shortfall_tons": max(
                0.0,
                cargo_required_tons
            ),
        }

    # ================================================================
    # MAIN OPTIMIZATION FUNCTION
    # ================================================================

    def solve_vessel_chartering(
        self,
        cargo_required_tons: float,
        available_vessels: list,
        route_distance_nm: float,
        fuel_price_usd_ton: float,
        delivery_deadline_days: float,
        port_congestion_days: float = 2.0,
        port_name: str = "Paradip",
        cargo_type: str = "iron_ore",
    ) -> dict:

        # ============================================================
        # 1. INPUT VALIDATION
        # ============================================================

        if cargo_required_tons <= 0:
            return self._invalid_response(
                "Cargo required must be greater than zero.",
                cargo_required_tons,
            )

        if route_distance_nm <= 0:
            return self._invalid_response(
                "Route distance must be greater than zero.",
                cargo_required_tons,
            )

        if delivery_deadline_days <= 0:
            return self._invalid_response(
                "Delivery deadline must be greater than zero.",
                cargo_required_tons,
            )

        if fuel_price_usd_ton < 0:
            return self._invalid_response(
                "Fuel price cannot be negative.",
                cargo_required_tons,
            )

        if port_congestion_days < 0:
            return self._invalid_response(
                "Port congestion days cannot be negative.",
                cargo_required_tons,
            )

        if not available_vessels:
            return {
                "status": "INFEASIBLE",
                "message": "No vessel fleet data was provided.",
                "selected_vessels": [],
                "rejected_vessels": [],
                "total_selected_capacity_tons": 0.0,
                "cargo_required_tons": cargo_required_tons,
                "capacity_utilization_pct": 0.0,
                "total_cost_usd": 0.0,
                "total_cost_inr_cr": 0.0,
                "max_delivery_days": None,
                "shortfall_tons": cargo_required_tons,
            }

        # ============================================================
        # 2. VALIDATE DESTINATION PORT
        # ============================================================

        port_constraints = get_port_constraints(port_name)

        if port_constraints.get("status") == "UNKNOWN_PORT":

            return {
                "status": "INFEASIBLE",
                "message": port_constraints.get(
                    "message",
                    f"Unknown port: {port_name}",
                ),
                "selected_vessels": [],
                "rejected_vessels": [
                    {
                        "id": vessel.get("id"),
                        "name": vessel.get(
                            "name",
                            "Unknown Vessel",
                        ),
                        "rejection_stage": "PORT_CONSTRAINT",
                        "reason": (
                            f"Port '{port_name}' has no "
                            "available constraint data."
                        ),
                    }
                    for vessel in available_vessels
                ],
                "port_constraints": port_constraints,
                "total_selected_capacity_tons": 0.0,
                "cargo_required_tons": cargo_required_tons,
                "capacity_utilization_pct": 0.0,
                "total_cost_usd": 0.0,
                "total_cost_inr_cr": 0.0,
                "max_delivery_days": None,
                "shortfall_tons": cargo_required_tons,
            }

        # ============================================================
        # 3. INITIALIZE FILTERING
        # ============================================================

        rejected_vessels = []
        feasible_vessels = []

        # ============================================================
        # 4. AVAILABILITY + PORT COMPATIBILITY FILTER
        # ============================================================

        for vessel in available_vessels:

            vessel_id = vessel.get("id")
            vessel_name = vessel.get(
                "name",
                "Unknown Vessel",
            )

            current_position = vessel.get(
                "current_position",
                "Unknown",
            )

            eta_available_days = float(
                vessel.get(
                    "eta_available_days",
                    0,
                )
            )

            # --------------------------------------------------------
            # Validate availability ETA
            # --------------------------------------------------------

            if eta_available_days < 0:

                rejected_vessels.append(
                    {
                        "id": vessel_id,
                        "name": vessel_name,
                        "rejection_stage": "AVAILABILITY",
                        "reason": "Invalid availability ETA",
                        "current_position": current_position,
                        "eta_available_days": eta_available_days,
                        "violations": [
                            "eta_available_days cannot be negative."
                        ],
                    }
                )

                continue

            # --------------------------------------------------------
            # Port compatibility
            # --------------------------------------------------------

            is_compatible, violations = (
                validate_vessel_port_compatibility(
                    vessel=vessel,
                    port_name=port_name,
                    cargo_type=cargo_type,
                )
            )

            if not is_compatible:

                rejected_vessels.append(
                    {
                        "id": vessel_id,
                        "name": vessel_name,
                        "rejection_stage": "PORT_CONSTRAINT",
                        "reason": "Port incompatible",
                        "current_position": current_position,
                        "eta_available_days": eta_available_days,
                        "violations": violations,
                    }
                )

                continue

            # --------------------------------------------------------
            # Vessel is currently available from the fleet perspective
            # --------------------------------------------------------

            feasible_vessels.append(
                vessel
            )

        # ============================================================
        # 5. CHECK PORT-COMPATIBLE VESSELS
        # ============================================================

        if not feasible_vessels:

            return {
                "status": "INFEASIBLE",
                "message": (
                    "No vessels satisfy the destination "
                    "port constraints."
                ),
                "selected_vessels": [],
                "rejected_vessels": rejected_vessels,
                "port_constraints": port_constraints,
                "total_selected_capacity_tons": 0.0,
                "cargo_required_tons": cargo_required_tons,
                "capacity_utilization_pct": 0.0,
                "total_cost_usd": 0.0,
                "total_cost_inr_cr": 0.0,
                "max_delivery_days": None,
                "shortfall_tons": cargo_required_tons,
            }

        # ============================================================
        # 6. CREATE OR-TOOLS SCIP SOLVER
        # ============================================================

        solver = pywraplp.Solver.CreateSolver(
            "SCIP"
        )

        if not solver:

            raise Exception(
                "Google OR-Tools SCIP solver unavailable."
            )

        num_vessels = len(
            feasible_vessels
        )

        x = {}

        vessel_costs = []

        vessel_total_days = []

        vessel_transit_days = []

        vessel_round_trip_days = []

        # ============================================================
        # 7. CALCULATE VOYAGE COST + DEADLINE
        # ============================================================

        for i, vessel in enumerate(
            feasible_vessels
        ):

            vessel_id = vessel.get("id")

            vessel_name = vessel.get(
                "name",
                "Unknown Vessel",
            )

            current_position = vessel.get(
                "current_position",
                "Unknown",
            )

            eta_available_days = float(
                vessel.get(
                    "eta_available_days",
                    0,
                )
            )

            capacity_dwt = float(
                vessel.get(
                    "capacity_dwt",
                    0,
                )
            )

            speed_knots = float(
                vessel.get(
                    "speed_knots",
                    14.0,
                )
            )

            daily_charter_rate = float(
                vessel.get(
                    "daily_charter_rate",
                    0.0,
                )
            )

            fuel_consumption = float(
                vessel.get(
                    "fuel_consumption_ton_day",
                    0.0,
                )
            )

            # --------------------------------------------------------
            # Validate vessel parameters
            # --------------------------------------------------------

            if capacity_dwt <= 0:

                rejected_vessels.append(
                    {
                        "id": vessel_id,
                        "name": vessel_name,
                        "rejection_stage": "VESSEL_DATA",
                        "reason": "Invalid vessel capacity",
                        "violations": [
                            "capacity_dwt must be greater than zero."
                        ],
                    }
                )

                x_index = i

                # Force this vessel out of the optimization.
                x[x_index] = solver.BoolVar(
                    f"charter_vessel_{x_index}"
                )

                solver.Add(
                    x[x_index] == 0
                )

                vessel_costs.append(
                    0.0
                )

                vessel_total_days.append(
                    float("inf")
                )

                vessel_transit_days.append(
                    float("inf")
                )

                vessel_round_trip_days.append(
                    float("inf")
                )

                continue

            if speed_knots <= 0:
                speed_knots = 1.0

            if daily_charter_rate < 0:
                daily_charter_rate = 0.0

            if fuel_consumption < 0:
                fuel_consumption = 0.0

            # --------------------------------------------------------
            # Create binary decision variable
            # --------------------------------------------------------

            x[i] = solver.BoolVar(
                f"charter_vessel_{i}"
            )

            # --------------------------------------------------------
            # Sailing time
            # --------------------------------------------------------

            transit_hours = (
                route_distance_nm
                /
                speed_knots
            )

            transit_days = (
                transit_hours
                /
                24.0
            )

            round_trip_days = (
                transit_days
                *
                2.0
            )

            # --------------------------------------------------------
            # Port operations
            # --------------------------------------------------------

            port_operation_days = 3.0

            # --------------------------------------------------------
            # Total operational duration
            #
            # Availability ETA is included because a vessel that
            # becomes available later cannot be considered instantly
            # ready for the voyage.
            # --------------------------------------------------------

            total_days = (
                eta_available_days
                +
                round_trip_days
                +
                port_operation_days
                +
                port_congestion_days
            )

            vessel_transit_days.append(
                transit_days
            )

            vessel_round_trip_days.append(
                round_trip_days
            )

            vessel_total_days.append(
                total_days
            )

            # --------------------------------------------------------
            # Deadline constraint
            # --------------------------------------------------------

            if (
                total_days
                >
                delivery_deadline_days
            ):

                solver.Add(
                    x[i] == 0
                )

                rejected_vessels.append(
                    {
                        "id": vessel_id,
                        "name": vessel_name,
                        "rejection_stage": "DELIVERY_DEADLINE",
                        "reason": (
                            "Availability plus voyage duration "
                            "exceeds delivery deadline."
                        ),
                        "current_position": current_position,
                        "eta_available_days": eta_available_days,
                        "estimated_voyage_days": round(
                            total_days,
                            1,
                        ),
                        "deadline_days": delivery_deadline_days,
                        "violations": [
                            (
                                f"Estimated total duration "
                                f"({total_days:.1f} days) exceeds "
                                f"delivery deadline "
                                f"({delivery_deadline_days:.1f} days)."
                            )
                        ],
                    }
                )

            # --------------------------------------------------------
            # Charter cost
            # --------------------------------------------------------

            charter_cost = (
                total_days
                *
                daily_charter_rate
            )

            # --------------------------------------------------------
            # Fuel cost
            #
            # Fuel consumption is applied to round-trip sailing time.
            # Availability/waiting time is not treated as sailing fuel.
            # --------------------------------------------------------

            fuel_cost = (
                round_trip_days
                *
                fuel_consumption
                *
                fuel_price_usd_ton
            )

            total_vessel_cost = (
                charter_cost
                +
                fuel_cost
            )

            vessel_costs.append(
                total_vessel_cost
            )

        # ============================================================
        # 8. CAPACITY CONSTRAINT
        # ============================================================

        capacity_terms = []

        for i in range(
            num_vessels
        ):

            capacity = float(
                feasible_vessels[i].get(
                    "capacity_dwt",
                    0,
                )
            )

            capacity_terms.append(
                x[i] * capacity
            )

        solver.Add(
            solver.Sum(
                capacity_terms
            )
            >=
            cargo_required_tons
        )

        # ============================================================
        # 9. MINIMUM COST OBJECTIVE
        # ============================================================

        objective = solver.Objective()

        for i in range(
            num_vessels
        ):

            objective.SetCoefficient(
                x[i],
                vessel_costs[i],
            )

        objective.SetMinimization()

        # ============================================================
        # 10. SOLVE MILP
        # ============================================================

        status = solver.Solve()

        # ============================================================
        # 11. OPTIMAL / FEASIBLE SOLUTION
        # ============================================================

        if (
            status
            ==
            pywraplp.Solver.OPTIMAL
            or
            status
            ==
            pywraplp.Solver.FEASIBLE
        ):

            selected_vessels = []

            total_capacity = 0.0

            total_cost_usd = 0.0

            max_delivery_days = 0.0

            # --------------------------------------------------------
            # Read selected vessels
            # --------------------------------------------------------

            for i in range(
                num_vessels
            ):

                if (
                    x[i].solution_value()
                    >
                    0.5
                ):

                    vessel = (
                        feasible_vessels[i]
                    )

                    selected_vessels.append(
                        {
                            "id": vessel.get(
                                "id"
                            ),

                            "name": vessel.get(
                                "name",
                                "Unknown Vessel",
                            ),

                            "vessel_class": vessel.get(
                                "vessel_class",
                                vessel.get(
                                    "vessel_type",
                                    "Unknown",
                                ),
                            ),

                            "capacity_dwt": vessel.get(
                                "capacity_dwt",
                                0,
                            ),

                            "loa_m": vessel.get(
                                "loa_m",
                                0,
                            ),

                            "beam_m": vessel.get(
                                "beam_m",
                                0,
                            ),

                            "draft_m": vessel.get(
                                "draft_m",
                                0,
                            ),

                            "speed_knots": vessel.get(
                                "speed_knots",
                                0,
                            ),

                            "fuel_consumption_ton_day":
                                vessel.get(
                                    "fuel_consumption_ton_day",
                                    0,
                                ),

                            "daily_charter_rate":
                                vessel.get(
                                    "daily_charter_rate",
                                    0,
                                ),

                            "current_position":
                                vessel.get(
                                    "current_position",
                                    "Unknown",
                                ),

                            "availability_status": (
                                "AVAILABLE_NOW"
                                if float(
                                    vessel.get(
                                        "eta_available_days",
                                        0,
                                    )
                                )
                                <= 0
                                else
                                "AVAILABLE_SOON"
                            ),

                            "eta_available_days":
                                float(
                                    vessel.get(
                                        "eta_available_days",
                                        0,
                                    )
                                ),

                            "voyage_days": round(
                                vessel_transit_days[i],
                                1,
                            ),

                            "total_operational_days":
                                round(
                                    vessel_total_days[i],
                                    1,
                                ),

                            "voyage_cost_usd":
                                round(
                                    vessel_costs[i],
                                    2,
                                ),

                            "port_compatible":
                                True,

                            "port_constraint_violations":
                                [],
                        }
                    )

                    total_capacity += float(
                        vessel.get(
                            "capacity_dwt",
                            0,
                        )
                    )

                    total_cost_usd += (
                        vessel_costs[i]
                    )

                    max_delivery_days = max(
                        max_delivery_days,
                        vessel_total_days[i],
                    )

            # ========================================================
            # 12. CAPACITY UTILIZATION
            # ========================================================

            if total_capacity > 0:

                capacity_utilization_pct = round(
                    min(
                        100.0,
                        (
                            cargo_required_tons
                            /
                            total_capacity
                        )
                        *
                        100.0,
                    ),
                    1,
                )

            else:

                capacity_utilization_pct = 0.0

            # ========================================================
            # 13. SHORTFALL
            # ========================================================

            shortfall_tons = max(
                0.0,
                cargo_required_tons
                -
                total_capacity,
            )

            # ========================================================
            # 14. USD → INR CRORE
            #
            # Existing project assumption:
            # 1 USD = ₹83
            # 1 crore = ₹10,000,000
            # ========================================================

            total_cost_inr_cr = round(
                (
                    total_cost_usd
                    *
                    83.0
                )
                /
                10_000_000.0,
                2,
            )

            # ========================================================
            # 15. RETURN OPTIMAL RESULT
            # ========================================================

            return {
                "status": "OPTIMAL",

                "message": (
                    "Optimal vessel combination found "
                    "under availability, port, deadline "
                    "and capacity constraints."
                ),

                "port_constraints":
                    port_constraints,

                "port_name":
                    port_name,

                "cargo_type":
                    cargo_type,

                "selected_vessels":
                    selected_vessels,

                "rejected_vessels":
                    rejected_vessels,

                "total_selected_capacity_tons":
                    round(
                        total_capacity,
                        2,
                    ),

                "cargo_required_tons":
                    cargo_required_tons,

                "capacity_utilization_pct":
                    capacity_utilization_pct,

                "shortfall_tons":
                    round(
                        shortfall_tons,
                        2,
                    ),

                "total_cost_usd":
                    round(
                        total_cost_usd,
                        2,
                    ),

                "total_cost_inr_cr":
                    total_cost_inr_cr,

                "max_delivery_days":
                    round(
                        max_delivery_days,
                        1,
                    ),

                "delivery_deadline_days":
                    delivery_deadline_days,

                "route_distance_nm":
                    route_distance_nm,

                "port_congestion_days":
                    port_congestion_days,

                "optimization_objective":
                    "Minimum total voyage cost",

                "optimization_method":
                    (
                        "OR-Tools SCIP Mixed Integer "
                        "Linear Programming"
                    ),

                "availability_logic":
                    (
                        "eta_available_days determines "
                        "whether a vessel is available now "
                        "or available soon."
                    ),

                "location_logic":
                    (
                        "current_position is reported for "
                        "operational transparency. Exact "
                        "repositioning distance is not assumed "
                        "because it is not present in the fleet data."
                    ),
            }

        # ============================================================
        # 16. INFEASIBLE SOLUTION
        # ============================================================

        else:

            feasible_capacity = 0.0

            deadline_filtered_vessels = []

            for i, vessel in enumerate(
                feasible_vessels
            ):

                total_days = (
                    vessel_total_days[i]
                )

                if (
                    total_days
                    <=
                    delivery_deadline_days
                ):

                    capacity = float(
                        vessel.get(
                            "capacity_dwt",
                            0,
                        )
                    )

                    feasible_capacity += (
                        capacity
                    )

                    deadline_filtered_vessels.append(
                        vessel
                    )

            shortfall_tons = max(
                0.0,
                cargo_required_tons
                -
                feasible_capacity,
            )

            if feasible_capacity <= 0:

                message = (
                    "No vessels satisfy the combined "
                    "availability, port and delivery "
                    "deadline constraints."
                )

            elif (
                feasible_capacity
                <
                cargo_required_tons
            ):

                message = (
                    "Available vessels satisfy the "
                    "availability, port and deadline "
                    "constraints, but their combined "
                    "capacity is insufficient for the "
                    "required cargo."
                )

            else:

                message = (
                    "No feasible vessel combination "
                    "was found by the optimization solver."
                )

            return {
                "status":
                    "INFEASIBLE",

                "message":
                    message,

                "port_constraints":
                    port_constraints,

                "port_name":
                    port_name,

                "cargo_type":
                    cargo_type,

                "selected_vessels":
                    [],

                "rejected_vessels":
                    rejected_vessels,

                "total_selected_capacity_tons":
                    0.0,

                "available_feasible_capacity_tons":
                    round(
                        feasible_capacity,
                        2,
                    ),

                "cargo_required_tons":
                    cargo_required_tons,

                "capacity_utilization_pct":
                    0.0,

                "shortfall_tons":
                    round(
                        shortfall_tons,
                        2,
                    ),

                "total_cost_usd":
                    0.0,

                "total_cost_inr_cr":
                    0.0,

                "max_delivery_days":
                    None,

                "delivery_deadline_days":
                    delivery_deadline_days,

                "route_distance_nm":
                    route_distance_nm,

                "port_congestion_days":
                    port_congestion_days,

                "optimization_objective":
                    "Minimum total voyage cost",

                "optimization_method":
                    (
                        "OR-Tools SCIP Mixed Integer "
                        "Linear Programming"
                    ),

                "availability_logic":
                    (
                        "eta_available_days is treated "
                        "as the vessel availability lead time."
                    ),

                "location_logic":
                    (
                        "current_position is retained in "
                        "vessel decisions but no artificial "
                        "repositioning distance is assumed."
                    ),
            }
import numpy as np
from scipy.optimize import linprog


def optimize_procurement(target_demand_tons, suppliers):
    """
    Optimizes cargo allocation across multiple suppliers using Linear Programming.

    Objective:
        Minimize total landed procurement cost.

    Landed cost:
        Commodity price + Freight rate

    Supplier capacity:
        Supports both 'capacity_tons' and 'available_tons'.

    Supplier ID:
        Supports both 'id' and 'supplier_id'.
    """
#backend/app/api and schemas
    # ---------------------------------------------------------
    # 1. Basic validation
    # ---------------------------------------------------------
    if target_demand_tons is None or target_demand_tons <= 0:
        return {
            "status": "error",
            "message": "Target demand must be greater than zero.",
            "allocations": []
        }

    if not suppliers:
        return {
            "status": "error",
            "message": "No supplier data was provided.",
            "allocations": []
        }

    num_suppliers = len(suppliers)

    # ---------------------------------------------------------
    # 2. Validate and prepare supplier data
    # ---------------------------------------------------------
    prepared_suppliers = []

    for i, supplier in enumerate(suppliers):

        if "commodity_price_usd" not in supplier:
            return {
                "status": "error",
                "message": (
                    f"Supplier {i + 1} is missing "
                    "'commodity_price_usd'."
                ),
                "allocations": []
            }

        if "freight_rate_usd" not in supplier:
            return {
                "status": "error",
                "message": (
                    f"Supplier {i + 1} is missing "
                    "'freight_rate_usd'."
                ),
                "allocations": []
            }

        # Support both naming conventions.
        capacity = supplier.get(
            "available_tons",
            supplier.get("capacity_tons")
        )

        if capacity is None:
            return {
                "status": "error",
                "message": (
                    f"Supplier {i + 1} is missing "
                    "'available_tons' or 'capacity_tons'."
                ),
                "allocations": []
            }

        if capacity < 0:
            return {
                "status": "error",
                "message": (
                    f"Supplier {i + 1} has negative capacity."
                ),
                "allocations": []
            }

        prepared_suppliers.append({
            **supplier,
            "available_tons": float(capacity)
        })

    # ---------------------------------------------------------
    # 3. Objective Function
    # ---------------------------------------------------------
    # Landed cost = commodity price + freight rate
    c = [
        s["commodity_price_usd"] + s["freight_rate_usd"]
        for s in prepared_suppliers
    ]

    # ---------------------------------------------------------
    # 4. Equality Constraint
    # ---------------------------------------------------------
    # Total allocated cargo must equal target demand.
    A_eq = [[1.0] * num_suppliers]
    b_eq = [target_demand_tons]

    # ---------------------------------------------------------
    # 5. Inequality Constraints
    # ---------------------------------------------------------
    A_ub = []
    b_ub = []

    # Supplier diversification cap
    for i, s in enumerate(prepared_suppliers):

        max_allocation_pct = s.get("max_allocation_pct")

        if max_allocation_pct is not None:

            # Accept either:
            # 0.50 = 50%
            # 50 = 50%
            if max_allocation_pct > 1:
                max_allocation_pct = max_allocation_pct / 100.0

            if max_allocation_pct <= 0:
                return {
                    "status": "error",
                    "message": (
                        f"Supplier {i + 1} has invalid "
                        "'max_allocation_pct'."
                    ),
                    "allocations": []
                }

            row = [0.0] * num_suppliers
            row[i] = 1.0

            A_ub.append(row)
            b_ub.append(
                target_demand_tons * max_allocation_pct
            )

    # ---------------------------------------------------------
    # 6. Variable Bounds
    # ---------------------------------------------------------
    # 0 <= allocation <= supplier available capacity
    bounds = []

    for s in prepared_suppliers:

        min_qty = float(s.get("min_order_tons", 0))
        max_qty = float(s["available_tons"])

        if min_qty < 0:
            return {
                "status": "error",
                "message": "min_order_tons cannot be negative.",
                "allocations": []
            }

        if min_qty > max_qty:
            return {
                "status": "error",
                "message": (
                    f"Minimum order quantity exceeds supplier "
                    f"capacity for {s.get('name', 'unknown supplier')}."
                ),
                "allocations": []
            }

        bounds.append((min_qty, max_qty))

    # ---------------------------------------------------------
    # 7. Feasibility pre-check
    # ---------------------------------------------------------
    total_available_capacity = sum(
        s["available_tons"]
        for s in prepared_suppliers
    )

    if total_available_capacity < target_demand_tons:
        shortfall = (
            target_demand_tons -
            total_available_capacity
        )

        return {
            "status": "infeasible",
            "message": (
                "Total supplier availability is insufficient "
                "to satisfy the target demand."
            ),
            "target_demand_tons": target_demand_tons,
            "total_available_capacity_tons": round(
                total_available_capacity, 2
            ),
            "shortfall_tons": round(shortfall, 2),
            "allocations": []
        }

    # ---------------------------------------------------------
    # 8. Solve LP using SciPy HiGHS
    # ---------------------------------------------------------
    res = linprog(
        c,
        A_ub=A_ub if A_ub else None,
        b_ub=b_ub if b_ub else None,
        A_eq=A_eq,
        b_eq=b_eq,
        bounds=bounds,
        method="highs"
    )

    # ---------------------------------------------------------
    # 9. Handle optimization failure
    # ---------------------------------------------------------
    if not res.success:
        return {
            "status": "infeasible",
            "message": (
                f"Optimization failed: {res.message}"
            ),
            "target_demand_tons": target_demand_tons,
            "total_available_capacity_tons": round(
                total_available_capacity, 2
            ),
            "allocations": []
        }

    # ---------------------------------------------------------
    # 10. Format optimization results
    # ---------------------------------------------------------
    allocations = []
    total_cost = 0.0
    total_allocated = 0.0

    for i, s in enumerate(prepared_suppliers):

        allocated_tons = round(float(res.x[i]), 2)

        # Ignore numerical noise.
        if allocated_tons <= 0:
            continue

        landed_cost = float(c[i])

        supplier_total_cost = (
            allocated_tons * landed_cost
        )

        total_cost += supplier_total_cost
        total_allocated += allocated_tons

        # Preserve supplied supplier ID.
        supplier_id = s.get(
            "supplier_id",
            s.get("id", f"sup_{i + 1}")
        )

        allocations.append({
            "supplier_id": supplier_id,
            "supplier_name": s.get(
                "name",
                f"Supplier {i + 1}"
            ),
            "origin": s.get("origin", "N/A"),
            "allocated_tons": allocated_tons,
            "share_of_total_pct": round(
                (allocated_tons / target_demand_tons) * 100,
                1
            ),
            "available_tons": round(
                s["available_tons"],
                2
            ),
            "commodity_price_usd": s[
                "commodity_price_usd"
            ],
            "freight_rate_usd": s[
                "freight_rate_usd"
            ],
            "landed_cost_per_ton_usd": round(
                landed_cost,
                2
            ),
            "total_cost_usd": round(
                supplier_total_cost,
                2
            )
        })

    # ---------------------------------------------------------
    # 11. Final totals
    # ---------------------------------------------------------
    shortfall = max(
        0.0,
        target_demand_tons - total_allocated
    )

    weighted_avg_landed_cost = (
        total_cost / total_allocated
        if total_allocated > 0
        else 0.0
    )

    return {
        "status": "success",
        "target_demand_tons": target_demand_tons,
        "total_allocated_tons": round(
            total_allocated,
            2
        ),
        "total_available_capacity_tons": round(
            total_available_capacity,
            2
        ),
        "shortfall_tons": round(
            shortfall,
            2
        ),
        "total_procurement_cost_usd": round(
            total_cost,
            2
        ),
        "weighted_avg_landed_cost_per_ton_usd": round(
            weighted_avg_landed_cost,
            2
        ),
        "allocations": allocations
    }
class RiskEvaluator:
    """
    Route risk evaluation engine.

    Risk components:
        40% - Port congestion
        25% - Weather exposure
        20% - Vessel supply scarcity
        15% - Route distance complexity

    Output:
        - risk score
        - risk level
        - key drivers
        - component scores
    """
#models/decision.py


    def __init__(self):
        pass

    def evaluate_route_risk(
        self,
        port_congestion_days: float,
        weather_risk_index: float,
        vessel_availability_index: float,
        distance_nautical_miles: float,
    ) -> dict:

        # ============================================================
        # 1. INPUT VALIDATION
        # ============================================================

        port_congestion_days = max(
            0.0,
            float(port_congestion_days)
        )

        weather_risk_index = max(
            0.0,
            float(weather_risk_index)
        )

        vessel_availability_index = max(
            0.0,
            float(vessel_availability_index)
        )

        distance_nautical_miles = max(
            0.0,
            float(distance_nautical_miles)
        )

        # ============================================================
        # 2. COMPONENT RISK SCORES
        # ============================================================

        # Congestion:
        # 7 or more days = maximum congestion risk.
        congestion_score = min(
            100.0,
            (
                port_congestion_days
                /
                7.0
            ) * 100.0
        )

        # Weather:
        # Index of 2.0 or above = maximum weather risk.
        weather_score = min(
            100.0,
            (
                weather_risk_index
                /
                2.0
            ) * 100.0
        )

        # Vessel scarcity:
        # Availability index of 150 = very healthy supply.
        # Lower availability means greater scarcity risk.
        supply_scarcity_score = max(
            0.0,
            min(
                100.0,
                150.0
                -
                vessel_availability_index
            )
        )

        # Distance:
        # 10,000 NM or above = maximum route complexity.
        distance_score = min(
            100.0,
            (
                distance_nautical_miles
                /
                10000.0
            ) * 100.0
        )

        # ============================================================
        # 3. WEIGHTED RISK SCORE
        # ============================================================

        risk_score = round(
            (
                congestion_score * 0.40
                +
                weather_score * 0.25
                +
                supply_scarcity_score * 0.20
                +
                distance_score * 0.15
            ),
            1
        )

        # ============================================================
        # 4. RISK LEVEL
        # ============================================================

        if risk_score >= 70:

            risk_level = "HIGH"

        elif risk_score >= 40:

            risk_level = "MEDIUM"

        else:

            risk_level = "LOW"

        # ============================================================
        # 5. EXPLAINABLE RISK DRIVERS
        # ============================================================

        key_drivers = []

        # Congestion driver
        if port_congestion_days >= 5:

            key_drivers.append(
                (
                    f"High port congestion of "
                    f"{port_congestion_days:.1f} days."
                )
            )

        elif port_congestion_days >= 3:

            key_drivers.append(
                (
                    f"Moderate port congestion of "
                    f"{port_congestion_days:.1f} days."
                )
            )

        # Weather driver
        if weather_risk_index >= 1.6:

            key_drivers.append(
                (
                    f"High weather exposure "
                    f"(index {weather_risk_index:.1f})."
                )
            )

        elif weather_risk_index >= 1.2:

            key_drivers.append(
                (
                    f"Elevated weather exposure "
                    f"(index {weather_risk_index:.1f})."
                )
            )

        # Vessel supply driver
        if vessel_availability_index < 80:

            key_drivers.append(
                (
                    f"High vessel supply scarcity "
                    f"(availability index "
                    f"{vessel_availability_index:.1f})."
                )
            )

        elif vessel_availability_index < 100:

            key_drivers.append(
                (
                    f"Moderate vessel supply scarcity "
                    f"(availability index "
                    f"{vessel_availability_index:.1f})."
                )
            )

        # Distance driver
        if distance_nautical_miles >= 7000:

            key_drivers.append(
                (
                    f"High route-distance complexity "
                    f"({distance_nautical_miles:.0f} NM)."
                )
            )

        elif distance_nautical_miles >= 4000:

            key_drivers.append(
                (
                    f"Moderate route-distance complexity "
                    f"({distance_nautical_miles:.0f} NM)."
                )
            )

        # ============================================================
        # 6. FALLBACK EXPLANATION
        # ============================================================

        if not key_drivers:

            key_drivers.append(
                "Low operational risk across the evaluated factors."
            )

        # ============================================================
        # 7. RETURN RESULT
        # ============================================================

        return {
            "risk_score": risk_score,

            "risk_level": risk_level,

            "congestion_days":
                round(
                    port_congestion_days,
                    2
                ),

            "key_drivers":
                key_drivers,

            "sub_scores": {
                "congestion":
                    round(
                        congestion_score,
                        1
                    ),

                "weather":
                    round(
                        weather_score,
                        1
                    ),

                "supply_scarcity":
                    round(
                        supply_scarcity_score,
                        1
                    ),

                "distance_complexity":
                    round(
                        distance_score,
                        1
                    ),
            },

            "weights": {
                "congestion": 0.40,
                "weather": 0.25,
                "supply_scarcity": 0.20,
                "distance_complexity": 0.15,
            },

            "methodology":
                (
                    "Weighted rule-based route risk model "
                    "using congestion, weather, vessel supply "
                    "and route-distance indicators."
                ),
        }
from pathlib import Path
from typing import List, Optional

import joblib
import numpy as np
import pandas as pd


class FreightForecaster:
    """
    Loads the trained freight forecasting model and performs
    real 30-day freight-rate inference.

    Forecast uncertainty is estimated from chronological
    out-of-sample residuals on the same 30-day target used
    during model training.
    """

    FEATURE_COLUMNS = [
        "freight_rate_usd_per_ton",
        "bunker_fuel_price_usd",
        "cargo_demand_index",
        "vessel_availability_index",
        "port_congestion_days",
        "rate_lag_1",
        "rate_lag_7",
        "rate_lag_14",
        "rate_roll_7_mean",
        "rate_roll_14_mean",
        "rate_roll_7_std",
        "demand_vessel_ratio",
        "fuel_price_lag_1",
        "month_sin",
        "month_cos",
    ]

    TARGET_COLUMN = "target_rate_30d"

    def __init__(self, model_path: Optional[str] = None):
        project_root = Path(__file__).resolve().parents[3]

        self.model_path = (
            Path(model_path)
            if model_path
            else project_root / "models" / "forecaster_model.pkl"
        )

        self.data_path = (
            project_root
            / "data"
            / "processed"
            / "freight_features_processed.csv"
        )

        if not self.model_path.exists():
            raise FileNotFoundError(
                f"Forecast model not found: {self.model_path}"
            )

        if not self.data_path.exists():
            raise FileNotFoundError(
                f"Processed forecast dataset not found: {self.data_path}"
            )

        self.model = joblib.load(self.model_path)
        self.data = pd.read_csv(self.data_path)

        if "date" in self.data.columns:
            self.data["date"] = pd.to_datetime(
                self.data["date"],
                errors="coerce",
            )

            self.data = (
                self.data
                .sort_values("date")
                .reset_index(drop=True)
            )

        # Validate trained model feature structure.
        if hasattr(self.model, "feature_names_in_"):
            trained_features = list(
                self.model.feature_names_in_
            )

            if trained_features != self.FEATURE_COLUMNS:
                raise ValueError(
                    "Model feature mismatch.\n"
                    f"Expected: {self.FEATURE_COLUMNS}\n"
                    f"Model has: {trained_features}"
                )

    def _get_historical_rates(
        self,
        historical_rates: Optional[List[float]],
    ) -> List[float]:

        if historical_rates and len(historical_rates) >= 14:
            rates = [
                float(rate)
                for rate in historical_rates
                if float(rate) > 0
            ]

            if len(rates) >= 14:
                return rates[-14:]

        # Use latest real historical observations
        # from the processed dataset.
        rates = (
            self.data["freight_rate_usd_per_ton"]
            .dropna()
            .astype(float)
            .tolist()
        )

        if len(rates) < 14:
            raise ValueError(
                "At least 14 historical freight-rate observations "
                "are required."
            )

        return rates[-14:]

    def _prepare_holdout_data(self):
        required_columns = (
            self.FEATURE_COLUMNS
            + [self.TARGET_COLUMN]
        )

        missing_columns = [
            column
            for column in required_columns
            if column not in self.data.columns
        ]

        if missing_columns:
            raise ValueError(
                "Dataset is missing required forecast columns: "
                f"{missing_columns}"
            )

        df = (
            self.data[required_columns]
            .replace(
                [np.inf, -np.inf],
                np.nan,
            )
            .dropna()
        )

        if len(df) < 30:
            return None

        split_index = int(len(df) * 0.8)

        test_df = df.iloc[split_index:]

        if test_df.empty:
            return None

        return test_df

    def _calculate_metrics_and_uncertainty(self):
        """
        Evaluate the trained model against the actual 30-day
        target and calculate empirical forecast uncertainty
        from chronological holdout residuals.
        """

        test_df = self._prepare_holdout_data()

        if test_df is None:
            return {
                "model_mae_usd": None,
                "model_rmse_usd": None,
                "naive_persistence_mae_usd": None,
                "naive_persistence_rmse_usd": None,
                "forecast_uncertainty": None,
            }

        X_test = test_df[
            self.FEATURE_COLUMNS
        ]

        # This is the actual training target.
        y_test = test_df[
            self.TARGET_COLUMN
        ].to_numpy(dtype=float)

        predictions = self.model.predict(X_test)

        predictions = np.asarray(
            predictions,
            dtype=float,
        )

        residuals = y_test - predictions

        absolute_errors = np.abs(residuals)

        model_mae = float(
            np.mean(absolute_errors)
        )

        model_rmse = float(
            np.sqrt(
                np.mean(residuals ** 2)
            )
        )

        # Persistence baseline:
        # use the current freight rate as the
        # naive estimate of the future 30-day rate.
        naive_predictions = test_df[
            "freight_rate_usd_per_ton"
        ].to_numpy(dtype=float)

        naive_errors = (
            y_test - naive_predictions
        )

        naive_mae = float(
            np.mean(np.abs(naive_errors))
        )

        naive_rmse = float(
            np.sqrt(
                np.mean(naive_errors ** 2)
            )
        )

        # Empirical 90% forecast interval
        # Use the 5th and 95th percentiles of historical
        # out-of-sample signed residuals.
        # This creates a data-derived, potentially asymmetric
        # uncertainty interval rather than a hardcoded range.

        lower_residual = float(
            np.percentile(
                residuals,
                5,
            )
        )

        upper_residual = float(
            np.percentile(
                residuals,
                95,
            )
        )

        return {
            "model_mae_usd": round(
                model_mae,
                4,
            ),
            "model_rmse_usd": round(
                model_rmse,
                4,
            ),
            "naive_persistence_mae_usd": round(
                naive_mae,
                4,
            ),
            "naive_persistence_rmse_usd": round(
                naive_rmse,
                4,
            ),
            "forecast_uncertainty": {
                "method": (
                    "Empirical 90% interval from "
                    "chronological holdout residuals"
                ),
                "lower_residual_usd": round(
                    lower_residual,
                    4,
                ),
                "upper_residual_usd": round(
                    upper_residual,
                    4,
                ),
                "holdout_observations": int(
                    len(residuals)
                ),
            },
        }

    def predict_30d_rate(
        self,
        current_rate: float,
        bunker_fuel: float,
        cargo_demand: float,
        vessel_avail: float,
        congestion_days: float,
        historical_rates: Optional[List[float]] = None,
    ):

        historical = self._get_historical_rates(
            historical_rates
        )

        rate_lag_1 = historical[-1]
        rate_lag_7 = historical[-7]
        rate_lag_14 = historical[0]

        rate_roll_7_mean = float(
            np.mean(historical[-7:])
        )

        rate_roll_14_mean = float(
            np.mean(historical)
        )

        rate_roll_7_std = float(
            np.std(historical[-7:])
        )

        demand_vessel_ratio = (
            float(cargo_demand)
            / max(float(vessel_avail), 1.0)
        )

        # Use latest recorded fuel price as
        # the lagged fuel feature.
        if "bunker_fuel_price_usd" in self.data.columns:
            fuel_history = (
                self.data[
                    "bunker_fuel_price_usd"
                ]
                .dropna()
                .astype(float)
                .tolist()
            )

            fuel_price_lag_1 = (
                fuel_history[-1]
                if fuel_history
                else float(bunker_fuel)
            )
        else:
            fuel_price_lag_1 = float(
                bunker_fuel
            )

        # Use the latest available dataset date
        # as the reference for the target month.
        if "date" in self.data.columns:
            dates = (
                pd.to_datetime(
                    self.data["date"],
                    errors="coerce",
                )
                .dropna()
            )

            if not dates.empty:
                target_date = (
                    dates.max()
                    + pd.Timedelta(days=30)
                )
            else:
                target_date = (
                    pd.Timestamp.today()
                    + pd.Timedelta(days=30)
                )
        else:
            target_date = (
                pd.Timestamp.today()
                + pd.Timedelta(days=30)
            )

        month = int(
            target_date.month
        )

        month_sin = float(
            np.sin(
                2 * np.pi * month / 12
            )
        )

        month_cos = float(
            np.cos(
                2 * np.pi * month / 12
            )
        )

        features = {
            "freight_rate_usd_per_ton": float(
                current_rate
            ),
            "bunker_fuel_price_usd": float(
                bunker_fuel
            ),
            "cargo_demand_index": float(
                cargo_demand
            ),
            "vessel_availability_index": float(
                vessel_avail
            ),
            "port_congestion_days": float(
                congestion_days
            ),
            "rate_lag_1": rate_lag_1,
            "rate_lag_7": rate_lag_7,
            "rate_lag_14": rate_lag_14,
            "rate_roll_7_mean": rate_roll_7_mean,
            "rate_roll_14_mean": rate_roll_14_mean,
            "rate_roll_7_std": rate_roll_7_std,
            "demand_vessel_ratio": demand_vessel_ratio,
            "fuel_price_lag_1": fuel_price_lag_1,
            "month_sin": month_sin,
            "month_cos": month_cos,
        }

        feature_frame = pd.DataFrame(
            [
                [
                    features[column]
                    for column in self.FEATURE_COLUMNS
                ]
            ],
            columns=self.FEATURE_COLUMNS,
        )

         # REAL MODEL INFERENCE

        prediction = float(
            self.model.predict(
                feature_frame
            )[0]
        )

        rate_change = (
            prediction
            - float(current_rate)
        )

        percentage_change = (
            (
                rate_change
                / float(current_rate)
            )
            * 100
            if current_rate > 0
            else 0.0
        )

        if percentage_change > 2:
            trend = "UPWARD"
        elif percentage_change < -2:
            trend = "DOWNWARD"
        else:
            trend = "STABLE"

        if percentage_change >= 5:
            recommendation = "CHARTER NOW"
        elif percentage_change <= -5:
            recommendation = "WAIT"
        else:
            recommendation = "WATCH"

        # METRICS + FORECAST UNCERTAINTY

        evaluation = (
            self._calculate_metrics_and_uncertainty()
        )

        uncertainty = evaluation[
            "forecast_uncertainty"
        ]

        forecast_range = None

        if uncertainty is not None:
            lower_bound = (
                prediction
                + uncertainty[
                    "lower_residual_usd"
                ]
            )

            upper_bound = (
                prediction
                + uncertainty[
                    "upper_residual_usd"
                ]
            )

            # Freight rate cannot be negative.
            lower_bound = max(
                0.0,
                lower_bound,
            )

            upper_bound = max(
                lower_bound,
                upper_bound,
            )

            forecast_range = {
                "confidence_level": "90%",
                "lower_usd": round(
                    lower_bound,
                    2,
                ),
                "upper_usd": round(
                    upper_bound,
                    2,
                ),
                "width_usd": round(
                    upper_bound
                    - lower_bound,
                    2,
                ),
            }

        # FORECAST CURVE FOR DASHBOARD
        
        if forecast_range is not None:
            forecast_curve = [
                {
                    "day": 0,
                    "forecast": round(
                        float(current_rate),
                        2,
                    ),
                    "lower": round(
                        float(current_rate),
                        2,
                    ),
                    "upper": round(
                        float(current_rate),
                        2,
                    ),
                },
                {
                    "day": 30,
                    "forecast": round(
                        float(prediction),
                        2,
                    ),
                    "lower": round(
                        float(
                            forecast_range[
                                "lower_usd"
                            ]
                        ),
                        2,
                    ),
                    "upper": round(
                        float(
                            forecast_range[
                                "upper_usd"
                            ]
                        ),
                        2,
                    ),
                },
            ]
        else:
            forecast_curve = [
                {
                    "day": 0,
                    "forecast": round(
                        float(current_rate),
                        2,
                    ),
                    "lower": round(
                        float(current_rate),
                        2,
                    ),
                    "upper": round(
                        float(current_rate),
                        2,
                    ),
                },
                {
                    "day": 30,
                    "forecast": round(
                        float(prediction),
                        2,
                    ),
                    "lower": round(
                        float(prediction),
                        2,
                    ),
                    "upper": round(
                        float(prediction),
                        2,
                    ),
                },
            ]

        return {
            "model_info": {
                "model_type": type(
                    self.model
                ).__name__,
                "feature_count": len(
                    self.FEATURE_COLUMNS
                ),
                "model_path": str(
                    self.model_path
                ),
            },

            "current_rate_usd": round(
                float(current_rate),
                2,
            ),

            "predicted_30d_rate_usd": round(
                prediction,
                2,
            ),

            "rate_change_usd": round(
                rate_change,
                2,
            ),

            "percentage_change": round(
                percentage_change,
                2,
            ),

            "trend": trend,

            "forecast_range": forecast_range,

            "forecast_curve": forecast_curve,

            "forecast_range_note": (
                "90% empirical forecast interval "
                "derived from chronological holdout "
                "residuals."
            ),

            "baseline_comparison": {
                "model_mae_usd": evaluation[
                    "model_mae_usd"
                ],

                "model_rmse_usd": evaluation[
                    "model_rmse_usd"
                ],

                "naive_persistence_mae_usd": (
                    evaluation[
                        "naive_persistence_mae_usd"
                    ]
                ),

                "naive_persistence_rmse_usd": (
                    evaluation[
                        "naive_persistence_rmse_usd"
                    ]
                ),
            },

            "uncertainty_details": uncertainty,

            "features_used": {
                key: round(
                    float(value),
                    4,
                )
                for key, value
                in features.items()
            },

            "recommendation_hint": recommendation,
        }
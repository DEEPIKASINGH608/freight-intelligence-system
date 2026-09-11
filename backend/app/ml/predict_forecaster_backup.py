from pathlib import Path
from typing import List, Optional

import joblib
import numpy as np
import pandas as pd


class FreightForecaster:
    """
    Loads the trained freight forecasting model and performs
    real model inference using the same feature structure
    used during training.
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

        # Validate trained model feature structure.
        if hasattr(self.model, "feature_names_in_"):
            trained_features = list(self.model.feature_names_in_)

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

        # Use latest real historical observations from the dataset.
        rates = (
            self.data["freight_rate_usd_per_ton"]
            .dropna()
            .astype(float)
            .tolist()
        )

        if len(rates) < 14:
            raise ValueError(
                "At least 14 historical freight-rate observations are required."
            )

        return rates[-14:]

    def _calculate_metrics(self):
        """
        Chronological 80/20 holdout comparison between:
        - trained model
        - naive persistence baseline
        """

        df = self.data.copy()

        if len(df) < 30:
            return {
                "model_mae_usd": None,
                "naive_persistence_mae_usd": None,
            }

        df = df.dropna(subset=self.FEATURE_COLUMNS)

        split_index = int(len(df) * 0.8)

        train_df = df.iloc[:split_index]
        test_df = df.iloc[split_index:]

        if test_df.empty:
            return {
                "model_mae_usd": None,
                "naive_persistence_mae_usd": None,
            }

        X_test = test_df[self.FEATURE_COLUMNS]
        y_test = test_df["freight_rate_usd_per_ton"]

        predictions = self.model.predict(X_test)

        model_mae = float(
            np.mean(np.abs(predictions - y_test.to_numpy()))
        )

        naive_predictions = test_df["rate_lag_1"].to_numpy()

        naive_mae = float(
            np.mean(np.abs(naive_predictions - y_test.to_numpy()))
        )

        return {
            "model_mae_usd": round(model_mae, 4),
            "naive_persistence_mae_usd": round(naive_mae, 4),
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

        historical = self._get_historical_rates(historical_rates)

        rate_lag_1 = historical[-1]
        rate_lag_7 = historical[-7]
        rate_lag_14 = historical[0]

        rate_roll_7_mean = float(np.mean(historical[-7:]))
        rate_roll_14_mean = float(np.mean(historical))

        rate_roll_7_std = float(np.std(historical[-7:]))

        demand_vessel_ratio = (
            float(cargo_demand) / max(float(vessel_avail), 1.0)
        )

        # Use latest recorded fuel price as the lagged fuel feature.
        if "bunker_fuel_price_usd" in self.data.columns:
            fuel_history = (
                self.data["bunker_fuel_price_usd"]
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
            fuel_price_lag_1 = float(bunker_fuel)

        # Use the latest available dataset date as the target month
        # when an explicit future date is not supplied.
        if "date" in self.data.columns:
            dates = pd.to_datetime(self.data["date"], errors="coerce").dropna()

            if not dates.empty:
                target_date = dates.max() + pd.Timedelta(days=30)
            else:
                target_date = pd.Timestamp.today() + pd.Timedelta(days=30)
        else:
            target_date = pd.Timestamp.today() + pd.Timedelta(days=30)

        month = int(target_date.month)

        month_sin = float(np.sin(2 * np.pi * month / 12))
        month_cos = float(np.cos(2 * np.pi * month / 12))

        features = {
            "freight_rate_usd_per_ton": float(current_rate),
            "bunker_fuel_price_usd": float(bunker_fuel),
            "cargo_demand_index": float(cargo_demand),
            "vessel_availability_index": float(vessel_avail),
            "port_congestion_days": float(congestion_days),
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
            [[features[column] for column in self.FEATURE_COLUMNS]],
            columns=self.FEATURE_COLUMNS,
        )

        # REAL MODEL INFERENCE
        prediction = float(self.model.predict(feature_frame)[0])

        rate_change = prediction - float(current_rate)

        percentage_change = (
            (rate_change / float(current_rate)) * 100
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

        metrics = self._calculate_metrics()

        return {
            "model_info": {
                "model_type": type(self.model).__name__,
                "feature_count": len(self.FEATURE_COLUMNS),
                "model_path": str(self.model_path),
            },
            "current_rate_usd": round(float(current_rate), 2),
            "predicted_30d_rate_usd": round(prediction, 2),
            "rate_change_usd": round(rate_change, 2),
            "percentage_change": round(percentage_change, 2),
            "trend": trend,
            "forecast_range": None,
            "forecast_range_note": (
                "Prediction interval will be added during Phase 3."
            ),
            "baseline_comparison": metrics,
            "features_used": {
                key: round(float(value), 4)
                for key, value in features.items()
            },
            "recommendation_hint": recommendation,
        }
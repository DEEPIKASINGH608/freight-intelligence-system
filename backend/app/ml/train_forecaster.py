import os
import joblib
import numpy as np
import pandas as pd

from datetime import datetime, timezone

from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error

from xgboost import XGBRegressor






FEATURE_COLS = [
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

TARGET_COL = "target_rate_30d"


def calculate_rmse(y_true, predictions):
    return np.sqrt(mean_squared_error(y_true, predictions))


def train_and_evaluate_forecaster():

    # ---------------------------------------------------------
    # 1. LOCATE DATA
    # ---------------------------------------------------------

    project_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../../../")
    )

    data_path = os.path.join(
        project_root,
        "data",
        "processed",
        "freight_features_processed.csv",
    )

    models_dir = os.path.join(project_root, "models")

    if not os.path.exists(data_path):
        raise FileNotFoundError(
            f"Processed dataset not found at {data_path}"
        )

    os.makedirs(models_dir, exist_ok=True)

    # ---------------------------------------------------------
    # 2. LOAD DATA
    # ---------------------------------------------------------

    df = pd.read_csv(data_path)

    print(f"Loaded dataset with {len(df)} records.")

    # ---------------------------------------------------------
    # 3. VALIDATE REQUIRED COLUMNS
    # ---------------------------------------------------------

    required_columns = FEATURE_COLS + [TARGET_COL, "date"]

    missing_columns = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Dataset is missing required columns: {missing_columns}"
        )

    # ---------------------------------------------------------
    # 4. SORT CHRONOLOGICALLY
    # ---------------------------------------------------------

    df["date"] = pd.to_datetime(df["date"])

    df = df.sort_values("date").reset_index(drop=True)

    print(
        f"Date range: "
        f"{df['date'].min().date()} "
        f"to "
        f"{df['date'].max().date()}"
    )

    # ---------------------------------------------------------
    # 5. REMOVE INVALID ROWS
    # ---------------------------------------------------------

    model_data = df[FEATURE_COLS + [TARGET_COL]].copy()

    before_rows = len(model_data)

    model_data = model_data.replace(
        [np.inf, -np.inf],
        np.nan
    ).dropna()

    removed_rows = before_rows - len(model_data)

    if removed_rows > 0:
        print(
            f"Removed {removed_rows} rows containing "
            f"missing/invalid values."
        )

    if len(model_data) < 100:
        raise ValueError(
            "Not enough valid records available for training."
        )

    # ---------------------------------------------------------
    # 6. FEATURES AND TARGET
    # ---------------------------------------------------------

    X = model_data[FEATURE_COLS]
    y = model_data[TARGET_COL]

    # ---------------------------------------------------------
    # 7. CHRONOLOGICAL TRAIN / TEST SPLIT
    # ---------------------------------------------------------

    split_idx = int(len(model_data) * 0.80)

    X_train = X.iloc[:split_idx]
    X_test = X.iloc[split_idx:]

    y_train = y.iloc[:split_idx]
    y_test = y.iloc[split_idx:]

    print(
        f"Training set size: {len(X_train)} | "
        f"Test set size: {len(X_test)}"
    )

    print(
        f"Training period: "
        f"{df['date'].iloc[:split_idx].min().date()} "
        f"to "
        f"{df['date'].iloc[:split_idx].max().date()}"
    )

    print(
        f"Test period: "
        f"{df['date'].iloc[split_idx:].min().date()} "
        f"to "
        f"{df['date'].iloc[split_idx:].max().date()}"
    )

    # ---------------------------------------------------------
    # 8. NAIVE PERSISTENCE BASELINE
    # ---------------------------------------------------------
    #
    # This asks:
    # "How well would we do if we simply predicted
    # the current freight rate?"
    #
    # Since the dataset contains rate_lag_1/current rate,
    # use the current freight rate as the naive forecast.
    # ---------------------------------------------------------

    naive_predictions = X_test["freight_rate_usd_per_ton"]

    naive_mae = mean_absolute_error(
        y_test,
        naive_predictions
    )

    naive_rmse = calculate_rmse(
        y_test,
        naive_predictions
    )

    print("\n--- NAIVE PERSISTENCE BASELINE ---")

    print(
        f"Naive MAE : ${naive_mae:.4f}/ton"
    )

    print(
        f"Naive RMSE: ${naive_rmse:.4f}/ton"
    )

    # ---------------------------------------------------------
    # 9. SCALE DATA FOR LINEAR REGRESSION
    # ---------------------------------------------------------

    scaler = StandardScaler()

    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # ---------------------------------------------------------
    # 10. MODEL CANDIDATES
    # ---------------------------------------------------------

    models = {
        "Linear Regression": LinearRegression(),

        "Random Forest": RandomForestRegressor(
            n_estimators=200,
            max_depth=8,
            random_state=42,
            n_jobs=-1,
        ),

        "XGBoost": XGBRegressor(
            n_estimators=200,
            learning_rate=0.05,
            max_depth=5,
            random_state=42,
            n_jobs=-1,
            objective="reg:squarederror",
        ),
    }

    # ---------------------------------------------------------
    # 11. TRAIN AND EVALUATE MODELS
    # ---------------------------------------------------------

    best_model = None
    best_model_name = None
    lowest_mae = float("inf")

    model_results = {}

    print(
        "\n=================================================="
    )

    print(
        "30-DAY FREIGHT RATE FORECAST MODEL EVALUATION"
    )

    print(
        "=================================================="
    )

    for name, model in models.items():

        print(f"\nTraining: {name}")

        # Linear Regression uses scaled features.
        if name == "Linear Regression":

            model.fit(
                X_train_scaled,
                y_train
            )

            predictions = model.predict(
                X_test_scaled
            )

            uses_scaler = True

        else:

            model.fit(
                X_train,
                y_train
            )

            predictions = model.predict(
                X_test
            )

            uses_scaler = False

        mae = mean_absolute_error(
            y_test,
            predictions
        )

        rmse = calculate_rmse(
            y_test,
            predictions
        )

        model_results[name] = {
            "MAE": float(mae),
            "RMSE": float(rmse),
            "uses_scaler": uses_scaler,
        }

        print(
            f"MAE : ${mae:.4f}/ton"
        )

        print(
            f"RMSE: ${rmse:.4f}/ton"
        )

        if mae < lowest_mae:

            lowest_mae = mae
            best_model = model
            best_model_name = name

    # ---------------------------------------------------------
    # 12. MODEL IMPROVEMENT OVER NAIVE BASELINE
    # ---------------------------------------------------------

    best_rmse = model_results[best_model_name]["RMSE"]

    mae_improvement = (
        (naive_mae - lowest_mae)
        / naive_mae
        * 100
    )

    rmse_improvement = (
        (naive_rmse - best_rmse)
        / naive_rmse
        * 100
    )

    # ---------------------------------------------------------
    # 13. PRINT FINAL RESULT
    # ---------------------------------------------------------

    print(
        "\n=================================================="
    )

    print(
        f"CHAMPION MODEL: {best_model_name}"
    )

    print(
        f"Champion MAE : ${lowest_mae:.4f}/ton"
    )

    print(
        f"Champion RMSE: ${best_rmse:.4f}/ton"
    )

    print(
        f"Naive MAE    : ${naive_mae:.4f}/ton"
    )

    print(
        f"Naive RMSE   : ${naive_rmse:.4f}/ton"
    )

    print(
        f"MAE improvement over naive: "
        f"{mae_improvement:.2f}%"
    )

    print(
        f"RMSE improvement over naive: "
        f"{rmse_improvement:.2f}%"
    )

    print(
        "=================================================="
    )

    # ---------------------------------------------------------
    # 14. SAVE MODEL
    # ---------------------------------------------------------

    model_path = os.path.join(
        models_dir,
        "forecaster_model.pkl"
    )

    scaler_path = os.path.join(
        models_dir,
        "forecaster_scaler.pkl"
    )

    metadata_path = os.path.join(
        models_dir,
        "forecaster_metadata.pkl"
    )

    joblib.dump(
        best_model,
        model_path
    )

    joblib.dump(
        scaler,
        scaler_path
    )

    # ---------------------------------------------------------
    # 15. SAVE METADATA
    # ---------------------------------------------------------

    metadata = {
        "model_type": best_model_name,
        "target": TARGET_COL,
        "features": FEATURE_COLS,
        "feature_count": len(FEATURE_COLS),

        "uses_scaler": model_results[
            best_model_name
        ]["uses_scaler"],

        "training_rows": len(X_train),
        "test_rows": len(X_test),

        "training_start": str(
            df["date"].iloc[:split_idx].min().date()
        ),

        "training_end": str(
            df["date"].iloc[:split_idx].max().date()
        ),

        "test_start": str(
            df["date"].iloc[split_idx:].min().date()
        ),

        "test_end": str(
            df["date"].iloc[split_idx:].max().date()
        ),

        "metrics": model_results,

        "naive_baseline": {
            "MAE": float(naive_mae),
            "RMSE": float(naive_rmse),
        },

        "champion": {
            "MAE": float(lowest_mae),
            "RMSE": float(best_rmse),
            "MAE_improvement_percent": float(
                mae_improvement
            ),
            "RMSE_improvement_percent": float(
                rmse_improvement
            ),
        },

        "trained_at": datetime.now(
            timezone.utc
        ).isoformat(),

        "random_state": 42,
    }

    joblib.dump(
        metadata,
        metadata_path
    )

    # ---------------------------------------------------------
    # 16. FINAL OUTPUT
    # ---------------------------------------------------------

    print("\nArtifacts saved:")

    print(
        f"Model    : {model_path}"
    )

    print(
        f"Scaler   : {scaler_path}"
    )

    print(
        f"Metadata : {metadata_path}"
    )

    print("\nTraining completed successfully.")


if __name__ == "__main__":
    train_and_evaluate_forecaster()
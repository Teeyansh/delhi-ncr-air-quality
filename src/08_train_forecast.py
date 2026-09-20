"""Step 8 - train an XGBoost model to predict PM2.5 and compare it with a naive baseline.

Split: everything before SPLIT_DATE (Aug 27) is training data, the last five days are the test
set (a time-based split, never random, so the model cannot peek at the future).

The model is compared with a *persistence baseline* that simply predicts "the next reading
equals the previous reading" (``pm25_lag1``). Any forecast model should beat this - see the
README for how the current model compares.

Input : data/delhi_ncr_pm25_features.csv
Output: results/xgboost_pm25_model.json, results/pm25_predictions.csv,
        results/xgboost_feature_importance.csv, results/model_metrics.json
"""
import json

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

import config

FEATURES, TARGET = config.FEATURE_COLS, config.TARGET_COL


def clean(part: pd.DataFrame) -> pd.DataFrame:
    """Drop rows whose target or any feature is missing or infinite."""
    part = part[np.isfinite(part[TARGET])].copy()
    part[FEATURES] = part[FEATURES].replace([np.inf, -np.inf], np.nan)
    return part.dropna(subset=FEATURES)


def regression_metrics(y_true, y_pred) -> dict:
    return {
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "r2": float(r2_score(y_true, y_pred)),
    }


def main():
    df = pd.read_csv(config.DATA_DIR / "delhi_ncr_pm25_features.csv")
    df["datetime_utc"] = pd.to_datetime(df["datetime_utc"])
    print(f"Total rows: {len(df)}  ({df['datetime_utc'].min()} to {df['datetime_utc'].max()})")

    split = pd.Timestamp(config.SPLIT_DATE)
    train_raw, test_raw = df[df["datetime_utc"] < split], df[df["datetime_utc"] >= split]
    train, test = clean(train_raw), clean(test_raw)
    print(f"Train rows: {len(train)} (of {len(train_raw)})  |  Test rows: {len(test)} (of {len(test_raw)})")

    model = xgb.XGBRegressor(**config.XGB_PARAMS)
    model.fit(train[FEATURES], train[TARGET])

    y_test = test[TARGET]
    y_pred = model.predict(test[FEATURES])

    metrics = {
        "n_train": int(len(train)),
        "n_test": int(len(test)),
        "test_period_utc": [str(test["datetime_utc"].min()), str(test["datetime_utc"].max())],
        "xgboost": regression_metrics(y_test, y_pred),
        "persistence_baseline": regression_metrics(y_test, test["pm25_lag1"]),
    }

    print("\nTest-set metrics (lower MAE/RMSE and higher R2 are better):")
    print(f"  XGBoost              MAE {metrics['xgboost']['mae']:.2f}  "
          f"RMSE {metrics['xgboost']['rmse']:.2f}  R2 {metrics['xgboost']['r2']:.3f}")
    print(f"  Persistence baseline MAE {metrics['persistence_baseline']['mae']:.2f}  "
          f"RMSE {metrics['persistence_baseline']['rmse']:.2f}  R2 {metrics['persistence_baseline']['r2']:.3f}")

    importance = (
        pd.DataFrame({"feature": FEATURES, "importance": model.feature_importances_})
        .sort_values("importance", ascending=False)
    )
    print("\nFeature importance:")
    print(importance.to_string(index=False))

    importance.to_csv(config.RESULTS_DIR / "xgboost_feature_importance.csv", index=False)
    model.save_model(str(config.RESULTS_DIR / "xgboost_pm25_model.json"))
    test = test.assign(pm25_predicted=y_pred)
    test.to_csv(config.RESULTS_DIR / "pm25_predictions.csv", index=False)
    (config.RESULTS_DIR / "model_metrics.json").write_text(json.dumps(metrics, indent=2))
    print("\nSaved model, predictions, feature importance and metrics to results/.")


if __name__ == "__main__":
    main()

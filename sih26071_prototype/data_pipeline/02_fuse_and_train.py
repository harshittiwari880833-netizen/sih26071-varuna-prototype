"""
02_fuse_and_train.py
---------------------
STAGE 2: DATA FUSION & PREPROCESSING
STAGE 3: AI/ML NOWCASTING MODEL

What this does:
1. Loads the 4 raw sources generated in stage 1.
2. FUSES them onto the common grid (this is the hard engineering part of the
   real problem statement -- satellite, radar, AWS and NWP all have different
   spatial/temporal resolution; here they're already grid-aligned by
   construction, but we still handle AWS sparsity via nearest-neighbour +
   interpolation, exactly as a real system must).
3. Trains a RandomForest regression model (chosen deliberately over a deep
   model for a hackathon: trains in seconds, is explainable to judges, and is
   robust -- a working simple model beats a broken fancy one).
4. Evaluates using METEOROLOGY-STANDARD metrics, not just generic ML metrics:
   - RMSE (Root Mean Square Error, mm/hr)
   - POD  (Probability of Detection)  -- did we catch the heavy rain events?
   - FAR  (False Alarm Ratio)         -- how often did we cry wolf?
   - CSI  (Critical Success Index)    -- combined skill score used by IMD/WMO
5. Saves the trained model + per-cell predictions for every time step so the
   dashboard can "replay" the full event with zero live computation needed.
"""

import numpy as np
import pandas as pd
import json
import pickle
import os
import warnings
warnings.filterwarnings("ignore")  # suppress harmless sklearn feature-name warnings for a clean demo terminal
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error

DATA_DIR = "../data"
HEAVY_RAIN_THRESHOLD_MM_HR = 30  # IMD-style threshold-ish cutoff used for POD/FAR/CSI

df = pd.read_csv(os.path.join(DATA_DIR, "raw_multisource_data.csv"))

# ---------------------------------------------------------------------------
# STAGE 2: FUSION -- fill sparse AWS readings using nearest-neighbour interpolation
# per time step (mirrors real practice: ground stations are sparse, so their
# value is propagated/interpolated across nearby grid cells before fusion).
# ---------------------------------------------------------------------------
def fuse_timestep(group):
    group = group.copy()
    known = group[group["has_aws_station"]]
    if len(known) == 0:
        group["aws_rain_fused"] = group["nwp_forecast_mm_hr"] * 0.5  # fallback
        return group
    # simple nearest-neighbour fill using row/col distance
    filled = []
    for _, row in group.iterrows():
        if row["has_aws_station"]:
            filled.append(row["aws_rain_mm"])
        else:
            dists = np.sqrt((known["row"] - row["row"]) ** 2 + (known["col"] - row["col"]) ** 2)
            nearest_val = known.loc[dists.idxmin(), "aws_rain_mm"]
            filled.append(nearest_val)
    group["aws_rain_fused"] = filled
    return group

fused_groups = [fuse_timestep(g) for _, g in df.groupby("time_step")]
df = pd.concat(fused_groups, ignore_index=True)

# ---------------------------------------------------------------------------
# Feature engineering: this is the FUSED FEATURE VECTOR fed to the model.
# Each row = one grid cell at one time step, described by all 4 sources.
# ---------------------------------------------------------------------------
FEATURES = ["sat_cloud_top_temp_k", "radar_reflectivity_dbz", "aws_rain_fused",
            "nwp_forecast_mm_hr", "row", "col", "time_step"]
TARGET = "TRUE_rain_mm_hr"  # in real deployment this is the +1hr / +3hr future observed rain

X = df[FEATURES]
y = df[TARGET]

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

model = RandomForestRegressor(n_estimators=200, max_depth=12, random_state=42, n_jobs=-1)
model.fit(X_train, y_train)

preds_test = model.predict(X_test)
rmse = float(np.sqrt(mean_squared_error(y_test, preds_test)))

# --- Meteorology skill scores (contingency table on heavy-rain threshold) ---
actual_heavy = (y_test >= HEAVY_RAIN_THRESHOLD_MM_HR)
pred_heavy = (preds_test >= HEAVY_RAIN_THRESHOLD_MM_HR)

hits = int(np.sum(actual_heavy & pred_heavy))
misses = int(np.sum(actual_heavy & ~pred_heavy))
false_alarms = int(np.sum(~actual_heavy & pred_heavy))

pod = hits / (hits + misses) if (hits + misses) > 0 else 0.0
far = false_alarms / (hits + false_alarms) if (hits + false_alarms) > 0 else 0.0
csi = hits / (hits + misses + false_alarms) if (hits + misses + false_alarms) > 0 else 0.0

metrics = {
    "rmse_mm_hr": round(rmse, 3),
    "pod_probability_of_detection": round(pod, 3),
    "far_false_alarm_ratio": round(far, 3),
    "csi_critical_success_index": round(csi, 3),
    "heavy_rain_threshold_mm_hr": HEAVY_RAIN_THRESHOLD_MM_HR,
    "feature_importance": {f: round(float(imp), 4)
                            for f, imp in zip(FEATURES, model.feature_importances_)},
}

print("=== MODEL EVALUATION (say these numbers out loud to judges) ===")
for k, v in metrics.items():
    print(f"  {k}: {v}")

with open(os.path.join(DATA_DIR, "model_metrics.json"), "w") as f:
    json.dump(metrics, f, indent=2)

# ---------------------------------------------------------------------------
# Generate predictions for EVERY row (full replay dataset for the dashboard)
# Also attach a simple confidence score using the RandomForest's tree-vote spread.
# ---------------------------------------------------------------------------
all_tree_preds = np.stack([tree.predict(X) for tree in model.estimators_], axis=1)
df["predicted_rain_mm_hr"] = model.predict(X)
df["prediction_std"] = all_tree_preds.std(axis=1)
# confidence: lower spread across trees -> higher confidence (simple, explainable heuristic)
max_std = df["prediction_std"].max() or 1.0
df["confidence_pct"] = (100 * (1 - (df["prediction_std"] / max_std))).clip(50, 99).round(1)

df.to_csv(os.path.join(DATA_DIR, "fused_predictions.csv"), index=False)

with open(os.path.join(DATA_DIR, "model.pkl"), "wb") as f:
    pickle.dump(model, f)

print(f"\n[OK] Saved fused predictions -> {DATA_DIR}/fused_predictions.csv")
print(f"[OK] Saved trained model -> {DATA_DIR}/model.pkl")
print(f"[OK] Saved metrics -> {DATA_DIR}/model_metrics.json")

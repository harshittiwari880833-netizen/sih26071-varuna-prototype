"""
05_generate_multi_city.py
---------------------------
Extends the single-city pipeline (scripts 01-04) to multiple real Indian
cities, each with:
  - its own real center coordinates
  - its own simulated heavy-rainfall event (different storm path/seed so
    each city looks genuinely distinct, not copy-pasted)
  - a curated list of REAL, well-known localities in that city (chosen from
    areas with documented monsoon flooding history), pinned to a specific
    grid cell for the demo
  - full per-source fusion breakdown attached to every cell (satellite,
    radar, AWS, NWP readings) so judges can see the actual data fusion,
    not just the final fused output
  - its own trained RandomForest model + meteorology metrics
  - its own DEM-based inundation map + alerts

IMPORTANT — say this to judges proactively:
The (row, col) grid cell assigned to each named locality is an
illustrative alignment for this demo (we don't have access to a licensed
geocoding service inside the hackathon build), not a survey-grade geocode.
In production this mapping would come directly from each locality's real
lat/lon via a geocoding API (e.g. Bhuvan/Google Maps/OpenStreetMap
Nominatim) snapped to the same analysis grid.

Run: python3 05_generate_multi_city.py
Output: frontend/data/cities/<city_id>.json  (one per city)
        frontend/data/cities/index.json      (city + locality directory)
"""

import numpy as np
import pandas as pd
import json
import os
import warnings
warnings.filterwarnings("ignore")
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error

OUT_DIR = "../frontend/data/cities"
os.makedirs(OUT_DIR, exist_ok=True)

GRID_SIZE = 20
GRID_SPACING_DEG = 0.02
TIME_STEPS = 12
TIME_STEP_MINUTES = 30
HEAVY_RAIN_THRESHOLD_MM_HR = 30

# ---------------------------------------------------------------------------
# CITY CONFIGS
# Localities are REAL places in each city with documented monsoon/urban
# flooding history (publicly reported in news coverage of Chennai 2015,
# Mumbai annual monsoon flooding, and Bengaluru 2022 floods). Their
# (row, col) placement on our synthetic grid is illustrative, as noted above.
# ---------------------------------------------------------------------------
CITIES = [
    {
        "id": "chennai",
        "name": "Chennai",
        "center_lat": 13.0827, "center_lon": 80.2707,
        "seed": 42,
        "storm_start": (2, 2), "storm_dir": (1.4, 1.1),
        "basin_center_frac": (0.55, 0.45),
        "localities": [
<<<<<<< HEAD
            {"name": "Anna Nagar",  "row": 16, "col": 7},
            {"name": "T. Nagar",    "row": 11, "col": 8},
            {"name": "Mylapore",    "row": 8,  "col": 14},
            {"name": "Adyar",       "row": 6,  "col": 15},
            {"name": "Velachery",   "row": 3,  "col": 10},
=======
            {"name": "Velachery",   "row": 15, "col": 13},
            {"name": "T. Nagar",    "row": 9,  "col": 8},
            {"name": "Adyar",       "row": 12, "col": 11},
            {"name": "Mylapore",    "row": 10, "col": 10},
            {"name": "Anna Nagar",  "row": 5,  "col": 4},
>>>>>>> f1dad71823a25971bdddb8324ef24ab522a630f1
        ],
    },
    {
        "id": "mumbai",
        "name": "Mumbai",
        "center_lat": 19.0760, "center_lon": 72.8777,
        "seed": 108,
        "storm_start": (17, 3), "storm_dir": (-1.2, 1.3),
        "basin_center_frac": (0.5, 0.55),
        "localities": [
<<<<<<< HEAD
            {"name": "Andheri Subway",   "row": 16, "col": 4},
            {"name": "Sion",             "row": 10, "col": 12},
            {"name": "Hindmata (Dadar)", "row": 9,  "col": 9},
            {"name": "King's Circle",    "row": 8,  "col": 10},
            {"name": "Kurla",            "row": 8,  "col": 14},
=======
            {"name": "Hindmata (Dadar)", "row": 8,  "col": 10},
            {"name": "Sion",             "row": 9,  "col": 12},
            {"name": "Kurla",            "row": 11, "col": 13},
            {"name": "Andheri Subway",   "row": 5,  "col": 6},
            {"name": "King's Circle",    "row": 8,  "col": 9},
>>>>>>> f1dad71823a25971bdddb8324ef24ab522a630f1
        ],
    },
    {
        "id": "bengaluru",
        "name": "Bengaluru",
        "center_lat": 12.9716, "center_lon": 77.5946,
        "seed": 77,
        "storm_start": (4, 16), "storm_dir": (1.1, -1.3),
        "basin_center_frac": (0.6, 0.4),
        "localities": [
<<<<<<< HEAD
            {"name": "Yemalur",           "row": 9,  "col": 16},
            {"name": "Koramangala",       "row": 6,  "col": 12},
            {"name": "Silk Board Jn.",    "row": 5,  "col": 11},
            {"name": "HSR Layout",        "row": 4,  "col": 13},
            {"name": "Bellandur",         "row": 3,  "col": 15},
=======
            {"name": "Bellandur",         "row": 14, "col": 15},
            {"name": "Koramangala",       "row": 11, "col": 13},
            {"name": "Silk Board Jn.",    "row": 13, "col": 12},
            {"name": "HSR Layout",        "row": 15, "col": 14},
            {"name": "Yemalur",           "row": 10, "col": 16},
>>>>>>> f1dad71823a25971bdddb8324ef24ab522a630f1
        ],
    },
]


def generate_city(config):
    np.random.seed(config["seed"])
    lat_vals = config["center_lat"] + (np.arange(GRID_SIZE) - GRID_SIZE / 2) * GRID_SPACING_DEG
    lon_vals = config["center_lon"] + (np.arange(GRID_SIZE) - GRID_SIZE / 2) * GRID_SPACING_DEG

    grid_cells = []
    for i, lat in enumerate(lat_vals):
        for j, lon in enumerate(lon_vals):
            grid_cells.append({"cell_id": f"{i}_{j}", "row": i, "col": j,
                                "lat": round(float(lat), 5), "lon": round(float(lon), 5)})

    sr, sc = config["storm_start"]
    dr, dc = config["storm_dir"]

    def storm_intensity(row, col, t):
        cr, cc = sr + t * dr, sc + t * dc
        dist = np.sqrt((row - cr) ** 2 + (col - cc) ** 2)
        peak = 85
        intensity = peak * np.exp(-(dist ** 2) / (2 * (5.5 ** 2)))
        intensity += np.random.normal(0, 1.5)
        return max(0.0, intensity)

    def satellite_reading(r):
        return round(float(260 - r * 0.55 + np.random.normal(0, 3)), 2)

    def radar_reflectivity(r):
        R = max(r, 0.01)
        Z = 200 * (R ** 1.6)
        return round(float(10 * np.log10(Z) + np.random.normal(0, 1.0)), 2)

    def nwp_forecast(future_r):
        bias = np.random.normal(5, 8)
        return round(float(max(0.0, future_r * 0.8 + bias)), 2)

    aws_station_cells = set(np.random.choice(len(grid_cells), size=int(0.15 * len(grid_cells)), replace=False))

    records = []
    for t in range(TIME_STEPS):
        for idx, cell in enumerate(grid_cells):
            true_rain = storm_intensity(cell["row"], cell["col"], t)
            future_rain = storm_intensity(cell["row"], cell["col"], t + 2)
            has_aws = idx in aws_station_cells
            aws_val = round(float(max(0.0, true_rain + np.random.normal(0, 1.0))), 2) if has_aws else None
            records.append({
                "time_step": t, "minutes_from_start": t * TIME_STEP_MINUTES,
                "cell_id": cell["cell_id"], "row": cell["row"], "col": cell["col"],
                "lat": cell["lat"], "lon": cell["lon"],
                "sat_cloud_top_temp_k": satellite_reading(true_rain),
                "radar_reflectivity_dbz": radar_reflectivity(true_rain),
                "has_aws_station": has_aws, "aws_rain_mm": aws_val,
                "nwp_forecast_mm_hr": nwp_forecast(future_rain),
                "TRUE_rain_mm_hr": round(float(true_rain), 2),
            })

    df = pd.DataFrame(records)

    # --- fusion: interpolate sparse AWS onto every cell, per time step ---
    fused_groups = []
    for t, group in df.groupby("time_step"):
        group = group.copy()
        known = group[group["has_aws_station"]]
        if len(known) == 0:
            group["aws_rain_fused"] = group["nwp_forecast_mm_hr"] * 0.5
        else:
            filled = []
            for _, row in group.iterrows():
                if row["has_aws_station"]:
                    filled.append(row["aws_rain_mm"])
                else:
                    dists = np.sqrt((known["row"] - row["row"]) ** 2 + (known["col"] - row["col"]) ** 2)
                    filled.append(known.loc[dists.idxmin(), "aws_rain_mm"])
            group["aws_rain_fused"] = filled
        fused_groups.append(group)
    df = pd.concat(fused_groups, ignore_index=True)

    FEATURES = ["sat_cloud_top_temp_k", "radar_reflectivity_dbz", "aws_rain_fused",
                "nwp_forecast_mm_hr", "row", "col", "time_step"]
    X, y = df[FEATURES], df["TRUE_rain_mm_hr"]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=config["seed"])
    model = RandomForestRegressor(n_estimators=200, max_depth=12, random_state=config["seed"], n_jobs=-1)
    model.fit(X_train, y_train)

    preds_test = model.predict(X_test)
    rmse = float(np.sqrt(mean_squared_error(y_test, preds_test)))
    actual_heavy = (y_test >= HEAVY_RAIN_THRESHOLD_MM_HR)
    pred_heavy = (preds_test >= HEAVY_RAIN_THRESHOLD_MM_HR)
    hits = int(np.sum(actual_heavy & pred_heavy))
    misses = int(np.sum(actual_heavy & ~pred_heavy))
    false_alarms = int(np.sum(~actual_heavy & pred_heavy))
    pod = hits / (hits + misses) if (hits + misses) > 0 else 0.0
    far = false_alarms / (hits + false_alarms) if (hits + false_alarms) > 0 else 0.0
    csi = hits / (hits + misses + false_alarms) if (hits + misses + false_alarms) > 0 else 0.0

    metrics = {
        "rmse_mm_hr": round(rmse, 3), "pod_probability_of_detection": round(pod, 3),
        "far_false_alarm_ratio": round(far, 3), "csi_critical_success_index": round(csi, 3),
        "heavy_rain_threshold_mm_hr": HEAVY_RAIN_THRESHOLD_MM_HR,
        "feature_importance": {f: round(float(imp), 4) for f, imp in zip(FEATURES, model.feature_importances_)},
    }

    all_tree_preds = np.stack([tree.predict(X) for tree in model.estimators_], axis=1)
    df["predicted_rain_mm_hr"] = model.predict(X)
    df["prediction_std"] = all_tree_preds.std(axis=1)
    max_std = df["prediction_std"].max() or 1.0
    df["confidence_pct"] = (100 * (1 - (df["prediction_std"] / max_std))).clip(50, 99).round(1)

    # --- synthetic DEM + drainage (city-specific basin position) ---
    rows_g, cols_g = np.meshgrid(np.arange(GRID_SIZE), np.arange(GRID_SIZE), indexing="ij")
    bf_r, bf_c = config["basin_center_frac"]
    center_r, center_c = GRID_SIZE * bf_r, GRID_SIZE * bf_c
    dist_from_basin = np.sqrt((rows_g - center_r) ** 2 + (cols_g - center_c) ** 2)
    elevation = 5 + 0.9 * dist_from_basin
    river_col_center = GRID_SIZE * 0.5 + 2 * np.sin(rows_g / 3.0)
    river_dist = np.abs(cols_g - river_col_center)
    elevation -= np.clip(4 - river_dist, 0, 4) * 1.5
    elevation += np.random.normal(0, 0.4, size=elevation.shape)
    elevation = np.clip(elevation, 0.5, None)

    urban_core_r, urban_core_c = GRID_SIZE * 0.5, GRID_SIZE * 0.5
    dist_from_core = np.sqrt((rows_g - urban_core_r) ** 2 + (cols_g - urban_core_c) ** 2)
    drainage_capacity = np.clip(15 + 1.3 * dist_from_core, 10, 60)

    dem_df = pd.DataFrame({"row": rows_g.flatten(), "col": cols_g.flatten(),
                            "elevation_m": elevation.flatten(), "drainage_capacity_mm_hr": drainage_capacity.flatten()})
    merged = df.merge(dem_df, on=["row", "col"], how="left")

    elev_grid = elevation.copy()
    def local_low_bonus(row, col):
        r, c = int(row), int(col)
        neigh = [elev_grid[r+dr, c+dc] for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]
                 if 0 <= r+dr < GRID_SIZE and 0 <= c+dc < GRID_SIZE]
        return max(0.0, np.mean(neigh) - elev_grid[r, c]) if neigh else 0.0

    merged["local_low_bonus"] = merged.apply(lambda r: local_low_bonus(r["row"], r["col"]), axis=1)
    merged["excess_rainfall_mm_hr"] = (merged["predicted_rain_mm_hr"] - merged["drainage_capacity_mm_hr"]).clip(lower=0)

    TIME_FACTOR, ACC_SCALE, DRAIN_RECOVERY = 0.5, 0.42, 1.6
    merged = merged.sort_values(["row", "col", "time_step"]).reset_index(drop=True)
    depths = []
    for (row, col), group in merged.groupby(["row", "col"], sort=False):
        depth = 0.0
        for _, r in group.sort_values("time_step").iterrows():
            mult = 1 + r["local_low_bonus"] * 0.25
            inflow = r["excess_rainfall_mm_hr"] * TIME_FACTOR * ACC_SCALE * mult
            depth = max(0.0, depth + inflow - DRAIN_RECOVERY)
            depths.append(round(depth, 2))
    merged = merged.sort_values(["row", "col", "time_step"]).reset_index(drop=True)
    merged["flood_depth_cm"] = depths

    def classify(d):
        if d <= 0.05: return "safe"
        if d < 5: return "low"
        if d < 15: return "moderate"
        if d < 30: return "high"
        return "severe"
    merged["flood_severity"] = merged["flood_depth_cm"].apply(classify)

    # --- build frames with FULL per-source breakdown for the fusion tooltip ---
    ALERT_LEVEL_MAP = {"low": "ADVISORY", "moderate": "WATCH", "high": "WARNING", "severe": "SEVERE WARNING"}
    SEVERITY_HI = {"low": "हल्का", "moderate": "मध्यम", "high": "उच्च", "severe": "गंभीर"}
    frames, alerts = [], []
    for t in sorted(merged["time_step"].unique()):
        sub = merged[merged["time_step"] == t]
        cells = []
        for _, r in sub.iterrows():
            cells.append({
                "id": r["cell_id"], "row": int(r["row"]), "col": int(r["col"]),
                "lat": r["lat"], "lon": r["lon"],
                "rain_mm_hr": round(float(r["predicted_rain_mm_hr"]), 1),
                "confidence_pct": float(r["confidence_pct"]),
                "flood_depth_cm": round(float(r["flood_depth_cm"]), 1),
                "flood_severity": r["flood_severity"],
                "sources": {
                    "satellite_cloud_top_k": r["sat_cloud_top_temp_k"],
                    "radar_dbz": r["radar_reflectivity_dbz"],
                    "aws_mm_hr": round(float(r["aws_rain_fused"]), 1),
                    "aws_is_real_station": bool(r["has_aws_station"]),
                    "nwp_mm_hr": r["nwp_forecast_mm_hr"],
                },
            })
        severe = sub[sub["flood_severity"].isin(["high", "severe"])]
        if len(severe) > 0:
            worst = severe.sort_values("flood_depth_cm", ascending=False).iloc[0]
            alerts.append({
                "time_step": int(t), "minutes_from_start": int(r["minutes_from_start"]),
                "level": ALERT_LEVEL_MAP[worst["flood_severity"]],
                "message": (f"{ALERT_LEVEL_MAP[worst['flood_severity']]}: Heavy rainfall "
                            f"({worst['predicted_rain_mm_hr']:.0f} mm/hr) causing {worst['flood_severity']} "
                            f"flooding risk near ({worst['lat']:.3f}, {worst['lon']:.3f}). "
                            f"Estimated water depth: {worst['flood_depth_cm']:.0f} cm."),
                "message_hi": (f"{SEVERITY_HI[worst['flood_severity']]} स्तर की बाढ़ की चेतावनी: भारी वर्षा "
                               f"({worst['predicted_rain_mm_hr']:.0f} मिमी/घंटा) के कारण जलभराव जोखिम। "
                               f"अनुमानित जल स्तर: {worst['flood_depth_cm']:.0f} सेमी।"),
                "affected_cells": int(len(severe)), "confidence_pct": float(worst["confidence_pct"]),
            })
        frames.append({
            "time_step": int(t), "minutes_from_start": int(sub["minutes_from_start"].iloc[0]), "cells": cells,
            "summary": {
                "max_rain_mm_hr": round(float(sub["predicted_rain_mm_hr"].max()), 1),
                "avg_confidence_pct": round(float(sub["confidence_pct"].mean()), 1),
                "cells_safe": int((sub["flood_severity"] == "safe").sum()),
                "cells_low": int((sub["flood_severity"] == "low").sum()),
                "cells_moderate": int((sub["flood_severity"] == "moderate").sum()),
                "cells_high": int((sub["flood_severity"] == "high").sum()),
                "cells_severe": int((sub["flood_severity"] == "severe").sum()),
            },
        })

    localities = []
    for loc in config["localities"]:
        cell = next(c for c in grid_cells if c["row"] == loc["row"] and c["col"] == loc["col"])
        localities.append({"name": loc["name"], "row": loc["row"], "col": loc["col"],
                            "cell_id": cell["cell_id"], "lat": cell["lat"], "lon": cell["lon"]})

    bundle = {
        "meta": {
            "city_id": config["id"], "city_name": config["name"],
            "center_lat": config["center_lat"], "center_lon": config["center_lon"],
            "grid_size": GRID_SIZE, "grid_spacing_deg": GRID_SPACING_DEG,
            "time_steps": TIME_STEPS, "time_step_minutes": TIME_STEP_MINUTES,
            "grid_cells": grid_cells, "localities": localities,
        },
        "model_metrics": metrics,
        "frames": frames,
        "alerts": alerts,
        "generated_by": f"SIH26071 offline demo pipeline — synthetic multi-source data for {config['name']}",
    }

    out_path = os.path.join(OUT_DIR, f"{config['id']}.json")
    with open(out_path, "w") as f:
        json.dump(bundle, f)
    size_kb = os.path.getsize(out_path) / 1024
    print(f"[OK] {config['name']}: {size_kb:.0f} KB, {len(frames)} frames, {len(alerts)} alerts, "
          f"RMSE={metrics['rmse_mm_hr']}, POD={metrics['pod_probability_of_detection']}")
    return bundle


if __name__ == "__main__":
    index = {"cities": []}
    for cfg in CITIES:
        bundle = generate_city(cfg)
        index["cities"].append({
            "id": cfg["id"], "name": cfg["name"],
            "center_lat": cfg["center_lat"], "center_lon": cfg["center_lon"],
            "localities": bundle["meta"]["localities"],
        })
    with open(os.path.join(OUT_DIR, "index.json"), "w") as f:
        json.dump(index, f, indent=2)
    print(f"\n[OK] Wrote city index -> {OUT_DIR}/index.json ({len(CITIES)} cities)")

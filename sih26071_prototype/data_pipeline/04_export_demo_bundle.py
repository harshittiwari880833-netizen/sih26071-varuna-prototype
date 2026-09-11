"""
04_export_demo_bundle.py
--------------------------
STAGE 5 (prep): ALERT GENERATION + FINAL EXPORT

Combines everything into ONE bundled JSON file that the dashboard loads
directly. This is the single most important file for a zero-error demo:
the frontend does NOT call any live API during judging -- it just reads
this pre-computed file, so there is nothing that can time out, fail on
venue wifi, or crash mid-presentation.

The same JSON schema is exactly what the FastAPI/Flask backend (see
/backend) would return from a live endpoint -- so you can demonstrate to
judges that "this is a real API-shaped response, currently served from a
cached snapshot for reliability, swappable for a live feed."
"""

import pandas as pd
import json
import os

DATA_DIR = "../data"
FRONTEND_DATA_DIR = "../frontend/data"
os.makedirs(FRONTEND_DATA_DIR, exist_ok=True)

with open(os.path.join(DATA_DIR, "grid_meta.json")) as f:
    meta = json.load(f)

with open(os.path.join(DATA_DIR, "model_metrics.json")) as f:
    metrics = json.load(f)

df = pd.read_csv(os.path.join(DATA_DIR, "final_predictions_with_flood.csv"))

SEVERITY_RANK = {"safe": 0, "low": 1, "moderate": 2, "high": 3, "severe": 4}
ALERT_LEVEL_MAP = {
    "safe": None,
    "low": "ADVISORY",
    "moderate": "WATCH",
    "high": "WARNING",
    "severe": "SEVERE WARNING",
}

# ---------------------------------------------------------------------------
# Build per-time-step frames (what the dashboard's time slider plays through)
# ---------------------------------------------------------------------------
frames = []
alerts_log = []

for t in sorted(df["time_step"].unique()):
    sub = df[df["time_step"] == t]
    cells = []
    for _, r in sub.iterrows():
        cells.append({
            "id": r["cell_id"],
            "row": int(r["row"]),
            "col": int(r["col"]),
            "lat": r["lat"],
            "lon": r["lon"],
            "rain_mm_hr": round(float(r["predicted_rain_mm_hr"]), 1),
            "confidence_pct": float(r["confidence_pct"]),
            "flood_depth_cm": round(float(r["flood_depth_cm"]), 1),
            "flood_severity": r["flood_severity"],
        })

    # generate alerts for this time step (top severity cells, deduped by region "zone")
    severe_cells = sub[sub["flood_severity"].isin(["high", "severe"])]
    if len(severe_cells) > 0:
        worst = severe_cells.sort_values("flood_depth_cm", ascending=False).iloc[0]
        alerts_log.append({
            "time_step": int(t),
            "minutes_from_start": int(r["minutes_from_start"]),
            "level": ALERT_LEVEL_MAP[worst["flood_severity"]],
            "message": (
                f"{ALERT_LEVEL_MAP[worst['flood_severity']]}: Heavy rainfall "
                f"({worst['predicted_rain_mm_hr']:.0f} mm/hr) causing "
                f"{worst['flood_severity']} flooding risk near "
                f"({worst['lat']:.3f}, {worst['lon']:.3f}). "
                f"Estimated water depth: {worst['flood_depth_cm']:.0f} cm."
            ),
            "affected_cells": int(len(severe_cells)),
            "confidence_pct": float(worst["confidence_pct"]),
        })

    frames.append({
        "time_step": int(t),
        "minutes_from_start": int(sub["minutes_from_start"].iloc[0]),
        "cells": cells,
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

bundle = {
    "meta": meta,
    "model_metrics": metrics,
    "frames": frames,
    "alerts": alerts_log,
    "generated_by": "SIH26071 offline demo pipeline (synthetic multi-source data, "
                     "real RandomForest ML model, simplified DEM-based inundation logic)",
}

out_path = os.path.join(FRONTEND_DATA_DIR, "demo_bundle.json")
with open(out_path, "w") as f:
    json.dump(bundle, f)

size_kb = os.path.getsize(out_path) / 1024
print(f"[OK] Exported demo bundle -> {out_path} ({size_kb:.1f} KB)")
print(f"[OK] {len(frames)} time-step frames, {len(alerts_log)} alerts generated")
print("[OK] Frontend can now run fully offline -- no backend/API required for the demo.")

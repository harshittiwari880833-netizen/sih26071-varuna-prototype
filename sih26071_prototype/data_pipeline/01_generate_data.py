"""
01_generate_data.py
--------------------
STAGE 1: DATA INGESTION (simulated)

Purpose (say this to judges):
Real IMD Doppler Radar / INSAT satellite feeds require ministry-level data-sharing
access that a student team cannot get in a hackathon window. To PROVE the pipeline
and AI model work correctly, we generate physically-plausible synthetic data that
mimics the structure, resolution, and statistical behaviour of:
    - Satellite cloud-top brightness temperature (proxy for INSAT-3D/GPM-IMERG)
    - Doppler Weather Radar reflectivity -> rainfall intensity
    - AWS/ARG ground station point readings
    - NWP model forecast grids (GFS/WRF-style)
for a single demo city, replaying a synthetic "heavy rainfall event" so the
system's *architecture and AI logic* can be demonstrated end-to-end, offline,
with zero risk of a live-API failure during judging.

Swapping this file for real IMD/MOSDAC/GPM-IMERG/data.gov.in API calls is a
drop-in replacement -- everything downstream (fusion, ML, inundation, dashboard)
is written against the same schema real data would use.
"""

import numpy as np
import pandas as pd
import json
import os

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
np.random.seed(42)  # reproducible demo -- IMPORTANT: same result every run

CITY_NAME = "Chennai (Demo Region)"
CITY_CENTER_LAT = 13.0827
CITY_CENTER_LON = 80.2707

GRID_SIZE = 20          # 20 x 20 grid cells covering the demo region
GRID_SPACING_DEG = 0.02 # ~2.2 km per cell

TIME_STEPS = 12          # 12 time steps -> simulate a 6-hour window (30 min each)
TIME_STEP_MINUTES = 30

OUT_DIR = "../data"
os.makedirs(OUT_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# Build the spatial grid (represents our fused analysis grid)
# ---------------------------------------------------------------------------
lat_vals = CITY_CENTER_LAT + (np.arange(GRID_SIZE) - GRID_SIZE / 2) * GRID_SPACING_DEG
lon_vals = CITY_CENTER_LON + (np.arange(GRID_SIZE) - GRID_SIZE / 2) * GRID_SPACING_DEG

grid_cells = []
for i, lat in enumerate(lat_vals):
    for j, lon in enumerate(lon_vals):
        grid_cells.append({"cell_id": f"{i}_{j}", "row": i, "col": j,
                            "lat": round(float(lat), 5), "lon": round(float(lon), 5)})

# ---------------------------------------------------------------------------
# Simulate a moving rain storm cell (a "heavy rainfall event") crossing the grid
# This mimics how a real convective storm system moves across a city.
# ---------------------------------------------------------------------------
def storm_intensity(row, col, t):
    """Returns rainfall intensity (mm/hr) at a grid cell for time step t."""
    storm_center_row = 2 + t * 1.4          # storm moves diagonally across the grid
    storm_center_col = 2 + t * 1.1
    dist = np.sqrt((row - storm_center_row) ** 2 + (col - storm_center_col) ** 2)
    storm_radius = 5.5
    peak_intensity = 85  # mm/hr at storm core -> classifies as "heavy/extreme" rainfall
    intensity = peak_intensity * np.exp(-(dist ** 2) / (2 * (storm_radius ** 2)))
    intensity += np.random.normal(0, 1.5)  # sensor noise
    return max(0.0, intensity)

# ---------------------------------------------------------------------------
# STAGE 1a: SATELLITE proxy (cloud-top brightness temp -- colder = deeper storm)
# ---------------------------------------------------------------------------
def satellite_reading(true_rain_intensity):
    # Deep convective clouds -> colder cloud tops. Rough inverse relationship + noise.
    base_temp = 260  # Kelvin, typical warm cloud top
    temp = base_temp - (true_rain_intensity * 0.55) + np.random.normal(0, 3)
    return round(float(temp), 2)

# ---------------------------------------------------------------------------
# STAGE 1b: RADAR proxy (reflectivity dBZ, standard radar meteorology unit)
# ---------------------------------------------------------------------------
def radar_reflectivity(true_rain_intensity):
    # Marshall-Palmer style relation (simplified): Z = 200 * R^1.6  -> dBZ = 10*log10(Z)
    R = max(true_rain_intensity, 0.01)
    Z = 200 * (R ** 1.6)
    dBZ = 10 * np.log10(Z) + np.random.normal(0, 1.0)
    # Radar has coverage gaps beyond a certain range from the radar station (simulate)
    return round(float(dBZ), 2)

# ---------------------------------------------------------------------------
# STAGE 1c: AWS/ARG proxy (sparse ground stations -- only ~15% of grid cells have one,
# exactly like real life: ground stations are sparse compared to satellite/radar coverage)
# ---------------------------------------------------------------------------
aws_station_cells = set(
    np.random.choice(len(grid_cells), size=int(0.15 * len(grid_cells)), replace=False)
)

def aws_reading(true_rain_intensity):
    # Ground truth rain gauge -- most accurate at its exact point, small noise only
    return round(float(max(0.0, true_rain_intensity + np.random.normal(0, 1.0))), 2)

# ---------------------------------------------------------------------------
# STAGE 1d: NWP proxy (coarse-resolution model forecast, known to have "drift")
# ---------------------------------------------------------------------------
def nwp_forecast(true_rain_intensity_future):
    # NWP models are coarse & biased -- simulate a smoothed, systematically-offset version
    bias = np.random.normal(5, 8)  # models often over/under-predict locally
    return round(float(max(0.0, true_rain_intensity_future * 0.8 + bias)), 2)

# ---------------------------------------------------------------------------
# GENERATE FULL DATASET ACROSS ALL TIME STEPS
# ---------------------------------------------------------------------------
records = []
for t in range(TIME_STEPS):
    for idx, cell in enumerate(grid_cells):
        true_rain = storm_intensity(cell["row"], cell["col"], t)
        future_true_rain = storm_intensity(cell["row"], cell["col"], t + 2)  # ~1hr ahead

        rec = {
            "time_step": t,
            "minutes_from_start": t * TIME_STEP_MINUTES,
            "cell_id": cell["cell_id"],
            "row": cell["row"],
            "col": cell["col"],
            "lat": cell["lat"],
            "lon": cell["lon"],
            "sat_cloud_top_temp_k": satellite_reading(true_rain),
            "radar_reflectivity_dbz": radar_reflectivity(true_rain),
            "has_aws_station": idx in aws_station_cells,
            "aws_rain_mm": aws_reading(true_rain) if idx in aws_station_cells else None,
            "nwp_forecast_mm_hr": nwp_forecast(future_true_rain),
            "TRUE_rain_mm_hr": round(float(true_rain), 2),  # ground truth (for training/eval only)
        }
        records.append(rec)

df = pd.DataFrame(records)
df.to_csv(os.path.join(OUT_DIR, "raw_multisource_data.csv"), index=False)

with open(os.path.join(OUT_DIR, "grid_meta.json"), "w") as f:
    json.dump({
        "city_name": CITY_NAME,
        "center_lat": CITY_CENTER_LAT,
        "center_lon": CITY_CENTER_LON,
        "grid_size": GRID_SIZE,
        "grid_spacing_deg": GRID_SPACING_DEG,
        "time_steps": TIME_STEPS,
        "time_step_minutes": TIME_STEP_MINUTES,
        "grid_cells": grid_cells,
    }, f, indent=2)

print(f"[OK] Generated {len(df)} rows across {TIME_STEPS} time steps for {len(grid_cells)} grid cells.")
print(f"[OK] Saved: {OUT_DIR}/raw_multisource_data.csv")
print(f"[OK] Saved: {OUT_DIR}/grid_meta.json")

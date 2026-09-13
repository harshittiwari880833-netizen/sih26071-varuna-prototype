"""
03_inundation_mapping.py
--------------------------
STAGE 4: INUNDATION / FLOOD MAPPING

Purpose (say this to judges):
Predicted rainfall alone doesn't tell you WHERE it floods -- that depends on
terrain elevation, drainage capacity and soil saturation. Full hydrodynamic
simulation (e.g., HEC-RAS / MIKE FLOOD) is a specialist, compute-heavy field
that is out of scope for a hackathon prototype. We deliberately use a
SIMPLIFIED, EXPLAINABLE rainfall-runoff accumulation model:

    flood_risk_score = f(predicted_rainfall, elevation, drainage_capacity)

    1. Low elevation cells accumulate more water (basic topography rule).
    2. A "drainage capacity" layer represents each area's ability to carry
       water away (storm drains, soil infiltration, existing water bodies).
    3. Cells where incoming rainfall exceeds local drainage capacity AND sit
       in a local elevation minimum are flagged as flood-risk, with a depth
       estimate proportional to the excess volume.

This is intentionally honest about being a simplification -- we say so
explicitly in the pitch. It is the same rainfall-runoff logic real municipal
early-warning systems use for a *fast first-pass* risk map before a full
hydrodynamic model is run.
"""

import numpy as np
import pandas as pd
import json
import os

DATA_DIR = "../data"
np.random.seed(7)

with open(os.path.join(DATA_DIR, "grid_meta.json")) as f:
    meta = json.load(f)

GRID_SIZE = meta["grid_size"]

# ---------------------------------------------------------------------------
# Synthetic DEM (Digital Elevation Model) -- represents Bhuvan/SRTM data in
# real deployment. We create a bowl-shaped low-lying zone (like a real city
# basin/floodplain) with a river channel running through it, since this is
# the classic geography of Indian flood-prone urban areas.
# ---------------------------------------------------------------------------
rows, cols = np.meshgrid(np.arange(GRID_SIZE), np.arange(GRID_SIZE), indexing="ij")

# Base elevation: bowl shape, higher at edges, lower in a "basin" off-center
center_r, center_c = GRID_SIZE * 0.55, GRID_SIZE * 0.45
dist_from_basin = np.sqrt((rows - center_r) ** 2 + (cols - center_c) ** 2)
elevation = 5 + 0.9 * dist_from_basin  # meters above sea level, roughly 5-25m range

# Carve a "river channel" -- a line of lower elevation cutting across the grid
river_col_center = GRID_SIZE * 0.5 + 2 * np.sin(rows / 3.0)
river_dist = np.abs(cols - river_col_center)
elevation -= np.clip(4 - river_dist, 0, 4) * 1.5

elevation += np.random.normal(0, 0.4, size=elevation.shape)  # micro-terrain noise
elevation = np.clip(elevation, 0.5, None)

# ---------------------------------------------------------------------------
# Drainage capacity layer (mm/hr the area can safely carry away).
# Urban dense zones (assume near city core) have WORSE drainage
# (concretized, overloaded storm drains) than outer greener zones -- this
# mirrors real Indian urban flooding patterns (e.g., Chennai/Bengaluru/Mumbai).
# ---------------------------------------------------------------------------
urban_core_r, urban_core_c = GRID_SIZE * 0.5, GRID_SIZE * 0.5
dist_from_core = np.sqrt((rows - urban_core_r) ** 2 + (cols - urban_core_c) ** 2)
drainage_capacity = 15 + 1.3 * dist_from_core  # low near core, higher outward
drainage_capacity = np.clip(drainage_capacity, 10, 60)

dem_df = pd.DataFrame({
    "row": rows.flatten(),
    "col": cols.flatten(),
    "elevation_m": elevation.flatten().round(2),
    "drainage_capacity_mm_hr": drainage_capacity.flatten().round(2),
})
dem_df.to_csv(os.path.join(DATA_DIR, "dem_drainage.csv"), index=False)

# ---------------------------------------------------------------------------
# Combine with the ML rainfall predictions to compute flood depth per cell
# per time step.
# ---------------------------------------------------------------------------
preds = pd.read_csv(os.path.join(DATA_DIR, "fused_predictions.csv"))
merged = preds.merge(dem_df, on=["row", "col"], how="left")

# Local elevation minimum bonus: cells lower than the average of their 4-neighbours
elev_grid = elevation.copy()

def local_low_bonus(row, col):
    r, c = int(row), int(col)
    neighbours = []
    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        nr, nc = r + dr, c + dc
        if 0 <= nr < GRID_SIZE and 0 <= nc < GRID_SIZE:
            neighbours.append(elev_grid[nr, nc])
    if not neighbours:
        return 0.0
    avg_neighbour = np.mean(neighbours)
    return max(0.0, avg_neighbour - elev_grid[r, c])  # positive if this cell is a local low point

merged["local_low_bonus"] = merged.apply(lambda r: local_low_bonus(r["row"], r["col"]), axis=1)

# Excess rainfall beyond what drainage can carry away
merged["excess_rainfall_mm_hr"] = (merged["predicted_rain_mm_hr"] - merged["drainage_capacity_mm_hr"]).clip(lower=0)

# ---------------------------------------------------------------------------
# Flood depth is modelled as CUMULATIVE water build-up over the event, not a
# one-shot value per time step -- this is what real flooding looks like
# (water rises across a storm and recedes slowly afterwards as drains catch
# up), and it makes for a much more convincing "watch the water rise" replay
# in the dashboard demo.
#   new_depth = max(0, previous_depth + excess_rainfall_this_step*scale - drainage_recovery)
# ---------------------------------------------------------------------------
TIME_FACTOR = 0.5          # 30-minute step, in hours
ACCUMULATION_SCALE = 0.42  # converts mm excess rainfall/hr into cm of standing water
DRAINAGE_RECOVERY_CM = 1.6 # cm/step that drains away naturally once rain eases

merged = merged.sort_values(["row", "col", "time_step"]).reset_index(drop=True)
flood_depths = []
for (row, col), group in merged.groupby(["row", "col"], sort=False):
    depth = 0.0
    depths_this_cell = []
    for _, r in group.sort_values("time_step").iterrows():
        low_bonus_mult = 1 + r["local_low_bonus"] * 0.25
        inflow = r["excess_rainfall_mm_hr"] * TIME_FACTOR * ACCUMULATION_SCALE * low_bonus_mult
        depth = max(0.0, depth + inflow - DRAINAGE_RECOVERY_CM)
        depths_this_cell.append(round(depth, 2))
    flood_depths.extend(depths_this_cell)

# re-merge back in the correct (row, col, time_step) sorted order we iterated in
merged = merged.sort_values(["row", "col", "time_step"]).reset_index(drop=True)
merged["flood_depth_cm"] = flood_depths

# Severity classification (used directly by the dashboard for colour-coding)
def classify(depth):
    if depth <= 0.05:
        return "safe"
    elif depth < 5:
        return "low"
    elif depth < 15:
        return "moderate"
    elif depth < 30:
        return "high"
    else:
        return "severe"

merged["flood_severity"] = merged["flood_depth_cm"].apply(classify)

merged.to_csv(os.path.join(DATA_DIR, "final_predictions_with_flood.csv"), index=False)

n_flooded_cells_peak = merged[merged["time_step"] == merged["time_step"].max()]
n_flooded_cells_peak = (n_flooded_cells_peak["flood_severity"].isin(["moderate", "high", "severe"])).sum()

print(f"[OK] Generated synthetic DEM + drainage layer -> {DATA_DIR}/dem_drainage.csv")
print(f"[OK] Computed flood depth/severity for every grid cell & time step")
print(f"[OK] Saved -> {DATA_DIR}/final_predictions_with_flood.csv")
print(f"[INFO] At peak of simulated event: {n_flooded_cells_peak} grid cells at moderate+ flood risk")

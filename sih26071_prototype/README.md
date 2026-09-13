# VARUNA — SIH26071 Prototype
### AI/ML-Based Heavy Rainfall Early Warning & Inundation Prediction System

A working prototype for **SIH26071** (Ministry of Earth Sciences, Disaster
Management theme): fuses satellite, radar, ground-station (AWS), and NWP
model data using AI/ML to predict heavy rainfall, then translates that
prediction into a flood/inundation risk map, with an alert dashboard.

---

## ⚡ Fastest path to a working demo (2 minutes)

You do **not** need to run the data pipeline or backend to see the demo —
the dashboard already ships with pre-computed data.

```bash
cd frontend
python3 -m http.server 8000
```

Then open **http://localhost:8000** in your browser. That's it.

> **Important:** you must open it via `http://localhost:8000`, NOT by
> double-clicking `index.html`. Browsers block local file loading of JSON
> for security reasons — see DEPLOYMENT_GUIDE.md if you hit any issue.

---

## What you'll see

- A 20×20 grid map of a demo region (Chennai), replaying a simulated
  6-hour heavy rainfall event in 12 steps of 30 minutes each.
- **Rainfall intensity layer** — shows the storm moving across the grid.
- **Inundation risk layer** — shows flood depth/severity building up in
  low-lying areas as the storm progresses (Safe → Moderate → High → Severe).
- **Live alert feed** — auto-generated warnings as risk crosses thresholds.
- **Model performance panel** — real ML evaluation metrics (RMSE, POD, FAR,
  CSI) and which data source (satellite/radar/AWS/NWP) mattered most.
- Press the **▶ play button** to auto-replay the whole event.

---

## Project structure

```
sih26071_prototype/
├── data_pipeline/          # The REAL pipeline — run this to regenerate everything
│   ├── 01_generate_data.py       # Stage 1: simulates satellite/radar/AWS/NWP data
│   ├── 02_fuse_and_train.py      # Stage 2+3: fusion + ML nowcasting model
│   ├── 03_inundation_mapping.py  # Stage 4: DEM + rainfall -> flood depth
│   └── 04_export_demo_bundle.py  # Stage 5 prep: bundles everything for the dashboard
├── data/                    # Generated CSVs, trained model (.pkl), metrics
├── backend/                 # OPTIONAL Flask API (not required for the demo)
│   ├── app.py
│   └── requirements.txt
├── frontend/                # The dashboard — THIS is what you show judges
│   ├── index.html
│   ├── style.css
│   ├── app.js
│   └── data/demo_bundle.json     # pre-computed, checked-in, zero-risk demo data
├── README.md
└── DEPLOYMENT_GUIDE.md       # Zero-knowledge git/GitHub/hosting instructions
```

---

## How to explain the grid to judges (say this out loud)

The grid used to be a bare heatmap with no landmarks — now it reads like an
actual map:

- **North is always up** (labelled with the compass badge, top-right of
  the map), just like every map anyone has ever read — so orient the
  judge with that first: *"North is up here, so this top edge is the
  northern part of the city, this bottom edge is the south."*
- **The small labelled circles are real places** — point at one and say
  its name out loud: *"This pin is Anna Nagar, this one is T. Nagar, this
  one down here is Velachery — these are real areas of Chennai with a
  documented history of monsoon flooding."*
- **Each square is roughly a 2.2 km × 2.2 km patch of the city** (shown
  in the caption under the map title) — say this so judges understand the
  scale: *"So this whole grid covers roughly a 44 km × 44 km stretch of
  the city."*
- **Colour = what's happening in that patch right now** — for the
  rainfall layer: *"darker/lighter blue means less/more rain right now."*
  For the inundation layer: *"grey is safe, and it goes amber → orange →
  red as flood risk increases."*
- **Click any place-pin (or use the "Jump to locality" dropdown)** to
  pull up a live readout box for that exact spot: *"Let's check
  Velachery specifically — [click it] — right now it's showing 43 mm/hr
  rainfall and a 12 cm flood depth, severity moderate."*
- **Then hit play** and narrate what changes: *"Watch this pin's number
  as the storm moves across — you can see the flood depth climbing over
  the 6-hour window."*

That six-step narration (orient → name a place → give scale → explain
colour → click a locality → play) is a complete, confident walkthrough
even for someone seeing this dashboard for the very first time.

## City & locality selection (answers "show us a real place")

The dashboard ships with **three real Indian cities** — Chennai, Mumbai,
Bengaluru — each with its own genuinely distinct simulated storm (different
starting point, direction, and random seed), its own trained model with
its own metrics, and its own DEM/drainage layout. Switch cities from the
**Region &amp; locality** panel at the top of the sidebar.

Each city also ships with **5 real, well-known localities with documented
monsoon/urban-flooding history** (e.g. Anna Nagar and Velachery in
Chennai; Andheri and Kurla in Mumbai; Bellandur and Silk Board Junction
in Bengaluru), shown as **always-visible labelled pins directly on the
grid** — hover one for its name, click it (or use "Jump to locality") to
pull up a live callout with its rainfall, flood depth, severity, and
confidence for the current frame. The grid also has a compass badge and a
"North is up" caption so it reads as an actual map, not an abstract
heatmap — this is your answer when a judge says "show me a specific
place, not just a grid."

**Be upfront about this, proactively:** the (row, col) grid cell assigned
to each named locality is an illustrative alignment for the demo, not a
survey-grade geocode (we don't have access to a licensed geocoding API
inside the hackathon environment). In production this would come from
each locality's real lat/lon via a geocoding service (Bhuvan / Google
Maps / OpenStreetMap Nominatim), snapped to the same analysis grid. Saying
this before being asked is a strength, not a weakness.

Hovering any grid cell also shows the **per-source fusion breakdown**
(satellite cloud-top temperature, radar reflectivity, AWS reading,
NWP forecast) that fed into that cell's fused prediction — this is the
proof of "fusion" a judge asking about your core methodology will want
to see, not just the final output number.

The alert feed also has an **EN / HI toggle** — a small nod to the fact
that a real citizen-facing alert system in India needs regional-language
support (as NDMA's own alert systems do).

## How to regenerate/extend the multi-city dataset

```bash
cd data_pipeline
python3 05_generate_multi_city.py
```

This writes `frontend/data/cities/<city_id>.json` for each city plus
`frontend/data/cities/index.json` (the directory the dashboard reads to
populate the city/locality dropdowns). To add a 4th city, add an entry to
the `CITIES` list at the top of `05_generate_multi_city.py` with its
center coordinates, a storm start/direction, and a localities list, then
re-run the script — the frontend picks up new cities automatically from
`index.json`, no frontend code changes needed.

## Uploading your own data (live in the dashboard)

The dashboard has a **Data source** panel (top of the left sidebar) that
lets you load a different dataset without touching any code:

- **Upload a `.json`** — the exact output of `04_export_demo_bundle.py`
  (a full fused bundle with trained-model metrics). Loads directly,
  including real RMSE/POD/FAR/CSI scores.
- **Upload a `.csv`** — raw grid data with columns
  `time_step, row, col, lat, lon, rain_mm_hr, flood_depth_cm, confidence_pct`
  (lat/lon/confidence_pct/flood_severity are optional). The browser runs
  the same severity-classification and alert logic as the Python pipeline
  (`03_inundation_mapping.py` / `04_export_demo_bundle.py`) on it live —
  no server round-trip needed.
- Sample templates for both formats are downloadable directly from that
  panel (`frontend/data/sample_data_format.json` and
  `frontend/data/sample_raw_data.csv`).
- **Reset to demo dataset** restores the original Chennai replay at any
  time — useful mid-demo if you want to show both your own data and the
  baseline.
- A bad/malformed file shows a clear inline error and leaves whatever was
  previously loaded untouched — it cannot crash the dashboard.

This is the answer to "where does new data go" for judges: this panel
*is* the ingestion point for anyone else's data once you have it in either
of these two shapes.

## How the pipeline works (regenerate it yourself)

If you want to show the *actual pipeline running* (not just the pre-baked
dashboard), or retrain with different parameters:

```bash
cd data_pipeline
pip install numpy pandas scikit-learn --break-system-packages   # if not already installed
python3 01_generate_data.py          # ~1 second
python3 02_fuse_and_train.py         # ~5 seconds — trains the RandomForest model
python3 03_inundation_mapping.py     # ~2 seconds — builds the flood map
python3 04_export_demo_bundle.py     # ~1 second — writes frontend/data/demo_bundle.json
```

Each script prints what it's doing and why — read the top comment block of
each file before your presentation; those comments are written as talking
points for explaining the architecture to judges.

**Why synthetic data?** Real IMD Doppler radar, INSAT satellite, and AWS
network feeds require ministry-level data-sharing access that a student
team cannot obtain within a hackathon window. The synthetic data is
generated with physically-plausible relationships (Marshall-Palmer
radar-rainfall relation, cloud-top-temperature-to-rainfall proxy, realistic
AWS sparsity, NWP bias) so the ML model, fusion logic, and inundation
mapping are all doing genuine work — only the raw inputs are simulated.
Swapping in real IMD/MOSDAC/GPM-IMERG API calls is a drop-in replacement
that doesn't require touching stages 2–5.

## Optional: running the backend API

Only do this if you want to show judges a live API responding to requests
(not required for the core dashboard demo):

```bash
cd backend
pip install -r requirements.txt --break-system-packages
python3 app.py
```

Visit `http://localhost:5000/api/health` to confirm it's running. Endpoints:
`/api/meta`, `/api/metrics`, `/api/frames`, `/api/frames/<time_step>`, `/api/alerts`.

---

## What's real vs. simplified in this prototype (say this to judges — proactively)

| Component | This prototype | Full production version |
|---|---|---|
| Satellite/Radar/AWS/NWP data | Physically-plausible synthetic data | Live IMD DWR, INSAT/MOSDAC, AWS network, NCMRWF/GFS feeds |
| ML model | RandomForest (fast, explainable, strong metrics) | Same + optional ConvLSTM for spatial-temporal deep learning |
| Inundation mapping | Simplified DEM + drainage-capacity runoff accumulation | Full hydrodynamic model (e.g. HEC-RAS) calibrated to historical floods |
| Alerts | Simulated dashboard feed | Integrated with NDMA Sachet / Common Alerting Protocol (CAP), SMS/IVR |
| Deployment | Static demo bundle + optional local API | Cloud-hosted, auto-refreshing on live data ingestion schedule |

Being upfront about this distinction is a strength, not a weakness — it
shows the judges you understand the real engineering constraints.

---

## Next steps if you want to extend this before the round

- Swap in real open data for one city (NASA GPM IMERG API for rainfall,
  Open-Meteo for NWP, data.gov.in for AWS) to replace stage 1's synthetic
  generator — everything downstream is already schema-compatible.
- Add a real DEM (Bhuvan/SRTM, free download) for your specific demo city
  instead of the synthetic bowl-shaped terrain in stage 3.
- Try a ConvLSTM model on a sequence of "radar-like" grids for the nowcast,
  if your team has the ML bandwidth — it's a strong differentiator in Q&A.

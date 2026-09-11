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

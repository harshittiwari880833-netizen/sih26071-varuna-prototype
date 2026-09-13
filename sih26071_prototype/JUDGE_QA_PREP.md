# Judge Q&A Prep — SIH26071 / VARUNA
### Real answers, grounded in your actual code. Every teammate should read this fully.

---

## Category 1: "Is this real / did you actually build this?"

**Q: Is this using real IMD data?**
No — we use physically-plausible **synthetic** data for satellite, radar,
AWS, and NWP sources, because live IMD Doppler Weather Radar and INSAT
satellite feeds require ministry-level data-sharing agreements a student
team cannot get within a hackathon window. What IS real: our data fusion
logic, our trained ML model (RandomForest, scikit-learn), our evaluation
metrics, and our inundation mapping logic. Only the raw sensor inputs are
simulated — everything downstream is genuine engineering. Swapping in real
IMD/MOSDAC/GPM-IMERG API calls is a drop-in replacement; the pipeline is
built with that exact schema in mind.

**Q: How do you know your synthetic data is realistic?**
We didn't just use random numbers. Specifically:
- Radar reflectivity is generated using the **Marshall-Palmer relation**
  (Z = 200·R^1.6, converted to dBZ) — the actual physics formula relating
  rainfall rate to radar reflectivity used in real meteorology.
- Satellite cloud-top temperature uses an inverse relationship to rainfall
  intensity (deeper/colder convective clouds → heavier rain), matching how
  INSAT/GPM-IMERG algorithms actually infer rainfall from brightness
  temperature.
- AWS (ground station) data is deliberately sparse — only ~15% of grid
  cells have a station — because that's genuinely how ground rain-gauge
  networks are distributed in reality; we then interpolate, the same
  approach real met departments use for sparse ground truth.
- NWP forecast data includes a deliberate bias/noise term, because real
  NWP models are known to have local-scale drift and coarse resolution.

**Q: Why didn't you just use a live weather API instead of synthetic data?**
We considered it and it's on our roadmap (NASA GPM IMERG, Open-Meteo, and
data.gov.in are all free and could replace Stage 1 directly). We chose to
demo with synthetic data for the actual judging round for one reason:
**reliability.** A live API call can fail from venue wifi, rate limits, or
an outage mid-demo. Our current build guarantees the same result every
time it's run, and lets us demonstrate a full historical-event replay
rather than being at the mercy of whether it's actually raining somewhere
right now.

---

## Category 2: Data Fusion (the hard part of this problem statement)

**Q: What exactly is "data fusion" here — you're not just averaging things?**
Correct, it's not a simple average. Each source has a different structure:
- Satellite & radar are already grid/image-based
- AWS ground stations are **sparse points** — we use nearest-neighbour
  interpolation per time step to fill gaps before fusion
- NWP is a coarse forecast grid

We fuse all four into one **common feature vector per grid cell per time
step** (`sat_cloud_top_temp_k`, `radar_reflectivity_dbz`, `aws_rain_fused`,
`nwp_forecast_mm_hr`, plus spatial/temporal position) and feed that vector
into the ML model. That feature vector IS the fusion — the model then
learns how to weigh the 4 sources against each other.

**Q: Which data source matters most to your model?**
We measured this directly with the RandomForest's feature importance
output — **radar reflectivity dominates at ~86% importance**, satellite
cloud-top temperature contributes ~13%, and AWS/NWP contribute a small
residual. This matches real meteorological intuition: radar gives the most
direct, high-resolution measurement of actual rainfall, while satellite
adds wide-area context and AWS/NWP provide ground-truth calibration and
longer lead time respectively.

---

## Category 3: The ML Model

**Q: Why RandomForest and not a deep learning / neural network model?**
Three deliberate reasons: (1) It trains in seconds, letting us iterate
fast during a hackathon; (2) it's explainable — we can show judges exactly
which features drove a prediction via feature importance, whereas a deep
model is a black box; (3) it's robust with the amount of data available.
We're aware that state-of-the-art real-world nowcasting research (e.g.
Google's MetNet, DeepMind's precipitation nowcasting) uses ConvLSTM/U-Net
architectures that treat radar/satellite as image sequences — that's our
Phase 2 roadmap once we have a larger training dataset. A working simple
model beats a broken fancy one on demo day.

**Q: How good is your model, actually? What are the numbers?**
(Run `02_fuse_and_train.py` before your presentation and read the printed
numbers — they regenerate with a fixed random seed, so they'll match what's
below unless you changed the code.)
- **RMSE: ~2.85 mm/hr** — average prediction error in rainfall rate
- **POD (Probability of Detection): ~98%** — of all actual heavy rainfall
  events (≥30mm/hr) in our test set, we correctly flagged ~98% of them
- **FAR (False Alarm Ratio): ~5%** — only ~5% of our heavy-rain alerts
  were false alarms
- **CSI (Critical Success Index): ~0.94** — a combined skill score (used
  by IMD/WMO) that penalizes both misses and false alarms; 0.94 is a very
  strong score
These are meteorology-standard metrics, not generic ML metrics — using
them signals to judges that we understand the domain, not just the ML.

**Q: What's your heavy rainfall threshold, and where does it come from?**
We used 30mm/hr in our metrics evaluation as an illustrative cutoff for
"heavy rainfall" classification. In production this threshold would be
calibrated against IMD's official rainfall intensity classification scale
(light/moderate/heavy/very heavy/extremely heavy), which we'd retrieve
from IMD's published criteria rather than choosing arbitrarily.

**Q: Isn't 98% POD suspiciously high? Could this be overfitting?**
Fair challenge — and partly yes, because our synthetic storm follows a
smooth, learnable spatial pattern (a Gaussian-shaped storm moving across
the grid), which is easier to learn than real chaotic weather. On real
data we'd expect these numbers to be meaningfully lower, and we'd validate
with cross-validation across multiple independent storm events, not just
a single event's held-out cells like we did here for the demo. We'd say
this openly if asked — it shows scientific honesty, which judges respect
more than an unchallenged inflated number.

---

## Category 4: Inundation / Flood Mapping

**Q: How do you go from "rainfall" to "this street floods"?**
We use a simplified rainfall-runoff accumulation model combining three
things per grid cell: (1) predicted rainfall intensity, (2) a **Digital
Elevation Model (DEM)** — lower-lying areas accumulate more water, (3) a
**drainage capacity** layer representing how much rainfall an area can
safely carry away (storm drains, soil infiltration). When predicted
rainfall exceeds local drainage capacity, the excess accumulates as
standing water depth, cumulatively over time (so flooding realistically
builds up during a storm and recedes slowly afterwards, not just a single
snapshot value).

**Q: Isn't full flood simulation way more complex than this?**
Yes — real hydrodynamic models (HEC-RAS, MIKE FLOOD) solve shallow-water
flow equations and are compute-intensive, specialist tools, typically
requiring detailed river cross-sections, soil data, and calibration
against historical flood extents. That's genuinely out of scope for a
hackathon prototype. Our simplified accumulation model is meant as a
**fast first-pass risk indicator** — the same role a quick heuristic model
plays in real early-warning systems before a full hydrodynamic simulation
is run for detailed planning. We say this proactively rather than waiting
to be caught out on it.

**Q: Where would you get a real DEM for an Indian city?**
ISRO's Bhuvan portal provides Indian elevation data, and SRTM (Shuttle
Radar Topography Mission) 30m-resolution global elevation data is freely
available via USGS EarthExplorer. Both are drop-in replacements for our
synthetic DEM in `03_inundation_mapping.py`.

---

## Category 5: System Design / Architecture

**Q: Walk me through your architecture in one breath.**
Four data sources (satellite, radar, AWS, NWP) → fused onto a common
spatial-temporal grid → fed into a trained ML model that predicts rainfall
intensity per grid cell per future time step → combined with elevation
and drainage data to estimate flood depth → surfaced as a live dashboard
with a rainfall layer, a flood-risk layer, and an auto-generated alert
feed with confidence scores.

**Q: What's your tech stack?**
Python (pandas, NumPy, scikit-learn) for the data pipeline and ML model;
a lightweight Flask API as an optional backend layer; a vanilla
HTML/CSS/JavaScript dashboard for the frontend (no framework dependency,
which keeps it fast, dependency-free, and reliable to run anywhere).

**Q: Why no frontend framework like React?**
Deliberate choice for a hackathon prototype: zero build step, zero
`npm install` that could fail on stage, works by opening one HTML file
through a static server. For a production system we'd likely move to
React for maintainability as the codebase grows, but for demo reliability
this was the right trade-off.

**Q: How would this scale to cover all of India, not just one city?**
The grid-based architecture is inherently tileable — the same pipeline
runs per-region, so scaling nationally is a matter of parallelizing the
same computation across many regional grids (e.g., one job per
meteorological subdivision), not redesigning the approach. The main real
constraints at national scale are compute cost and radar coverage gaps in
regions far from a Doppler Weather Radar station.

**Q: What confidence score are you showing, and how is it computed?**
We use the spread of predictions across the RandomForest's individual
decision trees — low spread (trees agree) → high confidence, high spread
(trees disagree) → lower confidence. It's a simple, explainable heuristic,
not a formal statistical confidence interval — we'd say this if pushed
further on the statistics.

---

## Category 6: "Why does this matter" / Impact

**Q: This already exists — Windy, weather apps, IMD's own website. What's different about yours?**
Those are general-purpose weather **display** apps — they show you a
forecast, but don't fuse multiple raw data sources with a model tuned for
threshold-based **actionable alerts**, and none of them translate rainfall
into a locality-level flood/inundation map. Ours is purpose-built for
disaster management authorities to get "this specific area will flood, to
this depth, with this much lead time" — not just "it might rain."

**Q: How much lead time / impact does this actually give?**
In our demo, alerts trigger as soon as predicted rainfall + accumulated
flood depth crosses risk thresholds — in our simulated 6-hour event, the
first WATCH-level alert fires well before the storm's peak (check your
alert feed's earliest timestamp vs. the peak-severity timestamp to quote
an exact number from your own run). In production, real lead time would
depend on NWP forecast horizon (typically hours to a few days) fused with
faster-updating radar/satellite nowcasts for the near-term.

**Q: Who is the end user — citizens or government?**
Both, with different framing: disaster management authorities (state/
district officials, NDRF) would get detailed technical alerts with
confidence scores and affected-cell counts for resource planning; citizens
would get simplified, plain-language, possibly multilingual alerts (e.g.
via SMS/IVR through NDMA's Sachet platform / Common Alerting Protocol)
without the technical detail.

---

## Category 7: City, locality, and multi-region coverage

**Q: You're only showing one city — does this actually work anywhere else?**
No, we now demo **three real cities — Chennai, Mumbai, and Bengaluru** —
each with its own independently simulated storm (different path, timing,
and severity), its own trained model with its own metrics, and its own
terrain/drainage layout. Switch between them live from the dashboard's
"Region & locality" panel. This proves the architecture is
city-agnostic — the same pipeline just needs a new city's coordinates and
data feeds to run anywhere in India.

**Q: Can you show me a specific place, not just a grid of cells?**
Yes — the "Jump to locality" dropdown lets you pick a real, well-known
locality in each city (e.g. Velachery or T. Nagar in Chennai, Kurla or
Hindmata/Dadar in Mumbai, Bellandur or Silk Board Junction in Bengaluru —
all chosen because they have documented monsoon/urban flooding history).
Selecting one highlights that exact spot on the grid and shows a live
readout of its rainfall, flood depth, severity, and confidence for
whatever moment you're viewing in the replay.

**Q: How precisely is "Velachery" (or any locality) mapped to a grid cell — did you actually geocode it?**
Be honest here: no — we manually assigned each named locality to a nearby
grid cell for this demo, because a licensed geocoding API wasn't
accessible inside the hackathon build environment. It's an illustrative
alignment, not a survey-grade geocode. In production, this would be a
one-time step: run each locality's real address through a geocoding
service (ISRO Bhuvan, Google Maps, or OpenStreetMap Nominatim, all of
which support Indian addresses) to get its precise lat/lon, then snap
that coordinate onto our analysis grid — the rest of the pipeline doesn't
change at all.

**Q: When I hover over a cell, what am I looking at exactly?**
That tooltip shows the actual per-source fusion breakdown for that cell:
the satellite cloud-top temperature reading, the radar reflectivity
(dBZ), the AWS ground-station reading (or its interpolated value if no
station sits exactly there), and the NWP forecast value — the four raw
inputs our model fused together to produce that cell's final rainfall
prediction. This is what genuinely proves "data fusion" is happening, not
just a single output number.

**Q: Why is the alert feed available in Hindi too?**
Because a real citizen-facing early warning system in India needs
regional-language alerts to actually be useful — this is consistent with
how NDMA's own alert systems (like Sachet) support multiple languages. We
built EN/HI as a proof-of-concept toggle; a production system would
extend this to whichever regional languages are relevant per state.

---

## Category 8: Honest limitations (say these BEFORE judges find them)

Proactively mentioning these shows maturity, not weakness:
1. Trained and demoed on synthetic events for three demo cities — not
   validated against multiple real historical floods yet.
2. Named-locality-to-grid-cell mapping is illustrative for this demo, not
   a survey-grade geocode (see Category 8).
3. Simplified inundation model, not a full hydrodynamic simulation.
4. Confidence score is a simple heuristic, not a rigorous statistical
   interval.
5. No real-time live data integration yet — architecture supports it,
   not yet implemented against actual IMD/ISRO endpoints.
6. Each city is its own independent grid — true national scaling means
   running many such grids in parallel, which is architecturally
   straightforward but not yet built/tested at that scale.

---

## Quick numbers cheat-sheet (say these out loud confidently)

| Metric | Chennai | Mumbai | Bengaluru |
|---|---|---|---|
| RMSE (mm/hr) | ~2.85 | ~2.95 | ~2.86 |
| POD | ~98% | ~96% | ~98% |
| Grid | 20×20 cells, ~2.2km spacing (all cities) | | |
| Event | 6 hours, 12 steps of 30 min (all cities) | | |
| Top feature | Radar (highest importance in all three) | | |

*(Re-run `05_generate_multi_city.py` before presenting and re-confirm
these numbers match — they're deterministic with fixed random seeds per
city unless someone on the team changed the code.)*

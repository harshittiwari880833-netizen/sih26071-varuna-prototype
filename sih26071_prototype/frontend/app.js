/* ==========================================================================
   VARUNA dashboard logic
   Loads the pre-computed demo_bundle.json (built by the offline data
   pipeline) and renders it. No network calls happen after this fetch —
   everything else is pure client-side rendering, so once the page has
   loaded once, it will not break mid-demo even if the venue wifi drops.
   ========================================================================== */

const STATE = {
  bundle: null,
  defaultBundle: null,   // cached original demo bundle, for "reset to demo dataset"
  cityIndex: null,       // list of available cities + their localities
  currentCityId: null,
  selectedLocalityCellId: null,
  currentFrame: 0,
  activeLayer: "rain",
  playing: false,
  playTimer: null,
  cellEls: {},          // cell_id -> DOM element
  shownAlertKeys: new Set(),
  alertLang: "en",
};

const SEVERITY_COLOR = {
  safe:     "var(--accent-safe)",
  low:      "var(--accent-radar)",
  moderate: "var(--accent-watch)",
  high:     "var(--accent-warn)",
  severe:   "var(--accent-severe)",
};

const RAIN_STOPS = [
  { max: 5,   color: "#1B3448" },
  { max: 15,  color: "#1F5E8C" },
  { max: 30,  color: "#2C86D6" },
  { max: 50,  color: "#4C8DFF" },
  { max: 999, color: "#B4C8FF" },
];

function rainColor(mmHr) {
  for (const stop of RAIN_STOPS) {
    if (mmHr <= stop.max) return stop.color;
  }
  return RAIN_STOPS[RAIN_STOPS.length - 1].color;
}

// --------------------------------------------------------------------------
// BOOTSTRAP
// --------------------------------------------------------------------------
async function init() {
  try {
    const idxRes = await fetch("data/cities/index.json");
    if (!idxRes.ok) throw new Error("HTTP " + idxRes.status);
    STATE.cityIndex = await idxRes.json();

    const defaultCity = STATE.cityIndex.cities[0];
    populateCitySelect();
    const bundle = await fetchCityBundle(defaultCity.id);
    STATE.defaultBundle = bundle;
    STATE.defaultCityId = defaultCity.id;
    STATE.currentCityId = defaultCity.id;
    loadBundle(bundle, "demo");
    populateLocalitySelect(defaultCity.id);
    document.getElementById("city-select").value = defaultCity.id;
  } catch (err) {
    renderFatalError(err);
    return;
  }

  wireControls();
  wireDataSource();
  wireCityAndLocality();
}

async function fetchCityBundle(cityId) {
  const res = await fetch(`data/cities/${cityId}.json`);
  if (!res.ok) throw new Error("HTTP " + res.status);
  return res.json();
}

function populateCitySelect() {
  const sel = document.getElementById("city-select");
  sel.innerHTML = STATE.cityIndex.cities.map(c => `<option value="${c.id}">${c.name}</option>`).join("");
}

function populateLocalitySelect(cityId) {
  const sel = document.getElementById("locality-select");
  const city = STATE.cityIndex.cities.find(c => c.id === cityId);
  const localities = city ? city.localities : [];
  sel.innerHTML = `<option value="">— Select a place —</option>` +
    localities.map(l => `<option value="${l.cell_id}">${l.name}</option>`).join("");
  STATE.selectedLocalityCellId = null;
  document.getElementById("locality-callout").hidden = true;
}

// --------------------------------------------------------------------------
// LOAD / SWITCH DATASET (shared by initial demo load and file uploads)
// --------------------------------------------------------------------------
function loadBundle(bundle, sourceKind) {
  STATE.bundle = bundle;
  STATE.currentFrame = 0;

  document.getElementById("meta-city").textContent = bundle.meta.city_name;

  const dot = document.getElementById("ds-dot");
  const label = document.getElementById("ds-status-text");
  if (sourceKind === "demo") {
    dot.className = "ds-dot ds-dot--demo";
    label.textContent = `Demo dataset · ${bundle.meta.city_name} synthetic event`;
  } else {
    dot.className = "ds-dot ds-dot--custom";
    label.textContent = `Custom dataset · ${bundle.meta.city_name} · ${bundle.frames.length} frames`;
  }

  // Custom uploads (raw CSV / hand-built JSON) won't carry a locality list —
  // disable the locality picker rather than showing stale/wrong entries.
  const localitySel = document.getElementById("locality-select");
  const hasLocalities = Array.isArray(bundle.meta.localities) && bundle.meta.localities.length > 0;
  localitySel.disabled = !hasLocalities;
  if (!hasLocalities) {
    localitySel.innerHTML = `<option value="">— Not available for this dataset —</option>`;
  }
  STATE.selectedLocalityCellId = null;
  document.getElementById("locality-callout").hidden = true;

<<<<<<< HEAD
  const spacingKm = (bundle.meta.grid_spacing_deg * 111).toFixed(1); // ~111km per degree latitude
  document.getElementById("grid-caption").textContent =
    `Each cell ≈ ${spacingKm} km × ${spacingKm} km · North is up · ${bundle.meta.city_name} metro area`;

=======
>>>>>>> f1dad71823a25971bdddb8324ef24ab522a630f1
  buildGrid();
  renderMetrics();
  renderLegend();
  renderFrame(0);
<<<<<<< HEAD
  renderLocalityMarkers();
=======
>>>>>>> f1dad71823a25971bdddb8324ef24ab522a630f1
}

// --------------------------------------------------------------------------
// SEVERITY / ALERT LOGIC — JS port of 03_inundation_mapping.py / 04_export_demo_bundle.py
// so a raw .csv upload gets classified exactly the same way the Python
// pipeline would, without needing a server round-trip.
// --------------------------------------------------------------------------
function classifySeverity(depthCm) {
  if (depthCm <= 0.05) return "safe";
  if (depthCm < 5) return "low";
  if (depthCm < 15) return "moderate";
  if (depthCm < 30) return "high";
  return "severe";
}

const ALERT_LEVEL_MAP = {
  low: "ADVISORY", moderate: "WATCH", high: "WARNING", severe: "SEVERE WARNING",
};

function buildFramesFromRawRows(rows) {
  // rows: array of objects with at least time_step, row, col, rain_mm_hr, flood_depth_cm
  // (lat/lon/confidence_pct/flood_severity optional — sensible defaults applied)
  const byStep = {};
  rows.forEach(r => {
    const t = Number(r.time_step);
    if (!byStep[t]) byStep[t] = [];
    const depth = r.flood_depth_cm !== undefined && r.flood_depth_cm !== ""
      ? Number(r.flood_depth_cm) : 0;
    byStep[t].push({
      id: `${r.row}_${r.col}`,
      row: Number(r.row),
      col: Number(r.col),
      lat: r.lat !== undefined && r.lat !== "" ? Number(r.lat) : 0,
      lon: r.lon !== undefined && r.lon !== "" ? Number(r.lon) : 0,
      rain_mm_hr: Number(r.rain_mm_hr || 0),
      confidence_pct: r.confidence_pct !== undefined && r.confidence_pct !== ""
        ? Number(r.confidence_pct) : 75,
      flood_depth_cm: depth,
      flood_severity: r.flood_severity || classifySeverity(depth),
    });
  });

  const steps = Object.keys(byStep).map(Number).sort((a, b) => a - b);
  const alerts = [];
  const frames = steps.map(t => {
    const cells = byStep[t];
    const summary = {
      max_rain_mm_hr: Math.max(...cells.map(c => c.rain_mm_hr)),
      avg_confidence_pct: cells.reduce((s, c) => s + c.confidence_pct, 0) / cells.length,
      cells_safe: cells.filter(c => c.flood_severity === "safe").length,
      cells_low: cells.filter(c => c.flood_severity === "low").length,
      cells_moderate: cells.filter(c => c.flood_severity === "moderate").length,
      cells_high: cells.filter(c => c.flood_severity === "high").length,
      cells_severe: cells.filter(c => c.flood_severity === "severe").length,
    };

    const severe = cells.filter(c => c.flood_severity === "high" || c.flood_severity === "severe");
    if (severe.length > 0) {
      const worst = severe.sort((a, b) => b.flood_depth_cm - a.flood_depth_cm)[0];
      alerts.push({
        time_step: t,
        minutes_from_start: t * 30,
        level: ALERT_LEVEL_MAP[worst.flood_severity],
        message: `${ALERT_LEVEL_MAP[worst.flood_severity]}: Heavy rainfall (${worst.rain_mm_hr.toFixed(0)} mm/hr) `
          + `causing ${worst.flood_severity} flooding risk near (${worst.lat.toFixed(3)}, ${worst.lon.toFixed(3)}). `
          + `Estimated water depth: ${worst.flood_depth_cm.toFixed(0)} cm.`,
        affected_cells: severe.length,
        confidence_pct: worst.confidence_pct,
      });
    }

    return { time_step: t, minutes_from_start: t * 30, cells, summary };
  });

  const maxRow = Math.max(...rows.map(r => Number(r.row)));
  const maxCol = Math.max(...rows.map(r => Number(r.col)));
  const gridSize = Math.max(maxRow, maxCol) + 1;

  return {
    meta: { city_name: "Custom uploaded region", grid_size: gridSize },
    model_metrics: null, // no trained model attached to a raw upload
    frames,
    alerts,
    generated_by: "Client-side CSV parser (browser) — no server round-trip",
  };
}

// --------------------------------------------------------------------------
// PARSERS
// --------------------------------------------------------------------------
function parseCSV(text) {
  const lines = text.trim().split(/\r?\n/);
  const headers = lines[0].split(",").map(h => h.trim());
  return lines.slice(1).filter(l => l.trim().length > 0).map(line => {
    const values = line.split(",");
    const row = {};
    headers.forEach((h, i) => row[h] = (values[i] !== undefined ? values[i].trim() : ""));
    return row;
  });
}

function validateUploadedBundle(bundle) {
  if (!bundle.meta || typeof bundle.meta.grid_size !== "number") {
    throw new Error("Missing or invalid 'meta.grid_size' in JSON.");
  }
  if (!Array.isArray(bundle.frames) || bundle.frames.length === 0) {
    throw new Error("Missing or empty 'frames' array in JSON.");
  }
  if (!Array.isArray(bundle.frames[0].cells)) {
    throw new Error("Each frame must contain a 'cells' array.");
  }
  if (!Array.isArray(bundle.alerts)) bundle.alerts = [];
  return bundle;
}

async function handleUploadedFile(file) {
  const errBox = document.getElementById("upload-error");
  errBox.hidden = true;
  errBox.textContent = "";

  // remember which city was active so "Reset to demo dataset" restores it, not always the first city
  if (STATE.currentCityId) STATE.lastCityBeforeUpload = STATE.currentCityId;

  try {
    const text = await file.text();
    let bundle;

    if (file.name.toLowerCase().endsWith(".json")) {
      bundle = validateUploadedBundle(JSON.parse(text));
    } else if (file.name.toLowerCase().endsWith(".csv")) {
      const rows = parseCSV(text);
      const required = ["time_step", "row", "col", "rain_mm_hr"];
      const missing = required.filter(k => !(k in rows[0]));
      if (missing.length > 0) {
        throw new Error(`CSV is missing required column(s): ${missing.join(", ")}`);
      }
      bundle = buildFramesFromRawRows(rows);
    } else {
      throw new Error("Unsupported file type — please upload a .json or .csv file.");
    }

    loadBundle(bundle, "custom");
  } catch (err) {
    errBox.textContent = `Could not load file: ${err.message}`;
    errBox.hidden = false;
  }
}

function wireDataSource() {
  const input = document.getElementById("file-upload");
  const dropZone = document.getElementById("upload-drop");
  const resetBtn = document.getElementById("reset-demo-btn");

  input.addEventListener("change", (e) => {
    if (e.target.files[0]) handleUploadedFile(e.target.files[0]);
  });

  dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.classList.add("is-dragover");
  });
  dropZone.addEventListener("dragleave", () => dropZone.classList.remove("is-dragover"));
  dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("is-dragover");
    if (e.dataTransfer.files[0]) handleUploadedFile(e.dataTransfer.files[0]);
  });

  resetBtn.addEventListener("click", async () => {
    document.getElementById("upload-error").hidden = true;
    input.value = "";
    const restoreCityId = STATE.lastCityBeforeUpload || STATE.defaultCityId;
    try {
      const bundle = (restoreCityId === STATE.defaultCityId)
        ? STATE.defaultBundle
        : await fetchCityBundle(restoreCityId);
      STATE.currentCityId = restoreCityId;
      loadBundle(bundle, "demo");
      document.getElementById("city-select").value = restoreCityId;
      populateLocalitySelect(restoreCityId);
    } catch (err) {
      loadBundle(STATE.defaultBundle, "demo");
      STATE.currentCityId = STATE.defaultCityId;
      document.getElementById("city-select").value = STATE.defaultCityId;
      populateLocalitySelect(STATE.defaultCityId);
    }
  });
}

function wireCityAndLocality() {
  const citySel = document.getElementById("city-select");
  const localitySel = document.getElementById("locality-select");

  citySel.addEventListener("change", async (e) => {
    const cityId = e.target.value;
    try {
      const bundle = await fetchCityBundle(cityId);
      STATE.currentCityId = cityId;
      stopPlayback();
      loadBundle(bundle, "demo");
      populateLocalitySelect(cityId);
    } catch (err) {
      const errBox = document.getElementById("upload-error");
      errBox.textContent = `Could not load city dataset: ${err.message}`;
      errBox.hidden = false;
    }
  });

  localitySel.addEventListener("change", (e) => {
<<<<<<< HEAD
    if (e.target.value) {
      selectLocality(e.target.value);
    } else {
      STATE.selectedLocalityCellId = null;
      updateMarkerSelection();
      renderFrame(STATE.currentFrame);
    }
=======
    STATE.selectedLocalityCellId = e.target.value || null;
    renderFrame(STATE.currentFrame); // re-render to show highlight + callout for the new selection
>>>>>>> f1dad71823a25971bdddb8324ef24ab522a630f1
  });
}

function renderFatalError(err) {
  const stage = document.getElementById("map-grid");
  stage.style.display = "block";
  stage.innerHTML = `
    <div style="padding:24px; font-family: var(--font-mono); font-size:12.5px; line-height:1.7; color:#F2B84B;">
      Could not load data/demo_bundle.json (${err.message}).<br><br>
      This almost always means the page was opened directly as a file
      (file://) instead of through a local web server, which browsers block
      for security reasons.<br><br>
      Fix: open a terminal in the <b>frontend</b> folder and run
      <br><span style="color:#35D1C9">python3 -m http.server 8000</span>
      <br>then visit <span style="color:#35D1C9">http://localhost:8000</span>
      in your browser. See DEPLOYMENT_GUIDE.md for full steps.
    </div>`;
}

// --------------------------------------------------------------------------
// GRID
// --------------------------------------------------------------------------
function buildGrid() {
  const gridEl = document.getElementById("map-grid");
  const size = STATE.bundle.meta.grid_size;
  gridEl.style.setProperty("--grid-size", size);
  gridEl.innerHTML = "";
  STATE.cellEls = {};

<<<<<<< HEAD
  // NOTE ON ORIENTATION: in our data, row index increases with latitude
  // (row 0 = southernmost, row size-1 = northernmost) — see
  // 05_generate_multi_city.py's lat_vals calculation. CSS Grid fills
  // top-to-bottom in DOM append order, so we must append the HIGHEST row
  // index first for North to end up at the TOP of the screen, matching
  // every map anyone has ever read.
  for (let r = size - 1; r >= 0; r--) {
=======
  for (let r = 0; r < size; r++) {
>>>>>>> f1dad71823a25971bdddb8324ef24ab522a630f1
    for (let c = 0; c < size; c++) {
      const id = `${r}_${c}`;
      const el = document.createElement("div");
      el.className = "map-cell";
      el.dataset.cellId = id;
      el.addEventListener("mousemove", (e) => showTooltip(e, id));
      el.addEventListener("mouseleave", hideTooltip);
      gridEl.appendChild(el);
      STATE.cellEls[id] = el;
    }
  }
}

<<<<<<< HEAD
// --------------------------------------------------------------------------
// LOCALITY MARKERS — always-visible labeled pins on the grid so it reads as
// an actual map of named places, not an abstract heatmap.
// --------------------------------------------------------------------------
function renderLocalityMarkers() {
  const container = document.getElementById("locality-markers");
  container.innerHTML = "";
  const localities = STATE.bundle.meta.localities;
  if (!Array.isArray(localities) || localities.length === 0) return;

  const size = STATE.bundle.meta.grid_size;
  localities.forEach(loc => {
    const visualRow = size - 1 - loc.row; // flip to match buildGrid's North-up order
    const leftPct = ((loc.col + 0.5) / size) * 100;
    const topPct = ((visualRow + 0.5) / size) * 100;

    const marker = document.createElement("div");
    marker.className = "locality-marker";
    marker.style.left = leftPct + "%";
    marker.style.top = topPct + "%";
    marker.dataset.cellId = loc.cell_id;
    marker.title = loc.name;
    marker.textContent = loc.name.slice(0, 2).toUpperCase();

    const label = document.createElement("span");
    label.className = "locality-marker__label";
    label.textContent = loc.name;
    marker.appendChild(label);

    marker.addEventListener("click", () => selectLocality(loc.cell_id));
    container.appendChild(marker);
  });

  updateMarkerSelection();
}

function updateMarkerSelection() {
  document.querySelectorAll(".locality-marker").forEach(m => {
    m.classList.toggle("is-selected", m.dataset.cellId === STATE.selectedLocalityCellId);
  });
}

function selectLocality(cellId) {
  STATE.selectedLocalityCellId = cellId;
  const sel = document.getElementById("locality-select");
  if (sel && !sel.disabled) sel.value = cellId;
  updateMarkerSelection();
  renderFrame(STATE.currentFrame);
}

=======
>>>>>>> f1dad71823a25971bdddb8324ef24ab522a630f1
function showTooltip(evt, cellId) {
  const tooltip = document.getElementById("map-tooltip");
  const frame = STATE.bundle.frames[STATE.currentFrame];
  const cell = frame.cells.find(c => c.id === cellId);
  if (!cell) return;

  tooltip.hidden = false;
  let sourcesHtml = "";
  if (cell.sources) {
    const s = cell.sources;
    sourcesHtml = `
      <div style="margin-top:6px; padding-top:6px; border-top:1px solid #1E3348; color:#7C93A8;">fused from</div>
      satellite: ${s.satellite_cloud_top_k.toFixed(1)} K cloud-top<br>
      radar: ${s.radar_dbz.toFixed(1)} dBZ<br>
      AWS: ${s.aws_mm_hr.toFixed(1)} mm/hr ${s.aws_is_real_station ? "(station)" : "(interpolated)"}<br>
      NWP: ${s.nwp_mm_hr.toFixed(1)} mm/hr forecast
    `;
  }

  tooltip.innerHTML = `
    lat ${cell.lat.toFixed(3)}, lon ${cell.lon.toFixed(3)}<br>
    rain: ${cell.rain_mm_hr.toFixed(1)} mm/hr<br>
    flood: ${cell.flood_depth_cm.toFixed(1)} cm (${cell.flood_severity})<br>
    confidence: ${cell.confidence_pct.toFixed(0)}%
    ${sourcesHtml}
  `;
  const stage = document.querySelector(".map-stage");
  const stageRect = stage.getBoundingClientRect();
  tooltip.style.left = (evt.clientX - stageRect.left + 14) + "px";
  tooltip.style.top = (evt.clientY - stageRect.top + 14) + "px";
}

function hideTooltip() {
  document.getElementById("map-tooltip").hidden = true;
}

// --------------------------------------------------------------------------
// FRAME RENDERING
// --------------------------------------------------------------------------
function renderFrame(frameIdx) {
  STATE.currentFrame = frameIdx;
  const frame = STATE.bundle.frames[frameIdx];

  frame.cells.forEach(cell => {
    const el = STATE.cellEls[cell.id];
    if (!el) return;
    if (STATE.activeLayer === "rain") {
      el.style.background = cell.rain_mm_hr < 1 ? "var(--accent-safe)" : rainColor(cell.rain_mm_hr);
      el.style.boxShadow = "none";
    } else {
      el.style.background = SEVERITY_COLOR[cell.flood_severity];
      el.style.boxShadow = (cell.flood_severity === "severe")
        ? "0 0 6px rgba(228,67,43,0.9)"
        : (cell.flood_severity === "high" ? "0 0 4px rgba(255,138,61,0.6)" : "none");
    }
    el.classList.toggle("is-highlighted", cell.id === STATE.selectedLocalityCellId);
  });

  document.getElementById("time-slider").value = frameIdx;
  document.getElementById("time-readout").textContent = `T+${frame.minutes_from_start} min`;
  document.getElementById("time-frame-readout").textContent =
    `Frame ${frameIdx + 1} / ${STATE.bundle.frames.length}`;

  renderSummary(frame);
  renderAlertsUpTo(frameIdx);
  renderLocalityCallout(frame);
}

function renderLocalityCallout(frame) {
  const callout = document.getElementById("locality-callout");
  if (!STATE.selectedLocalityCellId) { callout.hidden = true; return; }

  const cell = frame.cells.find(c => c.id === STATE.selectedLocalityCellId);
  if (!cell) { callout.hidden = true; return; }

  const localities = (STATE.bundle.meta.localities || []);
  const loc = localities.find(l => l.cell_id === STATE.selectedLocalityCellId);

  callout.hidden = false;
  document.getElementById("loc-name").textContent = loc ? loc.name : cell.id;
  document.getElementById("loc-stats").innerHTML = `
    <div><span>Rainfall</span>${cell.rain_mm_hr.toFixed(0)} mm/hr</div>
    <div><span>Flood depth</span>${cell.flood_depth_cm.toFixed(0)} cm</div>
    <div><span>Severity</span>${cell.flood_severity}</div>
    <div><span>Confidence</span>${cell.confidence_pct.toFixed(0)}%</div>
  `;
}

function renderSummary(frame) {
  const s = frame.summary;
  const grid = document.getElementById("summary-grid");
  grid.innerHTML = `
    <div class="summary-card">
      <div class="summary-card__value" style="color:var(--accent-rain)">${s.max_rain_mm_hr.toFixed(0)} mm/hr</div>
      <div class="summary-card__label">Peak rainfall this frame</div>
    </div>
    <div class="summary-card">
      <div class="summary-card__value" style="color:var(--accent-radar)">${s.avg_confidence_pct.toFixed(0)}%</div>
      <div class="summary-card__label">Avg. model confidence</div>
    </div>
    <div class="summary-card">
      <div class="summary-card__value" style="color:var(--accent-warn)">${s.cells_high}</div>
      <div class="summary-card__label">High-risk cells</div>
    </div>
    <div class="summary-card">
      <div class="summary-card__value" style="color:var(--accent-severe)">${s.cells_severe}</div>
      <div class="summary-card__label">Severe-risk cells</div>
    </div>
  `;
}

function renderAlertsUpTo(frameIdx) {
  const feed = document.getElementById("alert-feed");
  const alerts = STATE.bundle.alerts.filter(a => a.time_step <= frameIdx);

  if (alerts.length === 0) {
    feed.innerHTML = `<div class="alert-feed__empty">No alerts triggered yet — conditions nominal.</div>`;
    return;
  }

  // newest first
  const ordered = [...alerts].reverse();
  feed.innerHTML = ordered.map(a => {
    const levelClass = "level-" + a.level.toLowerCase().replace(/\s+/g, "-");
    const msg = (STATE.alertLang === "hi" && a.message_hi) ? a.message_hi : a.message;
    return `
      <div class="alert-card ${levelClass}">
        <div class="alert-card__level">${a.level}</div>
        <div class="alert-card__msg">${msg}</div>
        <div class="alert-card__meta">T+${a.minutes_from_start} min · ${a.affected_cells} cells affected · ${a.confidence_pct.toFixed(0)}% confidence</div>
      </div>`;
  }).join("");
}

// --------------------------------------------------------------------------
// METRICS / LEGEND
// --------------------------------------------------------------------------
function renderMetrics() {
  const m = STATE.bundle.model_metrics;
  const grid = document.getElementById("metric-grid");
  const fiWrap = document.getElementById("feature-importance");
  const note = document.getElementById("metric-note");

  if (!m) {
    grid.innerHTML = `<div class="panel-note" style="grid-column: 1 / -1;">
      No trained-model metrics attached to this dataset — run
      <code>02_fuse_and_train.py</code> on it and upload the resulting
      demo_bundle.json to see real RMSE / POD / FAR / CSI scores here.
    </div>`;
    fiWrap.innerHTML = "";
    note.textContent = "Showing raw uploaded grid data only.";
    return;
  }
  note.textContent = "Meteorology-standard skill scores, evaluated on held-out grid cells during training.";

  grid.innerHTML = `
    <div class="metric-card">
      <div class="metric-card__value">${m.rmse_mm_hr}</div>
      <div class="metric-card__label">RMSE (mm/hr)</div>
    </div>
    <div class="metric-card">
      <div class="metric-card__value">${(m.pod_probability_of_detection * 100).toFixed(0)}%</div>
      <div class="metric-card__label">POD — detection rate</div>
    </div>
    <div class="metric-card">
      <div class="metric-card__value">${(m.far_false_alarm_ratio * 100).toFixed(0)}%</div>
      <div class="metric-card__label">FAR — false alarms</div>
    </div>
    <div class="metric-card">
      <div class="metric-card__value">${m.csi_critical_success_index.toFixed(2)}</div>
      <div class="metric-card__label">CSI — critical success</div>
    </div>
  `;

  const fi = Object.entries(m.feature_importance).sort((a, b) => b[1] - a[1]).slice(0, 4);
  const labelMap = {
    sat_cloud_top_temp_k: "Satellite",
    radar_reflectivity_dbz: "Radar",
    aws_rain_fused: "AWS/ground",
    nwp_forecast_mm_hr: "NWP model",
    row: "Grid row", col: "Grid col", time_step: "Time step",
  };
  fiWrap.innerHTML = fi.map(([key, val]) => `
    <div class="fi-row">
      <div class="fi-name">${labelMap[key] || key}</div>
      <div class="fi-bar-wrap"><div class="fi-bar" style="width:${(val * 100).toFixed(0)}%"></div></div>
      <div class="fi-pct">${(val * 100).toFixed(0)}%</div>
    </div>
  `).join("");
}

function renderLegend() {
  const legend = document.getElementById("legend");
  function paint() {
    if (STATE.activeLayer === "rain") {
      legend.innerHTML = `
        <div class="legend-item"><span class="legend-swatch" style="background:#1B3448"></span>Light</div>
        <div class="legend-item"><span class="legend-swatch" style="background:#2C86D6"></span>Moderate</div>
        <div class="legend-item"><span class="legend-swatch" style="background:#4C8DFF"></span>Heavy</div>
        <div class="legend-item"><span class="legend-swatch" style="background:#B4C8FF"></span>Extreme</div>
      `;
    } else {
      legend.innerHTML = `
        <div class="legend-item"><span class="legend-swatch" style="background:var(--accent-safe)"></span>Safe</div>
        <div class="legend-item"><span class="legend-swatch" style="background:var(--accent-radar)"></span>Low</div>
        <div class="legend-item"><span class="legend-swatch" style="background:var(--accent-watch)"></span>Moderate</div>
        <div class="legend-item"><span class="legend-swatch" style="background:var(--accent-warn)"></span>High</div>
        <div class="legend-item"><span class="legend-swatch" style="background:var(--accent-severe)"></span>Severe</div>
      `;
    }
  }
  paint();
  STATE.repaintLegend = paint;
}

// --------------------------------------------------------------------------
// CONTROLS
// --------------------------------------------------------------------------
function wireControls() {
  document.querySelectorAll(".layer-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".layer-btn").forEach(b => b.classList.remove("is-active"));
      btn.classList.add("is-active");
      STATE.activeLayer = btn.dataset.layer;
      if (STATE.repaintLegend) STATE.repaintLegend();
      renderFrame(STATE.currentFrame);
    });
  });

  const slider = document.getElementById("time-slider");
  slider.max = STATE.bundle.frames.length - 1;
  slider.addEventListener("input", (e) => {
    stopPlayback();
    renderFrame(parseInt(e.target.value, 10));
  });

  document.getElementById("play-btn").addEventListener("click", togglePlayback);

  document.querySelectorAll(".lang-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".lang-btn").forEach(b => b.classList.remove("is-active"));
      btn.classList.add("is-active");
      STATE.alertLang = btn.dataset.lang;
      renderAlertsUpTo(STATE.currentFrame);
    });
  });
}

function togglePlayback() {
  STATE.playing ? stopPlayback() : startPlayback();
}

function startPlayback() {
  STATE.playing = true;
  document.getElementById("icon-play").hidden = true;
  document.getElementById("icon-pause").hidden = false;
  STATE.playTimer = setInterval(() => {
    let next = STATE.currentFrame + 1;
    if (next >= STATE.bundle.frames.length) {
      stopPlayback();
      return;
    }
    renderFrame(next);
  }, 1100);
}

function stopPlayback() {
  STATE.playing = false;
  document.getElementById("icon-play").hidden = false;
  document.getElementById("icon-pause").hidden = true;
  if (STATE.playTimer) clearInterval(STATE.playTimer);
  STATE.playTimer = null;
}

init();

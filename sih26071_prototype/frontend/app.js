/* ==========================================================================
   VARUNA dashboard logic
   Loads the pre-computed demo_bundle.json (built by the offline data
   pipeline) and renders it. No network calls happen after this fetch —
   everything else is pure client-side rendering, so once the page has
   loaded once, it will not break mid-demo even if the venue wifi drops.
   ========================================================================== */

const STATE = {
  bundle: null,
  currentFrame: 0,
  activeLayer: "rain",
  playing: false,
  playTimer: null,
  cellEls: {},          // cell_id -> DOM element
  shownAlertKeys: new Set(),
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
    const res = await fetch("data/demo_bundle.json");
    if (!res.ok) throw new Error("HTTP " + res.status);
    STATE.bundle = await res.json();
  } catch (err) {
    renderFatalError(err);
    return;
  }

  document.getElementById("meta-city").textContent = STATE.bundle.meta.city_name;

  buildGrid();
  renderMetrics();
  renderLegend();
  wireControls();
  renderFrame(0);
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

  // order cells row-major so CSS grid auto-placement matches (row, col)
  const firstFrame = STATE.bundle.frames[0];
  const byId = {};
  firstFrame.cells.forEach(c => byId[c.id] = c);

  for (let r = 0; r < size; r++) {
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

function showTooltip(evt, cellId) {
  const tooltip = document.getElementById("map-tooltip");
  const frame = STATE.bundle.frames[STATE.currentFrame];
  const cell = frame.cells.find(c => c.id === cellId);
  if (!cell) return;

  tooltip.hidden = false;
  tooltip.innerHTML = `
    lat ${cell.lat.toFixed(3)}, lon ${cell.lon.toFixed(3)}<br>
    rain: ${cell.rain_mm_hr.toFixed(1)} mm/hr<br>
    flood: ${cell.flood_depth_cm.toFixed(1)} cm (${cell.flood_severity})<br>
    confidence: ${cell.confidence_pct.toFixed(0)}%
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
  });

  document.getElementById("time-slider").value = frameIdx;
  document.getElementById("time-readout").textContent = `T+${frame.minutes_from_start} min`;
  document.getElementById("time-frame-readout").textContent =
    `Frame ${frameIdx + 1} / ${STATE.bundle.frames.length}`;

  renderSummary(frame);
  renderAlertsUpTo(frameIdx);
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
    return `
      <div class="alert-card ${levelClass}">
        <div class="alert-card__level">${a.level}</div>
        <div class="alert-card__msg">${a.message}</div>
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

  const fiWrap = document.getElementById("feature-importance");
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

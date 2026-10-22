/* Southwest siting dashboard, v2 design. Same data and behaviour as v1 (../app/app.js); data is read from ../app/data/.
   Colours come from the design tokens in styles.css (design/tokens.css), read once at boot. */
"use strict";

const BASE = "../app/";            // v1 folder: data/, doc.html, and the paths inside layers.json are relative to it
const DOC = `${BASE}doc.html?f=`;  // v1's markdown viewer renders memos, briefs and the method
const FACTORS = [
  ["grid", "Grid", "score_grid"], ["land", "Land", "score_land"], ["sun", "Sun", "score_sun"],
  ["permit", "Permitting", "score_permit"], ["dc", "Data center", "score_dc"]];
const STATE_NAMES = { CA: "California", AZ: "Arizona", NV: "Nevada", NM: "New Mexico", UT: "Utah" };
const MAX_ROWS = 400;
const REDUCED = matchMedia("(prefers-reduced-motion: reduce)").matches;

const S = {
  doc: null, n: 0, cols: {}, score: null, rank: null, show: null, order: [], viewRows: [],
  mode: "solar", weights: null, selected: null, sort: { key: "rank", dir: 1 },
  fs: { score: null, hide: null }, loaded: {}, charts: {}, summary: null, deliv: null, sources: null,
};

const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const fmt = (v, d = 0) => (v === null || v === undefined || Number.isNaN(v)) ? "n/a" :
  Number(v).toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d });

/* ---------- design tokens ---------- */
const T = {};
const tok = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
function readTokens() {
  ["paper", "paper-sunk", "ink", "ink-2", "muted", "rule", "rule-strong", "accent", "prov", "warn",
    "score-1", "score-2", "score-3", "score-4", "score-5", "site-edge", "site-selected",
    "kv-lt115", "kv-115", "kv-230", "kv-345", "kv-500", "kv-unknown",
    "q-unknown", "q-lt500", "q-500", "q-2000", "q-removed", "sub-stroke",
    "blm-available", "drecp-dfa", "drecp-variance", "sez-dev", "sez-nondev",
    "own-blm", "own-usfs", "own-nps", "own-dod", "own-tribal", "own-state", "own-other",
    "x-wilderness", "x-nca", "x-habitat", "x-flood", "x-tribal", "x-military", "x-wetlands", "x-slope", "x-urban", "x-nps",
    "tech-solar", "tech-wind", "tech-storage", "tech-hydro", "tech-gas", "tech-coal", "tech-nuclear", "tech-geothermal", "tech-other",
    "row-cases", "fiber", "roads", "dc-osm", "water-0", "water-2", "water-3", "water-4", "water-5", "state-line", "county-line",
    "chart-grid", "chart-axis", "queue-hybrid", "queue-solar", "queue-storage", "queue-wind", "queue-gas", "queue-other",
  ].forEach((k) => (T[k] = tok(`--${k}`)));
  T.fly = parseInt(tok("--t-fly"), 10) || 0;
}
const SCORE_T = [0, 60, 70, 80, 90];
const scoreSteps = () => SCORE_T.map((t, k) => [t, T[`score-${k + 1}`]]);
const scoreColor = (s) => { let c = T["score-1"]; for (const [t, col] of scoreSteps()) if (s >= t) c = col; return c; };
const scoreLabel = (k) => (k === 0 ? "under 60" : k === 4 ? "90 and over" : `${SCORE_T[k]} to ${SCORE_T[k + 1]}`);

/* v2 map colours replace v1's layers.json colours, by layer id and category; labels and order are kept. */
const VOLT = { "<115": "kv-lt115", "115-161": "kv-115", "230": "kv-230", "345": "kv-345", "500+": "kv-500", unknown: "kv-unknown" };
const VOLT_W = { "<115": 0.8, "115-161": 1.1, "230": 1.5, "345": 2.0, "500+": 2.6, unknown: 0.8 };
const BLM_CAT = { "Available (2024 Western Solar Plan ROD)": "blm-available", "DRECP Development Focus Area (CA)": "drecp-dfa", "DRECP Variance Land (CA)": "drecp-variance" };
const SEZ_CAT = { Developable: "sez-dev", "Non-developable": "sez-nondev" };
const OWN_CAT = { BLM: "own-blm", USFS: "own-usfs", NPS: "own-nps", DOD: "own-dod", Tribal: "own-tribal", State: "own-state", Other: "own-other", Private: "paper" };
const TECH = { solar: "tech-solar", wind: "tech-wind", storage: "tech-storage", gas: "tech-gas", coal: "tech-coal", nuclear: "tech-nuclear", hydro: "tech-hydro", geothermal: "tech-geothermal", other: "tech-other" };
const EXCL = { excl_wilderness: "x-wilderness", excl_nca_acec: "x-nca", excl_critical_habitat: "x-habitat", excl_flood_zone_a: "x-flood",
  excl_tribal: "x-tribal", excl_military: "x-military", excl_wetlands: "x-wetlands", excl_slope_gt5: "x-slope", excl_urban: "x-urban", excl_nps: "x-nps" };
const SOFT = new Set(["excl_nca_acec", "excl_wetlands"]);
const SINGLE = { blm_solar_row_cases: "row-cases", fiber: "fiber", roads_major: "roads", data_centers_osm: "dc-osm", admin_states: "state-line", admin_counties: "county-line" };
const WATER = [[0, "water-0"], [2, "water-2"], [3, "water-3"], [4, "water-4"], [5, "water-5"]];
const CAT_MAPS = { transmission_lines: VOLT, blm_solar_available: BLM_CAT, solar_energy_zones: SEZ_CAT, ownership: OWN_CAT, power_plants: TECH };

function recolorLayers() {
  for (const L of S.doc.layers) {
    const st = (L.style = L.style || {});
    const cm = CAT_MAPS[L.id];
    if (cm) {
      st.colors = Object.fromEntries(Object.keys(st.colors || cm).map((k) => [k, T[cm[k]] || T["own-other"]]));
      (L.legend || []).forEach((x) => { const k = Object.keys(cm).find((c) => x.label === c || x.label.startsWith(`${c} `) || x.label.startsWith(`${c}-`)); if (k) x.color = T[cm[k]]; });
    }
    if (EXCL[L.id]) { st.color = T[EXCL[L.id]]; L.legend.forEach((x) => (x.color = st.color)); }
    if (SINGLE[L.id]) { st.color = T[SINGLE[L.id]]; (L.legend || []).forEach((x) => (x.color = st.color)); }
    if (L.id === "water_stress") L.legend.forEach((x, k) => (x.color = T[WATER[k] ? WATER[k][1] : "water-5"]));
  }
}

async function getJSON(u) { const r = await fetch(u); if (!r.ok) throw new Error(`${u}: ${r.status}`); return r.json(); }
const setProgress = (p) => { const el = $(".progress"); if (el) el.style.width = `${p}%`; };

/* ---------- column access (strings are dictionary-encoded) ---------- */
function decode(columns) {
  const out = {};
  for (const [k, v] of Object.entries(columns)) {
    if (v && v.dict) { const d = v.dict; out[k] = v.idx.map((i) => (i < 0 ? null : d[i])); }
    else out[k] = v;
  }
  return out;
}
const A = (c, i) => (S.cols[c] ? S.cols[c][i] : null);

/* ---------- boot ---------- */
async function boot() {
  readTokens();
  setProgress(8);
  const [doc, attr, summary, sources, deliv] = await Promise.all([
    getJSON(`${BASE}data/layers.json`), getJSON(`${BASE}data/sites_attr.json`), getJSON(`${BASE}data/summary.json`),
    getJSON(`${BASE}data/sources.json`), getJSON(`${BASE}data/deliverables.json`)]);
  setProgress(45);
  S.doc = doc; S.n = attr.n; S.cols = decode(attr.columns); S.summary = summary; S.sources = sources; S.deliv = deliv;
  recolorLayers();
  S.score = new Float32Array(S.n); S.rank = new Int32Array(S.n); S.show = new Uint8Array(S.n);
  S.weights = { ...doc.sites.weights.solar };
  buildControls();
  buildLayerPanel();
  renderKey();
  renderSources();
  renderDeliverables();
  renderGuide();
  initMap();
}

/* ---------- controls ---------- */
const fillRange = (el) => el.style.setProperty("--p", `${(100 * (el.value - el.min)) / ((el.max - el.min) || 1)}%`);

function buildControls() {
  $("#weights").innerHTML = FACTORS.map(([k, label]) =>
    `<div class="wrow" id="w-row-${k}"><label for="w-${k}">${label}</label><input type="range" min="0" max="50" step="1" id="w-${k}" aria-describedby="weights-hint"><span class="v" id="w-v-${k}"></span></div>`).join("");
  FACTORS.forEach(([k]) => $(`#w-${k}`).addEventListener("input", (e) => { S.weights[k] = +e.target.value; syncWeights(); scheduleRecompute(); }));
  $("#reset-weights").onclick = () => setMode(S.mode, true);
  $$(".seg button").forEach((b) => (b.onclick = () => setMode(b.dataset.mode, true)));

  $("#state-filter").innerHTML = S.doc.states.map((s) => `<label title="${esc(STATE_NAMES[s] || s)}"><input type="checkbox" value="${s}" checked><span>${s}</span></label>`).join("");
  $$("#state-filter input").forEach((i) => (i.onchange = scheduleRecompute));
  [["#f-acres", "#acres-val", (v) => `${fmt(v)} ac`], ["#f-dist", "#dist-val", (v) => `${v} km`], ["#f-score", "#score-val", (v) => `${v}`]].forEach(([id, out, f]) => {
    const el = $(id); const upd = () => { $(out).textContent = f(+el.value); fillRange(el); }; upd();
    el.addEventListener("input", () => { upd(); scheduleRecompute(); });
  });
  ["#f-blm", "#f-prov", "#f-queue"].forEach((id) => ($(id).onchange = scheduleRecompute));
  $("#view-only").onchange = refreshTable;
  $("#export-csv").onclick = exportCSV;

  // tabs: click, arrow keys, and the narrow-screen menu
  const tabs = $$("#tabs button");
  tabs.forEach((b, k) => {
    b.onclick = () => { showView(b.dataset.view); document.body.classList.remove("tabs-open"); };
    b.onkeydown = (e) => {
      const d = { ArrowRight: 1, ArrowLeft: -1 }[e.key]; if (!d) return;
      e.preventDefault(); const nb = tabs[(k + d + tabs.length) % tabs.length]; nb.focus(); showView(nb.dataset.view);
    };
  });
  $("#tabs-menu").onclick = () => { const o = document.body.classList.toggle("tabs-open"); $("#tabs-menu").setAttribute("aria-expanded", o); };
  $("#rail-toggle").onclick = () => toggleRail();
  $("#scrim").onclick = () => toggleRail(false);

  $("#key-toggle").onclick = () => {
    const k = $("#map-key"), c = k.classList.toggle("collapsed");
    $("#key-toggle").textContent = c ? "Show" : "Hide"; $("#key-toggle").setAttribute("aria-expanded", !c);
  };

  // modal: Esc closes, focus is trapped and returned
  $("#modal-close").onclick = closeModal;
  $("#modal").onclick = (e) => { if (e.target.id === "modal") closeModal(); };
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      if (!$("#modal").classList.contains("hidden")) return closeModal();
      if (document.body.classList.contains("rail-open")) return toggleRail(false);
      if (S.selected !== null && $("#view-map").classList.contains("active")) closeScorecard();
    }
    if (e.key === "Tab" && !$("#modal").classList.contains("hidden")) {
      const f = $$("#modal a, #modal button"); if (!f.length) return;
      if (e.shiftKey && document.activeElement === f[0]) { e.preventDefault(); f[f.length - 1].focus(); }
      else if (!e.shiftKey && document.activeElement === f[f.length - 1]) { e.preventDefault(); f[0].focus(); }
    }
  });
  syncWeights();
}

function toggleRail(open) {
  const o = document.body.classList.toggle("rail-open", open);
  $("#rail-toggle").setAttribute("aria-expanded", o); $("#scrim").hidden = !o;
}

function setMode(mode, resetWeights) {
  S.mode = mode;
  $$(".seg button").forEach((b) => { const on = b.dataset.mode === mode; b.classList.toggle("active", on); b.setAttribute("aria-pressed", on); });
  if (resetWeights) S.weights = { ...S.doc.sites.weights[mode] };
  syncWeights(); scheduleRecompute(0);
}

function syncWeights() {
  const sum = Object.values(S.weights).reduce((a, b) => a + b, 0) || 1;
  FACTORS.forEach(([k]) => {
    const el = $(`#w-${k}`); el.value = S.weights[k]; fillRange(el);
    $(`#w-v-${k}`).innerHTML = `${S.weights[k]} <small>${Math.round((100 * S.weights[k]) / sum)}%</small>`;
    $(`#w-row-${k}`).classList.toggle("disabled", S.weights[k] === 0);
  });
  const d = S.doc.sites.weights[S.mode];
  const same = FACTORS.every(([k]) => d[k] === S.weights[k]);
  $("#weights-hint").textContent = (S.mode === "solar"
    ? "Solar ranking: no data center term by default. "
    : "Solar + Data Center ranking: adds fiber (proxy), water and road access. ") +
    (same ? "Weights match the pipeline defaults." : "Custom weights: ranks differ from the Excel and memos.");
}

function filters() {
  return {
    states: new Set($$("#state-filter input:checked").map((i) => i.value)),
    acres: +$("#f-acres").value, dist: +$("#f-dist").value, score: +$("#f-score").value,
    blm: $("#f-blm").checked, prov: $("#f-prov").checked, queue: $("#f-queue").checked,
  };
}

/* ---------- scoring (unchanged from v1) ---------- */
let recomputeTimer = null;
function scheduleRecompute(delay = 120) { clearTimeout(recomputeTimer); recomputeTimer = setTimeout(recompute, delay); }

function recompute() {
  const w = S.weights, sum = FACTORS.reduce((a, [k]) => a + w[k], 0) || 1, f = filters(), c = S.cols;
  const g = c.score_grid, l = c.score_land, su = c.score_sun, p = c.score_permit, dc = c.score_dc;
  const order = [];
  for (let i = 0; i < S.n; i++) {
    const s = ((g[i] || 0) * w.grid + (l[i] || 0) * w.land + (su[i] || 0) * w.sun + (p[i] || 0) * w.permit + (dc[i] || 0) * w.dc) / sum;
    S.score[i] = s;
    const ok = f.states.has(c.state[i]) && c.acres[i] >= f.acres && (c.dist_sub_km[i] ?? 99) <= f.dist && s >= f.score &&
      (!f.blm || c.blm_solar_available[i] === true) && (!f.prov || c.sub_provisional[i] !== true) &&
      (!f.queue || c.queue_confidence[i] === "high");
    S.show[i] = ok ? 1 : 0;
    if (ok) order.push(i);
  }
  order.sort((a, b) => S.score[b] - S.score[a] || c.acres[b] - c.acres[a]);
  S.rank.fill(0); order.forEach((i, k) => (S.rank[i] = k + 1));
  S.order = order;
  $("#filter-count").textContent = `${fmt(order.length)} of ${fmt(S.n)} sites shown`;
  $("#readout-n").textContent = fmt(order.length);
  $("#readout-of").textContent = `of ${fmt(S.n)}`;
  paintSites();
  refreshTable();
  if (S.selected !== null) renderScorecard(S.selected);
  if ($("#view-summary").classList.contains("active")) renderSummary();
}

/* ---------- map ---------- */
let map;
function initMap() {
  const rs = (tiles, attribution, maxzoom = 19) => ({ type: "raster", tiles, tileSize: 256, attribution, maxzoom });
  map = new maplibregl.Map({
    container: "map", center: [-112.5, 36.2], zoom: 4.9, minZoom: 3.5, maxZoom: 16, attributionControl: false,
    style: {
      version: 8, sources: {
        street: rs(["https://tile.openstreetmap.org/{z}/{x}/{y}.png"], "&copy; OpenStreetMap contributors"),
        satellite: rs(["https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"], "Imagery &copy; Esri, Maxar, Earthstar Geographics"),
        terrain: rs(["https://a.tile.opentopomap.org/{z}/{x}/{y}.png", "https://b.tile.opentopomap.org/{z}/{x}/{y}.png", "https://c.tile.opentopomap.org/{z}/{x}/{y}.png"], "&copy; OpenTopoMap (CC-BY-SA), OpenStreetMap contributors", 17),
      },
      layers: [
        { id: "bg", type: "background", paint: { "background-color": T["paper-sunk"] } },
        { id: "base-street", type: "raster", source: "street", paint: { "raster-saturation": -0.9, "raster-contrast": -0.15, "raster-opacity": 0.85 } },
        { id: "base-satellite", type: "raster", source: "satellite", layout: { visibility: "none" }, paint: { "raster-saturation": -0.35, "raster-brightness-max": 0.85 } },
        { id: "base-terrain", type: "raster", source: "terrain", layout: { visibility: "none" }, paint: { "raster-saturation": -0.6 } },
      ],
    },
  });
  map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
  map.addControl(new maplibregl.AttributionControl({ compact: false }), "bottom-right");
  map.addControl(new maplibregl.ScaleControl({ unit: "imperial" }), "bottom-right");
  $$("#basemap input").forEach((r) => (r.onchange = () => {
    ["street", "satellite", "terrain"].forEach((b) => map.setLayoutProperty(`base-${b}`, "visibility", r.value === b ? "visible" : "none"));
  }));
  new ResizeObserver(() => map.resize()).observe($("#map-wrap"));
  map.on("load", async () => {
    homeView();
    addPatterns();
    addOverlayLayers();
    setProgress(60);
    await addSites();
    setProgress(95);
    S.doc.layers.filter((l) => l.on).forEach((l) => setLayerVisible(l.id, true));
    map.on("moveend", refreshTable);
    map.on("click", onMapClick);
    map.on("mousemove", (e) => {
      const f = map.queryRenderedFeatures(e.point, { layers: interactiveLayers() });
      map.getCanvas().style.cursor = f.length ? "pointer" : "";
    });
    recompute();
    setProgress(100);
    document.body.classList.remove("is-loading");
    window.__appReady = true;
  });
}

/* the five states, framed to the right of the map key so nothing starts hidden under it */
function homeView() {
  const key = $("#map-key"), left = key && !key.classList.contains("collapsed") && innerWidth > 760 ? key.offsetWidth + 24 : 24;
  map.fitBounds([[-124.4, 31.3], [-103.0, 42.0]], { padding: { left, right: 48, top: 24, bottom: 24 }, duration: 0 });
}

/* hatch patterns (DRECP variance land, soft exclusions) and the square data center marker, drawn once */
function addPatterns() {
  const draw = (w, h, fn) => { const c = document.createElement("canvas"); c.width = w; c.height = h; const x = c.getContext("2d"); fn(x); return x.getImageData(0, 0, w, h); };
  const hatch = (col) => draw(16, 16, (x) => {
    x.strokeStyle = col; x.lineWidth = 2.2;
    for (const o of [-16, 0, 16]) { x.beginPath(); x.moveTo(o, 16); x.lineTo(o + 16, 0); x.stroke(); }
  });
  map.addImage("hatch-variance", hatch(T["drecp-variance"]), { pixelRatio: 2 });
  map.addImage("hatch-x-nca", hatch(T["x-nca"]), { pixelRatio: 2 });
  map.addImage("hatch-x-wetlands", hatch(T["x-wetlands"]), { pixelRatio: 2 });
  map.addImage("dc-square", draw(18, 18, (x) => { x.fillStyle = T.paper; x.fillRect(0, 0, 18, 18); x.fillStyle = T["dc-osm"]; x.fillRect(2, 2, 14, 14); }), { pixelRatio: 2 });
}

function matchExpr(prop, colors, fallback = T["own-other"]) {
  const e = ["match", ["get", prop]];
  for (const [k, v] of Object.entries(colors)) e.push(k, v);
  e.push(fallback); return e;
}

/* Every overlay is registered at start with an empty source; data is fetched on first toggle. */
function addOverlayLayers() {
  const empty = { type: "FeatureCollection", features: [] };
  const order = ["raster", "fill", "outline", "line", "point"];
  S.mapLayers = {};
  for (const kind of order) {
    for (const L of S.doc.layers.filter((l) => l.kind === kind)) {
      const ids = [];
      if (kind === "raster") {
        map.addSource(L.id, { type: "image", url: BASE + L.file, coordinates: L.bounds });
        map.addLayer({ id: L.id, type: "raster", source: L.id, layout: { visibility: "none" }, paint: { "raster-opacity": 0.72 } });
        ids.push(L.id); S.loaded[L.id] = true;
      } else {
        map.addSource(L.id, { type: "geojson", data: empty });
        layerSpecs(L).forEach((spec) => { map.addLayer({ ...spec, source: L.id, layout: { ...(spec.layout || {}), visibility: "none" } }); ids.push(spec.id); });
      }
      S.mapLayers[L.id] = ids;
    }
    if (kind === "outline" && !map.getLayer("sites-anchor")) map.addLayer({ id: "sites-anchor", type: "background", paint: { "background-opacity": 0 } });
  }
}

const zw = (w) => ["interpolate", ["linear"], ["zoom"], 5, w, 10, ["*", 1.6, w]];

function layerSpecs(L) {
  const st = L.style || {}, id = L.id;
  if (id === "transmission_lines") {
    const width = ["match", ["get", "volt_class"], ...Object.entries(VOLT_W).flat(), 0.8];
    const known = ["!=", ["get", "volt_class"], "unknown"];
    return [
      { id: `${id}-unk`, type: "line", filter: ["!", known], paint: { "line-color": T["kv-unknown"], "line-width": zw(0.8), "line-dasharray": [2, 2] } },
      { id, type: "line", filter: known, layout: { "line-cap": "round", "line-join": "round", "line-sort-key": ["match", ["get", "volt_class"], "500+", 5, "345", 4, "230", 3, "115-161", 2, 1] },
        paint: { "line-color": matchExpr("volt_class", st.colors, T["kv-unknown"]), "line-opacity": 0.95, "line-width": zw(width) } }];
  }
  if (id === "substations") {
    const r = ["interpolate", ["linear"], ["coalesce", ["get", "max_kv"], 69], 69, 1.6, 115, 2.2, 230, 3.2, 345, 4.4, 500, 5.6];
    const prov = ["==", ["get", "provisional"], true], removed = ["to-boolean", ["get", "excluded_reason"]];
    const paint = {
      "circle-radius": ["interpolate", ["linear"], ["zoom"], 4, ["*", 0.8, r], 8, ["*", 1.4, r], 12, ["*", 2.2, r]],
      "circle-color": ["case", removed, T["q-removed"],
        ["<=", ["coalesce", ["get", "queue_active_mw"], 0], 0], T["q-unknown"],
        ["step", ["get", "queue_active_mw"], T["q-lt500"], 500, T["q-500"], 2000, T["q-2000"]]],
      "circle-opacity": ["case", removed, 0.7, 1],
      "circle-stroke-color": ["case", prov, T.prov, removed, T["q-removed"], T["sub-stroke"]],
      "circle-stroke-opacity": ["case", removed, 0.7, 1],
      "circle-stroke-width": ["interpolate", ["linear"], ["zoom"], 5, ["case", prov, 1.4, 0.6], 9, ["case", prov, 2, 1]] };
    // 230 kV+ at every zoom; lower voltages from zoom 7 so the regional view stays readable
    const hi = [">=", ["coalesce", ["get", "max_kv"], 0], 230];
    return [{ id: `${id}-lo`, type: "circle", minzoom: 7, filter: ["!", hi], paint }, { id, type: "circle", filter: hi, paint }];
  }
  if (id === "power_plants") {
    return [{ id, type: "circle", paint: {
      "circle-radius": ["interpolate", ["linear"], ["sqrt", ["coalesce", ["get", "mw"], 1]], 1, 2.5, 10, 4, 40, 8],
      "circle-color": matchExpr("tech", st.colors, T["tech-other"]), "circle-opacity": 0.9, "circle-stroke-color": T.paper, "circle-stroke-width": 0.6 } }];
  }
  if (id === "data_centers_osm") {
    return [{ id, type: "symbol", layout: { "icon-image": "dc-square", "icon-allow-overlap": true, "icon-ignore-placement": true } }];
  }
  if (L.kind === "line") {
    if (id === "fiber") return [{ id, type: "line", paint: { "line-color": st.color, "line-width": 1.2, "line-dasharray": [4, 3] } }];
    return [{ id, type: "line", paint: { "line-color": st.color, "line-width": id === "roads_major" ? 0.9 : 1.2, "line-opacity": 0.8 } }];
  }
  if (L.kind === "outline") {
    const s = id === "admin_states";
    return [{ id, type: "line", paint: { "line-color": st.color, "line-width": s ? 1.2 : 0.5, "line-opacity": s ? 0.85 : 0.8 } }];
  }
  // fills
  if (id === "blm_solar_available") {
    const variance = ["==", ["get", "category"], "DRECP Variance Land (CA)"];
    const col = matchExpr("category", st.colors, T["blm-available"]);
    return [
      { id, type: "fill", paint: { "fill-color": col, "fill-opacity": ["case", variance, 0.18, 0.3] } },
      { id: `${id}-hatch`, type: "fill", filter: variance, paint: { "fill-pattern": "hatch-variance", "fill-opacity": 0.7 } },
      { id: `${id}-edge`, type: "line", paint: { "line-color": col, "line-width": 1, "line-opacity": 0.8 } }];
  }
  if (id === "solar_energy_zones") {
    const dev = ["==", ["get", "status"], "Developable"];
    return [
      { id, type: "fill", filter: dev, paint: { "fill-color": T["sez-dev"], "fill-opacity": 0.1 } },
      { id: `${id}-edge`, type: "line", filter: dev, paint: { "line-color": T["sez-dev"], "line-width": 1.6 } },
      { id: `${id}-edge2`, type: "line", filter: ["!", dev], paint: { "line-color": T["sez-nondev"], "line-width": 1, "line-dasharray": [3, 2] } }];
  }
  if (id === "ownership") {
    const priv = ["==", ["get", "category"], "Private"];
    const col = matchExpr("category", st.colors);
    return [
      { id, type: "fill", paint: { "fill-color": col, "fill-opacity": ["case", priv, 0, 0.4] } },
      { id: `${id}-edge`, type: "line", paint: { "line-color": col, "line-width": 0.5, "line-opacity": ["case", priv, 0, 0.6] } }];
  }
  if (id === "water_stress") {
    const col = ["interpolate", ["linear"], ["coalesce", ["get", "water_stress"], 0], ...WATER.flatMap(([v, k]) => [v, T[k]])];
    return [{ id, type: "fill", paint: { "fill-color": col, "fill-opacity": 0.35 } },
      { id: `${id}-edge`, type: "line", paint: { "line-color": col, "line-width": 0.5, "line-opacity": 0.6 } }];
  }
  if (SOFT.has(id)) {
    return [{ id, type: "fill", paint: { "fill-pattern": `hatch-${EXCL[id]}`, "fill-opacity": 0.5 } },
      { id: `${id}-edge`, type: "line", paint: { "line-color": st.color, "line-width": 1, "line-dasharray": [3, 2], "line-opacity": 0.9 } }];
  }
  const op = id === "blm_solar_row_cases" ? 0.25 : 0.22;
  return [{ id, type: "fill", paint: { "fill-color": st.color, "fill-opacity": op } },
    { id: `${id}-edge`, type: "line", paint: { "line-color": st.color, "line-width": id === "blm_solar_row_cases" ? 1.2 : 1, "line-opacity": 0.85 } }];
}

const SITE_LAYERS = ["sites-fill", "sites-edge", "sites-pt", "sites-sel-halo", "sites-sel"];
async function setLayerVisible(id, on) {
  if (id === "sites") { SITE_LAYERS.forEach((l) => map.setLayoutProperty(l, "visibility", on ? "visible" : "none")); return; }
  const L = S.doc.layers.find((l) => l.id === id);
  if (on && !S.loaded[id]) {
    const tag = $(`#ltag-${id}`); if (tag) { tag.textContent = "loading"; tag.classList.add("busy"); }
    const data = await getJSON(BASE + L.file);
    map.getSource(id).setData(data); S.loaded[id] = true;
    if (tag) { tag.textContent = "Source"; tag.classList.remove("busy"); }
  }
  (S.mapLayers[id] || []).forEach((l) => map.setLayoutProperty(l, "visibility", on ? "visible" : "none"));
  // free heavy layers when switched off so a laptop with little memory can browse every layer in turn
  if (!on && S.loaded[id] && L.kind !== "raster" && (L.mb || 0) > 3) {
    map.getSource(id).setData({ type: "FeatureCollection", features: [] }); S.loaded[id] = false;
  }
}

async function addSites() {
  const geom = await getJSON(BASE + S.doc.sites.geom);
  map.addSource("sites", { type: "geojson", data: geom, promoteId: "i" });
  const pts = { type: "FeatureCollection", features: [] };
  for (let i = 0; i < S.n; i++) pts.features.push({ type: "Feature", properties: { i }, geometry: { type: "Point", coordinates: [A("centroid_lon", i), A("centroid_lat", i)] } });
  map.addSource("sites-pts", { type: "geojson", data: pts, promoteId: "i" });
  const ramp = ["step", ["coalesce", ["feature-state", "score"], 0]]; scoreSteps().forEach(([t, c], k) => { if (k === 0) ramp.push(c); else ramp.push(t, c); });
  const hidden = ["boolean", ["feature-state", "hide"], false];
  map.addLayer({ id: "sites-fill", type: "fill", source: "sites", minzoom: 7,
    paint: { "fill-color": ramp, "fill-opacity": ["case", hidden, 0, 0.78] } }, "sites-anchor");
  map.addLayer({ id: "sites-edge", type: "line", source: "sites", minzoom: 7,
    paint: { "line-color": T["site-edge"], "line-width": 0.6, "line-opacity": ["case", hidden, 0, 0.6] } }, "sites-anchor");
  map.addLayer({ id: "sites-pt", type: "circle", source: "sites-pts", maxzoom: 7.5,
    paint: { "circle-radius": ["interpolate", ["linear"], ["zoom"], 4, 2.2, 7, 4], "circle-color": ramp,
      "circle-opacity": ["case", hidden, 0, 0.92], "circle-stroke-color": T.paper,
      "circle-stroke-width": ["case", hidden, 0, 0.5], "circle-stroke-opacity": ["case", hidden, 0, 0.9] } }, "sites-anchor");
  const none = ["==", ["get", "i"], -1];
  map.addLayer({ id: "sites-sel-halo", type: "line", source: "sites", filter: none, paint: { "line-color": T.paper, "line-width": 6 } }, "sites-anchor");
  map.addLayer({ id: "sites-sel", type: "line", source: "sites", filter: none, paint: { "line-color": T["site-selected"], "line-width": 3 } }, "sites-anchor");
  // keep point layers (substations, plants) and boundaries above the sites
  ["admin_states", "admin_counties", "substations", "power_plants", "data_centers_osm"].forEach((id) => (S.mapLayers[id] || []).forEach((l) => map.moveLayer(l)));
  S.fs.score = new Float32Array(S.n).fill(-1); S.fs.hide = new Int8Array(S.n).fill(-1);
}

function paintSites() {
  if (!map || !map.getSource("sites")) return;
  for (let i = 0; i < S.n; i++) {
    const sc = Math.round(S.score[i] * 10) / 10, hide = S.show[i] ? 0 : 1;
    if (S.fs.score[i] !== sc || S.fs.hide[i] !== hide) {
      const st = { score: sc, hide: !!hide };
      map.setFeatureState({ source: "sites", id: i }, st);
      map.setFeatureState({ source: "sites-pts", id: i }, st);
      S.fs.score[i] = sc; S.fs.hide[i] = hide;
    }
  }
}

function interactiveLayers() {
  const ids = ["sites-fill", "sites-pt"];
  for (const L of S.doc.layers) if (L.kind !== "raster" && L.kind !== "outline") ids.push(...(S.mapLayers[L.id] || []));
  return ids.filter((id) => map.getLayer(id) && map.getLayoutProperty(id, "visibility") !== "none");
}

const baseLayerId = (id) => id.replace(/-(edge2|edge|hatch|unk|lo)$/, "");
function onMapClick(e) {
  const box = [[e.point.x - 4, e.point.y - 4], [e.point.x + 4, e.point.y + 4]];
  const feats = map.queryRenderedFeatures(box, { layers: interactiveLayers() });
  const site = feats.find((f) => (f.layer.id === "sites-fill" || f.layer.id === "sites-pt") && S.show[f.properties.i]);
  const pointHit = feats.find((f) => ["substations", "substations-lo", "power_plants", "data_centers_osm"].includes(f.layer.id));
  if (pointHit) return popup(e.lngLat, pointHit);
  if (site) return selectSite(site.properties.i, false);
  const other = feats.find((f) => !f.layer.id.startsWith("sites"));
  if (other) popup(e.lngLat, other);
}

const POP_FIELDS = {
  substations: [["max_kv", "Max kV"], ["min_kv", "Min kV"], ["owner", "Owner"], ["status", "Status"], ["sub_type", "Type"], ["lines", "Lines"],
    ["queue_active_mw", "Active queue MW (POI name match)"], ["queue_n_active", "Active requests matched"], ["source", "Record source"], ["kv_source", "kV source"], ["county", "County"]],
  power_plants: [["tech", "Technology"], ["mw", "MW"], ["status", "Status"], ["utility", "Utility"], ["grid_voltage_kv", "Grid voltage kV"], ["first_operating_year", "First year"], ["county", "County"]],
};
function popup(lngLat, f) {
  const p = f.properties, id = baseLayerId(f.layer.id);
  const L = S.doc.layers.find((l) => l.id === id);
  const title = p.name || p.plant || p.project_name || p.category || p.constraint || p.sez_name || p.agency || (L && L.title) || id;
  const rows = POP_FIELDS[id] ? POP_FIELDS[id].map(([k, lab]) => [lab, p[k]]) : Object.entries(p).filter(([k]) => k !== "i");
  let tags = "";
  if (id === "substations") {
    if (p.provisional === true || p.provisional === "true") tags += `<span class="tag prov">Provisional record</span>`;
    if (p.excluded_reason) tags += `<span class="tag warn">Removed as POI: ${esc(p.excluded_reason)}</span>`;
  }
  const html = `<div class="pop-title">${esc(title)}</div><div class="pop-sub">${esc(L ? L.title : id)}</div>${tags ? `<div class="pop-tags">${tags}</div>` : ""}
    <table class="pop">${rows.filter(([, v]) => v !== null && v !== undefined && v !== "").map(([k, v]) => `<tr><td>${esc(k)}</td><td>${esc(typeof v === "number" ? fmt(v, v % 1 ? 1 : 0) : v)}</td></tr>`).join("")}</table>`;
  new maplibregl.Popup({ maxWidth: "320px" }).setLngLat(lngLat).setHTML(html).addTo(map);
}

/* ---------- swatches shared by the map key and the guide ---------- */
function sw(color, kind = "", extra = "") {
  let bg = `background:${color}`;
  if (kind === "hatch") bg = `background:repeating-linear-gradient(45deg,${color} 0 1.5px,transparent 1.5px 4px);box-shadow:inset 0 0 0 1px ${color}`;
  if (kind === "dash") bg = `background:repeating-linear-gradient(90deg,${color} 0 4px,transparent 4px 7px)`;
  if (kind === "outline") bg = `background:transparent;box-shadow:inset 0 0 0 1.5px ${color}`;
  if (kind === "dashoutline") bg = `background:transparent;outline:1px dashed ${color};outline-offset:-1px`;
  const cls = { line: "line", dash: "line", dot: "dot", ring: "dot", sq: "sq" }[kind] || "";
  return `<i class="sw ${cls}" style="${bg};${extra}"></i>`;
}
const subDot = (fill, stroke = "", size = 9) => sw(fill, "dot", `width:${size}px;height:${size}px;${stroke ? `box-shadow:inset 0 0 0 ${stroke}` : ""}`);
const ramp = (cols, ticks) => `<div class="ramp">${cols.map((c) => `<i style="background:${c}"></i>`).join("")}</div>
  <div class="ticks">${ticks.map((t) => `<span>${esc(t)}</span>`).join("")}</div>`;
const lineRamp = () => `<div class="ramp lines">${["kv-lt115", "kv-115", "kv-230", "kv-345", "kv-500"].map((k, n) => `<i style="background:${T[k]};height:${[1, 1.5, 2, 2.5, 3][n]}px"></i>`).join("")}</div>
  <div class="ticks"><span>&lt;115</span><span>115</span><span>230</span><span>345</span><span>500+</span></div>`;
const cats = (items) => `<div class="cats ${items.length > 4 ? "two" : ""}">${items.map(([s, l]) => `<span>${s}<span>${esc(l)}</span></span>`).join("")}</div>`;

/* the key for one layer, drawn like the key printed in the corner of a paper map */
function keyFor(id) {
  if (id === "sites") {
    return ramp(scoreSteps().map(([, c]) => c), ["<60", "60", "70", "80", "90+"]) +
      `<div class="dots" style="margin-top:6px"><span>${sw(T["score-5"], "", `width:14px;height:9px;box-shadow:inset 0 0 0 2px ${T.ink}`)}selected site (black outline, white halo)</span></div>
      <div class="kg-note">Points below zoom 7, polygons above. Colour = current blended score.</div>`;
  }
  const L = S.doc.layers.find((l) => l.id === id);
  let body = "";
  const lg = L.legend || [];
  if (id === "transmission_lines") body = lineRamp() + `<div class="dots" style="margin-top:6px"><span>${sw(T["kv-unknown"], "dash")}unknown kV</span></div>`;
  else if (id === "substations") {
    body = `<div class="dots">
      <span>${subDot(T["q-unknown"], `1px ${T["sub-stroke"]}`)}unknown</span><span>${subDot(T["q-lt500"])}&lt;500</span>
      <span>${subDot(T["q-500"])}500+</span><span>${subDot(T["q-2000"])}2,000+</span></div>
      <div class="dots" style="margin-top:4px"><span>${subDot(T.paper, `2px ${T.prov}`)}provisional</span>
      <span>${subDot(T["q-removed"])}removed as POI</span><span>size = kV</span></div>`;
  } else if (id === "water_stress") body = ramp(WATER.map(([, k]) => T[k]), WATER.map(([v]) => String(v))) + `<div class="kg-note">${esc(lg[0].label)} to ${esc(lg[lg.length - 1].label)}</div>`;
  else if (L.kind === "raster") body = ramp(lg.map((x) => x.color), lg.map((x) => x.label));
  else if (id === "blm_solar_available") body = cats(lg.map((x) => [sw(x.color, x.label.startsWith("DRECP Variance") ? "hatch" : ""), x.label]));
  else if (id === "solar_energy_zones") body = cats([[sw(T["sez-dev"], "outline"), "Developable"], [sw(T["sez-nondev"], "dashoutline"), "Non-developable"]]);
  else if (id === "ownership") body = cats(lg.map((x) => [x.label.startsWith("Private") ? sw(T.paper, "outline", `box-shadow:inset 0 0 0 1px ${T["rule-strong"]}`) : sw(x.color), x.label]));
  else if (EXCL[id]) body = cats(lg.map((x) => [sw(x.color, SOFT.has(id) ? "hatch" : ""), SOFT.has(id) ? "soft constraint (hatched)" : x.label]));
  else if (id === "data_centers_osm") body = cats(lg.map((x) => [sw(x.color, "sq", `outline:1px solid ${T.paper}`), x.label]));
  else if (id === "power_plants") body = cats(lg.map((x) => [sw(x.color, "dot", "width:8px;height:8px"), x.label]));
  else if (L.kind === "line" || L.kind === "outline") body = cats(lg.map((x) => [sw(x.color, x.dash ? "dash" : "line"), x.label]));
  else body = cats(lg.map((x) => [sw(x.color), x.label]));
  return body + (L.note ? `<div class="kg-note">${esc(L.note)}</div>` : "");
}

function renderKey() {
  const on = $$("#layer-list input[data-layer]:checked").map((c) => c.dataset.layer);
  const title = (id) => (id === "sites" ? "Candidate sites, by score" : S.doc.layers.find((l) => l.id === id).title);
  $("#key-groups").innerHTML = on.length
    ? on.map((id) => `<div class="kg" data-key="${id}"><div class="kg-t">${esc(title(id))}</div>${keyFor(id)}</div>`).join("")
    : `<div class="kg"><div class="kg-note">No layers are on. Switch layers on in the left column.</div></div>`;
}

/* ---------- layer panel ---------- */
function buildLayerPanel() {
  const groups = {};
  S.doc.layers.forEach((L) => (groups[L.group] = groups[L.group] || []).push(L));
  const item = (id, title, on) => `<div class="litem ${on ? "on" : ""}" id="li-${id}"><label><input type="checkbox" data-layer="${id}" ${on ? "checked" : ""}> ${esc(title)}</label>
    <button class="src" id="ltag-${id}" data-info="${id}" aria-label="Source and caveats: ${esc(title)}">Source</button></div>`;
  let html = `<div class="lgroup"><div class="caps lgroup-title">Screening result</div>${item("sites", "Candidate sites (by score)", true)}</div>`;
  for (const [g, list] of Object.entries(groups)) html += `<div class="lgroup"><div class="caps lgroup-title">${esc(g)}</div>${list.map((L) => item(L.id, L.title, L.on)).join("")}</div>`;
  $("#layer-list").innerHTML = html;
  $$("#layer-list input[data-layer]").forEach((cb) => (cb.onchange = () => {
    cb.closest(".litem").classList.toggle("on", cb.checked);
    renderKey();
    setLayerVisible(cb.dataset.layer, cb.checked);
  }));
  $$("#layer-list .src").forEach((b) => (b.onclick = () => showMeta(b.dataset.info, b)));
}

let modalReturn = null;
function showMeta(id, from) {
  const L = id === "sites" ? { title: "Candidate sites", meta: S.doc.sites.meta } : S.doc.layers.find((l) => l.id === id);
  const m = L.meta || {};
  const row = (k, v) => `<dt>${k}</dt><dd>${v}</dd>`;
  $("#modal-body").innerHTML = `<h3 id="modal-title">${esc(L.title)}</h3>
    <dl class="kv">${row("Source", esc(m.source_name || "not recorded"))}
    ${m.source_url ? row("URL", `<a href="${esc(m.source_url)}" target="_blank" rel="noopener">${esc(m.source_url)}</a>`) : ""}
    ${row("Retrieved", esc(m.retrieved || "n/a"))}
    ${row("Records (processed)", fmt(m.record_count))}
    ${L.features !== undefined ? row("Features in app copy", `${fmt(L.features)} <small>(${L.mb} MB, simplified for display)</small>`) : ""}
    ${row("Processed file", esc(m.path || ""))}
    ${row("Caveats", esc(m.caveats || "none recorded"))}</dl>`;
  modalReturn = from || document.activeElement;
  $("#modal").classList.remove("hidden");
  $("#modal-close").focus();
}
function closeModal() { $("#modal").classList.add("hidden"); if (modalReturn) modalReturn.focus(); }

/* ---------- selection and scorecard ---------- */
function selectSite(i, fly = true) {
  S.selected = i;
  const f = ["==", ["get", "i"], i];
  map.setFilter("sites-sel", f); map.setFilter("sites-sel-halo", f);
  if (fly) {
    const o = { center: [A("centroid_lon", i), A("centroid_lat", i)], zoom: Math.max(map.getZoom(), 10) };
    if (REDUCED) map.jumpTo(o); else map.flyTo({ ...o, duration: T.fly });
  }
  renderScorecard(i);
  $$("#site-table tbody tr").forEach((tr) => tr.classList.toggle("sel", +tr.dataset.i === i));
  const row = $(`#site-table tbody tr[data-i="${i}"]`); if (row) row.scrollIntoView({ block: "nearest" });
}

function closeScorecard() {
  $("#scorecard").classList.add("hidden"); document.body.classList.remove("sheet-open");
  S.selected = null; map.setFilter("sites-sel", ["==", ["get", "i"], -1]); map.setFilter("sites-sel-halo", ["==", ["get", "i"], -1]);
  $$("#site-table tbody tr.sel").forEach((tr) => tr.classList.remove("sel"));
}

function memoFor(siteId) { return (S.deliv.memos || []).find((m) => m.site_id === siteId); }

function renderScorecard(i) {
  const el = $("#scorecard"); el.classList.remove("hidden"); document.body.classList.add("sheet-open");
  const v = (c) => A(c, i);
  const w = S.weights, prov = v("sub_provisional") === true, blm = v("blm_solar_available") === true;
  const fact = (color, text) => `<span class="fact">${sw(color)}${text}</span>`;
  const facts = [
    blm ? fact(T["blm-available"], "BLM solar-available") : fact(T["rule-strong"], `${esc(v("owner_category"))} land`),
    v("sez_name") ? fact(T["sez-dev"], `SEZ: ${esc(v("sez_name"))}`) : "",
    prov ? `<span class="tag prov">Provisional substation</span>` : fact(T.ink, "HIFLD substation"),
    v("queue_confidence") === "high" ? fact(T.accent, "Queue data: high confidence") : `<span class="tag warn">Queue data: low confidence</span>`,
    v("row_cases_overlap") ? `<span class="tag warn">Overlaps active BLM ROW case</span>` : "",
  ].join("");
  const bars = FACTORS.map(([k, label, col]) => {
    const s = v(col) ?? 0, on = w[k] > 0;
    return `<div class="fx ${on ? "" : "off"}"><span>${label}</span><span class="wt">${w[k]}</span><span class="tr"><i style="width:${Math.max(0, Math.min(100, s))}%;background:${on ? scoreColor(s) : T["rule-strong"]}"></i></span><span class="val">${fmt(s, 0)}</span></div>`;
  }).join("");
  const row = (k, val) => `<dt>${k}</dt><dd>${val}</dd>`;
  const cons = (v("constraints_soft") || "").split(/;\s*/).filter(Boolean);
  const memo = memoFor(v("site_id"));
  const rk = S.rank[i];
  $("#sc-inner").innerHTML = `<div class="sc-id"><span>${esc(v("site_id"))}</span><button class="textbtn" id="sc-close">Close</button></div>
    <h2 class="sc-place">${esc(v("county"))} County, ${esc(STATE_NAMES[v("state")] || v("state"))}</h2>
    <div class="sc-hero"><span class="sc-score">${fmt(S.score[i], 1)}</span>
      <span class="sc-rank">${rk ? `Rank ${fmt(rk)} of ${fmt(S.order.length)}` : "Hidden by current filters"}
        <small>${rk ? "in the current view of filters. " : ""}Pipeline ranks: solar #${fmt(v("rank_solar"))} (${fmt(v("score_total_solar"), 1)}), Solar + Data Center #${fmt(v("rank_dc"))} (${fmt(v("score_total_dc"), 1)})</small></span></div>
    <div class="sc-facts">${facts}</div>
    ${prov ? `<p class="note prov">The nearest substation record is provisional (${esc(v("sub_source"))} record, kV from ${esc(v("sub_kv_source"))}). Its grid score was multiplied by 0.85. Confirm the substation exists, its operating voltage and owner with the utility before relying on this site.</p>` : ""}
    <h3 class="caps sc-h">Score by factor (0 to 100, weight shown)</h3>${bars}
    <h3 class="caps sc-h">Site</h3>
    <dl class="kv">
      ${row("Acres", `${fmt(v("acres"))} ac <small>about ${fmt(v("solar_mw_est"))} MW at 6 ac/MW</small>`)}
      ${row("Surface owner", esc(v("owner_category")))}
      ${row("BLM status", esc(v("blm_status") || "not BLM solar land"))}
      ${row("GHI", `${fmt(v("ghi"), 2)} kWh/m2/day`)}
      ${row("Mean slope", `${fmt(v("mean_slope"), 1)} percent`)}
      ${row("Centroid", `${fmt(v("centroid_lat"), 4)}, ${fmt(v("centroid_lon"), 4)}`)}
    </dl>
    <h3 class="caps sc-h">Grid connection</h3>
    <dl class="kv">
      ${row("Nearest 115 kV+ substation", `${esc(v("nearest_sub_name"))}${prov ? ' <span class="tag prov">provisional</span>' : ""}<small class="blk">${fmt(v("nearest_sub_kv"))} kV, ${fmt(v("dist_sub_km"), 1)} km, ${esc(v("nearest_sub_owner") || "owner unknown")}</small>`)}
      ${row("Nearest 230 kV+ substation", `${esc(v("nearest_sub230_name") || "n/a")}<small class="blk">${fmt(v("nearest_sub230_kv"))} kV, ${fmt(v("dist_sub230_km"), 1)} km</small>`)}
      ${row("Nearest 115 kV+ line", `${fmt(v("nearest_line_kv"))} kV, ${fmt(v("dist_line_km"), 1)} km`)}
      ${row("Active queue in county", `${fmt(v("queued_mw_county"))} MW <small>solar ${fmt(v("queued_mw_county_solar"))}, storage ${fmt(v("queued_mw_county_storage"))}</small>`)}
      ${row("Queued at nearest substation", `${fmt(v("nearest_sub_queue_mw"))} MW <small class="blk">POI name match; 0 can mean no match</small>`)}
      ${row("Queue confidence", `${esc(v("queue_confidence"))} <small class="blk">${fmt(100 * (v("queue_poi_match_rate") || 0))} percent of county requests matched to a POI</small>`)}
    </dl>
    <h3 class="caps sc-h">Data center fit</h3>
    <dl class="kv">
      ${row("Fiber (proxy)", `${fmt(v("fiber_km"), 1)} km <small class="blk">${esc(v("fiber_basis") || "")}</small>`)}
      ${row("Water stress", `${fmt(v("water_stress"), 1)} of 5 <small>${esc(v("water_stress_label") || "")}</small>`)}
      ${row("Major road", `${fmt(v("road_km"), 1)} km <small>${esc(v("road_name") || "")}</small>`)}
      ${row("Data center score", fmt(v("score_dc"), 0))}
    </dl>
    <h3 class="caps sc-h">Constraints hit (soft)</h3>
    <div class="sc-cons">${cons.length ? cons.map((c) => `<span class="tag warn">${esc(c.replace(/_/g, " "))}</span>`).join("") : '<span class="muted">none flagged</span>'}</div>
    <h3 class="caps sc-h">Recommended next step</h3>
    <p class="note">${esc(v("next_step") || "")}</p>
    <div class="sc-actions">
      <button class="btn primary" id="sc-zoom">Zoom to site</button>
      ${memo ? `<a class="btn" href="${DOC}${encodeURIComponent(memo.href)}" target="_blank">Open site memo</a>` : ""}
      ${blm ? `<a class="btn" href="${DOC}${encodeURIComponent("../deliverables/BLM_Application_Brief.md")}" target="_blank">BLM application brief</a>` : ""}
    </div>`;
  $("#sc-close").onclick = closeScorecard;
  $("#sc-zoom").onclick = () => { const o = { center: [v("centroid_lon"), v("centroid_lat")], zoom: 11.5 }; if (REDUCED) map.jumpTo(o); else map.flyTo({ ...o, duration: T.fly }); };
}

/* ---------- table ---------- */
const TCOLS = [
  ["rank", "Rank", (i) => S.rank[i], true], ["score", "Score", (i) => S.score[i], true, 1],
  ["site_id", "Site", (i) => A("site_id", i)], ["state", "State", (i) => A("state", i)], ["county", "County", (i) => A("county", i)],
  ["acres", "Acres", (i) => A("acres", i), true], ["owner_category", "Owner", (i) => A("owner_category", i)],
  ["blm", "BLM avail.", (i) => (A("blm_solar_available", i) ? "yes" : "")],
  ["nearest_sub_name", "Substation", (i) => A("nearest_sub_name", i)], ["nearest_sub_kv", "kV", (i) => A("nearest_sub_kv", i), true],
  ["dist_sub_km", "Sub km", (i) => A("dist_sub_km", i), true, 1], ["prov", "Grid data", (i) => (A("sub_provisional", i) ? "provisional" : "")],
  ["queued_mw_county", "County queue MW", (i) => A("queued_mw_county", i), true], ["ghi", "GHI", (i) => A("ghi", i), true, 2],
  ["score_grid", "Grid", (i) => A("score_grid", i), true], ["score_land", "Land", (i) => A("score_land", i), true],
  ["score_sun", "Sun", (i) => A("score_sun", i), true], ["score_permit", "Permit", (i) => A("score_permit", i), true],
  ["score_dc", "DC", (i) => A("score_dc", i), true]];

function currentRows() {
  if (!$("#view-only").checked || !map) return S.order.slice();
  const b = map.getBounds();
  return S.order.filter((i) => b.contains([A("centroid_lon", i), A("centroid_lat", i)]));
}

function refreshTable() {
  if (!S.score) return;
  const rows = currentRows();
  const col = TCOLS.find((c) => c[0] === S.sort.key) || TCOLS[0], get = col[2], d = S.sort.dir;
  if (col[0] !== "rank") rows.sort((a, b) => { const x = get(a), y = get(b); if (x === y) return 0; if (x === null || x === undefined) return 1; if (y === null || y === undefined) return -1; return (x < y ? -1 : 1) * d; });
  else if (d < 0) rows.reverse();
  S.viewRows = rows;
  $("#table-title").textContent = S.mode === "solar" ? "Ranked sites: Solar" : "Ranked sites: Solar + Data Center";
  $("#table-count").textContent = `${fmt(rows.length)} sites${rows.length > MAX_ROWS ? `, first ${MAX_ROWS} listed; CSV has all` : ""}`;
  $("#site-table thead").innerHTML = `<tr>${TCOLS.map(([k, lab, , num]) => `<th data-k="${k}" class="${num ? "num" : ""} ${S.sort.key === k ? "sorted" : ""}" aria-sort="${S.sort.key === k ? (S.sort.dir > 0 ? "ascending" : "descending") : "none"}">${lab}${S.sort.key === k ? (S.sort.dir > 0 ? " ↑" : " ↓") : ""}</th>`).join("")}</tr>`;
  $$("#site-table th").forEach((th) => (th.onclick = () => {
    const k = th.dataset.k; if (S.sort.key === k) S.sort.dir *= -1; else { S.sort.key = k; S.sort.dir = ["rank", "site_id", "state", "county", "owner_category", "nearest_sub_name", "dist_sub_km", "queued_mw_county"].includes(k) ? 1 : -1; }
    refreshTable();
  }));
  $("#site-table tbody").innerHTML = rows.slice(0, MAX_ROWS).map((i) => `<tr data-i="${i}" class="${i === S.selected ? "sel" : ""}">${TCOLS.map(([k, , g, num, dp]) => {
    const val = g(i);
    if (k === "score") return `<td class="num"><span class="chip" style="background:${scoreColor(val)}"></span>${fmt(val, 1)}</td>`;
    if (k === "site_id") return `<td class="id">${esc(val)}</td>`;
    if (k === "nearest_sub_name" && A("sub_provisional", i)) return `<td>${esc(val ?? "")}<span class="ring" title="provisional substation record"></span></td>`;
    if (k === "prov" && val) return `<td><span class="tag prov">provisional</span></td>`;
    return `<td class="${num ? "num" : ""}">${num ? fmt(val, dp || 0) : esc(val ?? "")}</td>`;
  }).join("")}</tr>`).join("");
  $$("#site-table tbody tr").forEach((tr) => (tr.onclick = () => selectSite(+tr.dataset.i, true)));
}

function exportCSV() {
  const fields = Object.keys(S.cols);
  const head = ["view_rank", "view_score", "ranking", ...fields];
  const q = (v) => { if (v === null || v === undefined) return ""; const s = String(v); return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s; };
  const lines = [head.join(",")];
  for (const i of S.viewRows) lines.push([S.rank[i], S.score[i].toFixed(2), S.mode, ...fields.map((f) => A(f, i))].map(q).join(","));
  const w = S.weights;
  const blob = new Blob([lines.join("\n") + "\n"], { type: "text/csv" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `southwest_sites_${S.mode}_g${w.grid}-l${w.land}-s${w.sun}-p${w.permit}-d${w.dc}_${S.viewRows.length}.csv`;
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 4000);
}

/* ---------- views ---------- */
const VIEW_NAMES = { map: "Map", summary: "Summary", sources: "Sources and Limits", deliverables: "Deliverables", guide: "How to Read This" };
function showView(v) {
  $$("#tabs button").forEach((b) => { const on = b.dataset.view === v; b.classList.toggle("active", on); b.setAttribute("aria-selected", on); b.tabIndex = on ? 0 : -1; });
  $$(".view").forEach((s) => s.classList.toggle("active", s.id === `view-${v}`));
  document.body.dataset.view = v;
  $("#tabs-menu-label").textContent = VIEW_NAMES[v];
  if (v === "summary") renderSummary();
  if (v === "map" && map) setTimeout(() => map.resize(), 0);
}

/* ---------- summary charts ---------- */
const TYPE_ORDER = ["hybrid", "solar", "storage", "wind", "gas", "other"];
const htmlKey = (items) => items.map(([c, l]) => `<span>${sw(c)}${esc(l)}</span>`).join("");
function chart(id, cfg) {
  if (S.charts[id]) S.charts[id].destroy();
  const d = Chart.defaults;
  d.font.family = '"IBM Plex Sans", "Helvetica Neue", Arial, sans-serif'; d.font.size = 12; d.color = T.muted; d.animation = false;
  Object.assign(d.plugins.tooltip, { backgroundColor: T.paper, titleColor: T.ink, bodyColor: T["ink-2"], borderColor: T["rule-strong"], borderWidth: 1,
    cornerRadius: 2, caretSize: 5, padding: 8, displayColors: true, boxWidth: 8, boxHeight: 8, titleFont: { weight: 500 } });
  d.plugins.legend.display = false;
  S.charts[id] = new Chart($(`#${id}`), cfg);
}
const yGrid = { grid: { color: () => T["chart-grid"], drawTicks: false }, border: { display: false }, ticks: { padding: 6 } };
const xPlain = { grid: { display: false }, border: { display: false } };
const endRadius = { topLeft: 2, topRight: 2, bottomLeft: 0, bottomRight: 0 };
const barLabels = { id: "barLabels", afterDatasetsDraw(c) {
  const ctx = c.ctx; ctx.save(); ctx.font = `11px ${Chart.defaults.font.family}`; ctx.fillStyle = T["ink-2"]; ctx.textBaseline = "middle";
  c.getDatasetMeta(0).data.forEach((b, k) => ctx.fillText(fmt(c.data.datasets[0].data[k]), b.x + 4, b.y));
  ctx.restore(); } };

function renderSummary() {
  const st = S.doc.states, o = S.order;
  const acres = o.reduce((a, i) => a + A("acres", i), 0), mw = o.reduce((a, i) => a + (A("solar_mw_est", i) || 0), 0);
  const blmN = o.filter((i) => A("blm_solar_available", i)).length, provN = o.filter((i) => A("sub_provisional", i)).length;
  const stats = [["Sites passing filters", fmt(o.length)], ["Total acres", `${fmt(acres / 1e6, 1)}<small>million</small>`], ["Solar MW potential (6 ac/MW)", `${fmt(mw / 1000, 1)}<small>GW</small>`],
    ["BLM solar-available sites", fmt(blmN)], ["On provisional substations", fmt(provN)]];
  $("#tiles").innerHTML = stats.map(([t, n]) => `<div class="stat"><div class="n">${n}</div><div class="t">${t}</div></div>`).join("");

  const byState = st.map((s) => o.filter((i) => A("state", i) === s).length);
  const blmState = st.map((s) => o.filter((i) => A("state", i) === s && A("blm_solar_available", i)).length);
  const bar = { borderRadius: endRadius, borderSkipped: "bottom", maxBarThickness: 28, categoryPercentage: 0.7, barPercentage: 0.92 };
  $("#k-state").innerHTML = htmlKey([[T["score-3"], "All candidate sites"], [T["blm-available"], "BLM solar-available"]]);
  chart("c-state", { type: "bar", data: { labels: st, datasets: [
    { label: "All candidate sites", data: byState, backgroundColor: T["score-3"], ...bar },
    { label: "BLM solar-available", data: blmState, backgroundColor: T["blm-available"], ...bar }] },
    options: { maintainAspectRatio: false, scales: { x: { ...xPlain, ticks: { color: T["ink-2"] } }, y: { ...yGrid, beginAtZero: true } } } });

  const bins = []; for (let b = 0; b < 100; b += 5) bins.push(b);
  const counts = bins.map(() => 0); o.forEach((i) => counts[Math.min(19, Math.floor(S.score[i] / 5))]++);
  const first = counts.findIndex((c) => c > 0);
  const lo = Math.max(0, first < 0 ? 0 : first - 1);
  $("#k-dist").innerHTML = htmlKey(scoreSteps().map(([, c], k) => [c, scoreLabel(k)]));
  chart("c-dist", { type: "bar", data: { labels: bins.slice(lo).map((b) => `${b} to ${b + 5}`), datasets: [
    { label: "Sites", data: counts.slice(lo), backgroundColor: bins.slice(lo).map((b) => scoreColor(b + 2.5)), borderRadius: endRadius, borderSkipped: "bottom", categoryPercentage: 1, barPercentage: 0.94 }] },
    options: { maintainAspectRatio: false, scales: { x: { ...xPlain, ticks: { maxRotation: 0, autoSkip: true } }, y: { ...yGrid, beginAtZero: true } } } });

  const q = S.summary.queue, types = TYPE_ORDER.filter((t) => q.types.includes(t)).concat(q.types.filter((t) => !TYPE_ORDER.includes(t)));
  const qc = (t) => T[`queue-${t}`] || T["queue-other"];
  $("#queue-cap").textContent = `${fmt(q.n_active)} active requests (Berkeley Lab Queued Up 2026 plus CAISO). Nameplate MW requested by primary type, not available capacity; hybrid MW is not double counted.`;
  $("#k-queue").innerHTML = htmlKey(types.map((t) => [qc(t), t]));
  chart("c-queue", { type: "bar", data: { labels: q.states, datasets: types.map((t) => ({ label: t, data: q.gw[t], backgroundColor: qc(t), borderColor: T.paper, borderWidth: { top: 1 }, maxBarThickness: 56 })) },
    options: { maintainAspectRatio: false, plugins: { tooltip: { callbacks: { label: (c) => `${c.dataset.label}: ${fmt(c.raw, 1)} GW` } } },
      scales: { x: { ...xPlain, stacked: true, ticks: { color: T["ink-2"] } }, y: { ...yGrid, stacked: true, title: { display: true, text: "GW", color: T.muted } } } } });

  const p = S.summary.sub_proxy;
  $("#proxy-cap").textContent = S.summary.sub_proxy_note;
  chart("c-proxy", { type: "bar", plugins: [barLabels], data: { labels: p.map((r) => `${r.name} (${r.state}, ${fmt(r.max_kv)} kV)`), datasets: [
    { label: "Candidate solar MW with this as nearest POI", data: p.map((r) => r.site_mw), backgroundColor: T["ink-2"], borderRadius: { topRight: 2, bottomRight: 2 }, borderSkipped: "left", maxBarThickness: 14 }] },
    options: { indexAxis: "y", maintainAspectRatio: false, layout: { padding: { right: 48 } },
      plugins: { tooltip: { callbacks: { label: (c) => `${fmt(c.raw)} MW of candidate sites; ${fmt(p[c.dataIndex].queue_active_mw)} MW matched in queue` } } },
      scales: { x: { grid: { color: () => T["chart-grid"] }, border: { display: false }, title: { display: true, text: "Candidate solar MW nearby (6 ac/MW)", color: T.muted } },
        y: { ...xPlain, ticks: { color: T["ink-2"], font: { size: 12 } } } } } });
  $("#proxy-table").innerHTML = `<thead><tr><th>Substation</th><th>State</th><th class="num">Max kV</th><th class="num">Lines</th><th class="num">Matched active queue MW</th><th class="num">Candidate sites</th><th class="num">Candidate solar MW</th></tr></thead><tbody>` +
    p.map((r) => `<tr><td>${esc(r.name)}</td><td>${r.state}</td><td class="num">${fmt(r.max_kv)}</td><td class="num">${fmt(r.lines)}</td><td class="num">${fmt(r.queue_active_mw)}</td><td class="num">${fmt(r.n_sites)}</td><td class="num">${fmt(r.site_mw)}</td></tr>`).join("") + "</tbody>";
}

/* ---------- sources and limits ---------- */
function renderSources() {
  const s = S.sources, ap = S.deliv.appendix;
  const domainOrder = { grid: 0, land: 1, infra: 2, sites: 3 };
  const ds = s.datasets.slice().sort((a, b) => (domainOrder[a.domain] - domainOrder[b.domain]) || a.layer.localeCompare(b.layer));
  $("#sources-page").innerHTML = `<header class="page-h"><h2 class="page-title">Sources and Limits</h2>
      <p class="dek">Every dataset behind the map, when it was retrieved and what it cannot tell you. Read the limits before relying on any score.</p></header>
    <div class="prose prov-note" style="margin-left:calc(240px + var(--s-6))"><span class="caps">Provisional data note</span> ${esc(s.provisional_note)}</div>
    <section class="sect"><div class="sect-h"><h3>Limits to know up front</h3><p class="cap">From the project scope, section 7.</p></div><div class="sect-b">
      <ul class="ruled">${s.scope_limits.map((x) => `<li>${esc(x)}</li>`).join("")}</ul></div></section>
    <section class="sect"><div class="sect-h"><h3>Screening limits</h3><p class="cap">From METHOD.md, the screening and scoring method.</p></div><div class="sect-b">
      <ul class="ruled">${s.method_limits.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>
      <p class="prose" style="margin-top:var(--s-4)">${esc(s.open_items)}</p></div></section>
    <section class="sect"><div class="sect-h"><h3>Appendix</h3><p class="cap">Independent review of the data and method.</p></div><div class="sect-b">
      <p class="prose">${ap ? `<a href="${DOC}${encodeURIComponent(ap.href)}" target="_blank">${esc(ap.title)}</a>. An independent model reviewed the data and method; its blocking and important findings drove the two rankings, provisional flags, POI filter and queue confidence in this version.` : "The methodology review file was not found when the app was built."}</p></div></section>
    <section class="sect wide"><div class="sect-h"><h3>Datasets</h3><p class="cap">${ds.length} datasets, from each domain's MANIFEST.json.</p></div><div class="sect-b">
    <table class="data"><thead><tr><th>Domain</th><th>Layer</th><th>Source</th><th>Retrieved</th><th class="num">Records</th><th>Caveats</th></tr></thead><tbody>
    ${ds.map((d) => `<tr><td>${esc(d.domain)}</td><td>${esc(d.layer)}</td><td>${d.source_url ? `<a href="${esc(d.source_url)}" target="_blank" rel="noopener">${esc(d.source_name)}</a>` : esc(d.source_name)}</td><td>${esc(d.retrieved || "")}</td><td class="num">${fmt(d.record_count)}</td><td class="caveat">${esc(d.caveats)}</td></tr>`).join("")}</tbody></table></div></section>
    <p class="colophon">Map tiles: OpenStreetMap contributors, Esri World Imagery, OpenTopoMap. App data built ${esc(S.doc.generated)}. Type: Source Serif 4 and IBM Plex Sans (SIL Open Font License).</p>`;
}

function renderDeliverables() {
  const d = S.deliv;
  const link = (it) => (it.kind === "md" ? `${DOC}${encodeURIComponent(it.href)}` : it.href);
  const ext = (it) => (it.href.match(/\.([a-z0-9]+)$/i) || [])[1];
  const items = d.items.map((it) => [it.kind === "md" ? "Document" : "Download", it]).concat(d.appendix ? [["Appendix", d.appendix]] : []);
  $("#deliverables-page").innerHTML = `<header class="page-h"><h2 class="page-title">Deliverables</h2>
      <p class="dek">The ranked Excel table, the BLM application brief, the method, and a memo for each of the top sites.</p></header>
    <ul class="dlist">${items.map(([k, it]) => `<li><span class="caps">${k}</span><a href="${link(it)}" target="_blank">${esc(it.title)}</a><span class="meta">${ext(it) ? ext(it).toUpperCase() : ""}</span></li>`).join("")}</ul>
    <section class="sect"><div class="sect-h"><h3>Site memos</h3><p class="cap">${d.memos.length} memos. Show on map selects the site and opens its scorecard.</p></div><div class="sect-b">
    <table class="data plain" id="memo-table"><thead><tr><th>Memo</th><th>Site</th><th></th></tr></thead><tbody>${d.memos.map((m) => `<tr><td><a href="${DOC}${encodeURIComponent(m.href)}" target="_blank">${esc(m.title)}</a></td><td class="id">${esc(m.site_id || "")}</td><td>${m.site_id ? `<button class="textbtn" data-site="${esc(m.site_id)}">Show on map</button>` : ""}</td></tr>`).join("")}</tbody></table></div></section>`;
  $$("#deliverables-page button[data-site]").forEach((b) => (b.onclick = () => {
    const i = S.cols.site_id.indexOf(b.dataset.site); if (i < 0) return;
    showView("map"); setTimeout(() => selectSite(i, true), 50);
  }));
}

/* ---------- How to Read This (plain-English guide; colours come from the tokens, counts and dates from app data) ---------- */
function renderGuide() {
  const L = (id) => S.doc.layers.find((l) => l.id === id) || { legend: [] };
  const ds = (layer) => S.sources.datasets.find((d) => d.layer === layer) || {};
  const count = (f) => { let n = 0; for (let i = 0; i < S.n; i++) if (f(i)) n++; return n; };
  const W = S.doc.sites.weights, ws = W.solar, wd = W.dc;
  const blmN = count((i) => A("blm_solar_available", i) === true), provN = count((i) => A("sub_provisional", i) === true);
  const hiQ = count((i) => A("queue_confidence", i) === "high");
  const byState = S.doc.states.map((s) => `${STATE_NAMES[s]} ${fmt(count((i) => A("state", i) === s))}`).join(", ");
  const top1 = S.cols.rank_solar.indexOf(1), topDc = S.cols.rank_dc.indexOf(1);
  const subDs = ds("substations"), subDate = ((subDs.caveats || "").match(/last edited (\d{4}-\d{2}-\d{2})/) || [])[1];
  const retrieved = subDs.retrieved || S.doc.sites.meta.retrieved;
  const q = ds("queue_projects"), fiberLbl = (L("fiber").legend[0] || {}).label || "";
  const r = (sws, text) => `<div><span class="sws">${sws}</span><span>${text}</span></div>`;
  const tl = L("transmission_lines");
  const voltRows = tl.legend.map((x) => {
    const k = Object.keys(VOLT).find((c) => x.label.startsWith(c));
    return r(sw(x.color, k === "unknown" ? "dash" : "line", `height:${k === "unknown" ? 1 : 1 + 0.6 * Math.max(0, ["<115", "115-161", "230", "345", "500+"].indexOf(k))}px`),
      `${esc(x.label)}${k === "500+" ? " <strong>(the thickest, darkest lines: the biggest highways of the grid)</strong>" : ""}`);
  }).join("");
  const blmRows = L("blm_solar_available").legend.map((x) => r(sw(x.color, x.label.startsWith("DRECP Variance") ? "hatch" : ""), esc(x.label))).join("");
  const sc = scoreSteps().map(([, c], k) => r(sw(c), k === 0 ? "below 60" : k === 4 ? "90 and up" : `${SCORE_T[k]} to ${SCORE_T[k + 1]}`)).join("");
  const otherLayers = S.doc.layers.filter((l) => !["transmission_lines", "substations", "blm_solar_available"].includes(l.id))
    .map((l) => {
      const c = l.legend && l.legend[0] ? (l.kind === "raster" ? l.legend[l.legend.length - 1].color : l.legend[0].color) : "";
      const kind = l.kind === "line" || l.kind === "outline" ? (l.id === "fiber" ? "dash" : "line") : SOFT.has(l.id) ? "hatch" : l.id === "data_centers_osm" ? "sq" : l.id === "power_plants" ? "dot" : "";
      return `<tr><td style="width:28px">${c ? sw(c, kind) : ""}</td><td>${esc(l.title)}</td><td>${esc(l.group)}</td><td>${l.on ? "on" : "off"}</td></tr>`;
    }).join("");
  const exclN = S.doc.layers.filter((l) => l.group === "Exclusions").length;
  const wrow = (k, lab, what) => `<tr><td>${lab}</td><td class="num">${ws[k]}</td><td class="num">${wd[k]}</td><td>${what}</td></tr>`;
  const nMemo = (S.deliv.memos || []).filter((m) => m.site_id).length;
  const dot = (fill, stroke, size = 10) => subDot(fill, stroke, size);
  const sections = [
    ["what", "What this is", `<div class="prose"><p>This dashboard helps you find the best places in California, Arizona, Nevada, New Mexico and Utah for a large solar farm (100 MW to 1 GW), and possibly a data center next to it, before you spend real money. It combines free public maps of the power grid, land ownership, sunshine, terrain, wildlife and flood areas, then scores ${fmt(S.n)} candidate pieces of land so you can see which ones are worth a closer look. It is a first filter, not a final answer.</p></div>`],
    ["ask", "What was asked", `<div class="prose"><p>The request, in short:</p><ul>
      <li>Look at the electric grid and substations, and find where there is a good way to connect power.</li>
      <li>Find good land for large-scale solar projects.</li>
      <li>Consider data centers as well.</li>
      <li>Point out BLM (federal) land that is worth applying for.</li>
      <li>Cover the Southwest, with California added.</li>
      <li>Find and list the data sources, and build a proper map-based dashboard, end to end, that takes in all the data and helps you make decisions.</li></ul></div>`],
    ["good", "What makes a good site", `<div class="prose"><ul>
      <li><strong>A grid connection close by, with room.</strong> A big substation or high-voltage line within a few miles, and not already crowded with other projects waiting to connect.</li>
      <li><strong>Large, flat, sunny land you can actually get.</strong> At least 600 acres (about 100 MW), slope under 5 percent, strong sunshine. Best of all is BLM land the federal government has already marked as open to solar.</li>
      <li><strong>No deal-breakers.</strong> Not in wilderness, national parks or monuments, protected wildlife habitat, flood zones, tribal land, military land or towns.</li>
      <li><strong>For a data center, also:</strong> fiber (internet) lines nearby, water that is not too scarce, and a major road.</li></ul></div>`],
    ["map", "How to read the map", `<div class="prose"><p>Turn layers on and off in the left column under <em>Layers</em>. Every layer that is switched on is explained in the map key in the lower-left corner of the map. These are the main ones.</p></div>
      <div class="gkeys">
        <div class="gkey"><div><h4>Lines: transmission lines; thicker and darker means higher voltage</h4><p class="gk-what">Higher voltage means a bigger line that can carry more power. kV means kilovolts.</p></div><div class="rows">${voltRows}</div></div>
        <div class="gkey"><div><h4>Dots: substations</h4><p class="gk-what">A substation is where a new power plant can plug into the grid. Substations of 230 kV and up show at every zoom; smaller ones appear when you zoom in.</p></div>
          <div class="rows">
            ${r(dot(T.paper, `1px ${T["sub-stroke"]}`, 6) + dot(T.paper, `1px ${T["sub-stroke"]}`, 9) + dot(T.paper, `1px ${T["sub-stroke"]}`, 13), "<strong>Size</strong> = voltage. Bigger dot, bigger substation.")}
            ${r(dot(T["q-lt500"]), "Light grey: under 500 MW of projects waiting to connect there")}
            ${r(dot(T["q-500"]), "Mid grey: 500 to 2,000 MW waiting")}
            ${r(dot(T["q-2000"]), "<strong>Near-black dots: over 2,000 MW waiting. That substation is crowded</strong>; a new project would join a long line.")}
            ${r(dot(T["q-unknown"], `1px ${T["sub-stroke"]}`), "White: we could not match any queue records to it. This means <em>unknown</em>, not empty.")}
            ${r(dot(T["q-removed"]), "Pale grey, faded: not used as a connection point (for example a converter station or a plant's own substation).")}
            ${r(dot(T.paper, `2px ${T.prov}`), "Violet ring: provisional record. The substation or its voltage is not confirmed in the main federal data.")}
          </div></div>
        <div class="gkey"><div><h4>Candidate sites, coloured by score</h4><p class="gk-what">Blue dots when zoomed out, land shapes when zoomed in. Darker blue = higher score. A black outline with a white halo marks the site you clicked.</p></div><div class="rows">${sc}</div></div>
        <div class="gkey"><div><h4>Gold areas: BLM solar-available land</h4><p class="gk-what">Federal land where BLM says it will accept solar applications.</p></div><div class="rows">${blmRows}<p class="gk-what">${esc(L("blm_solar_available").note || "")}</p></div></div>
      </div>
      <figure class="look"><div><svg viewBox="0 0 240 120" width="240" height="120" role="img" aria-label="Illustration: a dark blue site next to a thick dark line and a grey substation, on gold BLM land">
          <rect x="0" y="0" width="240" height="120" fill="${T["paper-sunk"]}"/>
          <path d="M60 116 Q 72 52 164 40 L 214 112 Z" fill="${T["blm-available"]}" fill-opacity="0.3" stroke="${T["blm-available"]}" stroke-opacity="0.8"/>
          <path d="M8 96 L86 72 L130 26 L232 10" stroke="${T["kv-500"]}" stroke-width="3.4" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
          <path d="M20 20 L70 44 L110 110" stroke="${T["kv-230"]}" stroke-width="1.6" fill="none"/>
          <path d="M104 94 L142 66 L174 82 L150 104 Z" fill="${T["score-5"]}" fill-opacity="0.85" stroke="${T.paper}" stroke-width="5" stroke-linejoin="round"/>
          <path d="M104 94 L142 66 L174 82 L150 104 Z" fill="none" stroke="${T.ink}" stroke-width="2" stroke-linejoin="round"/>
          <path d="M184 62 L204 52 L216 66 L196 76 Z" fill="${T["score-2"]}" fill-opacity="0.85"/>
          <circle cx="130" cy="26" r="7" fill="${T["q-500"]}" stroke="${T["sub-stroke"]}"/>
          <text x="12" y="112" font-size="9" font-style="italic" fill="${T["ink-2"]}" font-family="Source Serif 4, Georgia, serif">BLM land</text></svg>
          <figcaption class="cap">Illustration, not real data.</figcaption></div>
        <p><strong>What to look for:</strong> dark blue sites close to a thick, dark line and a light or mid grey substation, ideally sitting on gold (BLM solar-available) land. Near-black substations are crowded. White ones need a phone call to the utility to find out.</p></figure>
      <h4 class="sub-h" style="margin-top:var(--s-6)">Other layers</h4>
      <table class="data"><thead><tr><th></th><th>Layer</th><th>Group</th><th>On at start</th></tr></thead><tbody>${otherLayers}</tbody></table>
      <p class="after">The ${exclN} "Exclusions" layers are the deal-breaker areas that were cut out of every site. Click any line, dot or area on the map to see its details.</p>`],
    ["use", "How to use it, step by step", `<div class="prose"><ol>
      <li><strong>Pick a ranking</strong> at the top right: <em>Solar</em> (a solar farm only) or <em>Solar + Data Center</em> (also rewards fiber, water and roads).</li>
      <li><strong>Adjust the weights</strong> in the left column. Slide one up to make that factor matter more; the map, table and charts re-rank right away. <em>Reset</em> puts the defaults back.</li>
      <li><strong>Filter</strong>: tick or untick states; set the minimum acres, the maximum distance to a substation and a minimum score; tick <em>BLM solar-available only</em> to see only federal land open to solar; tick <em>Hide sites on provisional substations</em> to drop sites that rely on unconfirmed grid data; tick <em>High queue confidence only</em> to keep sites where the crowding data is reliable.</li>
      <li><strong>Click a site</strong> on the map (or a row in the table) to open its scorecard beside the map: the score for each factor, acres, owner, nearest substation and how far it is, how much is queued nearby, sunshine, any warnings, data center fit, BLM status and a recommended next step.</li>
      <li><strong>Use the table</strong> under the map. It lists the sites in the current map view (untick <em>Only sites in map view</em> to see all). Click a column title to sort.</li>
      <li><strong>Export CSV</strong> saves the table, with your current weights and filters, as a spreadsheet file.</li>
      <li><strong>Summary</strong> tab: charts of sites by state, score spread, the waiting line (queue) by state, and substations that look less crowded.</li>
      <li><strong>Sources and Limits</strong> tab: every dataset, its date and its known problems.</li>
      <li><strong>Deliverables</strong> tab: the Excel ranking, ${nMemo} site memos for top sites, and the BLM application brief.</li></ol></div>`],
    ["score", "How a score is made", `<div class="prose"><p>Each site gets five sub-scores from 0 (poor) to 100 (excellent). The total is a weighted average of them. The weights below are the defaults; the sliders change them.</p></div>
      <table class="data"><thead><tr><th>Factor</th><th class="num">Solar weight</th><th class="num">Solar + Data Center weight</th><th>What earns a high sub-score</th></tr></thead><tbody>
      ${wrow("grid", "Grid", "Close to a 115 kV or bigger substation and a 230 kV or bigger line, a high-voltage substation, and a county queue that is not crowded. Cut by 15 percent if the substation record is provisional.")}
      ${wrow("land", "Land", "BLM solar-available land scores best, then private and state land. Flatter and bigger is better.")}
      ${wrow("sun", "Sun", "More sunshine (GHI). 4.5 kWh/m2/day or less scores 0; 6.0 or more scores 100.")}
      ${wrow("permit", "Permitting", "Starts at 100 and loses points for warnings such as an ACEC (sensitive BLM area), wetlands, an existing BLM application on the land, or being near protected habitat.")}
      ${wrow("dc", "Data center", "Near fiber (a proxy), lower water stress, near a major road and near a 230 kV or bigger substation.")}</tbody></table>
      <div class="prose" style="margin-top:var(--s-4)"><p>Example: in the default Solar ranking the top site is <strong>${esc(A("site_id", top1))}</strong> in ${esc(A("county", top1))} County, ${esc(A("state", top1))} (score ${fmt(A("score_total_solar", top1), 1)}). In the Solar + Data Center ranking the top site is <strong>${esc(A("site_id", topDc))}</strong> (score ${fmt(A("score_total_dc", topDc), 1)}). The full formulas are in the method document on the Deliverables tab.</p></div>`],
    ["prep", "How it was prepared", `<div class="prose"><p>Everything comes from free public data, downloaded on ${esc(retrieved)}:</p><ul>
      <li><strong>Grid:</strong> federal grid maps (HIFLD transmission lines and substations), with OpenStreetMap filling some gaps; Berkeley Lab "Queued Up" data and the CAISO queue report for projects waiting to connect (${fmt(q.record_count)} records, ${fmt(S.summary.queue.n_active)} active requests in these states); EIA power plant list (EIA-860, 2025).</li>
      <li><strong>Land:</strong> the BLM 2024 Western Solar Plan (land open to solar) and Solar Energy Zones; BLM land ownership map; USFWS critical habitat; FEMA flood zones; wilderness, monuments, tribal, military, park and urban areas; wetlands.</li>
      <li><strong>Sun and terrain:</strong> NREL sunshine data (GHI) and slope built from USGS elevation data.</li>
      <li><strong>Data center inputs:</strong> a fiber proxy (telecom lines in OpenStreetMap plus interstate and rail corridors), WRI Aqueduct water stress, and major roads.</li></ul>
      <p><strong>Screening steps.</strong> 1) Cover the five states with a grid of 1 km squares. 2) Throw out squares that hit a deal-breaker or are too steep. 3) Join neighbouring squares with the same owner into blocks and cut out every deal-breaker exactly. 4) Keep pieces of at least 600 acres within 30 km of a usable substation: ${fmt(S.n)} sites (${byState}); ${fmt(blmN)} of them on BLM solar-available land. 5) Score and rank them.</p>
      <p><strong>Independent review.</strong> A separate AI model (GPT) reviewed the data and method and rated the first version 5 out of 10. Fixes applied: two separate rankings (Solar, and Solar + Data Center); a "provisional" flag and a 15 percent grid-score cut where substation data is not confirmed; converter stations and plant-owned substations removed as connection points; counties with no matched queue data treated as "unknown" instead of "uncrowded", with a queue confidence flag. The review is linked on the Sources and Limits tab.</p></div>`],
    ["limits", "Limitations (please read)", `<ul class="ruled">
      <li><strong>Public maps do not show spare capacity.</strong> They show where lines and substations are, not how much room is left. Only the utility can tell you that.</li>
      <li><strong>Queue data is a crowding signal, not capacity.</strong> Lots of projects waiting usually means a long, costly wait. Few or none may just mean no data matched. Only ${fmt(hiQ)} of ${fmt(S.n)} sites have high-confidence queue data.</li>
      <li><strong>Substation data is partly dated.</strong> The federal substation file was last edited ${esc(subDate || "years ago")}, and some records come from OpenStreetMap. ${fmt(provN)} sites rely on a provisional substation record.</li>
      <li><strong>Fiber is mostly a guess.</strong> The fiber layer is a proxy (${esc(fiberLbl)}), so the data center ranking is weaker than the solar ranking.</li>
      <li><strong>Land status is not legal title.</strong> The ownership map shows who manages the surface, not who owns it, and not leases, mining claims or other rights.</li>
      <li><strong>This is not engineering.</strong> No site visit, survey, grid study, cost estimate or environmental study has been done.</li>
      <li><strong>Federal policy changed in 2025 and 2026.</strong> Since a July 2025 Interior memo, most BLM solar steps need review by the Secretary's office (a 2026 court order blocks it only for members of certain trade groups). The 2025 tax law ended solar tax credits (45Y/48E) except for projects that started construction by 2026-07-04 or are in service by the end of 2027, which in practice rules them out for a new BLM project. See the BLM brief.</li>
      <li><strong>Scores are for narrowing down, not deciding.</strong> Use them to choose a short list to investigate, not to pick a winner.</li></ul>`],
    ["next", "What to do next with a top site", `<ol class="ruled">
      <li><span><strong>Call the utility.</strong> Ask for a pre-application meeting and ask directly: how much capacity is available at this substation, and what would connecting cost and take?</span></li>
      <li><span><strong>If it is BLM land, contact the BLM field office.</strong> Request a pre-application meeting (43 CFR 2804.10). Check MLRS for any existing application on the same land.</span></li>
      <li><span><strong>Check title and survey.</strong> Order a title report and a survey to confirm ownership, leases, mining claims and access.</span></li>
      <li><span><strong>Run environmental checks.</strong> Habitat, cultural resources, water and wetlands, with a qualified consultant.</span></li>
      <li><span><strong>Have counsel review.</strong> A land-use and energy attorney should review the plan, current federal rules and tax position before you file anything.</span></li></ol>`],
    ["glossary", "Glossary", `<dl class="gloss">
      <dt>kV</dt><dd>Kilovolt, a measure of line voltage. Higher kV lines carry more power over longer distances.</dd>
      <dt>MW</dt><dd>Megawatt, a measure of power. A 100 MW solar farm needs roughly 500 to 700 acres.</dd>
      <dt>Substation</dt><dd>A yard of electrical equipment where lines meet and where a new plant can connect.</dd>
      <dt>Interconnection queue</dt><dd>The waiting line of projects that have asked a utility or grid operator to connect.</dd>
      <dt>POI</dt><dd>Point of interconnection: the exact substation or line where a project plugs in.</dd>
      <dt>BLM</dt><dd>Bureau of Land Management, the federal agency that manages much of the open land in the West.</dd>
      <dt>SEZ</dt><dd>Solar Energy Zone: BLM areas first set aside in 2012 as priority places for solar.</dd>
      <dt>DRECP</dt><dd>California's desert renewable energy plan; its Development Focus Areas are California's version of BLM solar-available land.</dd>
      <dt>GHI</dt><dd>Global horizontal irradiance: how much sunshine reaches flat ground, in kWh per square metre per day.</dd>
      <dt>ROW</dt><dd>Right-of-way: the BLM permit that lets you build on federal land.</dd>
      <dt>Hard vs soft constraint</dt><dd>Hard: a deal-breaker, the land was cut out entirely. Soft: a warning that lowers the permitting score but does not remove the site.</dd>
      <dt>Provisional</dt><dd>A substation record that is not confirmed in the main federal dataset, so check it before relying on it.</dd></dl>`],
  ];
  $("#guide-page").innerHTML = `<header class="page-h"><h2 class="page-title">How to Read This</h2>
    <p class="dek">A plain-English guide to this dashboard: what it is, how to read the map, how to use it, how it was made and what it cannot tell you.</p></header>
    <div class="guide-grid">
      <nav class="toc" aria-label="On this page"><span class="caps">On this page</span>${sections.map(([id, t], k) => `<a href="#g-${id}" data-g="${id}"><span class="n">${k + 1}</span><span>${esc(t)}</span></a>`).join("")}</nav>
      <div class="gbody">${sections.map(([id, t, body], k) => `<section class="gsec" id="g-${id}" data-section="${id}"><h3><span class="n">${k + 1}</span>${esc(t)}</h3>${body}</section>`).join("")}</div>
    </div>`;
  $$("#guide-page .toc a").forEach((a) => (a.onclick = (e) => { e.preventDefault(); $(`#g-${a.dataset.g}`).scrollIntoView({ behavior: REDUCED ? "auto" : "smooth", block: "start" }); }));
  // mark the section being read in the contents column
  const view = $("#view-guide");
  const mark = () => {
    const top = view.getBoundingClientRect().top + 120; let cur = sections[0][0];
    for (const [id] of sections) if ($(`#g-${id}`).getBoundingClientRect().top <= top) cur = id;
    $$("#guide-page .toc a").forEach((a) => a.classList.toggle("current", a.dataset.g === cur));
  };
  view.addEventListener("scroll", mark, { passive: true }); mark();
}

window.__app = { S, selectSite, setMode, showView, recompute, closeScorecard, homeView };
boot().catch((e) => { console.error(e); $("#loading").textContent = `Failed to load data: ${e.message}. Run pipeline/build_app.py.`; document.body.classList.remove("is-loading"); $("#loading").style.display = "block"; });

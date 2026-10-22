/* Southwest siting dashboard. Data comes from app/data/ (built by pipeline/build_app.py). */
"use strict";

const SCORE_STEPS = [[0, "#cff4f0"], [60, "#8fdcd3"], [70, "#3fb8ad"], [80, "#13857f"], [90, "#0b4f55"]];
const FACTORS = [
  ["grid", "Grid", "score_grid"], ["land", "Land", "score_land"], ["sun", "Sun", "score_sun"],
  ["permit", "Permitting", "score_permit"], ["dc", "Data center", "score_dc"]];
const STATE_NAMES = { CA: "California", AZ: "Arizona", NV: "Nevada", NM: "New Mexico", UT: "Utah" };
const MAX_ROWS = 400;

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
const scoreColor = (s) => { let c = SCORE_STEPS[0][1]; for (const [t, col] of SCORE_STEPS) if (s >= t) c = col; return c; };

async function getJSON(u) { const r = await fetch(u); if (!r.ok) throw new Error(`${u}: ${r.status}`); return r.json(); }

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
  const [doc, attr, summary, sources, deliv] = await Promise.all([
    getJSON("data/layers.json"), getJSON("data/sites_attr.json"), getJSON("data/summary.json"),
    getJSON("data/sources.json"), getJSON("data/deliverables.json")]);
  S.doc = doc; S.n = attr.n; S.cols = decode(attr.columns); S.summary = summary; S.sources = sources; S.deliv = deliv;
  S.score = new Float32Array(S.n); S.rank = new Int32Array(S.n); S.show = new Uint8Array(S.n);
  S.weights = { ...doc.sites.weights.solar };
  buildControls();
  buildLayerPanel();
  renderSources();
  renderDeliverables();
  renderGuide();
  initMap();
}

/* ---------- controls ---------- */
function buildControls() {
  const box = $("#weights");
  box.innerHTML = FACTORS.map(([k, label]) =>
    `<div class="wrow" id="w-row-${k}"><span>${label}</span><input type="range" min="0" max="50" step="1" id="w-${k}"><span class="v" id="w-v-${k}"></span></div>`).join("");
  FACTORS.forEach(([k]) => $(`#w-${k}`).addEventListener("input", (e) => { S.weights[k] = +e.target.value; syncWeights(); scheduleRecompute(); }));
  $("#reset-weights").onclick = () => setMode(S.mode, true);
  $$(".seg").forEach((b) => (b.onclick = () => setMode(b.dataset.mode, true)));

  $("#state-filter").innerHTML = S.doc.states.map((s) => `<label><input type="checkbox" value="${s}" checked> ${s}</label>`).join("");
  $$("#state-filter input").forEach((i) => (i.onchange = scheduleRecompute));
  [["#f-acres", "#acres-val", (v) => `${fmt(v)} ac`], ["#f-dist", "#dist-val", (v) => `${v} km`], ["#f-score", "#score-val", (v) => `${v}`]].forEach(([id, out, f]) => {
    const el = $(id); const upd = () => ($(out).textContent = f(+el.value)); upd();
    el.addEventListener("input", () => { upd(); scheduleRecompute(); });
  });
  ["#f-blm", "#f-prov", "#f-queue"].forEach((id) => ($(id).onchange = scheduleRecompute));
  $("#view-only").onchange = refreshTable;
  $("#export-csv").onclick = exportCSV;
  $$("#tabs button").forEach((b) => (b.onclick = () => showView(b.dataset.view)));
  $("#modal-close").onclick = () => $("#modal").classList.add("hidden");
  $("#modal").onclick = (e) => { if (e.target.id === "modal") $("#modal").classList.add("hidden"); };
  syncWeights();
}

function setMode(mode, resetWeights) {
  S.mode = mode;
  $$(".seg").forEach((b) => b.classList.toggle("active", b.dataset.mode === mode));
  if (resetWeights) S.weights = { ...S.doc.sites.weights[mode] };
  syncWeights(); scheduleRecompute(0);
}

function syncWeights() {
  const sum = Object.values(S.weights).reduce((a, b) => a + b, 0) || 1;
  FACTORS.forEach(([k]) => {
    $(`#w-${k}`).value = S.weights[k];
    $(`#w-v-${k}`).textContent = `${S.weights[k]} (${Math.round((100 * S.weights[k]) / sum)}%)`;
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

/* ---------- scoring ---------- */
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
    container: "map", center: [-112.5, 36.2], zoom: 4.9, minZoom: 3.5, maxZoom: 16, attributionControl: { compact: true },
    style: {
      version: 8, sources: {
        street: rs(["https://tile.openstreetmap.org/{z}/{x}/{y}.png"], "&copy; OpenStreetMap contributors"),
        satellite: rs(["https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"], "Imagery &copy; Esri, Maxar, Earthstar Geographics"),
        terrain: rs(["https://a.tile.opentopomap.org/{z}/{x}/{y}.png", "https://b.tile.opentopomap.org/{z}/{x}/{y}.png", "https://c.tile.opentopomap.org/{z}/{x}/{y}.png"], "&copy; OpenTopoMap (CC-BY-SA), OpenStreetMap contributors", 17),
      },
      layers: [
        { id: "bg", type: "background", paint: { "background-color": "#eef1f4" } },
        { id: "base-street", type: "raster", source: "street", paint: { "raster-saturation": -0.55, "raster-opacity": 0.9 } },
        { id: "base-satellite", type: "raster", source: "satellite", layout: { visibility: "none" } },
        { id: "base-terrain", type: "raster", source: "terrain", layout: { visibility: "none" }, paint: { "raster-saturation": -0.3 } },
      ],
    },
  });
  map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "bottom-right");
  map.addControl(new maplibregl.ScaleControl({ unit: "imperial" }), "bottom-left");
  $$("#basemap input").forEach((r) => (r.onchange = () => {
    ["street", "satellite", "terrain"].forEach((b) => map.setLayoutProperty(`base-${b}`, "visibility", r.value === b ? "visible" : "none"));
  }));
  map.on("load", async () => {
    addOverlayLayers();
    await addSites();
    S.doc.layers.filter((l) => l.on).forEach((l) => setLayerVisible(l.id, true));
    map.on("moveend", refreshTable);
    map.on("click", onMapClick);
    map.on("mousemove", (e) => {
      const f = map.queryRenderedFeatures(e.point, { layers: interactiveLayers() });
      map.getCanvas().style.cursor = f.length ? "pointer" : "";
    });
    $("#loading").classList.add("hidden");
    recompute();
    window.__appReady = true;
  });
}

function matchExpr(prop, colors, fallback = "#adb5bd") {
  const e = ["match", ["get", prop]];
  for (const [k, v] of Object.entries(colors)) e.push(k, v);
  e.push(fallback); return e;
}

/* Every overlay is registered at start with an empty source; data is fetched on first toggle. */
function addOverlayLayers() {
  const empty = { type: "FeatureCollection", features: [] };
  const order = ["raster", "fill", "outline", "line", "point"];
  const byKind = (k) => S.doc.layers.filter((l) => l.kind === k);
  S.mapLayers = {};
  for (const kind of order) {
    for (const L of byKind(kind)) {
      const ids = [];
      if (kind === "raster") {
        map.addSource(L.id, { type: "image", url: L.file, coordinates: L.bounds });
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

function layerSpecs(L) {
  const st = L.style || {};
  const id = L.id;
  if (id === "transmission_lines") {
    const width = ["match", ["get", "volt_class"], "500+", 2.6, "345", 2.1, "230", 1.6, "115-161", 1.1, 0.8];
    return [{ id, type: "line", paint: { "line-color": matchExpr("volt_class", st.colors), "line-opacity": 0.9,
      "line-width": ["interpolate", ["linear"], ["zoom"], 4, ["*", 0.6, width], 9, ["*", 1.3, width], 13, ["*", 2, width]] } }];
  }
  if (id === "substations") {
    const r = ["interpolate", ["linear"], ["coalesce", ["get", "max_kv"], 69], 69, 1.6, 115, 2.2, 230, 3.2, 345, 4.4, 500, 5.6];
    const paint = {
      "circle-radius": ["interpolate", ["linear"], ["zoom"], 4, ["*", 0.8, r], 8, ["*", 1.4, r], 12, ["*", 2.2, r]],
      "circle-color": ["case", ["to-boolean", ["get", "excluded_reason"]], "#cbd5e1",
        ["<=", ["coalesce", ["get", "queue_active_mw"], 0], 0], "#ffffff",
        ["step", ["get", "queue_active_mw"], "#fde68a", 500, "#f59e0b", 2000, "#b91c1c"]],
      "circle-stroke-color": ["case", ["==", ["get", "provisional"], true], "#7c3aed", "#475569"],
      "circle-stroke-width": ["interpolate", ["linear"], ["zoom"], 5, ["case", ["==", ["get", "provisional"], true], 0.8, 0.5],
        9, ["case", ["==", ["get", "provisional"], true], 1.8, 0.9]] };
    // 230 kV+ at every zoom; lower voltages from zoom 7 so the regional view stays readable
    const hi = [">=", ["coalesce", ["get", "max_kv"], 0], 230];
    return [{ id: `${id}-lo`, type: "circle", minzoom: 7, filter: ["!", hi], paint },
      { id, type: "circle", filter: hi, paint }];
  }
  if (id === "power_plants") {
    return [{ id, type: "circle", paint: {
      "circle-radius": ["interpolate", ["linear"], ["sqrt", ["coalesce", ["get", "mw"], 1]], 1, 2, 10, 4, 40, 9],
      "circle-color": matchExpr("tech", st.colors), "circle-opacity": 0.85, "circle-stroke-color": "#fff", "circle-stroke-width": 0.6 } }];
  }
  if (id === "data_centers_osm") {
    return [{ id, type: "circle", paint: { "circle-radius": 4, "circle-color": st.color, "circle-stroke-color": "#fff", "circle-stroke-width": 1 } }];
  }
  if (L.kind === "line") {
    return [{ id, type: "line", paint: { "line-color": st.color || "#495057", "line-width": id === "roads_major" ? 1 : 1.4,
      "line-opacity": id === "roads_major" ? 0.55 : 0.85, ...(id === "fiber" ? { "line-dasharray": [2, 1.5] } : {}) } }];
  }
  if (L.kind === "outline") {
    const s = id === "admin_states";
    return [{ id, type: "line", paint: { "line-color": s ? "#334155" : "#94a3b8", "line-width": s ? 1.4 : 0.6, "line-opacity": s ? 0.8 : 0.6 } }];
  }
  // fills
  let color = st.color || "#868e96";
  if (st.by) color = matchExpr(st.by, st.colors);
  if (id === "water_stress") color = ["interpolate", ["linear"], ["coalesce", ["get", "water_stress"], 0], 0, "#e7f5ff", 2, "#ffe8a1", 3, "#ffa94d", 4, "#f76707", 5, "#a61e4d"];
  const op = id === "ownership" ? 0.32 : id === "water_stress" ? 0.45 : id.startsWith("excl_") ? 0.38 : 0.42;
  return [
    { id, type: "fill", paint: { "fill-color": color, "fill-opacity": op } },
    { id: `${id}-edge`, type: "line", paint: { "line-color": color, "line-width": 0.6, "line-opacity": 0.8 } }];
}

async function setLayerVisible(id, on) {
  if (id === "sites") {
    ["sites-fill", "sites-edge", "sites-pt", "sites-sel"].forEach((l) => map.setLayoutProperty(l, "visibility", on ? "visible" : "none"));
    return;
  }
  const L = S.doc.layers.find((l) => l.id === id);
  if (on && !S.loaded[id]) {
    const tag = $(`#ltag-${id}`); if (tag) tag.textContent = "loading";
    const data = await getJSON(L.file);
    map.getSource(id).setData(data); S.loaded[id] = true;
    if (tag) tag.textContent = "";
  }
  (S.mapLayers[id] || []).forEach((l) => map.setLayoutProperty(l, "visibility", on ? "visible" : "none"));
  // free heavy layers when switched off so a laptop with little memory can browse every layer in turn
  if (!on && S.loaded[id] && L.kind !== "raster" && (L.mb || 0) > 3) {
    map.getSource(id).setData({ type: "FeatureCollection", features: [] }); S.loaded[id] = false;
  }
}

async function addSites() {
  const geom = await getJSON(S.doc.sites.geom);
  map.addSource("sites", { type: "geojson", data: geom, promoteId: "i" });
  const pts = { type: "FeatureCollection", features: [] };
  for (let i = 0; i < S.n; i++) pts.features.push({ type: "Feature", properties: { i }, geometry: { type: "Point", coordinates: [A("centroid_lon", i), A("centroid_lat", i)] } });
  map.addSource("sites-pts", { type: "geojson", data: pts, promoteId: "i" });
  const ramp = ["step", ["coalesce", ["feature-state", "score"], 0]]; SCORE_STEPS.forEach(([t, c], k) => { if (k === 0) ramp.push(c); else ramp.push(t, c); });
  const hidden = ["boolean", ["feature-state", "hide"], false];
  map.addLayer({ id: "sites-fill", type: "fill", source: "sites", minzoom: 7,
    paint: { "fill-color": ramp, "fill-opacity": ["case", hidden, 0, 0.78] } }, "sites-anchor");
  map.addLayer({ id: "sites-edge", type: "line", source: "sites", minzoom: 7,
    paint: { "line-color": "#0b3b40", "line-width": 0.6, "line-opacity": ["case", hidden, 0, 0.7] } }, "sites-anchor");
  map.addLayer({ id: "sites-pt", type: "circle", source: "sites-pts", maxzoom: 7.5,
    paint: { "circle-radius": ["interpolate", ["linear"], ["zoom"], 4, 2.2, 7, 4], "circle-color": ramp,
      "circle-opacity": ["case", hidden, 0, 0.92], "circle-stroke-color": "#0b3b40",
      "circle-stroke-width": ["case", hidden, 0, 0.4], "circle-stroke-opacity": ["case", hidden, 0, 0.8] } }, "sites-anchor");
  map.addLayer({ id: "sites-sel", type: "line", source: "sites", filter: ["==", ["get", "i"], -1],
    paint: { "line-color": "#f97316", "line-width": 3 } }, "sites-anchor");
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
  const p = f.properties, id = f.layer.id.replace(/-(edge|lo)$/, "");
  const L = S.doc.layers.find((l) => l.id === id);
  let title = p.name || p.plant || p.project_name || p.category || p.constraint || p.sez_name || p.agency || (L && L.title) || id;
  let rows = POP_FIELDS[id] ? POP_FIELDS[id].map(([k, lab]) => [lab, p[k]]) : Object.entries(p).filter(([k]) => !["i"].includes(k)).map(([k, v]) => [k, v]);
  let extra = "";
  if (id === "substations") {
    if (p.provisional === true || p.provisional === "true") extra += `<div class="badge prov">Provisional record</div> `;
    if (p.excluded_reason) extra += `<div class="badge warn">Removed as POI: ${esc(p.excluded_reason)}</div>`;
  }
  const html = `<div class="pop-title">${esc(title)}</div><div class="muted">${esc(L ? L.title : id)}</div>${extra}
    <table class="pop">${rows.filter(([, v]) => v !== null && v !== undefined && v !== "").map(([k, v]) => `<tr><td>${esc(k)}</td><td>${esc(typeof v === "number" ? fmt(v, v % 1 ? 1 : 0) : v)}</td></tr>`).join("")}</table>`;
  new maplibregl.Popup({ maxWidth: "320px" }).setLngLat(lngLat).setHTML(html).addTo(map);
}

/* ---------- layer panel ---------- */
function legendHTML(L) {
  if (L.kind === "raster") {
    const stops = L.legend.map((x) => x.color).join(",");
    return `<div class="legend"><div class="lg"><span class="sw ramp" style="background:linear-gradient(90deg,${stops})"></span></div>
      <div class="lg muted">${esc(L.legend[0].label)} to ${esc(L.legend[L.legend.length - 1].label)}</div></div>`;
  }
  const line = L.kind === "line" || L.kind === "outline";
  return `<div class="legend">${(L.legend || []).map((x) => `<div class="lg"><span class="sw ${line ? "line" : ""}" style="background:${x.color};${x.stroke ? `border:1.5px solid ${x.stroke}` : ""}${x.dash ? ";background:repeating-linear-gradient(90deg," + x.color + " 0 5px,transparent 5px 8px)" : ""}"></span>${esc(x.label)}</div>`).join("")}</div>
    ${L.note ? `<div class="lnote">${esc(L.note)}</div>` : ""}`;
}

function buildLayerPanel() {
  const groups = {};
  S.doc.layers.forEach((L) => (groups[L.group] = groups[L.group] || []).push(L));
  const siteLegend = `<div class="legend">${SCORE_STEPS.map(([t, c], k) => `<div class="lg"><span class="sw" style="background:${c}"></span>${k === 0 ? "under 60" : k === SCORE_STEPS.length - 1 ? "90 and over" : `${t} to ${SCORE_STEPS[k + 1][0]}`}</div>`).join("")}
    <div class="lg"><span class="sw" style="background:#fff;border:2px solid #f97316"></span>selected site</div></div>
    <div class="lnote">Points below zoom 7, polygons above. Colour = current blended score.</div>`;
  let html = `<div class="lgroup"><div class="lgroup-title">Screening result</div>
    <div class="litem"><div class="litem-row"><label><input type="checkbox" data-layer="sites" checked> Candidate sites (by score)</label><button class="info" data-info="sites">i</button></div>${siteLegend}</div></div>`;
  for (const [g, list] of Object.entries(groups)) {
    html += `<div class="lgroup"><div class="lgroup-title">${esc(g)}</div>`;
    for (const L of list) {
      html += `<div class="litem" id="li-${L.id}"><div class="litem-row"><label><input type="checkbox" data-layer="${L.id}" ${L.on ? "checked" : ""}> ${esc(L.title)}</label>
        <span class="loading-tag" id="ltag-${L.id}"></span><button class="info" data-info="${L.id}" title="Source and caveats">i</button></div>
        <div class="lg-wrap ${L.on ? "" : "hidden"}">${legendHTML(L)}</div></div>`;
    }
    html += `</div>`;
  }
  $("#layer-list").innerHTML = html;
  $$("#layer-list input[data-layer]").forEach((cb) => (cb.onchange = () => {
    const wrap = cb.closest(".litem").querySelector(".lg-wrap"); if (wrap) wrap.classList.toggle("hidden", !cb.checked);
    setLayerVisible(cb.dataset.layer, cb.checked);
  }));
  $$("#layer-list .info").forEach((b) => (b.onclick = () => showMeta(b.dataset.info)));
}

function showMeta(id) {
  const L = id === "sites" ? { title: "Candidate sites", meta: S.doc.sites.meta } : S.doc.layers.find((l) => l.id === id);
  const m = L.meta || {};
  $("#modal-body").innerHTML = `<h3 style="margin-top:0">${esc(L.title)}</h3>
    <table class="kv"><tr><td>Source</td><td>${esc(m.source_name || "not recorded")}</td></tr>
    ${m.source_url ? `<tr><td>URL</td><td><a href="${esc(m.source_url)}" target="_blank" rel="noopener">${esc(m.source_url)}</a></td></tr>` : ""}
    <tr><td>Retrieved</td><td>${esc(m.retrieved || "n/a")}</td></tr>
    <tr><td>Records (processed)</td><td>${fmt(m.record_count)}</td></tr>
    ${L.features !== undefined ? `<tr><td>Features in app copy</td><td>${fmt(L.features)} (${L.mb} MB, simplified for display)</td></tr>` : ""}
    <tr><td>Processed file</td><td>${esc(m.path || "")}</td></tr>
    <tr><td>Caveats</td><td>${esc(m.caveats || "none recorded")}</td></tr></table>`;
  $("#modal").classList.remove("hidden");
}

/* ---------- selection and scorecard ---------- */
function selectSite(i, fly = true) {
  S.selected = i;
  map.setFilter("sites-sel", ["==", ["get", "i"], i]);
  if (fly) map.flyTo({ center: [A("centroid_lon", i), A("centroid_lat", i)], zoom: Math.max(map.getZoom(), 10), speed: 1.6 });
  renderScorecard(i);
  $$("#site-table tbody tr").forEach((tr) => tr.classList.toggle("sel", +tr.dataset.i === i));
  const row = $(`#site-table tbody tr[data-i="${i}"]`); if (row) row.scrollIntoView({ block: "nearest" });
}

function memoFor(siteId) { return (S.deliv.memos || []).find((m) => m.site_id === siteId); }

function renderScorecard(i) {
  const el = $("#scorecard"); el.classList.remove("hidden");
  const v = (c) => A(c, i);
  const w = S.weights, prov = v("sub_provisional") === true, blm = v("blm_solar_available") === true;
  const badges = [
    blm ? `<span class="badge ok">BLM solar-available</span>` : `<span class="badge">${esc(v("owner_category"))} land</span>`,
    v("sez_name") ? `<span class="badge ok">SEZ: ${esc(v("sez_name"))}</span>` : "",
    prov ? `<span class="badge prov">Provisional substation</span>` : `<span class="badge">HIFLD substation</span>`,
    v("queue_confidence") === "high" ? `<span class="badge ok">Queue data: high confidence</span>` : `<span class="badge warn">Queue data: low confidence</span>`,
    v("row_cases_overlap") ? `<span class="badge warn">Overlaps active BLM ROW case</span>` : "",
  ].join("");
  const bars = FACTORS.map(([k, label, col]) => {
    const s = v(col) ?? 0;
    return `<div class="bar"><span>${label} <span class="muted">${w[k]}</span></span><div class="track"><div class="fill ${w[k] ? "" : "off"}" style="width:${Math.max(0, Math.min(100, s))}%"></div></div><span class="val">${fmt(s, 0)}</span></div>`;
  }).join("");
  const row = (k, val) => `<tr><td>${k}</td><td>${val}</td></tr>`;
  const cons = (v("constraints_soft") || "").split(/;\s*/).filter(Boolean);
  const memo = memoFor(v("site_id"));
  const rk = S.rank[i];
  el.innerHTML = `<button class="close" aria-label="Close" id="sc-close">x</button>
    <h2>${esc(v("site_id"))}</h2>
    <div class="sub">${esc(v("county"))} County, ${esc(STATE_NAMES[v("state")] || v("state"))}</div>
    <div class="big"><span class="num">${fmt(S.score[i], 1)}</span><span class="of">${rk ? `rank ${fmt(rk)} of ${fmt(S.order.length)} in current view of filters` : "hidden by current filters"}</span></div>
    <div class="muted small">Pipeline ranks: solar #${fmt(v("rank_solar"))} (${fmt(v("score_total_solar"), 1)}), Solar + Data Center #${fmt(v("rank_dc"))} (${fmt(v("score_total_dc"), 1)})</div>
    <div class="badges">${badges}</div>
    ${prov ? `<div class="provbox">The nearest substation record is provisional (${esc(v("sub_source"))} record, kV from ${esc(v("sub_kv_source"))}). Its grid score was multiplied by 0.85. Confirm the substation exists, its operating voltage and owner with the utility before relying on this site.</div>` : ""}
    <div class="sc-section">Score by factor (0 to 100, weight shown)</div><div class="bars">${bars}</div>
    <div class="sc-section">Site</div>
    <table class="kv">
      ${row("Acres", `${fmt(v("acres"))} ac (about ${fmt(v("solar_mw_est"))} MW at 6 ac/MW)`)}
      ${row("Surface owner", esc(v("owner_category")))}
      ${row("BLM status", esc(v("blm_status") || "not BLM solar land"))}
      ${row("GHI", `${fmt(v("ghi"), 2)} kWh/m2/day`)}
      ${row("Mean slope", `${fmt(v("mean_slope"), 1)} percent`)}
      ${row("Centroid", `${fmt(v("centroid_lat"), 4)}, ${fmt(v("centroid_lon"), 4)}`)}
    </table>
    <div class="sc-section">Grid connection</div>
    <table class="kv">
      ${row("Nearest 115 kV+ substation", `${esc(v("nearest_sub_name"))} ${prov ? '<span class="badge prov">provisional</span>' : ""}<br><span class="muted">${fmt(v("nearest_sub_kv"))} kV, ${fmt(v("dist_sub_km"), 1)} km, ${esc(v("nearest_sub_owner") || "owner unknown")}</span>`)}
      ${row("Nearest 230 kV+ substation", `${esc(v("nearest_sub230_name") || "n/a")}<br><span class="muted">${fmt(v("nearest_sub230_kv"))} kV, ${fmt(v("dist_sub230_km"), 1)} km</span>`)}
      ${row("Nearest 115 kV+ line", `${fmt(v("nearest_line_kv"))} kV, ${fmt(v("dist_line_km"), 1)} km`)}
      ${row("Active queue in county", `${fmt(v("queued_mw_county"))} MW <span class="muted">(solar ${fmt(v("queued_mw_county_solar"))}, storage ${fmt(v("queued_mw_county_storage"))})</span>`)}
      ${row("Queued at nearest substation", `${fmt(v("nearest_sub_queue_mw"))} MW <span class="muted">(POI name match; 0 can mean no match)</span>`)}
      ${row("Queue confidence", `${esc(v("queue_confidence"))} <span class="muted">(${fmt(100 * (v("queue_poi_match_rate") || 0))} percent of county requests matched to a POI)</span>`)}
    </table>
    <div class="sc-section">Data center fit</div>
    <table class="kv">
      ${row("Fiber (proxy)", `${fmt(v("fiber_km"), 1)} km <span class="muted">(${esc(v("fiber_basis") || "")})</span>`)}
      ${row("Water stress", `${fmt(v("water_stress"), 1)} of 5 <span class="muted">${esc(v("water_stress_label") || "")}</span>`)}
      ${row("Major road", `${fmt(v("road_km"), 1)} km <span class="muted">${esc(v("road_name") || "")}</span>`)}
      ${row("Data center score", fmt(v("score_dc"), 0))}
    </table>
    <div class="sc-section">Constraints hit (soft)</div>
    <div>${cons.length ? cons.map((c) => `<span class="badge warn">${esc(c.replace(/_/g, " "))}</span>`).join(" ") : '<span class="muted">none flagged</span>'}</div>
    <div class="sc-section">Recommended next step</div>
    <div class="next">${esc(v("next_step") || "")}</div>
    <div class="sc-actions">
      <button class="btn primary" id="sc-zoom">Zoom to site</button>
      ${memo ? `<a class="btn" href="doc.html?f=${encodeURIComponent(memo.href)}" target="_blank">Open site memo</a>` : ""}
      ${blm ? `<a class="btn" href="doc.html?f=${encodeURIComponent("../deliverables/BLM_Application_Brief.md")}" target="_blank">BLM application brief</a>` : ""}
    </div>`;
  $("#sc-close").onclick = () => { el.classList.add("hidden"); S.selected = null; map.setFilter("sites-sel", ["==", ["get", "i"], -1]); };
  $("#sc-zoom").onclick = () => map.flyTo({ center: [v("centroid_lon"), v("centroid_lat")], zoom: 11.5 });
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
  let rows = currentRows();
  const col = TCOLS.find((c) => c[0] === S.sort.key) || TCOLS[0], get = col[2], d = S.sort.dir;
  if (col[0] !== "rank") rows.sort((a, b) => { const x = get(a), y = get(b); if (x === y) return 0; if (x === null || x === undefined) return 1; if (y === null || y === undefined) return -1; return (x < y ? -1 : 1) * d; });
  else if (d < 0) rows.reverse();
  S.viewRows = rows;
  $("#table-title").textContent = S.mode === "solar" ? "Ranked sites: Solar" : "Ranked sites: Solar + Data Center";
  $("#table-count").textContent = `${fmt(rows.length)} sites${rows.length > MAX_ROWS ? `, first ${MAX_ROWS} listed; CSV has all` : ""}`;
  $("#site-table thead").innerHTML = `<tr>${TCOLS.map(([k, lab, , num]) => `<th data-k="${k}" class="${num ? "num" : ""} ${S.sort.key === k ? "sorted" : ""}">${lab}${S.sort.key === k ? (S.sort.dir > 0 ? " ▲" : " ▼") : ""}</th>`).join("")}</tr>`;
  $$("#site-table th").forEach((th) => (th.onclick = () => {
    const k = th.dataset.k; if (S.sort.key === k) S.sort.dir *= -1; else { S.sort.key = k; S.sort.dir = ["rank", "site_id", "state", "county", "owner_category", "nearest_sub_name", "dist_sub_km", "queued_mw_county"].includes(k) ? 1 : -1; }
    refreshTable();
  }));
  $("#site-table tbody").innerHTML = rows.slice(0, MAX_ROWS).map((i) => `<tr data-i="${i}" class="${i === S.selected ? "sel" : ""}">${TCOLS.map(([k, , g, num, dp]) => {
    let val = g(i);
    if (k === "score") return `<td class="num"><span class="chip" style="background:${scoreColor(val)}"></span>${fmt(val, 1)}</td>`;
    if (k === "prov" && val) return `<td><span class="badge prov">provisional</span></td>`;
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
function showView(v) {
  $$("#tabs button").forEach((b) => b.classList.toggle("active", b.dataset.view === v));
  $$(".view").forEach((s) => s.classList.toggle("active", s.id === `view-${v}`));
  if (v === "summary") renderSummary();
  if (v === "map" && map) setTimeout(() => map.resize(), 0);
}

/* ---------- summary charts ---------- */
const CAT = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"];
const TYPE_ORDER = ["hybrid", "solar", "storage", "wind", "gas", "other"];
function chart(id, cfg) {
  if (S.charts[id]) S.charts[id].destroy();
  Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;
  Chart.defaults.font.size = 11.5; Chart.defaults.color = "#475569";
  S.charts[id] = new Chart($(`#${id}`), cfg);
}
const gridOpts = { grid: { color: "#eef2f6" }, border: { display: false } };

function renderSummary() {
  const st = S.doc.states, o = S.order;
  const acres = o.reduce((a, i) => a + A("acres", i), 0), mw = o.reduce((a, i) => a + (A("solar_mw_est", i) || 0), 0);
  const blmN = o.filter((i) => A("blm_solar_available", i)).length, provN = o.filter((i) => A("sub_provisional", i)).length;
  const tiles = [["Sites passing filters", fmt(o.length)], ["Total acres", fmt(acres)], ["Solar MW potential (6 ac/MW)", `${fmt(mw / 1000, 1)} GW`],
    ["BLM solar-available sites", fmt(blmN)], ["On provisional substations", fmt(provN)]];
  $("#tiles").innerHTML = tiles.map(([t, n]) => `<div class="tile"><div class="t">${t}</div><div class="n">${n}</div></div>`).join("");

  const byState = st.map((s) => o.filter((i) => A("state", i) === s).length);
  const blmState = st.map((s) => o.filter((i) => A("state", i) === s && A("blm_solar_available", i)).length);
  chart("c-state", { type: "bar", data: { labels: st, datasets: [
    { label: "All candidate sites", data: byState, backgroundColor: CAT[0], borderRadius: 4, maxBarThickness: 34 },
    { label: "BLM solar-available", data: blmState, backgroundColor: CAT[1], borderRadius: 4, maxBarThickness: 34 }] },
    options: { maintainAspectRatio: false, plugins: { legend: { position: "top", align: "start", labels: { boxWidth: 10 } } }, scales: { x: { grid: { display: false } }, y: { ...gridOpts, beginAtZero: true } } } });

  const bins = []; for (let b = 0; b < 100; b += 5) bins.push(b);
  const counts = bins.map(() => 0); o.forEach((i) => counts[Math.min(19, Math.floor(S.score[i] / 5))]++);
  const first = counts.findIndex((c) => c > 0);
  const lo = Math.max(0, first < 0 ? 0 : first - 1);
  chart("c-dist", { type: "bar", data: { labels: bins.slice(lo).map((b) => `${b} to ${b + 5}`), datasets: [
    { label: "Sites", data: counts.slice(lo), backgroundColor: bins.slice(lo).map((b) => scoreColor(b + 2.5)), borderRadius: 3, categoryPercentage: 0.94, barPercentage: 0.96 }] },
    options: { maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { grid: { display: false }, ticks: { maxRotation: 0, autoSkip: true } }, y: { ...gridOpts, beginAtZero: true } } } });

  const q = S.summary.queue, types = TYPE_ORDER.filter((t) => q.types.includes(t)).concat(q.types.filter((t) => !TYPE_ORDER.includes(t)));
  $("#queue-cap").textContent = `${fmt(q.n_active)} active requests (Berkeley Lab Queued Up 2026 plus CAISO). Nameplate MW requested by primary type, not available capacity; hybrid MW is not double counted.`;
  chart("c-queue", { type: "bar", data: { labels: q.states, datasets: types.map((t, k) => ({ label: t, data: q.gw[t], backgroundColor: CAT[k % CAT.length], borderColor: "#fff", borderWidth: 1, maxBarThickness: 40 })) },
    options: { maintainAspectRatio: false, plugins: { legend: { position: "top", align: "start", labels: { boxWidth: 10 } }, tooltip: { callbacks: { label: (c) => `${c.dataset.label}: ${fmt(c.raw, 1)} GW` } } },
      scales: { x: { stacked: true, grid: { display: false } }, y: { stacked: true, ...gridOpts, title: { display: true, text: "GW" } } } } });

  const p = S.summary.sub_proxy;
  $("#proxy-cap").textContent = S.summary.sub_proxy_note;
  chart("c-proxy", { type: "bar", data: { labels: p.map((r) => `${r.name} (${r.state}, ${fmt(r.max_kv)} kV)`), datasets: [
    { label: "Candidate solar MW with this as nearest POI", data: p.map((r) => r.site_mw), backgroundColor: CAT[0], borderRadius: 4, maxBarThickness: 14 }] },
    options: { indexAxis: "y", maintainAspectRatio: false, plugins: { legend: { display: false }, tooltip: { callbacks: { label: (c) => `${fmt(c.raw)} MW of candidate sites; ${fmt(p[c.dataIndex].queue_active_mw)} MW matched in queue` } } },
      scales: { x: { ...gridOpts, title: { display: true, text: "Candidate solar MW nearby (6 ac/MW)" } }, y: { grid: { display: false }, ticks: { font: { size: 11 } } } } } });
  $("#proxy-table").innerHTML = `<tr><th>Substation</th><th>State</th><th class="num">Max kV</th><th class="num">Lines</th><th class="num">Matched active queue MW</th><th class="num">Candidate sites</th><th class="num">Candidate solar MW</th></tr>` +
    p.map((r) => `<tr><td>${esc(r.name)}</td><td>${r.state}</td><td class="num">${fmt(r.max_kv)}</td><td class="num">${fmt(r.lines)}</td><td class="num">${fmt(r.queue_active_mw)}</td><td class="num">${fmt(r.n_sites)}</td><td class="num">${fmt(r.site_mw)}</td></tr>`).join("");
}

/* ---------- sources and limits ---------- */
function renderSources() {
  const s = S.sources, ap = S.deliv.appendix;
  const domainOrder = { grid: 0, land: 1, infra: 2, sites: 3 };
  const ds = s.datasets.slice().sort((a, b) => (domainOrder[a.domain] - domainOrder[b.domain]) || a.layer.localeCompare(b.layer));
  $("#sources-page").innerHTML = `<h2>Sources and Limits</h2>
    <div class="callout"><strong>Provisional data note.</strong> ${esc(s.provisional_note)}</div>
    <h3>Limits to know up front (SCOPE section 7)</h3>
    <div class="callout neutral"><ul>${s.scope_limits.map((x) => `<li>${esc(x)}</li>`).join("")}</ul></div>
    <h3>Screening limits (METHOD.md)</h3>
    <div class="callout neutral"><ul>${s.method_limits.map((x) => `<li>${esc(x)}</li>`).join("")}</ul><p>${esc(s.open_items)}</p></div>
    <h3>Appendix</h3>
    <div class="callout neutral">${ap ? `<a href="doc.html?f=${encodeURIComponent(ap.href)}" target="_blank">${esc(ap.title)}</a>. An independent model reviewed the data and method; its blocking and important findings drove the two rankings, provisional flags, POI filter and queue confidence in this version.` : "The methodology review file was not found when the app was built."}</div>
    <h3>Datasets (${ds.length}, from each domain's MANIFEST.json)</h3>
    <table class="plain"><tr><th>Domain</th><th>Layer</th><th>Source</th><th>Retrieved</th><th class="num">Records</th><th>Caveats</th></tr>
    ${ds.map((d) => `<tr><td>${esc(d.domain)}</td><td>${esc(d.layer)}</td><td>${d.source_url ? `<a href="${esc(d.source_url)}" target="_blank" rel="noopener">${esc(d.source_name)}</a>` : esc(d.source_name)}</td><td>${esc(d.retrieved || "")}</td><td class="num">${fmt(d.record_count)}</td><td>${esc(d.caveats)}</td></tr>`).join("")}</table>
    <p class="muted">Map tiles: OpenStreetMap contributors, Esri World Imagery, OpenTopoMap. App built ${esc(S.doc.generated)}.</p>`;
}

function renderDeliverables() {
  const d = S.deliv;
  const link = (it) => it.kind === "md" ? `doc.html?f=${encodeURIComponent(it.href)}` : it.href;
  $("#deliverables-page").innerHTML = `<h2>Deliverables</h2>
    <div class="deliv">${d.items.map((it) => `<a class="card" href="${link(it)}" target="_blank"><div class="k">${it.kind === "md" ? "Document" : "Download"}</div>${esc(it.title)}</a>`).join("")}
    ${d.appendix ? `<a class="card" href="${link(d.appendix)}" target="_blank"><div class="k">Appendix</div>${esc(d.appendix.title)}</a>` : ""}</div>
    <h3>Site memos (${d.memos.length})</h3>
    <table class="plain"><tr><th>Memo</th><th>Site</th><th></th></tr>${d.memos.map((m) => `<tr><td><a href="doc.html?f=${encodeURIComponent(m.href)}" target="_blank">${esc(m.title)}</a></td><td>${esc(m.site_id || "")}</td><td>${m.site_id ? `<button class="btn" data-site="${esc(m.site_id)}">Show on map</button>` : ""}</td></tr>`).join("")}</table>`;
  $$("#deliverables-page button[data-site]").forEach((b) => (b.onclick = () => {
    const i = S.cols.site_id.indexOf(b.dataset.site); if (i < 0) return;
    showView("map"); setTimeout(() => selectSite(i, true), 50);
  }));
}

/* ---------- How to Read This (plain-English guide; colours, counts and dates come from app/data) ---------- */
function renderGuide() {
  const L = (id) => S.doc.layers.find((l) => l.id === id) || { legend: [] };
  const ds = (layer) => S.sources.datasets.find((d) => d.layer === layer) || {};
  const lg = (id, label) => (L(id).legend || []).find((x) => x.label === label) || {};
  const sw = (color, opt = {}) => `<span class="sw ${opt.line ? "line" : ""} ${opt.dot ? "dot" : ""}" style="background:${color};${opt.stroke ? `border:${opt.dot ? 2 : 1.5}px solid ${opt.stroke};` : ""}${opt.size ? `width:${opt.size}px;height:${opt.size}px;` : ""}"></span>`;
  const count = (f) => { let n = 0; for (let i = 0; i < S.n; i++) if (f(i)) n++; return n; };
  const W = S.doc.sites.weights, ws = W.solar, wd = W.dc;
  const blmN = count((i) => A("blm_solar_available", i) === true), provN = count((i) => A("sub_provisional", i) === true);
  const hiQ = count((i) => A("queue_confidence", i) === "high");
  const byState = S.doc.states.map((s) => `${STATE_NAMES[s]} ${fmt(count((i) => A("state", i) === s))}`).join(", ");
  const top1 = S.cols.rank_solar.indexOf(1), topDc = S.cols.rank_dc.indexOf(1);
  const subDs = ds("substations"), subDate = ((subDs.caveats || "").match(/last edited (\d{4}-\d{2}-\d{2})/) || [])[1];
  const retrieved = subDs.retrieved || S.doc.sites.meta.retrieved;
  const q = ds("queue_projects"), fiberLbl = (L("fiber").legend[0] || {}).label || "";
  const tl = L("transmission_lines"), voltRows = tl.legend.map((x) => `<div class="lg">${sw(x.color, { line: true })}${esc(x.label)}${x.label.startsWith("500") ? " <strong>(the red lines: the biggest highways of the grid)</strong>" : ""}</div>`).join("");
  const subC = (lab) => lg("substations", lab).color;
  const blmRows = L("blm_solar_available").legend.map((x) => `<div class="lg">${sw(x.color)}${esc(x.label)}</div>`).join("");
  const sc = SCORE_STEPS.map(([t, c], k) => `<div class="lg">${sw(c)}${k === 0 ? `below ${SCORE_STEPS[1][0]}` : k === SCORE_STEPS.length - 1 ? `${t} and up` : `${t} to ${SCORE_STEPS[k + 1][0]}`}</div>`).join("");
  const otherLayers = S.doc.layers.filter((l) => !["transmission_lines", "substations", "blm_solar_available"].includes(l.id))
    .map((l) => `<tr><td>${l.legend && l.legend[0] ? sw(l.kind === "raster" ? l.legend[l.legend.length - 1].color : l.legend[0].color, { line: l.kind === "line" || l.kind === "outline" }) : ""}</td><td>${esc(l.title)}</td><td>${esc(l.group)}</td><td>${l.on ? "on" : "off"}</td></tr>`).join("");
  const exclN = S.doc.layers.filter((l) => l.group === "Exclusions").length;
  const wrow = (k, lab, what) => `<tr><td>${lab}</td><td class="num">${ws[k]}</td><td class="num">${wd[k]}</td><td>${what}</td></tr>`;
  const nMemo = (S.deliv.memos || []).filter((m) => m.site_id).length;
  const sections = [
    ["what", "1. What this is", `<p>This dashboard helps you find the best places in California, Arizona, Nevada, New Mexico and Utah for a large solar farm (100 MW to 1 GW), and possibly a data center next to it, before you spend real money. It combines free public maps of the power grid, land ownership, sunshine, terrain, wildlife and flood areas, then scores ${fmt(S.n)} candidate pieces of land so you can see which ones are worth a closer look. It is a first filter, not a final answer.</p>`],
    ["ask", "2. What was asked", `<p>The request, in short:</p><ul>
      <li>Look at the electric grid and substations, and find where there is a good way to connect power.</li>
      <li>Find good land for large-scale solar projects.</li>
      <li>Consider data centers as well.</li>
      <li>Point out BLM (federal) land that is worth applying for.</li>
      <li>Cover the Southwest, with California added.</li>
      <li>Find and list the data sources, and build a proper map-based dashboard, end to end, that takes in all the data and helps you make decisions.</li></ul>`],
    ["good", "3. What makes a good site", `<ul>
      <li><strong>A grid connection close by, with room.</strong> A big substation or high-voltage line within a few miles, and not already crowded with other projects waiting to connect.</li>
      <li><strong>Large, flat, sunny land you can actually get.</strong> At least 600 acres (about 100 MW), slope under 5 percent, strong sunshine. Best of all is BLM land the federal government has already marked as open to solar.</li>
      <li><strong>No deal-breakers.</strong> Not in wilderness, national parks or monuments, protected wildlife habitat, flood zones, tribal land, military land or towns.</li>
      <li><strong>For a data center, also:</strong> fiber (internet) lines nearby, water that is not too scarce, and a major road.</li></ul>`],
    ["map", "4. How to read the map", `<p>Turn layers on and off in the left panel under <em>Layers</em>. Each layer's colour key is shown there too. These are the main ones.</p>
      <div class="gl-grid">
        <div class="gl-card"><h4>Lines: transmission lines, coloured by voltage</h4><p>Higher voltage means a bigger line that can carry more power. kV means kilovolts.</p><div class="legend">${voltRows}</div></div>
        <div class="gl-card"><h4>Dots: substations</h4><p>A substation is where a new power plant can plug into the grid.</p>
          <div class="legend">
            <div class="lg">${sw("#ffffff", { dot: true, size: 6, stroke: "#475569" })}${sw("#ffffff", { dot: true, size: 10, stroke: "#475569" })}${sw("#ffffff", { dot: true, size: 14, stroke: "#475569" })}<strong>Size</strong> = voltage. Bigger dot, bigger substation.</div>
            <div class="lg">${sw(subC("< 500 MW queued at POI"), { dot: true })}Yellow: under 500 MW of projects waiting to connect there</div>
            <div class="lg">${sw(subC("500 to 2,000 MW"), { dot: true })}Orange: 500 to 2,000 MW waiting</div>
            <div class="lg">${sw(subC("> 2,000 MW"), { dot: true })}<strong>Red dots: over 2,000 MW waiting. That substation is crowded</strong>; a new project would join a long line.</div>
            <div class="lg">${sw("#ffffff", { dot: true, stroke: "#475569" })}White: we could not match any queue records to it. This means <em>unknown</em>, not empty.</div>
            <div class="lg">${sw(subC("removed as POI by screening (grey)"), { dot: true })}Grey: not used as a connection point (for example a converter station or a plant's own substation).</div>
            <div class="lg">${sw("#ffffff", { dot: true, stroke: "#7c3aed" })}Purple ring: provisional record. The substation or its voltage is not confirmed in the main federal data.</div>
          </div><p class="muted small">Substations of 230 kV and up show at every zoom; smaller ones appear when you zoom in.</p></div>
        <div class="gl-card"><h4>Candidate sites, coloured by score</h4><p>Teal dots when zoomed out, land shapes when zoomed in. Darker teal = higher score. An orange outline marks the site you clicked.</p><div class="legend">${sc}</div></div>
        <div class="gl-card"><h4>Mustard areas: BLM solar-available land</h4><p>Federal land where BLM says it will accept solar applications.</p><div class="legend">${blmRows}</div><p class="muted small">${esc(L("blm_solar_available").note || "")}</p></div>
      </div>
      <div class="look"><svg viewBox="0 0 220 90" width="220" height="90" aria-hidden="true">
          <rect x="0" y="0" width="220" height="90" fill="#eef1f4"/>
          <path d="M10 70 L80 52 L120 20 L210 8" stroke="${tl.style.colors["500+"]}" stroke-width="4" fill="none"/>
          <path d="M60 85 Q 70 40 150 30 L 190 82 Z" fill="${L("blm_solar_available").legend[0].color}" fill-opacity="0.45"/>
          <path d="M95 70 L130 48 L160 62 L138 80 Z" fill="${SCORE_STEPS[SCORE_STEPS.length - 1][1]}" fill-opacity="0.85" stroke="#0b3b40"/>
          <circle cx="120" cy="20" r="7" fill="${subC("500 to 2,000 MW")}" stroke="#475569"/></svg>
        <div><strong>What to look for:</strong> dark teal sites close to a big line (purple or red) and a yellow or orange substation, ideally sitting on mustard (BLM solar-available) land. Red substations are crowded. White ones need a phone call to the utility to find out.</div></div>
      <h3>Other layers</h3>
      <table class="plain"><tr><th></th><th>Layer</th><th>Group</th><th>On at start</th></tr>${otherLayers}</table>
      <p class="muted small">The ${exclN} "Exclusions" layers are the deal-breaker areas that were cut out of every site. Click any line, dot or area on the map to see its details.</p>`],
    ["use", "5. How to use it, step by step", `<ol>
      <li><strong>Pick a ranking</strong> at the top right: <em>Solar</em> (a solar farm only) or <em>Solar + Data Center</em> (also rewards fiber, water and roads).</li>
      <li><strong>Adjust the weights</strong> in the left panel. Slide one up to make that factor matter more; the map, table and charts re-rank right away. <em>Reset</em> puts the defaults back.</li>
      <li><strong>Filter</strong>: tick or untick states; set the minimum acres, the maximum distance to a substation and a minimum score; tick <em>BLM solar-available only</em> to see only federal land open to solar; tick <em>Hide sites on provisional substations</em> to drop sites that rely on unconfirmed grid data; tick <em>High queue confidence only</em> to keep sites where the crowding data is reliable.</li>
      <li><strong>Click a site</strong> on the map (or a row in the table) to open its scorecard: the score for each factor, acres, owner, nearest substation and how far it is, how much is queued nearby, sunshine, any warnings, data center fit, BLM status and a recommended next step.</li>
      <li><strong>Use the table</strong> under the map. It lists the sites in the current map view (untick <em>Only sites in map view</em> to see all). Click a column title to sort.</li>
      <li><strong>Export CSV</strong> saves the table, with your current weights and filters, as a spreadsheet file.</li>
      <li><strong>Summary</strong> tab: charts of sites by state, score spread, the waiting line (queue) by state, and substations that look less crowded.</li>
      <li><strong>Sources and Limits</strong> tab: every dataset, its date and its known problems.</li>
      <li><strong>Deliverables</strong> tab: the Excel ranking, ${nMemo} site memos for top sites, and the BLM application brief.</li></ol>`],
    ["score", "6. How a score is made", `<p>Each site gets five sub-scores from 0 (poor) to 100 (excellent). The total is a weighted average of them. The weights below are the defaults; the sliders change them.</p>
      <table class="plain"><tr><th>Factor</th><th class="num">Solar weight</th><th class="num">Solar + Data Center weight</th><th>What earns a high sub-score</th></tr>
      ${wrow("grid", "Grid", "Close to a 115 kV or bigger substation and a 230 kV or bigger line, a high-voltage substation, and a county queue that is not crowded. Cut by 15 percent if the substation record is provisional.")}
      ${wrow("land", "Land", "BLM solar-available land scores best, then private and state land. Flatter and bigger is better.")}
      ${wrow("sun", "Sun", "More sunshine (GHI). 4.5 kWh/m2/day or less scores 0; 6.0 or more scores 100.")}
      ${wrow("permit", "Permitting", "Starts at 100 and loses points for warnings such as an ACEC (sensitive BLM area), wetlands, an existing BLM application on the land, or being near protected habitat.")}
      ${wrow("dc", "Data center", "Near fiber (a proxy), lower water stress, near a major road and near a 230 kV or bigger substation.")}</table>
      <p>Example: in the default Solar ranking the top site is <strong>${esc(A("site_id", top1))}</strong> in ${esc(A("county", top1))} County, ${esc(A("state", top1))} (score ${fmt(A("score_total_solar", top1), 1)}). In the Solar + Data Center ranking the top site is <strong>${esc(A("site_id", topDc))}</strong> (score ${fmt(A("score_total_dc", topDc), 1)}). The full formulas are in the method document on the Deliverables tab.</p>`],
    ["prep", "7. How it was prepared", `<p>Everything comes from free public data, downloaded on ${esc(retrieved)}:</p><ul>
      <li><strong>Grid:</strong> federal grid maps (HIFLD transmission lines and substations), with OpenStreetMap filling some gaps; Berkeley Lab "Queued Up" data and the CAISO queue report for projects waiting to connect (${fmt(q.record_count)} records, ${fmt(S.summary.queue.n_active)} active requests in these states); EIA power plant list (EIA-860, 2025).</li>
      <li><strong>Land:</strong> the BLM 2024 Western Solar Plan (land open to solar) and Solar Energy Zones; BLM land ownership map; USFWS critical habitat; FEMA flood zones; wilderness, monuments, tribal, military, park and urban areas; wetlands.</li>
      <li><strong>Sun and terrain:</strong> NREL sunshine data (GHI) and slope built from USGS elevation data.</li>
      <li><strong>Data center inputs:</strong> a fiber proxy (telecom lines in OpenStreetMap plus interstate and rail corridors), WRI Aqueduct water stress, and major roads.</li></ul>
      <p><strong>Screening steps.</strong> 1) Cover the five states with a grid of 1 km squares. 2) Throw out squares that hit a deal-breaker or are too steep. 3) Join neighbouring squares with the same owner into blocks and cut out every deal-breaker exactly. 4) Keep pieces of at least 600 acres within 30 km of a usable substation: ${fmt(S.n)} sites (${byState}); ${fmt(blmN)} of them on BLM solar-available land. 5) Score and rank them.</p>
      <p><strong>Independent review.</strong> A separate AI model (GPT) reviewed the data and method and rated the first version 5 out of 10. Fixes applied: two separate rankings (Solar, and Solar + Data Center); a "provisional" flag and a 15 percent grid-score cut where substation data is not confirmed; converter stations and plant-owned substations removed as connection points; counties with no matched queue data treated as "unknown" instead of "uncrowded", with a queue confidence flag. The review is linked on the Sources and Limits tab.</p>`],
    ["limits", "8. Limitations (please read)", `<ul>
      <li><strong>Public maps do not show spare capacity.</strong> They show where lines and substations are, not how much room is left. Only the utility can tell you that.</li>
      <li><strong>Queue data is a crowding signal, not capacity.</strong> Lots of projects waiting usually means a long, costly wait. Few or none may just mean no data matched. Only ${fmt(hiQ)} of ${fmt(S.n)} sites have high-confidence queue data.</li>
      <li><strong>Substation data is partly dated.</strong> The federal substation file was last edited ${esc(subDate || "years ago")}, and some records come from OpenStreetMap. ${fmt(provN)} sites rely on a provisional substation record.</li>
      <li><strong>Fiber is mostly a guess.</strong> The fiber layer is a proxy (${esc(fiberLbl)}), so the data center ranking is weaker than the solar ranking.</li>
      <li><strong>Land status is not legal title.</strong> The ownership map shows who manages the surface, not who owns it, and not leases, mining claims or other rights.</li>
      <li><strong>This is not engineering.</strong> No site visit, survey, grid study, cost estimate or environmental study has been done.</li>
      <li><strong>Federal policy changed in 2025 and 2026.</strong> Since a July 2025 Interior memo, most BLM solar steps need review by the Secretary's office (a 2026 court order blocks it only for members of certain trade groups). The 2025 tax law ended solar tax credits (45Y/48E) except for projects that started construction by 2026-07-04 or are in service by the end of 2027, which in practice rules them out for a new BLM project. See the BLM brief.</li>
      <li><strong>Scores are for narrowing down, not deciding.</strong> Use them to choose a short list to investigate, not to pick a winner.</li></ul>`],
    ["next", "9. What to do next with a top site", `<ol>
      <li><strong>Call the utility.</strong> Ask for a pre-application meeting and ask directly: how much capacity is available at this substation, and what would connecting cost and take?</li>
      <li><strong>If it is BLM land, contact the BLM field office.</strong> Request a pre-application meeting (43 CFR 2804.10). Check MLRS for any existing application on the same land.</li>
      <li><strong>Check title and survey.</strong> Order a title report and a survey to confirm ownership, leases, mining claims and access.</li>
      <li><strong>Run environmental checks.</strong> Habitat, cultural resources, water and wetlands, with a qualified consultant.</li>
      <li><strong>Have counsel review.</strong> A land-use and energy attorney should review the plan, current federal rules and tax position before you file anything.</li></ol>`],
    ["glossary", "10. Glossary", `<table class="plain">
      <tr><td><strong>kV</strong></td><td>Kilovolt, a measure of line voltage. Higher kV lines carry more power over longer distances.</td></tr>
      <tr><td><strong>MW</strong></td><td>Megawatt, a measure of power. A 100 MW solar farm needs roughly 500 to 700 acres.</td></tr>
      <tr><td><strong>Substation</strong></td><td>A yard of electrical equipment where lines meet and where a new plant can connect.</td></tr>
      <tr><td><strong>Interconnection queue</strong></td><td>The waiting line of projects that have asked a utility or grid operator to connect.</td></tr>
      <tr><td><strong>POI</strong></td><td>Point of interconnection: the exact substation or line where a project plugs in.</td></tr>
      <tr><td><strong>BLM</strong></td><td>Bureau of Land Management, the federal agency that manages much of the open land in the West.</td></tr>
      <tr><td><strong>SEZ</strong></td><td>Solar Energy Zone: BLM areas first set aside in 2012 as priority places for solar.</td></tr>
      <tr><td><strong>DRECP</strong></td><td>California's desert renewable energy plan; its Development Focus Areas are California's version of BLM solar-available land.</td></tr>
      <tr><td><strong>GHI</strong></td><td>Global horizontal irradiance: how much sunshine reaches flat ground, in kWh per square metre per day.</td></tr>
      <tr><td><strong>ROW</strong></td><td>Right-of-way: the BLM permit that lets you build on federal land.</td></tr>
      <tr><td><strong>Hard vs soft constraint</strong></td><td>Hard: a deal-breaker, the land was cut out entirely. Soft: a warning that lowers the permitting score but does not remove the site.</td></tr>
      <tr><td><strong>Provisional</strong></td><td>A substation record that is not confirmed in the main federal dataset, so check it before relying on it.</td></tr></table>`],
  ];
  $("#guide-page").innerHTML = `<h2>How to Read This</h2>
    <p class="lead">A plain-English guide to this dashboard: what it is, how to read the map, how to use it, how it was made and what it cannot tell you.</p>
    <nav class="toc">${sections.map(([id, t]) => `<a href="#g-${id}" data-g="${id}">${esc(t)}</a>`).join("")}</nav>
    ${sections.map(([id, t, body]) => `<section class="gsec" id="g-${id}" data-section="${id}"><h3>${esc(t)}</h3>${body}</section>`).join("")}`;
  $$("#guide-page .toc a").forEach((a) => (a.onclick = (e) => { e.preventDefault(); $(`#g-${a.dataset.g}`).scrollIntoView({ behavior: "smooth", block: "start" }); }));
}

window.__app = { S, selectSite, setMode, showView, recompute };
boot().catch((e) => { console.error(e); $("#loading").textContent = `Failed to load data: ${e.message}. Run pipeline/build_app.py.`; });

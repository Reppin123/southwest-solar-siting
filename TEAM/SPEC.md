# Southwest Solar + Data Center Siting Platform: shared spec

## User's words (voice, verbatim)
"Are you able to access the grid electric grid, and substations in see where there's a good way to connect power and also good land for large scale solar projects. And data centers and and a BLM land that I should apply for. In the Southwest Region."
"Add california to scope out the project identify the sources, and launch multiple agents. With clear tasks and help me build like a nice dashboard or, a proper end to end product that intakes all the data and spells out like... Proper map based visualizations and whatever required. To aid adequate decision making."
"go ahead and build"

Read SCOPE.md in the project root first. It is the approved scope (sources, scoring weights, deliverables, limits).

## Defaults locked
- States: CA, AZ, NV, NM, UT. Clip everything to these five (Census TIGER state boundaries).
- Solar 100 MW to 1 GW (5 to 7 acres/MW, min contiguous block 600 acres). Data center load 50 to 500 MW track included.
- Land: all ownership types; BLM solar-available land flagged and prioritised; state trust and private shown as second pass.
- CRS: store everything in EPSG:4326 for delivery; do area/distance math in a projected CRS (EPSG:5070 CONUS Albers).

## What the finished product is
An end-to-end, re-runnable product in this folder:
1. `pipeline/` scripts that fetch raw public data, process it, screen and score sites, and build the app. One command re-runs everything: `uv run --script pipeline/run_all.py` (stages can be run alone; each stage skips work already done unless --force).
2. `app/` a decision dashboard: a local web app opened with `uv run --script app/serve.py` (serves on http://localhost:8765 and opens the browser). Map-first:
   - Basemap toggle (street / satellite / terrain) from free public tile services (OSM, Esri World Imagery, OpenTopoMap). Map libraries (MapLibre GL JS or Leaflet, plus any plugins) VENDORED into app/vendor, no CDN.
   - Toggleable layers: transmission lines (styled by voltage class), substations (sized by voltage, coloured by queue congestion), BLM solar-available areas / SEZs, land ownership, exclusion layers, solar resource (GHI), fiber, water stress, existing power plants, active BLM solar ROW cases, candidate sites coloured by score.
   - Click any site: scorecard panel (score breakdown by factor, acres, owner, nearest substation + voltage + distance, queued MW nearby, GHI, constraints hit, data center fit, BLM status, recommended next step).
   - Filters and weight sliders (grid / land / sun / permitting / data center) that re-rank sites live in the browser; state filter; min acres; max distance to substation; BLM-only toggle.
   - Ranked site table synced with the map; export current view to CSV.
   - Summary view: charts (sites by state, score distribution, queue GW by state and type, top substations by spare-looking capacity proxy).
   - A Sources and Limits panel listing every dataset, its date, and the caveats from SCOPE.md section 7.
3. `deliverables/`: Southwest_Solar_Sites.xlsx (ranked table), top-site memos, BLM application brief.

## Folder layout and ownership
- data/raw/<domain>/ untouched downloads (gitignored-scale files OK). data/processed/<domain>/ cleaned layers.
- domains: grid, land, infra, sites.
- Processed vector layers: GeoJSON (EPSG:4326) for anything the app loads, simplified so each app-facing file is under ~25 MB (use topology-preserving simplification; keep full-res in a .gpkg next to it for analysis). Rasters: GeoTIFF clipped to the five states, plus a pre-rendered PNG/tile overlay or a vectorised/gridded version for the app.
- Every processed layer gets an entry in data/processed/<domain>/MANIFEST.json: {layer, path, source_name, source_url, retrieved, record_count, fields: {name: description}, caveats}.

## Data contracts (screening and app depend on these exact names)
- data/processed/grid/transmission_lines.geojson: id, voltage_kv (number, null if unknown), volt_class ("<115","115-161","230","345","500+","unknown"), owner, status, state
- data/processed/grid/substations.geojson (points): id, name, max_kv, min_kv, owner, status, lines, state, county
- data/processed/grid/queue_projects.csv: queue_id, entity, poi_name, state, county, type (solar/storage/wind/gas/hybrid/other), mw, status (active/withdrawn/operational), queue_date, source
- data/processed/grid/queue_by_county.csv: state, county, active_mw_total, active_mw_solar, active_mw_storage, n_projects
- data/processed/land/blm_solar_available.geojson, data/processed/land/solar_energy_zones.geojson
- data/processed/land/ownership.gpkg (layer ownership: agency, category in {BLM, USFS, NPS, DOD, Tribal, State, Private, Other}) plus a simplified ownership.geojson
- data/processed/land/exclusions/*.geojson, one file per constraint with field kind in {hard, soft}: wilderness, nca_acec, critical_habitat, flood_zone_a, tribal, military, wetlands, slope_gt5 (derived), urban
- data/processed/land/ghi.tif (kWh/m2/day) and data/processed/land/slope.tif (percent), both clipped
- data/processed/infra/fiber.geojson, data/processed/infra/power_plants.geojson (EIA-860: plant, tech, mw, status), data/processed/infra/blm_solar_row_cases.geojson (or .csv with lat/lon if only points), data/processed/infra/water_stress.geojson (basin/county level), data/processed/infra/roads_major.geojson
- data/processed/sites/candidate_sites.geojson (polygons): site_id, state, county, acres, owner_category, blm_solar_available (bool), sez_name, centroid_lat, centroid_lon, nearest_sub_id, nearest_sub_name, nearest_sub_kv, dist_sub_km, nearest_line_kv, dist_line_km, queued_mw_county, ghi, mean_slope, constraints_soft (list), fiber_km, water_stress, road_km, score_grid, score_land, score_sun, score_permit, score_dc (all 0-100), score_total, rank, next_step
- data/processed/sites/top_sites.csv: top 50 by score_total with all fields.

## Sources (public, free; no paid tools, no logins)
HIFLD (transmission lines, substations; hifld-geoplatform.hub.arcgis.com and ArcGIS REST FeatureServer query endpoints, page with resultOffset), OpenStreetMap power data via Overpass as cross-check/gap fill, Berkeley Lab Queued Up 2026 Excel (emp.lbl.gov/queues), CAISO public queue report, EIA-860 2025, BLM Western Solar Plan GIS (blmsolar.anl.gov, BLM Navigator, BLM ArcGIS REST services incl. Surface Management Agency, national NLCS/wilderness/ACEC layers), MLRS (BLM solar ROW cases), USFWS critical habitat, FEMA NFHL (flood; can be heavy, use state/county NFHL or the FEMA National Flood Hazard REST service with spatial filters; if too large, use a documented proxy and say so), USGS 3DEP (via py3dep or AWS terrain tiles), NREL NSRDB / NREL solar resource GIS (GHI annual average), US Census TIGER (states, counties, tribal areas (AIANNH), roads, urban areas), NWI wetlands (may be heavy; acceptable to use a coarser summary), WRI Aqueduct (water stress), FCC/public fiber route maps or OSM telecom lines as fiber proxy (say clearly it is a proxy).
If a source is down or too heavy, use the documented next-best and record it in MANIFEST caveats. Never fabricate data. Never hardcode results.

## Engineering rules
- Python scripts with a PEP 723 header (pinned deps) run with `uv run --script` (uv is at /opt/homebrew/bin/uv). Never system python3. Geo stack OK: geopandas, shapely, pyogrio, rasterio, numpy, pandas, requests, openpyxl/xlsxwriter.
- Downloads: retry with backoff, resumable (skip if file exists), log to logs/<task>.log.
- Do not write outside this project folder. Do not touch files another task owns.
- Writing style for any text the user reads: plain, specific, sourced; no em dashes; no hype.

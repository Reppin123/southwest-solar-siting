# Data inventory

Every dataset used in this project: its source, when it was retrieved, its licence or terms, and where to get it. All data was retrieved on **2026-10-21** by the `pipeline/fetch_*.py` scripts. The per-layer details (fields, record counts, caveats) are in `data/processed/<domain>/MANIFEST.json`.

There are three places the data lives:

| Where | What | Size |
|---|---|---|
| **This git repo** | All processed layers under 95 MB, the dashboard data (`app/data/`), the deliverables | about 420 MB on disk (about 131 MB compressed in git) |
| **GitHub release [v1.0-data](https://github.com/Reppin123/southwest-solar-siting/releases/tag/v1.0-data)** | The 4 processed files over 95 MB (zstd-compressed), plus a bundle of all the other processed layers | 5 files, about 1.1 GB |
| **Not stored (re-fetchable)** | Raw downloads in `data/raw/` and the screening caches in `data/processed/sites/work/` | raw: land 10 GB, infra 817 MB, grid 75 MB |

## Sources

Licence notes are a summary, not legal advice. "Not verified" means the project did not confirm the terms. Check them with the publisher before you redistribute derived maps commercially.

| Dataset | Used for | Source URL | Licence / terms |
|---|---|---|---|
| HIFLD Electric Power Transmission Lines | `grid/transmission_lines.*` | https://services2.arcgis.com/FiaPA4ga0iQKduv3/arcgis/rest/services/US_Electric_Power_Transmission_Lines/FeatureServer/0 | HIFLD Open data, public domain |
| HIFLD Electric Substations (last public release, via an ArcGIS Online mirror; last edited 2021-02-25) | `grid/substations.*` | https://services5.arcgis.com/HDRa0B57OVrv2E1q/arcgis/rest/services/Electric_Substations/FeatureServer/0 | HIFLD Open data, public domain. Whether the mirror is allowed to redistribute it is not verified (the methodology review raises this) |
| OpenStreetMap power substations (gap fill for substations), telecom lines (fiber proxy), data centers | `grid/substations.*`, `infra/fiber.*`, `infra/data_centers_osm.geojson` | https://overpass-api.de/api/interpreter | ODbL 1.0. Credit "© OpenStreetMap contributors". Derived databases that are shared must also be ODbL |
| Berkeley Lab, Queued Up 2026 Edition (interconnection queue data through 2025) | `grid/queue_projects.csv`, `grid/queue_by_county.csv`, `grid/queue_state_check.csv` | https://emp.lbl.gov/queues ; https://eta-publications.lbl.gov/sites/default/files/2026-05/lbnl_ix_queue_data_file_thru2025.xlsx | Free public release. Cite Berkeley Lab "Queued Up". Exact licence not verified |
| CAISO Public Queue Report | fills missing POI and county in `grid/queue_projects.csv` | https://www.caiso.com/documents/publicqueuereport.xlsx | Public report on caiso.com. Terms not verified |
| US EIA Form EIA-860, 2025 data (files dated 2026-09-09) | `infra/power_plants.geojson`, `infra/power_generators.csv`, `infra/power_plants_by_state.csv` | https://www.eia.gov/electricity/data/eia860/ | US federal government data, public domain. EIA asks to be credited as the source |
| BLM 2024 Western Solar Plan (Solar PEIS Record of Decision geodatabase) and BLM Energy Designations (DRECP areas, layers 12 and 13) | `land/blm_solar_available.*` | https://blmsolar.anl.gov/maps/data/2024-solar-peis/BLM-National-Solar-PEIS-ROD.gdb.zip ; https://services1.arcgis.com/KbxwQRRfWyEYLgp4/arcgis/rest/services/Energy_Designations/FeatureServer/12 and /13 | US federal government data (BLM), public domain |
| BLM Solar Energy Zones (Energy Designations layer 10) | `land/solar_energy_zones.geojson` | https://services1.arcgis.com/KbxwQRRfWyEYLgp4/arcgis/rest/services/Energy_Designations/FeatureServer/10 | BLM, public domain |
| BLM National Surface Management Agency (SMA_WM.gdb) | `land/ownership.*`, `land/exclusions/nps.geojson`, part of `military` | https://www.arcgis.com/sharing/rest/content/items/6bf2e737c59d4111be92420ee5ab0b46/data | BLM, public domain |
| BLM NLCS National Monuments and NCAs; BLM ACEC | `land/exclusions/nca_acec.geojson` | https://services1.arcgis.com/KbxwQRRfWyEYLgp4/arcgis/rest/services/BLM_Natl_NLCS_National_Monuments_National_Conservation_Areas_Polygons/FeatureServer/0 ; https://gis.blm.gov/arcgis/rest/services/lands/BLM_Natl_ACEC/MapServer/0 | BLM, public domain |
| Wilderness Connect (University of Montana) wilderness boundaries; BLM NLCS Wilderness Study Areas | `land/exclusions/wilderness.geojson` | https://services1.arcgis.com/ERdCHt0sNM6dENSD/arcgis/rest/services/Wilderness_Areas_in_the_United_States/FeatureServer/0 ; https://services1.arcgis.com/KbxwQRRfWyEYLgp4/arcgis/rest/services/BLM_Natl_NLCS_Wilderness_Study_Areas_Polygons/FeatureServer/3 | WSAs: BLM, public domain. Wilderness Connect: terms not verified; credit Wilderness Connect |
| BLM MLRS solar rights-of-way (active and closed cases) | `infra/blm_solar_row_cases*` | https://nlsdbpubgis.blm.gov/arcgishub/rest/services/HUB/BLM_Natl_MLRS_LUA_ROW/FeatureServer/0 | BLM, public domain |
| USFWS Critical Habitat | `land/exclusions/critical_habitat.geojson` | https://services.arcgis.com/QVENGdaPbd4LUkLV/arcgis/rest/services/USFWS_Critical_Habitat/FeatureServer/0 | US federal government data (USFWS), public domain |
| USFWS National Wetlands Inventory (wetlands of 40 acres and up only) | `land/exclusions/wetlands.geojson` | https://fwspublicservices.wim.usgs.gov/wetlandsmapservice/rest/services/Wetlands/MapServer/0 | USFWS, public domain |
| FEMA National Flood Hazard Layer, flood zones A/AE/AH/AO/V/VE | `land/exclusions/flood_zone_a.geojson` | https://hazards.fema.gov/arcgis/rest/services/public/NFHL/MapServer/28 | US federal government data (FEMA), public domain |
| US Census Bureau TIGER/Line 2024 and cartographic boundaries 2024 (states, counties, tribal areas, military, urban areas); TIGER 2025 primary roads | `land/admin_*.geojson`, `land/exclusions/{tribal,military,urban}.geojson`, `infra/roads_major.*`, part of `infra/fiber.*` | https://www2.census.gov/geo/tiger/ (exact files in the land and infra MANIFEST.json) | US federal government data, public domain |
| NREL NSRDB PSM v3 GHI, 1998 to 2016 annual average (Internet Archive copy of NREL's file) | `land/ghi.tif`, `land/ghi_overlay.png` | https://web.archive.org/web/20240926182851id_/https://www.nrel.gov/gis/assets/data/nsrdbv3_ghi.zip | Public NREL data for the US Department of Energy. Cite NREL. Exact terms not verified |
| AWS Open Data Terrain Tiles (terrarium, zoom 11), built mainly from USGS 3DEP | `land/slope.tif`, `land/slope_overlay.png`, `land/exclusions/slope_gt5.geojson` | https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png | Open data. Attribution to the underlying sources (USGS 3DEP and others) is required; see the Terrain Tiles attribution page on the AWS Open Data registry |
| WRI Aqueduct 4.0 baseline annual water risk (Y2023M07D05) | `infra/water_stress.*` | https://www.wri.org/data/aqueduct-global-maps-40-data | CC BY 4.0. Credit World Resources Institute |
| Arizona Department of Water Resources AMA and INA boundaries (2024) | `infra/az_ama_ina.geojson` | https://services.arcgis.com/C34zQ7veRS0V1t04/arcgis/rest/services/AMA_INA_2024/FeatureServer/0 | State of Arizona public data. Terms not verified |
| BTS NTAD North American Rail Network (Class I main lines, part of the fiber proxy) | `infra/fiber.*` | https://geodata.bts.gov/datasets/usdot::north-american-rail-network-lines | US DOT, public domain |
| Map tiles in the dashboards (not stored here) | basemaps | OpenStreetMap, Esri World Imagery, OpenTopoMap | Each provider's tile terms. OSM tiles: ODbL data and the OSMF tile usage policy. Esri: Esri terms of use. OpenTopoMap: CC BY-SA |

Derived outputs (`data/processed/sites/*`, `app/data/*`, `deliverables/*`) were made by this project from the sources above. The scoring method is in `data/processed/sites/METHOD.md`.

## What is in the repo vs the release

**In git** (`data/processed/`, 53 files): every file listed in the processed folders except the four below. That includes:
- `grid/`: transmission lines and substations (GeoJSON and GPKG), and the queue CSVs
- `infra/`: power plants, generators, fiber proxy, roads, water stress, AZ AMAs, BLM ROW cases, OSM data centers
- `land/`: the simplified GeoJSON copies of ownership, BLM solar-available land and every exclusion; `ghi.tif` and the overlays; state and county boundaries; solar energy zones
- `sites/`: `candidate_sites.geojson` (60 MB, the largest file in git), `candidate_sites.gpkg`, `all_sites.csv`, the top-site CSVs, the check CSVs and `METHOD.md`

**In release v1.0-data** (https://github.com/Reppin123/southwest-solar-siting/releases/tag/v1.0-data):

| Asset | Unpacks to | Compressed | Original |
|---|---|---|---|
| `slope.tif.zst` | `data/processed/land/slope.tif` (slope in percent, about 90 m, float32) | 680 MB | 682 MB |
| `exclusions_full.gpkg.zst` | `data/processed/land/exclusions_full.gpkg` (full-resolution exclusion layers, one per constraint) | 226 MB | 580 MB |
| `blm_solar_available.gpkg.zst` | `data/processed/land/blm_solar_available.gpkg` (full resolution) | 79 MB | 101 MB |
| `ownership.gpkg.zst` | `data/processed/land/ownership.gpkg` (full-resolution surface management agency) | 61 MB | 101 MB |
| `processed_layers_small.tar.zst` | everything else in `data/processed/` (the same 53 files as in git), for people who do not use git | 56 MB | about 276 MB |
| `SHA256SUMS.txt` | the checksums below | | |

The screening stage (`pipeline/screen.py`) needs the four large files. The dashboards and deliverables do not.

**Not stored:** `data/raw/` (about 11 GB of original downloads) and `data/processed/sites/work/` (screening caches). To get the raw files, run `uv run --script pipeline/run_all.py`. The fetch stages download them again from the URLs above. They resume and skip files that already exist.

## Download and unpack the release files

You need the GitHub CLI (`gh`), access to the private repo, and `zstd` (`brew install zstd` on a Mac). Run these from the repo root:

```
gh release download v1.0-data -R Reppin123/southwest-solar-siting -D release-dl
cd release-dl && shasum -a 256 -c <(grep -v '^original' SHA256SUMS.txt | awk '{print $2"  "$3}') && cd ..
for f in slope.tif exclusions_full.gpkg ownership.gpkg blm_solar_available.gpkg; do
  zstd -d release-dl/$f.zst -o data/processed/land/$f
done
# optional, only if you did not clone the repo:
# zstd -dc release-dl/processed_layers_small.tar.zst | tar -xf -
```

You can also download each file from the release page in a browser.

## Checksums (SHA-256)

Compressed release assets:

```
e9d49d6d0011e40ccef9a0b2ea6618e61fda1ffb5a8468b68cc5b1902c6baf53  slope.tif.zst
8d2e979031e7efb772ca6137f912b3f6ffe25403584457509c0791975e96b8d3  exclusions_full.gpkg.zst
400204d25c8c686d5e6c87df7617f194473263792044d7599e819bff4bc543dd  blm_solar_available.gpkg.zst
3a5e15de257a40fbce10ed05e1b2fb9de3cfc3b3bd555b5be49a8b6225e33a8e  ownership.gpkg.zst
0ce7f078d0a2b1a0b514a74f96623b69f057aaf760bc42c84e665311ea470016  processed_layers_small.tar.zst
```

Original files, after unpacking:

```
e92e1c9a8572f33ab98665f65f767efa0f49ba3ef9161ae9dea37041617f3cdf  data/processed/land/slope.tif
48e0455cc3683968c3ebb97cda38b43b2bf4a3580fed497ff095483e569b41a8  data/processed/land/exclusions_full.gpkg
cd828e56c2ab9282ec244370b3b9371a6928c6f3a19a964332240f0dc844f94e  data/processed/land/blm_solar_available.gpkg
06dfe02518daf5a5fb0c2ef91591c29ad81c04961bad73501c0927b6a93fbd5f  data/processed/land/ownership.gpkg
```

These were checked after upload. GitHub's reported digest matched every asset. One asset (`ownership.gpkg.zst`) was downloaded again, unpacked, and matched the original's checksum.

The release was built with `scripts/package_release.sh`. It compresses one file at a time and uploads it, which keeps disk use low. Running `ONLY=<path> scripts/package_release.sh` handles a single file.

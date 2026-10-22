# Dashboard headless test results

Run: 2026-10-22 00:19:23 with `uv run --script app/tests/test_app.py` (Playwright 1.48.0, bundled Chromium, headless, software WebGL; test server on port 8771).
Total time 154 s. Hard limit per step: 30 s (first page load: 150 s).

**76 passed, 0 failed**

| # | Check | Result | Detail |
|---|---|---|---|
| 1 | test server answers | PASS | http://localhost:8771/app/ |
| 2 | page loads with data | PASS | 7.2 s |
| 3 | Map is the default view | PASS |  |
| 4 | sites from all five states | PASS | 25733 sites, ['AZ', 'CA', 'NM', 'NV', 'UT'] |
| 5 | map libraries load locally (no CDN scripts) | PASS |  |
| 6 | default solar ranking matches pipeline rank_solar (top 25, within 2 places) | PASS | 0 mismatches |
| 7 | default dc ranking matches pipeline rank_dc (top 25, within 2 places) | PASS | 0 mismatches |
| 8 | layer on/off: transmission_lines | PASS | 9086 features |
| 9 | layer on/off: substations | PASS | 5295 features |
| 10 | layer on/off: blm_solar_available | PASS | 19198 features |
| 11 | layer on/off: solar_energy_zones | PASS | 26 features |
| 12 | layer on/off: ownership | PASS | 28672 features |
| 13 | layer on/off: excl_wilderness | PASS | 1619 features |
| 14 | layer on/off: excl_nca_acec | PASS | 6704 features |
| 15 | layer on/off: excl_critical_habitat | PASS | 3998 features |
| 16 | layer on/off: excl_flood_zone_a | PASS | 22 features |
| 17 | layer on/off: excl_tribal | PASS | 1766 features |
| 18 | layer on/off: excl_military | PASS | 818 features |
| 19 | layer on/off: excl_wetlands | PASS | 30 features |
| 20 | layer on/off: excl_slope_gt5 | PASS | 15074 features |
| 21 | layer on/off: excl_urban | PASS | 1186 features |
| 22 | layer on/off: excl_nps | PASS | 495 features |
| 23 | layer on/off: power_plants | PASS | 3025 features |
| 24 | layer on/off: blm_solar_row_cases | PASS | 307 features |
| 25 | layer on/off: fiber | PASS | 1105 features |
| 26 | layer on/off: water_stress | PASS | 583 features |
| 27 | layer on/off: roads_major | PASS | 1728 features |
| 28 | layer on/off: data_centers_osm | PASS | 258 features |
| 29 | layer on/off: admin_states | PASS | 5 features |
| 30 | layer on/off: admin_counties | PASS | 152 features |
| 31 | layer on/off: raster_ghi | PASS | 1 features |
| 32 | layer on/off: raster_slope | PASS | 1 features |
| 33 | layer on/off: candidate sites | PASS |  |
| 34 | basemap switch: satellite | PASS |  |
| 35 | basemap switch: terrain | PASS |  |
| 36 | basemap switch: street | PASS |  |
| 37 | click site on map opens scorecard | PASS | SW-NM-00001 |
| 38 | scorecard shows substation, queue, GHI, BLM status, data center fit | PASS |  |
| 39 | provisional badge on scorecard | PASS | SW-NM-00097 |
| 40 | weight slider (sun) re-ranks sites | PASS | sun weight 20 -> 45; top site SW-NM-00001 |
| 41 | ranked table synced with new ranking | PASS | SW-NM-00001 |
| 42 | BLM-only filter | PASS | 3,866 of 25,733 sites shown |
| 43 | ranking switch to Solar + Data Center | PASS | top DC site SW-NM-00001 |
| 44 | ranking switch back to Solar | PASS | top solar site SW-NM-00001 |
| 45 | CSV export of current view | PASS | 2001 rows, 55 columns, file southwest_sites_solar_g35-l30-s20-p15-d0_2001.csv |
| 46 | table sorts by column | PASS | [5508.757, 5180.066, 5174.026, 4947.395, 4936.232] |
| 47 | table row click selects site | PASS |  |
| 48 | Summary tab: charts render | PASS | 4 charts |
| 49 | Sources and Limits tab: datasets, provisional note, SCOPE limits, appendix link | PASS | 23532 chars |
| 50 | Deliverables tab: Excel, memos, BLM brief | PASS |  |
| 51 | every deliverable link resolves | PASS | 21 links |
| 52 | How to Read This tab opens with all 10 sections | PASS | what, ask, good, map, use, score, prep, limits, next, glossary |
| 53 | How to Read This: answers red line / red dots, legend, limits, next steps, glossary | PASS | 13272 chars |
| 54 | How to Read This: no em or en dashes | PASS |  |
| 55 | How to Read This: legend swatches drawn from layers.json | PASS | 45 swatches |
| 56 | methodology review appendix renders | PASS |  |
| 57 | site memo renders | PASS | 01_SW-NM-00001.md |
| 58 | 1440 px layout: no overlapping panels | PASS | {"sidebarOverMap": false, "headerWrap": false, "tabsHitMode": false, "tableUnderMap": false, "docScrollX": false} |
| 59 | screenshot overview 1440 | PASS |  |
| 60 | screenshot scorecard open 1440 | PASS |  |
| 61 | screenshot data center ranking 1440 | PASS |  |
| 62 | screenshot summary tab 1440 | PASS |  |
| 63 | screenshot sources tab 1440 | PASS |  |
| 64 | screenshot How to Read This tab 1440 | PASS |  |
| 65 | 1280 px layout: no overlapping panels | PASS | {"sidebarOverMap": false, "headerWrap": false, "tabsHitMode": false, "tableUnderMap": false, "docScrollX": false} |
| 66 | screenshot overview 1280 | PASS |  |
| 67 | screenshot scorecard open 1280 | PASS |  |
| 68 | screenshot data center ranking 1280 | PASS |  |
| 69 | screenshot summary tab 1280 | PASS |  |
| 70 | screenshot sources tab 1280 | PASS |  |
| 71 | screenshot How to Read This tab 1280 | PASS |  |
| 72 | no console errors or page errors | PASS | none |
| 73 | README.md present (run, refresh, sources, limits, folder map) | PASS |  |
| 74 | pipeline/run_all.py --help works | PASS |  |
| 75 | run_all skips completed stages by default (--dry-run, no re-run) | PASS | 9 of 9 stages skipped |
| 76 | serve.py default port 8770 | PASS |  |

Screenshots saved in app/screenshots/:

- 01_overview_1280.png
- 01_overview_1440.png
- 02_scorecard_1280.png
- 02_scorecard_1440.png
- 03_dc_ranking_1280.png
- 03_dc_ranking_1440.png
- 04_summary_1280.png
- 04_summary_1440.png
- 05_sources_1280.png
- 05_sources_1440.png
- 06_how_to_read_1280.png
- 06_how_to_read_1440.png
- 07_how_to_read_map_legend_1280.png
- 07_how_to_read_map_legend_1440.png

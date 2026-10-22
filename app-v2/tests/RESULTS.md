# Dashboard v2 headless test results

Run: 2026-10-22 01:12:28 with `uv run --script app-v2/tests/test_v2.py` (Playwright 1.48.0, bundled Chromium, headless, software WebGL; test server app-v2/serve.py on port 4110).
Total time 141 s. Hard limit per step: 30 s; a progress line is printed every 30 s.

**97 passed, 0 failed**

Every check of v1's app/tests/test_app.py is ported, except the two that run pipeline/run_all.py: that script belongs to the pipeline, not the dashboard, and running it from here could write outside app-v2/. The How to Read This colour words are checked in their v2 form (DESIGN.md section 9.3).

| # | Check | Result | Detail |
|---|---|---|---|
| 1 | test server answers | PASS | http://localhost:4110/app-v2/ |
| 2 | page loads with data | PASS | 3.9 s |
| 3 | Map is the default view | PASS |  |
| 4 | sites from all five states | PASS | 25733 sites, ['AZ', 'CA', 'NM', 'NV', 'UT'] |
| 5 | map libraries load locally (no CDN scripts) | PASS |  |
| 6 | no stylesheet or font from another origin | PASS |  |
| 7 | self-hosted fonts load (Source Serif 4, IBM Plex Sans) | PASS | IBM Plex Sans 400, IBM Plex Sans 500, IBM Plex Sans 600, Source Serif 4 200 900 |
| 8 | no em dash in any visible text | PASS |  |
| 9 | no rounded boxes (corner radius at most 2 px) | PASS | none |
| 10 | no soft drop shadows | PASS | none |
| 11 | map key lists exactly the layers that are on, sites first | PASS | sites, transmission_lines, substations, blm_solar_available, admin_states |
| 12 | default solar ranking matches pipeline rank_solar (top 25, within 2 places) | PASS | 0 mismatches |
| 13 | default dc ranking matches pipeline rank_dc (top 25, within 2 places) | PASS | 0 mismatches |
| 14 | layer on/off: transmission_lines | PASS | 9086 features, map key follows |
| 15 | layer on/off: substations | PASS | 5295 features, map key follows |
| 16 | layer on/off: blm_solar_available | PASS | 19198 features, map key follows |
| 17 | layer on/off: solar_energy_zones | PASS | 26 features, map key follows |
| 18 | layer on/off: ownership | PASS | 28672 features, map key follows |
| 19 | layer on/off: excl_wilderness | PASS | 1619 features, map key follows |
| 20 | layer on/off: excl_nca_acec | PASS | 6704 features, map key follows |
| 21 | layer on/off: excl_critical_habitat | PASS | 3998 features, map key follows |
| 22 | layer on/off: excl_flood_zone_a | PASS | 22 features, map key follows |
| 23 | layer on/off: excl_tribal | PASS | 1766 features, map key follows |
| 24 | layer on/off: excl_military | PASS | 818 features, map key follows |
| 25 | layer on/off: excl_wetlands | PASS | 30 features, map key follows |
| 26 | layer on/off: excl_slope_gt5 | PASS | 15074 features, map key follows |
| 27 | layer on/off: excl_urban | PASS | 1186 features, map key follows |
| 28 | layer on/off: excl_nps | PASS | 495 features, map key follows |
| 29 | layer on/off: power_plants | PASS | 3025 features, map key follows |
| 30 | layer on/off: blm_solar_row_cases | PASS | 307 features, map key follows |
| 31 | layer on/off: fiber | PASS | 1105 features, map key follows |
| 32 | layer on/off: water_stress | PASS | 583 features, map key follows |
| 33 | layer on/off: roads_major | PASS | 1728 features, map key follows |
| 34 | layer on/off: data_centers_osm | PASS | 258 features, map key follows |
| 35 | layer on/off: admin_states | PASS | 5 features, map key follows |
| 36 | layer on/off: admin_counties | PASS | 152 features, map key follows |
| 37 | layer on/off: raster_ghi | PASS | 1 features, map key follows |
| 38 | layer on/off: raster_slope | PASS | 1 features, map key follows |
| 39 | layer on/off: candidate sites | PASS |  |
| 40 | Source panel opens with source, retrieved date and caveats; Esc closes it | PASS |  |
| 41 | basemap switch: satellite | PASS | satellite |
| 42 | basemap switch: terrain | PASS | terrain |
| 43 | basemap switch: plain | PASS | no raster base |
| 44 | basemap switch: street | PASS | street |
| 45 | click site on map opens scorecard | PASS | SW-NM-00001 |
| 46 | scorecard shows substation, queue, GHI, BLM status, data center fit | PASS |  |
| 47 | scorecard opens as a column beside the map (map narrows, nothing covers it) | PASS | map 1144 -> 752 px, sheet 392 px |
| 48 | selected site outlined in ink over a white halo | PASS |  |
| 49 | provisional badge on scorecard | PASS | SW-NM-00097 |
| 50 | Esc closes the scorecard and returns the width to the map | PASS |  |
| 51 | weight slider (sun) re-ranks sites | PASS | sun weight 20 -> 45; top site SW-NM-00001 |
| 52 | ranked table synced with new ranking | PASS | SW-NM-00001 |
| 53 | BLM-only filter | PASS | 3,866 of 25,733 sites shown |
| 54 | rail readout follows the filters | PASS | 3,866 |
| 55 | state filter (untick UT) | PASS |  |
| 56 | ranking switch to Solar + Data Center | PASS | top DC site SW-NM-00001 |
| 57 | ranking switch back to Solar | PASS | top solar site SW-NM-00001 |
| 58 | CSV export of current view | PASS | 1963 rows, 55 columns, file southwest_sites_solar_g35-l30-s20-p15-d0_1963.csv |
| 59 | table sorts by column | PASS | [5508.757, 5180.066, 5174.026, 4947.395, 4936.232] |
| 60 | table row click selects site (and the map flies to it) | PASS | SW-CA-02558 |
| 61 | Summary tab: charts render | PASS | 4 charts |
| 62 | Summary tab: five figures and HTML chart keys | PASS |  |
| 63 | Sources and Limits tab: datasets, provisional note, SCOPE limits, appendix link | PASS | 23681 chars |
| 64 | reading tabs hide the controls column | PASS |  |
| 65 | Deliverables tab: Excel, memos, BLM brief | PASS |  |
| 66 | every deliverable link resolves | PASS | 21 links |
| 67 | Show on map opens the map and the memo's site | PASS | SW-NM-00001 |
| 68 | How to Read This present (tab, page and table of contents) | PASS |  |
| 69 | How to Read This tab opens with all 10 sections | PASS | what, ask, good, map, use, score, prep, limits, next, glossary |
| 70 | How to Read This: answers big lines / crowded substations, legend, limits, next steps, glossary | PASS | 13489 chars |
| 71 | How to Read This: colour words match the v2 map (no teal, purple, mustard, red dots) | PASS | none |
| 72 | How to Read This: no em or en dashes | PASS |  |
| 73 | How to Read This: legend swatches drawn from the map colours | PASS | 45 swatches |
| 74 | methodology review appendix renders | PASS |  |
| 75 | site memo renders | PASS | 01_SW-NM-00001.md |
| 76 | 1440 px layout: no overlapping panels, nothing wraps | PASS | {"sidebarOverMap": false, "headerWrap": false, "tabsHitMode": false, "brandHitTabs": false, "tableUnderMap": false, "docScrollX": false, "statesWrap": false} |
| 77 | screenshot overview 1440 | PASS |  |
| 78 | screenshot scorecard open 1440 | PASS |  |
| 79 | screenshot data center ranking 1440 | PASS |  |
| 80 | screenshot summary tab 1440 | PASS |  |
| 81 | screenshot sources tab 1440 | PASS |  |
| 82 | screenshot How to Read This tab 1440 | PASS |  |
| 83 | screenshot deliverables tab 1440 | PASS |  |
| 84 | 1280 px layout: no overlapping panels, nothing wraps | PASS | {"sidebarOverMap": false, "headerWrap": false, "tabsHitMode": false, "brandHitTabs": false, "tableUnderMap": false, "docScrollX": false, "statesWrap": false} |
| 85 | screenshot overview 1280 | PASS |  |
| 86 | screenshot scorecard open 1280 | PASS |  |
| 87 | screenshot data center ranking 1280 | PASS |  |
| 88 | screenshot summary tab 1280 | PASS |  |
| 89 | screenshot sources tab 1280 | PASS |  |
| 90 | screenshot How to Read This tab 1280 | PASS |  |
| 91 | screenshot deliverables tab 1280 | PASS |  |
| 92 | under 1100 px the controls become a drawer and the tabs a menu; masthead fits | PASS |  |
| 93 | no console errors or page errors | PASS | none |
| 94 | project README.md present (run, refresh, sources, limits, folder map) | PASS |  |
| 95 | v2 serve.py default port 8772 and v2 README explains how to open it | PASS |  |
| 96 | index.html: no CDN script, no em dash | PASS |  |
| 97 | v1 files unchanged (checksums of app/ before and after) | PASS | 61 files compared |

Screenshots saved in app-v2/screenshots/:

- 01_overview_1280.png
- 01_overview_1440.png
- 02_scorecard_1280.png
- 02_scorecard_1440.png
- 03_dc_ranking_1280.png
- 03_dc_ranking_1440.png
- 04_summary_1280.png
- 04_summary_1440.png
- 04b_summary_lower_1280.png
- 04b_summary_lower_1440.png
- 05_sources_1280.png
- 05_sources_1440.png
- 06_how_to_read_1280.png
- 06_how_to_read_1440.png
- 07_how_to_read_map_legend_1280.png
- 07_how_to_read_map_legend_1440.png
- 08_deliverables_1280.png
- 08_deliverables_1440.png
- 09_narrow_controls_900.png
- compare_01_overview_1280.png
- compare_01_overview_1440.png
- compare_02_scorecard_1280.png
- compare_02_scorecard_1440.png

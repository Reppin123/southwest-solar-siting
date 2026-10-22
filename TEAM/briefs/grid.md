# Brief: grid (transmission, substations, interconnection queues)
Objective: produce the grid layers for CA, AZ, NV, NM, UT exactly per the SPEC data contracts.
Owns: pipeline/fetch_grid.py, pipeline/process_grid.py, data/raw/grid/**, data/processed/grid/**, logs/grid.log. Must not touch other domains, app/**, or TEAM/**.
User's words: "access the grid electric grid, and substations in see where there's a good way to connect power". "identify the sources".
Do:
1. HIFLD Electric Power Transmission Lines and Electric Substations via ArcGIS REST query (geometry filtered to the five-state bbox, paged), clip to state polygons (download Census TIGER states into data/raw/grid/ if land task has not; you may read data/processed/land/ if present but must not depend on it).
2. Derive volt_class; join state/county to substations; count connected lines per substation (spatial snap within 200 m) if HIFLD LINES field missing.
3. OSM Overpass cross-check for substations >=115 kV missing from HIFLD (add with source="osm"), documented.
4. Berkeley Lab Queued Up 2026 Excel: filter to the five states; normalise to queue_projects.csv; aggregate queue_by_county.csv. Add CAISO public queue if it adds POI substation names.
5. MANIFEST.json for every layer.
Done means: all grid contract files exist and parse; counts reported in MANIFEST; a 500 kV line exists in each of CA, AZ, NV; substations have state set; queue totals by state roughly match the Queued Up report (note the comparison).

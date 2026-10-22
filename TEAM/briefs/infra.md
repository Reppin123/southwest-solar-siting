# Brief: infra (data center inputs, existing plants, BLM ROW cases)
Objective: produce the infrastructure layers per SPEC for CA, AZ, NV, NM, UT.
Owns: pipeline/fetch_infra.py, pipeline/process_infra.py, data/raw/infra/**, data/processed/infra/**, logs/infra.log. Must not touch other domains, app/**, TEAM/**.
User's words: "And data centers" ... "good way to connect power".
Do:
1. EIA-860 (latest annual, 2025) plants + generators: plant points with tech, nameplate MW, status; filter to five states.
2. Fiber: best free source (OSM telecom/cable routes, public long-haul fiber maps, FCC data); label as proxy where it is.
3. Water stress: WRI Aqueduct baseline water stress at basin level clipped; plus a short note on groundwater rules (AZ AMAs) in MANIFEST caveats.
4. Major roads (TIGER primary roads / interstates).
5. BLM active and pending solar right-of-way cases (MLRS or BLM renewable energy project layer); points or polygons with case id, project name, MW, status.
6. Existing data centers if a free public list exists (OSM telecom=data_center / building=data_center); optional.
7. MANIFEST.json for every layer.
Done means: contract files exist and parse; EIA plants count per state reported; ROW cases present or a documented reason why not.

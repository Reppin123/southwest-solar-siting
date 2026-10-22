# Southwest Solar + Data Center Siting Study: Scope

Prepared 2026-10-21 for Aki. Status: draft for approval.

## 1. Objective
Find and rank sites in the Southwest that combine (a) a realistic grid connection, (b) buildable land with strong sun, and (c) where relevant, a fit for co-located data centers. Flag BLM parcels worth a right-of-way application.

## 2. Assumptions (change any of these)
- States: California, Arizona, Nevada, New Mexico, Utah (confirmed 2026-10-21).
- Project size: 100 MW to 1 GW solar, optionally paired with storage and a data center load of 50 to 500 MW.
- Land: BLM public land first, then large private and state trust parcels as a second pass.
- Rule of thumb: about 5 to 7 acres per MW of solar, so 100 MW needs roughly 500 to 700 contiguous acres.

## 3. Data layers and sources (all public, no paid tools)
| Layer | Source | Use |
|---|---|---|
| Transmission lines, 69 kV to 765 kV | HIFLD Electric Power Transmission Lines (DHS, updated 2026) | Distance to line, voltage class |
| Substations | HIFLD Electric Substations; OpenStreetMap power tags as cross-check | Distance to substation, max voltage |
| Interconnection queues | Berkeley Lab Queued Up 2026 (data through end of 2025); CAISO, LADWP, IID, SRP, APS, TEP, PNM, NV Energy, PacifiCorp queues | Congestion near each substation (GW already queued) |
| BLM solar availability | BLM Western Solar Plan (2024 ROD) GIS layers, Solar Energy Zones, priority areas, via blmsolar.anl.gov and BLM Navigator | Where BLM accepts solar applications |
| Land status / ownership | BLM Surface Management Agency layer; state trust land layers (CA State Lands Commission, AZ State Land Dept, NM SLO, UT SITLA, NV) | Federal vs state vs private |
| Solar resource | NREL National Solar Radiation Database (GHI / DNI) | Energy yield |
| Terrain | USGS 3DEP elevation (slope) | Exclude slope above about 5 percent |
| Exclusions | USFWS critical habitat, FEMA flood zones, wilderness / NCAs / ACECs, tribal land, military operating areas, wetlands (NWI) | Hard and soft constraints |
| Data center inputs | Long-haul fiber routes (public maps), water availability / groundwater basins, highway access, existing large-load substations | Data center suitability |
| Existing projects | EIA-860 generator data, BLM active solar ROW cases (MLRS) | Avoid occupied land, find clusters |

## 4. Screening method
1. Build a grid of candidate cells (about 1 km) across the five states.
2. Remove hard exclusions (wilderness, critical habitat, tribal, flood, steep slope, military).
3. Keep cells that form contiguous blocks of at least 600 acres.
4. Score each block on:
   - Grid: distance to nearest 115 kV+ substation and 230 kV+ line, queue congestion at that substation (30 percent)
   - Land: BLM solar-available status, ownership simplicity, slope, block size (25 percent)
   - Sun: annual GHI (15 percent)
   - Permitting risk: soft constraints nearby, sensitive species, visual / cultural flags (15 percent)
   - Data center fit: fiber distance, water, road access (15 percent, only for the data center track)
5. Rank the top 25 sites; deep-dive the top 5 to 10.

## 5. Deliverables
1. Interactive map (one self-contained HTML file, works offline): all layers toggleable, candidate sites colored by score, click any site for its scorecard.
2. Ranked site table (Excel): coordinates, county, acres, owner, nearest substation and voltage, distance, queued GW nearby, GHI, constraints, score.
3. Top-site memos (short, one per top site): why it works, grid path, key risks, next step.
4. BLM application brief: which sites fall in BLM solar-available areas, the right-of-way process (SF-299 application, cost recovery, NEPA review), current fees and rent, and the 2025 policy changes affecting solar on federal land, with what to file first.

## 6. Phases and timing
| Phase | Work | Time |
|---|---|---|
| 1. Data pull | Download and clip all layers to the five states | Same day |
| 2. Screening | Exclusions, contiguity, scoring | Same day |
| 3. Map + table | Build the HTML map and Excel ranking | Day 1 to 2 |
| 4. Deep dives | Top site memos, queue check per substation | Day 2 |
| 5. BLM brief | Process, fees, current policy, filing plan | Day 2 |
Runs as background helpers; Aki can keep working.

## 7. Limits to know up front
- Public maps show where lines and substations are, not how much spare capacity they have. Real capacity comes from the utility through a pre-application or interconnection request; queue congestion is the best public proxy.
- Some substation and line data is incomplete or generalized for security reasons.
- Federal review of solar and wind on public land became stricter in 2025. The BLM brief will confirm the current rules before anything is filed.
- This is a screening study, not engineering. Top sites still need a utility pre-application meeting, title and survey, and environmental review.

## 8. Decisions needed from Aki
1. States: confirm AZ, NV, NM, UT, and whether to add southeastern California.
2. Size: target MW, and whether storage is included.
3. Data center track: include it, and what load size.
4. Land: BLM only, or also state trust and private land.

# Brief: land (BLM solar availability, ownership, exclusions, sun, slope)
Objective: produce land suitability and constraint layers for CA, AZ, NV, NM, UT per the SPEC data contracts.
Owns: pipeline/fetch_land.py, pipeline/process_land.py, data/raw/land/**, data/processed/land/**, logs/land.log. Must not touch other domains, app/**, TEAM/**.
User's words: "good land for large scale solar projects ... a BLM land that I should apply for. In the Southwest Region." plus California.
Do:
1. Census TIGER: states, counties, AIANNH tribal areas, urban areas (write states/counties to data/processed/land/admin_states.geojson and admin_counties.geojson; others may read them).
2. BLM Western Solar Plan (2024 ROD) solar-available / open-to-application areas and Solar Energy Zones (blmsolar.anl.gov GIS downloads or BLM REST). If the 2024 plan layer is not downloadable, use the best official layer available and document it.
3. Ownership from BLM Surface Management Agency (SMA) layer, categorised per SPEC.
4. Exclusions per SPEC (wilderness, NCA/ACEC, USFWS critical habitat, FEMA flood zone A/V, tribal, DOD/military, wetlands, urban) with kind hard/soft (hard: wilderness, NPS, critical habitat, tribal, military, flood A/V, urban; soft: ACEC, wetlands proxy, etc. Document choices).
5. GHI raster (NREL NSRDB or NREL solar resource GIS) clipped; slope from USGS 3DEP at ~90 m (downsample is fine), plus slope_gt5 exclusion polygons.
6. MANIFEST.json for every layer.
Done means: contract files exist and parse; named SEZs (e.g. Riverside East CA, Dry Lake NV, Afton NM, Milford Flats South UT, Agua Caliente AZ) appear if in the source; rasters cover all five states; caveats documented.

# Brief: screening (candidate sites + scores + ranked deliverables)
Objective: turn the grid, land and infra layers into scored candidate sites per SCOPE.md section 4 and the SPEC sites contract, plus the ranked Excel and top-site memos.
Owns: pipeline/screen.py, pipeline/memos.py, data/processed/sites/**, deliverables/Southwest_Solar_Sites.xlsx, deliverables/site_memos/**, logs/screening.log. Read-only on data/processed/{grid,land,infra}. Must not touch app/**, TEAM/**.
User's words: "see where there's a good way to connect power and also good land for large scale solar projects. And data centers and ... BLM land that I should apply for." "To aid adequate decision making."
Do:
1. Grid of ~1 km cells over the five states (EPSG:5070); remove hard exclusions and slope >5%; dissolve contiguous remaining cells by ownership category; keep blocks >= 600 acres (split very large blocks into ~2,000-5,000 acre sites so ranking is meaningful).
2. Compute every contract field (distances via spatial index; queued MW by county; GHI and slope zonal means; soft constraints touched; fiber/road distance; water stress).
3. Scores 0-100 per factor with documented transforms (e.g. distance decay), weights grid 30 / land 25 / sun 15 / permit 15 / dc 15, and score_total; BLM solar-available gets a land bonus; rank. Put weights and transforms in a WEIGHTS dict at the top of screen.py and in data/processed/sites/METHOD.md.
4. next_step text per site (e.g. "Request pre-application with BLM Las Vegas FO; ask NV Energy about capacity at <substation>").
5. Excel: Top 50 sheet, All Sites sheet, Method sheet, Sources sheet; live formulas for score_total from factor scores and a weights block so Aki can change weights in Excel. Use XlsxWriter with cached values.
6. Memos for top 10 sites (markdown, one page each): location, why, grid path, risks, BLM/ownership status, next steps; plus deliverables/site_memos/README.md index.
Done means: candidate_sites.geojson and top_sites.csv exist with all contract fields; no site intersects a hard exclusion (check and report); sites exist in all five states or a stated reason; Excel opens with formulas; 10 memos.

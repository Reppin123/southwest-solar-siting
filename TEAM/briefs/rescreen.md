# Brief: rescreen (finish screening with review fixes, Excel, memos)
Read briefs/screening.md first: everything in it still applies. This is a resumed run. A previous attempt already produced data/processed/sites/candidate_sites.* , all_sites.csv, top_sites.csv and a cache in data/processed/sites/work/. It was killed for being silent 8 minutes during a long step, before writing the Excel and memos.
Also read the independent review: /Users/akshitbansal/research/southwest-solar-siting-review/review/METHODOLOGY_REVIEW.md (read only).
Owns: same as screening (pipeline/screen.py, pipeline/memos.py, data/processed/sites/**, deliverables/Southwest_Solar_Sites.xlsx, deliverables/site_memos/**, logs/screening.log).

Apply these fixes (approved direction from the user's agent after the GPT review):
1. Two rankings. score_total_solar (grid 35 / land 30 / sun 20 / permit 15, no data center term) and score_total_dc (grid 30 / land 25 / sun 15 / permit 15 / dc 15). rank_solar and rank_dc. top_sites.csv = top 50 by solar; add top_sites_dc.csv. Keep score_total as an alias of score_total_solar for the app contract.
2. Provisional grid flags per site: sub_source (hifld/osm), sub_kv_source (hifld/osm/osm_match/inferred_from_lines), sub_provisional (true if osm or inferred or name starts with UNKNOWN). Apply a modest grid-score penalty (e.g. x0.85) to provisional substations and say so in METHOD.md.
3. Exclude unsuitable POIs before nearest-substation search: HVDC converter stations (name contains HVDC or Converter, e.g. SunZia), generator-owned/collector substations where the owner or name indicates a plant (Solar, Wind, Energy Center, Collector, Gen) unless they are utility-owned, and retired/not-in-service status. Log how many were removed.
4. Queue congestion: keep county-level term but add queue_confidence (high when the county has POI-matched active projects, low when active MW is 0 or POI match rate is low); counties with 0 active MW are treated as unknown (neutral midpoint), not best.
5. Keep constraints_soft in the GeoJSON as a semicolon-joined string (the previous run dropped it as an unsupported list type).

Avoid being killed again: log a progress line at least every 60 seconds during any long step (chunked loops with log lines, or run heavy steps in the background and tail the log). Reuse data/processed/sites/work cache for cells and geometry; only recompute what the fixes change.
Excel: All Sites sheet as plain values (37k+ rows), Top 50 Solar and Top 50 Data Center sheets with live score formulas and an editable weights block, Method and Sources sheets, plus a Provisional Data note. Use XlsxWriter with cached values.
Memos: top 10 by solar ranking plus top 5 by data center ranking (skip duplicates), each noting provisional flags and the offline checks from the review's checklist.
Update METHOD.md with all changes and a before/after comparison of the top 10 (old ranks are in the existing top_sites.csv; save it as top_sites_v1.csv before overwriting).
Done means: candidate_sites.geojson and top_sites.csv/top_sites_dc.csv have the new fields; no site intersects a hard exclusion (report the check); no top-50 site uses an excluded POI; Excel opens with formulas; at least 10 memos; METHOD.md has the before/after table.

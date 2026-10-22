# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pyogrio==0.10.0",
#   "geopandas==1.0.1",
#   "shapely==2.0.6",
#   "numpy==2.1.3",
#   "pandas==2.2.3",
# ]
# ///
"""One-page markdown memos for the top candidate sites, plus a README index.

Reads data/processed/sites/candidate_sites.geojson (from screen.py) and the grid / land /
infra layers for context. Memos: the top 10 by the solar ranking (rank_solar) plus the top 5
by the data center ranking (rank_dc), skipping sites already covered. Each list takes at most
one site per contiguous ownership block and per nearest substation, so the memos cover distinct
places (also across the two lists) rather than neighbouring tiles of the same block. Each memo lists its provisional-data
flags and the offline checks from the 2026-10-21 methodology review.

Run: uv run --script pipeline/memos.py [--force]
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely

ROOT = Path(__file__).resolve().parent.parent
P = ROOT / "data" / "processed"
OUT = ROOT / "deliverables" / "site_memos"
LOG = ROOT / "logs" / "screening.log"
CRS = "EPSG:5070"
N_SOLAR = 10
N_DC = 5
FLAG_TEXT = {
    "acec": "touches a BLM Area of Critical Environmental Concern (ACEC); under the 2024 Western Solar Plan ACECs are excluded on BLM land, so the footprint must avoid it",
    "wetlands_nwi": "touches an NWI wetland or water feature of 40+ acres (proxy layer; site delineation needed)",
    "active_blm_row_case": "overlaps an active BLM solar right-of-way case in MLRS (competing claim)",
    "near_critical_habitat_1km": "within 1 km of designated critical habitat",
    "near_protected_area_1km": "within 1 km of wilderness / WSA, an NCA or monument, or NPS land",
    "existing_plant_on_site": "an operating EIA-860 power plant point lies inside the site (part may be occupied)",
    "blm_outside_available": "BLM land outside Western Solar Plan Available areas / DRECP DFAs (not open to solar ROW applications)",
    "drecp_variance": "DRECP Variance Land (extra BLM process)",
    "federal_review": "BLM land: NEPA review plus the 2025 DOI Secretary-level review of solar actions",
    "az_ama": "inside an Arizona groundwater Active Management Area (limits new groundwater use, relevant to data center cooling)",
}

log = logging.getLogger("memos")


def fnum(x, d=1, unit=""):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "unknown"
    return f"{x:,.{d}f}{unit}"


def pick_top(s):
    """Top N_SOLAR by rank_solar, then top N_DC by rank_dc that are not already picked."""
    used_sites, used_blocks, used_subs, rows = set(), set(), set(), []
    for track, n in (("solar", N_SOLAR), ("dc", N_DC)):
        k = 0
        for _, r in s.sort_values("rank_" + track).iterrows():
            if r["site_id"] in used_sites or r["block_id"] in used_blocks or r["nearest_sub_id"] in used_subs:
                continue
            r = r.copy(); r["memo_track"] = track
            rows.append(r); used_sites.add(r["site_id"]); used_blocks.add(r["block_id"]); used_subs.add(r["nearest_sub_id"])
            k += 1
            if k == n:
                break
    return pd.DataFrame(rows)


OFFLINE_CHECKS = [
    "Archive the source snapshots used here (HIFLD, OSM, NSRDB, BLM, FEMA, USFWS) with retrieval date, original vintage and license/attribution; trace each scored field back to a raw record.",
    "GIS/title check: legal parcel boundary, surface vs title ownership (SMA is not title), state trust status, withdrawals, mining claims, grazing permits and existing ROWs, and the field-office land-use designation (incl. DRECP DFA / variance / avoidance where relevant).",
    "Recompute usable acres from full-resolution geometry after setbacks, washes and exclusion holes; confirm enough contiguous usable land for the target MW (about 5,000-7,000 acres for 1 GW), not only the 600-acre screen.",
    "Environmental and flood: critical habitat and occupied species habitat (surveys), wetlands and waters incl. small washes, ACECs, cultural and tribal consultation, FEMA coverage status (unmapped is not flood-free), local flood studies, military airspace.",
    "Grid: confirm the exact bus or line voltage, operating status, owner and utility territory against utility one-line diagrams; ask the utility in writing for capacity, upgrade cost, study cluster, site-control rules and export limits; route the gen-tie.",
    "For co-located data center load: submit both a generation and a large-load service request; get carrier fiber letters with diverse routes and lateral pricing, and confirm water supply/rights and cooling design.",
    "Costs and schedule: land or lease quotes, BLM bond and rent (3.9% of gross proceeds capacity fee on BLM solar), interconnection upgrades and gen-tie, roads, tax scenarios with and without credits, NEPA/permitting timeline; current 43 CFR 2800 and litigation status with counsel.",
    "Re-run the rank under other weights and decay lengths and with missing data treated as unknown; check the site still ranks well before spending on surveys.",
]


def context(site_geom, layers):
    subs, cases, plants, closed = layers
    out = {}
    d = subs.distance(site_geom) / 1000
    near = subs.assign(d=d)[d <= 30].sort_values("d").head(4)
    out["subs"] = near
    d = cases.distance(site_geom) / 1000
    out["cases"] = cases.assign(d=d)[d <= 10].sort_values("d")
    d = closed.distance(site_geom) / 1000
    out["closed"] = closed.assign(d=d)[d <= 5]
    d = plants.distance(site_geom) / 1000
    out["plants"] = plants.assign(d=d)[d <= 15].sort_values("d")
    return out


def memo(r, ctx, qc):
    sid = r["site_id"]
    track = "solar ranking" if r["memo_track"] == "solar" else "data center ranking"
    lines = [f"# {sid}: {r['county']} County, {r['state']} (solar rank {int(r['rank_solar'])}, data center rank {int(r['rank_dc'])})", ""]
    lines += [f"Selected from the {track}. Solar score {r['score_total_solar']:.1f} / 100 and solar + data center score "
              f"{r['score_total_dc']:.1f} / 100 (factors: grid {r['score_grid']:.0f}, land {r['score_land']:.0f}, sun {r['score_sun']:.0f}, "
              f"permitting {r['score_permit']:.0f}, data center {r['score_dc']:.0f}). Screening result from public data, not engineering.", ""]
    lines += ["## Location",
              f"- Centre point {r['centroid_lat']:.4f}, {r['centroid_lon']:.4f} "
              f"([map](https://www.openstreetmap.org/?mlat={r['centroid_lat']:.5f}&mlon={r['centroid_lon']:.5f}#map=12/{r['centroid_lat']:.5f}/{r['centroid_lon']:.5f})).",
              f"- {r['acres']:,.0f} contiguous acres after hard exclusions; at 5 to 7 acres/MW that is about "
              f"{r['acres'] / 7:,.0f} to {r['acres'] / 5:,.0f} MW of solar.",
              f"- Mean slope {r['mean_slope']:.1f}%; GHI {r['ghi']:.2f} kWh/m2/day (NSRDB 1998-2016 mean).", ""]
    why = []
    if r["blm_solar_available"]:
        why.append(f"BLM land in {r['blm_status']}" + (f", inside the {r['sez_name']} Solar Energy Zone" if r["sez_name"] else ""))
    elif r["owner_category"] in ("Private", "State"):
        why.append(f"{r['owner_category']} land: no BLM right-of-way process or federal NEPA needed unless there is a federal nexus")
    if r["dist_sub_km"] <= 5:
        why.append(f"{fnum(r['dist_sub_km'])} km from {r['nearest_sub_name']} ({fnum(r['nearest_sub_kv'], 0)} kV)")
    if r["score_sun"] >= 85:
        why.append(f"strong sun (GHI {r['ghi']:.2f})")
    if r["score_permit"] >= 90:
        why.append("few soft constraints in the public layers")
    if r["score_dc"] >= 70:
        why.append("good data center inputs (fiber proxy, road, water stress, 230 kV+ substation)")
    lines += ["## Why it ranks well"] + [f"- {w}." for w in why] + [""]
    lines += ["## Grid path",
              f"- Nearest 115 kV+ substation: **{r['nearest_sub_name']}** ({fnum(r['nearest_sub_kv'], 0)} kV, owner {r['nearest_sub_owner'] or 'unknown'}), "
              f"{fnum(r['dist_sub_km'], 2)} km from the site edge (straight line).",
              f"- Nearest 230 kV+ substation: {r['nearest_sub230_name']} ({fnum(r['nearest_sub230_kv'], 0)} kV), {fnum(r['dist_sub230_km'], 1)} km.",
              f"- Nearest 115 kV+ line: {fnum(r['nearest_line_kv'], 0)} kV at {fnum(r['dist_line_km'], 2)} km; nearest 230 kV+ line {fnum(r['nearest_line230_kv'], 0)} kV at {fnum(r['dist_line230_km'], 1)} km.",
              f"- Active queue in {r['county']} County: {r['queued_mw_county']:,.0f} MW in total "
              f"({qc.get('n', 'unknown')} projects; solar {r['queued_mw_county_solar']:,.0f} MW, storage {r['queued_mw_county_storage']:,.0f} MW; "
              f"queue confidence {r['queue_confidence']}). Queue MW is a county-level congestion signal, not a capacity figure."]
    if len(ctx["subs"]):
        lines.append("- Other 115 kV+ substations within 30 km: " + "; ".join(
            f"{x['name']} ({fnum(x['max_kv'], 0)} kV, {x['d']:.1f} km, owner {x['owner']})" for _, x in ctx["subs"].iterrows()) + ".")
    lines.append("")
    risks = [FLAG_TEXT.get(f, f) for f in (r["constraints_soft"] or [])]
    if r["owner_category"] == "Private":
        risks.append("ownership is from the BLM Surface Management Agency layer, which does not show private parcel lines; the block may span several owners")
    ws = r["water_stress"]
    if ws is None or not np.isfinite(ws):
        risks.append("no Aqueduct water stress value")
    elif ws >= 4:
        risks.append(f"water stress {r['water_stress']:.1f}/5 ({r['water_stress_label']}), a constraint for evaporative data center cooling")
    if len(ctx["cases"]):
        risks.append("active BLM solar ROW cases within 10 km: " + "; ".join(
            f"{x['case_id']} {x['project_name'] or ''} ({x['status']}, {x['d']:.1f} km)".replace("  ", " ") for _, x in ctx["cases"].head(5).iterrows()))
    if len(ctx["closed"]):
        risks.append(f"{len(ctx['closed'])} closed BLM solar case(s) within 5 km; ask the field office why they closed")
    risks.append("FEMA flood maps and critical habitat layers are incomplete in rural areas; species surveys (e.g. desert tortoise where present) and a flood study are still needed")
    lines += ["## Risks"] + [f"- {x[0].upper() + x[1:]}." for x in risks] + [""]
    own = f"{r['owner_category']}"
    if r["owner_category"] == "BLM":
        own += f"; {r['blm_status']}; {r['blm_avail_pct']:.0f}% of the site lies in BLM solar-available / DFA land"
        own += f"; nearest MLRS solar case is administered by {r['blm_fo_hint']} ({r['blm_fo_hint_km']:.1f} km away; confirm jurisdiction)"
    if r["row_cases_overlap"]:
        own += f"; overlaps active MLRS case(s) {r['row_cases_overlap']}"
    lines += ["## BLM / ownership status", f"- {own}."]
    if len(ctx["plants"]):
        lines.append("- Existing EIA-860 plants within 15 km: " + "; ".join(
            f"{x['plant']} ({x['tech']}, {fnum(x['mw'], 0)} MW, {x['status']}, {x['d']:.1f} km)" for _, x in ctx["plants"].head(5).iterrows()) + ".")
    prov = [f"Nearest substation record: source {r['sub_source']}, voltage source {r['sub_kv_source']}; "
            + ("**provisional** (OSM-only, voltage from OSM or inferred from nearby lines, or unnamed). Grid score was multiplied by 0.85; "
               "confirm the substation exists, its voltage and owner before anything else"
               if r["sub_provisional"] else "HIFLD record with HIFLD voltage (not provisional), but HIFLD substations were last edited at the source in February 2021")]
    mr = r["queue_poi_match_rate"]
    prov.append(f"Queue confidence {r['queue_confidence']}: " + (
        "the county shows 0 active queue MW, which is treated as unknown (neutral score), not as an empty queue"
        if r["queued_mw_county"] <= 0 else
        f"{fnum(mr * 100 if mr is not None and np.isfinite(mr) else None, 0)}% of the county's {r['queue_n_active_county']} active queue projects "
        "are matched to a named substation; queue MW is not tied to this substation"))
    prov.append(f"Fiber distance uses a proxy layer ({r['fiber_basis']}); 99% of that layer is not confirmed fiber, so the data center score is weak evidence")
    lines += ["", "## Provisional data flags"] + [f"- {x}." for x in prov]
    lines += ["", "## Offline checks before relying on this site (from the methodology review checklist)"]
    lines += [f"- [ ] {x}" for x in OFFLINE_CHECKS]
    lines += ["", "## Next steps", f"- {r['next_step']}",
              "- Confirm hosting capacity and the next cluster window on the utility OASIS; file once site control is in hand.",
              "- Order a desktop title / environmental screen (species, cultural, flood) before spending on surveys.", "",
              f"Site polygon: `data/processed/sites/candidate_sites.geojson` (site_id {sid}). Method: `data/processed/sites/METHOD.md`."]
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    LOG.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        handlers=[logging.FileHandler(LOG), logging.StreamHandler(sys.stdout)])
    OUT.mkdir(parents=True, exist_ok=True)
    src = P / "sites/candidate_sites.geojson"
    if (OUT / "README.md").exists() and (OUT / "README.md").stat().st_mtime > src.stat().st_mtime and not a.force:
        log.info("memos: up to date; skipping (use --force)")
        return
    t = time.time()
    s = gpd.read_file(src).to_crs(CRS)
    s["constraints_soft"] = s["constraints_soft"].map(lambda v: list(v) if isinstance(v, (list, np.ndarray)) else
                                                      ([x for x in str(v).split("; ") if x] if v else []))
    subs = gpd.read_file(P / "grid/substations.gpkg").to_crs(CRS)
    # same usable-POI set as screen.py: drop the substations its POI filter removed
    excluded = set(pd.read_csv(P / "sites/excluded_pois.csv", usecols=["id"])["id"].astype(str))
    subs = subs[(subs["max_kv"].fillna(0) >= 115) & ~subs["id"].astype(str).isin(excluded)]
    cases = gpd.read_file(P / "infra/blm_solar_row_cases.geojson").to_crs(CRS)
    closed = gpd.read_file(P / "infra/blm_solar_row_cases_closed.geojson").to_crs(CRS)
    plants = gpd.read_file(P / "infra/power_plants.geojson").to_crs(CRS)
    plants = plants[plants["status"].isin(["operating", "proposed"])]
    q = pd.read_csv(P / "grid/queue_by_county.csv", dtype={"county_fips": str}).set_index("county_fips")
    top = pick_top(s)
    for old in OUT.glob("*.md"):
        old.unlink()
    idx = []
    for i, (_, r) in enumerate(top.iterrows(), 1):
        ctx = context(r.geometry, (subs, cases, plants, closed))
        fips = r["county_fips"]
        qc = {"n": int(q.loc[fips, "n_projects"])} if fips in q.index else {}
        name = f"{i:02d}_{r['site_id']}.md"
        (OUT / name).write_text(memo(r, ctx, qc))
        idx.append(f"| {i} | [{r['site_id']}]({name}) | {r['memo_track']} | {int(r['rank_solar'])} | {int(r['rank_dc'])} | {r['state']} | {r['county']} | {r['acres']:,.0f} | "
                   f"{r['owner_category']}{' (BLM solar-available)' if r['blm_solar_available'] else ''} | "
                   f"{r['nearest_sub_name']} {fnum(r['nearest_sub_kv'], 0)} kV, {r['dist_sub_km']:.1f} km | "
                   f"{'yes' if r['sub_provisional'] else 'no'} | {r['score_total_solar']:.1f} | {r['score_total_dc']:.1f} |")
    best = s.sort_values("rank").groupby("state").head(1).sort_values("rank")
    readme = ["# Top site memos", "",
              f"Generated {time.strftime('%Y-%m-%d')} by `pipeline/memos.py` from `data/processed/sites/candidate_sites.geojson` "
              f"({len(s):,} ranked sites). One memo per site below.", "",
              f"Memos 1-{N_SOLAR} are the top sites by the solar ranking; the rest are the top sites by the solar + data center "
              "ranking that were not already covered. Each list takes at most one site per contiguous ownership block and per "
              "nearest substation, across both lists, so the memos cover different places. Ranks are among all ranked sites; the full lists are in "
              "`deliverables/Southwest_Solar_Sites.xlsx` (Top 50 Solar, Top 50 Data Center). 'Provisional' means the nearest "
              "substation record is OSM-only or its voltage is inferred; every memo lists its provisional flags and offline checks.", "",
              "| # | Site | Picked from | Solar rank | DC rank | State | County | Acres | Owner | Nearest 115 kV+ substation | Provisional | Solar score | DC score |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|"] + idx + ["",
              "## Best site in each state (solar ranking)", "", "| State | Site | Solar rank | DC rank | County | Owner | Solar score |", "|---|---|---|---|---|---|---|"]
    readme += [f"| {r['state']} | {r['site_id']} | {int(r['rank_solar'])} | {int(r['rank_dc'])} | {r['county']} | {r['owner_category']} | {r['score_total_solar']:.1f} |"
               for _, r in best.iterrows()]
    readme += ["", "Limits: public data shows where lines and substations are, not spare capacity; ownership is surface "
               "managing agency, not title; all distances are straight-line. See `data/processed/sites/METHOD.md`."]
    (OUT / "README.md").write_text("\n".join(readme) + "\n")
    log.info("memos: wrote %d memos + README (%.0fs)", len(top), time.time() - t)


if __name__ == "__main__":
    main()

# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "geopandas==1.0.1",
#   "shapely==2.0.6",
#   "pyogrio==0.10.0",
#   "pandas==2.2.3",
#   "numpy==2.1.3",
#   "openpyxl==3.1.5",
# ]
# ///
"""Process raw grid data (from fetch_grid.py) into the data contracts in TEAM/SPEC.md.

Outputs in data/processed/grid/:
  transmission_lines.geojson (+ .gpkg full resolution)
  substations.geojson (+ .gpkg)
  queue_projects.csv, queue_by_county.csv, queue_state_check.csv
  MANIFEST.json

Usage: uv run --script pipeline/process_grid.py [--force]
"""
from __future__ import annotations

import json
import logging
import re
import sys
import time
import unicodedata
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "grid"
OUT = ROOT / "data" / "processed" / "grid"
LOG = ROOT / "logs" / "grid.log"
FORCE = "--force" in sys.argv
STATES = {"06": "CA", "04": "AZ", "32": "NV", "35": "NM", "49": "UT"}
ALBERS = 5070
SNAP_M = 200          # line-to-substation snap distance
OSM_MATCH_M = 1500    # an OSM substation within this distance of a HIFLD substation counts as already present
SIMPLIFY_DEG = 0.0003  # ~30 m; topology-preserving simplification for app-facing GeoJSON

LOG.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(level=logging.INFO, format="%(asctime)s process_grid %(levelname)s %(message)s",
                    handlers=[logging.FileHandler(LOG), logging.StreamHandler()])
log = logging.getLogger()
TODAY = time.strftime("%Y-%m-%d")


# ---------------------------------------------------------------- helpers
def read_pages(d: Path) -> gpd.GeoDataFrame:
    parts = [gpd.read_file(p) for p in sorted(d.glob("page_*.geojson"))]
    g = pd.concat(parts, ignore_index=True)
    return gpd.GeoDataFrame(g, geometry="geometry", crs=4326)


def meta(d: Path) -> dict:
    return json.loads((d / "_complete.json").read_text())


def kv(v):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    return v if v > 0 else None


def volt_class(v) -> str:
    if v is None or pd.isna(v):
        return "unknown"
    if v < 115:
        return "<115"
    if v <= 161:
        return "115-161"
    if v < 300:
        return "230"
    if v < 500:
        return "345"
    return "500+"


def norm_county(s) -> str:
    if s is None or (isinstance(s, float) and np.isnan(s)):
        return ""
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    s = re.sub(r"\b(county|city and county of|city of)\b", "", s, flags=re.I)
    s = s.split(",")[0].split("/")[0].split(";")[0]
    return re.sub(r"[^a-z]", "", s.lower())


def norm_subname(s) -> str:
    """Normalise a substation / POI name for exact matching."""
    if s is None or (isinstance(s, float) and np.isnan(s)):
        return ""
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().upper()
    s = re.sub(r"\(.*?\)", " ", s)
    s = re.sub(r"\b\d+(\.\d+)?\s*-?\s*KV\b", " ", s)
    s = re.sub(r"\b(SUBSTATION|SUBSTA|SUB|SWITCHYARD|SWITCHING STATION|SWITCHING|STATION|SS|SWYD|BUS|KV|"
               r"PROPOSED|NEW|EXISTING|THE)\b", " ", s)
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def write_geo(g: gpd.GeoDataFrame, stem: str, simplify: bool) -> tuple[Path, Path]:
    gpkg = OUT / f"{stem}.gpkg"
    gj = OUT / f"{stem}.geojson"
    for p in (gpkg, gj):
        if p.exists():
            p.unlink()
    g.to_file(gpkg, layer=stem, driver="GPKG", engine="pyogrio")
    app = g.copy()
    if simplify:
        app["geometry"] = app.geometry.simplify(SIMPLIFY_DEG, preserve_topology=True)
    app.to_file(gj, driver="GeoJSON", engine="pyogrio", layer_options={"COORDINATE_PRECISION": 5, "RFC7946": "YES"})
    log.info("wrote %s (%.1f MB) and %s", gj.relative_to(ROOT), gj.stat().st_size / 1e6, gpkg.relative_to(ROOT))
    return gj, gpkg


# ---------------------------------------------------------------- boundaries
def boundaries() -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    st = gpd.read_file(f"zip://{RAW / 'tiger' / 'cb_2024_us_state_500k.zip'}")
    st = st[st.STATEFP.isin(STATES)][["STUSPS", "geometry"]].rename(columns={"STUSPS": "state"}).to_crs(4326)
    co = gpd.read_file(f"zip://{RAW / 'tiger' / 'cb_2024_us_county_500k.zip'}")
    co = co[co.STATEFP.isin(STATES)].copy()
    co["state"] = co.STATEFP.map(STATES)
    co = co[["GEOID", "NAME", "state", "geometry"]].rename(columns={"NAME": "county", "GEOID": "county_fips"}).to_crs(4326)
    return st, co


# ---------------------------------------------------------------- lines
def process_lines(states: gpd.GeoDataFrame) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    raw = read_pages(RAW / "hifld_lines").drop_duplicates("ID")
    log.info("HIFLD lines in bbox: %d", len(raw))
    raw["voltage_kv"] = raw.VOLTAGE.map(kv)
    raw["hifld_id"] = raw.ID.astype(str)
    keep = raw[["hifld_id", "voltage_kv", "OWNER", "STATUS", "TYPE", "SUB_1", "SUB_2", "INFERRED", "SOURCE", "geometry"]]
    # split each line at state boundaries so every piece carries exactly one state
    pieces = gpd.overlay(keep, states, how="intersection", keep_geom_type=True)
    pieces = pieces[~pieces.geometry.is_empty]
    pieces["id"] = "hifld-" + pieces.hifld_id + "-" + pieces.state
    pieces = pieces.dissolve(by="id", as_index=False, aggfunc="first")
    pieces["volt_class"] = pieces.voltage_kv.map(volt_class)
    pieces = pieces.rename(columns={"OWNER": "owner", "STATUS": "status", "TYPE": "line_type", "SUB_1": "sub_1",
                                    "SUB_2": "sub_2", "INFERRED": "voltage_inferred", "SOURCE": "hifld_source"})
    pieces["length_km"] = (pieces.to_crs(ALBERS).length / 1000).round(2)
    cols = ["id", "hifld_id", "voltage_kv", "volt_class", "owner", "status", "state", "line_type", "sub_1", "sub_2",
            "voltage_inferred", "hifld_source", "length_km", "geometry"]
    pieces = gpd.GeoDataFrame(pieces[cols], geometry="geometry", crs=4326)
    log.info("line pieces in 5 states: %d; by class %s", len(pieces), pieces.volt_class.value_counts().to_dict())
    return pieces, raw


# ---------------------------------------------------------------- substations
def snap_lines(subs_alb: gpd.GeoDataFrame, lines_alb: gpd.GeoDataFrame) -> pd.DataFrame:
    buf = subs_alb[["sid", "geometry"]].copy()
    buf["geometry"] = buf.buffer(SNAP_M)
    j = gpd.sjoin(buf, lines_alb[["hifld_id", "voltage_kv", "OWNER", "geometry"]], predicate="intersects")
    agg = j.groupby("sid").agg(lines_snapped=("hifld_id", "nunique"), line_max_kv=("voltage_kv", "max"),
                               line_min_kv=("voltage_kv", "min"),
                               line_owner=("OWNER", lambda s: s[~s.astype(str).str.upper().isin(["NOT AVAILABLE", "NAN", "NONE", ""])].mode().iloc[0]
                                           if (~s.astype(str).str.upper().isin(["NOT AVAILABLE", "NAN", "NONE", ""])).any() else None))
    return agg


def osm_substations() -> gpd.GeoDataFrame:
    rows = []
    for p in sorted((RAW / "osm").glob("osm_subs_*.json")):
        for e in json.loads(p.read_text()).get("elements", []):
            t = e.get("tags", {})
            lat = e.get("lat", e.get("center", {}).get("lat"))
            lon = e.get("lon", e.get("center", {}).get("lon"))
            if lat is None:
                continue
            vs = []
            for v in re.split(r"[;,]", t.get("voltage", "")):
                try:
                    vs.append(float(v.strip()) / 1000)
                except ValueError:
                    pass
            vs = [v for v in vs if v > 0]
            if not vs:
                continue
            rows.append({"osm_id": f"{e['type']}/{e['id']}", "name": t.get("name"), "owner": t.get("operator"),
                         "osm_kind": t.get("substation"), "max_kv": max(vs), "min_kv": min(vs),
                         "lon": lon, "lat": lat})
    g = pd.DataFrame(rows).drop_duplicates("osm_id")
    return gpd.GeoDataFrame(g, geometry=gpd.points_from_xy(g.lon, g.lat), crs=4326)


def process_subs(states, counties, lines_raw) -> tuple[gpd.GeoDataFrame, dict]:
    raw = read_pages(RAW / "hifld_substations").drop_duplicates("ID")
    log.info("HIFLD substations in bbox: %d", len(raw))
    s = gpd.sjoin(raw, states, predicate="within").drop(columns="index_right")
    s = gpd.sjoin(s, counties[["county", "county_fips", "geometry"]], predicate="within", how="left").drop(columns="index_right")
    s = s.drop_duplicates("ID")
    s["sid"] = "hifld-" + s.ID.astype(str)
    s["max_kv"] = s.MAX_VOLT.map(kv)
    s["min_kv"] = s.MIN_VOLT.map(kv)
    s["lines_hifld"] = pd.to_numeric(s.LINES, errors="coerce")
    out = gpd.GeoDataFrame({
        "id": s.sid, "name": s.NAME, "max_kv": s.max_kv, "min_kv": s.min_kv, "owner": None,
        "status": s.STATUS, "lines_hifld": s.lines_hifld, "state": s.state, "county": s.county,
        "county_fips": s.county_fips, "sub_type": s.TYPE, "source": "hifld", "osm_id": None,
        "kv_source": np.where(s.max_kv.notna(), "hifld", None), "geometry": s.geometry}, crs=4326)

    # OSM gap fill: >=115 kV substations with no HIFLD substation within OSM_MATCH_M
    osm = osm_substations()
    osm = gpd.sjoin(osm, states, predicate="within").drop(columns="index_right")
    osm = gpd.sjoin(osm, counties[["county", "county_fips", "geometry"]], predicate="within", how="left").drop(columns="index_right")
    osm = osm.drop_duplicates("osm_id")
    osm_alb, out_alb = osm.to_crs(ALBERS), out.to_crs(ALBERS)
    near = gpd.sjoin_nearest(osm_alb[["osm_id", "geometry"]], out_alb[["id", "max_kv", "geometry"]],
                             max_distance=OSM_MATCH_M, distance_col="d")
    matched = set(near.osm_id)
    add = osm[~osm.osm_id.isin(matched)].copy()
    # collapse OSM duplicates (node + way for the same site) within 300 m
    add_alb = add.to_crs(ALBERS)
    add_alb["cell"] = (add_alb.geometry.x // 300).astype(int).astype(str) + "_" + (add_alb.geometry.y // 300).astype(int).astype(str)
    add = add.loc[add_alb.sort_values("max_kv", ascending=False).drop_duplicates("cell").index]
    osm_stats = {"osm_substations_ge115kv": int(len(osm)), "osm_matched_to_hifld_within_m": OSM_MATCH_M,
                 "osm_matched": int(len(matched)), "osm_added": int(len(add)),
                 "osm_added_by_state": add.state.value_counts().to_dict()}
    # where matched HIFLD record has no voltage, take the OSM voltage
    nn = near.sort_values("d").drop_duplicates("id").merge(
        osm[["osm_id", "max_kv", "min_kv"]].rename(columns={"max_kv": "max_kv_osm", "min_kv": "min_kv_osm"}), on="osm_id")
    fill = out.id.isin(nn.loc[nn.max_kv.isna(), "id"])
    m = nn.set_index("id")
    out.loc[fill, "max_kv"] = out.loc[fill, "id"].map(m.max_kv_osm)
    out.loc[fill, "min_kv"] = out.loc[fill, "id"].map(m.min_kv_osm)
    out.loc[fill, "kv_source"] = "osm_match"
    osm_stats["hifld_voltage_filled_from_osm"] = int(fill.sum())
    add_g = gpd.GeoDataFrame({
        "id": "osm-" + add.osm_id.str.replace("/", "-"), "name": add.name, "max_kv": add.max_kv, "min_kv": add.min_kv,
        "owner": add.owner, "status": "IN SERVICE (OSM)", "lines_hifld": np.nan, "state": add.state, "county": add.county,
        "county_fips": add.county_fips, "sub_type": add.osm_kind.fillna("substation").str.upper(), "source": "osm",
        "osm_id": add.osm_id, "kv_source": "osm", "geometry": add.geometry}, crs=4326)
    out = pd.concat([out, add_g], ignore_index=True)
    out = gpd.GeoDataFrame(out, geometry="geometry", crs=4326)

    # connected lines by 200 m snap (HIFLD LINES is often 0 for unnamed records), voltage/owner from lines
    lines_alb = lines_raw.to_crs(ALBERS)
    sub_alb = out.rename(columns={"id": "sid"}).to_crs(ALBERS)
    agg = snap_lines(sub_alb, lines_alb)
    out = out.merge(agg, left_on="id", right_index=True, how="left")
    out["lines_snapped"] = out.lines_snapped.fillna(0).astype(int)
    out["lines"] = np.where(out.lines_hifld.fillna(0) > 0, out.lines_hifld.fillna(0), out.lines_snapped).astype(int)
    out["lines_source"] = np.where(out.lines_hifld.fillna(0) > 0, "hifld", "snap_200m")
    inf = out.max_kv.isna() & out.line_max_kv.notna()
    out.loc[inf, "max_kv"] = out.loc[inf, "line_max_kv"]
    out.loc[inf, "min_kv"] = out.loc[inf, "line_min_kv"]
    out.loc[inf, "kv_source"] = "inferred_from_lines"
    out["owner_source"] = np.where(out.owner.notna(), "osm_operator", np.where(out.line_owner.notna(), "connected_lines", None))
    out["owner"] = out.owner.fillna(out.line_owner)
    out["volt_class"] = out.max_kv.map(volt_class)
    out = out.drop(columns=["line_owner"])
    osm_stats["hifld_voltage_inferred_from_lines"] = int(inf.sum())
    return gpd.GeoDataFrame(out, geometry="geometry", crs=4326), osm_stats


# ---------------------------------------------------------------- queues
def qtype(row) -> str:
    t = str(row.type_clean)
    if "+" in t:
        return "hybrid"
    return {"Solar": "solar", "Battery": "storage", "Other Storage": "storage", "Wind": "wind",
            "Offshore Wind": "wind", "Gas": "gas"}.get(t, "other")


STORAGE = {"Battery", "Other Storage", "Pumped Storage"}


def component_mw(row, kinds: set[str]) -> float:
    tot = 0.0
    for i in (1, 2, 3):
        t, mw = row[f"type_{i}"], row[f"mw_{i}"]
        if isinstance(t, str) and t in kinds and pd.notna(mw):
            tot += float(mw)
    return tot


def process_queue(counties: gpd.GeoDataFrame, subs: gpd.GeoDataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    f = RAW / "queued_up" / "lbnl_ix_queue_data_file_thru2025.xlsx"
    df = pd.read_excel(f, "03. Complete Queue Data", header=1)
    df = df[df.state.isin(STATES.values())].copy()
    log.info("Queued Up rows in 5 states: %d", len(df))
    # CAISO public queue (current report): adds project name, current status and POI where LBNL lacks it
    cq = []
    for sh, st in [("Grid GenerationQueue", "ACTIVE"), ("Completed Generation Projects", "COMPLETED"),
                   ("Withdrawn Generation Projects", "WITHDRAWN")]:
        c = pd.read_excel(RAW / "caiso" / "publicqueuereport.xlsx", sh, header=3)
        c = c[c["Queue Position"].notna()]
        c["caiso_sheet"] = st
        cq.append(c)
    cq = pd.concat(cq, ignore_index=True)
    cq["qkey"] = cq["Queue Position"].astype(str).str.strip().str.upper()
    cq = cq.drop_duplicates("qkey")
    cq = cq.rename(columns={"Station or Transmission Line": "caiso_poi", "County": "caiso_county", "State": "caiso_state",
                            "Project Name": "caiso_project_name", "Project Name - Confidential": "caiso_project_name2",
                            "Utility": "caiso_pto"})
    cq["caiso_project_name"] = cq.caiso_project_name.fillna(cq.get("caiso_project_name2"))

    df["qkey"] = df.q_id.astype(str).str.strip().str.upper()
    is_caiso = df.entity.eq("CAISO")
    df = df.merge(cq[["qkey", "caiso_poi", "caiso_county", "caiso_project_name", "caiso_pto", "caiso_sheet"]],
                  on="qkey", how="left")
    df.loc[~is_caiso.values, ["caiso_poi", "caiso_county", "caiso_project_name", "caiso_pto", "caiso_sheet"]] = None
    df["poi_from_caiso"] = df.poi_name.isna() & df.caiso_poi.notna()
    df["poi_name"] = df.poi_name.fillna(df.caiso_poi)
    df["county_from_caiso"] = df.county.isna() & df.caiso_county.notna()
    df["county"] = df.county.fillna(df.caiso_county)

    # county names standardised to TIGER 2024 (via FIPS first, then accent/case-insensitive name match)
    cmap = counties.drop(columns="geometry").copy()
    cmap["k"] = cmap.state + "|" + cmap.county.map(norm_county)
    by_fips = cmap.set_index("county_fips").county
    by_name = cmap.drop_duplicates("k").set_index("k")
    fips = pd.to_numeric(df.fips_code, errors="coerce").astype("Int64").astype(str).str.zfill(5)
    nm = (df.state + "|" + df.county.map(norm_county)).map(by_name.county)
    df["county_std"] = nm.fillna(fips.map(by_fips))
    df["county_fips"] = (df.state + "|" + df.county_std.map(norm_county)).map(by_name.county_fips)

    df["mw"] = df[["mw_1", "mw_2", "mw_3"]].sum(axis=1, min_count=1)
    df["mw_solar"] = df.apply(component_mw, axis=1, kinds={"Solar"})
    df["mw_storage"] = df.apply(component_mw, axis=1, kinds=STORAGE)
    df["type"] = df.apply(qtype, axis=1)
    # Queued Up's own "active" totals exclude suspended requests, so suspended stays a separate value
    df["status"] = df.q_status.map({"active": "active", "withdrawn": "withdrawn", "operational": "operational",
                                    "suspended": "suspended"}).fillna("unknown")
    df["queue_id"] = df.entity.astype(str) + ":" + df.q_id.astype(str)
    dup = df.groupby("queue_id").cumcount()
    df.loc[dup > 0, "queue_id"] += "#" + (dup[dup > 0] + 1).astype(str)  # q_id repeats (e.g. 'not assigned')
    df["q_year"] = pd.to_numeric(df.q_year, errors="coerce").astype("Int64")
    df["queue_date"] = pd.to_datetime(df.q_date, errors="coerce").dt.strftime("%Y-%m-%d")
    df["source"] = "LBNL Queued Up 2026 (data thru 2025)"
    df.loc[df.poi_from_caiso | df.county_from_caiso, "source"] += " + CAISO public queue report"

    # best-effort POI -> substation match on normalised names within the same state
    sn = subs[["id", "name", "state", "max_kv"]].copy()
    sn["k"] = sn.state + "|" + sn.name.map(norm_subname)
    sn = sn[~sn.name.astype(str).str.upper().str.startswith(("UNKNOWN", "TAP"))]
    sn = sn.sort_values("max_kv", ascending=False).drop_duplicates("k").set_index("k")
    poi_norm = df.poi_name.map(norm_subname)
    is_line = df.poi_name.astype(str).str.contains(r"\bline\b|-|\btap\b", case=False, regex=True)
    pk = df.state + "|" + poi_norm
    df["poi_sub_id"] = np.where(~is_line & poi_norm.ne(""), pk.map(sn.id), None)
    df["poi_sub_id"] = df.poi_sub_id.where(pd.notna(df.poi_sub_id), None)

    qp = df.rename(columns={"status": "status"})[[
        "queue_id", "entity", "poi_name", "state", "county_std", "type", "mw", "status", "queue_date", "source",
        "q_status", "type_clean", "mw_solar", "mw_storage", "county_fips", "project_name", "caiso_project_name",
        "utility", "service", "IA_phase_clean", "prop_date", "q_year", "poi_sub_id"]].rename(
        columns={"county_std": "county", "q_status": "status_raw", "IA_phase_clean": "study_phase"})
    qp["prop_date"] = pd.to_datetime(qp.prop_date, errors="coerce").dt.strftime("%Y-%m-%d")
    qp["project_name"] = qp.project_name.fillna(qp.caiso_project_name)
    qp = qp.drop(columns="caiso_project_name")

    act = qp[qp.status.eq("active")]
    by_c = act.groupby(["state", "county"], dropna=False).agg(
        active_mw_total=("mw", "sum"), active_mw_solar=("mw_solar", "sum"), active_mw_storage=("mw_storage", "sum"),
        n_projects=("queue_id", "count"), county_fips=("county_fips", "first")).reset_index()
    by_c["county"] = by_c.county.fillna("(county not reported)")
    by_c = by_c.round(1).sort_values(["state", "active_mw_total"], ascending=[True, False])

    # comparison with the Queued Up 2026 workbook's own state totals (sheet "11. Active Cap. Maps")
    m = pd.read_excel(f, "11. Active Cap. Maps", header=None)
    hdr = m.index[m.apply(lambda r: r.astype(str).str.contains("State").any(), axis=1)][0]
    stcol = [i for i, v in enumerate(m.iloc[hdr]) if str(v) == "State"][0]
    ref = m.iloc[hdr + 1:, [stcol, stcol + 1, stcol + 2]].dropna()
    ref.columns = ["state", "rtype", "gw"]
    ref = ref[ref.state.isin(STATES.values())]
    ref["gw"] = pd.to_numeric(ref.gw, errors="coerce")
    refp = ref.pivot_table(index="state", columns="rtype", values="gw", aggfunc="sum")
    ours = pd.DataFrame({
        "ours_active_gw_all": act.groupby("state").mw.sum() / 1000,
        "ours_active_gw_solar": act.groupby("state").mw_solar.sum() / 1000,
        "ours_active_gw_storage": act.groupby("state").mw_storage.sum() / 1000,
        "ours_n_active": act.groupby("state").size()})
    chk = ours.join(pd.DataFrame({
        "lbnl_report_gw_5types": refp.sum(axis=1), "lbnl_report_gw_solar": refp.get("Solar"),
        "lbnl_report_gw_storage": refp.get("Storage")}))
    chk["solar_ratio"] = chk.ours_active_gw_solar / chk.lbnl_report_gw_solar
    chk["storage_ratio"] = chk.ours_active_gw_storage / chk.lbnl_report_gw_storage
    chk = chk.round(3).reset_index().rename(columns={"index": "state"})
    return qp, by_c, chk


def sub_queue(subs: gpd.GeoDataFrame, qp: pd.DataFrame) -> gpd.GeoDataFrame:
    a = qp[qp.status.eq("active") & qp.poi_sub_id.notna()]
    g = a.groupby("poi_sub_id").agg(queue_active_mw=("mw", "sum"), queue_n_active=("queue_id", "count"))
    subs = subs.merge(g, left_on="id", right_index=True, how="left")
    subs["queue_active_mw"] = subs.queue_active_mw.fillna(0).round(1)
    subs["queue_n_active"] = subs.queue_n_active.fillna(0).astype(int)
    return subs


# ---------------------------------------------------------------- main
def main() -> None:
    targets = [OUT / n for n in ("transmission_lines.geojson", "substations.geojson", "queue_projects.csv",
                                  "queue_by_county.csv", "MANIFEST.json")]
    if all(p.exists() and p.stat().st_size > 0 for p in targets) and not FORCE:
        log.info("process_grid: outputs exist, skip (use --force)")
        return
    OUT.mkdir(parents=True, exist_ok=True)
    log.info("=== process_grid start")
    states, counties = boundaries()
    lines, lines_raw = process_lines(states)
    subs, osm_stats = process_subs(states, counties, lines_raw)
    qp, by_c, chk = process_queue(counties, subs)
    subs = sub_queue(subs, qp)
    sub_cols = ["id", "name", "max_kv", "min_kv", "owner", "status", "lines", "state", "county", "county_fips",
                "volt_class", "sub_type", "source", "osm_id", "kv_source", "lines_source", "lines_hifld",
                "lines_snapped", "owner_source", "queue_active_mw", "queue_n_active", "geometry"]
    subs = gpd.GeoDataFrame(subs[sub_cols], geometry="geometry", crs=4326)

    lj, lg = write_geo(lines, "transmission_lines", simplify=True)
    sj, sg = write_geo(subs, "substations", simplify=False)
    qp.to_csv(OUT / "queue_projects.csv", index=False)
    by_c.to_csv(OUT / "queue_by_county.csv", index=False)
    chk.to_csv(OUT / "queue_state_check.csv", index=False)
    log.info("queue state check:\n%s", chk.to_string())

    # ---- checks required by the brief
    c500 = lines[lines.volt_class.eq("500+")].groupby("state").size().to_dict()
    for st in ("CA", "AZ", "NV"):
        if c500.get(st, 0) == 0:
            raise SystemExit(f"check failed: no 500 kV line piece in {st}")
    if subs.state.isna().any():
        raise SystemExit("check failed: substation without state")
    log.info("500+ kV line pieces by state: %s", c500)

    lm, sm = meta(RAW / "hifld_lines"), meta(RAW / "hifld_substations")
    osm_meta = json.loads((RAW / "osm" / "_complete.json").read_text()) if (RAW / "osm" / "_complete.json").exists() else {}
    rel = lambda p: str(p.relative_to(ROOT))  # noqa: E731
    line_fields = {
        "id": "hifld-<HIFLD ID>-<state>; lines crossing a state border are split into one piece per state",
        "hifld_id": "HIFLD line ID", "voltage_kv": "HIFLD VOLTAGE in kV; null where HIFLD reports -999999 (unknown)",
        "volt_class": "<115, 115-161, 230 (162-299 kV), 345 (300-499 kV), 500+, unknown",
        "owner": "HIFLD OWNER", "status": "HIFLD STATUS", "state": "TIGER state the piece lies in",
        "line_type": "HIFLD TYPE (AC/DC, overhead/underground)", "sub_1": "HIFLD SUB_1 endpoint", "sub_2": "HIFLD SUB_2 endpoint",
        "voltage_inferred": "HIFLD INFERRED flag (Y = voltage inferred by HIFLD)", "hifld_source": "HIFLD SOURCE",
        "length_km": "piece length in EPSG:5070"}
    sub_fields = {
        "id": "hifld-<HIFLD ID> or osm-<type>-<osm id>", "name": "HIFLD NAME (UNKNOWNnnnn = unnamed) or OSM name",
        "max_kv": "max voltage kV (see kv_source)", "min_kv": "min voltage kV",
        "owner": "OSM operator for OSM records; for HIFLD records (no owner field) the most common OWNER of HIFLD lines within 200 m",
        "status": "HIFLD STATUS or 'IN SERVICE (OSM)'", "lines": "HIFLD LINES if >0, else count of distinct HIFLD lines within 200 m",
        "state": "TIGER 2024 state containing the point", "county": "TIGER 2024 county name containing the point",
        "county_fips": "5-digit county FIPS", "volt_class": "class of max_kv (same bins as lines)",
        "sub_type": "HIFLD TYPE (SUBSTATION, TAP, RISER...) or OSM substation=* tag", "source": "hifld or osm",
        "osm_id": "OSM element for source=osm", "kv_source": "hifld | osm_match (HIFLD unknown, taken from OSM match) | inferred_from_lines | osm | null",
        "lines_source": "hifld or snap_200m", "lines_hifld": "raw HIFLD LINES", "lines_snapped": "distinct HIFLD lines within 200 m",
        "owner_source": "osm_operator or connected_lines", "queue_active_mw": "active Queued Up MW whose POI name matches this substation name (approximate)",
        "queue_n_active": "count of those projects"}
    manifest = {"domain": "grid", "generated": TODAY, "script": "pipeline/process_grid.py", "layers": [
        {"layer": "transmission_lines", "path": rel(lj), "full_res_path": rel(lg),
         "source_name": "HIFLD Electric Power Transmission Lines (layer " + str(lm["layer_meta"].get("name")) + ")",
         "source_url": lm["source_url"], "retrieved": lm["retrieved"], "record_count": int(len(lines)),
         "raw_record_count_bbox": lm["count"],
         "stats": {"by_volt_class": lines.volt_class.value_counts().to_dict(),
                   "by_state": lines.state.value_counts().to_dict(), "pieces_500kv_plus_by_state": c500,
                   "km_by_volt_class": lines.groupby("volt_class").length_km.sum().round(0).to_dict()},
         "fields": line_fields,
         "caveats": ["HIFLD coverage is mostly >=69 kV transmission; distribution lines are absent.",
                     "Voltages flagged voltage_inferred=Y were estimated by HIFLD; -999999 values are stored as null/unknown.",
                     f"GeoJSON simplified with Douglas-Peucker {SIMPLIFY_DEG} deg (~30 m), 5-decimal coordinates; use the .gpkg for analysis.",
                     "Line locations show where lines are, not spare capacity."]},
        {"layer": "substations", "path": rel(sj), "full_res_path": rel(sg),
         "source_name": "HIFLD Electric Substations (last public HIFLD release, ArcGIS Online mirror) + OpenStreetMap power=substation >=115 kV gap fill",
         "source_url": sm["source_url"] + " ; https://overpass-api.de/api/interpreter",
         "retrieved": sm["retrieved"], "record_count": int(len(subs)), "raw_record_count_bbox": sm["count"],
         "stats": {"by_source": subs.source.value_counts().to_dict(), "by_state": subs.state.value_counts().to_dict(),
                   "by_volt_class": subs.volt_class.value_counts().to_dict(),
                   "kv_source": subs.kv_source.value_counts(dropna=False).rename(index=lambda x: str(x)).to_dict(),
                   "with_queue_poi_match": int((subs.queue_n_active > 0).sum()), "osm_crosscheck": osm_stats,
                   "osm_query": osm_meta.get("query"), "osm_retrieved": osm_meta.get("retrieved")},
         "fields": sub_fields,
         "caveats": ["HIFLD Electric Substations is no longer on HIFLD Open; the copy used is a public ArcGIS Online mirror of the last public release (data last edited " +
                     time.strftime("%Y-%m-%d", time.gmtime(sm["layer_meta"]["editingInfo"]["dataLastEditDate"] / 1000)) + "), so substations built since are missing unless OSM has them.",
                     f"OSM substations tagged >=115 kV were added only when no HIFLD substation lay within {OSM_MATCH_M} m; OSM tags are volunteer-mapped and may include plant collector substations (sub_type GENERATION) that are not open POIs.",
                     "Where HIFLD max voltage is unknown it was filled from a matched OSM record or from the highest-voltage HIFLD line within 200 m (kv_source tells which).",
                     "HIFLD substations carry no owner; owner is inferred from connected lines and may be wrong at shared/interconnection stations.",
                     "queue_active_mw uses exact matches of normalised POI names to substation names in the same state; many POIs are line taps or unmatched names, so 0 does not mean no queue.",
                     "No public data on spare capacity; queue volume is only a congestion proxy."]},
        {"layer": "queue_projects", "path": "data/processed/grid/queue_projects.csv",
         "source_name": "Berkeley Lab Queued Up 2026 Edition project-level data (through end of 2025); CAISO Public Queue Report (Grid Generation Queue)",
         "source_url": "https://emp.lbl.gov/queues ; https://eta-publications.lbl.gov/sites/default/files/2026-05/lbnl_ix_queue_data_file_thru2025.xlsx ; https://www.caiso.com/documents/publicqueuereport.xlsx",
         "retrieved": TODAY, "record_count": int(len(qp)),
         "stats": {"by_status": qp.status.value_counts().to_dict(),
                   "active_by_state_type_mw": qp[qp.status.eq("active")].groupby(["state", "type"]).mw.sum().round(0).unstack(fill_value=0).to_dict(orient="index"),
                   "active_with_poi_sub_match": int((qp.status.eq("active") & qp.poi_sub_id.notna()).sum()),
                   "active_total": int(qp.status.eq("active").sum()),
                   "filled_from_caiso": "poi/county filled from CAISO report where Queued Up blank (see source column)"},
         "fields": {"queue_id": "<entity>:<q_id>, with #n suffix where LBNL repeats a q_id (unique)", "entity": "transmission provider (ISO or utility)",
                    "poi_name": "point of interconnection as reported", "state": "state", "county": "TIGER 2024 county name (first listed county for multi-county projects)",
                    "type": "solar / storage / wind / gas / hybrid (any multi-type) / other", "mw": "sum of mw_1+mw_2+mw_3 (generator + storage nameplate, matches LBNL capacity totals)",
                    "status": "active / withdrawn / operational, plus suspended (LBNL 'suspended', not counted as active, matching the report) and unknown (LBNL 'unknown')",
                    "queue_date": "date entered queue", "source": "data source", "status_raw": "LBNL q_status", "type_clean": "LBNL type_clean",
                    "mw_solar": "solar component MW", "mw_storage": "battery / other-storage component MW", "county_fips": "county FIPS",
                    "project_name": "project name (LBNL, else CAISO report)", "utility": "utility", "service": "ERIS/NRIS etc",
                    "study_phase": "LBNL IA_phase_clean", "prop_date": "proposed online date", "q_year": "queue year",
                    "poi_sub_id": "matched substations.geojson id (approximate name match) or blank"},
         "caveats": ["Active storage MW here is well below the Queued Up report's state storage totals (ours / report: " +
                     ", ".join(f"{r.state} {r.storage_ratio:.2f}" for r in chk.itertuples()) +
                     "). The report's state storage totals include storage it imputes for hybrid projects (e.g. solar+storage with no storage MW given); the project-level file does not contain those imputed values, so they are missing here. Active solar MW matches the report exactly (ratio " +
                     ", ".join(f"{r.state} {r.solar_ratio:.2f}" for r in chk.itertuples()) + ").",
                     "NV Energy queue rows have no POI name in Queued Up.",
                     "Queue data is a snapshot through 2025-12-31; CAISO report is newer but only used to fill blanks.",
                     "Suspended requests are kept with status=suspended and excluded from active totals, as in the Queued Up report; they still hold queue positions (NV has about 17 GW of suspended solar)."]},
        {"layer": "queue_by_county", "path": "data/processed/grid/queue_by_county.csv",
         "source_name": "derived from queue_projects.csv (status=active)", "source_url": "https://emp.lbl.gov/queues",
         "retrieved": TODAY, "record_count": int(len(by_c)),
         "fields": {"state": "state", "county": "TIGER county name", "active_mw_total": "sum of mw for active projects",
                    "active_mw_solar": "solar component MW", "active_mw_storage": "storage component MW",
                    "n_projects": "active project count", "county_fips": "county FIPS"},
         "caveats": ["Projects with no county are grouped as '(county not reported)'."]},
        {"layer": "queue_state_check", "path": "data/processed/grid/queue_state_check.csv",
         "source_name": "comparison of queue_projects active totals vs Queued Up 2026 workbook sheet '11. Active Cap. Maps' (state x type GW)",
         "source_url": "https://emp.lbl.gov/queues", "retrieved": TODAY, "record_count": int(len(chk)),
         "fields": {c: "see column name; ratio = ours / report" for c in chk.columns},
         "comparison": chk.to_dict(orient="records"),
         "caveats": ["Report state totals cover 5 types (Gas, Offshore Wind, Solar, Storage, Wind); ours_active_gw_all includes all types."]},
    ]}
    (OUT / "MANIFEST.json").write_text(json.dumps(manifest, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)))
    log.info("=== process_grid done: lines %d, substations %d, queue %d, counties %d", len(lines), len(subs), len(qp), len(by_c))


if __name__ == "__main__":
    main()

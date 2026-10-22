# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "geopandas==1.1.1",
#   "shapely==2.1.1",
#   "pyogrio==0.11.1",
#   "pandas==2.3.3",
#   "numpy==2.3.4",
#   "openpyxl==3.1.5",
# ]
# ///
"""Process raw infrastructure data into app/screening layers (data/processed/infra/).

Inputs come from pipeline/fetch_infra.py (data/raw/infra/). Outputs (EPSG:4326):
  power_plants.geojson        EIA-860 2025 plants (one point per plant, generator MW rolled up)
  power_generators.csv        EIA-860 2025 generator rows for the five states
  fiber.geojson / .gpkg       fiber routes: OSM mapped telecom lines + labelled corridor proxies
  water_stress.geojson / .gpkg  WRI Aqueduct 4.0 baseline annual, basin x state units
  az_ama_ina.geojson          Arizona groundwater AMAs and INAs (ADWR)
  roads_major.geojson / .gpkg TIGER 2025 primary roads (interstates, US and state highways)
  blm_solar_row_cases.geojson / .csv   BLM MLRS solar ROW cases, active (Authorized/Pending/Interim)
  blm_solar_row_cases_closed.geojson   same, closed cases (history)
  data_centers_osm.geojson    OSM-mapped data centers
  MANIFEST.json               one entry per layer

Skips work already done unless --force. Log: logs/infra.log
"""
import argparse
import json
import logging
import re
import sys
import time
import zipfile
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely
from shapely.geometry import LineString, Point

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "infra"
OUT = ROOT / "data" / "processed" / "infra"
LOG = ROOT / "logs" / "infra.log"
STATES = {"CA": "California", "AZ": "Arizona", "NV": "Nevada", "NM": "New Mexico", "UT": "Utah"}
ALBERS = 5070
TODAY = time.strftime("%Y-%m-%d")

log = logging.getLogger("process_infra")


def setup_logging():
    LOG.parent.mkdir(parents=True, exist_ok=True)
    fmt = logging.Formatter("%(asctime)s process_infra %(levelname)s %(message)s")
    for h in (logging.FileHandler(LOG), logging.StreamHandler(sys.stdout)):
        h.setFormatter(fmt)
        log.addHandler(h)
    log.setLevel(logging.INFO)


def retrieved_date(path: Path):
    """Date the raw file was downloaded (file mtime), or the 'retrieved' key in fetched JSON."""
    if path.suffix in (".json", ".geojson"):
        try:
            with open(path) as f:
                head = json.load(f)
            if isinstance(head, dict) and head.get("retrieved"):
                return head["retrieved"]
        except Exception:  # noqa: BLE001
            pass
    return time.strftime("%Y-%m-%d", time.localtime(path.stat().st_mtime))


def write_geojson(gdf: gpd.GeoDataFrame, name: str, gpkg=False):
    OUT.mkdir(parents=True, exist_ok=True)
    gdf = gdf.to_crs(4326)
    if gpkg:
        p = OUT / f"{name}.gpkg"
        p.unlink(missing_ok=True)
        gdf.to_file(p, layer=name, driver="GPKG")
    p = OUT / f"{name}.geojson"
    p.unlink(missing_ok=True)
    gdf.to_file(p, driver="GeoJSON", COORDINATE_PRECISION=5, WRITE_BBOX="NO")
    mb = p.stat().st_size / 1e6
    log.info("wrote %s (%d features, %.1f MB)", p.relative_to(ROOT), len(gdf), mb)
    if mb > 25:
        log.warning("%s is over the 25 MB app budget", p.name)
    return p


def simplify_m(gdf: gpd.GeoDataFrame, tol_m: float):
    """Topology-preserving simplification with a tolerance in metres (done in EPSG:5070)."""
    g = gdf.to_crs(ALBERS)
    g["geometry"] = g.geometry.simplify(tol_m, preserve_topology=True)
    g = g[~g.geometry.is_empty & g.geometry.notna()]
    return g.to_crs(4326)


def states_gdf():
    z = RAW / "tiger" / "cb_2024_us_state_500k.zip"
    s = gpd.read_file(f"zip://{z}")
    s = s[s["STUSPS"].isin(STATES)][["STUSPS", "NAME", "geometry"]].rename(columns={"STUSPS": "state"})
    return s.to_crs(4326)


def assign_state(gdf: gpd.GeoDataFrame, states: gpd.GeoDataFrame):
    """State of each feature by its representative point."""
    pts = gpd.GeoDataFrame(geometry=gdf.geometry.representative_point(), crs=gdf.crs)
    j = gpd.sjoin(pts, states[["state", "geometry"]], how="left", predicate="within")
    j = j[~j.index.duplicated()]
    return j["state"].reindex(gdf.index)


# ---------------------------------------------------------------- EIA-860 plants
TECH_CLASS = [
    (r"solar photovoltaic|solar thermal", "solar"),
    (r"onshore wind|offshore wind|wind", "wind"),
    (r"batter|storage|flywheel", "storage"),
    (r"natural gas|other gases|landfill gas", "gas"),
    (r"coal", "coal"),
    (r"nuclear", "nuclear"),
    (r"hydro", "hydro"),
    (r"geothermal", "geothermal"),
    (r"petroleum", "oil"),
    (r"wood|biomass|municipal solid waste", "biomass"),
]
OPERABLE = {"OP", "SB", "OS", "OA"}


def tech_class(t: str):
    t = (t or "").lower()
    for pat, c in TECH_CLASS:
        if re.search(pat, t):
            return c
    return "other"


def read_eia(zf, member, sheet=None):
    df = pd.read_excel(zf.open(member), sheet_name=sheet or 0, header=1, dtype={"Generator ID": str})
    df = df[pd.to_numeric(df["Plant Code"], errors="coerce").notna()].copy()
    df["Plant Code"] = df["Plant Code"].astype(int)
    return df


def process_plants(states, manifest):
    z = RAW / "eia860" / "eia8602025.zip"
    zf = zipfile.ZipFile(z)
    plants = read_eia(zf, "2___Plant_Y2025.xlsx")
    plants = plants[plants["State"].isin(STATES)]
    gens = []
    for sheet, group in (("Operable", "operable"), ("Proposed", "proposed"), ("Retired and Canceled", "retired_or_canceled")):
        g = read_eia(zf, "3_1_Generator_Y2025.xlsx", sheet)
        g = g[g["State"].isin(STATES)].copy()
        g["status_group"] = group
        gens.append(g)
    gens = pd.concat(gens, ignore_index=True)
    gens["mw"] = pd.to_numeric(gens["Nameplate Capacity (MW)"], errors="coerce").fillna(0.0)
    gens["tech_class"] = gens["Technology"].map(tech_class)
    # Canceled proposals are in the same sheet as retirements; separate them by status code.
    gens.loc[(gens["status_group"] == "retired_or_canceled") & (gens["Status"] == "CN"), "status_group"] = "canceled"
    gens.loc[gens["status_group"] == "retired_or_canceled", "status_group"] = "retired"
    keep = ["Plant Code", "Plant Name", "State", "County", "Generator ID", "Technology", "tech_class",
            "Prime Mover", "Energy Source 1", "mw", "Status", "status_group", "Operating Year",
            "Planned Retirement Year", "Retirement Year", "Current Year", "Effective Year"]
    gcsv = gens[[c for c in keep if c in gens.columns]].rename(columns={
        "Plant Code": "plant_id", "Plant Name": "plant", "State": "state", "County": "county",
        "Generator ID": "generator_id", "Technology": "technology", "Prime Mover": "prime_mover",
        "Energy Source 1": "energy_source", "Status": "status_code", "Operating Year": "operating_year",
        "Planned Retirement Year": "planned_retirement_year", "Retirement Year": "retirement_year",
        "Current Year": "proposed_year", "Effective Year": "proposed_effective_year"})
    OUT.mkdir(parents=True, exist_ok=True)
    gcsv.to_csv(OUT / "power_generators.csv", index=False)
    log.info("wrote power_generators.csv (%d generators)", len(gcsv))

    def roll(df):
        by = {k: df.loc[df["status_group"] == k, "mw"].sum() for k in ("operable", "proposed", "retired", "canceled")}
        live = df[df["status_group"].isin(["operable", "proposed"])]
        base = live if len(live) else df
        tmw = base.groupby("tech_class")["mw"].sum().sort_values(ascending=False)
        techs = base.groupby("Technology")["mw"].sum().sort_values(ascending=False)
        op = df[df["status_group"] == "operable"]
        yrs = pd.to_numeric(op.get("Operating Year"), errors="coerce").dropna()
        if by["operable"] > 0:
            status = "operating"
        elif by["proposed"] > 0:
            status = "proposed"
        elif by["retired"] > 0:
            status = "retired"
        else:
            status = "canceled"
        return pd.Series({
            "tech": tmw.index[0] if len(tmw) else "other",
            "technologies": "; ".join(techs.index[:4]),
            "mw": round(by["operable"] if status == "operating" else by["proposed"] if status == "proposed" else by["retired"] if status == "retired" else by["canceled"], 2),
            "mw_operable": round(by["operable"], 2),
            "mw_proposed": round(by["proposed"], 2),
            "mw_retired": round(by["retired"], 2),
            "status": status,
            "status_codes": ",".join(sorted(df["Status"].dropna().astype(str).unique())),
            "n_generators": int(len(df)),
            "first_operating_year": int(yrs.min()) if len(yrs) else None,
            "last_operating_year": int(yrs.max()) if len(yrs) else None,
        })

    agg = gens.groupby("Plant Code").apply(roll, include_groups=False).reset_index()
    p = plants[["Plant Code", "Plant Name", "Utility Name", "State", "County", "Latitude", "Longitude",
                "Balancing Authority Code", "Sector Name", "Grid Voltage (kV)",
                "Transmission or Distribution System Owner"]].merge(agg, on="Plant Code", how="inner")
    p["Latitude"] = pd.to_numeric(p["Latitude"], errors="coerce")
    p["Longitude"] = pd.to_numeric(p["Longitude"], errors="coerce")
    n_nogeo = int(p[["Latitude", "Longitude"]].isna().any(axis=1).sum())
    p = p.dropna(subset=["Latitude", "Longitude"])
    p = p.rename(columns={
        "Plant Code": "plant_id", "Plant Name": "plant", "Utility Name": "utility", "State": "state",
        "County": "county", "Latitude": "lat", "Longitude": "lon", "Balancing Authority Code": "balancing_authority",
        "Sector Name": "sector", "Grid Voltage (kV)": "grid_voltage_kv",
        "Transmission or Distribution System Owner": "td_owner"})
    p["grid_voltage_kv"] = pd.to_numeric(p["grid_voltage_kv"], errors="coerce")
    gdf = gpd.GeoDataFrame(p, geometry=gpd.points_from_xy(p["lon"], p["lat"]), crs=4326)
    write_geojson(gdf, "power_plants")

    counts = gdf.groupby(["state", "status"]).size().unstack(fill_value=0)
    mw = gdf[gdf["status"] == "operating"].groupby("state")["mw_operable"].sum().round(0)
    log.info("EIA-860 2025 plants per state (status counts):\n%s", counts.to_string())
    log.info("EIA-860 2025 operating nameplate MW per state:\n%s", mw.to_string())
    (OUT / "power_plants_by_state.csv").write_text(
        counts.assign(total=counts.sum(axis=1), operating_mw=mw).to_csv())

    src = "https://www.eia.gov/electricity/data/eia860/"
    manifest.append({
        "layer": "power_plants", "path": "data/processed/infra/power_plants.geojson",
        "source_name": "US EIA Form EIA-860 Annual Electric Generator Report, 2025 data (zip files dated 2026-09-09)",
        "source_url": src, "retrieved": retrieved_date(z), "record_count": int(len(gdf)),
        "counts_by_state": {s: int(v) for s, v in gdf["state"].value_counts().items()},
        "fields": {
            "plant_id": "EIA plant code", "plant": "plant name", "utility": "operating utility",
            "state": "state", "county": "county", "lat": "latitude", "lon": "longitude",
            "tech": "dominant technology class by MW among operable+proposed generators (solar, wind, storage, gas, coal, nuclear, hydro, geothermal, oil, biomass, other)",
            "technologies": "EIA technology names, largest MW first (up to 4)",
            "mw": "nameplate MW for the plant's status (operable MW if operating, else proposed MW, else retired MW)",
            "mw_operable": "nameplate MW of operable generators (status OP, SB, OS, OA)",
            "mw_proposed": "nameplate MW of proposed generators (planned, under construction, etc.)",
            "mw_retired": "nameplate MW of retired generators",
            "status": "operating / proposed / retired / canceled (plant level, derived from generator statuses)",
            "status_codes": "EIA generator status codes present at the plant",
            "n_generators": "generator rows at the plant", "first_operating_year": "earliest operating year of operable units",
            "last_operating_year": "latest operating year of operable units",
            "balancing_authority": "EIA balancing authority code", "sector": "EIA sector",
            "grid_voltage_kv": "reported grid interconnection voltage (kV)", "td_owner": "transmission/distribution system owner"},
        "caveats": [
            "Plants are EIA-860 respondents (generally 1 MW and larger). Behind-the-meter and small distributed solar are not included.",
            "Proposed generators are self-reported plans and many never get built; treat proposed MW as indicative.",
            "Retired plants are kept because retired thermal sites often keep their interconnection and are candidates for reuse; filter on status.",
            f"{n_nogeo} plant(s) in the five states had no coordinates in the plant file and were dropped.",
            "Generator-level detail is in power_generators.csv; per-state counts in power_plants_by_state.csv.",
        ],
    })
    manifest.append({
        "layer": "power_generators", "path": "data/processed/infra/power_generators.csv",
        "source_name": "US EIA Form EIA-860, 2025 data, file 3_1 Generator (Operable, Proposed, Retired and Canceled sheets)",
        "source_url": src, "retrieved": retrieved_date(z), "record_count": int(len(gcsv)),
        "fields": {c: c.replace("_", " ") for c in gcsv.columns},
        "caveats": ["status_group 'canceled' is generator status CN from the Retired and Canceled sheet."],
    })
    return gdf


# ---------------------------------------------------------------- Roads
ROAD_CLASS = {"I": "interstate", "U": "us_highway", "S": "state_highway"}


def process_roads(states, manifest):
    z = RAW / "tiger" / "tl_2025_us_primaryroads.zip"
    r = gpd.read_file(f"zip://{z}").to_crs(4326)
    parts = []
    for _, s in states.iterrows():
        c = gpd.clip(r, s.geometry)
        c = c[c.geom_type.isin(["LineString", "MultiLineString"])].copy()
        c["state"] = s["state"]
        parts.append(c)
    r = pd.concat(parts, ignore_index=True)
    r = gpd.GeoDataFrame(r, geometry="geometry", crs=4326)
    r["road_class"] = r["RTTYP"].map(ROAD_CLASS).fillna("other")
    r = r.rename(columns={"LINEARID": "id", "FULLNAME": "name", "RTTYP": "route_type", "MTFCC": "mtfcc"})
    r = r[["id", "name", "route_type", "road_class", "mtfcc", "state", "geometry"]]
    full = r.copy()
    r = simplify_m(r, 30)
    p = OUT / "roads_major.gpkg"
    p.unlink(missing_ok=True)
    full.to_file(p, layer="roads_major", driver="GPKG")
    write_geojson(r, "roads_major")
    manifest.append({
        "layer": "roads_major", "path": "data/processed/infra/roads_major.geojson",
        "source_name": "US Census Bureau TIGER/Line 2025 Primary Roads (MTFCC S1100)",
        "source_url": "https://www2.census.gov/geo/tiger/TIGER2025/PRIMARYROADS/",
        "retrieved": retrieved_date(z), "record_count": int(len(r)),
        "counts_by_class": {k: int(v) for k, v in r["road_class"].value_counts().items()},
        "fields": {"id": "TIGER LINEARID", "name": "TIGER full name", "route_type": "TIGER RTTYP (I interstate, U US, S state, C county, M common name, O other)",
                   "road_class": "interstate / us_highway / state_highway / other", "mtfcc": "MAF/TIGER feature class code",
                   "state": "state the segment was clipped to"},
        "caveats": ["Primary roads only (limited-access divided highways, mostly interstates and some US/state routes). Secondary and local access roads are not included; site access roads must be checked separately.",
                    "App file simplified to 30 m tolerance; full resolution in roads_major.gpkg."],
    })
    return full


# ---------------------------------------------------------------- Fiber
def osm_lines(path: Path):
    d = json.loads(path.read_text())
    rows = []
    for e in d.get("elements", []):
        if e.get("type") != "way" or "geometry" not in e:
            continue
        t = e.get("tags", {})
        linear = (t.get("communication") in ("line", "cable") or t.get("telecom") in ("line", "cable")
                  or "fib" in t.get("cable", "") or (t.get("man_made") == "cable" and t.get("cable") != "power")
                  or ("fib" in t.get("telecom:medium", "") and not t.get("telecom") and not t.get("building")))
        if not linear or t.get("man_made") == "street_cabinet" or t.get("building") or t.get("area") == "yes":
            continue
        coords = [(g["lon"], g["lat"]) for g in e["geometry"]]
        if len(coords) < 2:
            continue
        medium = t.get("telecom:medium") or t.get("cable") or None
        fiber_tagged = bool(medium and "fib" in medium.lower())
        rows.append({
            "id": f"osm_way_{e['id']}", "basis": "osm_fiber_tagged" if fiber_tagged else "osm_telecom_line",
            "is_proxy": not fiber_tagged, "name": t.get("name"), "operator": t.get("operator"),
            "medium": medium, "location": t.get("location"), "geometry": LineString(coords)})
    return gpd.GeoDataFrame(rows, geometry="geometry", crs=4326), d.get("retrieved")


def process_fiber(states, roads, manifest):
    osm_p = RAW / "osm" / "osm_telecom_lines.json"
    osm, osm_date = osm_lines(osm_p)
    osm["state"] = assign_state(osm, states)
    osm = osm[osm["state"].notna()]

    inter = roads[roads["road_class"] == "interstate"].copy()
    inter = inter.dissolve(by=["name", "state"], as_index=False)
    inter = inter.assign(id=["proxy_interstate_" + re.sub(r"\W+", "_", f"{n}_{s}") for n, s in zip(inter["name"], inter["state"])],
                         basis="proxy_interstate_corridor", is_proxy=True, operator=None, medium=None, location=None)

    rail_p = RAW / "rail" / "narn_class1_mainline.geojson"
    rail = gpd.read_file(rail_p).to_crs(4326)
    rail["name"] = rail["RROWNER1"].fillna("") + " " + rail["SUBDIV"].fillna("").str.strip() + " Sub"
    rail = rail.dissolve(by=["RROWNER1", "SUBDIV", "STATEAB"], as_index=False, dropna=False)
    rail = rail.assign(id=[f"proxy_rail_{i}" for i in range(len(rail))], basis="proxy_class1_rail_corridor",
                       is_proxy=True, operator=rail["RROWNER1"], medium=None, location=None, state=rail["STATEAB"])

    cols = ["id", "basis", "is_proxy", "name", "operator", "medium", "location", "state", "geometry"]
    f = pd.concat([osm[cols], inter[cols], rail[cols]], ignore_index=True)
    f = gpd.GeoDataFrame(f, geometry="geometry", crs=4326)
    f["geometry"] = f.geometry.line_merge() if hasattr(f.geometry, "line_merge") else f.geometry
    p = OUT / "fiber.gpkg"
    p.unlink(missing_ok=True)
    f.to_file(p, layer="fiber", driver="GPKG")
    fs = simplify_m(f, 30)
    write_geojson(fs, "fiber")
    counts = {k: int(v) for k, v in fs["basis"].value_counts().items()}
    km = f.to_crs(ALBERS).assign(km=lambda d: d.length / 1000).groupby("basis")["km"].sum().round(0)
    log.info("fiber features by basis: %s; km: %s", counts, km.to_dict())
    manifest.append({
        "layer": "fiber", "path": "data/processed/infra/fiber.geojson",
        "source_name": "PROXY. OpenStreetMap telecom/communication lines (Overpass API) + interstate corridors (TIGER 2025) + Class I main-line rail corridors (BTS NTAD North American Rail Network)",
        "source_url": "https://overpass-api.de/ ; https://www2.census.gov/geo/tiger/TIGER2025/PRIMARYROADS/ ; https://geodata.bts.gov/datasets/usdot::north-american-rail-network-lines",
        "retrieved": osm_date or retrieved_date(osm_p), "record_count": int(len(fs)),
        "counts_by_basis": counts, "km_by_basis": {k: float(v) for k, v in km.items()},
        "fields": {"id": "feature id (osm_way_<id> or proxy_*)",
                   "basis": "osm_fiber_tagged (OSM line tagged fibre), osm_telecom_line (OSM communication/telecom line, medium unknown), proxy_interstate_corridor, proxy_class1_rail_corridor",
                   "is_proxy": "true unless the OSM feature is explicitly tagged as fibre",
                   "name": "name (OSM name, interstate name, or railroad + subdivision)", "operator": "OSM operator or railroad owner",
                   "medium": "OSM telecom:medium / cable tag", "location": "OSM location tag (underground/overhead)", "state": "state"},
        "caveats": [
            "This is a PROXY for long-haul fiber, not a carrier route map. No free, complete public map of US long-haul fiber exists; carrier route maps are proprietary or published only as images.",
            "OSM coverage of fiber is sparse and uneven; most OSM lines here are utility communication lines (for example SCE, PG&E, TEP) whose medium is not tagged.",
            "Interstate and Class I main-line rail corridors are included because published research (Durairajan et al., 'InterTubes', ACM SIGCOMM 2015) found US long-haul fiber is largely co-located with road and rail rights-of-way. Presence of a corridor does not prove fiber or available capacity.",
            "FCC Broadband Data Collection reports service availability by location, not routes, so it was not used for route geometry.",
            "Confirm fiber availability, carriers and lateral cost with providers before any data center decision.",
            "App file simplified to 30 m tolerance; full resolution in fiber.gpkg.",
        ],
    })


# ---------------------------------------------------------------- Water
AQ_FIELDS = ["string_id", "pfaf_id", "gid_0", "gid_1", "name_1", "area_km2",
             "bws_raw", "bws_score", "bws_cat", "bws_label",
             "bwd_score", "bwd_label", "iav_score", "iav_label", "sev_score", "sev_label",
             "gtd_raw", "gtd_score", "gtd_label", "drr_score", "drr_label", "w_awr_def_qal_label" ]


def process_water(states, manifest):
    z = RAW / "aqueduct" / "aqueduct-4-0-water-risk-data.zip"
    # Reading the GDB through /vsizip/ is slow and memory-hungry; extract it once next to the zip.
    inner = "Aqueduct40_waterrisk_download_Y2023M07D05/GDB/Aq40_Y2023D07M05.gdb"
    gdb = z.parent / inner
    if not gdb.exists():
        log.info("extracting Aqueduct GDB from %s", z.name)
        with zipfile.ZipFile(z) as zf:
            zf.extractall(z.parent, members=[m for m in zf.namelist() if m.startswith(inner)])
    gdb = str(gdb)
    names = "','".join(STATES.values())
    import pyogrio
    # GDAL OpenFileGDB returns nothing if a where-clause field is not among the selected columns,
    # so gid_0 and name_1 are kept in AQ_FIELDS.
    avail = set(pyogrio.read_info(gdb, layer="baseline_annual")["fields"])
    cols = [c for c in AQ_FIELDS if c in avail]
    w = gpd.read_file(gdb, layer="baseline_annual", columns=cols,
                      where=f"gid_0 = 'USA' AND name_1 IN ('{names}')", engine="pyogrio")
    w = w.to_crs(4326)
    inv = {v: k for k, v in STATES.items()}
    w["state"] = w["name_1"].map(inv)
    for c in [c for c in w.columns if c.endswith(("_score", "_raw"))]:
        w[c] = pd.to_numeric(w[c], errors="coerce").replace(-9999, np.nan)
    w["bws_cat"] = pd.to_numeric(w["bws_cat"], errors="coerce").replace(-9999, np.nan)
    w["water_stress"] = w["bws_score"]
    w = w.rename(columns={"string_id": "aq_id"}).drop(columns=["name_1", "gid_0"])
    w["geometry"] = w.geometry.make_valid()
    w = w[w.geom_type.isin(["Polygon", "MultiPolygon"]) | (w.geom_type == "GeometryCollection")]
    w["geometry"] = w.geometry.apply(lambda g: shapely.multipolygons(shapely.get_parts(g)[shapely.get_type_id(shapely.get_parts(g)) == 3]) if g.geom_type == "GeometryCollection" else g)
    p = OUT / "water_stress.gpkg"
    p.unlink(missing_ok=True)
    w.to_file(p, layer="water_stress", driver="GPKG")
    ws = w.to_crs(ALBERS)
    try:
        ws["geometry"] = ws.geometry.simplify_coverage(500)
        how = "coverage-preserving (shared edges kept) at 500 m"
    except Exception as e:  # noqa: BLE001
        log.warning("coverage simplify failed (%s); using per-polygon topology-preserving simplify", e)
        ws["geometry"] = ws.geometry.simplify(500, preserve_topology=True)
        how = "per-polygon topology-preserving at 500 m"
    ws = ws[~ws.geometry.is_empty].to_crs(4326)
    write_geojson(ws, "water_stress")
    log.info("water stress units: %d; by bws_label: %s", len(ws), ws["bws_label"].value_counts().to_dict())
    manifest.append({
        "layer": "water_stress", "path": "data/processed/infra/water_stress.geojson",
        "source_name": "WRI Aqueduct 4.0 Water Risk Atlas, baseline annual indicators (data version Y2023M07D05)",
        "source_url": "https://www.wri.org/data/aqueduct-global-maps-40-data", "retrieved": retrieved_date(z),
        "record_count": int(len(ws)),
        "counts_by_bws_label": {k: int(v) for k, v in ws["bws_label"].value_counts().items()},
        "fields": {"aq_id": "Aqueduct unit id (HydroBASINS level 6 basin x state)", "pfaf_id": "HydroBASINS Pfafstetter basin id",
                   "gid_1": "GADM state id", "state": "state", "area_km2": "unit area km2",
                   "bws_raw": "baseline water stress: ratio of total withdrawals to available renewable supply",
                   "bws_score": "baseline water stress score 0-5 (5 = extremely high)",
                   "bws_cat": "category: -1 arid and low water use, 0 low (<10%), 1 low-medium (10-20%), 2 medium-high (20-40%), 3 high (40-80%), 4 extremely high (>80%)",
                   "bws_label": "text label for bws_cat", "bwd_score": "baseline water depletion score 0-5", "bwd_label": "label",
                   "iav_score": "interannual variability score 0-5", "iav_label": "label", "sev_score": "seasonal variability score 0-5", "sev_label": "label",
                   "gtd_raw": "groundwater table decline (cm/yr)", "gtd_score": "groundwater table decline score 0-5", "gtd_label": "label",
                   "drr_score": "drought risk score 0-5", "drr_label": "label",
                   "water_stress": "copy of bws_score (0-5); the field screening uses"},
        "caveats": [
            "Aqueduct is a global model at sub-basin scale (baseline period 1979-2019); it does not show local water rights, aquifer yield or utility supply. Use it as a regional screen only.",
            f"App file simplified {how}; full resolution in water_stress.gpkg.",
            "Groundwater rules matter more than basin stress for a data center or solar wash-water supply. Arizona: under the 1980 Groundwater Management Act, groundwater in Active Management Areas (AMAs: Phoenix, Pinal, Prescott, Tucson, Santa Cruz, Willcox, Douglas, Ranegras Plain) is regulated by ADWR; new non-exempt uses generally need a grandfathered right, a withdrawal permit or service from a provider, and new subdivisions need an Assured Water Supply. Irrigation Non-expansion Areas (INAs) limit new irrigated acres. Boundaries are in az_ama_ina.geojson. Outside AMAs and INAs groundwater pumping is far less restricted.",
            "Other states (general, verify before relying on it): California's Sustainable Groundwater Management Act (SGMA, 2014) requires Groundwater Sustainability Plans in medium and high priority basins, and many basins now limit pumping; Nevada's State Engineer manages designated basins and many are fully or over-appropriated, so new water usually means buying or transferring existing rights; New Mexico's State Engineer administers declared groundwater basins (most of the state) and new appropriations require a permit; Utah's State Engineer (Division of Water Rights) issues appropriations and many basins are closed to new appropriations.",
            "Dry or hybrid cooling cuts data center water use sharply; low water stress is not required for a site if cooling design is chosen accordingly.",
        ],
    })


def process_ama(manifest):
    p = RAW / "water" / "adwr_ama_ina.geojson"
    a = gpd.read_file(p).to_crs(4326)
    a["kind"] = np.where(a["BASIN_NAME"].str.contains(" AMA"), "AMA", "INA")
    a = a.rename(columns={"BASIN_NAME": "name", "NAME_ABBR": "abbr"})[["name", "abbr", "kind", "geometry"]]
    a["state"] = "AZ"
    a = simplify_m(a, 100)
    write_geojson(a, "az_ama_ina")
    manifest.append({
        "layer": "az_ama_ina", "path": "data/processed/infra/az_ama_ina.geojson",
        "source_name": "Arizona Department of Water Resources, AMA and INA boundaries (AMA_INA_2024 feature service)",
        "source_url": "https://services.arcgis.com/C34zQ7veRS0V1t04/arcgis/rest/services/AMA_INA_2024/FeatureServer/0",
        "retrieved": retrieved_date(p), "record_count": int(len(a)),
        "fields": {"name": "AMA or INA name", "abbr": "ADWR abbreviation", "kind": "AMA (Active Management Area) or INA (Irrigation Non-expansion Area)", "state": "AZ"},
        "caveats": ["Boundaries simplified at 100 m. Groundwater rules differ inside each AMA; confirm with ADWR."],
    })


# ---------------------------------------------------------------- BLM ROW cases
ACTIVE = {"Authorized", "Pending", "Interim"}
MW_RE = re.compile(r"(\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?)\s*-?\s*(?:MW(?!h)|megawatt)", re.I)


def mw_from_name(name):
    """MW written in a case name ('... 1338MW ...', '600-megawatt'); ignores MWh. None if absent."""
    m = MW_RE.search(name or "")
    return float(m.group(1).replace(",", "")) if m else None


def process_row(states, manifest):
    p = RAW / "blm_row" / "mlrs_solar_row.geojson"
    raw = json.loads(p.read_text())
    rows = []
    for f in raw["features"]:
        a = f["properties"]
        geom = shapely.geometry.shape(f["geometry"]) if f.get("geometry") else None
        dt = a.get("CSE_DISP_DT")
        rows.append({
            "case_id": a.get("CSE_NR"), "legacy_case_id": (a.get("LEG_CSE_NR") or "").strip() or None,
            "project_name": a.get("CSE_NAME"), "customer": a.get("CUST_NM_SEC"),
            "customer_role": a.get("INT_REL_SEC"), "case_type": a.get("BLM_PROD"),
            "case_type_code": a.get("CSE_TYPE_NR"), "commodity": a.get("CMMDTY"),
            "status": a.get("CSE_DISP"), "active": a.get("CSE_DISP") in ACTIVE,
            "status_date": time.strftime("%Y-%m-%d", time.gmtime(dt / 1000)) if dt else None,
            "field_office": a.get("CSE_JURIS_DESC"), "state": a.get("GEO_STATE"),
            "acres": a.get("RCRD_ACRS"), "geom_source": a.get("SRC"),
            "geometry": geom})
    g = gpd.GeoDataFrame(rows, geometry="geometry", crs=4326)
    g["mw"] = g["project_name"].map(mw_from_name)
    solar_dev = g["case_type"].fillna("").str.contains("Solar Development", case=False)
    ac = pd.to_numeric(g["acres"], errors="coerce")
    g["mw_est_low"] = np.where(solar_dev & (ac > 0), (ac / 7).round(0), np.nan)
    g["mw_est_high"] = np.where(solar_dev & (ac > 0), (ac / 5).round(0), np.nan)
    has = g.geometry.notna() & ~g.geometry.is_empty
    g.loc[has, "geometry"] = g.loc[has, "geometry"].make_valid()
    cen = g.loc[has].to_crs(ALBERS).geometry.representative_point().to_crs(4326)
    g["centroid_lat"] = cen.y.round(5).reindex(g.index)
    g["centroid_lon"] = cen.x.round(5).reindex(g.index)
    n_nogeom = int((~has).sum())

    flat = pd.DataFrame(g.drop(columns="geometry"))
    flat.to_csv(OUT / "blm_solar_row_cases.csv", index=False)
    act = g[has & g["active"]]
    closed = g[has & ~g["active"]]
    write_geojson(simplify_m(act, 20), "blm_solar_row_cases")
    write_geojson(simplify_m(closed, 20), "blm_solar_row_cases_closed")
    summ = g.groupby(["state", "status"]).size().unstack(fill_value=0)
    log.info("BLM MLRS solar ROW cases by state/status:\n%s", summ.to_string())
    fields = {"case_id": "MLRS case serial number", "legacy_case_id": "LR2000 legacy serial number",
              "project_name": "case name in MLRS (often blank)", "customer": "applicant or holder (one customer per record)",
              "customer_role": "customer relationship (Applicant, Holder/billee, ...)", "case_type": "BLM product (e.g. Solar Development Grant, Solar Site Test)",
              "case_type_code": "MLRS case type number", "commodity": "MLRS commodity", "status": "case disposition (Authorized, Pending, Interim, Closed)",
              "active": "true if status is Authorized, Pending or Interim", "status_date": "disposition date (UTC)",
              "field_office": "BLM jurisdiction office", "state": "state", "acres": "acres recorded in MLRS",
              "mw": "MW as stated in the MLRS case name (e.g. 'Sunbeam Ridge Solar LLC, 1338MW'); null when the name states none. MLRS has no MW field",
              "mw_est_low": "rough MW estimate = acres / 7 (SCOPE rule of thumb; Solar Development grants/leases only)",
              "mw_est_high": "rough MW estimate = acres / 5", "geom_source": "MLRS geometry source (MIGRATE, LLD/CLS)",
              "centroid_lat": "representative point latitude", "centroid_lon": "representative point longitude"}
    common = [
        "Polygons are BLM's geocoding of each case's legal land description to PLSS, often to whole sections or aliquots; they show where a case sits, not the project footprint.",
        "MLRS has no MW field. mw is parsed from the case name text where the applicant wrote it (not verified; may be AC or DC); mw_est_low/high are acreage-based estimates (5 to 7 acres per MW) and are not project data.",
        "Includes all solar-commodity ROW case types (development grants, site and project-area testing, leases, related transmission and access). Filter on case_type for development cases.",
        f"{n_nogeom} case(s) had no mapped geometry in MLRS; they are listed in blm_solar_row_cases.csv only.",
        "Data reflect MLRS as published on the BLM hub at retrieval; check MLRS (mlrs.blm.gov) for current status before relying on any case.",
    ]
    src = "https://nlsdbpubgis.blm.gov/arcgishub/rest/services/HUB/BLM_Natl_MLRS_LUA_ROW/FeatureServer/0"
    base = {"source_name": "BLM Mineral and Land Records System (MLRS), BLM Natl MLRS Land Use Authorization - Rights of Way, filtered to commodity SOLAR ENERGY FACILITIES",
            "source_url": src, "retrieved": raw.get("retrieved") or retrieved_date(p), "fields": fields}
    manifest.append({**base, "layer": "blm_solar_row_cases", "path": "data/processed/infra/blm_solar_row_cases.geojson",
                     "record_count": int(len(act)),
                     "counts_by_state_status": {s: {k: int(v) for k, v in r.items() if v} for s, r in summ.iterrows()},
                     "caveats": ["Active cases only (Authorized, Pending, Interim)."] + common})
    manifest.append({**base, "layer": "blm_solar_row_cases_closed", "path": "data/processed/infra/blm_solar_row_cases_closed.geojson",
                     "record_count": int(len(closed)), "caveats": ["Closed cases (rejected, withdrawn, relinquished, expired or terminated); useful history of where developers have tried."] + common})
    manifest.append({**base, "layer": "blm_solar_row_cases_table", "path": "data/processed/infra/blm_solar_row_cases.csv",
                     "record_count": int(len(flat)), "caveats": ["All cases, active and closed, including those without geometry; use centroid_lat/lon for points."] + common})


# ---------------------------------------------------------------- Data centers
def process_dc(states, manifest):
    p = RAW / "osm" / "osm_data_centers.json"
    d = json.loads(p.read_text())
    rows = []
    for e in d.get("elements", []):
        t = e.get("tags", {})
        if e["type"] == "node":
            lon, lat = e.get("lon"), e.get("lat")
        else:
            c = e.get("center") or {}
            lon, lat = c.get("lon"), c.get("lat")
        if lon is None:
            continue
        rows.append({"id": f"osm_{e['type']}_{e['id']}", "name": t.get("name"), "operator": t.get("operator"),
                     "osm_tag": "telecom=" + t["telecom"] if t.get("telecom") else "building=" + t.get("building", ""),
                     "city": t.get("addr:city"), "geometry": Point(lon, lat)})
    g = gpd.GeoDataFrame(rows, geometry="geometry", crs=4326)
    g["state"] = assign_state(g, states)
    g = g[g["state"].notna()]
    write_geojson(g, "data_centers_osm")
    manifest.append({
        "layer": "data_centers_osm", "path": "data/processed/infra/data_centers_osm.geojson",
        "source_name": "OpenStreetMap features tagged telecom=data_center or building=data_center (Overpass API)",
        "source_url": "https://overpass-api.de/", "retrieved": d.get("retrieved") or retrieved_date(p), "record_count": int(len(g)),
        "counts_by_state": {k: int(v) for k, v in g["state"].value_counts().items()},
        "fields": {"id": "OSM element id", "name": "OSM name", "operator": "OSM operator", "osm_tag": "tag that matched",
                   "city": "OSM addr:city", "state": "state"},
        "caveats": ["Volunteer-mapped and incomplete; many data centers are unmapped or unnamed, and one campus can appear as several buildings. No capacity (MW) data. Use as context only."],
    })


# ---------------------------------------------------------------- main
LAYERS = ["power_plants", "fiber", "water_stress", "roads_major", "blm_solar_row_cases", "data_centers_osm", "az_ama_ina"]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--force", action="store_true", help="rebuild even if outputs exist")
    a = ap.parse_args()
    setup_logging()
    mpath = OUT / "MANIFEST.json"
    if not a.force and mpath.exists() and all((OUT / f"{n}.geojson").exists() for n in LAYERS):
        log.info("all infra outputs exist; skipping (use --force to rebuild)")
        return 0
    OUT.mkdir(parents=True, exist_ok=True)
    states = states_gdf()
    manifest = []
    process_plants(states, manifest)
    roads = process_roads(states, manifest)
    process_fiber(states, roads, manifest)
    process_water(states, manifest)
    process_ama(manifest)
    process_row(states, manifest)
    process_dc(states, manifest)
    # SPEC: a list of {layer, path, source_name, source_url, retrieved, record_count, fields, caveats}
    mpath.write_text(json.dumps(manifest, indent=2, default=str))
    log.info("wrote %s (%d layers)", mpath.relative_to(ROOT), len(manifest))
    return 0


if __name__ == "__main__":
    sys.exit(main())

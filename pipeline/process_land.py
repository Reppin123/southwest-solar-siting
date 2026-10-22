# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pyogrio==0.10.0",
#   "geopandas==1.0.1",
#   "shapely==2.0.6",
#   "pyarrow==18.1.0",
#   "rasterio==1.4.3",
#   "numpy==2.1.3",
#   "pandas==2.2.3",
#   "pillow==11.0.0",
# ]
# ///
"""Process raw land data (from fetch_land.py) into the land contract layers.

Outputs in data/processed/land/ (all EPSG:4326; area math in EPSG:5070):
  admin_states.geojson, admin_counties.geojson
  blm_solar_available.geojson (+ .gpkg), solar_energy_zones.geojson
  ownership.gpkg (layer "ownership", full resolution) + ownership.geojson (simplified)
  exclusions/<constraint>.geojson (simplified, field kind = hard|soft) + exclusions_full.gpkg
  ghi.tif (kWh/m2/day), slope.tif (percent), ghi_overlay.png, slope_overlay.png (EPSG:3857 overlays)
  MANIFEST.json

Each stage skips if its outputs exist, unless --force. Use --only to run some stages.
"""
import argparse
import datetime as dt
import glob
import json
import logging
import math
import sys
import warnings
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pyogrio
import rasterio
from rasterio import features
from rasterio.enums import Resampling
from rasterio.transform import from_origin
from rasterio.warp import reproject, transform_bounds
from shapely import make_valid
from shapely.geometry import box, shape

warnings.filterwarnings("ignore", category=RuntimeWarning)
# FileGDB polygons follow the Esri ring convention; this avoids very slow ring re-organisation on big multipolygons
pyogrio.set_gdal_config_options({"OGR_ORGANIZE_POLYGONS": "ONLY_CCW"})
warnings.filterwarnings("ignore", message=".*More than one layer found.*")

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "land"
OUT = ROOT / "data" / "processed" / "land"
EXC = OUT / "exclusions"
LOG = ROOT / "logs" / "land.log"
STATE_FIPS = {"06": "CA", "04": "AZ", "32": "NV", "35": "NM", "49": "UT"}
STATE_NAMES = {"California": "CA", "Arizona": "AZ", "Nevada": "NV", "New Mexico": "NM", "Utah": "UT"}
BBOX = (-124.6, 31.2, -102.9, 42.1)
ALBERS = "EPSG:5070"
M2_PER_ACRE = 4046.8564224
MAX_APP_MB = 24.0
NODATA = -9999.0

log = logging.getLogger("process_land")
MANIFEST = {}

KB = "https://services1.arcgis.com/KbxwQRRfWyEYLgp4/arcgis/rest/services"
SRC = {
    "tiger_state": ("US Census Bureau cartographic boundary file 2024 (cb_2024_us_state_500k)",
                    "https://www2.census.gov/geo/tiger/GENZ2024/shp/cb_2024_us_state_500k.zip"),
    "tiger_county": ("US Census Bureau cartographic boundary file 2024 (cb_2024_us_county_500k)",
                     "https://www2.census.gov/geo/tiger/GENZ2024/shp/cb_2024_us_county_500k.zip"),
    "aiannh": ("US Census Bureau TIGER/Line 2024 American Indian / Alaska Native / Native Hawaiian Areas",
               "https://www2.census.gov/geo/tiger/TIGER2024/AIANNH/tl_2024_us_aiannh.zip"),
    "mil": ("US Census Bureau TIGER/Line 2024 Military Installations",
            "https://www2.census.gov/geo/tiger/TIGER2024/MIL/tl_2024_us_mil.zip"),
    "uac": ("US Census Bureau TIGER/Line 2024 Urban Areas (2020 Census)",
            "https://www2.census.gov/geo/tiger/TIGER2024/UAC20/tl_2024_us_uac20.zip"),
    "peis": ("BLM 2024 Western Solar Plan (Utility-Scale Solar Energy Development PEIS) Record of Decision geodatabase, layer Solar_PEIS_ROD_Approved_Plan",
             "https://blmsolar.anl.gov/maps/data/2024-solar-peis/BLM-National-Solar-PEIS-ROD.gdb.zip"),
    "sez": ("BLM National Rights-of-Way Planning Tool Energy Designations, layer 10 BLM Solar Energy Zone",
            f"{KB}/Energy_Designations/FeatureServer/10"),
    "drecp_dfa": ("BLM Energy Designations, layer 12 BLM DRECP Development Focus Area (DFA)",
                  f"{KB}/Energy_Designations/FeatureServer/12"),
    "drecp_variance": ("BLM Energy Designations, layer 13 BLM DRECP Variance Land",
                       f"{KB}/Energy_Designations/FeatureServer/13"),
    "sma": ("BLM National Surface Management Agency Area Polygons (SMA_WM.gdb, BLM EGIS hub item 6bf2e737c59d4111be92420ee5ab0b46)",
            "https://www.arcgis.com/sharing/rest/content/items/6bf2e737c59d4111be92420ee5ab0b46/data"),
    "nwps": ("Wilderness Connect (University of Montana) National Wilderness Preservation System boundaries",
             "https://services1.arcgis.com/ERdCHt0sNM6dENSD/arcgis/rest/services/Wilderness_Areas_in_the_United_States/FeatureServer/0"),
    "wsa": ("BLM National NLCS Wilderness Study Areas Polygons",
            f"{KB}/BLM_Natl_NLCS_Wilderness_Study_Areas_Polygons/FeatureServer/3"),
    "nca": ("BLM National NLCS National Monuments and National Conservation Areas Polygons",
            f"{KB}/BLM_Natl_NLCS_National_Monuments_National_Conservation_Areas_Polygons/FeatureServer/0"),
    "acec": ("BLM National Areas of Critical Environmental Concern, ACEC Designated Polygons",
             "https://gis.blm.gov/arcgis/rest/services/lands/BLM_Natl_ACEC/MapServer/0"),
    "ch": ("USFWS Critical Habitat, Final Critical Habitat Features (polygons)",
           "https://services.arcgis.com/QVENGdaPbd4LUkLV/arcgis/rest/services/USFWS_Critical_Habitat/FeatureServer/0"),
    "fema": ("FEMA National Flood Hazard Layer (NFHL), layer 28 Flood Hazard Zones, zones A/AE/AH/AO/V/VE",
             "https://hazards.fema.gov/arcgis/rest/services/public/NFHL/MapServer/28"),
    "nwi": ("USFWS National Wetlands Inventory map service, wetlands >= 40 acres",
            "https://fwspublicservices.wim.usgs.gov/wetlandsmapservice/rest/services/Wetlands/MapServer/0"),
    "ghi": ("NREL NSRDB Physical Solar Model v3 GHI multi-year (1998-2016) annual average, 0.04 deg (nsrdbv3_ghi.zip; Internet Archive copy of NREL's file)",
            "https://web.archive.org/web/20240926182851id_/https://www.nrel.gov/gis/assets/data/nsrdbv3_ghi.zip"),
    "terrain": ("AWS Open Data Terrain Tiles (terrarium encoding, zoom 11), built mainly from USGS 3DEP / NED elevation",
                "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"),
}


# ---------------------------------------------------------------- helpers
def setup_logging():
    LOG.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s process_land %(levelname)s %(message)s",
                        handlers=[logging.FileHandler(LOG), logging.StreamHandler(sys.stdout)])


def retrieved(path_glob):
    paths = glob.glob(str(path_glob))
    if not paths:
        return None
    t = max(Path(p).stat().st_mtime for p in paths)
    return dt.date.fromtimestamp(t).isoformat()


def add_manifest(layer, path, src_keys, raw_glob, count, fields, caveats, **extra):
    names = "; ".join(SRC[k][0] for k in src_keys)
    urls = "; ".join(SRC[k][1] for k in src_keys)
    MANIFEST[layer] = dict(layer=layer, path=str(Path(path).relative_to(ROOT)), source_name=names,
                           source_url=urls, retrieved=retrieved(raw_glob), record_count=int(count),
                           fields=fields, caveats=caveats, **extra)


def load_manifest():
    p = OUT / "MANIFEST.json"
    if p.exists():
        for e in json.loads(p.read_text()):
            MANIFEST[e["layer"]] = e


def save_manifest():
    (OUT / "MANIFEST.json").write_text(json.dumps(sorted(MANIFEST.values(), key=lambda e: e["layer"]), indent=2))


_STATES = None


def states():
    global _STATES
    if _STATES is None:
        st = gpd.read_file(RAW / "tiger" / "cb_2024_us_state_500k.zip")
        st = st[st["STATEFP"].isin(STATE_FIPS)].to_crs(4326)
        st["state"] = st["STATEFP"].map(STATE_FIPS)
        _STATES = st[["state", "STATEFP", "NAME", "geometry"]].rename(columns={"STATEFP": "state_fips", "NAME": "name"}).reset_index(drop=True)
    return _STATES


def five_union():
    return states().union_all()


def read_arcgis(name):
    feats, seen = [], set()
    for f in sorted(glob.glob(str(RAW / "arcgis" / name / "*.geojson"))):
        js = json.loads(Path(f).read_text())
        for ft in js.get("features", []):
            props = ft.get("properties") or {}
            oid = ft.get("id", props.get("OBJECTID", props.get("ogc_fid", props.get("OBJECTID_1"))))
            if oid is not None:
                if oid in seen:
                    continue
                seen.add(oid)
            if ft.get("geometry"):
                feats.append(ft)
    if not feats:
        return gpd.GeoDataFrame(geometry=[], crs=4326)
    g = gpd.GeoDataFrame.from_features(feats, crs=4326)
    g["geometry"] = make_valid(g.geometry.values)
    return g


def polys_only(g):
    g = g.explode(index_parts=False)
    g = g[g.geometry.geom_type.isin(["Polygon", "MultiPolygon"]) & ~g.geometry.is_empty]
    return g


def clip_states(g, attach_state=True):
    """Clip to the five states and add a `state` column.

    Explodes to single polygons first; parts fully inside a state are kept unchanged and only
    parts crossing a state line are intersected (much faster than overlay on huge multipolygons)."""
    import shapely
    g = polys_only(g.to_crs(4326)).reset_index(drop=True)
    g["geometry"] = make_valid(g.geometry.values)
    g = polys_only(g).reset_index(drop=True)
    st = states()
    out = []
    for _, srow in st.iterrows():
        sg = srow.geometry
        shapely.prepare(sg)
        cand = g.iloc[g.sindex.query(sg, predicate="intersects")]
        if cand.empty:
            continue
        inside = shapely.contains_properly(sg, cand.geometry.values)
        keep = cand[inside].copy()
        edge = cand[~inside].copy()
        if len(edge):
            edge["geometry"] = shapely.intersection(edge.geometry.values, sg)
            keep = pd.concat([keep, edge])
        keep["state"] = srow.state
        out.append(keep)
    if not out:
        return gpd.GeoDataFrame(columns=list(g.columns) + ["state"], geometry="geometry", crs=4326)
    res = gpd.GeoDataFrame(pd.concat(out, ignore_index=True), geometry="geometry", crs=4326)
    res = polys_only(res)
    if not attach_state:
        res = res.drop(columns="state")
    return res.reset_index(drop=True)


def add_acres(g):
    g["acres"] = (g.to_crs(ALBERS).area / M2_PER_ACRE).round(1)
    return g


def prune(geoms, min_acres):
    """Drop interior rings and polygon parts smaller than min_acres (approximate, lat-corrected deg2)."""
    import shapely
    from shapely.geometry import MultiPolygon, Polygon

    def deg2(ring_or_poly, lat):
        return abs(shapely.area(ring_or_poly)) * 111320.0 ** 2 * math.cos(math.radians(lat)) / M2_PER_ACRE

    def fix_poly(p):
        lat = p.centroid.y
        if deg2(p, lat) < min_acres:
            return None
        holes = [r for r in p.interiors if deg2(Polygon(r), lat) >= min_acres]
        return Polygon(p.exterior, holes)

    out = []
    for gm in geoms:
        parts = [gm] if gm.geom_type == "Polygon" else list(getattr(gm, "geoms", []))
        kept = [q for q in (fix_poly(p) for p in parts if p.geom_type == "Polygon") if q is not None]
        out.append(None if not kept else (kept[0] if len(kept) == 1 else MultiPolygon(kept)))
    return out


# (simplify tolerance deg, prune holes/parts below this many acres) tried in order until the file fits
APP_STEPS = [(0.0, 0), (0.0005, 0), (0.0005, 2), (0.001, 5), (0.001, 10), (0.002, 20), (0.003, 40),
             (0.005, 80), (0.01, 160), (0.02, 320), (0.03, 640)]


def write_vector(g, geojson_path, gpkg_path=None, gpkg_layer=None, tol=0.0, dissolve_by=None):
    """Write full-res to gpkg (optional) and an app-facing GeoJSON under MAX_APP_MB.

    The GeoJSON is simplified with a topology-preserving simplifier (per geometry), and if needed
    holes and parts below a size threshold are dropped; settings step up until the file fits.
    Returns a text description of what was applied."""
    geojson_path = Path(geojson_path)
    geojson_path.parent.mkdir(parents=True, exist_ok=True)
    if gpkg_path:
        pyogrio.write_dataframe(g, gpkg_path, layer=gpkg_layer, driver="GPKG")
    app = g
    if dissolve_by:
        app = g.dissolve(by=dissolve_by, as_index=False)
    steps = [(max(t, tol), a) for t, a in APP_STEPS if t >= tol or t == 0]
    for t, min_ac in steps:
        a = app.copy()
        if min_ac:
            a["geometry"] = gpd.GeoSeries(prune(a.geometry.values, min_ac), index=a.index, crs=a.crs)
            a = a[a.geometry.notna()]
        if t > 0:
            a["geometry"] = a.geometry.simplify(t, preserve_topology=True)
        a = a[~a.geometry.is_empty]
        if geojson_path.exists():
            geojson_path.unlink()
        pyogrio.write_dataframe(a, geojson_path, driver="GeoJSON", COORDINATE_PRECISION=5)
        mb = geojson_path.stat().st_size / 1e6
        desc = f"simplify {t} deg" + (f", holes and parts under {min_ac} acres removed" if min_ac else "")
        if mb <= MAX_APP_MB:
            log.info("wrote %s (%d features, %.1f MB, %s)", geojson_path.name, len(a), mb, desc)
            return desc
        log.info("%s is %.1f MB with %s; stepping up", geojson_path.name, mb, desc)
    log.warning("%s still %.1f MB after all steps", geojson_path.name, mb)
    return desc + f" (file still {mb:.0f} MB)"


def need(paths, force):
    return force or not all(Path(p).exists() for p in paths)


# ---------------------------------------------------------------- stages
def stage_admin(force):
    a, c = OUT / "admin_states.geojson", OUT / "admin_counties.geojson"
    if not need([a, c], force):
        return
    st = states()
    pyogrio.write_dataframe(st, a, driver="GeoJSON")
    co = gpd.read_file(RAW / "tiger" / "cb_2024_us_county_500k.zip")
    co = co[co["STATEFP"].isin(STATE_FIPS)].to_crs(4326)
    co["state"] = co["STATEFP"].map(STATE_FIPS)
    co = co.rename(columns={"NAME": "county", "GEOID": "geoid", "NAMELSAD": "county_full"})[["geoid", "state", "county", "county_full", "geometry"]]
    co = add_acres(co)
    pyogrio.write_dataframe(co, c, driver="GeoJSON")
    add_manifest("admin_states", a, ["tiger_state"], RAW / "tiger" / "cb_2024_us_state_500k.zip", len(st),
                 {"state": "two-letter state code", "state_fips": "state FIPS", "name": "state name"},
                 "Cartographic boundary (1:500k) version of TIGER states; coastline generalised, offshore water removed.")
    add_manifest("admin_counties", c, ["tiger_county"], RAW / "tiger" / "cb_2024_us_county_500k.zip", len(co),
                 {"geoid": "5-digit county FIPS", "state": "state code", "county": "county name",
                  "county_full": "name with LSAD (e.g. 'Riverside County')", "acres": "area, acres (EPSG:5070)"},
                 "Cartographic boundary (1:500k) version of TIGER counties.")
    log.info("admin: %d states, %d counties", len(st), len(co))


def stage_blm(force):
    avail, sezp = OUT / "blm_solar_available.geojson", OUT / "solar_energy_zones.geojson"
    if not need([avail, sezp], force):
        return
    gdb = RAW / "BLM_Natl_Solar_PEIS_ROD.gdb"
    names = ",".join(f"'{n}'" for n in STATE_NAMES)
    # category summary for the caveat text
    attrs = pyogrio.read_dataframe(gdb, layer="Solar_PEIS_ROD_Approved_Plan", read_geometry=False, use_arrow=True,
                                   where=f"State IN ({names})")
    summ = (attrs.groupby(["State", "ApprovedPlan"])["Shape_Area"].sum() / M2_PER_ACRE).round(0)
    log.info("Western Solar Plan ROD categories (acres):\n%s", summ.to_string())
    # use_arrow=False so GDAL linearises curved (MultiSurface) geometries
    g = pyogrio.read_dataframe(gdb, layer="Solar_PEIS_ROD_Approved_Plan", use_arrow=False,
                               where=f"ApprovedPlan = 'Available' AND State IN ({names})")
    g["geometry"] = make_valid(g.geometry.values)
    parts = []
    for st_name, grp in g.groupby("State"):
        u = grp.geometry.buffer(0).union_all()
        d = gpd.GeoDataFrame({"state": [STATE_NAMES[st_name]]}, geometry=[u], crs=g.crs).explode(index_parts=False)
        parts.append(d)
    av = pd.concat(parts, ignore_index=True)
    av["category"] = "Available (2024 Western Solar Plan ROD)"
    av["basis"] = "Western Solar Plan ROD Approved Plan = Available"
    av = av.to_crs(4326)

    # California desert (CDCA) lands follow the DRECP land use plan amendment, not the Western Solar Plan
    dfa = read_arcgis("drecp_dfa")
    dfa["category"] = "DRECP Development Focus Area (CA)"
    dfa["basis"] = "DRECP LUPA DFA: " + dfa.get("technology", pd.Series("", index=dfa.index)).fillna("").astype(str)
    var = read_arcgis("drecp_variance")
    var["category"] = "DRECP Variance Land (CA)"
    var["basis"] = "DRECP LUPA variance land: open to application through the variance process"
    ca = pd.concat([dfa[["category", "basis", "geometry"]], var[["category", "basis", "geometry"]]], ignore_index=True)
    ca = gpd.GeoDataFrame(ca, geometry="geometry", crs=4326)
    log.info("DRECP DFA acres %.0f, variance acres %.0f",
             dfa.to_crs(ALBERS).area.sum() / M2_PER_ACRE, var.to_crs(ALBERS).area.sum() / M2_PER_ACRE)
    ca = clip_states(ca)
    ca = ca[ca["state"] == "CA"]
    allg = pd.concat([clip_states(av[["category", "basis", "geometry"]]), ca], ignore_index=True)
    allg = gpd.GeoDataFrame(allg, geometry="geometry", crs=4326)
    allg = add_acres(allg)
    allg = allg[allg["acres"] >= 1].sort_values(["state", "acres"], ascending=[True, False]).reset_index(drop=True)
    allg.insert(0, "id", [f"BLMSA-{s}-{i:05d}" for i, s in enumerate(allg["state"])])
    allg["blm_solar_available"] = True

    # SEZs
    sez = read_arcgis("sez")
    sez = sez[sez["stateoffice"].isin(STATE_NAMES)]
    sez["state"] = sez["stateoffice"].map(STATE_NAMES)
    sez = sez.dissolve(by=["zone_name", "state", "status"], as_index=False, aggfunc={"comments": lambda s: "; ".join(sorted({c for c in s if c}))})
    sez = sez.rename(columns={"zone_name": "sez_name", "comments": "notes"})
    sez = add_acres(sez)
    sez.insert(0, "id", [f"SEZ-{i:03d}" for i in range(len(sez))])
    sez = sez[["id", "sez_name", "state", "status", "notes", "acres", "geometry"]]

    # tag available polygons with the SEZ they fall in (developable part)
    dev = sez[sez["status"] == "Developable"][["sez_name", "geometry"]]
    j = gpd.sjoin(allg[["id", "geometry"]], dev, how="left", predicate="intersects")
    allg["sez_name"] = allg["id"].map(j.groupby("id")["sez_name"].agg(lambda s: "; ".join(sorted({x for x in s if isinstance(x, str)}))))
    allg["sez_name"] = allg["sez_name"].replace("", None)

    gp = OUT / "blm_solar_available.gpkg"
    tol = write_vector(allg, avail, gp, "blm_solar_available", tol=0.0)
    pyogrio.write_dataframe(sez, sezp, driver="GeoJSON")
    cats = allg.groupby(["state", "category"])["acres"].sum().round(0)
    add_manifest("blm_solar_available", avail, ["peis", "drecp_dfa", "drecp_variance"], RAW / "BLM_Natl_Solar_PEIS_ROD.gdb", len(allg),
                 {"id": "polygon id", "state": "state code", "category": "availability category",
                  "basis": "planning basis", "acres": "polygon area, acres (EPSG:5070)",
                  "blm_solar_available": "always true in this layer", "sez_name": "Solar Energy Zone(s) the polygon touches, if any"},
                 ("Western Solar Plan (2024 ROD, Approved Plan) polygons with ApprovedPlan = 'Available', dissolved per state and split into "
                  "contiguous parts. 'Available' means open to right-of-way applications, not approved or free of conflicts. In California most "
                  "BLM desert land is labelled 'DRECP/CDCA' in the ROD because it is governed by the DRECP land use plan amendment; for those "
                  "lands this layer adds BLM DRECP Development Focus Areas and Variance Lands from the BLM Energy Designations service. "
                  "Variance lands need a variance process and carry more risk than DFAs. Polygons under 1 acre were dropped. "
                  f"GeoJSON for the map: {tol}; full resolution in blm_solar_available.gpkg. "
                  "Acres by state/category: " + "; ".join(f"{s} {c}: {int(v):,}" for (s, c), v in cats.items()) + ". "
                  "Policy note: Interior's 2025 orders added senior review for solar and wind on federal land; availability here is the "
                  "land-use-plan status only."),
                 approved_plan_acres_by_category={f"{s}|{c}": int(v) for (s, c), v in summ.items()},
                 app_simplification=tol)
    add_manifest("solar_energy_zones", sezp, ["sez"], RAW / "arcgis" / "sez" / "*.geojson", len(sez),
                 {"id": "id", "sez_name": "Solar Energy Zone name", "state": "state code",
                  "status": "Developable or Non-developable (BLM-designated non-development areas inside the SEZ)",
                  "notes": "BLM comments, e.g. reason for non-development", "acres": "acres (EPSG:5070)"},
                 "BLM Solar Energy Zones (2012 PEIS plus later SEZs as carried in the BLM Energy Designations service). Non-developable "
                 "parts are washes, playas, wetlands and similar features BLM excluded inside each SEZ.")
    log.info("blm: %d available polygons; %d SEZ records: %s", len(allg), len(sez), sorted(sez["sez_name"].unique()))


AGENCY_CATEGORY = {"BLM": "BLM", "USFS": "USFS", "NPS": "NPS", "BIA": "Tribal", "ST": "State", "PVT": "Private", "UND": "Private"}


def stage_ownership(force):
    gp, gj = OUT / "ownership.gpkg", OUT / "ownership.geojson"
    if not need([gp, gj], force):
        return
    st = states().to_crs(3857)
    bb = tuple(st.total_bounds)
    g = pyogrio.read_dataframe(RAW / "SMA_WM.gdb", layer="SurfaceManagementAgency", bbox=bb, use_arrow=False,
                               columns=["ADMIN_UNIT_NAME", "ADMIN_DEPT_CODE", "ADMIN_AGENCY_CODE"])
    log.info("ownership: %d SMA features in bbox", len(g))
    g = g.to_crs(4326)
    cat = g["ADMIN_AGENCY_CODE"].map(AGENCY_CATEGORY)
    cat = cat.where(cat.notna(), np.where(g["ADMIN_DEPT_CODE"] == "DOD", "DOD", "Other"))
    g["category"] = cat
    g["agency"] = g["ADMIN_AGENCY_CODE"].fillna("UNK")
    g["agency_dept"] = g["ADMIN_DEPT_CODE"]
    g["unit_name"] = g["ADMIN_UNIT_NAME"]
    g = g[["agency", "agency_dept", "category", "unit_name", "geometry"]]
    g = clip_states(g)
    g = add_acres(g)
    g = g[g["acres"] > 0.5].reset_index(drop=True)
    pyogrio.write_dataframe(g, gp, layer="ownership", driver="GPKG")
    tot = g.groupby(["state", "category"])["acres"].sum().round(0)
    log.info("ownership acres by state/category:\n%s", tot.to_string())
    # SMA polygons are already merged per agency, so the map copy keeps parts (no costly dissolve)
    app = g[g["acres"] >= 40][["state", "category", "agency", "acres", "geometry"]]
    tol = write_vector(app, gj, tol=0.001)
    add_manifest("ownership", gp, ["sma"], RAW / "SMA_WM.gdb", len(g),
                 {"agency": "SMA ADMIN_AGENCY_CODE (BLM, USFS, NPS, ARMY, USAF, NAVY, USMC, BIA, ST, PVT, UND, FWS, USBR, DOE, LG, ...)",
                  "agency_dept": "SMA ADMIN_DEPT_CODE", "category": "BLM, USFS, NPS, DOD, Tribal, State, Private, Other",
                  "unit_name": "SMA administrative unit name", "state": "state code", "acres": "acres (EPSG:5070)"},
                 ("SMA shows the surface managing agency, not title. BIA lands are mapped to Tribal. ST = state lands (incl. state trust) mapped to "
                  "State. PVT and UND (private or unknown) are both mapped to Private. FWS, USBR, DOE, local government and other federal are "
                  "Other. Split-estate minerals are not shown. "
                  f"ownership.geojson keeps state, category, agency and acres per part, parts under 40 acres dropped, map copy: {tol}. "
                  "Acres by state/category: " + "; ".join(f"{s} {c}: {int(v):,}" for (s, c), v in tot.items())),
                 app_geojson=str(gj.relative_to(ROOT)), app_simplification=tol)
    MANIFEST["ownership"]["record_count_app_geojson"] = int(len(app))
    # NPS hard exclusion from SMA
    nps = g[g["category"] == "NPS"].copy()
    nps["kind"] = "hard"
    nps["name"] = nps["unit_name"]
    nps["source"] = "BLM SMA (NPS)"
    write_exclusion("nps", nps[["kind", "name", "source", "state", "acres", "geometry"]], ["sma"], RAW / "SMA_WM.gdb",
                    "National Park Service lands from BLM SMA. Not available for solar ROW.", tol=0.0005)


EXCL_FIELDS = {"kind": "hard or soft", "constraint": "constraint name (file name)", "name": "feature name where known",
               "subtype": "feature type or status", "source": "source dataset", "state": "state code", "acres": "acres (EPSG:5070)"}


def write_exclusion(name, g, src_keys, raw_glob, caveat, tol=0.0005, dissolve_by=None):
    g = g.copy()
    g["constraint"] = name
    for c in ["name", "subtype", "source"]:
        if c not in g:
            g[c] = None
    g = g[["kind", "constraint", "name", "subtype", "source", "state", "acres", "geometry"]]
    path = EXC / f"{name}.geojson"
    pyogrio.write_dataframe(g, OUT / "exclusions_full.gpkg", layer=name, driver="GPKG")
    used = write_vector(g, path, tol=tol, dissolve_by=dissolve_by)
    kinds = g["kind"].value_counts().to_dict()
    add_manifest(f"exclusion_{name}", path, src_keys, raw_glob, len(g), EXCL_FIELDS,
                 caveat + f" GeoJSON map copy: {used}" + (f" and dissolved by {dissolve_by}" if dissolve_by else "")
                 + f"; full resolution in exclusions_full.gpkg layer '{name}'.",
                 kind_counts={k: int(v) for k, v in kinds.items()}, app_simplification=used,
                 total_acres=int(g["acres"].sum()))


def stage_exclusions(force):
    EXC.mkdir(parents=True, exist_ok=True)
    targets = [EXC / f"{n}.geojson" for n in ["wilderness", "nca_acec", "critical_habitat", "flood_zone_a", "tribal", "military", "wetlands", "urban"]]
    if not need(targets, force):
        return

    if need([EXC / "wilderness.geojson"], force):
        log.info("exclusion %s", "wilderness")
        # wilderness: NWPS (all agencies) + BLM wilderness study areas, both hard
        w = read_arcgis("wilderness_nwps")
        w = gpd.GeoDataFrame({"name": w["NAME"], "subtype": "Designated wilderness (" + w["Agency"].fillna("?") + ")",
                              "source": "Wilderness Connect NWPS", "geometry": w.geometry}, crs=4326)
        wsa = read_arcgis("wsa_blm")
        wsa = gpd.GeoDataFrame({"name": wsa["NLCS_NAME"], "subtype": "BLM Wilderness Study Area",
                                "source": "BLM NLCS WSA", "geometry": wsa.geometry}, crs=4326)
        ww = add_acres(clip_states(pd.concat([w, wsa], ignore_index=True).pipe(gpd.GeoDataFrame, crs=4326)))
        ww["kind"] = "hard"
        write_exclusion("wilderness", ww, ["nwps", "wsa"], RAW / "arcgis" / "wilderness_nwps" / "*.geojson",
                        "Designated wilderness (all agencies) and BLM Wilderness Study Areas. Both are closed to solar ROWs.")

    if need([EXC / "nca_acec.geojson"], force):
        log.info("exclusion %s", "nca_acec")
        # NM/NCA (hard) + ACEC (soft)
        n = read_arcgis("nlcs_nm_nca")
        n = gpd.GeoDataFrame({"name": n["NCA_NAME"], "subtype": n["sma_code"].fillna("NLCS"), "source": "BLM NLCS NM/NCA",
                              "kind": "hard", "geometry": n.geometry}, crs=4326)
        a = read_arcgis("acec")
        a = gpd.GeoDataFrame({"name": a.get("ACEC_NAME"), "subtype": "ACEC", "source": "BLM ACEC designated", "kind": "soft",
                              "geometry": a.geometry}, crs=4326)
        na = add_acres(clip_states(pd.concat([n, a], ignore_index=True).pipe(gpd.GeoDataFrame, crs=4326)))
        write_exclusion("nca_acec", na, ["nca", "acec"], RAW / "arcgis" / "acec" / "*.geojson",
                        "BLM National Monuments and National Conservation Areas are hard (excluded from solar under the Western Solar Plan). "
                        "ACECs are soft here as the brief asks, but note the 2024 Western Solar Plan excludes ACECs from solar on BLM land; "
                        "on BLM land use blm_solar_available as the controlling layer.")

    if need([EXC / "critical_habitat.geojson"], force):
        log.info("exclusion %s", "critical_habitat")
        # critical habitat (hard)
        c = read_arcgis("critical_habitat")
        c = gpd.GeoDataFrame({"name": c["comname"], "subtype": c["sciname"], "source": "USFWS final critical habitat",
                              "kind": "hard", "geometry": c.geometry}, crs=4326)
        c = add_acres(clip_states(c))
        write_exclusion("critical_habitat", c, ["ch"], RAW / "arcgis" / "critical_habitat" / "*.geojson",
                        "Final designated critical habitat polygons only (proposed and line features not included). Species ranges and "
                        "occupied habitat outside designations (e.g. much desert tortoise habitat) are not captured.",
                        tol=0.0005)

    if need([EXC / "flood_zone_a.geojson"], force):
        log.info("exclusion %s", "flood_zone_a")
        # FEMA flood A/V (hard)
        f = read_arcgis("fema_flood_av")
        dfirms = sorted(set(f["DFIRM_ID"].dropna()))
        f = gpd.GeoDataFrame({"name": f["DFIRM_ID"], "subtype": f["FLD_ZONE"], "source": "FEMA NFHL",
                              "kind": "hard", "geometry": f.geometry}, crs=4326)
        f = add_acres(clip_states(f))
        write_exclusion("flood_zone_a", f, ["fema"], RAW / "arcgis" / "fema_flood_av" / "*.geojson",
                        "FEMA Special Flood Hazard Area zones A, AE, AH, AO, V, VE from the NFHL service (geometry generalised server-side to "
                        "~30 m). A99 and AR (levee-protected) are not included. NFHL does not cover every county; unmapped areas (common in "
                        f"rural NV, UT, NM, AZ) are not flood-free. {len(dfirms)} FIRM study areas present.",
                        tol=0.0005, dissolve_by=["subtype", "state"])
        MANIFEST["exclusion_flood_zone_a"]["dfirm_ids_present"] = dfirms

    if need([EXC / "tribal.geojson"], force):
        log.info("exclusion %s", "tribal")
        # tribal (hard)
        t = gpd.read_file(RAW / "tiger" / "tl_2024_us_aiannh.zip")
        t = gpd.GeoDataFrame({"name": t["NAMELSAD"], "subtype": t["CLASSFP"], "source": "Census TIGER AIANNH 2024",
                              "kind": "hard", "geometry": t.geometry}, crs=t.crs)
        t = add_acres(clip_states(t))
        write_exclusion("tribal", t, ["aiannh"], RAW / "tiger" / "tl_2024_us_aiannh.zip",
                        "Reservations, off-reservation trust land and other Census tribal areas. Treated as hard for a BLM/private screen; "
                        "development on tribal land is possible only with the tribe as partner (BIA/tribal process, not BLM).")

    if need([EXC / "military.geojson"], force):
        log.info("exclusion %s", "military")
        # military (hard): TIGER military installations + SMA DOD
        m = gpd.read_file(RAW / "tiger" / "tl_2024_us_mil.zip")
        m = gpd.GeoDataFrame({"name": m["FULLNAME"], "subtype": "Military installation", "source": "Census TIGER MIL 2024",
                              "geometry": m.geometry}, crs=m.crs)
        parts = [m]
        gp = OUT / "ownership.gpkg"
        if gp.exists():
            d = pyogrio.read_dataframe(gp, layer="ownership", where="category = 'DOD'")
            parts.append(gpd.GeoDataFrame({"name": d["unit_name"], "subtype": "DOD surface management (" + d["agency"] + ")",
                                           "source": "BLM SMA (DOD)", "geometry": d.geometry}, crs=d.crs))
        m = add_acres(clip_states(pd.concat([p.to_crs(4326) for p in parts], ignore_index=True).pipe(gpd.GeoDataFrame, crs=4326)))
        m["kind"] = "hard"
        write_exclusion("military", m, ["mil", "sma"], RAW / "tiger" / "tl_2024_us_mil.zip",
                        "Military installations (TIGER) plus DOD-managed land (SMA). Military training routes, special use airspace and "
                        "DOD siting-clearinghouse review areas are not included; those affect tall structures and glare and need DOD consultation.")

    if need([EXC / "wetlands.geojson"], force):
        log.info("exclusion %s", "wetlands")
        # wetlands (soft, proxy)
        wl = read_arcgis("nwi_wetlands_40ac")
        wl = gpd.GeoDataFrame({"name": wl["ATTRIBUTE"], "subtype": wl["WETLAND_TYPE"], "source": "USFWS NWI (>= 40 acres)",
                               "kind": "soft", "geometry": wl.geometry}, crs=4326)
        wl = add_acres(clip_states(wl))
        write_exclusion("wetlands", wl, ["nwi"], RAW / "arcgis" / "nwi_wetlands_40ac" / "*.geojson",
                        "Proxy: only NWI polygons of 40 acres or more are included (full NWI is too heavy), so small wetlands, springs and "
                        "washes are missing. Includes lakes, ponds and riverine polygons as mapped by NWI. Soft constraint; site-level "
                        "delineation needed.", tol=0.0005, dissolve_by=["subtype", "state"])

    if need([EXC / "urban.geojson"], force):
        log.info("exclusion %s", "urban")
        # urban (hard)
        u = gpd.read_file(RAW / "tiger" / "tl_2024_us_uac20.zip")
        u = gpd.GeoDataFrame({"name": u["NAMELSAD20"], "subtype": "2020 Census urban area", "source": "Census TIGER UAC20",
                              "kind": "hard", "geometry": u.geometry}, crs=u.crs)
        u = add_acres(clip_states(u))
        write_exclusion("urban", u, ["uac"], RAW / "tiger" / "tl_2024_us_uac20.zip",
                        "2020 Census urban areas (>= 2,000 housing units or 5,000 people). Hard for utility-scale solar; data center sites "
                        "near urban edges may still be relevant.")


# ---------------------------------------------------------------- rasters
RES = 1 / 1200.0  # 3 arc-seconds (~92 m N-S, ~76 m E-W at 35N)


def out_grid():
    w = int(round((BBOX[2] - BBOX[0]) / RES))
    h = int(round((BBOX[3] - BBOX[1]) / RES))
    return from_origin(BBOX[0], BBOX[3], RES, RES), w, h


def state_mask(transform, shape_):
    """True inside the five states."""
    return features.geometry_mask(states().geometry, out_shape=shape_, transform=transform, invert=True)


def colorize(arr, stops, alpha=200):
    """arr float with nan; stops = [(value, (r,g,b,a or None))...] piecewise-linear."""
    out = np.zeros(arr.shape + (4,), dtype=np.uint8)
    vals = np.array([s[0] for s in stops], dtype=float)
    cols = np.array([s[1] for s in stops], dtype=float)
    ok = np.isfinite(arr)
    a = np.clip(arr, vals[0], vals[-1])
    for ch in range(4):
        out[..., ch] = np.interp(a, vals, cols[:, ch]).astype(np.uint8)
    out[~ok] = 0
    return out


def write_overlay(arr, src_transform, png_path, stops, max_width=3000):
    """Reproject a 4326 array to EPSG:3857 and write an RGBA PNG for map overlay; returns lat/lon bounds."""
    from PIL import Image
    left, bottom, right, top = transform_bounds(4326, 3857, *BBOX)
    width = max_width
    res = (right - left) / width
    height = int(math.ceil((top - bottom) / res))
    dst = np.full((height, width), np.nan, dtype=np.float32)
    dtf = from_origin(left, top, res, res)
    reproject(arr.astype(np.float32), dst, src_transform=src_transform, src_crs=4326, dst_transform=dtf, dst_crs=3857,
              src_nodata=np.nan, dst_nodata=np.nan, resampling=Resampling.average)
    # palette PNG (with alpha) keeps the overlay small for the browser
    Image.fromarray(colorize(dst, stops), "RGBA").quantize(colors=96, method=Image.Quantize.FASTOCTREE).save(png_path, optimize=True)
    lb = transform_bounds(3857, 4326, left, top - height * res, right, top)
    return {"west": lb[0], "south": lb[1], "east": lb[2], "north": lb[3], "crs_of_image": "EPSG:3857",
            "note": "image pixels are in Web Mercator; place with these lat/lon corner bounds (e.g. Leaflet imageOverlay)"}


GHI_STOPS = [(4.0, (49, 54, 149, 210)), (4.6, (69, 117, 180, 210)), (5.0, (171, 217, 233, 210)),
             (5.4, (254, 224, 144, 210)), (5.8, (253, 174, 97, 210)), (6.1, (244, 109, 67, 210)), (6.4, (165, 0, 38, 210))]
SLOPE_STOPS = [(0, (0, 0, 0, 0)), (2.99, (0, 0, 0, 0)), (3, (255, 237, 160, 120)), (5, (254, 178, 76, 170)),
               (10, (240, 59, 32, 190)), (20, (128, 0, 38, 210)), (40, (60, 0, 20, 220))]


def stage_ghi(force):
    tif, png = OUT / "ghi.tif", OUT / "ghi_overlay.png"
    if not need([tif, png], force):
        return
    src_path = RAW / "nsrdbv3_ghi" / "nsrdbv3_ghi" / "Annual GHI" / "nsrdb3_ghi.tif"
    with rasterio.open(src_path) as s:
        win = rasterio.windows.from_bounds(*BBOX, s.transform).round_offsets().round_lengths()
        a = s.read(1, window=win).astype(np.float32)
        tf = s.window_transform(win)
    a[a <= 0] = np.nan
    inside = state_mask(tf, a.shape)
    a[~inside] = np.nan
    prof = dict(driver="GTiff", height=a.shape[0], width=a.shape[1], count=1, dtype="float32", crs="EPSG:4326",
                transform=tf, nodata=NODATA, compress="deflate", predictor=3, tiled=True, blockxsize=256, blockysize=256)
    with rasterio.open(tif, "w", **prof) as d:
        d.write(np.where(np.isfinite(a), a, NODATA).astype(np.float32), 1)
        d.update_tags(units="kWh/m2/day", description="Annual average daily GHI, NSRDB PSM v3 1998-2016")
    bounds = write_overlay(a, tf, png, GHI_STOPS, max_width=1200)
    v = a[np.isfinite(a)]
    add_manifest("ghi", tif, ["ghi"], src_path, int(v.size),
                 {"band 1": "annual average daily global horizontal irradiance, kWh/m2/day (nodata -9999 outside the five states)"},
                 ("NSRDB PSM v3 multi-year mean 1998-2016 at 0.04 deg (~4 km) cells, so values are smooth at site scale. The bundled "
                  "metadata text says kWh/m2/year but values (3.7 to 6.3) are kWh/m2/day, matching NREL's published map. A north-south seam "
                  "near 105W in eastern New Mexico is present in the NSRDB source (satellite coverage boundary), not added here. nrel.gov "
                  "(now NLR) no longer serves this file; the Internet Archive copy of NREL's original zip was used. "
                  f"Range in the five states: {v.min():.2f} to {v.max():.2f}, median {np.median(v):.2f}. "
                  "ghi_overlay.png is a pre-rendered map overlay (colour ramp 4.0 to 6.4)."),
                 overlay_png=str(png.relative_to(ROOT)), overlay_bounds=bounds,
                 overlay_legend=[{"value": s[0], "rgba": s[1]} for s in GHI_STOPS])
    log.info("ghi: %s cells, %.2f..%.2f", v.size, v.min(), v.max())


TILE_PX = 256
EARTH = 2 * math.pi * 6378137.0


def stage_slope(force):
    tif, png = OUT / "slope.tif", OUT / "slope_overlay.png"
    gt5 = EXC / "slope_gt5.geojson"
    if not need([tif, png, gt5], force):
        return
    from PIL import Image
    z = 11
    tdir = RAW / "terrain" / str(z)
    tiles = {tuple(t) for t in json.loads((RAW / "terrain" / f"tiles_z{z}.json").read_text())}
    have = {t for t in tiles if (tdir / f"{t[0]}_{t[1]}.png").exists()}
    log.info("slope: %d of %d terrain tiles on disk", len(have), len(tiles))
    xs, ys = [t[0] for t in have], [t[1] for t in have]
    m_px = EARTH / (TILE_PX * 2 ** z)  # mercator metres per pixel
    otf, W, H = out_grid()
    mm_path = OUT / "_slope_tmp.f32"
    mm = np.memmap(mm_path, dtype=np.float32, mode="w+", shape=(H, W))
    mm[:] = np.nan
    BS = 16

    def load(x, y):
        p = tdir / f"{x}_{y}.png"
        if (x, y) not in have:
            return None
        rgb = np.asarray(Image.open(p).convert("RGB"), dtype=np.float32)
        return rgb[..., 0] * 256 + rgb[..., 1] + rgb[..., 2] / 256 - 32768

    nblk = 0
    for bx in range(min(xs), max(xs) + 1, BS):
        for by in range(min(ys), max(ys) + 1, BS):
            if not any((x, y) in have for x in range(bx, bx + BS) for y in range(by, by + BS)):
                continue
            n = BS + 2
            elev = np.full((n * TILE_PX, n * TILE_PX), np.nan, dtype=np.float32)
            for i, x in enumerate(range(bx - 1, bx + BS + 1)):
                for j, y in enumerate(range(by - 1, by + BS + 1)):
                    e = load(x, y)
                    if e is not None:
                        elev[j * TILE_PX:(j + 1) * TILE_PX, i * TILE_PX:(i + 1) * TILE_PX] = e
            # latitude of each row centre
            rows = np.arange(elev.shape[0]) + 0.5
            ym = EARTH / 2 - ((by - 1) * TILE_PX + rows) * m_px
            lat = np.degrees(2 * np.arctan(np.exp(ym / 6378137.0)) - np.pi / 2)
            ground = (m_px * np.cos(np.radians(lat)))[:, None]
            dzdy, dzdx = np.gradient(elev)
            slope = 100.0 * np.hypot(dzdx / ground, dzdy / ground)
            del elev, dzdx, dzdy
            inner = slope[TILE_PX:-TILE_PX, TILE_PX:-TILE_PX].astype(np.float32)
            del slope
            src_tf = from_origin(-EARTH / 2 + bx * TILE_PX * m_px, EARTH / 2 - by * TILE_PX * m_px, m_px, m_px)
            lb = transform_bounds(3857, 4326, src_tf.c, src_tf.f - inner.shape[0] * m_px, src_tf.c + inner.shape[1] * m_px, src_tf.f)
            c0 = max(0, int(math.floor((lb[0] - BBOX[0]) / RES)) - 1)
            c1 = min(W, int(math.ceil((lb[2] - BBOX[0]) / RES)) + 1)
            r0 = max(0, int(math.floor((BBOX[3] - lb[3]) / RES)) - 1)
            r1 = min(H, int(math.ceil((BBOX[3] - lb[1]) / RES)) + 1)
            if c1 <= c0 or r1 <= r0:
                continue
            dst = np.full((r1 - r0, c1 - c0), np.nan, dtype=np.float32)
            dtf = from_origin(BBOX[0] + c0 * RES, BBOX[3] - r0 * RES, RES, RES)
            reproject(inner, dst, src_transform=src_tf, src_crs=3857, dst_transform=dtf, dst_crs=4326,
                      src_nodata=np.nan, dst_nodata=np.nan, resampling=Resampling.average)
            cur = mm[r0:r1, c0:c1]
            ok = np.isfinite(dst)
            cur[ok] = dst[ok]
            mm[r0:r1, c0:c1] = cur
            nblk += 1
            log.info("slope block %d (x %d, y %d) done", nblk, bx, by)
    mm.flush()

    # mask to states, write GeoTIFF, aggregate to ~0.005 deg for slope_gt5 polygons and overlay
    AGG = 6
    prof = dict(driver="GTiff", height=H, width=W, count=1, dtype="float32", crs="EPSG:4326", transform=otf,
                nodata=NODATA, compress="deflate", predictor=3, tiled=True, blockxsize=512, blockysize=512, BIGTIFF="IF_SAFER")
    Ha, Wa = H // AGG, W // AGG
    frac = np.full((Ha, Wa), np.nan, dtype=np.float32)
    meanv = np.full((Ha, Wa), np.nan, dtype=np.float32)
    STRIP = AGG * 100
    stats = []
    with rasterio.open(tif, "w", **prof) as d:
        for r in range(0, H, STRIP):
            h = min(STRIP, H - r)
            blk = np.array(mm[r:r + h, :])
            stf = from_origin(BBOX[0], BBOX[3] - r * RES, RES, RES)
            blk[~state_mask(stf, blk.shape)] = np.nan
            d.write(np.where(np.isfinite(blk), blk, NODATA).astype(np.float32), 1,
                    window=rasterio.windows.Window(0, r, W, h))
            fin = blk[np.isfinite(blk)]
            if fin.size:
                stats.append((fin.size, float((fin > 5).sum()), float(fin.sum())))
            ha = h // AGG
            if ha:
                b = blk[:ha * AGG, :Wa * AGG].reshape(ha, AGG, Wa, AGG)
                cnt = np.isfinite(b).sum(axis=(1, 3))
                steep = (b > 5).sum(axis=(1, 3))
                ssum = np.nansum(b, axis=(1, 3))
                with np.errstate(invalid="ignore", divide="ignore"):
                    frac[r // AGG:r // AGG + ha] = np.where(cnt > 0, steep / cnt, np.nan)
                    meanv[r // AGG:r // AGG + ha] = np.where(cnt > 0, ssum / cnt, np.nan)
        d.update_tags(units="percent", description="Terrain slope (percent rise) from AWS Terrain Tiles z11 (3DEP-based), resampled to 3 arc-seconds")
    del mm
    mm_path.unlink()
    n_all = sum(s[0] for s in stats)
    pct_gt5 = 100 * sum(s[1] for s in stats) / n_all
    log.info("slope: %d valid cells, %.1f%% over 5%%", n_all, pct_gt5)

    atf = from_origin(BBOX[0], BBOX[3], RES * AGG, RES * AGG)
    bounds = write_overlay(meanv, atf, png, SLOPE_STOPS, max_width=2400)

    # slope_gt5 polygons: aggregated cells where at least half the 3-arcsecond pixels exceed 5 percent
    steep = (np.nan_to_num(frac, nan=0) >= 0.5).astype(np.uint8)
    geoms = [shape(gm) for gm, v in features.shapes(steep, mask=steep == 1, transform=atf, connectivity=8) if v == 1]
    sg = gpd.GeoDataFrame(geometry=geoms, crs=4326)
    sg["kind"], sg["name"] = "hard", None
    sg["subtype"], sg["source"] = "slope > 5% (>= 50% of ~0.005 deg cell)", "derived from slope.tif"
    sg = add_acres(clip_states(sg))
    sg = sg[sg["acres"] >= 100].reset_index(drop=True)
    write_exclusion("slope_gt5", sg, ["terrain"], tdir / "*.png",
                    "Derived: slope.tif aggregated to 6x6-pixel cells (~0.005 deg, ~45-55 ha); a cell is steep when at least half its pixels "
                    "exceed 5 percent. Pieces under 100 acres were dropped. Use slope.tif for site-level slope; this layer is a screening mask.",
                    tol=0.002)
    add_manifest("slope", tif, ["terrain"], tdir / "*.png", n_all,
                 {"band 1": "slope in percent (rise/run x 100), nodata -9999 outside the five states"},
                 ("Elevation from AWS Terrain Tiles at zoom 11 (~62 m ground pixels at 35N), which in the US are built mainly from USGS "
                  "3DEP/NED, so this is a 3DEP-derived product rather than a direct 3DEP download. Slope computed in Web Mercator with "
                  "latitude-corrected pixel size, then averaged to a 3 arc-second (~92 m x 76 m) EPSG:4326 grid; averaging smooths short "
                  f"steep pitches. {pct_gt5:.1f} percent of the five-state area exceeds 5 percent slope. slope_overlay.png is a pre-rendered "
                  "overlay of the ~0.005 deg mean slope (transparent under 3 percent)."),
                 overlay_png=str(png.relative_to(ROOT)), overlay_bounds=bounds,
                 overlay_legend=[{"value": s[0], "rgba": s[1]} for s in SLOPE_STOPS], resolution_deg=RES)


STAGES = {"admin": stage_admin, "blm": stage_blm, "ownership": stage_ownership, "exclusions": stage_exclusions,
          "ghi": stage_ghi, "slope": stage_slope}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--only", nargs="*", choices=list(STAGES))
    args = ap.parse_args()
    setup_logging()
    OUT.mkdir(parents=True, exist_ok=True)
    EXC.mkdir(parents=True, exist_ok=True)
    load_manifest()
    for name, fn in STAGES.items():
        if args.only and name not in args.only:
            continue
        log.info("stage %s", name)
        fn(args.force)
        save_manifest()
    log.info("process_land done; manifest has %d layers", len(MANIFEST))


if __name__ == "__main__":
    main()

# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pyogrio==0.10.0",
#   "geopandas==1.0.1",
#   "shapely==2.0.6",
#   "pyproj==3.7.0",
#   "rasterio==1.4.3",
#   "numpy==2.1.3",
#   "pandas==2.2.3",
#   "scipy==1.15.2",
#   "scikit-image==0.25.2",
#   "xlsxwriter==3.2.0",
# ]
# ///
"""Screen and score candidate solar / data center sites (SCOPE.md section 4).

Steps
  1. 1 km cell grid over CA, AZ, NV, NM, UT in EPSG:5070. Per cell: state, surface
     owner (BLM SMA, by cell centre), BLM solar status, share of the cell under hard
     exclusions (250 m sub-grid), mean slope and share of 90 m slope pixels > 5 %, GHI.
  2. Keep cells with < 50 % hard exclusion, < 50 % steep pixels and mean slope <= 5 %.
     Dissolve 4-connected kept cells by ownership key; keep blocks >= 3 cells; split
     blocks > 20 cells (~4,900 acres) on a 4 x 4 km tile grid (~4,000 acre sites).
  3. Clip each site polygon exactly against every hard exclusion (full-resolution and
     map copies, plus SMA Tribal / NPS / DOD land) with a 5 m gap; keep parts >= 600 acres.
  4. Compute contract fields, factor scores (transforms in WEIGHTS), score_total, rank,
     next_step. Write candidate_sites.geojson, top_sites.csv, METHOD.md, checks and the
     Excel ranking with live formulas.

Run: uv run --script pipeline/screen.py [--rescore | --force]
"""
from __future__ import annotations

import argparse
import json
import logging
import math
import sys
import time
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pyogrio
import rasterio
import shapely
from pyproj import Transformer
from rasterio import features
from rasterio.transform import from_origin
from scipy import ndimage
from skimage.measure import label as sk_label

# ---------------------------------------------------------------------------
# Weights and transforms. Edit here; METHOD.md and the Excel weights block are
# generated from this dict.
# ---------------------------------------------------------------------------
WEIGHTS = {
    # Two rankings (after the 2026-10-21 methodology review). score = sum(w * factor) / sum(w).
    # Solar-only track: no data center term. score_total is an alias of score_total_solar.
    "factor_solar": {"grid": 35, "land": 30, "sun": 20, "permit": 15},
    # Solar + data center track.
    "factor_dc": {"grid": 30, "land": 25, "sun": 15, "permit": 15, "dc": 15},
    # grid sub-weights and transforms
    "grid": {
        "w_sub_dist": 0.40,   # 100 * exp(-dist_sub_km / sub_decay_km), nearest 115 kV+ substation
        "sub_decay_km": 15.0,
        "w_line_dist": 0.20,  # 100 * exp(-dist_line230_km / line_decay_km), nearest 230 kV+ line
        "line_decay_km": 20.0,
        "w_kv": 0.20,         # step score on nearest substation max_kv (kv_points)
        "kv_points": [[500, 100], [345, 90], [230, 75], [161, 55], [138, 50], [115, 40]],
        "w_queue": 0.20,      # 100 * exp(-queued_GW_county / queue_decay_gw), congestion penalty
        "queue_decay_gw": 15.0,
        # counties with 0 active queue MW: congestion is unknown, not zero -> neutral midpoint
        "queue_unknown_score": 50.0,
        # queue_confidence = high when >= 1 active project in the county is POI-matched to a
        # substation and the county POI match rate >= queue_match_min; otherwise low
        "queue_match_min": 0.5,
        # grid score multiplier when the nearest substation is provisional (OSM-only, kV
        # inferred from nearby lines or from OSM, or name starts with UNKNOWN)
        "provisional_mult": 0.85,
    },
    # land: 0.6 ownership/BLM status + 0.2 slope + 0.2 block size
    "land": {
        "w_owner": 0.60,
        "owner_base": {"BLM": 20, "State": 65, "Private": 70, "Other": 30, "USFS": 10},
        # BLM solar-available land bonus (added to BLM base, capped at 100)
        "blm_bonus": {"available": 65, "dfa": 65, "variance": 35, "sez": 15},
        "w_slope": 0.20,      # 100 * (1 - mean_slope / 5), clipped 0-100
        "w_size": 0.20,       # 100 * min(1, acres / size_full_acres)
        "size_full_acres": 3500,
    },
    # sun: linear GHI (kWh/m2/day) from ghi_lo -> 0 to ghi_hi -> 100
    "sun": {"ghi_lo": 4.5, "ghi_hi": 6.0},
    # permitting risk: start at 100 and subtract penalties per flag in constraints_soft
    "permit": {
        "penalties": {
            "acec": 25,                   # touches a BLM ACEC (soft)
            "wetlands_nwi": 15,           # touches an NWI wetland >= 40 acres
            "active_blm_row_case": 25,    # overlaps an active MLRS solar ROW case (competing claim)
            "near_critical_habitat_1km": 10,
            "near_protected_area_1km": 10,  # wilderness/WSA, NCA/monument, NPS within 1 km
            "existing_plant_on_site": 10,   # EIA-860 plant point inside the site
            "blm_outside_available": 30,    # BLM land outside Western Solar Plan Available / DFA
            "drecp_variance": 15,
            "federal_review": 10,           # BLM land: NEPA + 2025 DOI Secretary-level review
            "az_ama": 0,                    # informational (water rule, affects data centers)
        },
    },
    # data center fit: fiber, water, road, large-load substation
    "dc": {
        "w_fiber": 0.35, "fiber_decay_km": 10.0,   # 100 * exp(-fiber_km / 10)
        "w_water": 0.25,                           # 100 * (1 - water_stress / 5)
        "w_road": 0.20, "road_decay_km": 8.0,      # 100 * exp(-road_km / 8)
        "w_load": 0.20, "load_decay_km": 15.0,     # 100 * exp(-dist_sub230_km / 15)
        "water_missing": 2.5,                      # assumed stress where Aqueduct has no value
    },
}

SCREEN = {
    "cell_m": 1000,
    "sub": 4,                    # 250 m sub-grid for hard-exclusion share
    "max_excl_frac": 0.5,
    "max_steep_frac": 0.5,
    "max_mean_slope": 5.0,
    "min_cells": 3,
    "split_cells": 20,           # blocks larger than this are split on a tile grid
    "tile_cells": 4,             # 4 x 4 km tiles (~3,950 acres)
    "min_acres": 600.0,
    "gap_m": 5.0,                # gap kept from every hard exclusion
    "acres_per_mw": 6.0,         # midpoint of 5-7 acres/MW
    "sub_kv_min": 115,
    "max_sub_km": 30.0,          # candidate pool: within 30 km of a 115 kV+ substation
    "inset_m": 15.0,             # delivered polygons are inset 15 m, then simplified 12 m (stay inside the exact cut)
    "simplify_m": 12.0,
    "sub_types_excluded": ["TAP", "RISER", "GENERATION", "DEAD END", "MINOR_DISTRIBUTION",
                           "DISTRIBUTION", "INDUSTRIAL", "TRANSITION", "COMPENSATION", "CONVERTER"],
    # POIs removed before the nearest-substation search (review fix 3)
    "poi_hvdc_regex": r"HVDC|CONVERTER|AC-DC|\bTIE$",  # incl. back-to-back AC-DC-AC ties (Eddy, Blackwater)
    "poi_plant_name_regex": r"SOLAR|WIND|ENERGY CENTER|COLLECTOR|GENERAT|COGEN|\bGEN\b",
    "poi_plant_owner_regex": r"SOLAR|WIND|RENEWABLE|ENERGY CENTER|COLLECTOR",
    "poi_status_regex": r"RETIRED|DECOMMISSION|NOT IN SERVICE|INACTIVE|ABANDON|PROPOSED|PLANNED|UNDER CONSTRUCTION",
}

ROOT = Path(__file__).resolve().parent.parent
P = ROOT / "data" / "processed"
OUT = P / "sites"
WORK = OUT / "work"
LOG = ROOT / "logs" / "screening.log"
XLSX = ROOT / "deliverables" / "Southwest_Solar_Sites.xlsx"
CRS = "EPSG:5070"
ACRE = 4046.8564224
STATES = ["CA", "AZ", "NV", "NM", "UT"]
OWN_CODES = {"BLM": 1, "State": 2, "Private": 3, "Other": 4, "USFS": 5, "Tribal": 6, "NPS": 7, "DOD": 8}
OWN_NAMES = {v: k for k, v in OWN_CODES.items()}
HARD_OWNERS = {"Tribal", "NPS", "DOD"}
BLM_CODES = {"Available (2024 Western Solar Plan ROD)": 1, "DRECP Development Focus Area (CA)": 2,
             "DRECP Variance Land (CA)": 3}
BLM_STATUS = {0: "BLM outside solar-available area", 1: "Available (2024 Western Solar Plan ROD)",
              2: "DRECP Development Focus Area (CA)", 3: "DRECP Variance Land (CA)"}
STATE_TRUST = {
    "AZ": "Arizona State Land Department",
    "NM": "New Mexico State Land Office",
    "UT": "Utah Trust Lands Administration",
    "CA": "California State Lands Commission",
    "NV": "Nevada Division of State Lands",
}

log = logging.getLogger("screen")


def setup_log():
    LOG.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        handlers=[logging.FileHandler(LOG), logging.StreamHandler(sys.stdout)])


STAGE = {"name": "start", "t0": time.time()}


def stage(name):
    STAGE["name"] = name
    log.info("stage: %s", name)


def start_heartbeat(every_s=30):
    """Log a progress line every `every_s` seconds so long steps are never silent."""
    import threading

    def beat():
        while True:
            time.sleep(every_s)
            log.info("heartbeat: still working on '%s' (%.0fs elapsed)", STAGE["name"], time.time() - STAGE["t0"])
    threading.Thread(target=beat, daemon=True).start()


# ---------------------------------------------------------------------------
# Stage 1: cell rasters
# ---------------------------------------------------------------------------
def grid_def():
    st = gpd.read_file(P / "land/admin_states.geojson").to_crs(CRS)
    st = st[st["state"].isin(STATES)] if "state" in st.columns else st
    g = SCREEN["cell_m"]
    x0, y0, x1, y1 = st.total_bounds
    x0, y0 = math.floor(x0 / g) * g, math.floor(y0 / g) * g
    x1, y1 = math.ceil(x1 / g) * g, math.ceil(y1 / g) * g
    W, H = int((x1 - x0) / g), int((y1 - y0) / g)
    return st, x0, y1, W, H


def hard_layers_5070():
    """All hard-exclusion geometries (full-res + map copies + SMA hard owners) in EPSG:5070."""
    parts = []
    for lyr in pyogrio.list_layers(P / "land/exclusions_full.gpkg")[:, 0]:
        g = gpd.read_file(P / "land/exclusions_full.gpkg", layer=lyr, columns=["kind", "constraint"])
        g = g[g["kind"] == "hard"]
        parts.append(g[["constraint", "geometry"]].assign(src="full"))
    for f in sorted((P / "land/exclusions").glob("*.geojson")):
        g = gpd.read_file(f, columns=["kind", "constraint"])
        g = g[g["kind"] == "hard"]
        parts.append(g[["constraint", "geometry"]].assign(src="map"))
    o = gpd.read_file(P / "land/ownership.gpkg", layer="ownership", columns=["category"])
    o = o[o["category"].isin(HARD_OWNERS)]
    parts.append(gpd.GeoDataFrame({"constraint": "sma_" + o["category"].str.lower(), "src": "sma"},
                                  geometry=o.geometry, crs=o.crs))
    h = pd.concat(parts, ignore_index=True)
    h = h[h.geometry.notna()]
    h = h[~h.geometry.is_empty]
    h = gpd.GeoDataFrame(h, geometry="geometry", crs="EPSG:4326").to_crs(CRS)
    h["geometry"] = shapely.make_valid(h.geometry.values)
    return h


def build_cells(force=False):
    cache = WORK / "cells.npz"
    if cache.exists() and not force:
        log.info("cells: using cache %s", cache)
        d = np.load(cache)
        return {k: d[k] for k in d.files}
    t = time.time()
    st, x0, y1, W, H = grid_def()
    g = SCREEN["cell_m"]
    T1 = from_origin(x0, y1, g, g)
    log.info("grid %d x %d cells of %d m (EPSG:5070)", W, H, g)
    scode = {s: i + 1 for i, s in enumerate(STATES)}
    state_r = features.rasterize([(geom, scode[s]) for geom, s in zip(st.geometry, st["state"])],
                                 out_shape=(H, W), transform=T1, fill=0, dtype="uint8")
    own = gpd.read_file(P / "land/ownership.gpkg", layer="ownership", columns=["category"]).to_crs(CRS)
    own_r = features.rasterize([(geom, OWN_CODES.get(c, 4)) for geom, c in zip(own.geometry, own["category"])],
                               out_shape=(H, W), transform=T1, fill=0, dtype="uint8")
    del own
    blm = gpd.read_file(P / "land/blm_solar_available.gpkg", columns=["category"]).to_crs(CRS)
    blm = blm.assign(code=blm["category"].map(BLM_CODES).fillna(1).astype(int)).sort_values("code", ascending=False)
    blm_r = features.rasterize([(geom, c) for geom, c in zip(blm.geometry, blm["code"])],
                               out_shape=(H, W), transform=T1, fill=0, dtype="uint8")
    del blm
    log.info("state/owner/BLM rasters done (%.0fs)", time.time() - t)

    sub = SCREEN["sub"]
    T4 = from_origin(x0, y1, g / sub, g / sub)
    hard = hard_layers_5070()
    log.info("hard exclusion features: %d", len(hard))
    ex = features.rasterize(((geom, 1) for geom in hard.geometry), out_shape=(H * sub, W * sub),
                            transform=T4, fill=0, dtype="uint8")
    excl_frac = ex.reshape(H, sub, W, sub).mean(axis=(1, 3)).astype("float32")
    del ex, hard
    log.info("hard exclusion share done (%.0fs)", time.time() - t)

    # slope: exact per-cell aggregation of 90 m pixels (centre of each pixel -> cell)
    ssum = np.zeros(H * W, "float64"); scnt = np.zeros(H * W, "float64"); ssteep = np.zeros(H * W, "float64")
    tr = Transformer.from_crs("EPSG:4326", CRS, always_xy=True)
    with rasterio.open(P / "land/slope.tif") as src:
        nod = src.nodata
        step = 400
        cols = np.arange(src.width)
        lon = src.transform.c + (cols + 0.5) * src.transform.a
        for r0 in range(0, src.height, step):
            n = min(step, src.height - r0)
            a = src.read(1, window=((r0, r0 + n), (0, src.width)))
            lat = src.transform.f + (np.arange(r0, r0 + n) + 0.5) * src.transform.e
            LON, LAT = np.meshgrid(lon, lat)
            ok = (a != nod) & np.isfinite(a)
            X, Y = tr.transform(LON[ok], LAT[ok])
            ci = ((X - x0) // g).astype(np.int64); ri = ((y1 - Y) // g).astype(np.int64)
            inb = (ci >= 0) & (ci < W) & (ri >= 0) & (ri < H)
            idx = ri[inb] * W + ci[inb]
            v = a[ok][inb].astype("float64")
            ssum += np.bincount(idx, weights=v, minlength=H * W)
            scnt += np.bincount(idx, minlength=H * W)
            ssteep += np.bincount(idx, weights=(v > 5.0).astype("float64"), minlength=H * W)
    with np.errstate(invalid="ignore", divide="ignore"):
        slope_mean = (ssum / scnt).reshape(H, W).astype("float32")
        steep_frac = (ssteep / scnt).reshape(H, W).astype("float32")
    log.info("slope aggregation done (%.0fs)", time.time() - t)

    # GHI: sample 4 km raster at each cell centre (nearest)
    rr, cc = np.mgrid[0:H, 0:W]
    X = x0 + (cc + 0.5) * g; Y = y1 - (rr + 0.5) * g
    lon, lat = Transformer.from_crs(CRS, "EPSG:4326", always_xy=True).transform(X.ravel(), Y.ravel())
    with rasterio.open(P / "land/ghi.tif") as src:
        a = src.read(1)
        inv = ~src.transform
        col, row = inv * (np.asarray(lon), np.asarray(lat))
        col = np.floor(col).astype(int); row = np.floor(row).astype(int)
        okk = (col >= 0) & (col < src.width) & (row >= 0) & (row < src.height)
        ghi = np.full(H * W, np.nan, "float32")
        vals = a[row[okk], col[okk]]
        vals = np.where(vals == src.nodata, np.nan, vals)
        ghi[okk] = vals
        ghi = ghi.reshape(H, W)
    WORK.mkdir(parents=True, exist_ok=True)
    out = dict(state=state_r, own=own_r, blm=blm_r, excl=excl_frac, slope=slope_mean, steep=steep_frac,
               ghi=ghi, meta=np.array([x0, y1, W, H, g], "float64"))
    np.savez_compressed(cache, **out)
    log.info("cells cached (%.0fs)", time.time() - t)
    return out


# ---------------------------------------------------------------------------
# Stage 2: blocks and sites
# ---------------------------------------------------------------------------
def build_sites(c, force=False):
    cache = WORK / "sites_raw.gpkg"
    if cache.exists() and not force:
        log.info("sites_raw: using cache")
        return gpd.read_file(cache)
    x0, y1, W, H, g = c["meta"]; W, H = int(W), int(H)
    T1 = from_origin(x0, y1, g, g)
    own = c["own"].copy()
    own[(own == 0) & (c["state"] > 0)] = OWN_CODES["Private"]  # SMA gaps: unknown/private
    hard_own = np.isin(own, [OWN_CODES[k] for k in HARD_OWNERS])
    ok = ((c["state"] > 0) & ~hard_own & (c["excl"] < SCREEN["max_excl_frac"])
          & (np.nan_to_num(c["steep"], nan=1) < SCREEN["max_steep_frac"])
          & (np.nan_to_num(c["slope"], nan=99) <= SCREEN["max_mean_slope"]))
    log.info("cells in states %d; kept after hard exclusions + slope %d (%.1f%%)",
             int((c["state"] > 0).sum()), int(ok.sum()), 100 * ok.sum() / max(1, (c["state"] > 0).sum()))
    blm = np.where(own == OWN_CODES["BLM"], c["blm"], 0)
    key = np.where(ok, own.astype(np.int32) * 10 + blm.astype(np.int32), 0)
    comp = sk_label(key, connectivity=1, background=0).astype(np.int64)
    sizes = np.bincount(comp.ravel())
    small = sizes < SCREEN["min_cells"]; small[0] = True
    comp[small[comp]] = 0
    sizes = np.bincount(comp.ravel(), minlength=sizes.size)
    log.info("blocks >= %d cells: %d", SCREEN["min_cells"], int((sizes[1:] > 0).sum()))
    big = sizes > SCREEN["split_cells"]; big[0] = False
    tc = SCREEN["tile_cells"]
    rr, cc = np.mgrid[0:H, 0:W]
    ntw = W // tc + 1
    tile = (rr // tc) * ntw + (cc // tc) + 1
    nt = int(tile.max()) + 1
    pkey = np.where(comp > 0, comp * nt + np.where(big[comp], tile, 0), 0)
    site = sk_label(pkey, connectivity=1, background=0).astype(np.int64)
    # merge tiny tile fragments into a neighbouring piece of the same block
    ps = np.bincount(site.ravel())
    objs = ndimage.find_objects(site)
    merged = 0
    for lab in np.where((ps > 0) & (ps < SCREEN["min_cells"] + 1))[0]:
        if lab == 0 or objs[lab - 1] is None:
            continue
        sl = objs[lab - 1]
        sl = tuple(slice(max(s.start - 1, 0), s.stop + 1) for s in sl)
        sub_site = site[sl]; sub_comp = comp[sl]
        m = sub_site == lab
        if not m.any():
            continue
        cid = sub_comp[m][0]
        ring = ndimage.binary_dilation(m) & ~m & (sub_comp == cid) & (sub_site != lab) & (sub_site > 0)
        if ring.any():
            vals, cnt = np.unique(sub_site[ring], return_counts=True)
            sub_site[m] = vals[np.argmax(cnt)]
            merged += 1
    log.info("merged %d small tile fragments", merged)
    ps = np.bincount(site.ravel())
    site[(ps < SCREEN["min_cells"])[site] & (site > 0)] = 0
    site32 = site.astype(np.int32)
    geoms, labs = [], []
    for geom, val in features.shapes(site32, mask=site32 > 0, transform=T1, connectivity=4):
        geoms.append(shapely.geometry.shape(geom)); labs.append(int(val))
    gdf = gpd.GeoDataFrame({"lab": labs}, geometry=geoms, crs=CRS).dissolve("lab").reset_index()
    # per-site cell attributes
    flat = site.ravel()
    sel = flat > 0
    lab_index = pd.Index(gdf["lab"])

    def zmean(arr):
        s = pd.Series(arr.ravel()[sel]).groupby(flat[sel]).mean()
        return s.reindex(lab_index).values

    gdf["ghi"] = zmean(c["ghi"])
    gdf["mean_slope"] = zmean(c["slope"])
    gdf["cells"] = pd.Series(np.ones(sel.sum())).groupby(flat[sel]).sum().reindex(lab_index).values
    first = pd.Series(np.arange(flat.size)[sel]).groupby(flat[sel]).first().reindex(lab_index).values
    gdf["own_code"] = own.ravel()[first]
    gdf["blm_code"] = blm.ravel()[first]
    gdf["block_id"] = comp.ravel()[first]
    gdf["block_cells"] = sizes[gdf["block_id"].values]
    gdf.to_file(cache, driver="GPKG")
    log.info("raw sites: %d", len(gdf))
    return gdf


def subdivide(geoms, tile_m=10000.0, max_coords=500):
    """Split large polygons on a tile grid (like PostGIS ST_Subdivide) so per-site cuts stay fast."""
    geoms = shapely.get_parts(np.asarray(geoms))
    nc = shapely.get_num_coordinates(geoms)
    small = geoms[nc <= max_coords]
    big = geoms[nc > max_coords]
    out = [small]
    for g in big:
        x0, y0, x1, y1 = g.bounds
        xs = np.arange(math.floor(x0 / tile_m) * tile_m, x1, tile_m)
        ys = np.arange(math.floor(y0 / tile_m) * tile_m, y1, tile_m)
        X, Y = np.meshgrid(xs, ys)
        boxes = shapely.box(X.ravel(), Y.ravel(), X.ravel() + tile_m, Y.ravel() + tile_m)
        boxes = boxes[shapely.intersects(g, boxes)]
        parts = shapely.get_parts(shapely.intersection(g, boxes))
        parts = parts[shapely.get_type_id(parts) == 3]
        out.append(parts[~shapely.is_empty(parts)])
    res = np.concatenate(out)
    return res[shapely.area(res) > 0]


def clip_hard(sites, force=False):
    cache = WORK / "sites_clipped.gpkg"
    if cache.exists() and not force:
        log.info("sites_clipped: using cache")
        return gpd.read_file(cache)
    t = time.time()
    hard = hard_layers_5070()
    hg = subdivide(hard.geometry.values)
    del hard
    log.info("hard exclusions subdivided into %d pieces (%.0fs)", len(hg), time.time() - t)
    tree = shapely.STRtree(hg)
    gap = SCREEN["gap_m"]
    sg = sites.geometry.values
    i_in, i_t = tree.query(sg, predicate="dwithin", distance=gap)
    order = np.argsort(i_in, kind="stable")
    i_in, i_t = i_in[order], i_t[order]
    starts = np.searchsorted(i_in, np.arange(len(sg)))
    ends = np.searchsorted(i_in, np.arange(len(sg)), side="right")
    log.info("%d site/exclusion pairs within %.0f m (%.0fs)", len(i_in), gap, time.time() - t)
    out = []
    n_touched = 0
    recs = sites.drop(columns="geometry").to_dict("records")
    for i in range(len(sg)):
        geom = sg[i]
        idx = i_t[starts[i]:ends[i]]
        if len(idx):
            n_touched += 1
            cut = shapely.union_all(shapely.buffer(hg[idx], gap, quad_segs=2))
            geom = shapely.make_valid(geom.difference(cut))
        for k, part in enumerate(shapely.get_parts(geom)):
            if part.geom_type != "Polygon":
                continue
            if part.area / ACRE >= SCREEN["min_acres"]:
                d = dict(recs[i]); d["geometry"] = part; d["part"] = k
                out.append(d)
        if i % 5000 == 0:
            log.info("clip %d/%d (%.0fs)", i, len(sg), time.time() - t)
    res = gpd.GeoDataFrame(out, geometry="geometry", crs=CRS)
    log.info("clip: %d of %d sites were within %.0f m of hard exclusions; %d site parts >= %d acres remain",
             n_touched, len(sites), gap, len(res), SCREEN["min_acres"])
    res.to_file(cache, driver="GPKG")
    return res


# ---------------------------------------------------------------------------
# Stage 3: attributes and scores
# ---------------------------------------------------------------------------
def nearest(src_geoms, tgt: gpd.GeoDataFrame):
    i_in, i_tree = tgt.sindex.nearest(src_geoms, return_all=False)
    d = shapely.distance(np.asarray(src_geoms)[i_in], tgt.geometry.values[i_tree])
    idx = np.full(len(src_geoms), -1); dist = np.full(len(src_geoms), np.nan)
    idx[i_in] = i_tree; dist[i_in] = d
    return idx, dist / 1000.0


def kv_score(kv):
    if kv is None or not np.isfinite(kv):
        return 0.0
    for thr, pts in WEIGHTS["grid"]["kv_points"]:
        if kv >= thr:
            return float(pts)
    return 0.0


def touches(sites, layer_gdf, buffer_m=0.0):
    """bool array: site intersects (or within buffer of) any feature in layer_gdf (EPSG:5070)."""
    if len(layer_gdf) == 0:
        return np.zeros(len(sites), bool)
    tree = shapely.STRtree(subdivide(layer_gdf.geometry.values))
    if buffer_m > 0:
        i_in, _ = tree.query(sites.geometry.values, predicate="dwithin", distance=buffer_m)
    else:
        i_in, _ = tree.query(sites.geometry.values, predicate="intersects")
    m = np.zeros(len(sites), bool); m[np.unique(i_in)] = True
    return m


def poi_substations():
    """115 kV+ substations usable as a points of interconnection (POI) for screening.

    Returns (kept, removed). Removed (with a `removed_reason`): sub_type in sub_types_excluded
    (TAP, RISER, GENERATION, CONVERTER, ...), HVDC converter stations, generator-owned or plant
    collector substations (plant-like name and the owner is missing or itself plant-like; a
    utility-owned substation with a plant-like name such as SCE Windhub is kept), and
    retired / not-in-service status. Kept rows carry sub_source, sub_kv_source, sub_provisional.
    """
    subs = gpd.read_file(P / "grid/substations.gpkg").to_crs(CRS)
    subs = subs[subs["max_kv"].fillna(0) >= SCREEN["sub_kv_min"]].reset_index(drop=True)
    name = subs["name"].fillna("").astype(str).str.upper()
    owner = subs["owner"].fillna("").astype(str).str.upper().str.strip()
    status = subs["status"].fillna("").astype(str).str.upper()
    stype = subs["sub_type"].fillna("").astype(str).str.upper()
    owner_unknown = owner.isin(["", "NOT AVAILABLE", "UNKNOWN", "NONE"])
    owner_plant = owner.str.contains(SCREEN["poi_plant_owner_regex"], regex=True)
    utility_owned = ~owner_unknown & ~owner_plant
    reason = pd.Series("", index=subs.index, dtype=object)
    rules = [
        ("hvdc_converter", name.str.contains(SCREEN["poi_hvdc_regex"], regex=True) | (stype == "CONVERTER")),
        ("retired_or_not_in_service", status.str.contains(SCREEN["poi_status_regex"], regex=True)),
        ("generator_or_collector", (stype == "GENERATION") | owner_plant
         | (name.str.contains(SCREEN["poi_plant_name_regex"], regex=True) & ~utility_owned)),
        ("sub_type_" + "excluded", stype.isin(SCREEN["sub_types_excluded"])),
    ]
    for lab, m in rules:
        reason[(reason == "") & m] = lab
    subs["removed_reason"] = reason
    removed = subs[reason != ""].copy()
    kept = subs[reason == ""].reset_index(drop=True)
    kept["sub_source"] = kept["source"].fillna("unknown")
    kept["sub_kv_source"] = kept["kv_source"].fillna("unknown")
    kept["sub_provisional"] = ((kept["sub_source"] == "osm")
                               | kept["sub_kv_source"].isin(["osm", "inferred_from_lines", "unknown"])
                               | kept["name"].fillna("UNKNOWN").astype(str).str.upper().str.startswith("UNKNOWN"))
    return kept, removed


def substation_fields(s):
    """Nearest POI substation fields (cheap; recomputed on every run, not cached)."""
    stage("nearest POI substation search")
    kept, removed = poi_substations()
    cnt = removed["removed_reason"].value_counts().reindex(
        ["hvdc_converter", "retired_or_not_in_service", "generator_or_collector", "sub_type_excluded"], fill_value=0)
    log.info("POI filter: %d substations >= %d kV; removed %d (%s); %d kept, %d of them provisional",
             len(kept) + len(removed), SCREEN["sub_kv_min"], len(removed),
             ", ".join(f"{k} {v}" for k, v in cnt.items()), len(kept), int(kept["sub_provisional"].sum()))
    WORK.mkdir(parents=True, exist_ok=True)
    removed.drop(columns="geometry").to_csv(OUT / "excluded_pois.csv", index=False)
    k, d = nearest(s.geometry.values, kept)
    s["nearest_sub_id"] = kept["id"].values[k]; s["nearest_sub_name"] = kept["name"].values[k]
    s["nearest_sub_kv"] = kept["max_kv"].values[k]; s["dist_sub_km"] = d.round(2)
    s["nearest_sub_owner"] = kept["owner"].values[k]
    s["nearest_sub_queue_mw"] = kept["queue_active_mw"].values[k]
    s["nearest_sub_source"] = kept["source"].values[k]
    s["sub_source"] = kept["sub_source"].values[k]
    s["sub_kv_source"] = kept["sub_kv_source"].values[k]
    s["sub_provisional"] = kept["sub_provisional"].values[k].astype(bool)
    s230 = kept[kept["max_kv"] >= 230].reset_index(drop=True)
    k2, d2 = nearest(s.geometry.values, s230)
    s["nearest_sub230_id"] = s230["id"].values[k2]
    s["nearest_sub230_name"] = s230["name"].values[k2]; s["nearest_sub230_kv"] = s230["max_kv"].values[k2]
    s["dist_sub230_km"] = d2.round(2)
    s.attrs["poi_removed"] = {k: int(v) for k, v in cnt.items()}
    s.attrs["poi_kept"] = int(len(kept)); s.attrs["poi_provisional"] = int(kept["sub_provisional"].sum())
    return s


def queue_fields(s):
    """County queue MW plus a confidence flag based on POI matching of active projects."""
    q = pd.read_csv(P / "grid/queue_by_county.csv", dtype={"county_fips": str}).set_index("county_fips")
    s["queued_mw_county"] = s["county_fips"].map(q["active_mw_total"]).fillna(0).round(0)
    s["queued_mw_county_solar"] = s["county_fips"].map(q["active_mw_solar"]).fillna(0).round(0)
    s["queued_mw_county_storage"] = s["county_fips"].map(q["active_mw_storage"]).fillna(0).round(0)
    qp = pd.read_csv(P / "grid/queue_projects.csv", dtype={"county_fips": str},
                     usecols=["queue_id", "status", "county_fips", "poi_sub_id"])
    a = qp[qp["status"] == "active"]
    g = a.groupby("county_fips").agg(n=("queue_id", "size"), m=("poi_sub_id", lambda x: int(x.notna().sum())))
    n = s["county_fips"].map(g["n"]).fillna(0)
    m = s["county_fips"].map(g["m"]).fillna(0)
    s["queue_n_active_county"] = n.astype(int).values
    s["queue_poi_match_rate"] = np.where(n > 0, (m / n.where(n > 0, 1)).round(2), np.nan)
    hi = (s["queued_mw_county"] > 0) & (m >= 1) & (s["queue_poi_match_rate"].fillna(0) >= WEIGHTS["grid"]["queue_match_min"])
    s["queue_confidence"] = np.where(hi, "high", "low")
    log.info("queue confidence: %d sites high, %d low (%d of them in counties with 0 active MW, scored neutral)",
             int(hi.sum()), int((~hi).sum()), int((s["queued_mw_county"] <= 0).sum()))
    return s


def attributes(s):
    t = time.time()
    s = s.copy()
    s["acres"] = s.geometry.area / ACRE
    s["owner_category"] = s["own_code"].map(OWN_NAMES)
    s["blm_status"] = np.where(s["owner_category"] == "BLM", s["blm_code"].map(BLM_STATUS), "")
    cen = s.geometry.representative_point()
    cen_ll = gpd.GeoSeries(cen, crs=CRS).to_crs("EPSG:4326")
    s["centroid_lat"] = cen_ll.y.round(5); s["centroid_lon"] = cen_ll.x.round(5)

    # exact overlap with BLM solar-available layer
    blm = gpd.read_file(P / "land/blm_solar_available.gpkg", columns=["category", "sez_name"]).to_crs(CRS)
    tree = shapely.STRtree(blm.geometry.values)
    i_in, i_t = tree.query(s.geometry.values, predicate="intersects")
    inter = shapely.area(shapely.intersection(s.geometry.values[i_in], blm.geometry.values[i_t]))
    ov = pd.DataFrame({"i": i_in, "a": inter, "cat": blm["category"].values[i_t]})
    tot = ov.groupby("i")["a"].sum()
    s["blm_avail_pct"] = (100 * tot.reindex(range(len(s))).fillna(0).values / s.geometry.area.values).round(1)
    catmax = ov.sort_values("a").groupby("i")["cat"].last().reindex(range(len(s)))
    is_blm = s["owner_category"] == "BLM"
    s["blm_solar_category"] = np.where(is_blm & (s["blm_avail_pct"] >= 50), catmax.fillna("").values, "")
    s["blm_solar_available"] = (is_blm & (s["blm_avail_pct"] >= 50)
                                & s["blm_solar_category"].isin(["Available (2024 Western Solar Plan ROD)",
                                                                 "DRECP Development Focus Area (CA)"])).astype(bool)
    s.loc[is_blm & (s["blm_avail_pct"] < 50), "blm_status"] = BLM_STATUS[0]
    s.loc[is_blm & (s["blm_avail_pct"] >= 50), "blm_status"] = s.loc[is_blm & (s["blm_avail_pct"] >= 50), "blm_solar_category"]
    del blm

    sez = gpd.read_file(P / "land/solar_energy_zones.geojson").to_crs(CRS)
    sez = sez[sez["status"].astype(str).str.lower().str.startswith("developable")]
    j = gpd.sjoin(s[["geometry"]], sez[["sez_name", "geometry"]], predicate="intersects", how="left")
    s["sez_name"] = j.groupby(level=0)["sez_name"].first().reindex(s.index).fillna("").values

    # state and county from representative point
    cty = gpd.read_file(P / "land/admin_counties.geojson").to_crs(CRS)
    pts = gpd.GeoDataFrame(geometry=cen, crs=CRS)
    j = gpd.sjoin(pts, cty[["geoid", "state", "county", "geometry"]], predicate="within", how="left")
    j = j[~j.index.duplicated()]
    miss = j["geoid"].isna()
    if miss.any():
        k, _ = nearest(pts.geometry.values[miss.values], cty)
        j.loc[miss, ["geoid", "state", "county"]] = cty.iloc[k][["geoid", "state", "county"]].values
    s["state"] = j["state"].values; s["county"] = j["county"].values; s["county_fips"] = j["geoid"].values

    s = substation_fields(s)

    lines =gpd.read_file(P / "grid/transmission_lines.gpkg").to_crs(CRS)
    lines = lines[lines["status"].fillna("").str.upper() != "INACTIVE"]
    l115 = lines[lines["voltage_kv"].fillna(0) >= 115].reset_index(drop=True)
    k, d = nearest(s.geometry.values, l115)
    s["nearest_line_kv"] = l115["voltage_kv"].values[k]; s["dist_line_km"] = d.round(2)
    s["nearest_line_owner"] = l115["owner"].values[k]
    l230 = lines[lines["voltage_kv"].fillna(0) >= 230].reset_index(drop=True)
    k, d = nearest(s.geometry.values, l230)
    s["nearest_line230_kv"] = l230["voltage_kv"].values[k]; s["dist_line230_km"] = d.round(2)
    del lines
    log.info("grid distances done (%.0fs)", time.time() - t)

    s = queue_fields(s)

    fib = gpd.read_file(P / "infra/fiber.gpkg").to_crs(CRS)
    k, d = nearest(s.geometry.values, fib)
    s["fiber_km"] = d.round(2); s["fiber_basis"] = fib["basis"].values[k]
    rd = gpd.read_file(P / "infra/roads_major.gpkg").to_crs(CRS)
    k, d = nearest(s.geometry.values, rd)
    s["road_km"] = d.round(2); s["road_name"] = rd["name"].values[k]
    ws = gpd.read_file(P / "infra/water_stress.gpkg", columns=["water_stress", "bws_label"]).to_crs(CRS)
    ws = ws[ws["water_stress"].notna()].reset_index(drop=True)
    j = gpd.sjoin(pts, ws, predicate="within", how="left")
    j = j[~j.index.duplicated()]
    miss = j["water_stress"].isna()
    if miss.any():
        k, _ = nearest(pts.geometry.values[miss.values], ws)
        j.loc[miss, ["water_stress", "bws_label"]] = ws.iloc[k][["water_stress", "bws_label"]].values
    log.info("water join done (%.0fs)", time.time() - t)
    s["water_stress"] = j["water_stress"].astype(float).round(2).values
    s["water_stress_label"] = j["bws_label"].values
    log.info("infra distances done (%.0fs)", time.time() - t)

    # soft constraints and permitting flags
    flags = {k: np.zeros(len(s), bool) for k in WEIGHTS["permit"]["penalties"]}
    nac = gpd.read_file(P / "land/exclusions_full.gpkg", layer="nca_acec", columns=["kind"]).to_crs(CRS)
    flags["acec"] = touches(s, nac[nac["kind"] == "soft"])
    flags["near_protected_area_1km"] = touches(s, nac[nac["kind"] == "hard"], 1000)
    log.info("acec/nca flags (%.0fs)", time.time() - t)
    del nac
    for lyr in ["wilderness", "nps"]:
        e = gpd.read_file(P / "land/exclusions_full.gpkg", layer=lyr, columns=["kind"]).to_crs(CRS)
        flags["near_protected_area_1km"] |= touches(s, e, 1000)
    ch = gpd.read_file(P / "land/exclusions_full.gpkg", layer="critical_habitat", columns=["kind"]).to_crs(CRS)
    flags["near_critical_habitat_1km"] = touches(s, ch, 1000)
    log.info("critical habitat flag (%.0fs)", time.time() - t)
    del ch
    wl = gpd.read_file(P / "land/exclusions_full.gpkg", layer="wetlands", columns=["kind"])
    sll = s.geometry.to_crs("EPSG:4326")
    tree = shapely.STRtree(wl.geometry.values)
    i_in, _ = tree.query(sll.values, predicate="intersects")
    flags["wetlands_nwi"][np.unique(i_in)] = True
    log.info("wetlands flag (%.0fs)", time.time() - t)
    del wl, tree
    row = gpd.read_file(P / "infra/blm_solar_row_cases.geojson").to_crs(CRS)
    flags["active_blm_row_case"] = touches(s, row)
    tr_row = shapely.STRtree(row.geometry.values)
    i_in, i_t = tr_row.query(s.geometry.values, predicate="intersects")
    rc = pd.DataFrame({"i": i_in, "case": row["case_id"].values[i_t]}).groupby("i")["case"].apply(
        lambda x: ", ".join(sorted(set(map(str, x)))))
    s["row_cases_overlap"] = rc.reindex(range(len(s))).fillna("").values
    pp = gpd.read_file(P / "infra/power_plants.geojson").to_crs(CRS)
    pp = pp[pp["status"].astype(str).str.lower() == "operating"]
    flags["existing_plant_on_site"] = touches(s, pp)
    flags["blm_outside_available"] = (is_blm & (s["blm_status"] == BLM_STATUS[0])).values
    flags["drecp_variance"] = (s["blm_status"] == "DRECP Variance Land (CA)").values
    flags["federal_review"] = is_blm.values
    ama = gpd.read_file(P / "infra/az_ama_ina.geojson").to_crs(CRS)
    if "kind" in ama.columns:
        ama = ama[ama["kind"].astype(str).str.upper() == "AMA"]
    flags["az_ama"] = touches(s, ama)
    s["constraints_soft"] = [[k for k in flags if flags[k][i]] for i in range(len(s))]

    # BLM field office hint: nearest MLRS solar case (active or closed)
    cases = pd.concat([row, gpd.read_file(P / "infra/blm_solar_row_cases_closed.geojson").to_crs(CRS)],
                      ignore_index=True)
    cases = cases[cases["field_office"].notna()].reset_index(drop=True)
    k, d = nearest(s.geometry.values, cases)
    s["blm_fo_hint"] = [str(f).title().replace("Fo ", "FO ") for f in cases["field_office"].values[k]]
    s["blm_fo_hint_km"] = d.round(1)
    log.info("constraints done (%.0fs)", time.time() - t)
    return s


def score(s):
    W = WEIGHTS
    gw = W["grid"]
    s["s_sub"] = 100 * np.exp(-s["dist_sub_km"] / gw["sub_decay_km"])
    s["s_line"] = 100 * np.exp(-s["dist_line230_km"].fillna(999) / gw["line_decay_km"])
    s["s_kv"] = s["nearest_sub_kv"].astype(float).map(kv_score)
    s["s_queue"] = np.where(s["queued_mw_county"] > 0,
                            100 * np.exp(-(s["queued_mw_county"] / 1000.0) / gw["queue_decay_gw"]),
                            gw["queue_unknown_score"])
    raw_grid = (gw["w_sub_dist"] * s["s_sub"] + gw["w_line_dist"] * s["s_line"]
                + gw["w_kv"] * s["s_kv"] + gw["w_queue"] * s["s_queue"])
    s["score_grid"] = np.where(s["sub_provisional"], gw["provisional_mult"] * raw_grid, raw_grid)
    lw = W["land"]
    base = s["owner_category"].map(lw["owner_base"]).fillna(lw["owner_base"]["Other"]).astype(float)
    bonus = np.select([s["blm_status"] == "Available (2024 Western Solar Plan ROD)",
                       s["blm_status"] == "DRECP Development Focus Area (CA)",
                       s["blm_status"] == "DRECP Variance Land (CA)"],
                      [lw["blm_bonus"]["available"], lw["blm_bonus"]["dfa"], lw["blm_bonus"]["variance"]], 0)
    bonus = bonus + np.where((s["owner_category"] == "BLM") & (s["sez_name"] != ""), lw["blm_bonus"]["sez"], 0)
    s["s_owner"] = np.minimum(100, base + bonus)
    s["s_slope"] = np.clip(100 * (1 - s["mean_slope"] / 5.0), 0, 100)
    s["s_size"] = 100 * np.minimum(1, s["acres"] / lw["size_full_acres"])
    s["score_land"] = lw["w_owner"] * s["s_owner"] + lw["w_slope"] * s["s_slope"] + lw["w_size"] * s["s_size"]
    sw = W["sun"]
    s["score_sun"] = np.clip(100 * (s["ghi"] - sw["ghi_lo"]) / (sw["ghi_hi"] - sw["ghi_lo"]), 0, 100)
    pen = W["permit"]["penalties"]
    s["score_permit"] = [max(0, 100 - sum(pen[f] for f in fl)) for fl in s["constraints_soft"]]
    dw = W["dc"]
    wsv = s["water_stress"].fillna(dw["water_missing"])
    s["score_dc"] = (dw["w_fiber"] * 100 * np.exp(-s["fiber_km"] / dw["fiber_decay_km"])
                     + dw["w_water"] * np.clip(100 * (1 - wsv / 5.0), 0, 100)
                     + dw["w_road"] * 100 * np.exp(-s["road_km"] / dw["road_decay_km"])
                     + dw["w_load"] * 100 * np.exp(-s["dist_sub230_km"].fillna(999) / dw["load_decay_km"]))
    for col in ["score_grid", "score_land", "score_sun", "score_permit", "score_dc"]:
        s[col] = s[col].astype(float).round(1)
    for track in ("solar", "dc"):
        fw = W["factor_" + track]
        s["score_total_" + track] = (sum(fw[k] * s["score_" + k] for k in fw) / sum(fw.values())).round(2)
    s["score_total"] = s["score_total_solar"]  # app contract alias
    # ranks only for the candidate pool (within max_sub_km of a POI); others scored but unranked
    pool = s["in_grid_pool"].values
    s = s.sort_values(["in_grid_pool", "score_total_dc", "acres"], ascending=[False, False, False])
    s["rank_dc"] = np.where(s["in_grid_pool"], np.cumsum(s["in_grid_pool"].values), np.nan)
    s = s.sort_values(["in_grid_pool", "score_total_solar", "acres"], ascending=[False, False, False]).reset_index(drop=True)
    pool = s["in_grid_pool"].values
    s["rank_solar"] = np.where(pool, np.cumsum(pool), np.nan)
    s["rank"] = s["rank_solar"]
    seq = np.cumsum(~pool)
    s["site_id"] = [f"SW-{st}-{int(r):05d}" if p else f"SW-{st}-U{int(q):05d}"
                    for st, r, p, q in zip(s["state"], s["rank_solar"].fillna(0), pool, seq)]
    for c in ("rank_dc", "rank_solar", "rank"):
        s[c] = s[c].astype("Int64")
    s["solar_mw_est"] = (s["acres"] / SCREEN["acres_per_mw"]).round(0)
    return s


def fmt_km(x):
    return f"{x:.1f} km" if pd.notna(x) else "unknown distance"


def next_step(r):
    sub = r["nearest_sub_name"] if isinstance(r["nearest_sub_name"], str) and r["nearest_sub_name"] else r["nearest_sub_id"]
    kv = f"{r['nearest_sub_kv']:.0f} kV" if pd.notna(r["nearest_sub_kv"]) else "kV unknown"
    utility = r["nearest_sub_owner"] if isinstance(r["nearest_sub_owner"], str) and r["nearest_sub_owner"] not in ("", "NOT AVAILABLE") else "the transmission owner"
    grid = (f"ask {utility} about capacity at {sub} ({kv}, {fmt_km(r['dist_sub_km'])}) via a pre-application "
            f"or interconnection request")
    if r.get("sub_provisional"):
        grid += (" (substation record is provisional: first confirm it exists, its operating voltage and owner "
                 "against the utility's one-line diagram)")
    o = r["owner_category"]; st = r["state"]
    if o == "BLM" and r["blm_solar_available"]:
        fo = f"BLM {r['blm_fo_hint']}" if r["blm_fo_hint"] else "the BLM field office"
        sez = f" (inside the {r['sez_name']} Solar Energy Zone)" if r["sez_name"] else ""
        comp = (f"; MLRS shows overlapping active solar case(s) {r['row_cases_overlap']}, so check for a competing "
                f"application first" if r["row_cases_overlap"] else "; check MLRS for competing applications")
        return (f"Request a pre-application meeting (43 CFR 2804.10) with {fo} (nearest MLRS solar case is in this "
                f"office; confirm jurisdiction){sez}{comp}; {grid}. Budget rent at 3.9% of gross proceeds.")
    if o == "BLM" and r["blm_status"] == "DRECP Variance Land (CA)":
        return (f"DRECP Variance Land: discuss variance process with BLM {r['blm_fo_hint'] or 'field office'} "
                f"before investing; {grid}.")
    if o == "BLM":
        return ("BLM land outside Western Solar Plan Available areas / DRECP DFAs: BLM will not accept a solar ROW "
                f"without a plan amendment. Deprioritise, or look at adjacent State/Private land; {grid}.")
    if o == "State":
        return (f"Contact the {STATE_TRUST.get(st, 'state land agency')} about a solar/commercial lease or auction for "
                f"this trust land; {grid}.")
    if o == "Private":
        return (f"Pull parcel owners from the {r['county']} County assessor and approach for an option/lease; check "
                f"county zoning for utility-scale solar; {grid}.")
    if o == "USFS":
        return f"National Forest land: utility-scale solar is rarely authorised; deprioritise. {grid[0].upper() + grid[1:]}."
    return f"Ownership 'Other' (e.g. USBR, FWS, local government): confirm managing agency and whether solar is allowed; {grid}."


CONTRACT = ["site_id", "state", "county", "acres", "owner_category", "blm_solar_available", "sez_name",
            "centroid_lat", "centroid_lon", "nearest_sub_id", "nearest_sub_name", "nearest_sub_kv", "dist_sub_km",
            "nearest_line_kv", "dist_line_km", "queued_mw_county", "ghi", "mean_slope", "constraints_soft",
            "fiber_km", "water_stress", "road_km", "score_grid", "score_land", "score_sun", "score_permit",
            "score_dc", "score_total", "rank", "next_step"]
EXTRA = ["blm_status", "blm_avail_pct", "solar_mw_est", "nearest_sub_owner", "nearest_sub_queue_mw",
         "nearest_sub230_name", "nearest_sub230_kv", "dist_sub230_km", "nearest_line230_kv", "dist_line230_km",
         "queued_mw_county_solar", "queued_mw_county_storage", "fiber_basis", "road_name", "water_stress_label",
         "row_cases_overlap", "blm_fo_hint", "blm_fo_hint_km", "county_fips", "block_id",
         # two rankings and review flags (2026-10-21)
         "score_total_solar", "score_total_dc", "rank_solar", "rank_dc",
         "sub_source", "sub_kv_source", "sub_provisional", "nearest_sub230_id",
         "queue_confidence", "queue_poi_match_rate", "queue_n_active_county"]


# ---------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------
def write_geojson(s, path):
    g = s.to_crs("EPSG:4326")
    feats = []
    for r, geom in zip(g[CONTRACT + EXTRA].to_dict("records"), g.geometry):
        props = {}
        for k, v in r.items():
            if isinstance(v, (np.floating, float)):
                v = None if not np.isfinite(v) else round(float(v), 4)
            elif isinstance(v, (np.integer,)):
                v = int(v)
            elif isinstance(v, (np.bool_,)):
                v = bool(v)
            elif isinstance(v, (list, tuple, np.ndarray)):
                v = "; ".join(map(str, v))  # constraints_soft as a semicolon-joined string
            elif v is pd.NA or v is None:
                v = None
            props[k] = v
        geom = shapely.set_precision(geom, 1e-6)
        feats.append({"type": "Feature", "properties": props, "geometry": shapely.geometry.mapping(geom)})
    with open(path, "w") as f:
        json.dump({"type": "FeatureCollection", "name": "candidate_sites",
                   "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
                   "features": feats}, f, separators=(",", ":"))


def table(s):
    t = pd.DataFrame(s[CONTRACT + EXTRA])
    t["constraints_soft"] = t["constraints_soft"].map(lambda x: "; ".join(x))
    for c in ["acres", "ghi", "mean_slope"]:
        t[c] = t[c].astype(float).round(2 if c != "acres" else 0)
    return t


def check_hard(s):
    """Re-read candidate_sites.geojson and test it against every hard-exclusion feature
    (full-res layers, map copies, SMA Tribal/NPS/DOD), in EPSG:5070 on subdivided polygons."""
    g = gpd.read_file(OUT / "candidate_sites.geojson").to_crs(CRS)
    sg = g.geometry.values
    rows = []
    for lyr in pyogrio.list_layers(P / "land/exclusions_full.gpkg")[:, 0]:
        e = gpd.read_file(P / "land/exclusions_full.gpkg", layer=lyr, columns=["kind"])
        rows.append(("exclusions_full.gpkg:" + lyr, e[e["kind"] == "hard"]))
    for f in sorted((P / "land/exclusions").glob("*.geojson")):
        e = gpd.read_file(f, columns=["kind"])
        rows.append(("exclusions/" + f.name, e[e["kind"] == "hard"]))
    o = gpd.read_file(P / "land/ownership.gpkg", layer="ownership", columns=["category"])
    rows.append(("ownership.gpkg: Tribal/NPS/DOD", o[o["category"].isin(HARD_OWNERS)]))
    out = []
    for name, e in rows:
        if len(e) == 0:
            out.append({"layer": name, "hard_features": 0, "sites_intersecting": 0, "overlap_acres": 0.0})
            continue
        pieces = subdivide(shapely.make_valid(e.to_crs(CRS).geometry.values))
        tree = shapely.STRtree(pieces)
        i_in, i_t = tree.query(sg, predicate="intersects")
        oa = float(shapely.area(shapely.intersection(sg[i_in], pieces[i_t])).sum() / ACRE) if len(i_in) else 0.0
        out.append({"layer": name, "hard_features": len(e), "sites_intersecting": int(len(np.unique(i_in))),
                    "overlap_acres": round(oa, 4)})
        log.info("check %s: %d sites intersect", name, out[-1]["sites_intersecting"])
    df = pd.DataFrame(out)
    df.to_csv(OUT / "hard_exclusion_check.csv", index=False)
    log.info("hard exclusion check:\n%s", df.to_string(index=False))
    return df


def sources():
    rows = []
    for dom in ["grid", "land", "infra"]:
        m = json.load(open(P / dom / "MANIFEST.json"))
        m = m if isinstance(m, list) else m.get("layers", list(m.values()))
        for e in m:
            cav = e.get("caveats", "")
            if isinstance(cav, list):
                cav = " ".join(map(str, cav))
            rows.append({"domain": dom, "layer": e.get("layer"), "source": e.get("source_name"),
                         "url": e.get("source_url"), "retrieved": e.get("retrieved"),
                         "records": e.get("record_count"), "caveats": cav})
    return pd.DataFrame(rows)


def md_table(df):
    out = ["| " + " | ".join(df.columns) + " |", "|" + "---|" * len(df.columns)]
    out += ["| " + " | ".join(str(v) for v in r) + " |" for r in df.itertuples(index=False)]
    return "\n".join(out)


def poi_check(s_pool):
    """No top-50 site (either ranking) may use a removed POI as its nearest substation."""
    ex = pd.read_csv(OUT / "excluded_pois.csv", usecols=["id", "name", "removed_reason"])
    exid = set(ex["id"].astype(str))
    rows = []
    for track in ("solar", "dc"):
        top = s_pool.sort_values("rank_" + track).head(50)
        for col in ("nearest_sub_id", "nearest_sub230_id"):
            bad = top[top[col].astype(str).isin(exid)]
            rows.append({"ranking": f"top 50 {track}", "field": col, "sites": len(top),
                         "sites_using_excluded_poi": len(bad),
                         "examples": "; ".join(bad["site_id"].head(5))})
    v1 = OUT / "top_sites_v1.csv"
    if v1.exists():
        old = pd.read_csv(v1, usecols=["site_id", "nearest_sub_id", "nearest_sub_name"])
        bad = old[old["nearest_sub_id"].astype(str).isin(exid)]
        rows.append({"ranking": "v1 top 50 (before fixes, for reference)", "field": "nearest_sub_id", "sites": len(old),
                     "sites_using_excluded_poi": len(bad),
                     "examples": "; ".join(f"{a} ({b})" for a, b in zip(bad["site_id"].head(5), bad["nearest_sub_name"].head(5)))})
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "poi_check.csv", index=False)
    log.info("POI check:\n%s", df.drop(columns="examples").to_string(index=False))
    return df


def compare_v1(s_all):
    """Before/after table: v1 top 10 (old single ranking) vs the new solar and DC ranks."""
    v1 = OUT / "work" / "all_sites_v1_ranks.csv"
    if not v1.exists():
        return "(v1 ranks not available)", "(v1 ranks not available)"
    old = pd.read_csv(v1)
    key = lambda df: df["centroid_lat"].round(4).astype(str) + "," + df["centroid_lon"].round(4).astype(str)
    old["k"] = key(old)
    new = s_all.assign(k=key(s_all))[["k", "site_id", "rank_solar", "rank_dc", "score_total_solar", "score_total_dc",
                                      "nearest_sub_name", "nearest_sub_kv", "dist_sub_km", "sub_provisional",
                                      "queue_confidence", "state", "county", "owner_category"]]
    new = new.drop_duplicates("k")
    a = old.sort_values("rank").head(10).merge(new, on="k", how="left", suffixes=("_v1", ""))

    def fr(x):
        return "-" if pd.isna(x) else f"{int(x)}"
    ra = ["| v1 rank | v1 site_id | v1 score | v1 nearest substation | new site_id | new solar rank | new DC rank | new solar score | new nearest substation | provisional |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for _, r in a.iterrows():
        if pd.isna(r["site_id"]):
            ra.append(f"| {int(r['rank'])} | {r['site_id_v1']} | {r['score_total']:.2f} | {r['nearest_sub_name_v1']} | not matched | - | - | - | - | - |")
            continue
        ra.append(f"| {int(r['rank'])} | {r['site_id_v1']} | {r['score_total']:.2f} | {r['nearest_sub_name_v1']} | "
                  f"{r['site_id'] if pd.notna(r['site_id']) else 'not matched'} | {fr(r['rank_solar'])} | {fr(r['rank_dc'])} | "
                  f"{r['score_total_solar']:.2f} | {r['nearest_sub_name']} ({r['dist_sub_km']:.1f} km) | {bool(r['sub_provisional'])} |")
    b = new.dropna(subset=["rank_solar"]).sort_values("rank_solar").head(10).merge(
        old[["k", "site_id", "rank", "score_total"]].rename(columns={"site_id": "site_id_v1"}), on="k", how="left")
    rb = ["| new solar rank | site_id | state / county | owner | solar score | DC rank | nearest substation | provisional | queue confidence | v1 rank | v1 site_id |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for _, r in b.iterrows():
        rb.append(f"| {int(r['rank_solar'])} | {r['site_id']} | {r['state']} / {r['county']} | {r['owner_category']} | "
                  f"{r['score_total_solar']:.2f} | {fr(r['rank_dc'])} | {r['nearest_sub_name']} {r['nearest_sub_kv']:.0f} kV, "
                  f"{r['dist_sub_km']:.1f} km | {bool(r['sub_provisional'])} | {r['queue_confidence']} | {fr(r['rank'])} | "
                  f"{r['site_id_v1'] if pd.notna(r['site_id_v1']) else '-'} |")
    return "\n".join(ra), "\n".join(rb)


def method_md(s, chk, stats, poi, cmp_tables, s_all):
    W = WEIGHTS; g = W["grid"]; l = W["land"]; d = W["dc"]
    pen = "\n".join(f"| {k} | {v} |" for k, v in W["permit"]["penalties"].items())
    kvp = ", ".join(f">= {a} kV: {b}" for a, b in g["kv_points"])
    fs, fd = W["factor_solar"], W["factor_dc"]
    rem = s_all.attrs.get("poi_removed", {})
    n_prov_top = {t: int(s.sort_values("rank_" + t).head(50)["sub_provisional"].sum()) for t in ("solar", "dc")}
    qc = s["queue_confidence"].value_counts()
    lines = f"""# Candidate site screening and scoring method

Generated by `pipeline/screen.py` on {time.strftime('%Y-%m-%d')}. Re-run: `uv run --script pipeline/screen.py --force`
(`--force` rebuilds the cell and geometry caches in `data/processed/sites/work/`; without it the caches are reused and only
substations, queue, scores and outputs are recomputed). The weights and transforms below are the `WEIGHTS` and `SCREEN`
dicts at the top of `screen.py`.

## 0. Changes in this version (after the independent methodology review, 2026-10-21)
The review (`southwest-solar-siting-review/review/METHODOLOGY_REVIEW.md`) rated the first screen 5/10 and asked for
separate tracks and honest grid uncertainty. Changes:
1. **Two rankings.** `score_total_solar` (grid {fs['grid']} / land {fs['land']} / sun {fs['sun']} / permit {fs['permit']}, no data center term)
   and `score_total_dc` (grid {fd['grid']} / land {fd['land']} / sun {fd['sun']} / permit {fd['permit']} / dc {fd['dc']}). `rank_solar` and
   `rank_dc`. `score_total` and `rank` are aliases of the solar values (app contract). `site_id` follows the solar rank.
   `top_sites.csv` = top 50 by solar; `top_sites_dc.csv` = top 50 by data center score.
2. **Provisional grid flags.** Each site carries `sub_source` (hifld / osm), `sub_kv_source` (hifld / osm / osm_match /
   inferred_from_lines) and `sub_provisional` (true when the substation is OSM-only, its kV came from OSM or was inferred
   from nearby lines, or its name starts with UNKNOWN). The grid score of a site whose nearest substation is provisional is
   multiplied by {g['provisional_mult']}. This is a modest penalty for unverified data, not a statement that the substation is
   unusable. {s_all.attrs.get('poi_provisional', 'n/a')} of {s_all.attrs.get('poi_kept', 'n/a')} usable 115 kV+ substations are provisional;
   {n_prov_top['solar']} of the top 50 solar sites and {n_prov_top['dc']} of the top 50 data center sites have a provisional nearest substation.
3. **Unsuitable POIs removed before the nearest-substation search.** Removed: HVDC converter stations (name contains HVDC,
   Converter or AC-DC, or ends in TIE: the two SunZia converter stations and the Eddy County and Blackwater back-to-back
   AC-DC-AC ties in New Mexico, which link asynchronous grids rather than serve as generator POIs), generator-owned / plant collector substations (sub_type GENERATION, an
   owner name with Solar, Wind, Renewable, Energy Center or Collector, or a substation name with Solar, Wind, Energy Center,
   Collector, Generat/Cogen/Gen when the owner is missing; a utility-owned substation with such a name, e.g. SCE Windhub, is
   kept), retired / not-in-service status, and the sub_types already excluded in v1 ({', '.join(SCREEN['sub_types_excluded'])}).
   Removed this run: {', '.join(f'{k} {v}' for k, v in rem.items())} (list in `excluded_pois.csv`). HIFLD status is
   "NOT AVAILABLE" for many substations; those are kept, since unknown status is not evidence of retirement.
4. **Queue congestion confidence.** The county term is kept, but counties with 0 active queue MW now score the neutral
   midpoint ({g['queue_unknown_score']:.0f}) instead of the best value, because 0 MW usually means no matched record, not an empty queue.
   `queue_confidence` = high when the county has at least one active project matched to a substation by POI name and at least
   {g['queue_match_min']:.0%} of the county's active projects are matched; otherwise low (including all 0 MW counties).
   `queue_poi_match_rate` and `queue_n_active_county` are included. Ranked sites: {', '.join(f'{k} {v:,}' for k, v in qc.items())}.
5. `constraints_soft` is written to the GeoJSON as a semicolon-joined string (v1 dropped it in the GeoPackage).

Not fixed here (still open from the review): parcel-level BLM legal status and encumbrances, utility territory and real
headroom, confirmed fiber (the fiber layer is still 99% proxy, which weakens the data center ranking), cost and schedule
modelling, and weight/decay sensitivity runs.

### Before / after: v1 top 10 and where those sites rank now
Sites are matched by representative point (same polygons; only scoring changed). v1 ranks came from the single
blended score (grid 30 / land 25 / sun 15 / permit 15 / dc 15).

{cmp_tables[0]}

Why ranks moved: the solar ranking drops the data center term, so sites whose v1 rank leaned on fiber, road and water
(for example the Griffith, AZ site) fall in the solar ranking but stay near the top of the data center ranking; sites whose
nearest substation is provisional lose 15 percent of their grid score (for example North Loving Sub, an OSM-only record);
and sites in counties with 0 active queue MW no longer get the best queue score. Polygons, acres, land, sun and permitting
inputs did not change.

### New top 10 (solar ranking) and their v1 rank

{cmp_tables[1]}

## 1. Candidate sites
1. Cell grid: {SCREEN['cell_m']} m cells in EPSG:5070 covering CA, AZ, NV, NM, UT (Census state boundaries).
2. Per cell: state (cell centre), surface owner from the BLM Surface Management Agency layer (cell centre; gaps treated as Private),
   BLM solar status from `blm_solar_available.gpkg` (cell centre), share of the cell under any hard exclusion
   (rasterised on a {SCREEN['cell_m'] // SCREEN['sub']} m sub-grid), mean slope and share of 90 m slope pixels above 5 percent
   (`slope.tif`, every pixel assigned to the cell containing its centre), and GHI (`ghi.tif`, value at cell centre).
3. Hard exclusions (every feature with kind = hard): wilderness and WSAs, NCAs and national monuments, critical habitat,
   FEMA flood zones A/AE/AH/AO/V/VE, tribal areas, military, urban areas, NPS land, slope_gt5 polygons, and SMA
   Tribal/NPS/DOD land. A cell is kept when hard-exclusion share < {SCREEN['max_excl_frac']}, steep-pixel share
   < {SCREEN['max_steep_frac']} and mean slope <= {SCREEN['max_mean_slope']} percent.
4. Kept cells are joined (4-connected) into blocks with the same ownership key (owner category, and for BLM the solar
   status). Blocks under {SCREEN['min_cells']} cells are dropped. Blocks over {SCREEN['split_cells']} cells (about
   {SCREEN['split_cells'] * 247:,} acres) are split on a {SCREEN['tile_cells']} x {SCREEN['tile_cells']} km tile grid
   (about 3,950 acres per tile); tile fragments under 4 cells are merged into a neighbouring piece of the same block.
5. Each site polygon is then cut exactly against all hard-exclusion polygons (full-resolution layers from
   `exclusions_full.gpkg`, the simplified map copies in `exclusions/`, and SMA Tribal/NPS/DOD), keeping a
   {SCREEN['gap_m']:.0f} m gap. Pieces of at least {SCREEN['min_acres']:.0f} acres are kept as sites.
6. Candidate pool: sites whose edge is within {SCREEN['max_sub_km']:.0f} km of a usable {SCREEN['sub_kv_min']} kV+ substation (after the POI filter)
   are ranked and written to `candidate_sites.geojson`; the rest are scored but unranked (site_id `SW-<state>-U#####`) and
   appear only on the Excel All Sites sheet.
   Delivered polygons are inset {SCREEN['inset_m']:.0f} m and simplified with a {SCREEN['simplify_m']:.0f} m tolerance so they stay
   inside the exact cut and the GeoJSON stays small; `acres` is the area of the exact cut before the inset.
7. GHI and mean slope per site are the means of the 1 km cell values under the site before the exact cut
   (slope cells are means of ~90 m pixels), so they are zonal means at 1 km resolution.
8. 600 acres is about 86-120 MW at 5-7 acres/MW, a ~100 MW threshold. A 1 GW project needs roughly 5,000-7,000 usable acres.

Counts this run: {stats}

## 2. Fields
Contract fields are listed in TEAM/SPEC.md. Notes: distances are edge-of-site to feature, in km, EPSG:5070.
`nearest_sub_*` is the nearest usable substation with max_kv >= {SCREEN['sub_kv_min']} kV (POI filter in section 0).
`nearest_line_kv`/`dist_line_km` use lines >= 115 kV (not INACTIVE); `dist_line230_km` uses lines >= 230 kV.
`queued_mw_county` is active queue MW (all types; hybrid components summed as in `queue_by_county.csv`) in the site's county
(Queued Up 2026 + CAISO). It is nameplate MW requested, not transmission headroom. `water_stress` is WRI Aqueduct baseline water
stress 0-5 (5 worst) at the site's representative point. `fiber_km` uses a PROXY layer (OSM telecom lines, interstate and
Class I rail corridors), not real fiber routes. `blm_solar_available` is True when the site is BLM land and at least 50 percent
of it lies in Western Solar Plan Available land or a DRECP Development Focus Area (DRECP Variance Land is reported in
`blm_status` but not counted as available). `solar_mw_est` = acres / {SCREEN['acres_per_mw']}.
`blm_fo_hint` is the field office of the nearest MLRS solar case; it is a hint, not a jurisdiction lookup.

## 3. Scores (each 0-100)
**score_total_solar** = (grid x {fs['grid']} + land x {fs['land']} + sun x {fs['sun']} + permit x {fs['permit']}) / {sum(fs.values())}

**score_total_dc** = (grid x {fd['grid']} + land x {fd['land']} + sun x {fd['sun']} + permit x {fd['permit']} + dc x {fd['dc']}) / {sum(fd.values())}

**Grid** = [{g['w_sub_dist']} x 100 exp(-dist_sub_km / {g['sub_decay_km']}) + {g['w_line_dist']} x 100 exp(-dist_line230_km / {g['line_decay_km']})
+ {g['w_kv']} x kV points ({kvp}) + {g['w_queue']} x queue term] x ({g['provisional_mult']} if sub_provisional else 1).
Queue term = 100 exp(-queued GW in county / {g['queue_decay_gw']}) when the county has active MW, else {g['queue_unknown_score']:.0f} (unknown).
Queue MW is a congestion penalty: public data shows how much is queued, not how much capacity is left.

**Land** = {l['w_owner']} x ownership points + {l['w_slope']} x 100 (1 - mean_slope / 5) + {l['w_size']} x 100 min(1, acres / {l['size_full_acres']}).
Ownership points: {', '.join(f'{k} {v}' for k, v in l['owner_base'].items())}. BLM solar-available bonus added to the BLM base:
Western Solar Plan Available +{l['blm_bonus']['available']}, DRECP DFA +{l['blm_bonus']['dfa']}, DRECP Variance +{l['blm_bonus']['variance']},
inside a developable SEZ +{l['blm_bonus']['sez']} (capped at 100). BLM land outside Available/DFA keeps only the base, because under the 2024
Western Solar Plan BLM will not accept utility-scale solar applications there without a plan amendment.

**Sun** = 100 x (GHI - {W['sun']['ghi_lo']}) / ({W['sun']['ghi_hi']} - {W['sun']['ghi_lo']}), clipped 0-100 (GHI in kWh/m2/day, NSRDB 1998-2016).

**Permit** = 100 minus penalties for each flag in `constraints_soft`, floor 0:

| flag | penalty |
|---|---|
{pen}

**Data center fit** (DC ranking only) = {d['w_fiber']} x 100 exp(-fiber_km / {d['fiber_decay_km']}) + {d['w_water']} x 100 (1 - water_stress / 5)
+ {d['w_road']} x 100 exp(-road_km / {d['road_decay_km']}) + {d['w_load']} x 100 exp(-dist to 230 kV+ substation / {d['load_decay_km']}).
Missing water stress is set to {d['water_missing']}. Fiber is a proxy, so treat the DC ranking as weaker than the solar ranking.

Excel (`deliverables/Southwest_Solar_Sites.xlsx`): Top 50 Solar and Top 50 Data Center sheets recompute their totals and
in-sheet rank with live formulas from the factor scores and the editable weights block on the Method sheet; All Sites holds
plain values for every scored site (ranked and unranked).

## 4. Hard-exclusion check (sites re-read from candidate_sites.geojson, EPSG:4326)
{md_table(chk)}

## 5. POI check (no top-50 site may use a removed POI)
{md_table(poi.drop(columns='examples'))}

## 6. Limits
- Screening, not engineering. Public data shows where lines and substations are, not spare capacity or a usable bay.
- HIFLD substations were last edited 2021-02-25 at the source; OSM additions are unverified.
- Ownership is the surface managing agency (SMA), not title; split estate and private parcel boundaries are not shown.
- Critical habitat covers designated habitat only; species ranges (e.g. desert tortoise) are not mapped here.
- FEMA flood mapping is missing in many rural counties; unmapped is not flood-free.
- Fiber is a proxy. Water stress is a basin score, not a water right.
- Distances are straight-line; gen-tie routing, terrain and crossings are not modelled.
- Weights and decay lengths are policy choices; no sensitivity analysis has been run yet.
"""
    (OUT / "METHOD.md").write_text(lines)


TOP_COLS = ["rank", "site_id", "state", "county", "centroid_lat", "centroid_lon", "acres", "solar_mw_est",
            "owner_category", "blm_status", "blm_solar_available", "sez_name", "nearest_sub_name", "nearest_sub_kv",
            "dist_sub_km", "nearest_sub_owner", "sub_source", "sub_kv_source", "sub_provisional", "nearest_line_kv",
            "dist_line_km", "dist_line230_km", "queued_mw_county", "queue_confidence", "ghi", "mean_slope",
            "constraints_soft", "fiber_km", "fiber_basis", "water_stress", "road_km",
            "score_grid", "score_land", "score_sun", "score_permit", "score_dc", "TOTAL",
            "rank_solar", "rank_dc", "next_step", "row_cases_overlap", "blm_fo_hint", "nearest_sub_id"]


def _cell(ws, row, j, v, fmt=None):
    if v is None or v is pd.NA or (isinstance(v, (float, np.floating)) and not np.isfinite(v)):
        ws.write_blank(row, j, None)
    elif isinstance(v, (bool, np.bool_)):
        ws.write_boolean(row, j, bool(v))
    elif isinstance(v, (int, float, np.integer, np.floating)):
        ws.write_number(row, j, float(v), fmt)
    else:
        ws.write_string(row, j, str(v))


def write_excel(s_all, s_pool, chk, poi, src):
    import xlsxwriter
    from xlsxwriter.utility import xl_col_to_name
    stage("Excel workbook")
    XLSX.parent.mkdir(parents=True, exist_ok=True)
    wb = xlsxwriter.Workbook(str(XLSX), {"nan_inf_to_errors": True, "constant_memory": True})
    hdr = wb.add_format({"bold": True, "bg_color": "#DDE6EE", "border": 1, "text_wrap": True, "valign": "top"})
    num2 = wb.add_format({"num_format": "0.00"}); num0 = wb.add_format({"num_format": "#,##0"})
    bold = wb.add_format({"bold": True}); wrap = wb.add_format({"text_wrap": True, "valign": "top"})
    yel = wb.add_format({"bg_color": "#FFF2AB", "border": 1})
    fmt_of = lambda c: num2 if c in ("ghi", "mean_slope", "TOTAL") else (num0 if c in ("acres", "queued_mw_county", "solar_mw_est") else None)
    fs, fd = WEIGHTS["factor_solar"], WEIGHTS["factor_dc"]
    factors = ["grid", "land", "sun", "permit", "dc"]

    def top_sheet(name, df, track):
        ws = wb.add_worksheet(name)
        cols = TOP_COLS
        fi = {c: i for i, c in enumerate(cols)}
        L = {c: xl_col_to_name(fi[c]) for c in cols}
        label = {"TOTAL": f"score_total_{track}", "rank": f"rank in sheet ({track})"}
        for j, c in enumerate(cols):
            ws.write(0, j, label.get(c, c), hdr)
        n = len(df)
        pre = "ws_" if track == "solar" else "wd_"
        fl = [f for f in factors if (track == "dc" or f != "dc")]
        cached_rank = df["score_total_" + track].rank(method="min", ascending=False).astype(int).values
        tot = L["TOTAL"]
        for i, r in enumerate(df.to_dict("records")):
            row = i + 1; e = row + 1
            for j, c in enumerate(cols):
                if c == "rank":
                    ws.write_formula(row, j, f"=RANK({tot}{e},${tot}$2:${tot}${n + 1},0)", None, int(cached_rank[i]))
                elif c == "TOTAL":
                    num = "+".join(f"{pre}{f}*{L['score_' + f]}{e}" for f in fl)
                    den = "+".join(f"{pre}{f}" for f in fl)
                    ws.write_formula(row, j, f"=ROUND(({num})/({den}),2)", num2, float(r["score_total_" + track]))
                else:
                    _cell(ws, row, j, r[c], fmt_of(c))
        ws.write(n + 2, 0, f"score_total_{track} and the in-sheet rank are live formulas using the weights block on the Method "
                 "sheet (yellow cells). Grid scores already include the x0.85 provisional-substation penalty. rank_solar and "
                 "rank_dc are the overall ranks at default weights.")
        ws.freeze_panes(1, 2); ws.autofilter(0, 0, n, len(cols) - 1)
        ws.set_column(0, 0, 7); ws.set_column(1, 1, 15); ws.set_column(fi["next_step"], fi["next_step"], 90)
        ws.set_column(fi["constraints_soft"], fi["constraints_soft"], 30)
        ws.set_column(fi["blm_status"], fi["blm_status"], 30); ws.set_column(fi["nearest_sub_name"], fi["nearest_sub_name"], 22)

    top_sheet("Top 50 Solar", s_pool.sort_values("rank_solar").head(50), "solar")
    top_sheet("Top 50 Data Center", s_pool.sort_values("rank_dc").head(50), "dc")

    # Provisional data note
    pv = wb.add_worksheet("Provisional Data")
    note = [
        "Provisional data: read before using any site",
        "",
        "sub_provisional = TRUE means the nearest substation record is not confirmed by HIFLD: it is OSM-only, its voltage came",
        "from OSM or was inferred from nearby lines, or its name starts with UNKNOWN. These sites get a x0.85 grid score penalty.",
        "Even non-provisional HIFLD records were last edited at the source in February 2021 and do not show spare capacity.",
        "queue_confidence = low means the county queue MW could not be tied to specific substations (or the county shows 0 active MW,",
        "which is treated as unknown, not empty). The queue term is a county-level congestion signal only.",
        "fiber_km uses a proxy layer (99% of features are OSM telecom lines, interstates or rail corridors, not confirmed fiber).",
        "Ownership is the BLM Surface Management Agency layer, not title. BLM availability is from the 2024 Western Solar Plan GIS.",
        "Removed POIs (HVDC converters, plant collector substations, retired) are listed in data/processed/sites/excluded_pois.csv.",
        "",
        "Top-50 sites (either ranking) with a provisional substation or low queue confidence:",
    ]
    for i, t in enumerate(note):
        pv.write_string(i, 0, t, bold if i == 0 else None)
    tops = pd.concat([s_pool.sort_values("rank_solar").head(50), s_pool.sort_values("rank_dc").head(50)]).drop_duplicates("site_id")
    tops = tops[tops["sub_provisional"] | (tops["queue_confidence"] != "high")].sort_values("rank_solar")
    pcols = ["site_id", "rank_solar", "rank_dc", "state", "county", "nearest_sub_name", "nearest_sub_kv", "sub_source",
             "sub_kv_source", "sub_provisional", "queued_mw_county", "queue_confidence", "queue_poi_match_rate"]
    r0 = len(note) + 1
    for j, c in enumerate(pcols):
        pv.write(r0, j, c, hdr)
    for i, r in enumerate(tops[pcols].to_dict("records")):
        for j, c in enumerate(pcols):
            _cell(pv, r0 + 1 + i, j, r[c])
    pv.set_column(0, 0, 16); pv.set_column(5, 5, 26)

    # All Sites: plain values, every scored site
    stage("Excel All Sites sheet")
    al = wb.add_worksheet("All Sites")
    acols = ["in_grid_pool"] + [c for c in CONTRACT + EXTRA if c not in ("geometry",)]
    for j, c in enumerate(acols):
        al.write(0, j, c, hdr)
    t = s_all.sort_values(["in_grid_pool", "score_total_solar"], ascending=[False, False])
    recs = t[acols].to_dict("records")
    for i, r in enumerate(recs):
        for j, c in enumerate(acols):
            v = r[c]
            if c == "constraints_soft" and isinstance(v, (list, tuple, np.ndarray)):
                v = "; ".join(v)
            _cell(al, i + 1, j, v, fmt_of(c))
        if i % 10000 == 0:
            log.info("Excel All Sites: %d / %d rows", i, len(recs))
    al.freeze_panes(1, 2); al.autofilter(0, 0, len(recs), len(acols) - 1)

    # Method sheet: weights block (named ranges used by the Top 50 formulas) + method text
    ms = wb.add_worksheet("Method")
    ms.write(0, 0, "Weights (edit the yellow cells; Top 50 Solar and Top 50 Data Center recompute totals and in-sheet rank)", bold)
    ms.write(1, 0, "factor", hdr); ms.write(1, 1, "solar", hdr); ms.write(1, 2, "data center", hdr)
    for i, f in enumerate(factors):
        ms.write(2 + i, 0, f)
        if f in fs:
            ms.write_number(2 + i, 1, fs[f], yel); wb.define_name(f"ws_{f}", f"=Method!$B${3 + i}")
        else:
            ms.write(2 + i, 1, "n/a (not in solar track)")
        ms.write_number(2 + i, 2, fd[f], yel); wb.define_name(f"wd_{f}", f"=Method!$C${3 + i}")
    ms.write(7, 0, "sum")
    ms.write_formula(7, 1, "=SUM(B3:B6)", None, sum(fs.values()))
    ms.write_formula(7, 2, "=SUM(C3:C7)", None, sum(fd.values()))
    ms.write(9, 0, "Method (full text in data/processed/sites/METHOD.md)", bold)
    rr = 10
    for line in (OUT / "METHOD.md").read_text().splitlines():
        ms.write_string(rr, 0, line.replace("**", "")); rr += 1
    ms.set_column(0, 0, 30); ms.set_column(1, 2, 12)

    ss = wb.add_worksheet("Sources")
    for j, c in enumerate(src.columns):
        ss.write(0, j, c, hdr)
    for i, r in enumerate(src.to_dict("records")):
        for j, c in enumerate(src.columns):
            _cell(ss, i + 1, j, r[c])
    ss.set_column(0, 1, 18); ss.set_column(2, 3, 60); ss.set_column(6, 6, 100)

    hc = wb.add_worksheet("Checks")
    hc.write(0, 0, "Hard-exclusion check (candidate_sites.geojson vs every hard layer)", bold)
    for j, c in enumerate(chk.columns):
        hc.write(1, j, c, hdr)
    for i, r in enumerate(chk.to_dict("records")):
        for j, c in enumerate(chk.columns):
            _cell(hc, 2 + i, j, r[c])
    r0 = len(chk) + 4
    hc.write(r0, 0, "POI check (top 50 sites vs removed POIs)", bold)
    for j, c in enumerate(poi.columns):
        hc.write(r0 + 1, j, c, hdr)
    for i, r in enumerate(poi.to_dict("records")):
        for j, c in enumerate(poi.columns):
            _cell(hc, r0 + 2 + i, j, r[c])
    hc.set_column(0, 0, 45)

    wb.close()
    log.info("Excel written: %s", XLSX)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="redo every stage incl. cell and geometry caches")
    ap.add_argument("--rescore", action="store_true",
                    help="reuse the cell/geometry/attribute caches but redo substations, queue, scores and outputs")
    a = ap.parse_args()
    setup_log()
    start_heartbeat(30)
    OUT.mkdir(parents=True, exist_ok=True); WORK.mkdir(parents=True, exist_ok=True)
    outs = [OUT / "candidate_sites.geojson", OUT / "top_sites.csv", OUT / "top_sites_dc.csv", XLSX]
    if all(p.exists() for p in outs) and not (a.force or a.rescore):
        log.info("screen: outputs exist; skipping (use --force to redo)")
        return
    t = time.time()
    # keep v1 ranks for the before/after table (first run after the review only)
    v1r = WORK / "all_sites_v1_ranks.csv"
    if not v1r.exists() and (OUT / "all_sites.csv").exists():
        old = pd.read_csv(OUT / "all_sites.csv", usecols=["site_id", "rank", "score_total", "centroid_lat",
                                                          "centroid_lon", "nearest_sub_id", "nearest_sub_name"])
        if "score_total_solar" not in pd.read_csv(OUT / "all_sites.csv", nrows=1).columns:
            old.to_csv(v1r, index=False)
            if not (OUT / "top_sites_v1.csv").exists():
                pd.read_csv(OUT / "top_sites.csv").to_csv(OUT / "top_sites_v1.csv", index=False)
    stage("cells"); c = build_cells(a.force)
    stage("blocks and sites"); raw = build_sites(c, a.force)
    n_raw = len(raw)
    del c
    stage("exact hard-exclusion cut"); clipped = clip_hard(raw, a.force)
    del raw
    acache = WORK / "sites_attr.pkl"
    if acache.exists() and not a.force:
        stage("load attribute cache"); s = pd.read_pickle(acache)
        s = substation_fields(s)   # POI filter + provisional flags (review fixes 2, 3)
        s = queue_fields(s)        # queue confidence (review fix 4)
    else:
        stage("attributes"); s = attributes(clipped)
        s.to_pickle(acache)
    del clipped
    n_cut = len(s)
    s["in_grid_pool"] = (s["dist_sub_km"] <= SCREEN["max_sub_km"]).values
    log.info("candidate pool: %d of %d sites within %.0f km of a usable %d kV+ substation",
             int(s["in_grid_pool"].sum()), n_cut, SCREEN["max_sub_km"], SCREEN["sub_kv_min"])
    stage("inset and simplify polygons")
    geo = shapely.buffer(s.geometry.values, -SCREEN["inset_m"], join_style="mitre")
    geo = shapely.simplify(geo, SCREEN["simplify_m"], preserve_topology=True)
    geo = shapely.make_valid(geo)
    attrs = dict(s.attrs)
    s = gpd.GeoDataFrame(s, geometry=geo, crs=CRS)
    s = s[~s.geometry.is_empty].reset_index(drop=True)
    stage("scores and ranks")
    s = score(s)
    s.attrs.update(attrs)
    s["next_step"] = s.apply(next_step, axis=1)
    pool = s[s["in_grid_pool"]].sort_values("rank_solar").reset_index(drop=True)
    stage("write candidate_sites.geojson")
    write_geojson(pool, OUT / "candidate_sites.geojson")
    t_pool = table(pool)
    t_pool.to_csv(OUT / "all_sites.csv", index=False)
    t_pool.head(50).to_csv(OUT / "top_sites.csv", index=False)
    t_pool.sort_values("rank_dc").head(50).to_csv(OUT / "top_sites_dc.csv", index=False)
    import shutil
    if shutil.disk_usage(OUT).free > 2e9:
        stage("write candidate_sites.gpkg")
        gpd.GeoDataFrame(t_pool, geometry=pool.to_crs("EPSG:4326").geometry.values, crs="EPSG:4326").to_file(
            OUT / "candidate_sites.gpkg", driver="GPKG")
    else:
        log.warning("less than 2 GB free disk: skipped candidate_sites.gpkg (the GeoJSON has the same data)")
    stage("hard-exclusion check"); chk = check_hard(pool)
    stage("POI check"); poi = poi_check(pool)
    by_state = pool.groupby("state").agg(sites=("site_id", "size"), acres=("acres", "sum"),
                                         blm_available=("blm_solar_available", "sum"),
                                         best_solar=("score_total_solar", "max"),
                                         best_dc=("score_total_dc", "max")).reindex(STATES)
    by_state.to_csv(OUT / "sites_by_state.csv")
    log.info("sites by state:\n%s", by_state.to_string())
    stats = (f"{n_raw:,} sites before the exact cut, {n_cut:,} after it (>= {SCREEN['min_acres']:.0f} acres), "
             f"{len(pool):,} within {SCREEN['max_sub_km']:.0f} km of a usable {SCREEN['sub_kv_min']} kV+ substation and ranked; "
             + ", ".join(f"{k} {int(v['sites']) if pd.notna(v['sites']) else 0:,}" for k, v in by_state.iterrows())
             + f"; {int(pool['blm_solar_available'].sum()):,} BLM solar-available sites.")
    stage("METHOD.md"); method_md(pool, chk, stats, poi, compare_v1(s), s)
    write_excel(s, pool, chk, poi, sources())
    log.info("screen done: %d ranked sites, %d scored (%.0fs)", len(pool), len(s), time.time() - t)


if __name__ == "__main__":
    main()

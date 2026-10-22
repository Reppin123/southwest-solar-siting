# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "requests==2.32.3",
#   "pyogrio==0.10.0",
#   "geopandas==1.0.1",
#   "shapely==2.0.6",
#   "pyarrow==18.1.0",
# ]
# ///
"""Fetch raw land-domain data for CA, AZ, NV, NM, UT into data/raw/land/.

Every download is resumable: a file (or a per-tile .done marker) that already
exists is skipped unless --force is given. Progress goes to logs/land.log.

Sources
- Census TIGER/Line 2024 and cartographic boundary 2024 (states, counties,
  AIANNH tribal areas, military installations, 2020 urban areas)
- BLM 2024 Western Solar Plan ROD geodatabase (blmsolar.anl.gov)
- BLM Energy Designations service: Solar Energy Zones, DRECP DFAs, DRECP variance lands
- BLM national Surface Management Agency geodatabase (SMA_WM.gdb, BLM EGIS hub)
- Wilderness Connect national wilderness (NWPS), BLM NLCS WSAs, NLCS NM/NCAs, BLM ACECs
- USFWS final critical habitat, FEMA NFHL flood hazard zones (A/V), USFWS NWI wetlands (>= 40 acres)
- NREL NSRDB v3 GHI annual average (nsrdbv3_ghi.zip via Internet Archive copy; nrel.gov is offline)
- USGS 3DEP-derived elevation via AWS Terrain Tiles (terrarium PNG, zoom 11)
"""
import argparse
import json
import logging
import math
import sys
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests
import requests.adapters

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "land"
LOG = ROOT / "logs" / "land.log"
STATES = {"06": "CA", "04": "AZ", "32": "NV", "35": "NM", "49": "UT"}
BBOX = (-124.6, 31.2, -102.9, 42.1)  # five-state envelope, lon/lat

log = logging.getLogger("fetch_land")
SESSION = requests.Session()
SESSION.headers["User-Agent"] = "southwest-solar-siting/1.0 (research screening)"
SESSION.mount("https://", requests.adapters.HTTPAdapter(pool_connections=32, pool_maxsize=32))

TIGER = {
    "cb_2024_us_state_500k.zip": "https://www2.census.gov/geo/tiger/GENZ2024/shp/cb_2024_us_state_500k.zip",
    "cb_2024_us_county_500k.zip": "https://www2.census.gov/geo/tiger/GENZ2024/shp/cb_2024_us_county_500k.zip",
    "tl_2024_us_aiannh.zip": "https://www2.census.gov/geo/tiger/TIGER2024/AIANNH/tl_2024_us_aiannh.zip",
    "tl_2024_us_mil.zip": "https://www2.census.gov/geo/tiger/TIGER2024/MIL/tl_2024_us_mil.zip",
    "tl_2024_us_uac20.zip": "https://www2.census.gov/geo/tiger/TIGER2024/UAC20/tl_2024_us_uac20.zip",
}
BIG_FILES = {
    "BLM-National-Solar-PEIS-ROD.gdb.zip": "https://blmsolar.anl.gov/maps/data/2024-solar-peis/BLM-National-Solar-PEIS-ROD.gdb.zip",
    "SMA_WM.gdb.zip": "https://www.arcgis.com/sharing/rest/content/items/6bf2e737c59d4111be92420ee5ab0b46/data",
    # NREL's own URL (https://www.nrel.gov/gis/assets/data/nsrdbv3_ghi.zip) went offline when NREL
    # became NLR; this is the Internet Archive capture of that exact file (2024-09-26, same digest as 2020-2024 captures).
    "nsrdbv3_ghi.zip": "https://web.archive.org/web/20240926182851id_/https://www.nrel.gov/gis/assets/data/nsrdbv3_ghi.zip",
}

EXTRACT_TO = {"BLM-National-Solar-PEIS-ROD.gdb.zip": "BLM_Natl_Solar_PEIS_ROD.gdb",
              "SMA_WM.gdb.zip": "SMA_WM.gdb", "nsrdbv3_ghi.zip": "nsrdbv3_ghi"}

KB = "https://services1.arcgis.com/KbxwQRRfWyEYLgp4/arcgis/rest/services"
# name -> (layer url, where, tile size deg (0 = one query), maxAllowableOffset deg, page size)
ARCGIS = {
    "sez": (f"{KB}/Energy_Designations/FeatureServer/10", "1=1", 0, None, 1000),
    "drecp_dfa": (f"{KB}/Energy_Designations/FeatureServer/12", "1=1", 0, None, 1000),
    "drecp_variance": (f"{KB}/Energy_Designations/FeatureServer/13", "1=1", 0, None, 1000),
    "wilderness_nwps": ("https://services1.arcgis.com/ERdCHt0sNM6dENSD/arcgis/rest/services/Wilderness_Areas_in_the_United_States/FeatureServer/0", "1=1", 0, None, 200),
    "wsa_blm": (f"{KB}/BLM_Natl_NLCS_Wilderness_Study_Areas_Polygons/FeatureServer/3", "1=1", 0, None, 200),
    "nlcs_nm_nca": (f"{KB}/BLM_Natl_NLCS_National_Monuments_National_Conservation_Areas_Polygons/FeatureServer/0", "1=1", 0, None, 100),
    "acec": ("https://gis.blm.gov/arcgis/rest/services/lands/BLM_Natl_ACEC/MapServer/0", "1=1", 2, None, 500),
    "critical_habitat": ("https://services.arcgis.com/QVENGdaPbd4LUkLV/arcgis/rest/services/USFWS_Critical_Habitat/FeatureServer/0", "1=1", 2, None, 200),
    "fema_flood_av": ("https://hazards.fema.gov/arcgis/rest/services/public/NFHL/MapServer/28",
                      "FLD_ZONE IN ('A','AE','AH','AO','V','VE')", 0.5, 0.0003, 1000),
    "nwi_wetlands_40ac": ("https://fwspublicservices.wim.usgs.gov/wetlandsmapservice/rest/services/Wetlands/MapServer/0",
                          "ACRES >= 40", 1, 0.0003, 500),
}
TERRAIN_URL = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"
TERRAIN_Z = 11


def setup_logging():
    LOG.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s fetch_land %(levelname)s %(message)s",
                        handlers=[logging.FileHandler(LOG), logging.StreamHandler(sys.stdout)])


def get(url, params=None, stream=False, timeout=180, tries=6):
    for i in range(tries):
        try:
            r = SESSION.get(url, params=params, stream=stream, timeout=timeout)
            if r.status_code == 200:
                return r
            if r.status_code == 404:
                return r
            log.warning("HTTP %s for %s (try %d)", r.status_code, url, i + 1)
        except requests.RequestException as e:
            log.warning("error %s for %s (try %d)", e, url, i + 1)
        time.sleep(min(60, 2 ** i * 2))
    raise RuntimeError(f"failed after {tries} tries: {url}")


def download(url, dest: Path, force=False):
    if dest.exists() and dest.stat().st_size > 0 and not force:
        log.info("skip (exists) %s", dest.name)
        return dest
    tmp = dest.with_suffix(dest.suffix + ".part")
    headers = {}
    if tmp.exists():
        headers["Range"] = f"bytes={tmp.stat().st_size}-"
    for i in range(6):
        try:
            with SESSION.get(url, stream=True, timeout=300, headers=headers) as r:
                if r.status_code not in (200, 206):
                    raise requests.RequestException(f"HTTP {r.status_code}")
                mode = "ab" if r.status_code == 206 else "wb"
                with open(tmp, mode) as f:
                    for chunk in r.iter_content(1 << 20):
                        f.write(chunk)
            tmp.rename(dest)
            log.info("downloaded %s (%.1f MB)", dest.name, dest.stat().st_size / 1e6)
            return dest
        except (requests.RequestException, OSError) as e:
            log.warning("download error %s (try %d): %s", dest.name, i + 1, e)
            headers = {"Range": f"bytes={tmp.stat().st_size}-"} if tmp.exists() else {}
            time.sleep(min(60, 2 ** i * 3))
    raise RuntimeError(f"download failed: {url}")


def unzip(zpath: Path, marker_name: str, force=False):
    target = zpath.parent / marker_name
    if target.exists() and not force:
        return target
    with zipfile.ZipFile(zpath) as z:
        names = z.namelist()
        if marker_name.endswith(".gdb") and not any(n.startswith(marker_name + "/") for n in names):
            # gdb nested under a different folder name; extract into a directory of that name
            target.mkdir(exist_ok=True)
            z.extractall(target)
        elif marker_name.endswith(".gdb"):
            z.extractall(zpath.parent)
        else:
            target.mkdir(exist_ok=True)
            z.extractall(target)
    log.info("extracted %s -> %s", zpath.name, target.name)
    return target


def state_tiles(step):
    """Tiles of `step` degrees over the five-state bbox that touch one of the states."""
    import geopandas as gpd
    from shapely.geometry import box
    st = gpd.read_file(RAW / "tiger" / "cb_2024_us_state_500k.zip")
    st = st[st["STATEFP"].isin(STATES)]
    u = st.union_all()
    out = []
    x = math.floor(BBOX[0])
    while x < BBOX[2]:
        y = math.floor(BBOX[1])
        while y < BBOX[3]:
            if u.intersects(box(x, y, x + step, y + step)):
                out.append((x, y, x + step, y + step))
            y += step
        x += step
    return out


def arcgis_query_extent(name, url, where, env, offset, page, outdir: Path):
    tag = "all" if env is None else f"{env[0]:.2f}_{env[1]:.2f}".replace("-", "m")
    done = outdir / f"{tag}.done"
    if done.exists():
        return 0
    n_total, start, part = 0, 0, 0
    while True:
        p = {"where": where, "outFields": "*", "outSR": 4326, "f": "geojson",
             "resultOffset": start, "resultRecordCount": page, "returnGeometry": "true"}
        if env is not None:
            p.update(geometry=",".join(map(str, env)), geometryType="esriGeometryEnvelope",
                     inSR=4326, spatialRel="esriSpatialRelIntersects")
        else:
            p.update(geometry=",".join(map(str, BBOX)), geometryType="esriGeometryEnvelope",
                     inSR=4326, spatialRel="esriSpatialRelIntersects")
        if offset:
            p["maxAllowableOffset"] = offset
        for attempt in range(5):
            r = get(url + "/query", params=p, timeout=300)
            try:
                js = r.json()
            except ValueError:
                js = {"error": {"message": r.text[:200]}}
            if "error" not in js:
                break
            log.warning("%s %s page %d error %s (attempt %d)", name, tag, part, js["error"], attempt + 1)
            if attempt >= 2 and page > 50:
                page = max(50, page // 4)
                p["resultRecordCount"] = page
            time.sleep(5 * (attempt + 1))
        else:
            raise RuntimeError(f"{name} {tag}: query kept failing")
        feats = js.get("features", [])
        (outdir / f"{tag}_{part:04d}.geojson").write_text(json.dumps(js))
        n_total += len(feats)
        exceeded = js.get("exceededTransferLimit") or js.get("properties", {}).get("exceededTransferLimit")
        if not feats or (len(feats) < page and not exceeded):
            break
        start += len(feats)
        part += 1
    done.write_text(str(n_total))
    return n_total


def fetch_arcgis(name, force=False):
    url, where, step, offset, page = ARCGIS[name]
    outdir = RAW / "arcgis" / name
    if force and outdir.exists():
        for f in outdir.iterdir():
            f.unlink()
    outdir.mkdir(parents=True, exist_ok=True)
    meta = outdir / "_layer.json"
    if not meta.exists():
        meta.write_text(get(url, params={"f": "json"}).text)
    envs = [None] if step == 0 else state_tiles(step)
    total = 0
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = {ex.submit(arcgis_query_extent, name, url, where, e, offset, page, outdir): e for e in envs}
        for f in as_completed(futs):
            total += f.result()
    n_done = sum(int(p.read_text() or 0) for p in outdir.glob("*.done"))
    log.info("%s: %d tiles, %d features on disk (%d new this run)", name, len(envs), n_done, total)


def lonlat_to_tile(lon, lat, z):
    n = 2 ** z
    x = int((lon + 180) / 360 * n)
    y = int((1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n)
    return x, y


def tile_bounds(x, y, z):
    n = 2 ** z
    lon0, lon1 = x / n * 360 - 180, (x + 1) / n * 360 - 180
    lat0 = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (y + 1) / n))))
    lat1 = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n))))
    return lon0, lat0, lon1, lat1


def terrain_tile_list(z=TERRAIN_Z):
    import geopandas as gpd
    from shapely.geometry import box
    st = gpd.read_file(RAW / "tiger" / "cb_2024_us_state_500k.zip")
    st = st[st["STATEFP"].isin(STATES)]
    u = st.union_all().buffer(0.05)
    x0, y0 = lonlat_to_tile(BBOX[0], BBOX[3], z)
    x1, y1 = lonlat_to_tile(BBOX[2], BBOX[1], z)
    tiles = []
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            if u.intersects(box(*tile_bounds(x, y, z))):
                tiles.append((x, y))
    return tiles


def fetch_terrain(force=False):
    z = TERRAIN_Z
    outdir = RAW / "terrain" / str(z)
    outdir.mkdir(parents=True, exist_ok=True)
    tiles = terrain_tile_list(z)
    (RAW / "terrain" / f"tiles_z{z}.json").write_text(json.dumps(tiles))
    todo = [(x, y) for x, y in tiles if force or not (outdir / f"{x}_{y}.png").exists()]
    log.info("terrain z%d: %d tiles needed, %d to download", z, len(tiles), len(todo))

    def one(xy):
        x, y = xy
        r = get(TERRAIN_URL.format(z=z, x=x, y=y), timeout=60)
        if r.status_code != 200:
            return False
        tmp = outdir / f"{x}_{y}.png.part"
        tmp.write_bytes(r.content)
        tmp.rename(outdir / f"{x}_{y}.png")
        return True

    ok = 0
    with ThreadPoolExecutor(max_workers=24) as ex:
        for i, res in enumerate(ex.map(one, todo)):
            ok += bool(res)
            if (i + 1) % 1000 == 0:
                log.info("terrain: %d / %d", i + 1, len(todo))
    log.info("terrain: downloaded %d of %d", ok, len(todo))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--force", action="store_true", help="re-download even if files exist")
    ap.add_argument("--only", nargs="*", help="subset: tiger big arcgis:<name> terrain")
    args = ap.parse_args()
    setup_logging()
    only = set(args.only or [])
    want = lambda k: not only or k in only or (k.startswith("arcgis:") and "arcgis" in only)

    (RAW / "tiger").mkdir(parents=True, exist_ok=True)
    if want("tiger"):
        for fn, url in TIGER.items():
            download(url, RAW / "tiger" / fn, args.force)
    if want("big"):
        # zips are deleted after extraction to save disk; an extracted folder counts as done
        for fn, url in BIG_FILES.items():
            extracted = RAW / EXTRACT_TO[fn]
            if extracted.exists() and not args.force:
                log.info("skip (extracted) %s", extracted.name)
                continue
            download(url, RAW / fn, args.force)
            unzip(RAW / fn, EXTRACT_TO[fn], args.force)
            (RAW / fn).unlink()
    for name in ARCGIS:
        if want(f"arcgis:{name}"):
            try:
                fetch_arcgis(name, args.force)
            except Exception as e:  # keep going; process step records the gap
                log.error("arcgis %s failed: %s", name, e)
    if want("terrain"):
        fetch_terrain(args.force)
    log.info("fetch_land done")


if __name__ == "__main__":
    main()

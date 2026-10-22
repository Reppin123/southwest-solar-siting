# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "requests==2.32.3",
# ]
# ///
"""Fetch raw grid data for CA, AZ, NV, NM, UT into data/raw/grid/.

Sources:
  - HIFLD Electric Power Transmission Lines (ArcGIS REST, paged, bbox filtered)
  - HIFLD Electric Substations (last public HIFLD release, ArcGIS REST mirror, paged)
  - OpenStreetMap power=substation via Overpass (cross-check / gap fill)
  - Berkeley Lab Queued Up 2026 Excel (data through end of 2025)
  - CAISO public interconnection queue report (Excel)
  - US Census TIGER cartographic boundary states and counties (2024, 1:500k)

Resumable: every file is skipped if it already exists unless --force.
Usage: uv run --script pipeline/fetch_grid.py [--force]
"""
from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "grid"
LOG = ROOT / "logs" / "grid.log"
FORCE = "--force" in sys.argv

# Five-state bbox (lon/lat), slightly padded; features are clipped to state polygons in process_grid.py
BBOX = (-124.6, 31.2, -102.9, 42.1)
STATES = {"CA": "06", "AZ": "04", "NV": "32", "NM": "35", "UT": "49"}

HIFLD_LINES_URLS = [
    # HIFLD Electric Power Transmission Lines, hosted copy in the ArcGIS Online org that served HIFLD Open data
    "https://services2.arcgis.com/FiaPA4ga0iQKduv3/arcgis/rest/services/US_Electric_Power_Transmission_Lines/FeatureServer/0",
    "https://services1.arcgis.com/Hp6G80Pky0om7QvQ/arcgis/rest/services/Electric_Power_Transmission_Lines/FeatureServer/0",
]
HIFLD_SUBS_URLS = [
    # HIFLD Electric Substations was removed from HIFLD Open; these are public ArcGIS Online copies of the
    # last public HIFLD release (75,328 records nationally, identical schema).
    "https://services5.arcgis.com/HDRa0B57OVrv2E1q/arcgis/rest/services/Electric_Substations/FeatureServer/0",
    "https://services3.arcgis.com/tIXNvLw6bzMyLMS6/arcgis/rest/services/hifld_substations/FeatureServer/0",
    "https://services7.arcgis.com/QmuNrTCnY2EFlCq9/arcgis/rest/services/hifld_substations/FeatureServer/0",
]
OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]
# voltage tag contains a value >= 115000 V (6-digit volts from 115000 to 999999)
OSM_KV_RE = "(^|;)(11[5-9]|1[2-9][0-9]|[2-9][0-9]{2})[0-9]{3}($|;)"
QUEUED_UP_URL = "https://eta-publications.lbl.gov/sites/default/files/2026-05/lbnl_ix_queue_data_file_thru2025.xlsx"
QUEUED_UP_PDF = "https://eta-publications.lbl.gov/sites/default/files/2026-06/queued_up_2026_edition.pdf"
CAISO_QUEUE_URL = "https://www.caiso.com/documents/publicqueuereport.xlsx"
TIGER_STATES = "https://www2.census.gov/geo/tiger/GENZ2024/shp/cb_2024_us_state_500k.zip"
TIGER_COUNTIES = "https://www2.census.gov/geo/tiger/GENZ2024/shp/cb_2024_us_county_500k.zip"

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/130 Safari/537.36 southwest-solar-siting research"}

LOG.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s fetch_grid %(levelname)s %(message)s",
    handlers=[logging.FileHandler(LOG), logging.StreamHandler()],
)
log = logging.getLogger()


def request(method: str, url: str, tries: int = 5, **kw) -> requests.Response:
    kw.setdefault("timeout", 180)
    headers = {**UA, **kw.pop("headers", {})}
    for i in range(tries):
        try:
            r = requests.request(method, url, headers=headers, **kw)
            if r.status_code in (429, 502, 503, 504):
                raise requests.HTTPError(f"HTTP {r.status_code}")
            r.raise_for_status()
            return r
        except Exception as e:  # noqa: BLE001
            wait = 2 ** i * 3
            log.warning("attempt %d/%d failed for %s: %s; retry in %ss", i + 1, tries, url, e, wait)
            time.sleep(wait)
    raise RuntimeError(f"giving up on {url}")


def download(url: str, dest: Path) -> Path:
    if dest.exists() and dest.stat().st_size > 0 and not FORCE:
        log.info("skip (exists) %s", dest.relative_to(ROOT))
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    log.info("download %s -> %s", url, dest.relative_to(ROOT))
    r = request("GET", url, stream=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    with open(tmp, "wb") as f:
        for chunk in r.iter_content(1 << 20):
            f.write(chunk)
    tmp.rename(dest)
    return dest


def arcgis_paged(urls: list[str], outdir: Path, label: str) -> None:
    """Page an ArcGIS FeatureServer layer filtered to BBOX into GeoJSON page files."""
    done = outdir / "_complete.json"
    if done.exists() and not FORCE:
        log.info("skip (exists) %s", outdir.relative_to(ROOT))
        return
    outdir.mkdir(parents=True, exist_ok=True)
    geom = json.dumps({"xmin": BBOX[0], "ymin": BBOX[1], "xmax": BBOX[2], "ymax": BBOX[3],
                       "spatialReference": {"wkid": 4326}})
    base = {"where": "1=1", "geometry": geom, "geometryType": "esriGeometryEnvelope", "inSR": 4326,
            "spatialRel": "esriSpatialRelIntersects", "outFields": "*", "outSR": 4326, "f": "geojson"}
    last_err = None
    for url in urls:
        try:
            meta = request("GET", url, params={"f": "json"}).json()
            if "error" in meta:
                raise RuntimeError(meta["error"])
            page = min(int(meta.get("maxRecordCount", 1000) or 1000), 2000)
            cnt = request("GET", url + "/query", params={**base, "returnCountOnly": "true", "f": "json"}).json()["count"]
            log.info("%s: %s features in bbox at %s (page %d)", label, cnt, url, page)
            got, off = 0, 0
            while off < cnt:
                pf = outdir / f"page_{off:07d}.geojson"
                if not (pf.exists() and pf.stat().st_size > 0) or FORCE:
                    r = request("GET", url + "/query", params={**base, "resultOffset": off, "resultRecordCount": page,
                                                               "orderByFields": meta.get("objectIdField") or "OBJECTID"})
                    js = r.json()
                    if "error" in js:
                        raise RuntimeError(js["error"])
                    pf.write_text(json.dumps(js))
                n = len(json.loads(pf.read_text()).get("features", []))
                got += n
                off += page
                if n == 0:
                    break
            if got < cnt:
                raise RuntimeError(f"{label}: got {got} of {cnt}")
            done.write_text(json.dumps({"source_url": url, "count": cnt, "fetched": got,
                                        "retrieved": time.strftime("%Y-%m-%d"), "layer_meta": {
                                            k: meta.get(k) for k in ("name", "editingInfo", "description", "copyrightText")}}, indent=1))
            log.info("%s: fetched %d features", label, got)
            return
        except Exception as e:  # noqa: BLE001
            last_err = e
            log.error("%s: source %s failed: %s; trying next", label, url, e)
            for p in outdir.glob("page_*.geojson"):
                p.unlink()
    raise RuntimeError(f"{label}: all sources failed: {last_err}")


def overpass_substations(outdir: Path) -> None:
    """OSM power=substation tagged >=115 kV (any value in a ';' list), one Overpass area query per state."""
    outdir.mkdir(parents=True, exist_ok=True)
    failed = []
    for st in STATES:
        pf = outdir / f"osm_subs_{st}.json"
        if pf.exists() and pf.stat().st_size > 0 and not FORCE:
            log.info("skip (exists) %s", pf.relative_to(ROOT))
            continue
        q = (f'[out:json][timeout:280];area["ISO3166-2"="US-{st}"]->.a;'
             f'nwr["power"="substation"]["voltage"~"{OSM_KV_RE}"](area.a);out center tags;')
        ok = False
        for url in OVERPASS_URLS:
            try:
                r = request("POST", url, tries=3, data={"data": q}, timeout=300,
                            headers={"User-Agent": "southwest-solar-siting/1.0 (research)"})
                js = r.json()
                if "elements" not in js:
                    raise RuntimeError("no elements in response")
                pf.write_text(json.dumps(js))
                log.info("overpass %s: %d elements via %s", st, len(js["elements"]), url)
                ok = True
                break
            except Exception as ex:  # noqa: BLE001
                log.warning("overpass %s failed at %s: %s", st, url, ex)
        if not ok:
            failed.append(st)
        time.sleep(5)
    if failed:
        raise RuntimeError(f"overpass failed for states {failed}")
    (outdir / "_complete.json").write_text(json.dumps({
        "states": list(STATES), "retrieved": time.strftime("%Y-%m-%d"),
        "query": f'area["ISO3166-2"="US-<ST>"]; nwr["power"="substation"]["voltage"~"{OSM_KV_RE}"](area); out center tags;'}))


def main() -> None:
    log.info("=== fetch_grid start (force=%s)", FORCE)
    download(TIGER_STATES, RAW / "tiger" / "cb_2024_us_state_500k.zip")
    download(TIGER_COUNTIES, RAW / "tiger" / "cb_2024_us_county_500k.zip")
    arcgis_paged(HIFLD_LINES_URLS, RAW / "hifld_lines", "HIFLD transmission lines")
    arcgis_paged(HIFLD_SUBS_URLS, RAW / "hifld_substations", "HIFLD substations")
    download(QUEUED_UP_URL, RAW / "queued_up" / "lbnl_ix_queue_data_file_thru2025.xlsx")
    try:
        download(QUEUED_UP_PDF, RAW / "queued_up" / "queued_up_2026_edition.pdf")
    except Exception as e:  # noqa: BLE001
        log.warning("Queued Up PDF not fetched (optional): %s", e)
    try:
        download(CAISO_QUEUE_URL, RAW / "caiso" / "publicqueuereport.xlsx")
    except Exception as e:  # noqa: BLE001
        log.warning("CAISO queue not fetched (optional): %s", e)
    try:
        overpass_substations(RAW / "osm")
    except Exception as e:  # noqa: BLE001
        log.warning("OSM Overpass cross-check incomplete (optional): %s", e)
    log.info("=== fetch_grid done")


if __name__ == "__main__":
    main()

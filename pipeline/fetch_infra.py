# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "requests==2.32.3",
# ]
# ///
"""Fetch raw infrastructure data for the Southwest siting study (CA, AZ, NV, NM, UT).

Downloads (all public, no login) into data/raw/infra/:
  - EIA-860 2025 annual release (plants + generators)            eia860/
  - US Census cartographic state boundaries 2024 (clip mask)      tiger/
  - US Census TIGER 2025 primary roads (interstates, US highways) tiger/
  - BTS NTAD North American Rail Network, Class I main lines     rail/ (fiber corridor proxy)
  - WRI Aqueduct 4.0 water risk data (baseline annual)            aqueduct/
  - ADWR Arizona AMA / INA groundwater boundaries                water/
  - BLM MLRS land use authorization ROW cases, solar commodity    blm_row/
  - OpenStreetMap telecom lines (fiber proxy) via Overpass        osm/
  - OpenStreetMap data centers via Overpass                       osm/

Each download is skipped if the file already exists (use --force to refetch).
Log: logs/infra.log
"""
import argparse
import json
import logging
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "infra"
LOG = ROOT / "logs" / "infra.log"
UA = {"User-Agent": "southwest-solar-siting/1.0 (research; public data fetch)"}
STATES = ["CA", "AZ", "NV", "NM", "UT"]
STATE_FIPS = {"CA": "06", "AZ": "04", "NV": "32", "NM": "35", "UT": "49"}

FILES = {
    "eia860/eia8602025.zip": "https://www.eia.gov/electricity/data/eia860/xls/eia8602025.zip",
    "tiger/cb_2024_us_state_500k.zip": "https://www2.census.gov/geo/tiger/GENZ2024/shp/cb_2024_us_state_500k.zip",
    "tiger/tl_2025_us_primaryroads.zip": "https://www2.census.gov/geo/tiger/TIGER2025/PRIMARYROADS/tl_2025_us_primaryroads.zip",
    "aqueduct/aqueduct-4-0-water-risk-data.zip": "https://files.wri.org/aqueduct/aqueduct-4-0-water-risk-data.zip",
}

NARN = "https://services.arcgis.com/xOi1kZaI0eWDREZv/arcgis/rest/services/NTAD_North_American_Rail_Network_Lines/FeatureServer/0"
ADWR_AMA = "https://services.arcgis.com/C34zQ7veRS0V1t04/arcgis/rest/services/AMA_INA_2024/FeatureServer/0"
MLRS_ROW = "https://nlsdbpubgis.blm.gov/arcgishub/rest/services/HUB/BLM_Natl_MLRS_LUA_ROW/FeatureServer/0"
OVERPASS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]

log = logging.getLogger("fetch_infra")


def setup_logging():
    LOG.parent.mkdir(parents=True, exist_ok=True)
    fmt = logging.Formatter("%(asctime)s fetch_infra %(levelname)s %(message)s")
    for h in (logging.FileHandler(LOG), logging.StreamHandler(sys.stdout)):
        h.setFormatter(fmt)
        log.addHandler(h)
    log.setLevel(logging.INFO)


def retry(fn, what, tries=5, base=5):
    for i in range(tries):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001
            wait = base * 2**i
            log.warning("%s failed (attempt %d/%d): %s; retry in %ds", what, i + 1, tries, e, wait)
            if i == tries - 1:
                raise
            time.sleep(wait)


def download(url, dest: Path, force=False):
    if dest.exists() and dest.stat().st_size > 0 and not force:
        log.info("skip (exists) %s", dest.relative_to(ROOT))
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_suffix(dest.suffix + ".part")

    def go():
        headers = dict(UA)
        start = part.stat().st_size if part.exists() else 0
        if start:
            headers["Range"] = f"bytes={start}-"
        with requests.get(url, headers=headers, stream=True, timeout=120) as r:
            if r.status_code == 416:  # already complete
                return
            r.raise_for_status()
            mode = "ab" if start and r.status_code == 206 else "wb"
            with open(part, mode) as f:
                for chunk in r.iter_content(1 << 20):
                    f.write(chunk)

    log.info("download %s -> %s", url, dest.relative_to(ROOT))
    retry(go, f"download {url}")
    part.rename(dest)
    log.info("done %s (%.1f MB)", dest.name, dest.stat().st_size / 1e6)


def arcgis_geojson(service, where, dest: Path, force=False, page=500, label="arcgis"):
    """Page an ArcGIS FeatureServer layer query into one GeoJSON file (EPSG:4326)."""
    if dest.exists() and not force:
        log.info("skip (exists) %s", dest.relative_to(ROOT))
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    feats, offset = [], 0
    while True:
        params = {
            "where": where, "outFields": "*", "outSR": 4326, "f": "geojson",
            "resultOffset": offset, "resultRecordCount": page, "orderByFields": "OBJECTID",
        }

        def go():
            r = requests.get(f"{service}/query", params=params, headers=UA, timeout=180)
            r.raise_for_status()
            d = r.json()
            if "error" in d:
                raise RuntimeError(d["error"])
            return d

        d = retry(go, f"{label} page offset {offset}")
        got = d.get("features", [])
        feats.extend(got)
        log.info("%s: offset %d got %d (total %d)", label, offset, len(got), len(feats))
        if len(got) < page and not d.get("exceededTransferLimit") and not d.get("properties", {}).get("exceededTransferLimit"):
            break
        if not got:
            break
        offset += len(got)
    fc = {"type": "FeatureCollection", "features": feats,
          "retrieved": time.strftime("%Y-%m-%d"), "source": service, "where": where}
    dest.write_text(json.dumps(fc))
    log.info("wrote %s (%d features)", dest.relative_to(ROOT), len(feats))


def in_states(field):
    return f"{field} IN (" + ",".join(f"'{s}'" for s in STATES) + ")"


def fetch_mlrs_solar(force=False):
    """All BLM MLRS ROW cases with solar commodity in the five states (all dispositions)."""
    arcgis_geojson(MLRS_ROW, f"CMMDTY LIKE '%SOLAR%' AND {in_states('GEO_STATE')}",
                   RAW / "blm_row" / "mlrs_solar_row.geojson", force, label="MLRS solar ROW")


def fetch_rail(force=False):
    """Class I (UP, BNSF) main-line track in the five states, used as a long-haul fiber corridor proxy."""
    arcgis_geojson(NARN, f"NET = 'M' AND RROWNER1 IN ('UP','BNSF') AND {in_states('STATEAB')}",
                   RAW / "rail" / "narn_class1_mainline.geojson", force, page=1000, label="NARN rail")


def fetch_ama(force=False):
    """Arizona Active Management Areas and Irrigation Non-expansion Areas (ADWR)."""
    arcgis_geojson(ADWR_AMA, "1=1", RAW / "water" / "adwr_ama_ina.geojson", force, label="ADWR AMA/INA")


def overpass(query, dest: Path, force=False):
    if dest.exists() and dest.stat().st_size > 0 and not force:
        log.info("skip (exists) %s", dest.relative_to(ROOT))
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    last = None
    for attempt in range(3):
        for url in OVERPASS:
            try:
                log.info("overpass %s -> %s", url, dest.name)
                r = requests.post(url, data={"data": query}, headers=UA, timeout=600)
                r.raise_for_status()
                d = r.json()
                if d.get("remark") and "error" in d["remark"].lower():
                    raise RuntimeError(d["remark"])
                d["retrieved"] = time.strftime("%Y-%m-%d")
                d["endpoint"] = url
                dest.write_text(json.dumps(d))
                log.info("wrote %s (%d elements)", dest.relative_to(ROOT), len(d.get("elements", [])))
                return
            except Exception as e:  # noqa: BLE001
                last = e
                log.warning("overpass %s failed: %s", url, e)
        time.sleep(30 * (attempt + 1))
    raise RuntimeError(f"all overpass endpoints failed: {last}")


def area_block():
    return "".join(f'area["ISO3166-2"="US-{s}"];' for s in STATES)


def fetch_osm(force=False):
    # Telecom / fiber lines. OSM coverage of buried long-haul fiber is partial; used as a proxy.
    telecom = f"""[out:json][timeout:500];
({area_block()})->.a;
(
  way["telecom"~"^(line|cable)$"](area.a);
  way["communication"~"^(line|cable)$"](area.a);
  way["man_made"="cable"]["cable"!="power"](area.a);
  way["utility"="telecom"](area.a);
  way["telecom:medium"~"fib"](area.a);
  way["cable"~"fib"](area.a);
);
out tags geom;"""
    overpass(telecom, RAW / "osm" / "osm_telecom_lines.json", force)
    dc = f"""[out:json][timeout:300];
({area_block()})->.a;
(
  nwr["telecom"="data_center"](area.a);
  nwr["building"="data_center"](area.a);
  nwr["building"="data_centre"](area.a);
  nwr["telecom"="data_centre"](area.a);
);
out tags center;"""
    overpass(dc, RAW / "osm" / "osm_data_centers.json", force)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--force", action="store_true", help="re-download even if files exist")
    ap.add_argument("--only", choices=["files", "mlrs", "rail", "ama", "osm"], help="run one part")
    a = ap.parse_args()
    setup_logging()
    log.info("start fetch (force=%s only=%s)", a.force, a.only)
    failures = []
    if a.only in (None, "files"):
        for rel, url in FILES.items():
            try:
                download(url, RAW / rel, a.force)
            except Exception as e:  # noqa: BLE001
                failures.append(rel)
                log.error("FAILED %s: %s", rel, e)
    for name, fn in (("mlrs", fetch_mlrs_solar), ("rail", fetch_rail), ("ama", fetch_ama), ("osm", fetch_osm)):
        if a.only in (None, name):
            try:
                fn(a.force)
            except Exception as e:  # noqa: BLE001
                failures.append(name)
                log.error("FAILED %s: %s", name, e)
    log.info("fetch finished; failures: %s", failures or "none")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

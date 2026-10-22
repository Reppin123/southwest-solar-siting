# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "geopandas==1.0.1",
#   "pyogrio==0.10.0",
#   "shapely==2.0.6",
#   "pandas==2.2.3",
#   "numpy==2.1.3",
# ]
# ///
"""Package processed layers for the dashboard (app/data/).

Reads data/processed/** and deliverables/** (read only) and writes:
  app/data/layers/*.geojson   simplified map copies (EPSG:4326, rounded coordinates, trimmed fields)
  app/data/sites_geom.geojson candidate site polygons (property i = row index into sites_attr.json)
  app/data/sites_attr.json    columnar site attributes used for scorecards and in-browser re-ranking
  app/data/overlays/*.png     GHI and slope overlays (EPSG:3857 images placed by lat/lon bounds)
  app/data/summary.json       chart data (queue by state and type, substation proxy list)
  app/data/sources.json       every MANIFEST entry, SCOPE section 7 limits, provisional data note
  app/data/deliverables.json  links to the Excel ranking, site memos, BLM brief, method and review
  app/data/layers.json        layer list with file, style, legend and MANIFEST metadata
  app/data/appendix/METHODOLOGY_REVIEW.md  copy of the independent methodology review

Run: uv run --script pipeline/build_app.py [--force]
Skips work when app/data/layers.json is newer than every input unless --force.
"""
import argparse
import json
import logging
import os
import re
import shutil
import sys
import time
import warnings
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pyogrio

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "data" / "processed"
APP = ROOT / "app"
OUT = APP / "data"
LOG = ROOT / "logs" / "app.log"
REVIEW = ROOT.parent / "southwest-solar-siting-review" / "review" / "METHODOLOGY_REVIEW.md"
STATES = ["CA", "AZ", "NV", "NM", "UT"]
warnings.filterwarnings("ignore", "GeoSeries.notna", UserWarning)

logging.basicConfig(level=logging.INFO, format="%(asctime)s build_app %(message)s",
                    handlers=[logging.FileHandler(LOG), logging.StreamHandler(sys.stdout)])
log = logging.getLogger()

# Voltage colours follow the common utility-map convention (low kV cool, 500 kV red).
VOLT_COLORS = {"<115": "#9aa5b1", "115-161": "#2f9e44", "230": "#1c7ed6", "345": "#ae3ec9",
               "500+": "#e03131", "unknown": "#c0c6cc"}
OWN_COLORS = {"BLM": "#f2c94c", "USFS": "#6fcf97", "NPS": "#9b7653", "DOD": "#eb5757", "Tribal": "#bb6bd9",
              "State": "#56ccf2", "Private": "#e5e7eb", "Other": "#bdbdbd"}


def manifest_entries():
    """All MANIFEST entries keyed by (domain, layer)."""
    out = {}
    for d in ["grid", "land", "infra", "sites"]:
        f = P / d / "MANIFEST.json"
        if not f.exists():
            continue
        m = json.loads(f.read_text())
        rows = m["layers"] if isinstance(m, dict) else m
        for r in rows:
            out[(d, r["layer"])] = r
    return out


def caveat_text(c):
    if c is None:
        return ""
    if isinstance(c, list):
        return " ".join(str(x) for x in c)
    return str(c)


def meta(entry):
    if not entry:
        return None
    return {k: entry.get(k) for k in ["layer", "path", "source_name", "source_url", "retrieved", "record_count"]} | {
        "caveats": caveat_text(entry.get("caveats"))}


def write_geojson(gdf, name, keep, tol=None, precision=5):
    """Trim fields, simplify (per-feature, topology preserving), round coordinates, write GeoJSON."""
    gdf = gdf[[c for c in keep if c in gdf.columns] + ["geometry"]].copy()
    gdf = gdf[~gdf.geometry.is_empty & gdf.geometry.notna()]
    if tol:
        gdf["geometry"] = gdf.geometry.simplify(tol, preserve_topology=True)
        gdf = gdf[~gdf.geometry.is_empty]
    for c in gdf.columns:
        if c != "geometry" and gdf[c].dtype == object:
            gdf[c] = gdf[c].where(gdf[c].notna(), None)
    dst = OUT / "layers" / f"{name}.geojson"
    if dst.exists():
        dst.unlink()
    pyogrio.write_dataframe(gdf, dst, driver="GeoJSON", layer_options={"COORDINATE_PRECISION": precision,
                                                                       "RFC7946": "YES"})
    mb = dst.stat().st_size / 1e6
    log.info("layer %-22s %6d features %6.1f MB", name, len(gdf), mb)
    return {"file": f"data/layers/{name}.geojson", "features": int(len(gdf)), "mb": round(mb, 2)}


def read(path, cols=None):
    return gpd.read_file(path, columns=cols, engine="pyogrio").to_crs(4326)


def build_layers(man):
    layers = []

    # --- grid
    lines = read(P / "grid/transmission_lines.geojson")
    info = write_geojson(lines, "transmission_lines", ["id", "voltage_kv", "volt_class", "owner", "status", "state"],
                         tol=0.0005)
    layers.append(dict(id="transmission_lines", group="Grid", title="Transmission lines (by voltage)", kind="line",
                       on=True, **info,
                       legend=[{"label": f"{k} kV" if k != "unknown" else "unknown kV", "color": v}
                               for k, v in VOLT_COLORS.items()],
                       style={"by": "volt_class", "colors": VOLT_COLORS}, meta=meta(man.get(("grid", "transmission_lines")))))

    subs = read(P / "grid/substations.geojson")
    excl = pd.read_csv(P / "sites/excluded_pois.csv", usecols=["id", "removed_reason"])
    subs = subs.merge(excl, on="id", how="left")
    subs["excluded_reason"] = subs["removed_reason"].where(subs["removed_reason"].notna(), None)
    src = subs["source"].fillna("unknown")
    kvs = subs["kv_source"].fillna("unknown")
    # same rule as screen.py sub_provisional
    subs["provisional"] = ((src == "osm") | kvs.isin(["osm", "inferred_from_lines", "unknown"])
                           | subs["name"].fillna("UNKNOWN").astype(str).str.upper().str.startswith("UNKNOWN"))
    subs["queue_active_mw"] = subs["queue_active_mw"].fillna(0).round(0)
    subs = subs[subs["max_kv"].fillna(0) >= 69]
    info = write_geojson(subs, "substations", ["id", "name", "max_kv", "min_kv", "owner", "status", "state", "county",
                                               "sub_type", "source", "kv_source", "lines", "queue_active_mw",
                                               "queue_n_active", "provisional", "excluded_reason", "volt_class"])
    layers.append(dict(id="substations", group="Grid", title="Substations 69 kV+ (size = kV, colour = queue MW)",
                       kind="point", on=True, **info,
                       legend=[{"label": "no name-matched queue (unknown)", "color": "#ffffff", "stroke": "#475569"},
                               {"label": "< 500 MW queued at POI", "color": "#fde68a"},
                               {"label": "500 to 2,000 MW", "color": "#f59e0b"},
                               {"label": "> 2,000 MW", "color": "#b91c1c"},
                               {"label": "removed as POI by screening (grey)", "color": "#cbd5e1"},
                               {"label": "provisional record (purple ring)", "color": "#ffffff", "stroke": "#7c3aed"}],
                       note="Queue MW is matched by POI name; 0 means no match, not an empty queue.",
                       meta=meta(man.get(("grid", "substations")))))

    # --- land
    blm = read(P / "land/blm_solar_available.geojson")
    blm["acres"] = blm["acres"].round(0)
    info = write_geojson(blm, "blm_solar_available", ["category", "state", "acres", "sez_name"], tol=0.002, precision=4)
    cats = {"Available (2024 Western Solar Plan ROD)": "#e8a317", "DRECP Development Focus Area (CA)": "#f08c00",
            "DRECP Variance Land (CA)": "#c9a227"}
    layers.append(dict(id="blm_solar_available", group="Land", title="BLM solar-available land", kind="fill", on=True,
                       **info, legend=[{"label": k, "color": v} for k, v in cats.items()],
                       style={"by": "category", "colors": cats},
                       note="DRECP Variance Land is riskier and is not counted as available in the scores.",
                       meta=meta(man.get(("land", "blm_solar_available")))))

    sez = read(P / "land/solar_energy_zones.geojson")
    info = write_geojson(sez, "solar_energy_zones", ["sez_name", "state", "status", "acres"], tol=0.001)
    layers.append(dict(id="solar_energy_zones", group="Land", title="Solar Energy Zones (SEZ)", kind="fill", on=False,
                       **info, legend=[{"label": "Developable", "color": "#d9480f"},
                                       {"label": "Non-developable", "color": "#868e96"}],
                       style={"by": "status", "colors": {"Developable": "#d9480f", "Non-developable": "#868e96"}},
                       meta=meta(man.get(("land", "solar_energy_zones")))))

    own = read(P / "land/ownership.geojson")
    own = own[own["category"] != "Private"]  # private is the background; drawing it adds weight but no information
    info = write_geojson(own, "ownership", ["category", "agency"], tol=0.004, precision=3)
    layers.append(dict(id="ownership", group="Land", title="Land ownership (surface manager)", kind="fill", on=False,
                       **info, legend=[{"label": k, "color": v} for k, v in OWN_COLORS.items() if k != "Private"]
                       + [{"label": "Private (unshaded)", "color": "#ffffff", "stroke": "#cbd5e1"}],
                       style={"by": "category", "colors": OWN_COLORS},
                       note="Surface management agency, not title. Generalised map copy.",
                       meta=meta(man.get(("land", "ownership")))))

    ex_colors = {"wilderness": "#2b8a3e", "nca_acec": "#5c940d", "critical_habitat": "#e8590c", "flood_zone_a": "#1971c2",
                 "tribal": "#862e9c", "military": "#c92a2a", "wetlands": "#0c8599", "slope_gt5": "#795548",
                 "urban": "#495057", "nps": "#7b5e3b"}
    ex_titles = {"wilderness": "Wilderness and WSAs", "nca_acec": "NCAs, monuments and ACECs",
                 "critical_habitat": "Critical habitat (USFWS)", "flood_zone_a": "FEMA flood zone A/V",
                 "tribal": "Tribal land", "military": "Military land", "wetlands": "Wetlands (NWI, 40 ac+)",
                 "slope_gt5": "Slope over 5 percent", "urban": "Urban areas", "nps": "National Park Service land"}
    for name in ex_titles:
        f = P / "land/exclusions" / f"{name}.geojson"
        if not f.exists():
            continue
        g = read(f)
        kinds = sorted(set(g["kind"].dropna())) if "kind" in g else []
        info = write_geojson(g, f"excl_{name}", ["kind", "constraint", "name", "subtype", "state"],
                             tol=0.003 if name in ("flood_zone_a", "slope_gt5", "wetlands") else 0.002, precision=4)
        layers.append(dict(id=f"excl_{name}", group="Exclusions", title=ex_titles[name], kind="fill", on=False, **info,
                           legend=[{"label": f"{'/'.join(kinds) or 'n/a'} constraint", "color": ex_colors[name]}],
                           style={"color": ex_colors[name]}, meta=meta(man.get(("land", f"exclusion_{name}")))))

    # --- infra
    pp = read(P / "infra/power_plants.geojson")
    pp["mw"] = pp["mw"].round(1)
    info = write_geojson(pp, "power_plants", ["plant", "utility", "state", "county", "tech", "mw", "status",
                                              "grid_voltage_kv", "first_operating_year"])
    tech_colors = {"solar": "#f59f00", "wind": "#22b8cf", "storage": "#7048e8", "gas": "#868e96", "coal": "#343a40",
                   "nuclear": "#e64980", "hydro": "#1c7ed6", "geothermal": "#c2255c", "other": "#adb5bd"}
    layers.append(dict(id="power_plants", group="Infrastructure", title="Power plants (EIA-860 2025)", kind="point",
                       on=False, **info, legend=[{"label": k, "color": v} for k, v in tech_colors.items()],
                       style={"by": "tech", "colors": tech_colors}, meta=meta(man.get(("infra", "power_plants")))))

    row = read(P / "infra/blm_solar_row_cases.geojson")
    info = write_geojson(row, "blm_solar_row_cases", ["case_id", "project_name", "customer", "case_type", "status",
                                                      "field_office", "state", "acres", "mw", "mw_est_low",
                                                      "mw_est_high"], tol=0.0005)
    layers.append(dict(id="blm_solar_row_cases", group="Infrastructure", title="Active BLM solar ROW cases (MLRS)",
                       kind="fill", on=False, **info, legend=[{"label": "active case footprint", "color": "#d6336c"}],
                       style={"color": "#d6336c"}, note="Footprints are often whole PLSS sections, not project areas.",
                       meta=meta(man.get(("infra", "blm_solar_row_cases")))))

    fib = read(P / "infra/fiber.geojson")
    info = write_geojson(fib, "fiber", ["basis", "is_proxy", "name", "operator", "medium", "state"], tol=0.001)
    layers.append(dict(id="fiber", group="Infrastructure", title="Fiber PROXY (telecom, interstate, rail)", kind="line",
                       on=False, **info, legend=[{"label": "proxy corridor (99% not confirmed fiber)",
                                                  "color": "#0ca678", "dash": True}],
                       style={"color": "#0ca678"}, meta=meta(man.get(("infra", "fiber")))))

    ws = read(P / "infra/water_stress.geojson")
    info = write_geojson(ws, "water_stress", ["water_stress", "bws_label", "state"], tol=0.004, precision=4)
    layers.append(dict(id="water_stress", group="Infrastructure", title="Water stress (WRI Aqueduct, 0 to 5)",
                       kind="fill", on=False, **info,
                       legend=[{"label": "0 low", "color": "#e7f5ff"}, {"label": "2", "color": "#ffe8a1"},
                               {"label": "3", "color": "#ffa94d"}, {"label": "4", "color": "#f76707"},
                               {"label": "5 extremely high", "color": "#a61e4d"}],
                       meta=meta(man.get(("infra", "water_stress")))))

    rd = read(P / "infra/roads_major.geojson")
    info = write_geojson(rd, "roads_major", ["road_class", "name"], tol=0.001)
    layers.append(dict(id="roads_major", group="Infrastructure", title="Major roads (TIGER)", kind="line", on=False,
                       **info, legend=[{"label": "interstate / US / state highway", "color": "#495057"}],
                       style={"color": "#495057"}, meta=meta(man.get(("infra", "roads_major")))))

    dc = read(P / "infra/data_centers_osm.geojson")
    info = write_geojson(dc, "data_centers_osm", ["name", "operator", "city", "state"])
    layers.append(dict(id="data_centers_osm", group="Infrastructure", title="Existing data centers (OSM, incomplete)",
                       kind="point", on=False, **info, legend=[{"label": "OSM data center", "color": "#364fc7"}],
                       style={"color": "#364fc7"}, meta=meta(man.get(("infra", "data_centers_osm")))))

    # --- admin
    st = read(P / "land/admin_states.geojson")
    info = write_geojson(st, "admin_states", ["state", "name"], tol=0.002, precision=4)
    layers.append(dict(id="admin_states", group="Reference", title="State boundaries", kind="outline", on=True, **info,
                       legend=[{"label": "state line", "color": "#334155"}], meta=meta(man.get(("land", "admin_states")))))
    co = read(P / "land/admin_counties.geojson")
    info = write_geojson(co, "admin_counties", ["state", "county"], tol=0.003, precision=4)
    layers.append(dict(id="admin_counties", group="Reference", title="County boundaries", kind="outline", on=False,
                       **info, legend=[{"label": "county line", "color": "#94a3b8"}],
                       meta=meta(man.get(("land", "admin_counties")))))

    # --- rasters
    (OUT / "overlays").mkdir(exist_ok=True)
    for name, title in [("ghi", "Solar resource GHI (kWh/m2/day)"), ("slope", "Slope (percent, 3 percent+ shown)")]:
        e = man.get(("land", name))
        if not e or not e.get("overlay_png"):
            continue
        shutil.copy2(ROOT / e["overlay_png"], OUT / "overlays" / f"{name}.png")
        b = e["overlay_bounds"]
        legend = [{"label": f"{x['value']:g}", "color": "rgba({},{},{},{:.2f})".format(*x["rgba"][:3], x["rgba"][3] / 255)}
                  for x in e["overlay_legend"] if x["rgba"][3] > 0]
        layers.append(dict(id=f"raster_{name}", group="Resource", title=title, kind="raster", on=False,
                           file=f"data/overlays/{name}.png",
                           bounds=[[b["west"], b["north"]], [b["east"], b["north"]], [b["east"], b["south"]],
                                   [b["west"], b["south"]]], legend=legend, meta=meta(e)))
    return layers


SITE_FIELDS = ["site_id", "state", "county", "acres", "owner_category", "blm_solar_available", "blm_status", "sez_name",
               "centroid_lat", "centroid_lon", "nearest_sub_id", "nearest_sub_name", "nearest_sub_kv", "nearest_sub_owner",
               "dist_sub_km", "nearest_sub230_name", "nearest_sub230_kv", "dist_sub230_km", "nearest_line_kv",
               "dist_line_km", "dist_line230_km", "queued_mw_county", "queued_mw_county_solar",
               "queued_mw_county_storage", "nearest_sub_queue_mw", "queue_confidence", "queue_poi_match_rate",
               "ghi", "mean_slope", "constraints_soft", "fiber_km", "fiber_basis", "water_stress", "water_stress_label",
               "road_km", "road_name", "score_grid", "score_land", "score_sun", "score_permit", "score_dc",
               "score_total_solar", "score_total_dc", "rank_solar", "rank_dc", "solar_mw_est", "sub_provisional",
               "sub_source", "sub_kv_source", "row_cases_overlap", "blm_fo_hint", "next_step"]


def build_sites():
    src = P / "sites/candidate_sites.geojson"
    g = gpd.read_file(src, engine="pyogrio").to_crs(4326)
    g = g.sort_values("rank_solar").reset_index(drop=True)
    log.info("sites: %d ranked candidate polygons", len(g))
    cols = {}
    for c in SITE_FIELDS:
        if c not in g.columns:
            log.info("sites: field %s missing, skipped", c)
            continue
        v = g[c]
        if v.dtype.kind == "f":
            cols[c] = [None if pd.isna(x) else round(float(x), 3) for x in v]
        elif v.dtype.kind in "iu":
            cols[c] = [int(x) for x in v]
        elif v.dtype.kind == "b":
            cols[c] = [bool(x) for x in v]
        else:
            vals = [None if (x is None or (isinstance(x, float) and np.isnan(x))) else
                    (bool(x) if isinstance(x, (bool, np.bool_)) else str(x)) for x in v]
            uniq = {}
            if all(x is None or isinstance(x, str) for x in vals) and c != "site_id":
                # dictionary-encode repeated strings: {"dict": [...], "idx": [...]} (idx -1 = null)
                idx = [-1 if x is None else uniq.setdefault(x, len(uniq)) for x in vals]
                cols[c] = {"dict": list(uniq), "idx": idx}
            else:
                cols[c] = vals
    (OUT / "sites_attr.json").write_text(json.dumps({"n": len(g), "columns": cols}, separators=(",", ":")))
    log.info("sites_attr.json %.1f MB", (OUT / "sites_attr.json").stat().st_size / 1e6)
    geom = gpd.GeoDataFrame({"i": np.arange(len(g))}, geometry=g.geometry.simplify(0.0012, preserve_topology=True),
                            crs=4326)
    dst = OUT / "sites_geom.geojson"
    if dst.exists():
        dst.unlink()
    pyogrio.write_dataframe(geom, dst, driver="GeoJSON", layer_options={"COORDINATE_PRECISION": 4, "RFC7946": "YES"})
    log.info("sites_geom.geojson %.1f MB", dst.stat().st_size / 1e6)
    return g


def build_summary(sites):
    q = pd.read_csv(P / "grid/queue_projects.csv", usecols=["state", "type", "mw", "status"])
    a = q[q["status"] == "active"]
    qt = a.groupby(["state", "type"])["mw"].sum().unstack(fill_value=0).reindex(STATES).fillna(0) / 1000
    queue = {"states": STATES, "types": list(qt.columns),
             "gw": {t: [round(float(x), 2) for x in qt[t]] for t in qt.columns},
             "n_active": int(len(a))}
    # Spare-looking capacity proxy (not headroom): 230 kV+ non-provisional substations that are the nearest POI of at
    # least one candidate site, ranked by candidate solar MW nearby relative to name-matched active queue MW.
    subs = gpd.read_file(P / "grid/substations.geojson", engine="pyogrio",
                         columns=["id", "name", "max_kv", "state", "queue_active_mw", "queue_n_active", "lines", "source",
                                  "kv_source"])
    use = sites.groupby("nearest_sub_id").agg(n_sites=("site_id", "size"), site_mw=("solar_mw_est", "sum"),
                                              prov=("sub_provisional", "max")).reset_index()
    m = use.merge(pd.DataFrame(subs.drop(columns="geometry")), left_on="nearest_sub_id", right_on="id")
    m = m[(m["max_kv"] >= 230) & (~m["prov"].astype(bool))]
    m["queue_active_mw"] = m["queue_active_mw"].fillna(0)
    m = m.sort_values(["queue_active_mw", "max_kv", "site_mw"], ascending=[True, False, False])
    top = m.head(15)
    proxy = [{"id": r.id, "name": r.name, "state": r.state, "max_kv": float(r.max_kv), "lines": None if pd.isna(r.lines)
              else int(r.lines), "queue_active_mw": float(r.queue_active_mw), "queue_n_active": int(r.queue_n_active or 0),
              "n_sites": int(r.n_sites), "site_mw": round(float(r.site_mw))} for r in top.itertuples()]
    summary = {"queue": queue, "sub_proxy": proxy,
               "sub_proxy_note": ("Proxy, not headroom: 230 kV+ substations that are the nearest usable POI for at least "
                                  "one candidate site and are not provisional, sorted by fewest name-matched active queue "
                                  "MW, then highest kV, then most candidate solar MW nearby. Queue MW is matched by POI "
                                  "name, so 0 can mean no match. Real capacity comes only from the utility."),
               "generated": time.strftime("%Y-%m-%d %H:%M")}
    (OUT / "summary.json").write_text(json.dumps(summary, indent=1))


def scope_limits():
    t = (ROOT / "SCOPE.md").read_text()
    m = re.search(r"## 7\.[^\n]*\n(.*?)(\n## |\Z)", t, re.S)
    if not m:
        return []
    return [re.sub(r"^\s*-\s*", "", x).strip() for x in m.group(1).splitlines() if x.strip().startswith("-")]


def build_sources(man, sites):
    entries = []
    for (d, layer), e in man.items():
        entries.append({"domain": d} | meta(e))
    prov_n = int(sites["sub_provisional"].astype(bool).sum())
    top50 = sites.nsmallest(50, "rank_solar")["sub_provisional"].astype(bool).sum()
    top50dc = sites.nsmallest(50, "rank_dc")["sub_provisional"].astype(bool).sum()
    method = (P / "sites/METHOD.md").read_text() if (P / "sites/METHOD.md").exists() else ""
    mm = re.search(r"(\d[\d,]*) of (\d[\d,]*) usable 115 kV\+ substations are provisional", method)
    prov_note = ("A substation record is provisional when it is OSM-only, its voltage came from OSM or was inferred from "
                 "nearby lines, or its name is UNKNOWN. Screening multiplies the grid score of a site whose nearest "
                 "substation is provisional by 0.85. ")
    if mm:
        prov_note += f"{mm.group(1)} of {mm.group(2)} usable 115 kV+ substations are provisional. "
    prov_note += (f"{prov_n:,} of {len(sites):,} ranked sites have a provisional nearest substation; {int(top50)} of the top 50 "
                  f"solar sites and {int(top50dc)} of the top 50 data center sites do. Queue congestion is county level "
                  f"with a confidence flag: {int((sites['queue_confidence'] == 'high').sum()):,} ranked sites high, "
                  f"{int((sites['queue_confidence'] != 'high').sum()):,} low. Counties with no matched active queue MW get a "
                  "neutral queue score, not the best one. Fiber is a proxy (99 percent of features are not confirmed "
                  "fiber), so the data center ranking is weaker than the solar ranking.")
    open_items = ("Still open after the review: parcel-level BLM legal status and encumbrances, utility territory and real "
                  "headroom, confirmed fiber, cost and schedule modelling, and weight sensitivity runs.")
    lim = re.search(r"## 6\. Limits\n(.*?)(\n## |\Z)", method, re.S)
    method_limits = [re.sub(r"^\s*-\s*", "", x).strip() for x in lim.group(1).splitlines()
                     if x.strip().startswith("-")] if lim else []
    sources = {"datasets": entries, "scope_limits": scope_limits(), "method_limits": method_limits,
               "provisional_note": prov_note, "open_items": open_items}
    (OUT / "sources.json").write_text(json.dumps(sources, indent=1))


def build_deliverables():
    d = ROOT / "deliverables"
    items = []

    def add(path, title, kind):
        if path.exists():
            items.append({"title": title, "href": "../" + str(path.relative_to(ROOT)), "kind": kind})
    add(d / "Southwest_Solar_Sites.xlsx", "Ranked site table (Excel)", "file")
    add(d / "BLM_Application_Brief.md", "BLM application brief", "md")
    add(d / "sources_blm.md", "BLM brief sources", "md")
    add(P / "sites/METHOD.md", "Screening and scoring method", "md")
    memos = []
    if (d / "site_memos").exists():
        for f in sorted((d / "site_memos").glob("*.md")):
            first = f.read_text().splitlines()[0].lstrip("# ").strip() if f.stat().st_size else f.stem
            memos.append({"title": first, "file": f.name, "href": "../" + str(f.relative_to(ROOT)),
                          "site_id": (re.search(r"SW-[A-Z]{2}-\d{5}", f.name) or [None])[0]})
    appendix = None
    if REVIEW.exists():
        (OUT / "appendix").mkdir(exist_ok=True)
        shutil.copy2(REVIEW, OUT / "appendix" / "METHODOLOGY_REVIEW.md")
        appendix = {"title": "Appendix: independent methodology review (GPT, 2026-10-21)",
                    "href": "data/appendix/METHODOLOGY_REVIEW.md", "kind": "md"}
    else:
        log.info("methodology review not found at %s", REVIEW)
    (OUT / "deliverables.json").write_text(json.dumps({"items": items, "memos": memos, "appendix": appendix}, indent=1))
    log.info("deliverables: %d items, %d memos, appendix %s", len(items), len(memos), bool(appendix))


def method_weights():
    """Default weights of both rankings, read from METHOD.md (written by screen.py from its WEIGHTS dict)."""
    t = (P / "sites/METHOD.md").read_text()
    out = {}
    for key, name in [("solar", "score_total_solar"), ("dc", "score_total_dc")]:
        m = re.search(r"\*\*" + name + r"\*\* = \(([^)]*)\)", t)
        w = {"grid": 0, "land": 0, "sun": 0, "permit": 0, "dc": 0}
        for f, v in re.findall(r"(grid|land|sun|permit|dc) x (\d+(?:\.\d+)?)", m.group(1)):
            w[f] = float(v)
        out[key] = w
    log.info("default weights from METHOD.md: %s", out)
    return out


def inputs():
    for d in ["grid", "land", "infra", "sites"]:
        for f in (P / d).rglob("*"):
            if f.is_file() and f.suffix in (".geojson", ".json", ".csv", ".png", ".md") and "work" not in f.parts:
                yield f
    for f in (ROOT / "deliverables").rglob("*"):
        if f.is_file():
            yield f
    yield ROOT / "SCOPE.md"
    yield Path(__file__)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="rebuild even if app/data is up to date")
    a = ap.parse_args()
    done = OUT / "layers.json"
    if done.exists() and not a.force:
        newest = max(f.stat().st_mtime for f in inputs())
        if done.stat().st_mtime >= newest:
            log.info("app/data is up to date (use --force to rebuild)")
            return
    t0 = time.time()
    (OUT / "layers").mkdir(parents=True, exist_ok=True)
    man = manifest_entries()
    sites = build_sites()
    layers = build_layers(man)
    build_summary(sites)
    build_sources(man, sites)
    build_deliverables()
    site_meta = {"layer": "candidate_sites", "path": "data/processed/sites/candidate_sites.geojson",
                 "source_name": "pipeline/screen.py (see data/processed/sites/METHOD.md)",
                 "record_count": int(len(sites)), "retrieved": time.strftime(
                     "%Y-%m-%d", time.localtime((P / "sites/candidate_sites.geojson").stat().st_mtime)),
                 "caveats": "Screening result, not engineering. Polygons simplified for display; acres are exact-cut."}
    doc = {"generated": time.strftime("%Y-%m-%d %H:%M"), "states": STATES,
           "sites": {"geom": "data/sites_geom.geojson", "attr": "data/sites_attr.json", "n": int(len(sites)),
                     "weights": method_weights(),
                     "meta": site_meta},
           "layers": layers}
    done.write_text(json.dumps(doc, indent=1))
    total = sum(f.stat().st_size for f in OUT.rglob("*") if f.is_file()) / 1e6
    log.info("wrote %s: %d layers, %d sites, app/data %.0f MB, %.0f s", done.relative_to(ROOT), len(layers), len(sites),
             total, time.time() - t0)


if __name__ == "__main__":
    main()

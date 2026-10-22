# /// script
# requires-python = ">=3.10"
# dependencies = ["playwright==1.48.0"]
# ///
"""Headless browser test of the v2 dashboard (Playwright's bundled Chromium, software WebGL). Port of app/tests/test_app.py.

Run: uv run --script app-v2/tests/test_v2.py [--port 4110]
Starts its own app-v2/serve.py on port 4110 (never touches the user's server on 8770), loads http://localhost:4110/app-v2/,
runs every v1 check against v2 (layers on and off, basemaps, site click and scorecard, provisional badge, weight slider,
filters, ranking switch, CSV export, table sort and row click, Summary, Sources, Deliverables and its links,
How to Read This with all 10 sections, memo and appendix pages, layout at 1440 and 1280 px), adds v2 checks
(fonts self-hosted and loaded, no em dashes, no CDN, no rounded boxes, scorecard opens as a column beside the map,
map key lists the layers that are on, v1 files unchanged), and saves screenshots to app-v2/screenshots/.

A watchdog thread prints a progress line every 30 s and aborts the run (exit 3) if any single step exceeds its hard
30 s limit. Results go to app-v2/tests/last_run.json and app-v2/tests/RESULTS.md. Fails on any console or page error.
"""
import argparse
import csv
import hashlib
import json
import os
import subprocess
import sys
import threading
import time
import urllib.request
from contextlib import contextmanager
from pathlib import Path

from playwright.sync_api import sync_playwright

V2 = Path(__file__).resolve().parents[1]
ROOT = V2.parent
SHOTS = V2 / "screenshots"
TESTS = V2 / "tests"
ap = argparse.ArgumentParser()
ap.add_argument("--port", type=int, default=4110)
ARGS = ap.parse_args()
URL = f"http://localhost:{ARGS.port}/app-v2/"
V1URL = f"http://localhost:{ARGS.port}/app/"
LAUNCH_ARGS = ["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"]
STEP_LIMIT = 30
T_START = time.time()
TOTAL_LIMIT = 590

results = []
errors = []
SRV = None


def stamp():
    s = int(time.time() - T_START)
    return f"[{s // 60:02d}:{s % 60:02d}]"


def check(name, ok, detail=""):
    results.append((name, bool(ok), str(detail)))
    print(f"{stamp()} {'PASS' if ok else 'FAIL'}  {name}{'  ' + str(detail) if detail else ''}", flush=True)


def write_results(aborted=None):
    (TESTS / "last_run.json").write_text(json.dumps([{"check": a, "ok": b, "detail": c} for a, b, c in results], indent=1))
    n_fail = sum(1 for r in results if not r[1])
    lines = ["# Dashboard v2 headless test results", "",
             f"Run: {time.strftime('%Y-%m-%d %H:%M:%S')} with `uv run --script app-v2/tests/test_v2.py` "
             f"(Playwright 1.48.0, bundled Chromium, headless, software WebGL; test server app-v2/serve.py on port {ARGS.port}).",
             f"Total time {time.time() - T_START:.0f} s. Hard limit per step: {STEP_LIMIT} s; a progress line is printed every 30 s.", "",
             f"**{len(results) - n_fail} passed, {n_fail} failed{', ABORTED: ' + aborted if aborted else ''}**", "",
             "Every check of v1's app/tests/test_app.py is ported, except the two that run pipeline/run_all.py: that script "
             "belongs to the pipeline, not the dashboard, and running it from here could write outside app-v2/. "
             "The How to Read This colour words are checked in their v2 form (DESIGN.md section 9.3).", "",
             "| # | Check | Result | Detail |", "|---|---|---|---|"]
    for k, (a, b, c) in enumerate(results, 1):
        lines.append(f"| {k} | {a} | {'PASS' if b else 'FAIL'} | {c.replace('|', '/')[:300]} |")
    shots = sorted(p.name for p in SHOTS.glob("*.png"))
    lines += ["", "Screenshots saved in app-v2/screenshots/:", ""] + [f"- {s}" for s in shots]
    (TESTS / "RESULTS.md").write_text("\n".join(lines) + "\n")
    return n_fail


class Watchdog:
    def __init__(self):
        self.name, self.t0, self.limit = "startup", time.time(), 60
        self.last_print = time.time()
        threading.Thread(target=self.loop, daemon=True).start()

    @contextmanager
    def step(self, name, limit=STEP_LIMIT):
        self.name, self.t0, self.limit = name, time.time(), limit
        print(f"{stamp()} step: {name}", flush=True)
        try:
            yield
        except Exception as e:  # noqa: BLE001
            check(name, False, f"{type(e).__name__}: {str(e).splitlines()[0][:200]}")
        finally:
            self.name, self.t0, self.limit = "between steps", time.time(), 60

    def loop(self):
        while True:
            time.sleep(1)
            now = time.time()
            el = now - self.t0
            if now - self.last_print >= 30:
                print(f"{stamp()} ... progress: {len(results)} checks so far, current step: {self.name} ({el:.0f} s of {self.limit} s)", flush=True)
                self.last_print = now
            if el > self.limit or now - T_START > TOTAL_LIMIT:
                why = f"step '{self.name}' exceeded {self.limit} s" if el > self.limit else "total time limit"
                print(f"{stamp()} ABORT: {why}", flush=True)
                check(self.name, False, f"timed out: {why}")
                write_results(aborted=why)
                stop_server()
                os._exit(3)


def stop_server():
    if SRV and SRV.poll() is None:
        try:
            os.killpg(SRV.pid, 15)
            SRV.wait(timeout=10)
        except Exception:  # noqa: BLE001
            pass


WD = Watchdog()


def wait_idle(page, timeout=25000):
    page.wait_for_function("""() => new Promise(r => { const m = (typeof map !== "undefined" && map && map.loaded) ? map : null; if (!m) return r(false);
        if (m.loaded() && !m.isMoving()) return r(true); m.once('idle', () => r(true)); setTimeout(() => r(false), 4000); })""",
                           timeout=timeout)


def new_page(p, width=1440, height=900):
    browser = p.chromium.launch(headless=True, args=LAUNCH_ARGS)
    ctx = browser.new_context(viewport={"width": width, "height": height}, accept_downloads=True)
    page = ctx.new_page()
    page.set_default_timeout(25000)
    page.on("console", lambda m: errors.append(f"console {m.type}: {m.text}") if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
    return browser, ctx, page


def load(page):
    t0 = time.time()
    page.goto(URL)
    page.wait_for_function("window.__appReady === true", timeout=28000)
    return time.time() - t0


def v1_checksums():
    out = []
    for f in sorted((ROOT / "app").rglob("*")):
        if f.is_file():
            out.append(f"{hashlib.sha256(f.read_bytes()).hexdigest()}  {f.relative_to(ROOT)}")
    return out


def main():
    global SRV
    SHOTS.mkdir(exist_ok=True)
    for f in SHOTS.glob("[0-9][0-9]_*.png"):
        f.unlink()
    SRV = subprocess.Popen(["/opt/homebrew/bin/uv", "run", "--script", str(V2 / "serve.py"), "--port", str(ARGS.port), "--no-browser"],
                           cwd=V2, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    try:
        with WD.step("start test server"):
            for _ in range(50):
                try:
                    urllib.request.urlopen(URL, timeout=1)
                    break
                except Exception:  # noqa: BLE001
                    time.sleep(0.5)
            check("test server answers", urllib.request.urlopen(URL, timeout=2).status == 200, URL)
        with sync_playwright() as p:
            if not os.environ.get("SKIP_LAYERS"):
                session_layers(p)
            session_interactions(p)
            session_screens(p)
    finally:
        stop_server()
    check("no console errors or page errors", not errors, "; ".join(errors[:5]) or "none")
    with WD.step("project checks"):
        rd = (ROOT / "README.md").read_text() if (ROOT / "README.md").exists() else ""
        check("project README.md present (run, refresh, sources, limits, folder map)",
              all(k in rd for k in ["app/serve.py", "run_all.py", "## Data sources", "## Limits", "## Folder map", "8770"]))
        check("v2 serve.py default port 8772 and v2 README explains how to open it",
              "default=8772" in (V2 / "serve.py").read_text() and "http://localhost:8770/app-v2/" in (V2 / "README.md").read_text())
        html = (V2 / "index.html").read_text()
        check("index.html: no CDN script, no em dash", "\u2014" not in html and 'src="http' not in html)
        before = (TESTS / "v1_checksums_before.txt").read_text().split("\n")
        before = [ln.strip() for ln in before if ln.strip()]
        now = v1_checksums()
        check("v1 files unchanged (checksums of app/ before and after)", sorted(before) == sorted(now), f"{len(now)} files compared")
    n_fail = write_results()
    print(f"\n{len(results) - n_fail} passed, {n_fail} failed", flush=True)
    sys.exit(1 if n_fail else 0)


def session_layers(p):
    """Session 1: load, data sanity, ranking parity, toggle every layer on and off, map key follows."""
    browser, ctx, page = new_page(p)
    with WD.step("load page (first)"):
        dt = load(page)
        check("page loads with data", True, f"{dt:.1f} s")
        check("Map is the default view", page.evaluate("document.querySelector('#view-map').classList.contains('active') && document.querySelector('#tabs button.active').dataset.view === 'map'"))
    with WD.step("data covers five states"):
        n = page.evaluate("window.__app.S.n")
        states = page.evaluate("[...new Set(window.__app.S.cols.state)].sort()")
        check("sites from all five states", states == ["AZ", "CA", "NM", "NV", "UT"] and n > 1000, f"{n} sites, {states}")
        check("map libraries load locally (no CDN scripts)",
              page.evaluate("[...document.scripts].every(s => !s.src || s.src.startsWith(location.origin))"))
        check("no stylesheet or font from another origin",
              page.evaluate("performance.getEntriesByType('resource').filter(r => /\\.(css|woff2?|js)(\\?|$)/.test(r.name)).every(r => r.name.startsWith(location.origin))"))
    with WD.step("v2 design checks"):
        page.evaluate("document.fonts.ready")
        fonts = page.evaluate("""[document.fonts.check('600 20px "Source Serif 4"'), document.fonts.check('400 13px "IBM Plex Sans"'),
            [...document.fonts].filter(f => f.status === 'loaded').map(f => f.family + ' ' + f.weight).join(', ')]""")
        check("self-hosted fonts load (Source Serif 4, IBM Plex Sans)", fonts[0] and fonts[1], fonts[2])
        check("no em dash in any visible text", not page.evaluate("document.body.innerText.includes('\\u2014')"))
        rounded = page.evaluate("""[...document.querySelectorAll('body *')].filter(e => { const s = getComputedStyle(e);
            const r = parseFloat(s.borderTopLeftRadius); return r > 2.5 && !s.borderTopLeftRadius.includes('%') && e.offsetWidth > 0 && !e.closest('.maplibregl-ctrl'); })
            .map(e => e.id || e.className).slice(0, 5)""")
        check("no rounded boxes (corner radius at most 2 px)", not rounded, ", ".join(map(str, rounded)) or "none")
        shadows = page.evaluate("""[...document.querySelectorAll('body *')].filter(e => { const s = getComputedStyle(e).boxShadow;
            return s !== 'none' && /\) -?\\d+px -?\\d+px [1-9]\\d*px/.test(s) && e.offsetWidth > 0; }).map(e => e.id || e.className).slice(0, 5)""")
        check("no soft drop shadows", not shadows, ", ".join(map(str, shadows)) or "none")
        key = page.evaluate("[...document.querySelectorAll('#key-groups .kg')].map(g => g.dataset.key)")
        on = page.evaluate("['sites', ...window.__app.S.doc.layers.filter(l => l.on).map(l => l.id)]")
        check("map key lists exactly the layers that are on, sites first", key == on, ", ".join(key))
    for mode, col in [("solar", "rank_solar"), ("dc", "rank_dc")]:
        with WD.step(f"ranking parity {mode}"):
            page.click(f"#mode-{mode}")
            page.wait_for_timeout(600)
            mism = page.evaluate(f"""() => {{ const S = window.__app.S; let bad = 0;
                for (let k = 0; k < 25; k++) {{ const i = S.order[k]; if (Math.abs(S.cols['{col}'][i] - (k + 1)) > 2) bad++; }} return bad; }}""")
            check(f"default {mode} ranking matches pipeline {col} (top 25, within 2 places)", mism == 0, f"{mism} mismatches")
    page.click("#mode-solar")
    page.wait_for_timeout(400)
    layer_ids = page.evaluate("window.__app.S.doc.layers.map(l => l.id)")
    print(f"{stamp()} {len(layer_ids)} layers to toggle", flush=True)
    for lid in layer_ids:
        with WD.step(f"toggle layer {lid}"):
            cb = page.locator(f'#layer-list input[data-layer="{lid}"]')
            was = cb.is_checked()
            if not was:
                cb.check()
            page.wait_for_function(f"""() => {{ const S = window.__app.S; return S.loaded['{lid}'] &&
                (S.mapLayers['{lid}'] || []).every(l => map.getLayoutProperty(l, 'visibility') === 'visible'); }}""", timeout=25000)
            nfeat = page.evaluate(f"""() => {{ const s = map.getSource('{lid}'); return s.type === 'image' ? 1 :
                (s._data && s._data.features ? s._data.features.length : -1); }}""")
            in_key = page.evaluate(f"!!document.querySelector('#key-groups [data-key=\"{lid}\"]')")
            cb.uncheck()
            page.wait_for_function(f"(window.__app.S.mapLayers['{lid}'] || []).every(l => map.getLayoutProperty(l, 'visibility') === 'none')")
            gone = not page.evaluate(f"!!document.querySelector('#key-groups [data-key=\"{lid}\"]')")
            if was:
                cb.check()
            check(f"layer on/off: {lid}", nfeat != 0 and in_key and gone, (f"{nfeat} features" if nfeat >= 0 else "loaded") + ", map key follows")
    with WD.step("toggle candidate sites layer"):
        page.locator('#layer-list input[data-layer="sites"]').uncheck()
        hidden = page.evaluate("map.getLayoutProperty('sites-pt','visibility') === 'none'")
        page.locator('#layer-list input[data-layer="sites"]').check()
        check("layer on/off: candidate sites", hidden and page.evaluate("map.getLayoutProperty('sites-pt','visibility') === 'visible'"))
    with WD.step("layer source panel"):
        page.hover("#li-substations")
        page.click("#ltag-substations")
        page.wait_for_selector("#modal:not(.hidden)", timeout=5000)
        mt = page.text_content("#modal-body")
        page.keyboard.press("Escape")
        page.wait_for_timeout(200)
        check("Source panel opens with source, retrieved date and caveats; Esc closes it",
              "Retrieved" in mt and "Caveats" in mt and page.evaluate("document.querySelector('#modal').classList.contains('hidden')"))
    with WD.step("close browser (session 1)"):
        browser.close()


def session_interactions(p):
    """Session 2: basemaps, site click and scorecard, weight slider, filters, mode switch, CSV, tabs, links."""
    browser, ctx, page = new_page(p)
    with WD.step("load page (session 2)"):
        load(page)
    for b in ["satellite", "terrain", "none", "street"]:
        with WD.step(f"basemap {b}"):
            page.click(f'#basemap label:has(input[value="{b}"])')
            vis = page.evaluate("['street','satellite','terrain'].filter(b => map.getLayoutProperty('base-' + b, 'visibility') === 'visible')")
            check(f"basemap switch: {'plain' if b == 'none' else b}", vis == ([] if b == "none" else [b]), ", ".join(vis) or "no raster base")

    with WD.step("click top site on map"):
        top = page.evaluate("window.__app.S.order[0]")
        lon, lat, sid = page.evaluate(f"[window.__app.S.cols.centroid_lon[{top}], window.__app.S.cols.centroid_lat[{top}], window.__app.S.cols.site_id[{top}]]")
        page.evaluate(f"void map.jumpTo({{center: [{lon}, {lat}], zoom: 10.5}})")
        wait_idle(page)
        pt = page.evaluate(f"""() => {{ const c = map.project([{lon}, {lat}]); const r = map.getContainer().getBoundingClientRect();
            for (let dx = 0; dx < 60; dx += 6) for (const s of [1, -1]) {{ const x = c.x + s * dx, y = c.y;
              const hit = map.queryRenderedFeatures([[x - 4, y - 4], [x + 4, y + 4]], {{layers: ['sites-fill']}});
              if (hit.some(f => f.layer.id === 'sites-fill' && f.properties.i === {top})) return [x + r.left, y + r.top]; }}
            return [c.x + r.left, c.y + r.top]; }}""")
        mapw0 = page.evaluate("document.querySelector('#map').getBoundingClientRect().width")
        page.mouse.click(pt[0], pt[1])
        page.wait_for_selector("#scorecard:not(.hidden)", timeout=10000)
        page.wait_for_timeout(500)
        txt = page.text_content("#scorecard")  # raw text; inner_text applies CSS uppercase to section titles
        check("click site on map opens scorecard", sid in txt and "Score by factor" in txt and "Recommended next step" in txt, sid)
        check("scorecard shows substation, queue, GHI, BLM status, data center fit",
              all(k in txt for k in ["Nearest 115 kV+ substation", "Active queue in county", "GHI", "BLM status", "Data center fit"]))
        geo = page.evaluate("""() => { const m = document.querySelector('#map').getBoundingClientRect(), s = document.querySelector('#scorecard').getBoundingClientRect();
            return [m.width, m.right, s.left, s.width]; }""")
        check("scorecard opens as a column beside the map (map narrows, nothing covers it)",
              geo[0] < mapw0 - 300 and geo[2] >= geo[1] - 1 and geo[3] >= 350, f"map {mapw0:.0f} -> {geo[0]:.0f} px, sheet {geo[3]:.0f} px")
        check("selected site outlined in ink over a white halo", page.evaluate(
            f"JSON.stringify(map.getFilter('sites-sel')) === JSON.stringify(['==', ['get', 'i'], {top}]) && map.getPaintProperty('sites-sel-halo', 'line-width') === 6"))

    with WD.step("provisional badge"):
        prov = page.evaluate("window.__app.S.order.find(i => window.__app.S.cols.sub_provisional[i] === true)")
        if prov is None:
            check("provisional badge on scorecard", True, "no provisional site in data; not applicable")
        else:
            page.evaluate(f"window.__app.selectSite({prov}, false)")
            page.wait_for_timeout(600)
            t2 = page.inner_text("#scorecard")
            check("provisional badge on scorecard", "Provisional substation" in t2, page.evaluate(f"window.__app.S.cols.site_id[{prov}]"))

    with WD.step("scorecard closes with Esc"):
        page.keyboard.press("Escape")
        page.wait_for_timeout(400)
        check("Esc closes the scorecard and returns the width to the map",
              page.evaluate("document.querySelector('#scorecard').classList.contains('hidden') && window.__app.S.selected === null"))

    with WD.step("weight slider re-ranks"):
        page.evaluate("void map.jumpTo({center: [-112.5, 36.2], zoom: 4.9})")
        before = page.evaluate("window.__app.S.order.slice(0, 20)")
        w0 = page.evaluate("window.__app.S.weights.sun")
        page.focus("#w-sun")
        for _ in range(25):
            page.keyboard.press("ArrowRight")
        page.wait_for_timeout(900)
        after = page.evaluate("window.__app.S.order.slice(0, 20)")
        w = page.evaluate("window.__app.S.weights.sun")
        check("weight slider (sun) re-ranks sites", before != after and w > w0 and "Custom weights" in page.inner_text("#weights-hint"),
              f"sun weight {w0} -> {w}; top site {page.evaluate('window.__app.S.cols.site_id[window.__app.S.order[0]]')}")
        top_id = page.evaluate("window.__app.S.cols.site_id[window.__app.S.order[0]]")
        check("ranked table synced with new ranking", top_id in page.inner_text("#site-table tbody tr:first-child"), top_id)
        page.click("#reset-weights")
        page.wait_for_timeout(500)

    with WD.step("filters"):
        page.check("#f-blm")
        page.wait_for_timeout(700)
        allblm = page.evaluate("window.__app.S.order.length > 0 && window.__app.S.order.every(i => window.__app.S.cols.blm_solar_available[i] === true)")
        check("BLM-only filter", allblm, page.text_content("#filter-count"))
        check("rail readout follows the filters", page.inner_text("#readout-n") == f"{page.evaluate('window.__app.S.order.length'):,}", page.inner_text("#readout-n"))
        page.uncheck("#f-blm")
        page.click('#state-filter label:has(input[value="UT"])')
        page.wait_for_timeout(700)
        noUT = page.evaluate("window.__app.S.order.every(i => window.__app.S.cols.state[i] !== 'UT')")
        page.click('#state-filter label:has(input[value="UT"])')
        page.wait_for_timeout(500)
        check("state filter (untick UT)", noUT)

    with WD.step("switch Solar + Data Center"):
        page.click("#mode-dc")
        page.wait_for_timeout(700)
        dc_top = page.evaluate("window.__app.S.cols.site_id[window.__app.S.order[0]]")
        check("ranking switch to Solar + Data Center", page.evaluate("window.__app.S.mode === 'dc' && window.__app.S.weights.dc > 0")
              and "Solar + Data Center" in page.inner_text("#table-title") and page.get_attribute("#mode-dc", "aria-pressed") == "true", f"top DC site {dc_top}")
        page.click("#mode-solar")
        page.wait_for_timeout(700)
        check("ranking switch back to Solar", page.evaluate("window.__app.S.mode === 'solar'"),
              f"top solar site {page.evaluate('window.__app.S.cols.site_id[window.__app.S.order[0]]')}")

    with WD.step("export CSV of current view"):
        page.evaluate("void map.jumpTo({center: [-114.5, 35.3], zoom: 7})")
        wait_idle(page)
        page.wait_for_timeout(500)
        nview = page.evaluate("window.__app.S.viewRows.length")
        with page.expect_download(timeout=15000) as dl:
            page.click("#export-csv")
        out = TESTS / "export_test.csv"
        dl.value.save_as(out)
        with out.open() as f:
            rows = list(csv.DictReader(f))
        check("CSV export of current view", len(rows) == nview and nview > 0 and rows[0].get("view_rank") and "site_id" in rows[0],
              f"{len(rows)} rows, {len(rows[0]) if rows else 0} columns, file {dl.value.suggested_filename}")

    with WD.step("table sort and row click"):
        page.click('#site-table th[data-k="acres"]')
        page.wait_for_timeout(300)
        ac = page.evaluate("window.__app.S.viewRows.slice(0, 5).map(i => window.__app.S.cols.acres[i])")
        check("table sorts by column", ac == sorted(ac, reverse=True), str(ac))
        want = int(page.get_attribute("#site-table tbody tr:nth-child(2)", "data-i"))
        page.click("#site-table tbody tr:nth-child(2)")
        page.wait_for_timeout(1500)
        check("table row click selects site (and the map flies to it)", page.evaluate(f"window.__app.S.selected === {want}")
              and page.evaluate(f"!!document.querySelector('#site-table tbody tr.sel[data-i=\"{want}\"]')"), page.evaluate(f"window.__app.S.cols.site_id[{want}]"))
        page.click("#sc-close")

    with WD.step("summary tab"):
        page.click('#tabs button[data-view="summary"]')
        page.wait_for_timeout(1200)
        nch = page.evaluate("Object.keys(window.__app.S.charts).length")
        check("Summary tab: charts render", nch >= 4, f"{nch} charts")
        check("Summary tab: five figures and HTML chart keys", page.evaluate("document.querySelectorAll('#tiles .stat').length === 5 && document.querySelectorAll('.ckey span').length >= 10"))
    with WD.step("sources tab"):
        page.click('#tabs button[data-view="sources"]')
        st = page.text_content("#sources-page")
        check("Sources and Limits tab: datasets, provisional note, SCOPE limits, appendix link",
              "Provisional data note" in st and "spare capacity" in st and "methodology review" in st.lower(), f"{len(st)} chars")
        check("reading tabs hide the controls column", not page.is_visible("#sidebar"))
    with WD.step("deliverables tab and links"):
        page.click('#tabs button[data-view="deliverables"]')
        dtxt = page.inner_text("#deliverables-page")
        check("Deliverables tab: Excel, memos, BLM brief", "Excel" in dtxt and "BLM application brief" in dtxt and "Site memos" in dtxt)
        hrefs = page.evaluate("[...document.querySelectorAll('#deliverables-page a')].map(a => a.href)")
        bad = []
        for h in hrefs:
            u = urllib.request.urljoin(V1URL, urllib.request.unquote(h.split("f=", 1)[1])) if "doc.html?f=" in h else h
            try:
                urllib.request.urlopen(u, timeout=5)
            except Exception as e:  # noqa: BLE001
                bad.append(f"{u}: {e}")
        check("every deliverable link resolves", not bad, f"{len(hrefs)} links" if not bad else "; ".join(bad[:3]))
    with WD.step("show on map from Deliverables"):
        page.click("#deliverables-page button[data-site]")
        page.wait_for_selector("#scorecard:not(.hidden)", timeout=8000)
        sid = page.get_attribute("#deliverables-page button[data-site]", "data-site")
        check("Show on map opens the map and the memo's site", page.evaluate("document.body.dataset.view") == "map" and sid in page.text_content("#scorecard"), sid)
        page.click("#sc-close")
    with WD.step("How to Read This tab"):
        page.click('#tabs button[data-view="guide"]')
        page.wait_for_selector("#view-guide.active", timeout=5000)
        check("How to Read This present (tab, page and table of contents)", page.is_visible("#guide-page") and page.evaluate("document.querySelectorAll('#guide-page .toc a').length") == 10)
        secs = page.evaluate("[...document.querySelectorAll('#guide-page .gsec')].map(s => s.dataset.section)")
        want = ["what", "ask", "good", "map", "use", "score", "prep", "limits", "next", "glossary"]
        check("How to Read This tab opens with all 10 sections", secs == want and page.is_visible("#guide-page"), ", ".join(secs))
        g = page.text_content("#guide-page")
        keys = ["500+ kV", "Near-black dots", "unknown", "Violet ring", "Darker blue", "BLM solar-available", "What to look for", "spare capacity",
                "not legal title", "pre-application", "Hard vs soft constraint", "GHI", "POI", "Export CSV", str(page.evaluate("window.__app.S.doc.sites.weights.solar.grid"))]
        miss = [k for k in keys if k not in g]
        check("How to Read This: answers big lines / crowded substations, legend, limits, next steps, glossary", not miss, "missing: " + ", ".join(miss) if miss else f"{len(g)} chars")
        old = [k for k in ["teal", "Purple ring", "Mustard", "Red dots", "orange outline", "Yellow:"] if k in g]
        check("How to Read This: colour words match the v2 map (no teal, purple, mustard, red dots)", not old, ", ".join(old) or "none")
        check("How to Read This: no em or en dashes", "\u2014" not in g and "\u2013" not in g)
        cols = page.evaluate("[...document.querySelectorAll('#g-map .sw')].map(e => getComputedStyle(e).backgroundColor)")
        check("How to Read This: legend swatches drawn from the map colours", len(cols) >= 15, f"{len(cols)} swatches")
    with WD.step("memo and appendix pages"):
        doc = ctx.new_page()
        doc.set_default_timeout(20000)
        doc.on("console", lambda m: errors.append(f"doc console {m.type}: {m.text}") if m.type == "error" else None)
        doc.goto(V1URL + "doc.html?f=" + urllib.request.quote("data/appendix/METHODOLOGY_REVIEW.md"))
        doc.wait_for_selector(".doc h1")
        check("methodology review appendix renders", "methodology review" in doc.inner_text(".doc h1").lower())
        memo = page.evaluate("window.__app.S.deliv.memos.find(m => m.site_id)")
        doc.goto(V1URL + "doc.html?f=" + urllib.request.quote(memo["href"]))
        doc.wait_for_selector(".doc h1")
        check("site memo renders", len(doc.inner_text(".doc")) > 300, memo["file"])
    with WD.step("close browser (session 2)"):
        browser.close()


def session_screens(p):
    """Session 3: screenshots at 1440 and 1280 px, plus a layout overlap check at each width."""
    browser, ctx, page = new_page(p)
    with WD.step("load page (session 3)"):
        load(page)
    for width, height in [(1440, 900), (1280, 800)]:
        with WD.step(f"layout {width}px"):
            page.set_viewport_size({"width": width, "height": height})
            page.click('#tabs button[data-view="map"]')
            page.click("#mode-solar")
            page.wait_for_timeout(800)
            ov = page.evaluate("""() => { const r = (s) => document.querySelector(s).getBoundingClientRect();
                const a = r('#sidebar'), m = r('#map'), h = r('header#top'), t = r('#table-wrap'), mode = r('.mode'), tabs = r('#tabs'), b = r('.brand');
                return { sidebarOverMap: a.right > m.left + 1, headerWrap: h.height > 57, tabsHitMode: tabs.right > mode.left, brandHitTabs: b.right > tabs.left,
                         tableUnderMap: t.top < m.bottom - 1, docScrollX: document.documentElement.scrollWidth > innerWidth,
                         statesWrap: document.querySelector('#state-filter').getBoundingClientRect().height > 30 }; }""")
            check(f"{width} px layout: no overlapping panels, nothing wraps", not any(ov.values()), json.dumps(ov))
        with WD.step(f"screenshot overview {width}"):
            page.evaluate("window.__app.homeView()")
            wait_idle(page)
            page.wait_for_timeout(1500)
            page.screenshot(path=str(SHOTS / f"01_overview_{width}.png"))
            check(f"screenshot overview {width}", (SHOTS / f"01_overview_{width}.png").stat().st_size > 50000)
        with WD.step(f"screenshot scorecard {width}"):
            page.evaluate("window.__app.selectSite(window.__app.S.order[0], false)")
            i = page.evaluate("window.__app.S.order[0]")
            page.wait_for_selector("#scorecard:not(.hidden)")
            page.wait_for_timeout(500)
            page.evaluate(f"void map.jumpTo({{center: [window.__app.S.cols.centroid_lon[{i}], window.__app.S.cols.centroid_lat[{i}]], zoom: 10}})")
            wait_idle(page)
            page.wait_for_timeout(1500)
            page.screenshot(path=str(SHOTS / f"02_scorecard_{width}.png"))
            check(f"screenshot scorecard open {width}", page.is_visible("#scorecard"))
        with WD.step(f"screenshot data center ranking {width}"):
            page.click("#sc-close")
            page.click("#mode-dc")
            page.wait_for_timeout(400)
            page.evaluate("window.__app.homeView()")
            page.wait_for_timeout(800)
            wait_idle(page)
            page.wait_for_timeout(1000)
            page.screenshot(path=str(SHOTS / f"03_dc_ranking_{width}.png"))
            check(f"screenshot data center ranking {width}", "Solar + Data Center" in page.inner_text("#table-title"))
            page.click("#mode-solar")
        with WD.step(f"screenshot summary {width}"):
            page.click('#tabs button[data-view="summary"]')
            page.evaluate("document.querySelector('#view-summary').scrollTop = 0")
            page.wait_for_timeout(1500)
            page.screenshot(path=str(SHOTS / f"04_summary_{width}.png"))
            page.evaluate("document.querySelector('#view-summary').scrollTop = 760")
            page.wait_for_timeout(400)
            page.screenshot(path=str(SHOTS / f"04b_summary_lower_{width}.png"))
            check(f"screenshot summary tab {width}", page.is_visible("#view-summary"))
        with WD.step(f"screenshot sources {width}"):
            page.click('#tabs button[data-view="sources"]')
            page.wait_for_timeout(600)
            page.screenshot(path=str(SHOTS / f"05_sources_{width}.png"))
            check(f"screenshot sources tab {width}", page.is_visible("#sources-page"))
        with WD.step(f"screenshot How to Read This {width}"):
            page.click('#tabs button[data-view="guide"]')
            page.evaluate("document.querySelector('#view-guide').scrollTop = 0")
            page.wait_for_timeout(400)
            page.screenshot(path=str(SHOTS / f"06_how_to_read_{width}.png"))
            page.evaluate("document.querySelector('#g-map').scrollIntoView({block: 'start'})")
            page.wait_for_timeout(400)
            page.screenshot(path=str(SHOTS / f"07_how_to_read_map_legend_{width}.png"))
            check(f"screenshot How to Read This tab {width}", page.is_visible("#guide-page") and (SHOTS / f"07_how_to_read_map_legend_{width}.png").exists())
        with WD.step(f"screenshot deliverables {width}"):
            page.click('#tabs button[data-view="deliverables"]')
            page.wait_for_timeout(500)
            page.screenshot(path=str(SHOTS / f"08_deliverables_{width}.png"))
            check(f"screenshot deliverables tab {width}", page.is_visible("#deliverables-page"))
            page.click('#tabs button[data-view="map"]')
    with WD.step("narrow layout 900 px"):
        page.set_viewport_size({"width": 900, "height": 800})
        page.wait_for_timeout(600)
        drawer_hidden = page.evaluate("document.querySelector('#sidebar').getBoundingClientRect().right <= 0")
        page.click("#rail-toggle")
        page.wait_for_timeout(500)
        opened = page.evaluate("document.querySelector('#sidebar').getBoundingClientRect().left >= 0")
        page.screenshot(path=str(SHOTS / "09_narrow_controls_900.png"))
        page.keyboard.press("Escape")
        fits = page.evaluate("document.querySelector('.mode').getBoundingClientRect().right <= innerWidth && document.querySelector('#tabs-menu').offsetWidth > 0")
        check("under 1100 px the controls become a drawer and the tabs a menu; masthead fits", drawer_hidden and opened and fits)
    with WD.step("close browser (session 3)"):
        browser.close()


if __name__ == "__main__":
    main()

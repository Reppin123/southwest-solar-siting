# /// script
# requires-python = ">=3.10"
# dependencies = ["playwright==1.48.0"]
# ///
"""Headless browser test of the dashboard (Playwright's bundled Chromium, software WebGL).

Run: uv run --script app/tests/test_app.py [--port 8771]
Starts its own app/serve.py on port 8771 (never touches the user's server on 8770), loads the page, toggles every
layer, clicks a site, moves a weight slider, switches Solar / Solar + Data Center, exports CSV, opens Summary,
Sources, Deliverables and How to Read This (all 10 sections), checks README and run_all, checks the layout at 1440 and 1280 px, and saves screenshots to app/screenshots/.
Fails on any console error or page error.

A watchdog thread prints a progress line every 15 s and aborts the run (exit 3) if any single step exceeds its
hard time limit (30 s by default; the first page load, which parses about 25 MB of site data under software
rendering, gets 150 s). Results go to app/tests/last_run.json and app/tests/RESULTS.md.
"""
import argparse
import csv
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

ROOT = Path(__file__).resolve().parents[2]
SHOTS = ROOT / "app" / "screenshots"
TESTS = ROOT / "app" / "tests"
ap = argparse.ArgumentParser()
ap.add_argument("--port", type=int, default=8771)
ARGS = ap.parse_args()
URL = f"http://localhost:{ARGS.port}/app/"
LAUNCH_ARGS = ["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"]
T_START = time.time()
TOTAL_LIMIT = 570

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
    (TESTS / "last_run.json").write_text(json.dumps(
        [{"check": a, "ok": b, "detail": c} for a, b, c in results], indent=1))
    n_fail = sum(1 for r in results if not r[1])
    lines = ["# Dashboard headless test results", "",
             f"Run: {time.strftime('%Y-%m-%d %H:%M:%S')} with `uv run --script app/tests/test_app.py` "
             f"(Playwright 1.48.0, bundled Chromium, headless, software WebGL; test server on port {ARGS.port}).",
             f"Total time {time.time() - T_START:.0f} s. Hard limit per step: 30 s (first page load: 150 s).", "",
             f"**{len(results) - n_fail} passed, {n_fail} failed{', ABORTED: ' + aborted if aborted else ''}**", "",
             "| # | Check | Result | Detail |", "|---|---|---|---|"]
    for k, (a, b, c) in enumerate(results, 1):
        lines.append(f"| {k} | {a} | {'PASS' if b else 'FAIL'} | {c.replace('|', '/')[:300]} |")
    shots = sorted(p.name for p in SHOTS.glob("*.png"))
    lines += ["", "Screenshots saved in app/screenshots/:", ""] + [f"- {s}" for s in shots]
    (TESTS / "RESULTS.md").write_text("\n".join(lines) + "\n")
    return n_fail


class Watchdog:
    def __init__(self):
        self.name, self.t0, self.limit = "startup", time.time(), 120
        self.last_print = time.time()
        threading.Thread(target=self.loop, daemon=True).start()

    @contextmanager
    def step(self, name, limit=30):
        self.name, self.t0, self.limit = name, time.time(), limit
        print(f"{stamp()} step: {name}", flush=True)
        self.last_print = time.time()
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
            if now - self.last_print >= 15:
                print(f"{stamp()} ... still running: {self.name} ({el:.0f} s of {self.limit} s)", flush=True)
                self.last_print = now
            if el > self.limit or now - T_START > TOTAL_LIMIT:
                why = f"step '{self.name}' exceeded {self.limit} s" if el > self.limit else "total time limit"
                print(f"{stamp()} ABORT: {why}", flush=True)
                check(self.name, False, f"timed out: {why}")
                write_results(aborted=why)
                stop_server()
                os._exit(3)


def stop_server():
    """Stop uv and the python child it spawned (same process group)."""
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
    page.wait_for_function("window.__appReady === true", timeout=140000)
    return time.time() - t0


def main():
    global SRV
    SHOTS.mkdir(exist_ok=True)
    for f in SHOTS.glob("*.png"):
        f.unlink()
    SRV = subprocess.Popen(["/opt/homebrew/bin/uv", "run", "--script", str(ROOT / "app/serve.py"), "--port", str(ARGS.port),
                            "--no-browser"], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           start_new_session=True)
    try:
        with WD.step("start test server", 60):
            for _ in range(100):
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
    with WD.step("project checks (README, run_all)", 120):
        rd = (ROOT / "README.md").read_text() if (ROOT / "README.md").exists() else ""
        check("README.md present (run, refresh, sources, limits, folder map)",
              all(k in rd for k in ["app/serve.py", "run_all.py", "## Data sources", "## Limits", "## Folder map", "8770"]))
        uv = "/opt/homebrew/bin/uv"
        h = subprocess.run([uv, "run", "--script", str(ROOT / "pipeline/run_all.py"), "--help"], cwd=ROOT,
                           capture_output=True, text=True, timeout=110, stdin=subprocess.DEVNULL)
        check("pipeline/run_all.py --help works", h.returncode == 0 and "--force" in h.stdout)
        d = subprocess.run([uv, "run", "--script", str(ROOT / "pipeline/run_all.py"), "--dry-run"], cwd=ROOT,
                           capture_output=True, text=True, timeout=110, stdin=subprocess.DEVNULL)
        nskip = d.stdout.count(" skipped ")
        check("run_all skips completed stages by default (--dry-run, no re-run)", d.returncode == 0 and nskip == 9,
              f"{nskip} of 9 stages skipped")
        check("serve.py default port 8770", "default=8770" in (ROOT / "app/serve.py").read_text())
    n_fail = write_results()
    print(f"\n{len(results) - n_fail} passed, {n_fail} failed", flush=True)
    sys.exit(1 if n_fail else 0)


def session_layers(p):
    """Session 1: load, data sanity, ranking parity, toggle every layer on and off."""
    browser, ctx, page = new_page(p)
    with WD.step("load page (first)", 150):
        dt = load(page)
        check("page loads with data", True, f"{dt:.1f} s")
        check("Map is the default view", page.evaluate("document.querySelector('#view-map').classList.contains('active') && document.querySelector('#tabs button.active').dataset.view === 'map'"))
    with WD.step("data covers five states"):
        n = page.evaluate("window.__app.S.n")
        states = page.evaluate("[...new Set(window.__app.S.cols.state)].sort()")
        check("sites from all five states", states == ["AZ", "CA", "NM", "NV", "UT"] and n > 1000, f"{n} sites, {states}")
        check("map libraries load locally (no CDN scripts)",
              page.evaluate("[...document.scripts].every(s => !s.src || s.src.startsWith(location.origin))"))
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
        with WD.step(f"toggle layer {lid}", 45):
            cb = page.locator(f'#layer-list input[data-layer="{lid}"]')
            was = cb.is_checked()
            if not was:
                cb.check()
            page.wait_for_function(f"""() => {{ const S = window.__app.S; return S.loaded['{lid}'] &&
                (S.mapLayers['{lid}'] || []).every(l => map.getLayoutProperty(l, 'visibility') === 'visible'); }}""",
                                   timeout=40000)
            nfeat = page.evaluate(f"""() => {{ const s = map.getSource('{lid}'); return s.type === 'image' ? 1 :
                (s._data && s._data.features ? s._data.features.length : -1); }}""")
            cb.uncheck()
            page.wait_for_function(f"(window.__app.S.mapLayers['{lid}'] || []).every(l => map.getLayoutProperty(l, 'visibility') === 'none')")
            if was:
                cb.check()
            check(f"layer on/off: {lid}", nfeat != 0, f"{nfeat} features" if nfeat >= 0 else "loaded")
    with WD.step("toggle candidate sites layer"):
        page.locator('#layer-list input[data-layer="sites"]').uncheck()
        hidden = page.evaluate("map.getLayoutProperty('sites-pt','visibility') === 'none'")
        page.locator('#layer-list input[data-layer="sites"]').check()
        check("layer on/off: candidate sites", hidden and page.evaluate("map.getLayoutProperty('sites-pt','visibility') === 'visible'"))
    with WD.step("close browser (session 1)", 30):
        browser.close()


def session_interactions(p):
    """Session 2: basemaps, site click and scorecard, weight slider, filters, mode switch, CSV, tabs, links."""
    browser, ctx, page = new_page(p)
    with WD.step("load page (session 2)", 150):
        load(page)
    for b in ["satellite", "terrain", "street"]:
        with WD.step(f"basemap {b}"):
            page.check(f'#basemap input[value="{b}"]')
            check(f"basemap switch: {b}", page.evaluate(f"map.getLayoutProperty('base-{b}','visibility') === 'visible'"))

    with WD.step("click top site on map", 45):
        top = page.evaluate("window.__app.S.order[0]")
        lon, lat, sid = page.evaluate(f"[window.__app.S.cols.centroid_lon[{top}], window.__app.S.cols.centroid_lat[{top}], window.__app.S.cols.site_id[{top}]]")
        page.evaluate(f"void map.jumpTo({{center: [{lon}, {lat}], zoom: 10.5}})")
        print(f"{stamp()}   jumped to {sid}", flush=True)
        wait_idle(page)
        print(f"{stamp()}   map idle", flush=True)
        pt = page.evaluate(f"""() => {{ const c = map.project([{lon}, {lat}]); const r = map.getContainer().getBoundingClientRect();
            for (let dx = 0; dx < 60; dx += 6) for (const s of [1, -1]) {{ const x = c.x + s * dx, y = c.y;
              const hit = map.queryRenderedFeatures([[x - 4, y - 4], [x + 4, y + 4]], {{layers: ['sites-fill']}});
              if (hit.some(f => f.layer.id === 'sites-fill' && f.properties.i === {top})) return [x + r.left, y + r.top]; }}
            return [c.x + r.left, c.y + r.top]; }}""")
        print(f"{stamp()}   clicking at {pt}", flush=True)
        page.mouse.click(pt[0], pt[1])
        page.wait_for_selector("#scorecard:not(.hidden)", timeout=10000)
        txt = page.text_content("#scorecard")  # raw text; inner_text applies CSS uppercase to section titles
        check("click site on map opens scorecard", sid in txt and "Score by factor" in txt and "Recommended next step" in txt, sid)
        check("scorecard shows substation, queue, GHI, BLM status, data center fit",
              all(k in txt for k in ["Nearest 115 kV+ substation", "Active queue in county", "GHI", "BLM status", "Data center fit"]))

    with WD.step("provisional badge"):
        prov = page.evaluate("window.__app.S.order.find(i => window.__app.S.cols.sub_provisional[i] === true)")
        if prov is None:
            check("provisional badge on scorecard", True, "no provisional site in data; not applicable")
        else:
            page.evaluate(f"window.__app.selectSite({prov}, false)")
            page.wait_for_timeout(600)
            t2 = page.inner_text("#scorecard")
            check("provisional badge on scorecard", "Provisional substation" in t2, page.evaluate(f"window.__app.S.cols.site_id[{prov}]"))

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
        check("BLM-only filter", allblm, page.inner_text("#filter-count"))
        page.uncheck("#f-blm")
        page.wait_for_timeout(500)

    with WD.step("switch Solar + Data Center"):
        page.click("#mode-dc")
        page.wait_for_timeout(700)
        dc_top = page.evaluate("window.__app.S.cols.site_id[window.__app.S.order[0]]")
        check("ranking switch to Solar + Data Center", page.evaluate("window.__app.S.mode === 'dc' && window.__app.S.weights.dc > 0")
              and "Solar + Data Center" in page.inner_text("#table-title"), f"top DC site {dc_top}")
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
        page.click("#site-table tbody tr:nth-child(2)")
        page.wait_for_timeout(1200)
        check("table row click selects site", page.evaluate("window.__app.S.selected === window.__app.S.viewRows[1]"))

    with WD.step("summary tab"):
        page.click('#tabs button[data-view="summary"]')
        page.wait_for_timeout(1200)
        nch = page.evaluate("Object.keys(window.__app.S.charts).length")
        check("Summary tab: charts render", nch >= 4, f"{nch} charts")
    with WD.step("sources tab"):
        page.click('#tabs button[data-view="sources"]')
        st = page.inner_text("#sources-page")
        check("Sources and Limits tab: datasets, provisional note, SCOPE limits, appendix link",
              "Provisional data note" in st and "spare capacity" in st and "methodology review" in st.lower(), f"{len(st)} chars")
    with WD.step("deliverables tab and links", 45):
        page.click('#tabs button[data-view="deliverables"]')
        dtxt = page.inner_text("#deliverables-page")
        check("Deliverables tab: Excel, memos, BLM brief", "Excel" in dtxt and "BLM application brief" in dtxt and "Site memos" in dtxt)
        hrefs = page.evaluate("[...document.querySelectorAll('#deliverables-page a')].map(a => a.getAttribute('href'))")
        bad = []
        for h in hrefs:
            u = urllib.request.unquote(h.split("f=", 1)[1] if "doc.html?f=" in h else h)
            try:
                urllib.request.urlopen(urllib.request.urljoin(URL, u), timeout=5)
            except Exception as e:  # noqa: BLE001
                bad.append(f"{u}: {e}")
        check("every deliverable link resolves", not bad, f"{len(hrefs)} links" if not bad else "; ".join(bad[:3]))
    with WD.step("How to Read This tab"):
        page.click('#tabs button[data-view="guide"]')
        page.wait_for_selector("#view-guide.active", timeout=5000)
        secs = page.evaluate("[...document.querySelectorAll('#guide-page .gsec')].map(s => s.dataset.section)")
        want = ["what", "ask", "good", "map", "use", "score", "prep", "limits", "next", "glossary"]
        check("How to Read This tab opens with all 10 sections", secs == want and page.is_visible("#guide-page"), ", ".join(secs))
        g = page.text_content("#guide-page")
        keys = ["500+ kV", "Red dots", "unknown", "Purple ring", "Darker teal", "BLM solar-available", "What to look for", "spare capacity",
                "not legal title", "pre-application", "Hard vs soft constraint", "GHI", "POI", "Export CSV", str(page.evaluate("window.__app.S.doc.sites.weights.solar.grid"))]
        miss = [k for k in keys if k not in g]
        check("How to Read This: answers red line / red dots, legend, limits, next steps, glossary", not miss, "missing: " + ", ".join(miss) if miss else f"{len(g)} chars")
        check("How to Read This: no em or en dashes", "\u2014" not in g and "\u2013" not in g)
        cols = page.evaluate("[...document.querySelectorAll('#g-map .sw')].map(e => getComputedStyle(e).backgroundColor)")
        check("How to Read This: legend swatches drawn from layers.json", len(cols) >= 15, f"{len(cols)} swatches")
    with WD.step("memo and appendix pages"):
        doc = ctx.new_page()
        doc.set_default_timeout(20000)
        doc.on("console", lambda m: errors.append(f"doc console {m.type}: {m.text}") if m.type == "error" else None)
        doc.goto(URL + "doc.html?f=" + urllib.request.quote("data/appendix/METHODOLOGY_REVIEW.md"))
        doc.wait_for_selector(".doc h1")
        check("methodology review appendix renders", "methodology review" in doc.inner_text(".doc h1").lower())
        memo = page.evaluate("window.__app.S.deliv.memos.find(m => m.site_id)")
        doc.goto(URL + "doc.html?f=" + urllib.request.quote(memo["href"]))
        doc.wait_for_selector(".doc h1")
        check("site memo renders", len(doc.inner_text(".doc")) > 300, memo["file"])
    with WD.step("close browser (session 2)", 30):
        browser.close()


def session_screens(p):
    """Session 3: screenshots at 1440 and 1280 px, plus a layout overlap check at each width."""
    browser, ctx, page = new_page(p)
    with WD.step("load page (session 3)", 150):
        load(page)
    for width, height in [(1440, 900), (1280, 800)]:
        with WD.step(f"layout {width}px"):
            page.set_viewport_size({"width": width, "height": height})
            page.click('#tabs button[data-view="map"]')
            page.click("#mode-solar")
            page.wait_for_timeout(800)
            ov = page.evaluate("""() => { const r = (s) => document.querySelector(s).getBoundingClientRect();
                const a = r('#sidebar'), m = r('#map'), h = r('header#top'), t = r('#table-wrap'), mode = r('.mode'), tabs = r('#tabs');
                return { sidebarOverMap: a.right > m.left + 1, headerWrap: h.height > 60, tabsHitMode: tabs.right > mode.left,
                         tableUnderMap: t.top < m.bottom - 1, docScrollX: document.documentElement.scrollWidth > innerWidth }; }""")
            check(f"{width} px layout: no overlapping panels", not any(ov.values()), json.dumps(ov))
        with WD.step(f"screenshot overview {width}"):
            page.evaluate(f"void map.jumpTo({{center: [-112.5, 36.2], zoom: {4.9 if width == 1440 else 4.7}}})")
            wait_idle(page)
            page.screenshot(path=str(SHOTS / f"01_overview_{width}.png"))
            check(f"screenshot overview {width}", (SHOTS / f"01_overview_{width}.png").stat().st_size > 50000)
        with WD.step(f"screenshot scorecard {width}"):
            page.evaluate("window.__app.selectSite(window.__app.S.order[0], false)")
            i = page.evaluate("window.__app.S.order[0]")
            page.evaluate(f"void map.jumpTo({{center: [window.__app.S.cols.centroid_lon[{i}], window.__app.S.cols.centroid_lat[{i}]], zoom: 10}})")
            page.wait_for_selector("#scorecard:not(.hidden)")
            wait_idle(page)
            page.screenshot(path=str(SHOTS / f"02_scorecard_{width}.png"))
            check(f"screenshot scorecard open {width}", page.is_visible("#scorecard"))
        with WD.step(f"screenshot data center ranking {width}"):
            page.click("#sc-close")
            page.click("#mode-dc")
            page.evaluate(f"void map.jumpTo({{center: [-112.5, 36.2], zoom: {4.9 if width == 1440 else 4.7}}})")
            page.wait_for_timeout(800)
            wait_idle(page)
            page.screenshot(path=str(SHOTS / f"03_dc_ranking_{width}.png"))
            check(f"screenshot data center ranking {width}", "Solar + Data Center" in page.inner_text("#table-title"))
            page.click("#mode-solar")
        with WD.step(f"screenshot summary {width}"):
            page.click('#tabs button[data-view="summary"]')
            page.wait_for_timeout(1500)
            page.screenshot(path=str(SHOTS / f"04_summary_{width}.png"), full_page=True)
            check(f"screenshot summary tab {width}", page.is_visible("#view-summary") if page.query_selector("#view-summary") else True)
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
            check(f"screenshot How to Read This tab {width}", page.is_visible("#guide-page")
                  and (SHOTS / f"07_how_to_read_map_legend_{width}.png").exists())
            page.click('#tabs button[data-view="map"]')
    with WD.step("close browser (session 3)", 30):
        browser.close()


if __name__ == "__main__":
    main()

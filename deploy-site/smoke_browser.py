# /// script
# requires-python = ">=3.10"
# dependencies = ["playwright==1.48.0"]
# ///
"""Browser smoke test of the live site at 1440x900 (called by deploy-site/smoke.sh).

Checks: landing page renders with its links; v2 map loads all sites and draws them; v2 scorecard opens for the
top site; v2 "How to Read This" opens from #guide; v1 map loads its data. Fails on any console error or page error.
Screenshots go to deploy-site/*.png, results to deploy-site/smoke_result.json.
Run: /opt/homebrew/bin/uv run --script deploy-site/smoke_browser.py https://<worker>.workers.dev
"""
import json
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
URL = (sys.argv[1] if len(sys.argv) > 1 else (HERE / "URL").read_text().strip()).rstrip("/")
ARGS = ["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"]
results, errors = [], []


def check(name, ok, detail=""):
    results.append({"check": name, "ok": bool(ok), "detail": str(detail)})
    print(f"{'ok  ' if ok else 'FAIL'} {name}{'  (' + str(detail) + ')' if detail else ''}", flush=True)


def wait_idle(page):
    page.wait_for_function("""() => new Promise(r => { if (typeof map === 'undefined' || !map || !map.loaded) return r(false);
        if (map.loaded() && !map.isMoving()) return r(true); map.once('idle', () => r(true)); setTimeout(() => r(false), 4000); })""",
                           timeout=45000)


def page_for(browser, label):
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    pg = ctx.new_page()
    pg.set_default_timeout(45000)
    pg.on("console", lambda m: errors.append(f"[{label}] console {m.type}: {m.text}") if m.type == "error" else None)
    pg.on("pageerror", lambda e: errors.append(f"[{label}] pageerror: {e}"))
    pg.on("response", lambda r: errors.append(f"[{label}] HTTP {r.status} {r.url}") if r.status >= 400 and r.url.startswith(URL) else None)
    return ctx, pg


with sync_playwright() as p:
    b = p.chromium.launch(headless=True, args=ARGS)

    # Landing
    ctx, pg = page_for(b, "landing")
    try:
        r = pg.goto(URL + "/")
        pg.evaluate("document.fonts.ready")
        title = pg.inner_text("h1")
        links = pg.evaluate("[...document.querySelectorAll('a')].map(a => a.getAttribute('href'))")
        check("landing 200 with title", r.status == 200 and "Siting" in title, title)
        check("landing links to v2, v1, How to Read, Excel, memos, review",
              all(any(l and l.startswith(x) for l in links) for x in ["app-v2/", "app/", "app-v2/#guide", "deliverables/Southwest_Solar_Sites.xlsx", "app/doc.html?f=..%2Fdeliverables%2Fsite_memos", "app/doc.html?f=data%2Fappendix"])
              or all(any(l and l.startswith(x) for l in links) for x in ["app-v2/", "app/", "app-v2/#guide", "deliverables/Southwest_Solar_Sites.xlsx", "app/doc.html?f=../deliverables/site_memos", "app/doc.html?f=data/appendix"]),
              f"{len(links)} links")
        pg.screenshot(path=str(HERE / "01_landing_1440.png"), full_page=True)
        # A memo rendered through the markdown viewer
        memo = next(l for l in links if "site_memos/01_" in (l or "") and l.startswith("app/doc.html"))
        pg.goto(URL + "/" + memo)
        pg.wait_for_function("document.querySelector('#doc h1')", timeout=20000)
        check("site memo renders as HTML", "SW-NM-00001" in pg.inner_text("#doc"), memo)
        pg.screenshot(path=str(HERE / "04_memo_1440.png"))
    except Exception as e:  # noqa: BLE001
        check("landing", False, e)
    ctx.close()

    # Dashboard v2: map and scorecard
    ctx, pg = page_for(b, "v2")
    try:
        t0 = time.time()
        pg.goto(URL + "/app-v2/")
        pg.wait_for_function("window.__appReady === true", timeout=60000)
        n = pg.evaluate("window.__app.S.n")
        states = pg.evaluate("[...new Set(window.__app.S.cols.state)].sort()")
        check("v2 map loads all sites", n > 20000 and states == ["AZ", "CA", "NM", "NV", "UT"], f"{n} sites, {states}, {time.time() - t0:.1f} s")
        wait_idle(pg)
        drawn = pg.evaluate("map.queryRenderedFeatures().filter(f => f.source === 'sites' || f.source === 'sites-pts').length")
        check("v2 map draws candidate sites", drawn > 0, f"{drawn} rendered features")
        rows = pg.evaluate("document.querySelectorAll('#site-table tbody tr').length")
        check("v2 ranked table filled", rows > 0, f"{rows} rows")
        pg.wait_for_timeout(1500)
        pg.screenshot(path=str(HERE / "02_v2_map_1440.png"))
        top = pg.evaluate("window.__app.S.order[0]")
        sid = pg.evaluate(f"window.__app.S.cols.site_id[{top}]")
        pg.evaluate(f"window.__app.selectSite({top}, true)")
        pg.wait_for_selector("#scorecard:not(.hidden)", timeout=15000)
        wait_idle(pg)
        pg.wait_for_timeout(1500)
        sc = pg.inner_text("#scorecard")
        check("v2 scorecard opens for the top site", sid in sc, sid)
        pg.screenshot(path=str(HERE / "03_v2_scorecard_1440.png"))
    except Exception as e:  # noqa: BLE001
        check("v2 dashboard", False, e)
    ctx.close()

    # Dashboard v2: How to Read This via #guide
    ctx, pg = page_for(b, "v2-guide")
    try:
        pg.goto(URL + "/app-v2/#guide")
        pg.wait_for_function("window.__appReady === true", timeout=60000)
        pg.wait_for_function("document.querySelector('button[data-view=\"guide\"]').getAttribute('aria-selected') === 'true'", timeout=15000)
        check("v2 #guide opens How to Read This", True)
        pg.screenshot(path=str(HERE / "05_v2_guide_1440.png"))
    except Exception as e:  # noqa: BLE001
        check("v2 #guide opens How to Read This", False, e)
    ctx.close()

    # Dashboard v1
    ctx, pg = page_for(b, "v1")
    try:
        pg.goto(URL + "/app/")
        pg.wait_for_function("window.__appReady === true", timeout=60000)
        n = pg.evaluate("window.__app.S.n")
        check("v1 map loads all sites", n > 20000, f"{n} sites")
        wait_idle(pg)
        pg.wait_for_timeout(1500)
        pg.screenshot(path=str(HERE / "06_v1_map_1440.png"))
    except Exception as e:  # noqa: BLE001
        check("v1 dashboard", False, e)
    ctx.close()
    b.close()

check("no console errors, page errors or failed requests", not errors, "; ".join(errors[:6]) or "none")
(HERE / "smoke_result.json").write_text(json.dumps({"url": URL, "when": time.strftime("%Y-%m-%d %H:%M %Z"), "checks": results, "errors": errors}, indent=1))
sys.exit(0 if all(r["ok"] for r in results) else 1)

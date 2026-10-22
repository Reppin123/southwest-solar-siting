# /// script
# requires-python = ">=3.10"
# dependencies = ["playwright==1.48.0"]
# ///
"""Dev helper: render app-v2 views from the running project server and save quick screenshots to tests/_dev/."""
import sys, time
from pathlib import Path
from playwright.sync_api import sync_playwright
OUT = Path(__file__).resolve().parent / "_dev"
URL = "http://localhost:8770/app-v2/"
w = int(sys.argv[1]) if len(sys.argv) > 1 else 1440
h = 900 if w >= 1440 else 800
what = sys.argv[2:] or ["map"]
errs = []
with sync_playwright() as p:
    b = p.chromium.launch(headless=True, args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])
    pg = b.new_page(viewport={"width": w, "height": h})
    pg.on("console", lambda m: errs.append(m.text[:200]) if m.type == "error" else None)
    pg.on("pageerror", lambda e: errs.append(str(e)[:200]))
    t = time.time(); pg.goto(URL); pg.wait_for_function("window.__appReady === true", timeout=120000)
    print(f"ready {time.time()-t:.1f}s")
    pg.wait_for_timeout(2500)
    for v in what:
        if v == "map":
            pg.screenshot(path=str(OUT / f"map_{w}.png"))
        elif v == "sc":
            pg.evaluate("(() => { const i = window.__app.S.order[0]; window.__app.selectSite(i, false); map.jumpTo({center:[window.__app.S.cols.centroid_lon[i], window.__app.S.cols.centroid_lat[i]], zoom: 10}); })()")
            pg.wait_for_timeout(3000); pg.screenshot(path=str(OUT / f"sc_{w}.png"))
            pg.evaluate("document.querySelector('#scorecard').scrollTop = 700"); pg.wait_for_timeout(300)
            pg.screenshot(path=str(OUT / f"sc2_{w}.png"))
        elif v == "layers":
            for lid in ["power_plants", "ownership", "excl_nca_acec", "water_stress", "solar_energy_zones", "data_centers_osm", "fiber"]:
                pg.locator(f'#layer-list input[data-layer="{lid}"]').check()
            pg.wait_for_timeout(5000); pg.screenshot(path=str(OUT / f"layers_{w}.png"))
            pg.evaluate("document.querySelector('#sidebar').scrollTop = 2000"); pg.wait_for_timeout(200)
            pg.screenshot(path=str(OUT / f"layers2_{w}.png"))
        else:
            pg.click(f'#tabs button[data-view="{v}"]'); pg.wait_for_timeout(1500)
            pg.screenshot(path=str(OUT / f"{v}_{w}.png"), full_page=False)
            if v == "summary":
                pg.evaluate("document.querySelector('#view-summary').scrollTop = 900"); pg.wait_for_timeout(300); pg.screenshot(path=str(OUT / f"summary2_{w}.png"))
            if v == "guide":
                pg.evaluate("document.querySelector('#g-map').scrollIntoView()"); pg.wait_for_timeout(400)
                pg.screenshot(path=str(OUT / f"guide2_{w}.png"))
            pg.click('#tabs button[data-view="map"]')
    em = pg.evaluate("document.body.innerText.includes('\\u2014')")
    print("em dash:", em, "errors:", errs[:5])
    b.close()

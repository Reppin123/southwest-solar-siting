# /// script
# requires-python = ">=3.10"
# dependencies = ["playwright==1.48.0"]
# ///
"""Serve design/ on port 4100 for the duration of the run, screenshot specimen.html, report fonts and console errors."""
import subprocess, sys, time
from pathlib import Path
from playwright.sync_api import sync_playwright
D = Path(__file__).resolve().parents[1]
srv = subprocess.Popen([sys.executable, "-m", "http.server", "4100", "--bind", "127.0.0.1"], cwd=D, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    time.sleep(1)
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1440, "height": 900})
        errs = []
        pg.on("console", lambda m: m.type == "error" and errs.append(m.text))
        pg.on("requestfailed", lambda r: errs.append("failed " + r.url))
        pg.goto("http://127.0.0.1:4100/specimen.html", wait_until="networkidle")
        pg.evaluate("document.fonts.ready")
        print("fonts:", pg.evaluate("[...document.fonts].filter(f=>f.status==='loaded').map(f=>f.family+' '+f.weight+' '+f.style)"))
        print("em dashes in page:", pg.evaluate("document.body.innerText.includes('—')"))
        pg.screenshot(path=str(D / "specimen-1440.jpg"), type="jpeg", quality=75, full_page=True)
        top = pg.locator(".fig").nth(2)
        top.screenshot(path=str(D / "specimen-mapview-1440.jpg"), type="jpeg", quality=80)
        print("errors:", errs)
        b.close()
finally:
    srv.terminate(); srv.wait()

# /// script
# requires-python = ">=3.10"
# dependencies = ["playwright==1.48.0"]
# ///
"""Capture v1 (http://localhost:8770/app/, read-only) as JPEG evidence into design/v1/."""
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parents[1] / "v1"
URL = "http://localhost:8770/app/"
with sync_playwright() as p:
    b = p.chromium.launch(args=["--enable-gpu", "--use-angle=metal", "--ignore-gpu-blocklist"])
    pg = b.new_page(viewport={"width": 1440, "height": 900})
    pg.goto(URL, wait_until="load", timeout=120000)
    pg.wait_for_function("!document.querySelector('#loading') || document.querySelector('#loading').classList.contains('hidden') || getComputedStyle(document.querySelector('#loading')).display==='none'", timeout=150000)
    pg.wait_for_timeout(4000)
    shot = lambda n: pg.screenshot(path=str(OUT / f"{n}.jpg"), type="jpeg", quality=72)
    shot("v1-01-map-1440")
    pg.evaluate("document.querySelector('#sidebar').scrollTop = 900"); pg.wait_for_timeout(500); shot("v1-02-layer-list-1440")
    pg.evaluate("document.querySelector('#sidebar').scrollTop = 1900"); pg.wait_for_timeout(500); shot("v1-03-layer-list-lower-1440")
    pg.evaluate("document.querySelector('#sidebar').scrollTop = 0")
    info = pg.locator("button.info").first
    if info.count():
        info.click(); pg.wait_for_timeout(600); shot("v1-04-info-modal-1440"); pg.click("#modal-close")
    pg.locator("#site-table tbody tr").first.click(); pg.wait_for_timeout(3500); shot("v1-05-scorecard-1440")
    pg.evaluate("document.querySelector('#scorecard').scrollTop = 600"); pg.wait_for_timeout(400); shot("v1-06-scorecard-lower-1440")
    pg.click("#tabs button[data-view=deliverables]"); pg.wait_for_timeout(800); shot("v1-07-deliverables-1440")
    pg.click("#tabs button[data-view=guide]"); pg.wait_for_timeout(800)
    pg.evaluate("document.querySelector('#view-guide').scrollTop = 1500"); pg.wait_for_timeout(400); shot("v1-08-guide-map-key-1440")
    pg.click("#tabs button[data-view=summary]"); pg.wait_for_timeout(1500); shot("v1-09-summary-1440")
    pg.set_viewport_size({"width": 1280, "height": 800}); pg.click("#tabs button[data-view=map]"); pg.wait_for_timeout(2500); shot("v1-10-map-1280")
    b.close()
print("done")

# /// script
# requires-python = ">=3.10"
# dependencies = ["playwright==1.48.0"]
# ///
"""Capture reference sites as JPEG (1440x900 viewport, quality 70) into design/refs/.
Run: uv run --script design/tools/shoot.py name=url [name=url ...]"""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parents[1] / "refs"
jobs = [a.split("=", 1) for a in sys.argv[1:]]
with sync_playwright() as p:
    b = p.chromium.launch(args=["--enable-gpu", "--use-angle=metal", "--ignore-gpu-blocklist", "--enable-webgl"])
    ctx = b.new_context(viewport={"width": 1440, "height": 900}, user_agent=(
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36"))
    for name, url in jobs:
        pg = ctx.new_page()
        try:
            pg.goto(url, wait_until="domcontentloaded", timeout=45000)
            pg.wait_for_timeout(9000)
            for label in ["Reject optional cookies", "Reject non-essential cookies", "Reject all", "Reject", "No, thanks",
                          "Accept All", "Accept all", "Accept", "I agree", "Got it", "OK"]:
                try:
                    btn = pg.get_by_role("button", name=label, exact=True)
                    if btn.count() and btn.first.is_visible():
                        btn.first.click(timeout=2000); pg.wait_for_timeout(800); break
                except Exception:
                    pass
            pg.wait_for_timeout(2500)
            pg.screenshot(path=str(OUT / f"{name}.jpg"), type="jpeg", quality=70)
            print("ok", name, pg.title())
        except Exception as e:
            print("FAIL", name, url, str(e)[:120])
        pg.close()
    b.close()

# /// script
# requires-python = ">=3.10"
# dependencies = ["pillow"]
# ///
"""Side-by-side v1 and v2 images for the overview and the open scorecard at 1440 px.

v1 images are v1's own screenshots in ../app/screenshots/ (read only); v2 images come from tests/test_v2.py.
Run: uv run --script app-v2/tests/compare.py
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

V2 = Path(__file__).resolve().parents[1]
V1SHOTS = V2.parent / "app" / "screenshots"
FONT = V2 / "fonts"


def font(size):
    for f in ["/System/Library/Fonts/Supplemental/Arial.ttf", "/System/Library/Fonts/Helvetica.ttc"]:
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            continue
    return ImageFont.load_default()


for name, title in [("01_overview", "Overview"), ("02_scorecard", "Scorecard open")]:
    for w in (1440, 1280):
        a = Image.open(V1SHOTS / f"{name}_{w}.png").convert("RGB")
        b = Image.open(V2 / "screenshots" / f"{name}_{w}.png").convert("RGB")
        h = max(a.height, b.height)
        gap, head = 24, 56
        out = Image.new("RGB", (a.width + b.width + gap, h + head), "white")
        d = ImageDraw.Draw(out)
        d.text((0, 16), f"v1 (app/): {title}, {w} px", fill=(22, 24, 27), font=font(22))
        d.text((a.width + gap, 16), f"v2 (app-v2/): {title}, {w} px", fill=(22, 24, 27), font=font(22))
        out.paste(a, (0, head))
        out.paste(b, (a.width + gap, head))
        d.line([(a.width + gap // 2, head), (a.width + gap // 2, h + head)], fill=(201, 198, 190), width=1)
        p = V2 / "screenshots" / f"compare_{name}_{w}.png"
        out.save(p, optimize=True)
        print("saved", p.name, out.size)

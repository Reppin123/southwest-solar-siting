# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Assemble site-build/, the static site deployed to Cloudflare (Workers static assets).

Run: /opt/homebrew/bin/uv run --script scripts/build_site.py
Then deploy: scripts/deploy_site.sh (build + wrangler deploy + smoke test).

Layout of site-build/ mirrors the project so every relative link in the apps keeps working:
  index.html                      landing page (written here)
  app/                            dashboard v1 with app/data/ (v2 reads ../app/data/)
  app-v2/                         dashboard v2 (recommended)
  app-v3/                         only if app-v3/index.html exists and its last test run passed
  deliverables/                   Excel, BLM brief, sources, site memos (apps link ../deliverables/...)
  data/processed/sites/METHOD.md  scoring method (linked from the Deliverables tab)
  media/                          explainer video, only if video/out/southwest-solar-explainer.mp4 exists
  _headers                        cache headers for data, fonts, deliverables
  build-info.json                 file count, total size, largest files, what was included

Source folders are only read, never written. Cloudflare limits: 25 MiB per file, 20,000 files.
Oversized JSON/GeoJSON is minified in the deployed copy; anything still over the limit stops the build.
"""
import html
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "site-build"
MAX_FILE = 25 * 1024 * 1024
MAX_FILES = 20000
VIDEO = ROOT / "video" / "out" / "southwest-solar-explainer.mp4"

# Development-only material that is not part of the dashboards.
SKIP_DIRS = {"tests", "screenshots", "TEAM", "__pycache__", "node_modules", "_dev"}
SKIP_FILES = {"serve.py", ".DS_Store"}
SKIP_V2_DESIGN = {"refs", "v1", "tools"}  # design evidence, not loaded by the app

# Small shim added to the deployed index.html of each dashboard only: opens a tab from the URL hash,
# so the landing page can link straight to "How to Read This" (#guide) and other tabs.
TAB_SHIM = """<script>
(function () {
  var v = (location.hash || "").slice(1);
  if (!/^(map|summary|sources|deliverables|guide)$/.test(v)) return;
  var n = 0, t = setInterval(function () {
    var b = document.querySelector('button[data-view="' + v + '"]');
    if ((window.__appReady && b) || ++n > 300) { clearInterval(t); if (b) b.click(); }
  }, 100);
})();
</script>
"""


def ignore(src_root: Path):
    def _ignore(d, names):
        rel = Path(d).relative_to(src_root)
        out = [n for n in names if n in SKIP_DIRS or n in SKIP_FILES or n.endswith(".pyc")]
        if src_root.name == "app-v2" and rel == Path("design"):
            out += [n for n in names if n in SKIP_V2_DESIGN]
        return out
    return _ignore


def copy_app(name: str) -> None:
    src = ROOT / name
    shutil.copytree(src, OUT / name, ignore=ignore(src))
    idx = OUT / name / "index.html"
    if idx.exists():
        t = idx.read_text(encoding="utf-8")
        if "</body>" in t and TAB_SHIM not in t:
            idx.write_text(t.replace("</body>", TAB_SHIM + "</body>", 1), encoding="utf-8")


def v3_ready() -> tuple[bool, str]:
    v3 = ROOT / "app-v3"
    if not (v3 / "index.html").exists():
        return False, "app-v3/index.html not found"
    res = v3 / "tests" / "last_run.json"
    if not res.exists():
        return False, "app-v3/tests/last_run.json not found (tests not run)"
    try:
        checks = json.loads(res.read_text())
        rows = checks if isinstance(checks, list) else checks.get("checks", [])
        failed = [c for c in rows if not c.get("ok")]
    except Exception as e:  # noqa: BLE001
        return False, f"cannot read app-v3 test results: {e}"
    if not rows or failed:
        return False, f"app-v3 tests: {len(failed)} failing of {len(rows)}"
    return True, f"app-v3 tests: {len(rows)} checks passed"


def compact_json(p: Path) -> None:
    """Minify JSON/GeoJSON and round coordinates to 5 decimals (about 1 m). Deployed copy only."""
    def rnd(o):
        if isinstance(o, float):
            return round(o, 5)
        if isinstance(o, list):
            return [rnd(x) for x in o]
        if isinstance(o, dict):
            return {k: rnd(v) for k, v in o.items()}
        return o
    data = rnd(json.loads(p.read_text(encoding="utf-8")))
    p.write_text(json.dumps(data, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")


def fmt_mb(n: int) -> str:
    return f"{n / 1024 / 1024:.1f} MB"


def landing(memos: list, review: dict | None, has_v3: bool, has_video: bool, n_sites: int, generated: str) -> str:
    e = html.escape
    doc = lambda f: "app/doc.html?f=" + e(f, quote=True)  # noqa: E731
    xlsx = ROOT / "deliverables" / "Southwest_Solar_Sites.xlsx"
    memo_rows = "\n".join(
        f'<li><a href="{doc(m["href"])}">{e(m["title"])}</a> <a class="raw" href="{e(m["href"].replace("../", ""))}" download>.md</a></li>'
        for m in memos if m.get("site_id"))
    v3 = ('<li><a href="app-v3/"><span class="t">Dashboard v3</span></a><span class="d">Newest version.</span></li>'
          if has_v3 else "")
    video = ('<section><h2>Explainer video</h2><video controls preload="metadata" playsinline src="media/southwest-solar-explainer.mp4"></video>'
             '<p class="note"><a href="media/southwest-solar-explainer.mp4" download>Download the video (MP4)</a></p></section>'
             if has_video else "")
    review_li = (f'<li><a href="{doc("data/appendix/" + Path(review["href"]).name)}">{e(review["title"])}</a></li>'
                 if review else "")
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Southwest Solar and Data Center Siting</title>
<meta name="description" content="Screening map of {n_sites:,} candidate solar and data center sites in CA, AZ, NV, NM and UT, built from public grid, land and BLM data.">
<link rel="icon" href="data:,">
<link rel="preload" as="font" type="font/woff2" crossorigin href="app-v2/fonts/source-serif-4-latin-wght-normal.woff2">
<style>
@font-face {{ font-family: "IBM Plex Sans"; font-weight: 400; font-display: swap; src: url("app-v2/fonts/ibm-plex-sans-latin-400-normal.woff2") format("woff2"); }}
@font-face {{ font-family: "IBM Plex Sans"; font-weight: 600; font-display: swap; src: url("app-v2/fonts/ibm-plex-sans-latin-600-normal.woff2") format("woff2"); }}
@font-face {{ font-family: "Source Serif 4"; font-weight: 200 900; font-display: swap; src: url("app-v2/fonts/source-serif-4-latin-wght-normal.woff2") format("woff2"); }}
:root {{ --paper:#FFFFFF; --sunk:#F4F3EF; --ink:#16181B; --ink-2:#3E434A; --muted:#666B73; --rule:#E3E1DB; --rule-strong:#C9C6BE; --accent:#1F5370;
  --sans:"IBM Plex Sans","Helvetica Neue",Arial,sans-serif; --serif:"Source Serif 4",Georgia,"Times New Roman",serif; }}
* {{ box-sizing: border-box; }}
body {{ margin:0; background:var(--paper); color:var(--ink); font:400 17px/1.6 var(--serif); }}
main {{ max-width: 68ch; margin: 0 auto; padding: 64px 24px 48px; }}
.kicker {{ font:600 11px/1.4 var(--sans); letter-spacing:.06em; text-transform:uppercase; color:var(--muted); margin:0 0 12px; }}
h1 {{ font:600 40px/1.15 var(--serif); margin:0 0 24px; }}
h2 {{ font:600 11px/1.4 var(--sans); letter-spacing:.06em; text-transform:uppercase; color:var(--muted); margin:0 0 12px; padding-top:16px; border-top:1px solid var(--rule-strong); }}
section {{ margin-top: 48px; }}
a {{ color: var(--accent); text-underline-offset: 3px; text-decoration-thickness: 1px; }}
ul {{ list-style:none; padding:0; margin:0; }}
.apps li {{ padding:12px 0; border-bottom:1px solid var(--rule); display:flex; gap:16px; align-items:baseline; flex-wrap:wrap; }}
.apps .t {{ font:600 20px/1.3 var(--serif); }}
.apps .d, .note, .raw {{ font:400 13px/1.4 var(--sans); color:var(--muted); }}
.files li {{ padding:8px 0; border-bottom:1px solid var(--rule); font:400 15px/1.45 var(--sans); }}
.raw {{ margin-left: 8px; }}
.tag {{ font:600 11px/1 var(--sans); letter-spacing:.06em; text-transform:uppercase; color:var(--accent); border:1px solid var(--accent); border-radius:2px; padding:3px 5px; }}
video {{ width:100%; border:1px solid var(--rule); background:#000; }}
footer {{ margin-top:64px; padding-top:16px; border-top:1px solid var(--rule); font:400 12px/1.5 var(--sans); color:var(--muted); }}
@media (max-width: 600px) {{ main {{ padding-top: 32px; }} h1 {{ font-size: 28px; }} }}
</style>
</head>
<body>
<main>
<p class="kicker">Screening study from public data</p>
<h1>Southwest Solar and Data Center Siting</h1>
<p>Where in California, Arizona, Nevada, New Mexico and Utah is there land suited to a 100 MW to 1 GW solar project, close to a substation that can take the power, and where could a 50 to 500 MW data center sit next to it? This project pulls public grid, interconnection queue, land ownership, BLM solar, environmental and infrastructure data, screens {n_sites:,} candidate sites, scores each on grid, land, sun, permitting and data center fit, and shows the results on an interactive map with a scorecard for every site. It is a first-pass screen, not engineering: confirm grid capacity, title and constraints before acting on any site.</p>

<section>
<h2>Dashboards</h2>
<ul class="apps">
{v3}
<li><a href="app-v2/"><span class="t">Dashboard v2</span></a> <span class="tag">Recommended</span><span class="d">Map, ranked table, scorecards, weight sliders, summary charts, sources.</span></li>
<li><a href="app/"><span class="t">Dashboard v1</span></a><span class="d">First version. Same data and features.</span></li>
<li><a href="app-v2/#guide"><span class="t">How to Read This</span></a><span class="d">Plain-English guide to the colours, controls, scores and limits.</span></li>
</ul>
<p class="note">Best on a laptop or desktop. The map loads about 25 MB of data on first open.</p>
</section>

{video}

<section>
<h2>Deliverables</h2>
<ul class="files">
<li><a href="deliverables/Southwest_Solar_Sites.xlsx" download>Ranked site table (Excel, {fmt_mb(xlsx.stat().st_size)})</a></li>
<li><a href="{doc('../deliverables/BLM_Application_Brief.md')}">BLM application brief</a> <a class="raw" href="deliverables/BLM_Application_Brief.md" download>.md</a></li>
<li><a href="{doc('../deliverables/sources_blm.md')}">BLM brief sources</a> <a class="raw" href="deliverables/sources_blm.md" download>.md</a></li>
<li><a href="{doc('../data/processed/sites/METHOD.md')}">Screening and scoring method</a> <a class="raw" href="data/processed/sites/METHOD.md" download>.md</a></li>
<li><a href="{doc('../deliverables/site_memos/README.md')}">Site memos: overview table</a></li>
</ul>
</section>

<section>
<h2>Site memos</h2>
<ul class="files">
{memo_rows}
</ul>
</section>

<section>
<h2>Independent review</h2>
<ul class="files">
{review_li}
</ul>
<p class="note">A second model reviewed the data and method. Its blocking and important findings drove the two rankings, the provisional flags and the queue confidence shown in the dashboards.</p>
</section>

<footer>Data built {e(generated)}. Sources, dates and caveats for every layer are in the dashboard's Sources and Limits tab. Basemaps: OpenStreetMap contributors, Esri World Imagery, OpenTopoMap.</footer>
</main>
</body>
</html>
"""


def main() -> int:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    included = ["index.html", "app/", "app-v2/", "deliverables/", "data/processed/sites/METHOD.md"]

    copy_app("app")
    copy_app("app-v2")
    has_v3, v3_note = v3_ready()
    if has_v3:
        copy_app("app-v3")
        included.append("app-v3/")
    shutil.copytree(ROOT / "deliverables", OUT / "deliverables", ignore=ignore(ROOT / "deliverables"))
    (OUT / "data/processed/sites").mkdir(parents=True)
    shutil.copy2(ROOT / "data/processed/sites/METHOD.md", OUT / "data/processed/sites/METHOD.md")
    has_video = VIDEO.exists()
    if has_video:
        (OUT / "media").mkdir()
        shutil.copy2(VIDEO, OUT / "media" / VIDEO.name)
        included.append("media/" + VIDEO.name)

    # Every ../ link the dashboards' data files point at must exist in the build.
    missing = []
    for jf in (OUT / "app/data").glob("*.json"):
        for s in json.dumps(json.loads(jf.read_text())).split('"'):
            if s.startswith("../") and not (OUT / "app" / s).resolve().exists():
                missing.append(f"{jf.name}: {s}")

    deliv = json.loads((ROOT / "app/data/deliverables.json").read_text())
    layers = json.loads((ROOT / "app/data/layers.json").read_text())
    generated = layers.get("generated", "unknown")
    n_sites = int(layers.get("sites", {}).get("n", 0))
    (OUT / "index.html").write_text(
        landing(deliv.get("memos", []), deliv.get("appendix"), has_v3, has_video, n_sites, generated), encoding="utf-8")

    (OUT / "_headers").write_text(
        "/*\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: strict-origin-when-cross-origin\n"
        "/app/data/*\n  Cache-Control: public, max-age=3600, stale-while-revalidate=86400\n"
        "/app-v3/data/*\n  Cache-Control: public, max-age=3600, stale-while-revalidate=86400\n"
        "/deliverables/*\n  Cache-Control: public, max-age=3600, stale-while-revalidate=86400\n"
        "/app/vendor/*\n  Cache-Control: public, max-age=604800\n"
        "/app-v2/vendor/*\n  Cache-Control: public, max-age=604800\n"
        "/app-v2/fonts/*\n  Cache-Control: public, max-age=31536000, immutable\n",
        encoding="utf-8")

    # Size limits.
    compacted, too_big = [], []
    for p in sorted(OUT.rglob("*")):
        if p.is_file() and p.stat().st_size > MAX_FILE:
            before = p.stat().st_size
            if p.suffix in (".json", ".geojson"):
                compact_json(p)
                compacted.append(f"{p.relative_to(OUT)}: {fmt_mb(before)} -> {fmt_mb(p.stat().st_size)}")
            if p.stat().st_size > MAX_FILE:
                too_big.append(f"{p.relative_to(OUT)} ({fmt_mb(p.stat().st_size)})")
    files = [p for p in OUT.rglob("*") if p.is_file()]
    total = sum(p.stat().st_size for p in files)
    largest = sorted(files, key=lambda p: -p.stat().st_size)[:8]
    info = {
        "built": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "data_generated": generated,
        "files": len(files),
        "total_bytes": total,
        "total": fmt_mb(total),
        "largest": [{"path": str(p.relative_to(OUT)), "size": fmt_mb(p.stat().st_size)} for p in largest],
        "included": included,
        "app_v3": v3_note,
        "video": "included" if has_video else "video/out/southwest-solar-explainer.mp4 not found",
        "compacted_json": compacted,
        "over_25MiB": too_big,
        "missing_links": missing,
    }
    (OUT / "build-info.json").write_text(json.dumps(info, indent=1), encoding="utf-8")

    print(f"site-build: {len(files)} files, {fmt_mb(total)}; largest {largest[0].relative_to(OUT)} {fmt_mb(largest[0].stat().st_size)}")
    print(f"v3: {v3_note}; video: {info['video']}")
    if compacted:
        print("compacted:", *compacted, sep="\n  ")
    errs = []
    if too_big:
        errs.append("files over 25 MiB (split them or move to R2): " + ", ".join(too_big))
    if len(files) > MAX_FILES:
        errs.append(f"{len(files)} files, over the {MAX_FILES} limit")
    if missing:
        errs.append("dashboard links with no file in the build: " + ", ".join(missing))
    for m in errs:
        print("ERROR:", m, file=sys.stderr)
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())

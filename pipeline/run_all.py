# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Run the whole Southwest siting pipeline end to end.

Order: grid (fetch, process), land (fetch, process), infra (fetch, process), screen.py, memos.py, build_app.py.
A stage is skipped when its outputs exist and are newer than its inputs; --force reruns every stage and passes
--force to it. Each stage is its own `uv run --script` process, so their pinned dependencies stay separate.

  uv run --script pipeline/run_all.py              # run what is missing or stale
  uv run --script pipeline/run_all.py --dry-run    # show the plan only
  uv run --script pipeline/run_all.py --only screen memos build_app
  uv run --script pipeline/run_all.py --from screen --force

Timing on the build machine: a fresh land process run takes about 30 to 40 min and fetch_land downloads about 4 GB;
screen.py takes several minutes; build_app.py about 3 min.
"""
import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "data" / "processed"
LOG = ROOT / "logs" / "app.log"
UV = shutil.which("uv") or "/opt/homebrew/bin/uv"


def files(*globs):
    out = []
    for g in globs:
        out += [f for f in ROOT.glob(g) if f.is_file()]
    return out


def mtime(paths, newest=True):
    ts = [p.stat().st_mtime for p in paths if p.exists()]
    if not ts:
        return None
    return max(ts) if newest else min(ts)


# name, script, extra args, outputs (all must exist), inputs (outputs must be newer than these)
STAGES = [
    ("fetch_grid", "pipeline/fetch_grid.py", [], ["data/raw/grid"], []),
    ("process_grid", "pipeline/process_grid.py", [],
     ["data/processed/grid/MANIFEST.json", "data/processed/grid/transmission_lines.geojson",
      "data/processed/grid/substations.geojson", "data/processed/grid/queue_projects.csv",
      "data/processed/grid/queue_by_county.csv"], []),
    ("fetch_land", "pipeline/fetch_land.py", [], ["data/raw/land"], []),
    ("process_land", "pipeline/process_land.py", [],
     ["data/processed/land/MANIFEST.json", "data/processed/land/blm_solar_available.geojson",
      "data/processed/land/ownership.gpkg", "data/processed/land/exclusions_full.gpkg", "data/processed/land/ghi.tif",
      "data/processed/land/slope.tif"], []),
    ("fetch_infra", "pipeline/fetch_infra.py", [], ["data/raw/infra"], []),
    ("process_infra", "pipeline/process_infra.py", [],
     ["data/processed/infra/MANIFEST.json", "data/processed/infra/fiber.geojson",
      "data/processed/infra/power_plants.geojson", "data/processed/infra/water_stress.geojson",
      "data/processed/infra/blm_solar_row_cases.geojson"], []),
    ("screen", "pipeline/screen.py", [],
     ["data/processed/sites/candidate_sites.geojson", "data/processed/sites/top_sites.csv",
      "data/processed/sites/all_sites.csv", "deliverables/Southwest_Solar_Sites.xlsx"],
     ["data/processed/grid/MANIFEST.json", "data/processed/land/MANIFEST.json", "data/processed/infra/MANIFEST.json"]),
    ("memos", "pipeline/memos.py", [], ["deliverables/site_memos/README.md"],
     ["data/processed/sites/top_sites.csv"]),
    ("build_app", "pipeline/build_app.py", [], ["app/data/layers.json"],
     ["data/processed/sites/candidate_sites.geojson", "deliverables/site_memos/README.md",
      "data/processed/grid/MANIFEST.json", "data/processed/land/MANIFEST.json", "data/processed/infra/MANIFEST.json",
      "pipeline/build_app.py"]),
]
NAMES = [s[0] for s in STAGES]


def status(outputs, inputs):
    out = [ROOT / o for o in outputs]
    missing = [str(o.relative_to(ROOT)) for o in out if not o.exists() or (o.is_dir() and not any(o.iterdir()))]
    if missing:
        return "missing", f"missing {', '.join(missing[:2])}{' ...' if len(missing) > 2 else ''}"
    newest_in = mtime([ROOT / i for i in inputs])
    oldest_out = mtime(out, newest=False)
    if newest_in and oldest_out and newest_in > oldest_out:
        return "stale", "inputs changed since last run"
    return "done", "outputs present and up to date"


def log(msg):
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} run_all {msg}"
    print(line, flush=True)
    LOG.parent.mkdir(exist_ok=True)
    with LOG.open("a") as f:
        f.write(line + "\n")


def summary_counts():
    lines = []
    f = P / "sites" / "sites_by_state.csv"
    if f.exists():
        rows = [r.split(",") for r in f.read_text().strip().splitlines()]
        h = rows[0]
        for r in rows[1:]:
            d = dict(zip(h, r))
            lines.append(f"  {d.get('state')}: {int(float(d.get('sites', 0))):,} ranked sites, "
                         f"{int(float(d.get('blm_available', 0))):,} BLM solar-available, best solar score {d.get('best_solar')}")
    lj = ROOT / "app" / "data" / "layers.json"
    if lj.exists():
        d = json.loads(lj.read_text())
        lines.append(f"  app: {len(d['layers'])} layers, {d['sites']['n']:,} sites, built {d['generated']}")
    memos = ROOT / "deliverables" / "site_memos"
    if memos.exists():
        lines.append(f"  memos: {len([m for m in memos.glob('*.md') if m.name != 'README.md'])} site memos")
    return lines


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--force", action="store_true", help="rerun every selected stage and pass --force to it")
    ap.add_argument("--only", nargs="+", choices=NAMES, help="run only these stages")
    ap.add_argument("--from", dest="start", choices=NAMES, help="start at this stage")
    ap.add_argument("--dry-run", action="store_true", help="print the plan and exit")
    a = ap.parse_args()

    sel = STAGES
    if a.start:
        sel = sel[NAMES.index(a.start):]
    if a.only:
        sel = [s for s in sel if s[0] in a.only]

    results = []
    upstream_ran = False
    log(f"start: stages {', '.join(s[0] for s in sel)}{' (force)' if a.force else ''}")
    for name, script, extra, outputs, inputs in sel:
        st, why = status(outputs, inputs)
        run = a.force or st != "done"
        if not run and upstream_ran and name in ("screen", "memos", "build_app"):
            run, why = True, "an earlier stage ran"
        if not run:
            log(f"{name:13s} skip ({why})")
            results.append((name, "skipped", 0.0, why))
            continue
        cmd = [UV, "run", "--script", str(ROOT / script), *extra]
        if a.force:
            cmd.append("--force")
        elif name == "screen" and (ROOT / "data/processed/sites/work/cells.npz").exists():
            cmd.append("--rescore")  # caches exist; recompute substations, queue, scores and outputs only
        if a.dry_run:
            log(f"{name:13s} would run: {' '.join(cmd[3:])} ({why})")
            results.append((name, "planned", 0.0, why))
            continue
        log(f"{name:13s} run ({why}): {' '.join(Path(c).name if i == 3 else c for i, c in enumerate(cmd[3:], 3))}")
        t0 = time.time()
        rc = subprocess.call(cmd, cwd=ROOT)
        dt = time.time() - t0
        if rc != 0:
            log(f"{name:13s} FAILED (exit {rc}) after {dt:.0f} s; later stages not run")
            results.append((name, f"failed ({rc})", dt, why))
            break
        st2, _ = status(outputs, [])
        log(f"{name:13s} ok in {dt:.0f} s{'' if st2 == 'done' else ' (warning: outputs still missing)'}")
        results.append((name, "ran", dt, why))
        upstream_ran = True

    print("\nPipeline summary")
    print(f"  {'stage':13s} {'result':12s} {'time':>7s}  note")
    for name, res, dt, why in results:
        print(f"  {name:13s} {res:12s} {dt:6.0f}s  {why}")
    for line in summary_counts():
        print(line)
    print("\nOpen the dashboard: uv run --script app/serve.py  (http://localhost:8770/app/)")
    if any(r[1].startswith("failed") for r in results):
        sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env bash
# Smoke test for the live site. Usage: deploy-site/smoke.sh [URL]   (default: the URL in deploy-site/URL)
# 1. HTTP 200 (and a sane size) for the landing page, both dashboards, key data files and deliverables.
# 2. Playwright at 1440x900 on the live URL: landing, v2 map, v2 scorecard; fails on any console or page error.
#    Screenshots: deploy-site/*.png. Results: deploy-site/smoke_result.json.
set -uo pipefail
cd "$(dirname "$0")/.."
URL="${1:-$(cat deploy-site/URL 2>/dev/null)}"
URL="${URL%/}"
[ -n "$URL" ] || { echo "usage: deploy-site/smoke.sh https://<worker>.workers.dev" >&2; exit 2; }

fail=0
check() {  # path  min_bytes
  local out code size
  out=$(curl -sL -o /dev/null -w '%{http_code} %{size_download}' --max-time 120 "$URL$1")
  code=${out% *}; size=${out#* }
  if [ "$code" = "200" ] && [ "$size" -ge "$2" ]; then echo "ok   $code $(printf '%10s' "$size") $1"
  else echo "FAIL $code $(printf '%10s' "$size") $1"; fail=1; fi
}
check /                                         2000
check /app/                                     2000
check /app-v2/                                  2000
check /app/doc.html?f=x                           1000
check /app/data/layers.json                     1000
check /app/data/sites_attr.json                 1000000
check /app/data/sites_geom.geojson              1000000
check /app/data/summary.json                    1000
check /app/data/sources.json                    1000
check /app/data/deliverables.json               500
check /app/data/layers/excl_slope_gt5.geojson   1000000
check /app/data/appendix/METHODOLOGY_REVIEW.md  1000
check /app-v2/app.js                            10000
check /app-v2/fonts/source-serif-4-latin-wght-normal.woff2 10000
check /deliverables/Southwest_Solar_Sites.xlsx  1000000
check /deliverables/BLM_Application_Brief.md    1000
check /deliverables/site_memos/01_SW-NM-00001.md 1000
check /data/processed/sites/METHOD.md           1000
if [ -d site-build/app-v3 ]; then check /app-v3/ 1000; fi
if [ -d site-build/media ]; then check /media/southwest-solar-explainer.mp4 100000; fi

# Every file listed in layers.json must be served.
for f in $(curl -s "$URL/app/data/layers.json" | grep -Eo '"file": *"[^"]+"' | sed -E 's/.*"([^"]+)"$/\1/' | sort -u); do
  check "/app/$f" 100
done

echo "--- browser (Playwright, 1440x900)"
/opt/homebrew/bin/uv run --script deploy-site/smoke_browser.py "$URL" || fail=1

if [ "$fail" = 0 ]; then echo "SMOKE PASS $URL"; else echo "SMOKE FAIL $URL"; fi
exit $fail

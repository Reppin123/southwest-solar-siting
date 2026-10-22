#!/usr/bin/env bash
# Build site-build/ and deploy it to Cloudflare (Worker "southwest-solar-siting"), then smoke-test the live URL.
# Usage: scripts/deploy_site.sh            build + deploy + smoke test
#        scripts/deploy_site.sh --no-smoke build + deploy only
set -euo pipefail
cd "$(dirname "$0")/.."

/opt/homebrew/bin/uv run --script scripts/build_site.py

npx wrangler whoami >/dev/null 2>&1 || { echo "Cloudflare login missing: run 'npx wrangler login' and retry." >&2; exit 2; }

npx wrangler deploy 2>&1 | tee deploy-site/last_deploy.log
URL=$(grep -Eo 'https://[a-zA-Z0-9.-]+\.workers\.dev' deploy-site/last_deploy.log | head -1)
[ -n "$URL" ] || { echo "Could not find the workers.dev URL in the deploy output." >&2; exit 1; }
echo "$URL" > deploy-site/URL
echo "Live: $URL/"

if [ "${1:-}" != "--no-smoke" ]; then
  deploy-site/smoke.sh "$URL"
fi

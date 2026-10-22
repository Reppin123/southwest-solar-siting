# Live site

**URL: https://southwest-solar-siting.akshitbansal1313.workers.dev/**

- Landing page: https://southwest-solar-siting.akshitbansal1313.workers.dev/
- Dashboard v2 (recommended): https://southwest-solar-siting.akshitbansal1313.workers.dev/app-v2/
- Dashboard v1: https://southwest-solar-siting.akshitbansal1313.workers.dev/app/
- How to Read This (opens v2 on that tab): https://southwest-solar-siting.akshitbansal1313.workers.dev/app-v2/#guide

Hosted on the user's Cloudflare account as the Worker `southwest-solar-siting` (Workers static assets, the same setup as ~/saboteur-game/site). Deployed 2026-10-22 with wrangler 4.151.3. Right now the site is **public**: anyone who has the link can open it. The section at the end explains how to make it private.

## What is on the site

| Path | What | Source (read only) |
|---|---|---|
| `/` | Landing page: summary, links to the dashboards, How to Read This, deliverables, site memos, the GPT methodology review | written by `scripts/build_site.py` |
| `/app/` | Dashboard v1 and all dashboard data (`/app/data/`) | `app/` (tests, screenshots, serve.py left out) |
| `/app-v2/` | Dashboard v2. It reads `../app/data/` the same way it does locally | `app-v2/` (tests, screenshots, TEAM, design evidence left out) |
| `/deliverables/` | Excel ranking, BLM brief, BLM sources, 15 site memos + README | `deliverables/` |
| `/data/processed/sites/METHOD.md` | Scoring method (linked from the Deliverables tab) | same path |

The markdown files (memos, brief, method, review) open as formatted pages through v1's `app/doc.html` viewer. Each one also has a raw `.md` download link on the landing page.

The only change made to the deployed copies: `build_site.py` adds a small script to each dashboard's `index.html` that opens a tab from the URL hash (`#guide`, `#summary`, `#sources`, `#deliverables`). The landing page needs this for its How to Read This link. The source folders are never edited.

## Size and Cloudflare limits

- 93 files, 114.2 MB in total (details in `site-build/build-info.json`).
- Largest file: `app/data/layers/excl_slope_gt5.geojson` at 15.1 MB. The next largest are `deliverables/Southwest_Solar_Sites.xlsx` (14.6 MB) and `app/data/sites_attr.json` (13.8 MB).
- No file is over the 25 MiB per-file limit, and the site is far below the 20,000-file limit. No splitting or R2 was needed.
- The build checks for this on every run. A JSON or GeoJSON file over 25 MiB gets minified with its coordinates rounded to 5 decimals in the deployed copy. Any file still over the limit stops the build with an error that names it. That file would then need splitting or moving to R2.
- When the map first opens, the browser downloads about 25 MB of site data. Other layers download only when they are switched on.
- Cache headers (`site-build/_headers`): data and deliverables 1 hour plus 1 day stale-while-revalidate, vendor JS 1 week, fonts 1 year. Checked live: `/app/data/summary.json` returns `cache-control: public, max-age=3600, stale-while-revalidate=86400`.

## What was checked (2026-10-22, against the live URL)

`deploy-site/smoke.sh` passed (`SMOKE PASS`):

1. **HTTP 200 checks** (curl, following redirects, with a minimum size for each):
   - the landing page, `/app/`, `/app-v2/` and `/app/doc.html`
   - the dashboard data files: layers.json, sites_attr.json (14.4 MB), sites_geom.geojson (10.7 MB), summary.json, sources.json, deliverables.json, and the methodology review
   - the v2 app.js and its fonts
   - the Excel file (15.3 MB), the BLM brief, memo 01 and METHOD.md
   - every layer and overlay file listed in `app/data/layers.json`
2. **Playwright checks at 1440x900** (`deploy-site/smoke_browser.py`, Chromium; results in `deploy-site/smoke_result.json`). All 10 checks passed:
   - The landing page renders with its title and all of its key links.
   - Site memo 01 renders as HTML.
   - The v2 map loads all 25,733 sites across the 5 states (in about 3 s).
   - The v2 map draws the sites: 25,733 rendered features.
   - The v2 ranked table fills.
   - The v2 scorecard opens for the top site (SW-NM-00001).
   - `#guide` opens How to Read This.
   - The v1 map loads all 25,733 sites.
   - There were **no console errors, page errors or failed requests**.
3. **Screenshots**, in `deploy-site/`:
   - `01_landing_1440.png`
   - `02_v2_map_1440.png`
   - `03_v2_scorecard_1440.png`
   - `04_memo_1440.png`
   - `05_v2_guide_1440.png`
   - `06_v1_map_1440.png`

Known limits, not caused by hosting:
- Inside the site memo overview (`site_memos/README.md`), the links between memos are relative to the .md file. When it is rendered through `app/doc.html`, those links point to the wrong folder. This also happens when you run the dashboards locally. The memos open correctly from the landing page and from the dashboards' Deliverables tab.
- The map basemaps come from public tile servers (OpenStreetMap, Esri, OpenTopoMap), not from Cloudflare.

## Redeploy (one command)

```
scripts/deploy_site.sh
```

This command does three things:
1. Rebuilds `site-build/` (`/opt/homebrew/bin/uv run --script scripts/build_site.py`).
2. Runs `npx wrangler deploy`, which uploads only the files that changed.
3. Runs `deploy-site/smoke.sh` against the live URL.

Use `scripts/deploy_site.sh --no-smoke` to skip the test. To run only the test, use `deploy-site/smoke.sh`, which reads the URL from `deploy-site/URL`. If Cloudflare login has expired, the script stops and asks you to run `npx wrangler login`.

## Adding v3 and the explainer video later

Nothing needs editing. Just rerun `scripts/deploy_site.sh` once the inputs below exist.

- **Dashboard v3** is included only when both of these are true:
  - `app-v3/index.html` exists.
  - `app-v3/tests/last_run.json` exists and every check in it has `"ok": true`. It uses the same format as app-v2's test output.

  When v3 is included, it goes to `/app-v3/`, gets listed first on the landing page, and smoke.sh checks it returns 200. If v3 later needs its own data folder (`app-v3/data/`), it already has a cache rule. Today: `app-v3/index.html not found`, so v3 is not on the site.
- **Explainer video**: once `video/out/southwest-solar-explainer.mp4` exists, it is copied to `/media/` and shown on the landing page with a download link. `deploy-site/worker.js` runs only for `/media/*`. It answers byte-range requests with 206, which Safari on iPhone needs to play an MP4. Today the video is not rendered yet, so `/media/` is empty.
- If the video is over 25 MiB, the build will stop and name the file. Re-encode it smaller. Another option is to upload it to an R2 bucket (`npx wrangler r2 bucket create southwest-solar-media`, then `npx wrangler r2 object put southwest-solar-media/southwest-solar-explainer.mp4 --file ... --remote`) and serve it through an R2 binding in `worker.js`.

## Making it private (Cloudflare Access)

Today anyone with the URL can open the site. To limit it to named people:

1. In the Cloudflare dashboard, go to **Zero Trust**. The first time, choose a team name; the Free plan covers up to 50 users.
2. Go to **Access > Applications > Add an application > Self-hosted**. Set the domain to `southwest-solar-siting.akshitbansal1313.workers.dev`.
3. Add a policy with Action **Allow** and the rule **Emails** set to the addresses you want, for example the person you share the link with. The default login method is a one-time PIN sent by email.
4. A shortcut: open **Workers & Pages > southwest-solar-siting > Settings > Domains & Routes**. Next to the workers.dev route, choose **Enable Cloudflare Access**, then edit the policy it creates.

People then get an email PIN prompt before the site loads. The smoke test will start failing at that point (it will get the login page), which is expected. To turn it off again, delete the Access application.

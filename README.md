# Southwest Solar and Data Center Siting

**Live dashboards: https://southwest-solar-siting.akshitbansal1313.workers.dev/**

## What this is

This is a screening tool for finding land in the US Southwest for large solar farms. It covers California, Arizona, Nevada, New Mexico and Utah. It looks for sites with three things: a realistic way to connect to the power grid, land that can be built on, and strong sun. It also checks whether a site could host a data center next to the solar farm, and it flags Bureau of Land Management (BLM) land worth applying for.

It uses only free public data: transmission lines, substations, interconnection queues, BLM land, land ownership, environmental limits, sun, slope, roads, fiber and water. From that data it finds 25,733 candidate sites, scores and ranks them, and shows them on an interactive map. It also produces an Excel ranking, memos for the top 15 sites, and a brief on how to apply for BLM land.

This is a screening study built from public data, not an engineering study. See "Limits" below.

## The ask

The question behind the project, in the owner's words: "see where there's a good way to connect power and also good land for large scale solar projects. And data centers and a BLM land that I should apply for. In the Southwest Region." California was added to the scope later. The agreed scope is in `SCOPE.md`:
- solar projects of 100 MW to 1 GW, at about 5 to 7 acres per MW, so each site needs at least 600 contiguous acres
- optionally, a 50 to 500 MW data center load on the same site
- every type of land owner, with BLM solar-available land flagged and ranked first

## Open the dashboards

**Online (nothing to install):**
- Landing page: https://southwest-solar-siting.akshitbansal1313.workers.dev/
- Dashboard v2 (recommended): https://southwest-solar-siting.akshitbansal1313.workers.dev/app-v2/
- Dashboard v1: https://southwest-solar-siting.akshitbansal1313.workers.dev/app/
- How to Read This guide: https://southwest-solar-siting.akshitbansal1313.workers.dev/app-v2/#guide

The site runs on Cloudflare Workers. `deploy-site/LIVE.md` covers what was deployed and tested, how to redeploy (`scripts/deploy_site.sh`) and how to restrict the site to named people.

**Locally** (needs [uv](https://docs.astral.sh/uv/); the dashboard data is already in the repo):

```
uv run --script app/serve.py
```

This command serves the project on http://localhost:8770 and opens your browser. v1 is at `/app/` and v2 at `/app-v2/`. Use `--port N` to pick a different port and `--no-browser` if you do not want a browser window opened. You can also run v2 on its own with `uv run --script app-v2/serve.py` (port 8772).

Dashboard tabs:
- **Map** (default): layers to switch on and off, and candidate sites coloured by score. Click a site to see its scorecard. Weight sliders and filters re-rank the sites as you move them. A switch changes the ranking between Solar and Solar + Data Center. There is also a ranked table and a CSV export.
- **Summary**: charts of sites by state, the spread of scores, the interconnection queue by state and type, and substations with less crowded queues.
- **Sources and Limits**: every dataset, with its source, date, record count and caveats.
- **Deliverables**: links to the Excel file, the site memos, the BLM brief and the scoring method.
- **How to Read This**: a plain-English guide to the colours, the controls, how scores are made, the limits, and a glossary.

## Deliverables

| File | What |
|---|---|
| `deliverables/Southwest_Solar_Sites.xlsx` | Ranked table of all sites (solar ranking and data center ranking) |
| `deliverables/site_memos/` | Memos for the top 15 sites, plus a README index |
| `deliverables/BLM_Application_Brief.md` | How to apply for a BLM solar right-of-way, which sites to start with, and policy changes |
| `deliverables/sources_blm.md` | Sources used in the BLM brief |
| `data/processed/sites/top_sites.csv`, `top_sites_dc.csv`, `all_sites.csv` | Top 50 solar sites, top 50 data center sites, and every site |
| `data/processed/sites/METHOD.md` | Scoring method |
| `review/METHODOLOGY_REVIEW.md` | Independent methodology review by a different AI model (GPT), with its audit script in `review/checks/` |

## Get the data

- **In this repo:** all code, the dashboard data, the deliverables, and every processed layer under 95 MB (CSV, GeoJSON, small GeoPackages and GeoTIFFs).
- **In the GitHub release [v1.0-data](https://github.com/Reppin123/southwest-solar-siting/releases/tag/v1.0-data):** four processed files too large for git (the full-resolution slope raster, exclusions, ownership and BLM solar-available layers), plus a bundle of all the other processed layers for people who do not use git.
- **Not stored anywhere:** the raw downloads (about 11 GB). The pipeline fetches them again from the public sources.

`DATA.md` lists every dataset with its source, retrieval date, licence, location and checksums.

## Rerun the pipeline

```
uv run --script pipeline/run_all.py --help      # options
uv run --script pipeline/run_all.py --dry-run   # show which stages would run
uv run --script pipeline/run_all.py             # run only missing or stale stages
uv run --script pipeline/run_all.py --only screen memos build_app
uv run --script pipeline/run_all.py --from screen --force
```

The stages run in this order: fetch_grid, process_grid, fetch_land, process_land, fetch_infra, process_infra, screen, memos, build_app. A stage is skipped when its outputs exist and are newer than its inputs; `--force` reruns it.

On a fresh clone there is no `data/raw/`, so the fetch stages download everything again (about 11 GB). The land stage alone downloads about 4 GB and takes 30 to 40 minutes to process. To only re-score sites, download the four release files first (see `DATA.md`) and run `--only screen memos build_app`. The screen stage also uses intermediate caches in `data/processed/sites/work/`, which are not in the repo. They are rebuilt the first time the stage runs. The one exception is `all_sites_v1_ranks.csv`, which is only used for the before and after table in `METHOD.md`. Without it, that table shows "v1 ranks not available".

Every script has a PEP 723 header with pinned dependencies and runs with `uv run --script`. No system Python packages are used.

Tests:
- `uv run --script app/tests/test_app.py` (v1; results in `app/tests/RESULTS.md`)
- `uv run --script app-v2/tests/test_v2.py` (v2)
- `deploy-site/smoke.sh` (live site)

## Folder map

```
README.md, DATA.md, SHARE.md, LICENSES.md   overview, data inventory, how to share, licences
SCOPE.md                  approved scope (sources, weights, deliverables, limits)
pipeline/                 fetch_*.py, process_*.py, screen.py, memos.py, build_app.py, run_all.py
data/processed/           grid, land, infra, sites layers, each with MANIFEST.json
data/raw/                 raw downloads (not in git; re-fetched by the pipeline)
app/                      dashboard v1: serve.py, index.html, app.js, doc.html, data/, vendor/, tests/, screenshots/
app-v2/                   dashboard v2 (same data, new design): design/, fonts/, tests/, screenshots/
deliverables/             Excel ranking, site memos, BLM brief
review/                   independent GPT methodology review and audit script
scripts/                  build_site.py, deploy_site.sh (Cloudflare), package_release.sh (GitHub release)
deploy-site/              Cloudflare Worker, smoke tests, LIVE.md, screenshots of the live site
wrangler.jsonc            Cloudflare Workers config
logs/                     pipeline logs
TEAM/                     planning notes and briefs from the build (not needed to use the product)
```

Coming later (not in this commit): dashboard v3 (`app-v3/`, being built by another team) and an explainer video (`video/`). Both are left out until they are finished. Once they are, the site build picks them up automatically (see `deploy-site/LIVE.md`).

## Limits

- Public maps show where lines and substations are, not how much spare capacity they have. Only the utility can tell you that.
- Queue data shows crowding, not capacity. Queue MW is matched to substations by name, so 0 (or white on the map) means unknown, not empty.
- Some substation data is old: the HIFLD substation file was last edited 2021-02-25. Some records are provisional (found only in OSM, or with an inferred voltage). Sites that depend on them have their grid score cut by 15 percent and are flagged.
- Fiber is a proxy. About 99 percent of it is not confirmed fiber, so the data center ranking is weaker than the solar ranking.
- Land ownership shows the agency that manages the surface. It does not show legal title, leases or mining claims.
- This is not engineering: there were no site visits, grid studies, cost estimates or environmental studies.
- Federal policy on solar on public land changed in 2025 and 2026. See `deliverables/BLM_Application_Brief.md`.
- The scores are for narrowing a list down to a short list, not for making the final decision. The independent review in `review/` lists further caveats.

## Credits and sources

All data is public and free: HIFLD, OpenStreetMap contributors, Berkeley Lab (Queued Up), CAISO, US EIA (Form 860), BLM (Western Solar Plan, Surface Management Agency, NLCS, ACEC, MLRS), USFWS (critical habitat, National Wetlands Inventory), FEMA (NFHL), US Census Bureau (TIGER), NREL (NSRDB), AWS Terrain Tiles (USGS 3DEP), WRI Aqueduct 4.0, Wilderness Connect (University of Montana), Arizona Department of Water Resources, and BTS (NTAD rail). Map tiles come from OpenStreetMap, Esri and OpenTopoMap. `DATA.md` has the full source list and `LICENSES.md` the licence terms.

The project was built with AI agent teams (Claude) working for the owner. The methodology review was done by a separate model (GPT).

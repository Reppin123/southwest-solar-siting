# Team report

**Goal:** An end-to-end Southwest (CA, AZ, NV, NM, UT) siting platform for utility-scale solar and data centers: public grid, land, BLM and infrastructure data in, scored candidate sites and a map-based decision dashboard out, plus a BLM application brief. (Run 4: finish and verify the already-built dashboard only.)  
**Deliverable:** ~/research/southwest-solar-siting: app/ (run uv run --script app/serve.py), pipeline/ (uv run --script pipeline/run_all.py), deliverables/ (Excel ranking, site memos, BLM brief)  
**Final reviewer:** anthropic/claude-opus-5-5

| Task | State | Model | Reviewed by | Review | Fix rounds | Minutes | Cost |
|---|---|---|---|---|---|---|---|
| app-finish: Finish, verify and add How to Read This page | done | claude-opus-5-5 | claude-opus-5-5 | pass 9/10 | 0 | 24.5 | $2.91 |

Total model spend reported: $2.91 (subscription sign-ins report what it would have cost).

## app-finish: Finish, verify and add How to Read This page (done)

**Note:** I checked the work myself and the summary holds up. The How to Read This tab has all 10 sections and directly answers the red line and red dots question. Its colours come from layers.json and its counts and dates come from the data, and its policy claims agree with the BLM brief. RESULTS.md shows 76 of 76 checks passing, both 1440 and 1280 screenshots are saved (including the new tab), README.md is present with the default port set to 8770, and running `run_all.py --help` works.

**Checks:** `test -s app/index.html` passed, `test -s app/serve.py` passed, `test -s pipeline/run_all.py` passed, `ls app/screenshots/*.png` passed, `! grep -Eiq '<script[^>]+src="https?:' app/index.html` passed, `test -s README.md` passed, `test -s app/tests/RESULTS.md` passed, `grep -rqi 'How to Read This' app/index.html app/app.js` passed

**Files:** app/app.js, app/tests/test_app.py, README.md

**What the helper says it did:**

e earlier test hung.** The problem was in the test script, not the dashboard. The click-a-site step asked the browser for a value that turned out to be the whole map object, and the test froze trying to copy it back. Two other test bugs showed up once that was fixed: the "wait until the map is idle" helper was looking at the wrong thing, and the scorecard text check was case-sensitive in a way that made it fail. All three are fixed, and the dashboard itself needed no changes. The test also now shuts down its own server on 8771 when it finishes; before, it left one running.

**The new page.** "How to Read This" is the last tab; the Map is still the default view. It's plain English with no em dashes, and it has the 10 sections from your brief:
- **Red line and red dots:** it answers your question directly. Red lines are 500 kV and up, the biggest lines on the grid. A red substation dot means over 2,000 MW of projects are already waiting to connect there, so it's crowded.
- **Map key:** it also covers white dots (no queue data matched, which means unknown rather than empty), the purple ring for unconfirmed records, darker teal for higher-scoring sites and mustard for BLM land open to solar. A small diagram shows what a good site looks like.
- **Real data:** the colours come from the dashboard's own layer file. Counts, dates and default weights come from the data files, including 25,733 sites, the 2021 date on the federal substation file and the top-ranked site.

**Other items:**
- `README.md` is new at the project root and covers what it is, how to run and refresh it, sources, limits and a folder map. Port 8770 is the default in `serve.py`, and no docs mention 8765.
- `uv run --script pipeline/run_all.py --help` works. A dry run shows all 9 stages skipped as already done; I did not force a full re-run.
- Screenshots are saved at 1440 and 1280 px: overview, scorecard open, data center ranking, Summary, Sources, and two of the new page (top, and the map key section).
- `app/tests/RESULTS.md` lists every check with pass or fail, including the README and run_all checks.

**Left open:** the dashboard loads its free map backgrounds (street, satellite, terrain) from the internet, so those need a connection. The test also leaves a sample CSV export in `app/tests/`.

Files are in `~/research/southwest-solar-siting`:
- `README.md`
- `app/index.html`
- `app/app.js`
- `app/style.css`
- `app/tests/test_app.py`
- `app/tests/RESULTS.md`
- `app/screenshots/`
- `logs/app.log`

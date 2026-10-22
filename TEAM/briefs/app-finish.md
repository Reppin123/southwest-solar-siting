# Brief: app-finish (finish and verify the existing dashboard; do NOT rebuild it)
Read briefs/app.md first: its requirements still apply. A previous attempt already built app/ (index.html, app.js, style.css, serve.py, data/, vendor/, some screenshots) and pipeline/build_app.py and pipeline/run_all.py. It was killed only because its headless browser test went silent for 8 minutes.
NOTE: port 8765 is permanently taken by another app on this Mac (it answers HTTP 426), so change serve.py default port to 8770 and update README and any docs. The user currently has the dashboard open on port 8770; do not kill that server. Run your own test server on port 8771.
Do:
1. Inspect what exists; fix only what is broken or missing.
2. Headless test (Playwright via uv, chromium): load page, no console errors, toggle each layer, click a site and confirm the scorecard, move a weight slider and confirm re-rank, switch Solar / Solar + Data Center, export CSV. Run it with a hard timeout per step (e.g. 30 s) and print a progress line at least every 30 seconds so the run is never silent. Save screenshots to app/screenshots/ (overview, scorecard open, data center ranking, summary tab, sources tab) at 1440 and 1280 wide.
3. Make sure README.md exists at the project root (what it is, how to run, how to refresh, sources, limits, folder map) and that `uv run --script pipeline/run_all.py --help` works and run_all skips completed stages by default (do not actually force a full re-run).
4. Write app/tests/RESULTS.md with each check and pass/fail.
Owns: app/**, README.md, pipeline/run_all.py, pipeline/build_app.py, logs/app.log.
Done means: all checks in RESULTS.md pass, screenshots saved, README present, run_all --help works.

## ADDED: a "How to Read This" page (user request, verbatim)
"Can you add a, basically, one more page to this dashboard? Call it something like ReadMe or how to understand it. And then include, like, very nontech easy to understand, instructions on how to read the dashboard, how to use it, how it was prepared. What was the ask, what is it doing, What are some of the limitations and so on and so forth."
Earlier the user asked "how do I read it? And, there is this red line and red dots. What are these?" so the page must answer exactly that kind of question.

Build it as a new top tab named "How to Read This" (place it first or last in the tab bar; the Map stays the default view). Plain English, short sentences, no jargon without a one-line explanation, no em dashes. Sections:
1. What this is, in one paragraph (finding the best places in CA, AZ, NV, NM, UT for a large solar farm and possibly a data center, before spending real money).
2. What was asked (summarise the user's request faithfully: grid and substations, good land, data centers, BLM land to apply for, Southwest plus California, a dashboard to aid decisions).
3. What makes a good site: a nearby grid connection with room, large flat sunny land you can get (ideally BLM solar-available), no deal-breakers, and for data centers fiber, water and roads.
4. How to read the map: a visual legend built from the real layer colours in app/data/layers.json (line colours by voltage with red = 500 kV and up; substation dots: size = voltage, colour = queued MW with red = over 2,000 MW queued meaning crowded, white = unknown not empty, purple ring = provisional; teal sites darker = higher score; mustard = BLM solar-available land; other layers). Include a "what to look for" line: dark teal sites near a big line and a yellow or orange substation, ideally on mustard land.
5. How to use it, step by step: switch Solar vs Solar + Data Center, move weight sliders, filters (states, acres, distance, BLM only, hide provisional, high queue confidence), click a site for its scorecard, the table, export CSV, Summary and Sources tabs, Deliverables (Excel, memos, BLM brief).
6. How a score is made, in plain words, with the default weights for each ranking.
7. How it was prepared: the public data sources in plain terms (federal grid maps, Berkeley Lab queue data, CAISO, BLM solar plan, land ownership, USFWS habitat, FEMA flood, NREL sunshine, USGS slope, EIA power plants, fiber proxy, WRI water), the screening steps, the independent GPT review and the fixes applied.
8. Limitations, honest and plain: public maps do not show spare capacity; queue data is a crowding signal, not capacity; substation data partly dated (HIFLD substations last edited 2021) and some records provisional; fiber is mostly a proxy; land status is not legal title; not engineering; 2025 to 2026 federal policy changes and the end of solar tax credits for new BLM projects; scores are for narrowing down, not deciding.
9. What to do next with a top site (utility pre-application and capacity question, BLM field office pre-application, title and survey, environmental checks, counsel review).
10. A short glossary (kV, substation, interconnection queue, POI, BLM, SEZ, GHI, ROW, hard vs soft constraint).
Content must be generated from or consistent with the real data (pull counts and dates from the manifests/summary.json where cited). Add it to the headless test (tab opens, all sections present) and to the screenshots.
Accept adds: app/index.html (or app.js) contains the "How to Read This" tab.

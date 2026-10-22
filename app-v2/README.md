# Southwest siting dashboard, v2 design

A redesign of the Southwest Solar and Data Center Siting dashboard. It has the same content, data and features as v1. Only the design changed. v1 in `../app/` was not modified: `tests/test_v2.py` compares checksums of every v1 file before and after.

## How to open it

- If the project server is already running (`uv run --script app/serve.py`), open **http://localhost:8770/app-v2/**. v1 stays at http://localhost:8770/app/.
- To run v2 on its own: `uv run --script app-v2/serve.py`, then open http://localhost:8772/app-v2/. Use `--port N` to pick another port and `--no-browser` to skip opening a browser.

v2 needs no build step and makes no CDN calls. It reads the data from `../app/data/` instead of keeping a second 25 MB copy. Memos, briefs and the method open in v1's document viewer (`../app/doc.html`). MapLibre GL 4.7.1 and Chart.js 4.4.4 are in `vendor/`, copied from v1. The fonts are self-hosted in `fonts/`: Source Serif 4 and IBM Plex Sans, both under the SIL Open Font License 1.1, with their licence files alongside. Base map tiles still come from OpenStreetMap, Esri and OpenTopoMap, as in v1.

## Files

- `index.html`, `styles.css`, `app.js`: the app. The first part of `styles.css` is `design/tokens.css` copied verbatim; every colour, size and space in the app comes from those tokens. `app.js` reads the tokens at startup and uses them to colour the map and charts.
- `serve.py`: a standalone server that defaults to port 8772.
- `tests/test_v2.py`: a headless browser test ported from v1's `app/tests/test_app.py`, with extra checks for v2. Results are in `tests/RESULTS.md`. Run it with `uv run --script app-v2/tests/test_v2.py`. It starts its own server on port 4110.
- `tests/compare.py`: builds the side-by-side v1 and v2 images. `tests/look.py`: a development helper for quick renders.
- `screenshots/`: v2 at 1440 and 1280 px (overview, scorecard open, data center ranking, summary, sources, How to Read This, deliverables), plus `compare_*` images that place v1 and v2 side by side.

The design rationale, the v1 critique and the references are in `design/DESIGN.md`, which the refs helper wrote.

## What changed from v1

**Look and type**
- v1 used Tailwind's default slate palette, the system font at 13 px, rounded boxes and soft shadows everywhere. v2 is a single white sheet divided by hairline rules, and nothing has a corner radius above 2 px.
- Type uses two families with a fixed scale. Source Serif 4 sets the title, the large numbers and the reading text. IBM Plex Sans, with tabular figures, sets every control, label and table.
- The page has one accent colour, the deep blue of a high score. Every other colour belongs to the data.

**Map**
- The map has a real map key in its lower-left corner. The key lists only the layers that are switched on, as ramps with tick labels, line samples that thicken with voltage, and swatches. In v1 each legend sat under its checkbox in the left column, about 2,000 px down the page.
- The basemap choice (Street, Satellite, Terrain, Plain) is now in the key's footer, not a floating card.
- The base map is desaturated, so the data colours stand out.
- Map colours carry order:
  - Candidate sites use one blue ramp, with the same score thresholds as v1.
  - Transmission lines use one red-brown ramp, darker and thicker for higher voltage, where v1 used a rainbow.
  - Substations use a grey ramp by queued MW. White still means "unknown".
  - Provisional records have a violet ring.
  - BLM solar-available land is gold.
  - Soft exclusions are hatched, so they read differently from hard exclusions.
  - Existing data centers are the only square markers.
- The selected site has a black outline with a white halo, in place of v1's orange outline.
- The opening view frames all five states to the right of the map key.

**Left column, scorecard and table**
- Left column: a live "Sites shown" figure leads. Below it are weights, filters and layers. The state filter is five toggles on one line (v1's chips wrapped). Each layer's circled "i" button became a "Source" text link that opens the same source panel.
- Scorecard: it opens as a column beside the map, so the map narrows and is not covered (v1 used a floating card). It reads as a data sheet: a 48 px score, rank lines, factor bars coloured by the score ramp, and ruled key and value lists. The next step is set in italic with a rule beside it. Flags are outlined tags instead of tinted boxes. It closes with "Close" or Esc.
- Ranked table: it has the same columns, sorting, 400-row cap and CSV export. The header is in small capitals over an ink rule, rows are separated by hairlines and numbers are right-aligned. The selected row is marked with an accent bar. A provisional substation shows a small violet ring.

**Summary, Sources and Limits, Deliverables**
- Summary: five key figures run in one row separated by thin rules, where v1 had stat tiles. Each chart is a newspaper-style figure: an ink rule, a serif title and a caption, with no card around it. The chart colours match the map, the score histogram uses the score ramp, the chart keys are HTML rather than boxed legends, and charts have no entrance animation.
- Sources and Limits and Deliverables: these read as documents, with a title, a one-line summary, ruled lists and tables. The controls column is hidden on these two tabs and on How to Read This, because those pages do not depend on the controls. The provisional data note sits under a violet rule instead of a lavender box.

**How to Read This**
- The text and the ten sections are unchanged in substance. They are set as serif reading text at a 68-character line, with a sticky numbered table of contents that marks the section being read.
- The colour words were updated to match the new map: "darker blue", "near-black dots", "violet ring", "gold areas", and so on. The swatches are drawn from the same tokens as the map, so the guide and the map cannot disagree.
- One sentence changed in meaning to match the new layout: the colour key is now in the map's lower-left corner, not in the left column.

**Smaller screens**
- Under 1100 px wide, the controls become a drawer opened by "Controls" in the masthead, and the scorecard overlays the right edge.
- Under 760 px, the tabs collapse into a menu.

## Known limits

- The GHI and slope overlays are pre-rendered images in v1's data, so their colours could not change. Their key shows v1's values.
- The large categorical sets (9 plant types, 8 ownership classes, 10 exclusion layers) cannot all be told apart under colour-blindness simulation. Each colour has a text label in the map key, and the map popup names the category.
- Memo and document links open v1's document viewer, which still has v1's styling.
- The test does not run `pipeline/run_all.py`, unlike v1's test. That is a pipeline check, not a dashboard check, and running it could write outside app-v2.

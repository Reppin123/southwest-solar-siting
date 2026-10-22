# References

Captured 2026-10-22 with `design/tools/shoot.py` (headless Chromium, 1440 x 900 viewport, JPEG quality 70, cookie banners dismissed where a button allowed it). Each screenshot is the first screen of the page as a visitor sees it. Their images, logos and text belong to their owners; we borrow ideas only, never assets.

Sites that could not be captured: Reuters Graphics (bot wall: "Access is temporarily restricted"), Berkeley Lab Queued Up (Cloudflare check), NREL RE Explorer (host did not resolve). NYT, Bloomberg and FT graphics were not attempted: they sit behind paywalls or bot walls, so I have no first-hand capture of them and borrow nothing specific from them here.

## Map-centric tools (the core references)

| File | Source | What to borrow | What not to borrow |
|---|---|---|---|
| `openinframap.jpg` | https://openinframap.org/#5.2/35.5/-113.5/L,O,P,S | Line width that grows with voltage, so the 500 kV backbone reads before any colour is decoded. A map that fills the whole frame with a tiny title block and nothing else floating on it. | The dark basemap and glowing heat blobs (decorative here; our sites need a quiet light base). Its rainbow hue-per-voltage scheme: we use one hue, darker = higher kV. |
| `electricitymaps.jpg` | https://app.electricitymaps.com/map | The legend as a single horizontal ramp with tick values, docked bottom-right, labelled with the quantity and unit. A narrow left rail of plain text links, no icons-in-boxes. Map controls stacked tight at top-right. | Rounded floating cards and the soft-shadow time slider (exactly the "Tailwind box" look the user dislikes). The red-to-brown carbon ramp. |
| `felt.jpg` | https://felt.com | A serif display face paired with a plain sans for UI: the most direct model for our Source Serif 4 + IBM Plex Sans pairing. The coordinate strip at the very top (LAT, LON, ZOOM in small spaced caps) shows how cartographic metadata can be typographic. Square-cornered black primary button next to an outlined secondary one. The legend popover: a title, two rows with swatches, a hairline, one big number. | The watercolour illustration (it is marketing art). Cream background. |
| `climatetrace.jpg` | https://climatetrace.org/explore | The stat panel: one very large tabular number, its unit set smaller beside it, a one-line count under it, then a small chart. That hierarchy is our scorecard hero (score, rank, factor bars). | The globe, the dark sky, the 3D bars, and the button row bottom-right (pill-ish boxes for every control). |
| `transect.jpg` | https://www.transect.com | Siting-industry content model: a site "Summary" sheet with acres, distance to transmission, nearest substation, ownership, then interconnection and permitting sections. Confirms our scorecard sections are what developers expect. | Its UI: every metric in its own bordered tile, pastel-tinted alert banners, topo-line background texture, orange pill buttons. This is the look to move away from. |
| `paces.jpg` | https://www.paces.com | Restraint in palette: one deep green-black plus one light accent, square-ish buttons, uppercase spaced nav. Real photography rather than illustration. | The video hero and the green-on-photo headline: a marketing page, not a tool. |
| `landgate.jpg` | https://www.landgate.com | Nothing visual; included because the brief names it as the market's land and energy platform. Note what to avoid: gradient-filled giant uppercase hero, cyan pill buttons, a cookie panel that covers a third of the screen. | All of it. |
| `interconnectionfyi.jpg` | https://www.interconnection.fyi | Content: queue data presented as "N requests, X TW" with a county choropleth. Our Summary queue chart says the same with source and caveat. | Ticker strip, emoji, rounded filter chips in a grey well, orange floating CTA. A clear example of chip-row clutter. |
| `gem.jpg` | https://globalenergymonitor.org/projects/global-solar-power-tracker/tracker-map/ | The key-figures row: big coloured numbers, each with a one-line label, separated by thin vertical rules instead of cards. Our Summary stat row uses this pattern in ink, not colour. | Rounded container behind the row, rounded navbar card, orange buttons. |

## Editorial and data-journalism references

| File | Source | What to borrow | What not to borrow |
|---|---|---|---|
| `propublica-toxmap.jpg` | https://projects.propublica.org/toxmap/ | Map labels set like a printed atlas: small spaced caps for features (HOUSTON, GALVESTON BAY, MISSISSIPPI RIVER), italic for water. A heavy serif headline with a byline and date in small italic. A plain, dated data note set on a single colour. | The dark grey page and glowing overlays. |
| `owid.jpg` | https://ourworldindata.org/grapher/share-electricity-solar | The best model for our map plus ranked table: a map and, beside it, a ranked list where each row carries its value right-aligned with a faint inline bar behind it. Serif chart title with the year in lighter weight, a one-line description under it, then small caps section labels ("SELECT COUNTRIES AND REGIONS"). | The rounded grey tab group, and the large rounded-corner chart card. |
| `datawrapper-blog.jpg` | https://www.datawrapper.de/blog/ | Editorial page structure for Sources, Deliverables and How to Read This: a narrow left column of plain text links as the table of contents, a wide right column with a serif headline, a one-sentence dek, and a small grey dateline. Sections divided by full-width hairlines, not boxes. | The small grey "6 min" pill. |
| `linear.jpg` | https://linear.app | Restraint in a dense tool: one surface, hairline dividers between rail and content, muted secondary text, tight 13 px UI type, almost no colour except state. | Dark mode and the gradient glow behind the product shot. |

## How the references map to decisions in DESIGN.md

- Typography pairing: Felt (serif display, sans UI), OWID (serif chart titles, small caps labels), ProPublica (atlas labelling).
- Line hierarchy by width and lightness: Open Infrastructure Map.
- Map key: Electricity Maps (ramp with ticks, docked) and Felt (title, swatch rows, hairline).
- Scorecard hero: Climate TRACE stat panel; content order from Transect.
- Table: OWID ranked list with right-aligned values.
- Summary stat row: Global Energy Monitor key figures with rules between.
- Pages: Datawrapper blog layout; Linear for density and restraint.
- What to avoid, with evidence: Transect, LandGate, Interconnection.fyi and Electricity Maps' floating cards all show the rounded-box, pill and chip look the user called "AI slop".

## Detail crops (PNG)

Cropped at full resolution from the captures above with Pillow, so a single borrowed detail can be studied without the rest of the page.

| File | Cropped from | The detail to borrow |
|---|---|---|
| `detail-electricitymaps-legend.png` | `electricitymaps.jpg` (https://app.electricitymaps.com/map) | Legend as one continuous ramp, quantity name left, unit right, tick values under it. Our score and voltage keys follow this form, without the rounded translucent card. |
| `detail-owid-ranked-list.png` | `owid.jpg` (https://ourworldindata.org/grapher/share-electricity-solar) | Ranked rows with the value right-aligned and a faint bar behind each row proportional to the value; small caps section label above. Model for the ranked table and the substation proxy list. |
| `detail-gem-key-figures.png` | `gem.jpg` (https://globalenergymonitor.org/projects/global-solar-power-tracker/tracker-map/) | Key figures separated by thin vertical rules, number above a short label. Model for the Summary stat row (we set the numbers in ink, serif 40, and drop the rounded tinted container). |
| `detail-felt-legend-popover.png` | `felt.jpg` (https://felt.com) | Map key anatomy: bold title, swatch rows with counts right-aligned, a hairline, then one large figure with a small label. Model for the map key groups and the scorecard hero. |

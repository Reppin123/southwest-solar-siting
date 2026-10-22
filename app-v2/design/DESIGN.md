# Southwest siting dashboard v2: design system

Owner: refs. Status: ready for build-v2. Files: `design/tokens.css` (all variables), `design/specimen.html` (every component rendered with the tokens, real v1 values for SW-NM-00001), `design/specimen-1440.jpg` and `design/specimen-mapview-1440.jpg` (renders of it), `design/refs/` (references with notes in `refs/README.md`), `design/v1/` (v1 evidence screenshots), `design/fonts/` (font files and licences), `design/tools/` (the capture scripts).

Same content, same features, same data as v1. Only the look changes. Where this file and the user's words disagree, the user wins: "a much superior, well crafted and a much more tasteful page. Page which makes the reader want to engage."

---

## 1. Concept

**A survey sheet, not a SaaS panel.** The page should feel like a well-made map plate from a land office or a newspaper graphics desk: one white sheet, a large map, the controls and the result set along its edges as typeset columns divided by hairline rules. Nothing floats in a rounded box except the map key, which is drawn like the key printed in the corner of a paper map. The type does the hierarchy: a serif (Source Serif 4) for the title, the big numbers and anything you read; a sober sans (IBM Plex Sans) with tabular figures for every control, label and number in a table. Colour is spent on the data and almost nowhere else. The candidate sites carry one deep blue ramp, the grid carries one ordered red-brown ramp, substations a grey ramp, land a gold family, and the interface has a single accent taken from the score ramp so that every active control points at the result. Motion is reserved for moving through space: the map flies to a site and the scorecard column slides in beside it. The reader should feel invited to click a dark blue parcel and read its data sheet, the way you would lean over a printed map.

---

## 2. v1 critique: why it reads as "AI slop"

Evidence: `design/v1/*.jpg` were captured on 2026-10-22 from the running v1 at http://localhost:8770/app/ (read-only) with `design/tools/shoot_v1.py`. The full v1 stylesheet is `../app/style.css`.

1. **It is literally the Tailwind palette.** `style.css` uses `#0f172a`, `#475569`, `#64748b`, `#e2e8f0`, `#cbd5e1`, `#f8fafc`, `#f1f5f9`, `#fef3c7`, `#ede9fe`: Tailwind's slate, amber and violet steps, unchanged. The type is the system font stack at 13 px. Nothing about the page was decided; it is the default. (`v1-01-map-1440.jpg`)
2. **Boxes everywhere, all slightly rounded, many with soft shadows.** The basemap switcher is a rounded card with a shadow floating on the map. The scorecard is a 10 px rounded card with a 16 px shadow floating over the map and hiding a third of it. The info modal, the Summary stat tiles, the Summary chart cards, the Sources callouts, the How to Read sections, the glossary, the Deliverables links and the table on Sources are all rounded bordered boxes. (`v1-04-info-modal-1440.jpg`, `v1-05-scorecard-1440.jpg`, `v1-09-summary-1440.jpg`, `../app/screenshots/06_how_to_read_1440.png`)
3. **Pills and chips.** The active tab is a teal-tinted rounded pill. The ranking toggle is a filled teal segmented pill. The state filter is five bordered checkbox chips that wrap so "UT" sits alone on a second line. Scorecard facts are tinted pill badges in four colours. The How to Read table of contents is ten pill links in two rows. (`v1-01-map-1440.jpg`, `../app/screenshots/06_how_to_read_1440.png`)
4. **Circles in boxes.** Every one of the 25 layers has a circled "i" button. Repeated down the rail it reads as decoration. (`v1-02-layer-list-1440.jpg`)
5. **The legend lives in the wrong place.** Each layer's legend is printed under its checkbox in the rail, so the rail is about 2,000 px tall and the key to what you see on the map is often scrolled out of view. The map itself has no key. (`v1-02-layer-list-1440.jpg`, `v1-03-layer-list-lower-1440.jpg`)
6. **Map colours fight each other.** Voltage is a rainbow (grey, green, blue, purple, red) with no order. Red means 500 kV on lines and also "over 2,000 MW queued" on substations. Orange means BLM land and also "500 to 2,000 MW". The candidate sites are a teal carpet with dark outlines that buries the grid; white substation circles with grey rings add speckle everywhere. (`v1-01-map-1440.jpg`)
7. **No typographic hierarchy.** Title 15 px, tabs 13 px, section labels 12 px uppercase grey, legend 11.5 px, notes 11 px: five sizes within 4 px of each other, one weight doing most of the work. The score, the one number that matters, is 30 px bold teal sans next to 13 px grey text. Off-scale values such as 11.5, 13.5 and 650 weight show there was no scale. (`v1-05-scorecard-1440.jpg`)
8. **Uneven spacing.** Paddings of 2, 3, 4, 5, 6, 7, 8, 10, 12, 14, 16 and 18 px all appear in `style.css`. The rail sections, the table bar and the scorecard each use different insets, which is why the page feels loose even though nothing is broken.
9. **Template grids on the secondary pages.** Summary is five identical stat tiles above a 2 x 2 grid of identical chart cards. Deliverables is a 2 x 2 grid of link cards above a table with a "Show on map" button repeated on every row and underlined link text. (`v1-07-deliverables-1440.jpg`, `v1-09-summary-1440.jpg`)
10. **Charts ignore the map's palette.** Summary uses Chart.js default-looking bright blue and orange plus an eight-colour categorical set unrelated to the map, and default boxed legends. (`v1-09-summary-1440.jpg`)
11. **Reading text is set like UI.** How to Read This is 13.5 px sans at a 980 px measure, about 150 characters a line, inside bordered cards. It is the page meant for a newcomer and the hardest to read. (`../app/screenshots/06_how_to_read_1440.png`)
12. **Tinted alert boxes for caveats.** The provisional note on Sources and in the scorecard is a lavender box; the next step is a mint box. Colour fills stand in for hierarchy. (`v1-06-scorecard-lower-1440.jpg`, `../app/screenshots/05_sources_1440.png`)

What v1 gets right and v2 keeps: the map-first layout with the table under it, the dense ranked table with tabular figures, honest captions under every chart, the plain-English copy, and the information in the scorecard.

---

## 3. References

Thirteen full-page captures kept (`design/refs/*.jpg`) plus four detail crops (`design/refs/detail-*.png`: the Electricity Maps legend, the OWID ranked list, the GEM key figures, the Felt legend popover); sources, what to borrow and what to avoid are in `design/refs/README.md`. In short:

- **Open Infrastructure Map**: line width grows with voltage; the map fills the frame.
- **Electricity Maps**: one horizontal ramp with ticks as the legend, docked in a corner.
- **Felt**: serif display with sans UI; a square-cornered ink button; the key as title, swatch rows, hairline.
- **Climate TRACE**: the stat panel hierarchy (huge number, small unit, count, small chart) for the scorecard hero.
- **Transect** and **Paces**: siting-industry content model (Transect) and palette restraint (Paces); Transect's boxed tiles are also the look to avoid.
- **Our World in Data**: map plus ranked list with right-aligned values; serif chart titles, small caps labels.
- **ProPublica**: atlas-style labels in spaced caps and italics; a dated data note.
- **Datawrapper blog**: the editorial page layout for the text tabs (left TOC, right column, full-width hairlines).
- **Global Energy Monitor**: key figures separated by thin rules, not cards.
- **Linear**: density and restraint in a tool.
- **LandGate** and **Interconnection.fyi**: counter-examples (gradient hero, pills, chip rows).

---

## 4. Layout and grid

Base unit 4 px. All spacing from `--s-1` to `--s-8`: 4, 8, 12, 16, 24, 32, 48, 64 px.

### 4.1 Map view (1440 x 900 and 1280 x 800)

```
+--------------------------------------------------------------------------------------------+
| MASTHEAD 56px  title (serif 20) + one-line note (11)   tabs (13, underline)   RANK FOR [Solar|Solar + Data Center] |
+------------------+-------------------------------------------------------+-----------------+
| RAIL 296px       | MAP (fluid)                                           | SHEET 392px     |
| (272 <1340px)    |                                                       | (only when a    |
| scrolls on its   |                                                       |  site is chosen;|
| own              |                                                       |  360 <1340px)   |
|                  |  [map key, bottom-left, 264px]        [+/-, top-right] |                 |
|                  +-------------------------------------------------------+                 |
|                  | TABLE 34vh (min 220px), spans map + sheet columns     |                 |
+------------------+-------------------------------------------------------+-----------------+
```

- The page is one surface (`--paper`). Columns are separated by a 1 px `--rule-strong` vertical rule; sections inside a column by 1 px `--rule`. No backgrounds on panels, no shadows, no rounded containers.
- The **rail** (left) holds, top to bottom: the live readout "Sites shown 25,733 of 25,733", Weights, Filters, Layers. 24 px side padding, 16 px between sections, hairline above each section.
- The **map** takes every remaining pixel. Only three things sit on it: the map key (bottom-left), the zoom buttons (top-right, square 28 px, 1 px `--rule-strong` border, 2 px radius, stacked with no gap) and the scale bar (bottom-right, ink 1 px, 11 px label). The basemap switcher moves into the map key footer. The "Loading data" notice is a single line of 12 px text with a 2 px accent bar under it, centred at the top edge of the map.
- The **scorecard sheet** is a column that opens to the right of the map (the map narrows, it does not get covered), with its own scroll. Closing it returns the width to the map.
- The **table** sits under the map and the sheet. It keeps v1's columns and behaviour.
- Under 1100 px wide: the rail becomes a drawer opened by a "Controls" text button in the masthead; the sheet becomes a full-height overlay on the right edge, 100% wide under 600 px; the table stays under the map. Under 760 px the tabs collapse to a select-style list button showing the current tab name.

### 4.2 Text tabs (Summary, Sources and Limits, Deliverables, How to Read This)

- The rail stays on Summary (its charts follow the weights and filters, as in v1) and is hidden on Sources, Deliverables and How to Read so the page reads as a document. Note for build-v2: v1 shows the rail on every tab; hiding it on the three reading tabs is a layout change, not a feature change, because those pages do not depend on the controls.
- Page column: max 1120 px, centred, 48 px top padding. Page title serif 28, then a one-sentence dek in serif 17 `--ink-2`, then a 1 px ink rule.
- Reading text (How to Read, Sources prose): serif 17/27 (1.6), measure 68ch.
- Every figure or section starts with a 1 px ink top rule, then a serif 17 title, a 12 px muted caption, then the content. This is the newspaper figure convention and it replaces every card.

---

## 5. Typography

| Role | Family | Size / line height | Weight | Notes |
|---|---|---|---|---|
| Scorecard score | Source Serif 4 | 48 / 1 | 600 | tabular |
| Summary stat numbers | Source Serif 4 | 40 / 1 | 600 | tabular |
| Page titles | Source Serif 4 | 28 / 1.15 | 600 | |
| Rail readout number | Source Serif 4 | 28 / 1 | 600 | tabular |
| Masthead title, scorecard place name, page section titles | Source Serif 4 | 20 / 1.15 | 600 | |
| Reading text, figure titles, dek | Source Serif 4 | 17 / 1.6 (titles 1.15) | 400 / 600 | 68ch measure |
| Next-step note, map-key emphasis | Source Serif 4 italic | 15 / 1.45 | 400 | |
| Lead labels, scorecard rank line, table title | IBM Plex Sans / serif for table title | 15 / 1.4 | 400 / 600 | |
| UI body: controls, scorecard values, tabs | IBM Plex Sans | 13 / 1.4 | 400, 500 for active | |
| Table cells, legend rows, captions, hints, meta | IBM Plex Sans | 12 / 1.4 | 400, 500 for site IDs | |
| Section labels (WEIGHTS, FILTERS, MAP KEY), table headers | IBM Plex Sans | 11 / 1.4, uppercase, +0.06em | 600 | the only uppercase text |

- Scale: 11, 12, 13, 15, 17, 20, 28, 40, 48 px. No other sizes. Weights: 400, 500, 600. No bold 700, no 650.
- Numerals: every number in data uses `font-variant-numeric: tabular-nums lining-nums` (`--num`). IBM Plex Sans digits are tabular by default (all digits measured 600 units wide in the shipped files); Source Serif 4 has a `tnum` feature and its default digits are also equal width (529 units). Right-align numeric columns.
- Site IDs (SW-NM-00001) in Plex Sans 500 with +0.02em tracking; no monospace face (keeps to two families).
- Italic only for the next-step note and for water and feature labels in the How to Read map illustration.
- No em dashes anywhere in UI text or copy. Use a colon, a comma or "to" for ranges ("500 to 2,000 MW").

**Fonts and licences.** Both families are under the SIL Open Font License 1.1, which allows self-hosting and bundling. Files (latin subset, woff2) were downloaded on 2026-10-22 from the npm packages `@fontsource/ibm-plex-sans` (400, 500, 600 normal; 400 italic) and `@fontsource-variable/source-serif-4` (variable weight 200 to 900, normal and italic) via jsdelivr, and are in `design/fonts/` with `LICENSE-ibm-plex-sans.txt` and `LICENSE-source-serif-4.txt`. build-v2 copies them into `app-v2/fonts/` (no CDN at runtime). Total about 200 KB.

---

## 6. Palette

All values are in `design/tokens.css`. One value per role. Interface roles:

| Variable | Hex | Role | Contrast |
|---|---|---|---|
| `--paper` | #FFFFFF | the one surface: page, rail, sheet, table | |
| `--paper-sunk` | #F4F3EF | Plain basemap, row hover, table header when sticky over rows | |
| `--ink` | #16181B | primary text, active controls, figure top rules, selected site outline | 17.8:1 |
| `--ink-2` | #3E434A | secondary text, values in lists, captions under figures | 10.0:1 |
| `--muted` | #666B73 | labels, units, counts, notes | 5.3:1 on paper, 4.7:1 on sunk |
| `--rule` | #E3E1DB | hairlines between rows and sections | decorative |
| `--rule-strong` | #C9C6BE | column dividers, control tracks, input borders | decorative |
| `--accent` | #1F5370 | the single UI accent: active tab underline, links, text buttons, focus ring, selected table row bar | 8.3:1 |
| `--accent-wash` | #E9F0F3 | selected table row background only | |
| `--prov` | #5B3F99 | provisional data: map ring, tag text, note rule | 8.0:1 |
| `--warn` | #8A5300 | low queue confidence, soft constraints hit: tag text and rule | 6.3:1 |

The accent equals score step 4 on purpose: the UI's one colour is the colour of a good site.

**Why white and not cream:** the map basemap and the gold BLM land already bring warmth; a tinted page would muddy the land colours and is the "safe beige" the playbook warns against. `--paper-sunk` is warm grey only where something must sit back.

### 6.1 Map colours

Ordered quantities use one hue running light to dark, checked with the dataviz skill's validator (`validate_palette.js --ordinal`, on the Plain basemap surface #F4F3EF): monotone lightness, adjacent steps at least 0.06 apart in OKLCH L, light end at least 2:1 against the surface, hue spread under 40 degrees. Results: score, voltage, substation queue and water stress **all pass**. Lightness carries the order, so the ramps survive colour blindness and greyscale print.

**Candidate sites, by blended score** (thresholds unchanged from v1): under 60 `#80AEBD`, 60 to 70 `#5C93A7`, 70 to 80 `#3B738D`, 80 to 90 `#1F5370`, 90 and over `#0D324E`. Polygon fill opacity 0.78, edge `--site-edge` 0.6 px at 0.6 opacity; points below zoom 7 as in v1, radius 2.2 to 4, with a 0.5 px white stroke so dense clusters separate. **Selected site**: 6 px white line under a 3 px `--ink` line (colour-independent, replaces v1's orange).

**Transmission lines, by voltage** (darker and thicker means higher): under 115 kV `#D3A08C` 0.8 px; 115 to 161 kV `#C27A62` 1.1 px; 230 kV `#A6533F` 1.5 px; 345 kV `#7F2F22` 2.0 px; 500 kV and over `#4F130E` 2.6 px; unknown `#9A9DA3` 0.8 px dashed 2 2. Widths scale by 1.0 at zoom 5 to 1.6 at zoom 10.

**Substations, by queued MW at the POI** (grey ramp; size = kV as in v1): no name-matched queue = white fill with 1 px ink stroke ("unknown, not empty"); under 500 MW `#B0A99E`; 500 to 2,000 MW `#756E64`; over 2,000 MW `#2E2A26`; removed as POI by screening `#D9D6CF` fill and stroke at 0.7 opacity; provisional record = a 2 px `--prov` ring replacing the stroke. Grey keeps substations from competing in hue with the lines they sit on and with the sites.

**Land.** BLM solar-available `#D9A521` fill 0.30, 1 px edge; DRECP Development Focus Area `#C47A1E` fill 0.30; DRECP Variance Land `#B9A15E` fill 0.18 with a 45 degree hatch (riskier, not counted as available). Solar Energy Zones: developable `#8C4A12` 1.6 px outline, fill 0.10; non-developable `#9A9DA3` 1 px dashed outline. Land ownership (fill 0.40, private unshaded), soft tints near the usual US surface-management map colours: BLM `#E6CF7E`, USFS `#9CC08A`, NPS `#B59A74`, DOD `#D69A92`, Tribal `#B9A3D3`, State `#93BFD6`, Other `#CFCBC3`.

**Exclusions.** Hard constraints: solid fill at 0.22 with a 1 px edge of the same colour. Soft constraints (NCAs, monuments and ACECs; wetlands): 45 degree hatch at 0.5 opacity with a dashed 1 px edge, so hard and soft read differently without colour. Wilderness and WSAs `#2F7A3A`; NCAs, monuments and ACECs `#6F8A1F` (soft); critical habitat `#C0632C`; FEMA flood zone A/V `#2A6FB8`; tribal land `#6A4AA0`; military land `#A8343A`; wetlands `#3E9DB0` (soft); slope over 5 percent `#7A5A3C`; urban areas `#4E535A`; National Park Service land `#6B2F5B`.

**Infrastructure.** Power plants by technology (circle 4 px, 0.6 px white stroke): solar `#EDA100`, wind `#1BAF7A`, storage `#4A3AA7`, hydro `#2A78D6`, gas `#EB6834`, coal `#3B3E43`, nuclear `#E87BA4`, geothermal `#E34948`, other `#9A9DA3`. Active BLM solar ROW cases `#B8336A` fill 0.25, edge 1.2 px. Fiber PROXY `#1B8A6B` dashed 4 3, 1.2 px (the dash says "proxy"). Major roads `#6E7178` 0.9 px. Existing data centers (OSM) `#2B3A8C` 7 px square with 1 px white stroke (the only square marker, so it reads as a building). Water stress (fill 0.35): 0 `#D0A37A`, 2 `#BD7D4F`, 3 `#9E5832`, 4 `#76381C`, 5 `#4A1B0D`. State lines `#3A3D42` 1.2 px; county lines `#A9ADB3` 0.5 px.

**Rasters.** GHI and slope are pre-rendered PNGs in `../app/data/overlays/`; their colours are baked in and cannot change without regenerating outside app-v2. Keep v1's legend values for them. (The GHI ramp is red-yellow-blue, which is a diverging scheme on a sequential quantity; noted as a known limit, not fixed here.)

**Honest limits of the categorical sets.** Nine plant types, eight ownership classes and ten exclusion layers cannot all be told apart pairwise under colour-blind simulation; the validator fails them on all-pairs, as it does any set that large. Mitigations, all required: every colour sits next to a text label in the map key; the map tooltip names the category; exclusion layers are separate toggles, usually viewed one or two at a time; hard and soft exclusions differ by hatch; data centres differ by shape.

### 6.2 Basemap

Street: v1's OSM raster, but set `raster-saturation: -0.9`, `raster-contrast: -0.15`, `raster-opacity: 0.85` so it reads as a grey printed base and every data colour stands out. Satellite: `raster-saturation: -0.35`, `raster-brightness-max: 0.85` so the light site colours stay visible. Terrain: `raster-saturation: -0.6`. Plain: `--paper-sunk`. Attribution stays visible (11 px, `--muted`, no box).

### 6.3 Summary charts (Chart.js)

- Defaults: font IBM Plex Sans 12, colour `--muted`; horizontal gridlines only, `--chart-grid` #ECEAE5, 1 px; no vertical grid; no axis border; bars with 2 px corner radius only at the data end, 2 px gap between bars, `maxBarThickness` 28.
- Candidate sites by state: "All candidate sites" `--score-3`, "BLM solar-available" `--blm-available`. The two differ by 37 OKLab units (validator), easily told apart.
- Score distribution: each 5-point bin coloured by the score ramp step it falls in, so the chart is also a legend for the map.
- Queue by state and type (stacked, order fixed): hybrid `#2A78D6`, solar `#EDA100`, storage `#4A3AA7`, wind `#1BAF7A`, gas `#EB6834`, other `#9A9DA3`. The five hues pass the validator on adjacent pairs (worst CVD 9.2, normal vision 27.6); "other" is the neutral fold bucket. Solar and wind sit under 3:1 against white, so the legend and tooltip must name them (they do).
- Substation proxy: single series in `--ink-2`, labels at left in 12 px, value labels at bar ends in 11 px tabular.
- Legends: Chart.js legend replaced by a one-line HTML key above the chart: 8 x 8 px square swatch + 12 px label, 16 px gap. No boxed legend.
- Tooltips: white, 1 px `--rule-strong` border, 2 px radius, no shadow, 12 px, title in 500.

---

## 7. Components

Every component uses only tokens. Rendered in `design/specimen.html`.

**Masthead.** 56 px, 24 px side padding, 1 px `--rule-strong` bottom rule. Left: title in serif 20/600, under it the one-line note in 11 px `--muted`. Centre-left: tabs. Right: "RANK FOR" (11 px caps) and the ranking switch.

**Tabs.** Plain text 13 px `--ink-2`, 24 px apart, full masthead height. Active: `--ink`, weight 500, 2 px `--accent` underline at the bottom edge of the masthead. Hover: `--ink`. No background, no pill. `role="tablist"`, arrow keys move.

**Ranking switch (Solar | Solar + Data Center).** Two adjoining text buttons inside one 1 px `--ink` frame, 2 px radius, 12 px weight 500, 5 x 10 px padding, a 1 px ink divider. Selected: ink fill, white text. It is the only filled control on the page because it changes the whole ranking. `aria-pressed`.

**Rail readout.** "SITES SHOWN" caps label, then the count in serif 28/600 with "of 25,733" in 13 px `--muted`. Updates live with filters (replaces v1's teal "25,733 of 25,733 sites shown").

**Section label.** 11 px uppercase, +0.06em, 600, `--muted`, with an optional right-aligned text button ("Reset") in 12 px `--accent`.

**Slider (weights and filters).** Track 2 px: filled part `--ink`, rest `--rule-strong`. Thumb 12 px ink circle with a 2 px white ring; focus adds `--focus`. Weight rows: grid 76 px label / track / 52 px value, 28 px tall; value "35" in 13 px plus "35%" in 12 px `--muted`. A weight at 0 (data center in Solar mode) shows the label, value and track in `--muted` with a grey thumb, as in v1's disabled state. Filter sliders: label left and value right on one line above the track.

**State filter.** Five 40 px wide text toggles (CA AZ NV NM UT) on one line, 1 px border, 2 px radius, 12 px weight 500. On: ink border, ink text, a 2 px ink underline inside the bottom. Off: `--rule-strong` border, `--muted` text. They never wrap at 272 px rail width.

**Checkbox toggle.** 14 px square, 1.5 px `--ink-2` border, 2 px radius. Checked: ink fill with a white tick. Label 13 px `--ink-2`, 12 px above. Used for filters, layers and "Only sites in map view".

**Layer row.** 26 px tall: checkbox, layer title (13 px; `--ink` when on, `--ink-2` when off), and at the right a "Source" text button in 11 px `--muted` that appears on row hover and keyboard focus and is always visible on touch screens. It opens the same source panel v1's circled "i" opened. Group labels (SCREENING RESULT, GRID, LAND, EXCLUSIONS, INFRASTRUCTURE, REFERENCE, RESOURCE) in the section-label style, 12 px above, 4 px below. **No legends in the rail.** A layer still loading shows "loading" in 11 px `--muted` in place of "Source".

**Map key (the legend).** Bottom-left of the map, 264 px wide, white, 1 px `--rule-strong` border, 2 px radius, no shadow, 12 px padding, max height 60% of the map with its own scroll. Header "MAP KEY" (section label) with a "Hide" text button. It lists **only the layers that are on**, in drawing order (sites first), each as a group: a 12 px weight 500 title, then its key, then a 1 px `--rule` between groups. Key forms:
- ordered ramps (score, voltage, water stress): a row of equal blocks 10 px tall with a 2 px gap and tick labels under them in 11 px `--muted`. Voltage uses line samples whose thickness grows, not blocks.
- substations: 9 px circles with labels on one line, then the provisional ring and "size = kV".
- categories: 8 x 8 swatches (lines as 16 x 2 px samples, dashed where dashed, hatched where hatched) with 12 px labels, two columns when more than four items.
- notes (for example "Queue MW is matched by POI name; 0 means no match, not an empty queue") in 11 px `--muted`, kept from v1 word for word.
Footer: "Base" then Street, Satellite, Terrain, Plain as text buttons; the selected one in `--ink` with a 1 px underline. Collapsed state: a single 28 px row "Map key" + "Show".

**Map tooltip / popup.** White, 1 px `--rule-strong`, 2 px radius, no shadow, 12 px; title in 13 px weight 600; rows as a two-column key/value list with `--muted` keys. Arrow tip kept, same border.

**Scorecard sheet** (the data sheet). Column 392 px, 24 px side padding, scrolls. Top to bottom:
1. Site ID in 12 px 600 `--ink-2` with "Close" text button at right (no "x" glyph).
2. Place name ("Doña Ana County, New Mexico") serif 20/600.
3. Hero row: score in serif 48/600 `--ink`; beside it "Rank 1 of 25,733" 15 px and the pipeline ranks line in 12 px `--muted`; 1 px `--rule` under.
4. Facts and flags: facts are plain 12 px text with an 8 px square swatch in the matching map colour (BLM solar-available in `--blm-available`, SEZ in `--sez-dev`, HIFLD substation in `--ink`). Flags that need care are tags: 1 px border in the flag colour, 2 px radius, 0 x 5 px padding, 12 px weight 500, transparent background (Provisional in `--prov`; Queue data: low confidence in `--warn`). Never filled.
5. "SCORE BY FACTOR (0 TO 100, WEIGHT SHOWN)": rows of label 82 px / weight 28 px right-aligned `--muted` / 4 px bar on a `--rule` track filled with the score-ramp colour of that factor's value / value right-aligned. A factor with weight 0 is drawn entirely in `--muted` with a `--rule-strong` fill.
6. "SITE", "GRID CONNECTION" and "DATA CENTER FIT" (v1's section names), as definition lists: 42% `--muted` keys, values in `--ink` 13 px, secondary detail in 12 px `--muted` on the same line, 1 px `--rule` above each row, 6 px vertical padding.
7. "CONSTRAINTS HIT (SOFT)" as tags (hard in `--ink`, soft in `--warn`).
8. "RECOMMENDED NEXT STEP": serif italic 15 with a 2 px `--accent` left rule and 12 px indent. The provisional explanation uses the same form with a `--prov` rule. No tinted boxes.
9. Actions: primary "Zoom to site" (ink fill), secondary "Open site memo" and others (1 px ink border), 12 px weight 500, 5 x 10 px, 2 px radius, 8 px apart.

**Ranked table.** Bar above: table title in serif 15/600 ("Ranked sites, Solar"), the "Only sites in map view" checkbox, the count in 12 px `--muted`, then at right "Export CSV" as a secondary button. Header: 11 px caps 600 `--muted`, 1 px `--ink` rule under it, sticky on `--paper`; the sorted column in `--ink` with an arrow. Rows 28 px, 12 px, 1 px `--rule` under each, cells padded 10 px; numbers right-aligned tabular; site ID in 500. Score cell: 8 px square swatch of the score colour then the value. Hover `--paper-sunk`. Selected: `--accent-wash` with a 3 px `--accent` bar at the left edge (inset shadow), scrolled into view. No zebra stripes, no vertical rules. Column groups (Site, Grid, Land, Scores) may carry a quiet 11 px group label above the header if the build has room; optional.

**Buttons.** Primary: ink fill, white 12 px 500 text. Secondary: 1 px ink border, transparent. Text button: `--accent`, underline on hover. All 2 px radius, 28 px tall. Nothing else looks clickable.

**Badges ("provisional" anywhere).** The tag form above. In the table, a provisional site shows a 6 px `--prov` ring after its substation name with `title="provisional substation record"`.

**Modal (layer source).** Centered, 560 px, white, 1 px `--rule-strong` border, 2 px radius, a backdrop of `rgba(22,24,27,0.28)`, no shadow. Title serif 20, then the key/value list. "Close" text button top right; Esc closes; focus is trapped and returned.

**Summary stat row.** Five figures in one row: serif 40/600 number over a 12 px `--muted` label, separated by 1 px `--rule` vertical lines, 24 px padding; a 1 px ink rule above the row. No tiles.

**Deliverables.** A ruled list, not cards: each item one row with its kind in the section-label style (DOWNLOAD, DOCUMENT, APPENDIX), the title as a link in 15 px `--ink` with an underline on hover, and the file type and size in 12 px `--muted` if known. Site memos: a ruled table (Memo, Site, Solar rank, DC rank) where the memo title is the link and "Show on map" is a text button in `--accent` at the row end.

**Sources and Limits.** The provisional data note as serif 17 text under a 2 px `--prov` left rule. "Limits to know up front" and "Screening limits" as ruled lists (1 px `--rule` between items, no bullets boxes). Datasets table in the ranked-table style.

---

## 8. Motion

- Map fly-to on selecting a site from the table or Deliverables: `map.flyTo` 900 ms, MapLibre's default curve. Under `prefers-reduced-motion`, use `jumpTo`.
- Scorecard column: opens by growing the grid column from 0 to 392 px while its content fades in from 0 to 1 opacity and 8 px x-offset, 240 ms `--ease-out`; the map calls `resize()` at the end. Close reverses at 180 ms.
- Map key hide and show: height and opacity, 240 ms.
- Hover on rows, tabs and buttons: colour and background, 140 ms.
- Nothing else moves: no loading spinners (a 2 px accent progress line under the masthead while data loads), no animated numbers, no chart entrance animations (`animation: false` in Chart.js).
- `prefers-reduced-motion: reduce` sets every duration token to 0 ms.

---

## 9. Wireframes

### 9.1 Map (1440 x 900, no site selected)

```
 0                     296                                                                          1440
 +-----------------------------------------------------------------------------------------------------+
 | Southwest Solar and Data Center Siting   Map  Summary  Sources and Limits  Deliverables  How to Read This   RANK FOR [#Solar#|Solar + Data Center] |
 | CA, AZ, NV, NM, UT. Screening study ...  ---                                                         |  56px, serif 20 title; accent underline under "Map"
 +---------------------+-------------------------------------------------------------------------------+
 | SITES SHOWN         |                                                                       [+]     |
 | 25,733 of 25,733    |                     (map: grey street base, blue site parcels,        [-]     |  readout: serif 28
 |---------------------|                      red-brown lines by kV, grey substations)                 |
 | WEIGHTS       Reset |                                                                               |
 | Grid    ---o---  35 |                                                                               |  2px ink track, 12px thumb
 | Land    --o----  30 |                                                                               |
 | Sun     -o-----  20 |                                                                               |
 | Permitting o---- 15 |                                                                               |
 | Data center o     0 |  (muted)                                                                      |
 | Solar ranking: no data center term by default...                                                    |
 |---------------------| +-MAP KEY----------- Hide -+                                                   |
 | FILTERS             | | Candidate sites, by score |                                                  |
 | [CA][AZ][NV][NM][UT]| | [][][][][]                |                                                  |  ramp blocks + ticks
 | Min acres     600 ac| | <60 60  70  80  90+       |                                                  |
 | o----------------   | |---------------------------|                                                  |
 | Max dist.     30 km | | Transmission, kV          |                                                  |
 | ----------------o   | | -- -- == == ##            |                                                  |  thickness grows
 | [ ] BLM available   | | <115 115 230 345 500+     |                                                  |
 | [ ] Hide provisional| |---------------------------|                                                  |
 | [ ] High queue conf.| | Substations, queued MW    |                                                  |
 |---------------------| | o unknown o<500 o500 o2k  |                                                  |
 | LAYERS              | |---------------------------|                                  100 mi |----|  |
 | SCREENING RESULT    | | Base Street Satellite ... |                         (c) OpenStreetMap ...    |
 | [x] Candidate sites | +---------------------------+                                                  |
 | GRID                +-------------------------------------------------------------------------------+
 | [x] Transmission    | Ranked sites, Solar   [x] Only sites in map view   24,584 sites ...   [Export CSV] |  serif 15 title
 | [x] Substations  Source | RANK  SCORE  SITE         STATE COUNTY   ACRES OWNER ... SUBSTATION  KV  SUB KM  GHI |  11px caps, ink rule under
 | LAND                |    1  # 95.9 SW-NM-00001  NM    Doña Ana  3,697 BLM   ... AFTON      345   0.5  6.00 |  28px rows, hairlines
 | [x] BLM solar-avail.|    2  # 95.1 SW-NM-00002  NM    Doña Ana  3,438 BLM   ... AFTON      345   1.6  6.00 |
 | ... (scrolls)       |    3  # 95.0 SW-NM-00003  NM    Doña Ana  3,933 BLM   ... AFTON      345   2.5  6.01 |
 +---------------------+-------------------------------------------------------------------------------+
```

Annotations: the rail is about 1,000 px tall instead of v1's 2,000 because legends moved to the map key. The only filled control is the ranking switch. Every number column is right-aligned tabular. The map key shows only layers that are on.

### 9.2 Scorecard open (site selected from the table or the map)

```
 +---------------------+---------------------------------------------------+---------------------------+
 | (rail as above)     |                                           [+][-]  | SW-NM-00001         Close |  12px 600
 |                     |       map has flown to the site (900 ms);         | Doña Ana County,          |  serif 20
 |                     |       selected parcel: white halo + 3px ink line  | New Mexico                |
 |                     |                                                   | 95.9   Rank 1 of 25,733   |  serif 48 + 15px
 |                     |              .---.                                |        Pipeline: solar #1 |  12px muted
 |                     |             | ### |  <- selected                   |        (95.9), Solar + DC |
 |                     |              '---'                                |        #1 (88.2)          |
 |                     |                                                   |---------------------------|
 |                     |                                                   | # BLM solar-available     |  swatch + text
 |                     |                                                   | # SEZ: Afton  # HIFLD sub.|
 |                     |                                                   | [Queue data: low conf.]   |  outlined tag, --warn
 |                     |                                                   | SCORE BY FACTOR           |
 |                     |                                                   | Grid        35 ======  96 |  4px bars, score colours
 |                     |                                                   | Land        30 ======  97 |
 |                     |                                                   | Sun         20 ======= 100|
 |                     |                                                   | Permitting  15 =====   90 |
 |                     | +-MAP KEY---+                                     | Data center  0 ---     46 |  muted (weight 0)
 |                     | | ...       |                                     | SITE                      |
 |                     | +-----------+                                     | Acres       3,697 ac  ... |  ruled key/value
 |                     +---------------------------------------------------+ Surface owner   BLM      |
 |                     | Ranked sites ... row 1 highlighted: accent bar +  | BLM status  Available ... |
 |                     | wash; table spans map + sheet width               | ... GRID, DATA CENTER FIT |
 |                     |  > 1  # 95.9 SW-NM-00001 ...                       | RECOMMENDED NEXT STEP     |
 |                     |    2  # 95.1 SW-NM-00002 ...                       | | Request a pre-applica-  |  serif italic, accent rule
 |                     |                                                   | | tion meeting ...        |
 |                     |                                                   | [Zoom to site] [Open memo]|
 +---------------------+---------------------------------------------------+---------------------------+
                         ^ map narrows from 1144 to 752 px; nothing covers it          392px column, own scroll
```

Annotations: the sheet is a column with a 1 px `--rule-strong` left rule, not a floating card. Every v1 scorecard field appears in the same order. The table row and the map parcel are selected together; Esc or "Close" closes and returns the width to the map.

### 9.3 How to Read This

```
 +-----------------------------------------------------------------------------------------------------+
 | masthead (rail hidden on this tab)                                       ---- under "How to Read This" |
 +-----------------------------------------------------------------------------------------------------+
 |            (centred page, max 1120px)                                                               |
 |   How to Read This                                                         serif 28/600             |
 |   A plain-English guide to this dashboard: what it is, how to read the map, how to use it,          |
 |   how it was made and what it cannot tell you.                             serif 17 ink-2 (dek)     |
 |   ________________________________________________________________________________________ 1px ink  |
 |                                                                                                     |
 |   ON THIS PAGE            |  1  What this is                                serif 20/600            |
 |   1  What this is         |  This dashboard helps you find the best places in California, Arizona,  |
 |   2  What was asked       |  Nevada, New Mexico and Utah for a large solar farm (100 MW to 1 GW),   |  serif 17/27,
 |   3  What makes a good    |  and possibly a data center next to it, before you spend real money...  |  68ch measure
 |      site                 |  ___________________________________________________________ 1px rule   |
 |   4  How to read the map  |  2  What was asked                                                       |
 |   5  How to use it, step  |  The request, in short:                                                 |
 |      by step              |  - Look at the electric grid and substations ...   (ruled list)        |
 |   6  How a score is made  |  ...                                                                    |
 |   7  How it was prepared  |  4  How to read the map                                                 |
 |   8  Limitations          |  Candidate sites      [][][][][]  <60 ... 90+    (real map-key rows,    |
 |   9  What to do next      |  Transmission, kV     -- -- == == ##               same component as    |
 |   10 Glossary             |  Substations          o o o o  (o) provisional     the map key)         |
 |                           |  +------------------------------------+                                 |
 |   (sticky, 12px numbers   |  | small SVG: a dark blue parcel near |  "What to look for: dark blue   |
 |    muted, 13px titles;    |  | a thick dark line and a dark       |   sites next to a thick, dark   |
 |    current section in ink |  | substation, on gold BLM land"      |   line ..." serif 17            |
 |    with accent bar)       |  +------------------------------------+   (figure: 1px ink top rule,   |
 |                           |                                            no tinted box)               |
 |                           |  10 Glossary                                                            |
 |                           |  GHI          Global horizontal irradiance ...   (two-column definition |
 |                           |  POI          Point of interconnection ...         list, ruled rows)     |
 +-----------------------------------------------------------------------------------------------------+
   240px TOC column + 32px gap + reading column (68ch)
```

Annotations: the ten sections, their order and their plain-English text stay as in v1; only the setting changes. The TOC is a quiet numbered list, not pills, and section headings carry the number in `--muted` before the title, set in the same size (no "01 //" decoration). The map-key illustrations reuse the map key component so the guide and the map can never disagree.

**Colour words in the guide must change with the colours.** v1's guide text names colours that v2 replaces. build-v2 must update these phrases (meaning unchanged):

| v1 wording (in `../app/app.js`, guide section 4 and the "What to look for" figure) | v2 wording |
|---|---|
| "Darker teal = higher score" | "Darker blue = higher score" |
| "Teal dots when zoomed out, land shapes when zoomed in" | "Blue dots when zoomed out, land shapes when zoomed in" |
| "An orange outline marks the site you clicked" | "A black outline with a white halo marks the site you clicked" |
| "Lines: transmission lines, coloured by voltage" | "Lines: transmission lines; thicker and darker means higher voltage" |
| "(the red lines: the biggest highways of the grid)" | "(the thickest, darkest lines: the biggest highways of the grid)" |
| "Yellow: under 500 MW of projects waiting to connect there" | "Light grey: under 500 MW of projects waiting to connect there" |
| "Orange: 500 to 2,000 MW waiting" | "Mid grey: 500 to 2,000 MW waiting" |
| "Red dots: over 2,000 MW waiting" / "Red substations are crowded" | "Near-black dots: over 2,000 MW waiting" / "Near-black substations are crowded" |
| "White: we could not match any queue records to it" / "White ones need a phone call to the utility to find out" | unchanged (white still means unknown) |
| "Purple ring: provisional record" | "Violet ring: provisional record" |
| "Mustard areas: BLM solar-available land" | "Gold areas: BLM solar-available land" |
| "dark teal sites close to a big line (purple or red) and a yellow or orange substation, ideally sitting on mustard (BLM solar-available) land" | "dark blue sites close to a thick, dark line and a light or mid grey substation, ideally sitting on gold (BLM solar-available) land" |

The guide's swatches must be drawn from the tokens too (v1 builds them from `layers.json` colours and hard-coded hexes such as `#7c3aed`), so the words and swatches match the map.

---

## 10. Implementation notes for build-v2

- Link `design/tokens.css` (or copy it to the app root with the font URLs pointing at `fonts/`). Use only its variables; if a role is missing, add it to tokens.css rather than a raw hex in styles.css.
- Map paint cannot read CSS variables directly. At boot read them once: `const tok = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();` and build the MapLibre paint and the Chart.js colours from `tok("--score-1")` and so on.
- `layers.json` legend colours come from v1's data. In v2, override them by layer id and legend label with the token colours in section 6.1 (for example `transmission_lines` "500+ kV" uses `--kv-500`); keep the labels and order. Rasters keep their data colours.
- The circle "i" becomes the "Source" text button; the basemap radios move into the map key footer; the scorecard close "x" becomes "Close".
- Check before shipping: no `border-radius` above 2 px; no `box-shadow` except focus rings; no hex outside tokens.css; no em dash in any visible string (`document.body.innerText.includes("\u2014")` is false); fonts load (no fallback); every number column right-aligned with tabular figures.

---

## 11. How this was checked

- References: captured live on 2026-10-22 with `design/tools/shoot.py`; I looked at each image and dropped captures that were blocked, broken or off topic (Reuters, EIA Atlas, Stripe Press, Berkeley Lab, the GEM integrated tracker page, The Pudding, Rest of World).
- v1: captured live with `design/tools/shoot_v1.py` from the running v1 (read-only), plus v1's own screenshots in `../app/screenshots/`.
- Ramps: validated with the dataviz skill's `validate_palette.js` as described in section 6.1; the queue-type order was validated on adjacent pairs; categorical map sets fail all-pairs and are mitigated as stated.
- Text contrast: computed with the WCAG formula for every interface colour against `--paper` and `--paper-sunk` (table in section 6).
- Tokens and components: `design/specimen.html` served on port 4100 and rendered with `design/tools/shoot_specimen.py`: all five font faces load, no console errors, no failed requests, no em dashes. Output in `design/specimen-1440.jpg` and `design/specimen-mapview-1440.jpg`.

# Marche regional profile, Phase B: pages and design

Date: 2026-10-13. Status: approved in brainstorming, waiting for the implementation plan.

Phase A built the semantic model, its checks and one model check page ([Phase A spec](2026-10-12-marche-regional-profile-report-design.md), [Phase A plan](../plans/2026-10-12-marche-regional-profile-phase-a.md)). Phase B builds the report on top of it: the theme, the navigation, the eight pages, the drill-through and tooltip pages, the exports and the READMEs.

Mockups: the "Marche regional profile — Phase B pages" design canvas (private claude.ai artifact `RUxTj3aGs73Aes1T3vn3Gu`). Rows 2 and 3 of the canvas are the approved design; row 1 holds the rejected directions A, B and C. The mockups use real values from the model's sources, so they double as reference values.

## Decisions

| Topic | Decision |
|---|---|
| Visual direction | "D": a story column on the left (editorial, from direction B) and a dashboard on the right (cards and charts, from direction C), split at the page centre |
| Grid | 8 pt: every size, gap and padding is a multiple of 8 px |
| Font | Segoe UI only, weights 400 and 600 |
| Palette | Three colours (base, text, accent) plus tints of the text colour. Accent: Marche green |
| Accent rule | The accent marks the focus region and one key phrase per page, nothing else |
| Accessibility | Markers and line styles tell series apart; values are written on the chart; text at least 14 px; contrast checked (see Accessibility) |
| Province map | An SVG drawn by a DAX measure, shown in an Image visual. Not Azure Maps: Microsoft documents that it is not exported to PDF, and the PDF and PNG files are the main distribution |
| Photos | Wikimedia Commons, CC0 or CC BY only, credited on About. Overview: Tempio del Valadier. Education: Urbino. About: Spiaggia delle Due Sorelle |
| Authoring | Mixed. Claude writes the PBIR JSON for the theme, the navigation and the page layout, with every visual placed and bound to its fields. The user refines the visuals in Power BI Desktop |
| Best Practice Analyzer | In the plan, timeboxed to 30 minutes (Phase A Task 18) |

## Visual system

### Page grid

Every page is 1280 × 720 px.

| Zone | x | Width | Content |
|---|---|---|---|
| Navigation | 0 | 192 | Text-colour background, page navigator, region name, "Data up to …" |
| Story | 192 | 448 | Base background, padding 32: eyebrow, headline, one paragraph, one story visual or photo, source line |
| Dashboard | 640 | 640 | Surface background (`#ECEEEA`), 1 px rule on its left edge, padding 32: controls, cards and charts on base-colour cards with 8 px corners |

The split at x = 640 is the page centre. Cards inside the dashboard use gaps of 24 px between rows and 16 or 24 px between columns.

### Colour

| Token | Hex | Use | Contrast on base |
|---|---|---|---|
| Base | `#F5F6F3` | Page ground, cards | — |
| Text | `#15201A` | Text, numbers, navigation background | 15.5 : 1 |
| Accent | `#00753A` | Focus region, one key phrase per page | 5.4 : 1 |
| Muted (text tint) | `#4F5A53` | Labels, axes, captions | 6.6 : 1 |
| Benchmark grey (text tint) | `#6B746E` | Lines and bars of other areas (graphics only, not text) | 4.4 : 1 |
| Surface (text tint) | `#ECEEEA` | Dashboard half | — |
| Rule (text tint) | `#C9CEC9` | Card borders, dividers | decorative |
| Accent tints | `#D0E3D7`, `#7AB696`, `#4A9C72` | Map classes, highlighted table column | text colour on each ≥ 5 : 1 |

Grey tints are the text colour mixed into the base, so they are not extra colours. The accent can be swapped for another focus area: azzurro `#0062B8` (5.6 : 1) or tricolour red `#C8102E` (5.4 : 1). Yellow and white cannot carry text on this base.

### Type

| Role | px | pt in Power BI | Weight |
|---|---|---|---|
| Headline | 40 / 48 line | 30 | 600 |
| KPI value | 32 / 40 | 24 | 600 |
| Region name in navigation | 24 / 32 | 18 | 600 |
| Body, card titles | 16 / 24 | 12 | 400, 600 for titles |
| Labels, axes, legends, table cells, navigation | 14 / 24 | 10.5 | 400 |

Nothing is smaller than 14 px.

### Encoding of areas

| Area | Line | Marker | Bar |
|---|---|---|---|
| Focus region | accent, solid, 3 px | filled circle | accent, solid; bold label |
| Italy | grey, dashed 6-4 | hollow square | grey, outlined |
| EU-27 | grey, dotted 2-4 | filled triangle | grey, outlined |
| Peer regions | grey, solid | hollow circle | grey, solid |
| Provinces (index chart) | grey, solid | one shape each: circle, square, triangle, diamond, cross | — |

Line charts show the value at the end of each line, with the area name. Bar charts show the value on every bar.

## Accessibility

1. Body 16 px (12 pt), labels and axes 14 px. Nothing smaller.
2. Text contrast at least 4.5 : 1; lines, bars and markers at least 3 : 1.
3. A marker on every point. When five or more lines share a chart, a marker every third year.
4. Values are written on bars and at line ends, so no legend lookup is needed.
5. The map prints each province's value, and a table next to it repeats the data.
6. Every visual has a title that says what and when, and alt text that names the chart and what it compares. The values themselves are written on the chart (rule 4).
7. Tab order follows reading order: navigation, story, controls, visuals. Buttons are 40 px tall.
8. No red against green. Gaps carry a sign and a word ("+1.9 pp vs Italy").
9. A tooltip is never the only place a number appears.

## Pages

Every page has the navigation, an eyebrow with the page name, a headline whose last words are in the accent, a short paragraph and a source line. Headlines and paragraphs are DAX text measures (see Model additions). Values below are those of the mockups.

### 1 · Overview

- Story: headline "An older, smaller region with **fewer firms**"; paragraph with the population trend since 2013, the share aged 65+ and the change in active companies since March 2009; photo (Tempio del Valadier).
- Dashboard: "Compare with" buttons (country, EU, peers; the country button shows the country's name), driven by the `Compare to` calculation group; six KPI cards in a 3 × 2 grid (population and 5-year change, share aged 65+, crude death rate, unemployment rate, GDP per inhabitant, active companies); two line charts with markers: population on 1 January from the first year of `demo_r_pjangrp3` (2014) to the latest, active companies in December 2009–2024.

### 2 · Population & Health

- Story: headline "One resident in four is **65 or over**"; pyramid-year slicer; line chart of the crude death rate 2019–2024, Marche against Italy and EU.
- Dashboard: age pyramid of the focus region (men left, women right, five-year bands, bands aged 65+ in the accent); ranked bars of the share aged 65+ (focus, peers, Italy, EU).

### 3 · Economy & Labour

- Story: headline "GDP per inhabitant is **€3,200 below Italy**"; ranked bars of GDP per inhabitant (latest common year).
- Dashboard: legend row with the area encoding; line chart of GDP per inhabitant 2009–2024; line chart of the unemployment rate 2009–2025; both with Marche, Italy and EU.

### 4 · Education

- Story: headline "Fewer university students than **every peer region**"; photo (Urbino).
- Dashboard: ISCED level buttons (All, 0–3, 4, 5–8); butterfly chart of students enrolled by level and sex (women left, men right, tertiary levels in the accent); ranked bars of tertiary students per 1,000 residents.

### 5 · Provinces

- Story: headline "Macerata and Fermo have the **most firms per resident**"; the `Province indicator` field parameter as five buttons.
- Dashboard: the SVG map (four classes: the three accent tints and the accent; name and value on each province; legend) with the selected indicator; a table of the five indicators by province with the selected column highlighted; the hint "Right-click a province › Drill through › Province detail".

### 6 · Business deep dive

- Story: headline "Shops, farms and factories shrink; **services grow**"; eyebrow states "Marche only"; line chart of active companies by province, December 2009 = 100, one marker shape per province.
- Dashboard: actual (last 24 months) and 12-month SARIMA forecast with the 95 % interval, in text colour and grey (the accent belongs to the headline here); diverging bars of the change by ATECO section 2009–2024 for the ten largest sections, growing sections in the accent; columns of the seasonal effect by calendar month; bars of the holdout MAPE of SARIMA, naive and seasonal naive.

### 7 · Benchmark

- Story: headline "Mid-table, but **last for students**"; dot plot of the focus region's position among peers, Italy and EU for six indicators (lowest left, highest right).
- Dashboard: `Compare to` buttons Values / vs Italy / vs EU / vs Peers avg; matrix of areas × indicators with a year row, the focus row highlighted in an accent tint, and a final row "Marche rank of 6"; footnote on the rank direction (1 = highest) and the common-year rule.

### 8 · About

- Story: headline "How this report is **built and checked**"; sources, limits, refresh instructions, link to the repository, photo credits.
- Dashboard: reconciliation, 12 checkpoints in two columns of six, each with value and a "✓ Match" or "✗ Differs" status (icon and word); freshness, the latest period per source; the note on Eurostat flags in tooltips; photo strip (Spiaggia delle Due Sorelle, 576 × 160). The canvas shows the reconciliation in one column and no photo: the two columns make room for the photo, and this spec wins.

### Province detail (drill-through, hidden from navigation)

Same grid. Story: province name, headline on its most distinctive indicator, back button. Dashboard: the five `Province indicator` values as cards with the regional value beside each; population on 1 January and active companies index (2009 = 100) for the province against the region; change by ATECO section for the province.

### Tooltip pages (hidden)

- **Area tooltip**: indicator value, year, gap to Italy, Eurostat flag in words (provisional, estimated, break in series).
- **Province tooltip**: the five indicators of the province.

Both use the theme and the 14 px minimum.

## Photos

| Slot | Photo | Author | Licence | Source |
|---|---|---|---|---|
| Overview, story column | Tempio del Valadier dall'eremo | Kimahri88 | CC0 | https://commons.wikimedia.org/wiki/File:Tempio_del_Valadier_dall%27eremo.jpg |
| Education, story column | Panorama (Urbino) | Fabio Poggi | CC BY 3.0 | https://commons.wikimedia.org/wiki/File:Panorama_(Urbino)_-_panoramio.jpg |
| About, dashboard strip | Spiaggia due sorelle | Gaspa | CC BY 2.0 | https://commons.wikimedia.org/wiki/File:Spiaggia_due_sorelle.jpg |

Only Wikimedia Commons was searched: Unsplash and Pixabay refuse automated access. CC BY-SA was excluded so the report does not inherit a share-alike licence.

Each image is cropped to its slot (384 px wide in the story column), saved as JPEG under 300 KB, stored in the report's `RegisteredResources` and credited on About and in `powerbi/sources.md` (author, licence, link). Each image has alt text.

## Authoring

| Who | What |
|---|---|
| Claude, in PBIR JSON (Desktop closed) | Theme file and its registration; pages, sizes, order, visibility and drill-through settings; navigation (page navigator); background shapes for the three zones; every visual placed on the grid and bound to its measures and fields; titles, alt text and tab order; images |
| User, in Power BI Desktop | Formatting the theme cannot set: per-series marker shapes and line styles, data labels, conditional formatting, interactions; a visual check of each page against the canvas; then Save |

After each Desktop session the changed PBIR files are committed. Claude edits PBIR and TMDL only while Desktop is closed.

The theme JSON sets: the three colours and their tints (`dataColors` starts with the accent and the benchmark grey), the base background, Segoe UI with the sizes above, markers on by default for line charts, data labels on by default for bar charts, 8 px card corners.

## Model additions

New measures, in the existing `_Measures` table and display folders, each with a description:
- **Headline and story measures**, two per page (headline lead, headline accent) plus one paragraph. Each states its claim only when the data support it, and otherwise returns a neutral title (the page name and the focus region). The rule for each claim is written in the measure's description.
- **Map SVG**: builds the SVG from the province shapes and the selected `Province indicator` (classes, labels, legend); data category Image URL.
- **Signed measures for the pyramid and the butterfly chart**: men as negative values, displayed without the sign through the format string.
- **Benchmark helpers**: the focus region's rank per indicator for the "rank of 6" row, and the position (0–1 between the lowest and highest area) for the dot plot.
- **Business helpers**: province index (December 2009 = 100), change by ATECO section, seasonal effect.

New data from `marche-stats export-powerbi`, read through `RepoRawBase` like the Phase A files:
- `powerbi/data/province_shapes.csv`: NUTS 3 code and SVG path, projected and simplified from `data/raw/marche_nuts3.geojson` into a 400 × 400 box;
- `powerbi/data/seasonality.csv`: calendar month and the average STL seasonal effect.

`check-sources` picks up the new files from the TMDL without changes.

## Checks

1. **pytest** for the two new export tables, in the style of the current suite: five shapes with valid paths inside the box; twelve months whose effects sum to about zero.
2. **Static report tests** (`tests/test_powerbi_report.py`) on the PBIR files: page list, order and size; the navigator on every visible page; every visual inside the page and on the 8 px grid; every visual with a title or alt text; theme colours limited to the palette; no font size under 10.5 pt.
3. **Best Practice Analyzer**, timeboxed to 30 minutes: Tabular Editor 2 on the TMDL folder, in CI if it loads, otherwise a note in `powerbi/README.md`.
4. **User, after refresh and refinement**: each page compared with its canvas artboard; reconciliation 12/12 ✓; the headline claims and the values in this spec still match the data.

## Delivery

- The report pages in `powerbi/marche-regional-profile.Report/`; the model check page from Phase A stays as a hidden page.
- `powerbi/exports/marche-regional-profile.pdf`, exported from Desktop by the user.
- One PNG per page from that PDF: a new CLI step `marche-stats export-pngs` using `pypdfium2` (a new dependency).
- `powerbi/README.md`: pages with screenshots, the visual system, accessibility, how the map works, refresh.
- Root `README.md`: the "Power BI report" section with the Overview image, the PDF link and "What this demonstrates".

## Risks to check in the plan

- Card visuals: whether a text measure wraps over several lines in the story column. Fallback: a text box with static text and the numbers as dynamic values.
- Dot plot: built as a scatter chart with one series per area role. Fallback: the matrix alone.
- Image visual with a measure-driven SVG: size limit of the URL and rendering in the PDF export.
- Page navigator: whether its states can be styled to the navigation mockup. Fallback: buttons with page navigation actions.

## Out of scope

- Mobile layout (not supported by Publish to web).
- Everything listed as out of scope in the Phase A spec.

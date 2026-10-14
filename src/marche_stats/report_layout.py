"""Layout of the report pages: what goes where, in px on the 8 px grid.

Zones (Phase B spec, Visual system): navigation 0-192, story 192-640, dashboard 640-1280.
`marche-stats scaffold-report` writes each page once; the formatting a theme cannot set is
done in Power BI Desktop, and Desktop's saved files are then the source of truth.
"""

from __future__ import annotations

from marche_stats.pbir import (
    C,
    Field,
    M,
    Page,
    Visual,
    field_expr,
    in_filter,
    integer,
    literal,
    solid,
)

ACCENT, TEXT, MUTED = "#00753A", "#15201A", "#4F5A53"
EVERY = {"id": "default"}  # the "All" series selector; shapes and new cards read it
BASE, SURFACE, RULE = "#F5F6F3", "#ECEEEA", "#C9CEC9"
NAVIGATOR_TYPE = "pageNavigator"

STORY_X, STORY_W = 224, 384
DASH_X, DASH_W = 672, 576
HALF_W, RIGHT_X = 280, 968
THIRD_W, THIRDS = 176, (672, 872, 1072)
SLOT_Y, SLOT_H = 344, 304
HEADLINE_PT = 27  # 30 pt did not fit the Overview headline in Desktop
KPI_Y, KPI_H, GAP_H = 80, 88, 64  # a gap line needs two lines of 10.5 pt
CHART_Y, CHART_H = 400, 288

FOCUS = in_filter(C("Geo", "Role"), ["Focus"])
AREAS = in_filter(C("Geo", "Role"), ["Focus", "Peer", "Country", "EU"])
LINES = in_filter(C("Geo", "Role"), ["Focus", "Country", "EU"])
PROVINCES = in_filter(C("Geo", "Role"), ["Province"])


def shape(key: str, x: int, y: int, w: int, h: int, color: str) -> Visual:
    """Decorative rectangle. Desktop ignores a fill colour without the "All" selector."""
    return Visual(
        key,
        "shape",
        x,
        y,
        w,
        h,
        objects={
            "shape": [{"properties": {"tileShape": literal("rectangle")}}],
            "fill": [
                {"properties": {"show": literal(True)}},
                {"properties": {"fillColor": solid(color)}, "selector": EVERY},
            ],
            "outline": [{"properties": {"show": literal(False)}}],
        },
    )


def textbox(
    key: str, x: int, y: int, w: int, h: int, lines: list[str] | str, color: str = MUTED
) -> Visual:
    """Static text, 10.5 pt. A line that starts with '# ' is a bold heading."""
    paragraphs = []
    for line in [lines] if isinstance(lines, str) else lines:
        bold = line.startswith("# ")
        style = {
            "fontFamily": "Segoe UI Semibold" if bold else "Segoe UI",
            "fontSize": "10.5pt",
            "color": TEXT if bold else color,
        }
        paragraphs.append({"textRuns": [{"value": line.removeprefix("# "), "textStyle": style}]})
    return Visual(
        key,
        "textbox",
        x,
        y,
        w,
        h,
        objects={"general": [{"properties": {"paragraphs": paragraphs}}]},
    )


def card(
    key: str,
    x: int,
    y: int,
    w: int,
    h: int,
    measure: str,
    size: float = 12,
    color: str = TEXT,
    title: str | None = None,
    alt: str | Field | None = None,
    filters: tuple[dict, ...] = (),
    font: str | None = None,
    background: bool = True,
    precision: int | None = None,
) -> Visual:
    """Classic card showing one measure (a number, or a text measure for the story).

    alt is required (pbir raises without it): a literal, or M(<text measure>) to have the
    shown text read aloud. font None keeps the theme's Segoe UI Semibold. background False
    drops the theme's light background, for cards on the dark navigation rail. precision
    fixes the decimals, so the automatic display units keep the value readable (1.48M).
    """
    labels = {"color": solid(color), "fontSize": literal(size)}
    if font:
        labels["fontFamily"] = literal(font)
    if precision is not None:
        labels["labelPrecision"] = integer(precision)
    container = None
    if not background:
        container = {"background": [{"properties": {"show": literal(False)}}]}
    return Visual(
        key,
        "card",
        x,
        y,
        w,
        h,
        roles={"Values": [M(measure)]},
        title=title,
        alt=alt,
        objects={
            "labels": [{"properties": labels}],
            "categoryLabels": [{"properties": {"show": literal(False)}}],
        },
        filters=list(filters),
        container=container,
    )


def text_card(
    key: str,
    x: int,
    y: int,
    w: int,
    h: int,
    measure: str,
    alt: str | Field,
    filters: tuple[dict, ...] = (),
) -> Visual:
    """New card (cardVisual) showing a text measure in Segoe UI 10.5 pt that wraps.

    The classic card keeps its text on one line and cuts it; the new card wraps it. Object
    and property names follow the cardVisual section of the report theme schema. The new
    card reads them per series: the selector {"id": "default"} is its "All" series, and
    without it Desktop ignores them. Border, padding and title are off, so the text has
    the whole box.
    """
    value = {
        "fontSize": literal(10.5),
        "fontColor": solid(TEXT),
        "fontFamily": literal("Segoe UI"),
        "textWrap": literal(True),
    }
    return Visual(
        key,
        "cardVisual",
        x,
        y,
        w,
        h,
        roles={"Data": [M(measure)]},
        alt=alt,
        objects={
            "value": [{"properties": value, "selector": EVERY}],
            "label": [{"properties": {"show": literal(False)}, "selector": EVERY}],
            "outline": [{"properties": {"show": literal(False)}, "selector": EVERY}],
            "padding": [{"properties": {"paddingUniform": integer(0)}, "selector": EVERY}],
        },
        filters=list(filters),
        container={"title": [{"properties": {"show": literal(False)}}]},
    )


def image(key: str, x: int, y: int, w: int, h: int, resource: str, alt: str) -> Visual:
    url = {
        "expr": {
            "ResourcePackageItem": {
                "PackageName": "RegisteredResources",
                "PackageType": 1,
                "ItemName": resource,
            }
        }
    }
    return Visual(
        key,
        "image",
        x,
        y,
        w,
        h,
        alt=alt,
        objects={
            "general": [{"properties": {"imageUrl": url}}],
            "imageScaling": [{"properties": {"imageScalingType": literal("Fill")}}],
        },
    )


def measure_image(key: str, x: int, y: int, w: int, h: int, measure: str, alt: str) -> Visual:
    """Image whose URL comes from a measure (data category Image URL)."""
    return Visual(
        key,
        "image",
        x,
        y,
        w,
        h,
        alt=alt,
        objects={
            "general": [{"properties": {"imageUrl": {"expr": field_expr(M(measure))}}}],
            "imageScaling": [{"properties": {"imageScalingType": literal("Fit")}}],
        },
    )


def slicer(
    key: str,
    x: int,
    y: int,
    w: int,
    h: int,
    column: Field,
    alt: str,
    mode: str = "Basic",
    header: bool = False,
    filters: tuple[dict, ...] = (),
    horizontal: bool = False,
) -> Visual:
    """Single-select slicer; horizontal lays a Basic slicer out as a row of buttons."""
    objects = {
        "data": [{"properties": {"mode": literal(mode)}}],
        "selection": [{"properties": {"singleSelect": literal(True)}}],
        "header": [{"properties": {"show": literal(header)}}],
    }
    if horizontal:
        objects["general"] = [{"properties": {"orientation": literal(1)}}]
    return Visual(
        key,
        "slicer",
        x,
        y,
        w,
        h,
        roles={"Values": [column]},
        alt=alt,
        objects=objects,
        filters=list(filters),
    )


def chart(
    key: str,
    kind: str,
    x: int,
    y: int,
    w: int,
    h: int,
    title: str,
    category: Field,
    values: list[Field],
    alt: str,
    series: Field | None = None,
    tooltips: list[Field] | None = None,
    filters: tuple[dict, ...] = (),
    sort: tuple[Field, str] | None = None,
) -> Visual:
    roles: dict[str, list[Field]] = {"Category": [category], "Y": values}
    if series:
        roles["Series"] = [series]
    if tooltips:
        roles["Tooltips"] = tooltips
    return Visual(
        key, kind, x, y, w, h, roles=roles, title=title, alt=alt, filters=list(filters), sort=sort
    )


def ranked_bars(
    key: str, x: int, y: int, w: int, h: int, title: str, measure: str, alt: str
) -> Visual:
    """Bars of the focus region, peers, country and EU, highest first."""
    return chart(
        key,
        "clusteredBarChart",
        x,
        y,
        w,
        h,
        title,
        C("Geo", "Name"),
        [M(measure)],
        alt,
        filters=(AREAS,),
        sort=(M(measure), "Descending"),
    )


def table(
    key: str,
    x: int,
    y: int,
    w: int,
    h: int,
    title: str,
    fields: list[Field],
    alt: str,
    filters: tuple[dict, ...] = (),
) -> Visual:
    return Visual(
        key,
        "tableEx",
        x,
        y,
        w,
        h,
        roles={"Values": fields},
        title=title,
        alt=alt,
        filters=list(filters),
    )


def navigator(key: str, x: int, y: int, w: int, h: int) -> Visual:
    """Page navigator: one button per visible page, stacked vertically.

    Desktop lists the hidden pages too unless showHiddenPages is off.
    """
    return Visual(
        key,
        NAVIGATOR_TYPE,
        x,
        y,
        w,
        h,
        alt="Report pages",
        objects={
            "layout": [{"properties": {"orientation": literal(1)}}],
            "pages": [{"properties": {"showHiddenPages": literal(False)}}],
        },
    )


def chrome(prefix: str, page_name: str) -> list[Visual]:
    """Navigation, the three zones and the story header (eyebrow, headline, paragraph)."""
    return [
        shape("nav", 0, 0, 192, 720, TEXT),
        shape("surface", 640, 0, 640, 720, SURFACE),
        shape("rule", 640, 0, 1, 720, RULE),
        textbox("nav-kicker", 24, 24, 144, 32, "Regional profile", color=RULE),
        card(
            "nav-region",
            24,
            56,
            144,
            32,
            "Focus region name",
            size=18,
            color=BASE,
            alt=M("Focus region name"),
            background=False,
        ),
        navigator("navigator", 16, 112, 160, 320),
        card(
            "nav-data",
            24,
            656,
            144,
            32,
            "Data up to",
            size=10.5,
            color=RULE,
            alt=M("Data up to"),
            background=False,
        ),
        textbox("eyebrow", STORY_X, 24, STORY_W, 32, page_name.upper()),
        card(
            "headline",
            STORY_X,
            56,
            STORY_W,
            128,
            f"{prefix} headline lead",
            size=HEADLINE_PT,
            alt=M(f"{prefix} headline lead"),
        ),
        card(
            "headline-accent",
            STORY_X,
            184,
            STORY_W,
            48,
            f"{prefix} headline accent",
            size=HEADLINE_PT,
            color=ACCENT,
            alt=M(f"{prefix} headline accent"),
        ),
        card(
            "paragraph",
            STORY_X,
            232,
            STORY_W,
            96,
            f"{prefix} paragraph",
            alt=M(f"{prefix} paragraph"),
            font="Segoe UI",
        ),
    ]


def source(text: str) -> Visual:
    return textbox("source", STORY_X, 656, STORY_W, 56, text)


KPIS = (
    ("population", "Population", "Population", "KPI gap Population"),
    ("aged-65", "Aged 65+", "Share aged 65+", "KPI gap Share aged 65+"),
    ("deaths", "Deaths per 1,000", "Crude death rate per 1,000", "KPI gap Crude death rate"),
    ("unemployment", "Unemployment", "Unemployment rate", "KPI gap Unemployment rate"),
    ("gdp", "GDP per inhabitant", "GDP per inhabitant (EUR)", "KPI gap GDP per inhabitant"),
    ("companies", "Active companies", "Active companies", "KPI gap Active companies"),
)


def overview() -> Page:
    v = chrome("Overview", "Overview")
    v.append(
        image(
            "photo",
            STORY_X,
            SLOT_Y,
            STORY_W,
            SLOT_H,
            "photo-overview-valadier.jpg",
            "The Tempio del Valadier, a white octagonal church"
            " under a rock overhang in the Frasassi gorge",
        )
    )
    v.append(source("Eurostat, Chamber of Commerce of the Marche · Photo: Kimahri88, CC0"))
    v.append(textbox("compare-label", DASH_X, 32, 280, 32, "Compare with"))
    v.append(
        slicer(
            "benchmark",
            RIGHT_X,
            32,
            HALF_W,
            40,
            C("Benchmark", "Benchmark"),
            "Benchmark for the KPI gaps: country, EU or peer average",
            horizontal=True,
        )
    )
    for i, (key, title, value, gap) in enumerate(KPIS):
        x, y = THIRDS[i % 3], KPI_Y + (i // 3) * (KPI_H + GAP_H + 8)
        v.append(
            card(
                f"kpi-{key}",
                x,
                y,
                THIRD_W,
                KPI_H,
                value,
                size=24,
                title=title,
                alt=f"{title} of the focus region",
                filters=(FOCUS,),
                precision=2 if key == "population" else None,
            )
        )
        v.append(text_card(f"kpi-{key}-gap", x, y + KPI_H, THIRD_W, GAP_H, gap, M(gap), (FOCUS,)))
    v.append(
        chart(
            "population",
            "lineChart",
            DASH_X,
            CHART_Y,
            HALF_W,
            CHART_H,
            "Population on 1 January",
            C("Calendar", "Year"),
            [M("Population")],
            "Line chart of the focus region's population on 1 January, by year",
            filters=(FOCUS,),
        )
    )
    v.append(
        chart(
            "companies",
            "lineChart",
            RIGHT_X,
            CHART_Y,
            HALF_W,
            CHART_H,
            "Active companies in December",
            C("Calendar", "Year"),
            [M("Active companies, December")],
            "Line chart of the focus region's active companies in December, by year",
            filters=(FOCUS,),
        )
    )
    return Page("overview", "Overview", v)


def spike() -> Page:
    """Hidden page for the Task 15 Desktop spike: one visual of each kind Overview lacks.

    Not in pages(): it is scaffolded once by hand, checked in Desktop, then deleted.
    """
    xs, ys, w, h = (16, 440, 864), (16, 256, 496), 400, 224
    slots = [(x, y, w, h) for y in ys for x in xs]
    pyramid = [M("Population (men, negative)"), M("Population (women)")]
    visuals = [
        measure_image("map", *slots[0], "Map SVG", "Spike: map of the provinces"),
        slicer(
            "year", *slots[1], C("Calendar", "Year"), "Spike: year", mode="Dropdown", header=True
        ),
        chart(
            "pyramid",
            "barChart",
            *slots[2],
            "Spike: pyramid",
            C("AgeGroup", "Name"),
            pyramid,
            "Spike: population pyramid",
            filters=(FOCUS, in_filter(C("AgeGroup", "IsBand"), [True])),
        ),
        Visual(
            "dots",
            "scatterChart",
            *slots[3],
            roles={
                "Category": [C("Benchmark point", "Point")],
                "Series": [C("Benchmark point", "Role")],
                "X": [M("Dot position")],
                "Y": [M("Dot row")],
            },
            title="Spike: dot plot",
            alt="Spike: dot plot",
        ),
        chart(
            "season",
            "clusteredColumnChart",
            *slots[4],
            "Spike: seasonal effect",
            C("Seasonality", "MonthName"),
            [M("Seasonal effect")],
            "Spike: seasonal effect",
        ),
        Visual(
            "values",
            "multiRowCard",
            *slots[5],
            roles={"Values": [M("Population"), M("Share aged 65+")]},
            alt="Spike: multi-row card",
            filters=[FOCUS],
        ),
        ranked_bars("ranked", *slots[6], "Spike: aged 65+", "Share aged 65+", "Spike: ranked"),
        table(
            "table",
            *slots[7],
            "Spike: table",
            [C("Geo", "Name"), M("Share aged 65+")],
            "Spike: table",
            filters=(PROVINCES,),
        ),
        Visual(
            "matrix",
            "pivotTable",
            *slots[8],
            roles={"Rows": [C("Geo", "Name")], "Values": [M("Share aged 65+")]},
            title="Spike: matrix",
            alt="Spike: matrix",
            filters=[AREAS],
        ),
    ]
    return Page("spike", "Spike", visuals, hidden=True)


def pages() -> list[Page]:
    return [overview()]


PAGE_NAMES = [p.name for p in pages()]

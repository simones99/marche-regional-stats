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

ACCENT, TEXT, MUTED, GREY = "#00753A", "#15201A", "#4F5A53", "#6B746E"
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
    objects: dict | None = None,
) -> Visual:
    roles: dict[str, list[Field]] = {"Category": [category], "Y": values}
    if series:
        roles["Series"] = [series]
    if tooltips:
        roles["Tooltips"] = tooltips
    return Visual(
        key,
        kind,
        x,
        y,
        w,
        h,
        roles=roles,
        title=title,
        alt=alt,
        objects=objects,
        filters=list(filters),
        sort=sort,
    )


def two_sided_bars(left: tuple[str, str], right: tuple[str, str]) -> tuple[list, dict]:
    """Values and formatting of a pyramid or butterfly whose highlighted rows are in the accent.

    Desktop offers no fx colour on a bar chart with two measures, so each side is split into a
    highlighted and a plain measure (one of them blank in every row), each with a fixed colour.
    """
    values = [M(name) for name in (*left, *right)]
    colours = [
        {
            "properties": {"fill": solid(ACCENT if i % 2 == 0 else GREY)},
            "selector": {"metadata": f"{f.table}.{f.name}"},
        }
        for i, f in enumerate(values)
    ]
    axis = {"innerPadding": integer(20)}
    return values, {"dataPoint": colours, "categoryAxis": [{"properties": axis}]}


def ranked_bars(
    key: str, x: int, y: int, w: int, h: int, title: str, measure: str, alt: str
) -> Visual:
    """Bars of the focus region, neighbouring regions, country and EU, highest first."""
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
            "Benchmark for the KPI gaps: country, EU or neighbouring regions average",
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


def population() -> Page:
    v = chrome("Population", "Population & Health")
    v.append(
        slicer(
            "year",
            STORY_X,
            SLOT_Y,
            160,
            64,
            C("Calendar", "Year"),
            "Year of the age pyramid",
            mode="Dropdown",
            header=True,
        )
    )
    v.append(
        chart(
            "deaths",
            "lineChart",
            STORY_X,
            424,
            STORY_W,
            224,
            "Deaths per 1,000 residents",
            C("Calendar", "Year"),
            [M("Crude death rate per 1,000")],
            "Line chart of the crude death rate by year"
            " for the focus region, the country and the EU",
            series=C("Geo", "Name"),
            filters=(LINES,),
        )
    )
    v.append(source("Eurostat demo_r_pjangrp3, demo_r_magec3"))
    pyramid, pyramid_format = two_sided_bars(
        ("Population (men aged 65+, negative)", "Population (men under 65, negative)"),
        ("Population (women aged 65+)", "Population (women under 65)"),
    )
    v.append(
        chart(
            "pyramid",
            "barChart",
            DASH_X,
            32,
            DASH_W,
            656,  # Desktop needs about 23 px per band to show all 19 without a scroll bar
            "Residents by age and sex, 1 January (men left, women right)",
            C("AgeGroup", "Name"),
            pyramid,
            "Population pyramid of the focus region by five-year age band"
            "; bands aged 65 and over in the accent colour",
            filters=(FOCUS, in_filter(C("AgeGroup", "IsBand"), [True])),
            sort=(C("AgeGroup", "Name"), "Descending"),
            objects=pyramid_format,
        )
    )
    return Page("population", "Population & Health", v)


def economy() -> Page:
    v = chrome("Economy", "Economy & Labour")
    v.append(
        ranked_bars(
            "gdp-rank",
            STORY_X,
            SLOT_Y,
            STORY_W,
            SLOT_H,
            "GDP per inhabitant, euro",
            "GDP per inhabitant (EUR)",
            "Bar chart of GDP per inhabitant for the focus region, its neighbouring regions, the country and the EU",
        )
    )
    v.append(source("Eurostat nama_10r_2gdp, lfst_r_lfu3rt"))
    v.append(
        textbox(
            "legend",
            DASH_X,
            32,
            DASH_W,
            24,
            "●  Focus region, solid      □  Country, dashed      ▲  EU-27, dotted",
        )
    )
    v.append(
        chart(
            "gdp",
            "lineChart",
            DASH_X,
            80,
            DASH_W,
            288,
            "GDP per inhabitant, euro",
            C("Calendar", "Year"),
            [M("GDP per inhabitant (EUR)")],
            "Line chart of GDP per inhabitant by year for the focus region, the country and the EU",
            series=C("Geo", "Name"),
            filters=(LINES,),
        )
    )
    v.append(
        chart(
            "unemployment",
            "lineChart",
            DASH_X,
            392,
            DASH_W,
            296,
            "Unemployment rate, ages 15-74",
            C("Calendar", "Year"),
            [M("Unemployment rate")],
            "Line chart of the unemployment rate by year"
            " for the focus region, the country and the EU",
            series=C("Geo", "Name"),
            filters=(LINES,),
        )
    )
    return Page("economy", "Economy & Labour", v)


def education() -> Page:
    v = chrome("Education", "Education")
    v.append(
        image(
            "photo",
            STORY_X,
            SLOT_Y,
            STORY_W,
            SLOT_H,
            "photo-education-urbino.jpg",
            "Urbino's historic centre with the cathedral dome and the towers of the Ducal Palace",
        )
    )
    v.append(source("Eurostat educ_uoe_enra11 · Photo: Fabio Poggi, CC BY 3.0"))
    v.append(textbox("level-label", DASH_X, 40, 120, 24, "ISCED level"))
    v.append(
        slicer(
            "level",
            800,
            32,
            448,
            40,
            C("ISCED", "Group"),
            "Filter by education level",
            filters=(in_filter(C("ISCED", "Group"), ["ISCED 0-3", "ISCED 4", "ISCED 5-8"]),),
            horizontal=True,
        )
    )
    butterfly, butterfly_format = two_sided_bars(
        ("Students (women, tertiary, negative)", "Students (women, other levels, negative)"),
        ("Students (men, tertiary)", "Students (men, other levels)"),
    )
    v.append(
        chart(
            "butterfly",
            "barChart",
            DASH_X,
            96,
            DASH_W,
            304,
            "Students enrolled by level and sex (women left, men right)",
            C("ISCED", "ShortName"),
            butterfly,
            "Butterfly chart of students enrolled in the focus region by level and sex"
            "; tertiary levels in the accent colour",
            filters=(FOCUS, in_filter(C("ISCED", "IsTotal"), [False])),
            sort=(C("ISCED", "ShortName"), "Ascending"),
            objects=butterfly_format,
        )
    )
    v.append(
        ranked_bars(
            "tertiary",
            DASH_X,
            424,
            DASH_W,
            264,
            "Tertiary students per 1,000 residents",
            "Tertiary students per 1,000 residents",
            "Bar chart of tertiary students per 1,000 residents"
            " for the focus region, its neighbouring regions, the country and the EU",
        )
    )
    return Page("education", "Education", v)


PROVINCE_MEASURES = [
    "Population change 5y %",
    "Share aged 65+",
    "Crude death rate per 1,000",
    "Companies per 1,000 residents",
    "GDP per inhabitant (EUR)",
]
BENCHMARK_MEASURES = [
    "Population change 5y %",
    "Share aged 65+",
    "Crude death rate per 1,000",
    "GDP per inhabitant (EUR)",
    "Unemployment rate",
    "Tertiary students per 1,000 residents",
]


def provinces() -> Page:
    v = chrome("Provinces", "Provinces")
    v.append(
        slicer(
            "indicator",
            STORY_X,
            SLOT_Y,
            STORY_W,
            SLOT_H,
            C("Province indicator", "Province indicator"),
            "Indicator shown on the map",
            header=True,
        )
    )
    v.append(source("Eurostat, Chamber of Commerce · GISCO boundaries, © EuroGeographics"))
    v.append(
        measure_image(
            "map",
            DASH_X,
            32,
            DASH_W,
            320,
            "Map SVG",
            "Map of the provinces shaded by the selected indicator; each province shows its name"
            " and value",
        )
    )
    v.append(
        table(
            "table",
            DASH_X,
            376,
            DASH_W,
            280,
            "All indicators by province",
            [C("Geo", "Name"), *[M(m) for m in PROVINCE_MEASURES]],
            "Table of the five indicators by province",
            filters=(PROVINCES,),
        )
    )
    v.append(
        textbox(
            "drill-hint",
            DASH_X,
            664,
            DASH_W,
            24,
            "Right-click a province › Drill through › Province detail",
        )
    )
    return Page("provinces", "Provinces", v)


def business() -> Page:
    v = chrome("Business", "Business deep dive · focus region only")
    v.append(
        chart(
            "index",
            "lineChart",
            STORY_X,
            SLOT_Y,
            STORY_W,
            SLOT_H,
            "Active companies by province, December 2009 = 100",
            C("Calendar", "Year"),
            [M("Active companies index")],
            "Line chart of active companies by province as an index, first December = 100; one"
            " marker shape per province",
            series=C("Geo", "Name"),
            filters=(PROVINCES,),
        )
    )
    v.append(source("Chamber of Commerce of the Marche · SARIMA by marche-stats"))
    v.append(
        chart(
            "forecast",
            "lineChart",
            DASH_X,
            32,
            DASH_W,
            280,
            "Active companies: last 24 months and 12-month SARIMA forecast",
            C("Calendar", "Date"),
            [M("Forecast chart actual"), M("Forecast chart forecast")],
            "Line chart of active companies in the last 24 months and the SARIMA forecast for the"
            " next 12, with its 95 % interval",
            tooltips=[M("Forecast lower 95"), M("Forecast upper 95")],
        )
    )
    v.append(
        chart(
            "sectors",
            "clusteredBarChart",
            DASH_X,
            336,
            HALF_W,
            352,
            "Change by sector since December 2009",
            C("Sector", "ShortName"),
            [M("Sector change, ten largest")],
            "Bar chart of the change in active companies for the ten largest ATECO sections;"
            " growing sections in the accent colour",
            filters=(FOCUS,),
            sort=(M("Sector change, ten largest"), "Descending"),
        )
    )
    v.append(
        chart(
            "season",
            "clusteredColumnChart",
            RIGHT_X,
            336,
            HALF_W,
            184,
            "Seasonal effect by month",
            C("Seasonality", "MonthName"),
            [M("Seasonal effect")],
            "Column chart of the average seasonal effect on active companies by calendar month",
            sort=(C("Seasonality", "MonthName"), "Ascending"),
        )
    )
    v.append(
        chart(
            "mape",
            "clusteredBarChart",
            RIGHT_X,
            536,
            HALF_W,
            152,
            "Forecast error on the 24-month test (MAPE)",
            C("ForecastAccuracy", "Method"),
            [M("Forecast MAPE")],
            "Bar chart of the mean absolute percentage error of SARIMA and two naive forecasts",
            sort=(M("Forecast MAPE"), "Ascending"),
        )
    )
    return Page("business", "Business deep dive", v)


def benchmark() -> Page:
    v = chrome("Benchmark", "Benchmark")
    v.append(
        textbox(
            "dot-labels",
            STORY_X,
            SLOT_Y,
            128,
            SLOT_H,
            [
                "Population change, 5 years",
                "Aged 65+",
                "Deaths per 1,000",
                "GDP per inhabitant",
                "Unemployment",
                "Tertiary students per 1,000",
            ],
        )
    )
    v.append(
        Visual(
            "dots",
            "scatterChart",
            352,
            SLOT_Y,
            256,
            SLOT_H,
            roles={
                "Category": [C("Benchmark point", "Point")],
                "Series": [C("Benchmark point", "Role")],
                "X": [M("Dot position")],
                "Y": [M("Dot row")],
            },
            title="Where the focus region sits, lowest to highest",
            alt=(
                "Dot plot of the focus region, its neighbouring regions, the country and the EU for six"
                " indicators, from the lowest value on the left to the highest on the right"
            ),
        )
    )
    v.append(source("Eurostat · neighbouring regions set by the PeerRegions parameter"))
    v.append(textbox("show-label", DASH_X, 40, 120, 24, "Show"))
    v.append(
        slicer(
            "compare",
            800,
            32,
            448,
            40,
            C("Compare to", "Comparison"),
            "Show values or differences from a benchmark",
            filters=(
                in_filter(
                    C("Compare to", "Comparison"), ["Value", "vs Country", "vs EU", "vs Neighbours avg"]
                ),
            ),
            horizontal=True,
        )
    )
    v.append(
        Visual(
            "matrix",
            "pivotTable",
            DASH_X,
            96,
            DASH_W,
            432,
            roles={"Rows": [C("Geo", "Name")], "Values": [M(m) for m in BENCHMARK_MEASURES]},
            title="Indicators by area",
            alt="Matrix of six indicators for the focus region, its neighbouring regions, the country and the EU",
            filters=[AREAS],
        )
    )
    v.append(
        table(
            "ranks",
            DASH_X,
            544,
            DASH_W,
            64,
            "Rank among Neighbours (1 = Highest)",
            [M("Rank row label"), *[M(m) for m in BENCHMARK_MEASURES]],
            "Rank of the focus region among its neighbouring regions for each indicator",
            filters=(FOCUS, in_filter(C("Compare to", "Comparison"), ["Rank among neighbours"])),
        )
    )
    v.append(
        card(
            "years",
            DASH_X,
            624,
            DASH_W,
            64,
            "Benchmark years",
            size=10.5,
            color=MUTED,
            alt="Years compared and rank direction",
        )
    )
    return Page("benchmark", "Benchmark", v)


def about() -> Page:
    v = chrome("About", "About")
    v.append(
        textbox(
            "about-text",
            STORY_X,
            SLOT_Y,
            STORY_W,
            SLOT_H,
            [
                "# Sources",
                "Eurostat: population, deaths, GDP, unemployment, enrolment",
                "GISCO NUTS 2024: codes and province boundaries",
                "Chamber of Commerce of the Marche: active companies, 2009–2025",
                "# Limits",
                "Companies end in March 2025: ATECO 2025 replaces ATECO 2007 from April",
                "February 2025 is dropped: identical to January, so not updated",
                "Provincial GDP lags the regional series by a year",
                "# Refresh",
                "Open the .pbip in Power BI Desktop, choose Refresh, use anonymous access",
                "# Photos (Wikimedia Commons)",
                "Kimahri88, CC0 · Fabio Poggi, CC BY 3.0 · Gaspa, CC BY 2.0",
            ],
        )
    )
    v.append(source("github.com/simones99/marche-regional-stats"))
    checkpoint = [
        C("Reconciliation", "Checkpoint"),
        M("Reconciliation in model"),
        M("Reconciliation status"),
    ]
    v.append(
        table(
            "reconciliation-a",
            DASH_X,
            32,
            HALF_W,
            256,
            "Reconciliation: region and north",
            checkpoint,
            "Reconciliation checkpoints for the region, Pesaro e Urbino and Ancona",
            filters=(in_filter(C("Reconciliation", "GeoCode"), ["ITI3", "ITI31", "ITI32"]),),
        )
    )
    v.append(
        table(
            "reconciliation-b",
            RIGHT_X,
            32,
            HALF_W,
            256,
            "Reconciliation: south",
            checkpoint,
            "Reconciliation checkpoints for Macerata, Ascoli Piceno and Fermo",
            filters=(in_filter(C("Reconciliation", "GeoCode"), ["ITI33", "ITI34", "ITI35"]),),
        )
    )
    v.append(
        table(
            "freshness",
            DASH_X,
            312,
            DASH_W,
            184,
            "Latest period per source",
            [C("Data source", "Source"), M("Latest period")],
            "Table of the latest period available for each source",
        )
    )
    v.append(
        textbox(
            "flags-note",
            DASH_X,
            504,
            DASH_W,
            24,
            "Tooltips mark Eurostat flags: p provisional, e estimated, b break in series.",
        )
    )
    v.append(
        image(
            "photo",
            DASH_X,
            528,
            DASH_W,
            160,
            "photo-about-due-sorelle.jpg",
            "The Spiaggia delle Due Sorelle, a white beach below the Conero cliffs, seen from"
            " above",
        )
    )
    return Page("about", "About", v)


def province_detail() -> Page:
    v = chrome("Province detail", "Province detail")
    v.append(
        chart(
            "index",
            "lineChart",
            STORY_X,
            SLOT_Y,
            STORY_W,
            SLOT_H,
            "Active companies, December 2009 = 100",
            C("Calendar", "Year"),
            [M("Active companies index")],
            "Line chart of the province's active companies as an index, first December = 100",
        )
    )
    v.append(source("Eurostat, Chamber of Commerce of the Marche"))
    for i, name in enumerate(PROVINCE_MEASURES):
        only = in_filter(C("Province indicator", "Province indicator"), [name])
        x, y = THIRDS[i % 3], 32 + (i // 3) * (KPI_H + GAP_H + 8)
        v.append(
            card(
                f"kpi-{i}",
                x,
                y,
                THIRD_W,
                KPI_H,
                "Province indicator value",
                size=24,
                title=name,
                alt=f"{name} of the province",
                filters=(only,),
            )
        )
        v.append(
            text_card(
                f"kpi-{i}-gap",
                x,
                y + KPI_H,
                THIRD_W,
                GAP_H,
                "Province gap to region",
                M("Province gap to region"),
                (only,),
            )
        )
    v.append(
        chart(
            "sectors",
            "clusteredBarChart",
            DASH_X,
            352,
            DASH_W,
            336,
            "Change by sector since December 2009",
            C("Sector", "ShortName"),
            [M("Sector change, ten largest")],
            "Bar chart of the change in active companies in the province for its ten largest"
            " ATECO sections",
            sort=(M("Sector change, ten largest"), "Descending"),
        )
    )
    return Page("province-detail", "Province detail", v, hidden=True)


def area_tooltip() -> Page:
    return Page(
        "area-tooltip",
        "Area tooltip",
        [
            card("name", 16, 16, 288, 32, "Area name", alt="Area"),
            Visual(
                "values",
                "multiRowCard",
                16,
                56,
                288,
                136,
                roles={"Values": [M(m) for m in BENCHMARK_MEASURES]},
                alt="Indicators of the area",
            ),
            card(
                "flags",
                16,
                200,
                288,
                24,
                "Flags text",
                size=10.5,
                color=MUTED,
                alt="Eurostat flags",
            ),
        ],
        hidden=True,
        width=320,
        height=240,
    )


def province_tooltip() -> Page:
    return Page(
        "province-tooltip",
        "Province tooltip",
        [
            card("name", 16, 16, 288, 32, "Area name", alt="Province"),
            Visual(
                "values",
                "multiRowCard",
                16,
                56,
                288,
                168,
                roles={"Values": [M(m) for m in PROVINCE_MEASURES]},
                alt="Indicators of the province",
            ),
        ],
        hidden=True,
        width=320,
        height=240,
    )


def pages() -> list[Page]:
    return [
        overview(),
        population(),
        economy(),
        education(),
        provinces(),
        business(),
        benchmark(),
        about(),
        province_detail(),
        area_tooltip(),
        province_tooltip(),
    ]


PAGE_NAMES = [p.name for p in pages()]

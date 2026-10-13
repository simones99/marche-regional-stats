"""Layout of the report pages: what goes where, in px on the 8 px grid.

Zones (Phase B spec, Visual system): navigation 0-192, story 192-640, dashboard 640-1280.
`marche-stats scaffold-report` writes each page once; the formatting a theme cannot set is
done in Power BI Desktop, and Desktop's saved files are then the source of truth.
"""

from __future__ import annotations

from marche_stats.pbir import C, Field, M, Page, Visual, in_filter, literal, solid

ACCENT, TEXT, MUTED = "#00753A", "#15201A", "#4F5A53"
BASE, SURFACE, RULE = "#F5F6F3", "#ECEEEA", "#C9CEC9"
NAVIGATOR_TYPE = "pageNavigator"

STORY_X, STORY_W = 224, 384
DASH_X, DASH_W = 672, 576
HALF_W, RIGHT_X = 280, 968
THIRD_W, THIRDS = 176, (672, 872, 1072)
SLOT_Y, SLOT_H = 344, 304

FOCUS = in_filter(C("Geo", "Role"), ["Focus"])
AREAS = in_filter(C("Geo", "Role"), ["Focus", "Peer", "Country", "EU"])
LINES = in_filter(C("Geo", "Role"), ["Focus", "Country", "EU"])
PROVINCES = in_filter(C("Geo", "Role"), ["Province"])


def shape(key: str, x: int, y: int, w: int, h: int, color: str) -> Visual:
    return Visual(
        key,
        "shape",
        x,
        y,
        w,
        h,
        objects={
            "shape": [{"properties": {"tileShape": literal("rectangle")}}],
            "fill": [{"properties": {"show": literal(True), "fillColor": solid(color)}}],
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
    alt: str | None = None,
    filters: tuple[dict, ...] = (),
) -> Visual:
    """Classic card showing one measure (a number, or a text measure for the story)."""
    return Visual(
        key,
        "card",
        x,
        y,
        w,
        h,
        roles={"Values": [M(measure)]},
        title=title,
        alt=alt or measure,
        objects={
            "labels": [{"properties": {"color": solid(color), "fontSize": literal(size)}}],
            "categoryLabels": [{"properties": {"show": literal(False)}}],
        },
        filters=list(filters),
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
            "general": [
                {
                    "properties": {
                        "imageUrl": {
                            "expr": {
                                "Measure": {
                                    "Expression": {"SourceRef": {"Entity": "_Measures"}},
                                    "Property": measure,
                                }
                            }
                        }
                    }
                }
            ],
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
) -> Visual:
    return Visual(
        key,
        "slicer",
        x,
        y,
        w,
        h,
        roles={"Values": [column]},
        alt=alt,
        objects={
            "data": [{"properties": {"mode": literal(mode)}}],
            "selection": [{"properties": {"singleSelect": literal(True)}}],
            "header": [{"properties": {"show": literal(header)}}],
        },
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


def chrome(prefix: str, page_name: str) -> list[Visual]:
    """Navigation, the three zones and the story header (eyebrow, headline, paragraph)."""
    return [
        shape("nav", 0, 0, 192, 720, TEXT),
        shape("surface", 640, 0, 640, 720, SURFACE),
        shape("rule", 640, 0, 1, 720, RULE),
        textbox("nav-kicker", 24, 32, 144, 24, "Regional profile", color=RULE),
        card(
            "nav-region",
            24,
            56,
            144,
            32,
            "Focus region name",
            size=18,
            color=BASE,
            alt="Focus region",
        ),
        Visual("navigator", NAVIGATOR_TYPE, 16, 112, 160, 320),
        card("nav-data", 24, 656, 144, 32, "Data up to", size=10.5, color=RULE, alt="Latest data"),
        textbox("eyebrow", STORY_X, 32, STORY_W, 24, page_name.upper()),
        card(
            "headline", STORY_X, 72, STORY_W, 96, f"{prefix} headline lead", size=30, alt="Headline"
        ),
        card(
            "headline-accent",
            STORY_X,
            168,
            STORY_W,
            48,
            f"{prefix} headline accent",
            size=30,
            color=ACCENT,
            alt="Headline, key phrase",
        ),
        card("paragraph", STORY_X, 232, STORY_W, 96, f"{prefix} paragraph", alt="Summary"),
    ]


def source(text: str) -> Visual:
    return textbox("source", STORY_X, 664, STORY_W, 24, text)


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
    v.append(textbox("compare-label", DASH_X, 40, 280, 24, "Compare with"))
    v.append(
        slicer(
            "benchmark",
            RIGHT_X,
            32,
            HALF_W,
            40,
            C("Benchmark", "Benchmark"),
            "Benchmark for the KPI gaps: country, EU or peer average",
        )
    )
    for i, (key, title, value, gap) in enumerate(KPIS):
        x, y = THIRDS[i % 3], 96 + (i // 3) * 144
        v.append(
            card(
                f"kpi-{key}",
                x,
                y,
                THIRD_W,
                88,
                value,
                size=24,
                title=title,
                alt=f"{title} of the focus region",
                filters=(FOCUS,),
            )
        )
        v.append(
            card(
                f"kpi-{key}-gap",
                x,
                y + 88,
                THIRD_W,
                32,
                gap,
                size=10.5,
                alt=f"{title}: gap to the benchmark",
                filters=(FOCUS,),
            )
        )
    v.append(
        chart(
            "population",
            "lineChart",
            DASH_X,
            384,
            HALF_W,
            304,
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
            384,
            HALF_W,
            304,
            "Active companies in December",
            C("Calendar", "Year"),
            [M("Active companies, December")],
            "Line chart of the focus region's active companies in December, by year",
            filters=(FOCUS,),
        )
    )
    return Page("overview", "Overview", v)


def pages() -> list[Page]:
    return [overview()]


PAGE_NAMES = [p.name for p in pages()]

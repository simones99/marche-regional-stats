"""Static checks of the report against the Phase B rules (spec, Visual system and
Accessibility): palette, font minimum, registered resources, and, once pages exist, the
page list, the navigator, the 8 px grid and alt text.
"""

import json
import re
from pathlib import Path

from marche_stats import pbir, report_layout

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "powerbi" / "marche-regional-profile.Report"
DEFINITION = REPORT / "definition"
RESOURCES = REPORT / "StaticResources" / "RegisteredResources"
THEME = RESOURCES / "MarcheProfile.json"
PALETTE = {
    "#F5F6F3",
    "#15201A",
    "#00753A",
    "#4F5A53",
    "#6B746E",
    "#ECEEEA",
    "#C9CEC9",
    "#D0E3D7",
    "#7AB696",
    "#4A9C72",
}
HEX = re.compile(r"#[0-9A-Fa-f]{6}\b")
MIN_POINTS = 10.5  # 14 px


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _points(value) -> float:
    if isinstance(value, dict):
        value = value["expr"]["Literal"]["Value"]
    # Desktop writes some sizes as quoted text, for example the line chart labels ('12').
    return float(str(value).strip("'").removesuffix("pt").removesuffix("D"))


def font_sizes(node):
    if isinstance(node, dict):
        for key, value in node.items():
            if key in ("fontSize", "textSize"):
                yield _points(value)
            else:
                yield from font_sizes(value)
    elif isinstance(node, list):
        for value in node:
            yield from font_sizes(value)


def colours(node) -> set[str]:
    return {c.upper() for c in HEX.findall(json.dumps(node))}


def test_theme_uses_the_palette_segoe_ui_and_the_font_minimum():
    theme = read(THEME)
    assert colours(theme) <= PALETTE
    assert theme["dataColors"][0] == "#00753A"
    assert all(size >= MIN_POINTS for size in font_sizes(theme))
    faces = re.findall(r'"font(?:Face|Family)": "([^"]+)"', json.dumps(theme))
    assert faces and all(face.startswith("Segoe UI") for face in faces)


def test_report_uses_the_registered_theme():
    report = read(DEFINITION / "report.json")
    assert report["themeCollection"]["customTheme"]["name"] == THEME.name
    assert report["themeCollection"]["customTheme"]["type"] == "RegisteredResources"
    packages = [p for p in report["resourcePackages"] if p["type"] == "RegisteredResources"]
    assert {"name": THEME.name, "path": THEME.name, "type": "CustomTheme"} in [
        item for package in packages for item in package["items"]
    ]


def test_registered_resources_exist_and_photos_are_small():
    report = read(DEFINITION / "report.json")
    packages = [p for p in report["resourcePackages"] if p["type"] == "RegisteredResources"]
    assert packages
    for package in packages:
        for item in package["items"]:
            path = RESOURCES / item["path"]
            assert path.exists(), item["path"]
            if item["type"] == "Image":
                assert path.stat().st_size < 300_000, item["path"]


def written_pages():
    meta = read(DEFINITION / "pages" / "pages.json")
    for name in meta["pageOrder"]:
        folder = DEFINITION / "pages" / name
        visuals = [read(p) for p in sorted((folder / "visuals").glob("*/visual.json"))]
        yield read(folder / "page.json"), visuals


def layout_pages():
    return [(p, v) for p, v in written_pages() if p["displayName"] in report_layout.PAGE_NAMES]


def test_pages_follow_the_layout_order():
    names = [p["displayName"] for p, _ in written_pages()]
    assert names[: len(report_layout.PAGE_NAMES)] == report_layout.PAGE_NAMES
    assert names[-1] == "Model check"


def test_visible_pages_are_the_report_pages():
    visible = [
        p["displayName"] for p, _ in written_pages() if p.get("visibility") != "HiddenInViewMode"
    ]
    assert visible == [p.name for p in report_layout.pages() if not p.hidden]


def test_every_visible_page_has_the_navigator():
    for page, visuals in written_pages():
        if page.get("visibility") == "HiddenInViewMode":
            continue
        types = {v["visual"]["visualType"] for v in visuals}
        assert report_layout.NAVIGATOR_TYPE in types, page["displayName"]


def test_visuals_sit_on_the_grid_inside_the_page():
    for page, visuals in layout_pages():
        for v in visuals:
            pos, where = v["position"], f"{page['displayName']}: {v['name']}"
            assert pos["x"] % 8 == 0 and pos["y"] % 8 == 0, where
            for size in (pos["width"], pos["height"]):
                assert size < 8 or size % 8 == 0, where
            assert pos["x"] + pos["width"] <= page["width"], where
            assert pos["y"] + pos["height"] <= page["height"], where


def test_pages_have_the_layout_size():
    sizes = {p.name: (p.width, p.height) for p in report_layout.pages()}
    for page, _ in layout_pages():
        assert (page["width"], page["height"]) == sizes[page["displayName"]]
        if page.get("visibility") != "HiddenInViewMode":
            assert (page["width"], page["height"]) == (1280, 720), page["displayName"]


def test_visuals_have_alt_text():
    """Every visual but shapes and textboxes: a literal, or an expression bound to a measure."""
    for page, visuals in layout_pages():
        for v in visuals:
            if v["visual"]["visualType"] in ("shape", "textbox"):
                continue
            general = v["visual"].get("visualContainerObjects", {}).get("general", [{}])
            alt = general[0].get("properties", {}).get("altText", {}).get("expr", {})
            assert "Literal" in alt or "Measure" in alt, f"{page['displayName']}: {v['name']}"


def _box(v):
    pos = v["position"]
    return pos["x"], pos["y"], pos["x"] + pos["width"], pos["y"] + pos["height"]


def test_visuals_do_not_overlap():
    for page, visuals in layout_pages():
        boxes = [(v["name"], _box(v)) for v in visuals if v["visual"]["visualType"] != "shape"]
        for i, (name, (x0, y0, x1, y1)) in enumerate(boxes):
            for other, (a0, b0, a1, b1) in boxes[i + 1 :]:
                overlap = x0 < a1 and a0 < x1 and y0 < b1 and b0 < y1
                assert not overlap, f"{page['displayName']}: {name} and {other}"


def test_cards_on_the_dark_rail_have_no_background():
    off = {"show": {"expr": {"Literal": {"Value": "false"}}}}
    for page, visuals in layout_pages():
        for v in visuals:
            if v["visual"]["visualType"] != "card" or _box(v)[2] > 192:
                continue
            background = v["visual"].get("visualContainerObjects", {}).get("background")
            assert background and background[0]["properties"] == off, (
                f"{page['displayName']}: {v['name']}"
            )


def test_kpi_gap_lines_wrap_in_the_new_card():
    # The classic card cannot wrap: at 10.5 pt the gap lines do not fit 176 px on one line.
    on = {"expr": {"Literal": {"Value": "true"}}}
    off = {"expr": {"Literal": {"Value": "false"}}}
    gaps = [v for v in report_layout.overview().visuals if v.key.endswith("-gap")]
    assert len(gaps) == len(report_layout.KPIS)
    for page, visuals in layout_pages():
        if page["displayName"] != "Overview":
            continue
        written = {v["name"]: v for v in visuals}
        for gap in gaps:
            v = written[pbir.object_id("overview", gap.key)]["visual"]
            assert v["visualType"] == "cardVisual", gap.key
            value, label = v["objects"]["value"][0], v["objects"]["label"][0]
            assert value["properties"]["textWrap"] == on, gap.key
            assert label["properties"]["show"] == off, gap.key
            # Without the "All" series selector Desktop ignores the font size.
            assert value["selector"] == label["selector"] == {"id": "default"}, gap.key


def test_shapes_fill_through_the_all_selector_and_skip_the_tab_order():
    # Desktop ignores a shape's fill colour without the "All" series selector and saves
    # a negative tabOrder for a visual left out of the tab order.
    for page, visuals in layout_pages():
        for v in visuals:
            if v["visual"]["visualType"] != "shape":
                continue
            where = f"{page['displayName']}: {v['name']}"
            fills = v["visual"]["objects"]["fill"]
            assert any(
                f.get("selector") == {"id": "default"} and "fillColor" in f["properties"]
                for f in fills
            ), where
            assert v["position"]["tabOrder"] < 0, where


def test_navigator_leaves_out_the_hidden_pages():
    off = {"expr": {"Literal": {"Value": "false"}}}
    for page, visuals in layout_pages():
        for v in visuals:
            if v["visual"]["visualType"] == report_layout.NAVIGATOR_TYPE:
                pages = v["visual"]["objects"]["pages"][0]["properties"]
                assert pages["showHiddenPages"] == off, page["displayName"]


def test_two_sided_bars_colour_each_series():
    # Desktop offers no fx colour on a bar chart with two measures: the pyramid and the
    # butterfly split each side into an accent and a grey measure with a fixed colour.
    accent = pbir.solid(report_layout.ACCENT)
    for page_key, key in (("population", "pyramid"), ("education", "butterfly")):
        written = {v["name"]: v for _, vs in layout_pages() for v in vs}
        v = written[pbir.object_id(page_key, key)]["visual"]
        refs = [p["queryRef"] for p in v["query"]["queryState"]["Y"]["projections"]]
        assert len(refs) == 4, key
        points = v["objects"]["dataPoint"]
        fills = {d["selector"]["metadata"]: d["properties"]["fill"] for d in points}
        assert set(fills) == set(refs), key
        assert [fills[r] == accent for r in refs] == [True, False, True, False], key
        assert "innerPadding" in v["objects"]["categoryAxis"][0]["properties"], key


def test_pages_use_the_palette_and_the_font_minimum():
    for page, visuals in layout_pages():
        for v in visuals:
            assert colours(v) <= PALETTE, f"{page['displayName']}: {v['name']}"
            assert all(size >= MIN_POINTS for size in font_sizes(v)), v["name"]


def test_spike_page_is_hidden_and_outside_the_layout():
    spike = report_layout.spike()
    assert spike.hidden and spike.key == "spike"
    assert spike.key not in {p.key for p in report_layout.pages()}
    assert all(v.alt for v in spike.visuals)


def _page(name):
    return next((p, v) for p, v in written_pages() if p["displayName"] == name)


def _fields(visual) -> list[str]:
    state = visual["visual"].get("query", {}).get("queryState", {})
    return [p["queryRef"] for role in state.values() for p in role["projections"]]


def test_tooltips_list_the_indicators_in_a_fixed_height_table():
    # A multi-row card wraps its values by text length and scrolls when they do not fit.
    for name, flag in (("Area tooltip", "InArea"), ("Province tooltip", "InProvince")):
        _, visuals = _page(name)
        assert "multiRowCard" not in {v["visual"]["visualType"] for v in visuals}, name
        tables = [v for v in visuals if v["visual"]["visualType"] == "tableEx"]
        assert len(tables) == 1, name
        assert _fields(tables[0]) == ["Tooltip indicator.Indicator", "_Measures.Tooltip value"]
        assert f'"Property": "{flag}"' in json.dumps(tables[0]["filterConfig"]), name


def test_benchmark_dot_plot_is_a_table_of_strips():
    # One row per indicator keeps each strip next to its label; a scatter chart cannot.
    _, visuals = _page("Benchmark")
    assert "scatterChart" not in {v["visual"]["visualType"] for v in visuals}
    strips = [v for v in visuals if "_Measures.Dot plot SVG" in _fields(v)]
    assert len(strips) == 1
    assert _fields(strips[0]) == [
        "Benchmark point.Indicator",
        "_Measures.Dot plot SVG",
        "_Measures.Dot focus value",
    ]
    assert any("Dot plot legend SVG" in json.dumps(v["visual"].get("objects", {})) for v in visuals)


def test_dot_plot_strips_have_no_tooltip():
    # The default tooltip of a table shows the SVG data URI of the strip as text.
    _, visuals = _page("Benchmark")
    strips = next(v for v in visuals if "_Measures.Dot plot SVG" in _fields(v))
    tooltip = strips["visual"]["visualContainerObjects"]["visualTooltip"][0]["properties"]
    assert tooltip["show"]["expr"]["Literal"]["Value"] == "false"


def test_province_legend_uses_the_short_names():
    _, visuals = _page("Business deep dive")
    index = next(v for v in visuals if "_Measures.Active companies index" in _fields(v))
    assert "Geo.LegendName" in _fields(index)
    styles = json.dumps(index["visual"]["objects"])
    assert "'PU'" in styles and "'AP'" in styles and "Pesaro e Urbino" not in styles


def test_benchmark_matrix_names_the_peer_regions():
    _, visuals = _page("Benchmark")
    matrix = next(v for v in visuals if v["visual"]["visualType"] == "pivotTable")
    subtitle = matrix["visual"]["visualContainerObjects"]["subTitle"][0]["properties"]
    assert subtitle["text"]["expr"]["Measure"]["Property"] == "Peer regions note"


def test_tables_and_matrices_have_no_total_row():
    # The measures are rates and shares: a total row is empty and takes the space of a row.
    off = {"expr": {"Literal": {"Value": "false"}}}
    for page, visuals in written_pages():
        for v in visuals:
            kind, objects = v["visual"]["visualType"], v["visual"].get("objects", {})
            where = f"{page['displayName']}: {v['name']}"
            if kind == "tableEx":
                assert objects["total"][0]["properties"]["totals"] == off, where
            elif kind == "pivotTable":
                assert objects["subTotals"][0]["properties"]["rowSubtotals"] == off, where


def test_area_tooltip_falls_back_to_the_focus_region():
    # A line chart hovered between points passes only the year, so the tooltip gets several areas.
    _, visuals = _page("Area tooltip")
    fields = {f for v in visuals for f in _fields(v)}
    assert {"_Measures.Tooltip title", "_Measures.Tooltip value", "_Measures.Tooltip flags"} <= fields

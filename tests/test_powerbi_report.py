"""Static checks of the report against the Phase B rules (spec, Visual system and
Accessibility): palette, font minimum, registered resources, and, once pages exist, the
page list, the navigator, the 8 px grid and alt text.
"""

import json
import re
from pathlib import Path

from marche_stats import report_layout

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
    return float(str(value).removesuffix("pt").removesuffix("D"))


def font_sizes(node):
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "fontSize":
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


def test_data_visuals_have_alt_text():
    for page, visuals in layout_pages():
        for v in visuals:
            if "query" not in v["visual"]:
                continue
            general = v["visual"].get("visualContainerObjects", {}).get("general", [{}])
            assert "altText" in general[0].get("properties", {}), (
                f"{page['displayName']}: {v['name']}"
            )


def test_pages_use_the_palette_and_the_font_minimum():
    for page, visuals in layout_pages():
        for v in visuals:
            assert colours(v) <= PALETTE, f"{page['displayName']}: {v['name']}"
            assert all(size >= MIN_POINTS for size in font_sizes(v)), v["name"]

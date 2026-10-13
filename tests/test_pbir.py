import json
import re

import pytest

from marche_stats import pbir
from marche_stats.pbir import C, M, Page, Visual


def test_object_id_is_stable_hex():
    name = pbir.object_id("overview", "kpi")
    assert name == pbir.object_id("overview", "kpi")
    assert re.fullmatch(r"[0-9a-f]{20}", name)
    assert name != pbir.object_id("overview", "kpi-2")


def test_literal_forms():
    assert pbir.literal("it's") == {"expr": {"Literal": {"Value": "'it''s'"}}}
    assert pbir.literal(10.5) == {"expr": {"Literal": {"Value": "10.5D"}}}
    assert pbir.literal(True) == {"expr": {"Literal": {"Value": "true"}}}


def test_visual_json_binds_fields_title_and_alt_text():
    visual = Visual(
        "bars",
        "clusteredBarChart",
        672,
        32,
        576,
        280,
        roles={"Category": [C("Geo", "Name")], "Y": [M("Share aged 65+")]},
        title="Share aged 65+",
        alt="Bar chart of the share aged 65+ by area",
        sort=(M("Share aged 65+"), "Descending"),
    )
    body = pbir.visual_json("page", visual, order=3)
    assert body["name"] == pbir.object_id("page", "bars")
    assert body["position"] == {
        "x": 672,
        "y": 32,
        "z": 3000,
        "height": 280,
        "width": 576,
        "tabOrder": 3000,
    }
    query = body["visual"]["query"]
    assert query["queryState"]["Category"]["projections"][0]["queryRef"] == "Geo.Name"
    assert "Measure" in query["queryState"]["Y"]["projections"][0]["field"]
    assert query["sortDefinition"]["sort"][0]["direction"] == "Descending"
    container = body["visual"]["visualContainerObjects"]
    assert container["title"][0]["properties"]["text"] == pbir.literal("Share aged 65+")
    assert container["general"][0]["properties"]["altText"] == pbir.literal(
        "Bar chart of the share aged 65+ by area"
    )


def test_in_filter_lists_values():
    roles = pbir.in_filter(C("Geo", "Role"), ["Focus", "Peer"])
    condition = roles["filter"]["Where"][0]["Condition"]["In"]
    assert condition["Values"] == [
        [{"Literal": {"Value": "'Focus'"}}],
        [{"Literal": {"Value": "'Peer'"}}],
    ]
    band = pbir.in_filter(C("AgeGroup", "IsBand"), [True])
    assert band["filter"]["Where"][0]["Condition"]["In"]["Values"] == [
        [{"Literal": {"Value": "true"}}]
    ]


def test_hidden_page():
    body = pbir.page_json(Page("tip", "Tip", [], hidden=True, width=320, height=240))
    assert body["visibility"] == "HiddenInViewMode"
    assert (body["width"], body["height"]) == (320, 240)


def _definition(tmp_path):
    (tmp_path / "pages").mkdir()
    (tmp_path / "pages" / "pages.json").write_text(
        json.dumps({"pageOrder": ["old"], "activePageName": "old"}), encoding="utf-8"
    )
    return tmp_path


def test_scaffold_writes_new_pages_first_and_keeps_the_others(tmp_path):
    definition = _definition(tmp_path)
    page = Page("one", "One", [Visual("a", "shape", 0, 0, 8, 8)])
    assert pbir.scaffold([page], definition) == ["One"]
    meta = json.loads((definition / "pages" / "pages.json").read_text(encoding="utf-8"))
    page_id = pbir.object_id("one")
    assert meta["pageOrder"] == [page_id, "old"]
    assert meta["activePageName"] == page_id
    visual = definition / "pages" / page_id / "visuals" / pbir.object_id("one", "a") / "visual.json"
    assert visual.exists()


def test_scaffold_never_overwrites_a_page_without_force(tmp_path):
    definition = _definition(tmp_path)
    page = Page("one", "One", [Visual("a", "shape", 0, 0, 8, 8)])
    pbir.scaffold([page], definition)
    page_file = definition / "pages" / pbir.object_id("one") / "page.json"
    page_file.write_text("refined in Desktop", encoding="utf-8")
    assert pbir.scaffold([page], definition) == []
    assert page_file.read_text(encoding="utf-8") == "refined in Desktop"
    assert pbir.scaffold([page], definition, force=True) == ["One"]
    assert json.loads(page_file.read_text(encoding="utf-8"))["displayName"] == "One"


def test_duplicate_visual_keys_are_rejected(tmp_path):
    page = Page("one", "One", [Visual("a", "shape", 0, 0, 8, 8), Visual("a", "shape", 8, 0, 8, 8)])
    with pytest.raises(ValueError, match="duplicate"):
        pbir.scaffold([page], _definition(tmp_path))

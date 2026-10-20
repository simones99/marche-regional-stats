import json
import re
import sys

import pytest

from marche_stats import cli, pbir
from marche_stats.pbir import C, M, Page, Visual


def test_object_id_is_stable_hex():
    name = pbir.object_id("overview", "kpi")
    assert name == pbir.object_id("overview", "kpi")
    assert re.fullmatch(r"[0-9a-f]{20}", name)
    assert name != pbir.object_id("overview", "kpi-2")
    assert pbir.object_id("a", "b/c") != pbir.object_id("a/b", "c")


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


def test_alt_text_bound_to_a_measure_and_container_objects():
    off = {"background": [{"properties": {"show": pbir.literal(False)}}]}
    visual = Visual("name", "card", 0, 0, 8, 8, alt=M("Focus region name"), container=off)
    container = pbir.visual_json("page", visual, order=0)["visual"]["visualContainerObjects"]
    assert container["general"][0]["properties"]["altText"] == {
        "expr": pbir.field_expr(M("Focus region name"))
    }
    assert container["background"] == off["background"]


def test_visuals_other_than_shapes_and_textboxes_need_alt_text(tmp_path):
    page = Page("one", "One", [Visual("kpi", "card", 0, 0, 8, 8, roles={"Values": [M("X")]})])
    with pytest.raises(ValueError, match="One: kpi has no alt text"):
        pbir.scaffold([page], _definition(tmp_path))


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
    assert meta["activePageName"] == "old"
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
    assert pbir.scaffold([page], definition, force={"one"}) == ["One"]
    assert json.loads(page_file.read_text(encoding="utf-8"))["displayName"] == "One"


def test_force_rewrites_only_the_named_pages(tmp_path):
    definition = _definition(tmp_path)
    pages = [Page("one", "One", []), Page("two", "Two", [])]
    pbir.scaffold(pages, definition)
    files = {k: definition / "pages" / pbir.object_id(k) / "page.json" for k in ("one", "two")}
    for path in files.values():
        path.write_text("refined in Desktop", encoding="utf-8")
    assert pbir.scaffold(pages, definition, force={"one"}) == ["One"]
    assert json.loads(files["one"].read_text(encoding="utf-8"))["displayName"] == "One"
    assert files["two"].read_text(encoding="utf-8") == "refined in Desktop"


def test_failed_page_leaves_no_folder_behind(tmp_path):
    definition = _definition(tmp_path)
    bad = Visual("a", "shape", 0, 0, 8, 8, objects={"o": {1, 2}})
    with pytest.raises(TypeError):
        pbir.scaffold([Page("one", "One", [bad])], definition)
    assert [p.name for p in (definition / "pages").iterdir()] == ["pages.json"]


def _meta(definition):
    return json.loads((definition / "pages" / "pages.json").read_text(encoding="utf-8"))


def test_rerun_leaves_pages_json_untouched(tmp_path):
    definition = _definition(tmp_path)
    pages = [Page("one", "One", []), Page("two", "Two", [])]
    pbir.scaffold(pages, definition)
    path = definition / "pages" / "pages.json"
    before = path.read_bytes()
    assert pbir.scaffold(pages, definition) == []
    assert path.read_bytes() == before
    assert len(_meta(definition)["pageOrder"]) == len(set(_meta(definition)["pageOrder"]))


def test_desktop_order_and_active_page_survive_a_rerun(tmp_path):
    definition = _definition(tmp_path)
    one, two, three = (Page(k, k.title(), []) for k in ("one", "two", "three"))
    pbir.scaffold([one, two], definition)
    ids = {k: pbir.object_id(k) for k in ("one", "two", "three")}
    path = definition / "pages" / "pages.json"
    path.write_text(
        json.dumps(
            {"pageOrder": ["old", ids["two"], "extra", ids["one"]], "activePageName": ids["two"]}
        ),
        encoding="utf-8",
    )
    assert pbir.scaffold([one, two, three], definition) == ["Three"]
    meta = _meta(definition)
    assert meta["pageOrder"] == ["old", ids["two"], ids["three"], "extra", ids["one"]]
    assert meta["activePageName"] == ids["two"]


def test_active_page_is_repaired_when_missing(tmp_path):
    definition = _definition(tmp_path)
    (definition / "pages" / "pages.json").write_text(
        json.dumps({"pageOrder": ["old"], "activePageName": "gone"}), encoding="utf-8"
    )
    pbir.scaffold([Page("one", "One", [])], definition)
    assert _meta(definition)["activePageName"] == pbir.object_id("one")


def test_duplicate_page_keys_and_empty_layout_are_rejected(tmp_path):
    definition = _definition(tmp_path)
    with pytest.raises(ValueError, match="duplicate page keys.*one"):
        pbir.scaffold([Page("one", "One", []), Page("one", "Uno", [])], definition)
    with pytest.raises(ValueError, match="no pages"):
        pbir.scaffold([], definition)


def test_duplicate_visual_keys_are_rejected(tmp_path):
    page = Page("one", "One", [Visual("a", "shape", 0, 0, 8, 8), Visual("a", "shape", 8, 0, 8, 8)])
    with pytest.raises(ValueError, match="duplicate"):
        pbir.scaffold([page], _definition(tmp_path))


@pytest.mark.skipif(sys.platform != "win32", reason="Windows file locking")
def test_locked_page_is_left_intact_when_forced(tmp_path, monkeypatch):
    monkeypatch.setattr(pbir.time, "sleep", lambda seconds: None)
    definition = _definition(tmp_path)
    page = Page("one", "One", [Visual("a", "shape", 0, 0, 8, 8)])
    pbir.scaffold([page], definition)
    folder = definition / "pages" / pbir.object_id("one")
    before = sorted(p.relative_to(folder) for p in folder.rglob("*"))
    with open(folder / "page.json"):
        with pytest.raises(PermissionError):
            pbir.scaffold([page], definition, force={"one"})
    assert sorted(p.relative_to(folder) for p in folder.rglob("*")) == before


def test_force_keys_must_be_page_keys(tmp_path):
    page = Page("one", "One", [])
    with pytest.raises(ValueError, match="unknown page keys.*One"):
        pbir.scaffold([page], _definition(tmp_path), force={"One"})


def test_hidden_active_page_moves_to_the_first_visible_layout_page(tmp_path):
    definition = _definition(tmp_path)
    old = definition / "pages" / "old"
    old.mkdir()
    (old / "page.json").write_text(json.dumps({"visibility": "HiddenInViewMode"}), "utf-8")
    pbir.scaffold([Page("tip", "Tip", [], hidden=True), Page("one", "One", [])], definition)
    assert _meta(definition)["activePageName"] == pbir.object_id("one")


def _flaky_rename(monkeypatch, failures):
    """Path.rename that raises PermissionError for the first `failures` calls."""
    real, calls, sleeps = pbir.Path.rename, [], []

    def rename(self, target):
        calls.append(self)
        if len(calls) <= failures:
            raise PermissionError(13, "locked", str(self))
        return real(self, target)

    monkeypatch.setattr(pbir.Path, "rename", rename)
    monkeypatch.setattr(pbir.time, "sleep", sleeps.append)
    return sleeps


def test_rename_is_retried_while_a_file_is_briefly_locked(tmp_path, monkeypatch):
    definition = _definition(tmp_path)
    sleeps = _flaky_rename(monkeypatch, failures=2)
    assert pbir.scaffold([Page("one", "One", [])], definition) == ["One"]
    assert sleeps == [0.1, 0.2]
    assert (definition / "pages" / pbir.object_id("one") / "page.json").exists()


def test_rename_gives_up_after_five_attempts(tmp_path, monkeypatch):
    definition = _definition(tmp_path)
    sleeps = _flaky_rename(monkeypatch, failures=99)
    with pytest.raises(PermissionError):
        pbir.scaffold([Page("one", "One", [])], definition)
    assert sleeps == [0.1, 0.2, 0.4, 0.8]
    assert [p.name for p in (definition / "pages").iterdir()] == ["pages.json"]


def test_cli_scaffold_report_rejects_an_unknown_page(tmp_path):
    with pytest.raises(SystemExit):
        cli.main(["scaffold-report", "--powerbi", str(tmp_path), "--force", "nowhere"])


def test_cli_scaffold_report_warns_when_desktop_is_open(tmp_path, monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(cli, "_desktop_running", lambda: True)
    monkeypatch.setattr(
        pbir, "scaffold", lambda pages, definition, force: calls.append(force) or ["Overview"]
    )
    assert cli.main(["scaffold-report", "--powerbi", str(tmp_path), "--force", "overview"]) == 0
    out, err = capsys.readouterr()
    assert out == "wrote Overview\n"
    assert "Power BI Desktop is open" in err
    assert calls == [["overview"]]


def test_cli_scaffold_report_explains_a_locked_file(tmp_path, monkeypatch, capsys):
    def locked(pages, definition, force):
        raise PermissionError(13, "Access is denied", "pages/x/page.json")

    monkeypatch.setattr(cli, "_desktop_running", lambda: False)
    monkeypatch.setattr(pbir, "scaffold", locked)
    assert cli.main(["scaffold-report", "--powerbi", str(tmp_path)]) == 1
    _, err = capsys.readouterr()
    assert err.startswith("cannot replace pages/x/page.json: a file is locked")

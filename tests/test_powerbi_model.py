"""Static checks of the Power BI project: names and references that Desktop would reject.

DAX and Power Query cannot run outside Power BI Desktop; the refresh is the real test.
These checks catch a renamed column or measure, a missing table file or a space-indented
TMDL line before the project is opened.
"""

import json
import re
from pathlib import Path

import pytest

from marche_stats import sources

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "powerbi" / sources.MODEL_DEFINITION
REPORT = ROOT / "powerbi" / "marche-regional-profile.Report" / "definition"
NAME = r"('[^']+'|[^\s=.]+)"
# Measure and calculation item expressions: name, then the DAX after " = ".
EXPRESSION = re.compile(rf"^(\t+)(?:measure|calculationItem) {NAME}\s*=(.*)$")
# String literals and comments, dropped before looking for references.
DAX_IGNORED = re.compile(r'"(?:[^"]|"")*"|//[^\n]*|--[^\n]*|/\*.*?\*/', re.S)
# Qualified references: Table[Name] or 'Table name'[Name].
DAX_REFERENCE = re.compile(r"('[^']+'|\b[A-Za-z_]\w*)\[([^\]]+)\]")


def _name(raw: str) -> str:
    raw = raw.strip()
    return raw[1:-1] if raw.startswith("'") else raw


def model_tables() -> dict[str, dict[str, set[str]]]:
    tables = {}
    for path in sorted((MODEL / "tables").glob("*.tmdl")):
        text = path.read_text(encoding="utf-8")
        match = re.search(r"^table (.+)$", text, re.M)
        assert match, path.name
        name = _name(match.group(1))
        tables[name] = {
            "columns": {_name(m) for m in re.findall(rf"^\tcolumn {NAME}", text, re.M)},
            "measures": {_name(m) for m in re.findall(rf"^\tmeasure {NAME}", text, re.M)},
        }
    return tables


def test_model_references_every_table_file():
    text = (MODEL / "model.tmdl").read_text(encoding="utf-8")
    refs = {_name(m) for m in re.findall(r"^ref table (.+)$", text, re.M)}
    assert refs == set(model_tables())


def test_tmdl_lines_are_tab_indented():
    for path in MODEL.rglob("*.tmdl"):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            assert not line.startswith(" "), f"{path.name}:{number} starts with a space"


def test_measure_properties_come_before_child_objects():
    # formatStringDefinition and annotation are child objects: TMDL rejects a property
    # (displayFolder: …) after them with "Invalid indentation".
    for path in MODEL.rglob("*.tmdl"):
        child = None
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if re.match(r"\t\S", line):  # a new object: measure, column, partition…
                child = None
            elif re.match(r"\t\t(formatStringDefinition|annotation) ", line):
                child = number
            elif child and re.match(r"\t\t\w+:", line):
                pytest.fail(f"{path.name}:{number} is a property after the child object on {child}")


def test_relationships_use_existing_columns():
    path = MODEL / "relationships.tmdl"
    if not path.exists():
        pytest.skip("no relationships yet")
    tables = model_tables()
    text = path.read_text(encoding="utf-8")
    for ref in re.findall(r"^\t(?:from|to)Column: (.+)$", text, re.M):
        table, column = re.match(rf"{NAME}\.(.+)$", ref.strip()).groups()
        assert _name(table) in tables, ref
        assert _name(column) in tables[_name(table)]["columns"], ref


def test_measure_references_exist():
    tables = model_tables()
    if "_Measures" not in tables:
        pytest.skip("no measures yet")
    measures = tables["_Measures"]["measures"]
    text = "\n".join(p.read_text(encoding="utf-8") for p in (MODEL / "tables").glob("*.tmdl"))
    named = re.findall(r"NAMEOF\s*\(\s*'?_Measures'?\[([^\]]+)\]", text)
    selected = [
        m
        for args in re.findall(r"ISSELECTEDMEASURE\s*\(((?:[^()]|\([^()]*\))*)\)", text)
        for m in re.findall(r"\[([^\]]+)\]", args)
    ]
    for measure in named + selected:
        assert measure in measures, measure


def _field_refs(node):
    """Yield (table, field) for every model field under node.

    Report-level measures (SourceRef Schema "extension") are not in the model and are skipped.
    """
    if isinstance(node, dict):
        source = node.get("Expression", {}).get("SourceRef", {})
        if "Entity" in source and "Property" in node and source.get("Schema") != "extension":
            yield source["Entity"], node["Property"]
        for value in node.values():
            yield from _field_refs(value)
    elif isinstance(node, list):
        for value in node:
            yield from _field_refs(value)


def _visual_field_refs(visual):
    """Fields of the visual's query and filters, not formatting selectors in objects."""
    yield from _field_refs(visual.get("visual", {}).get("query", {}))
    yield from _field_refs(visual.get("filterConfig", {}))


def test_report_fields_exist_in_model():
    tables = model_tables()
    for path in REPORT.glob("pages/*/visuals/*/visual.json"):
        visual = json.loads(path.read_text(encoding="utf-8"))
        for entity, prop in _visual_field_refs(visual):
            assert entity in tables, f"{path.parent.name}: table {entity}"
            fields = tables[entity]["columns"] | tables[entity]["measures"]
            assert prop in fields, f"{path.parent.name}: {entity}[{prop}]"


def dax_expressions(text: str) -> list[str]:
    """DAX of every measure and calculation item in a TMDL table file.

    An expression starts after " = " and runs over the lines indented deeper than its
    properties; the first line at the property level or above (formatString, ///, the next
    measure, column or partition) ends it, so Power Query partitions are never read.
    """
    lines = text.splitlines()
    expressions = []
    for number, line in enumerate(lines):
        match = EXPRESSION.match(line)
        if not match:
            continue
        depth = len(match.group(1))
        body = [match.group(3)]
        for following in lines[number + 1 :]:
            indent = len(following) - len(following.lstrip("\t"))
            if following.strip() and indent <= depth + 1:
                break
            body.append(following)
        expressions.append("\n".join(body))
    return expressions


def test_measure_column_references_exist():
    tables = model_tables()
    for path in sorted((MODEL / "tables").glob("*.tmdl")):
        for expression in dax_expressions(path.read_text(encoding="utf-8")):
            code = DAX_IGNORED.sub("", expression)
            for table, name in DAX_REFERENCE.findall(code):
                ref = f"{path.name}: {table}[{name}]"
                assert _name(table) in tables, ref
                fields = tables[_name(table)]["columns"] | tables[_name(table)]["measures"]
                assert name in fields, ref


def test_measure_table_has_the_spec_indicators():
    measures = model_tables()["_Measures"]["measures"]
    assert {
        "Population",
        "Population change 5y %",
        "Share aged 0-14",
        "Share aged 65+",
        "Share aged 80+",
        "Deaths",
        "Crude death rate per 1,000",
        "GDP per inhabitant (EUR)",
        "GDP per inhabitant (PPS, EU = 100)",
        "Unemployment rate",
        "Students enrolled",
        "Tertiary students per 1,000 residents",
        "Active companies",
        "Active companies change %",
        "Companies per 1,000 residents",
        "Reconciliation status",
    } <= measures


def test_phase_b_tables_and_columns():
    tables = model_tables()
    for name in ("ProvinceShape", "Seasonality", "Benchmark", "Benchmark point", "Data source"):
        assert name in tables, name
    assert {"GeoCode", "Path", "LabelX", "LabelY"} <= tables["ProvinceShape"]["columns"]
    assert {"Month", "MonthName", "Effect"} <= tables["Seasonality"]["columns"]
    assert {"Benchmark", "Item", "ValueItem", "Order"} <= tables["Benchmark"]["columns"]
    assert {"Code", "Area", "Role", "Row", "Indicator", "Point"} <= tables["Benchmark point"][
        "columns"
    ]
    assert {"Source", "Order"} <= tables["Data source"]["columns"]
    assert "ShortName" in tables["ISCED"]["columns"]
    assert "ShortName" in tables["Sector"]["columns"]


def test_report_visual_measures():
    assert {
        "Focus region name",
        "Country name",
        "Data up to",
        "Population (men, negative)",
        "Population (women)",
        "Students (women, negative)",
        "Students (men)",
        "Pyramid colour",
        "Education level colour",
        "Area colour",
        "Change colour",
        "Active companies at month-end",
        "Active companies, December",
        "Active companies index",
        "Sector change, ten largest",
        "Seasonal effect",
        "Forecast MAPE",
        "Forecast chart actual",
        "Forecast chart forecast",
        "Latest period",
        "Area name",
        "Flags text",
    } <= model_tables()["_Measures"]["measures"]


def test_kpi_province_map_and_dot_measures():
    assert {
        "KPI gap Population",
        "KPI gap Share aged 65+",
        "KPI gap Crude death rate",
        "KPI gap Unemployment rate",
        "KPI gap GDP per inhabitant",
        "KPI gap Active companies",
        "Province indicator value",
        "Province indicator label",
        "Province gap to region",
        "Highlight population change",
        "Highlight aged 65+",
        "Highlight death rate",
        "Highlight companies",
        "Highlight GDP",
        "Map SVG",
        "Dot value",
        "Dot position",
        "Dot row",
        "Rank row label",
        "Benchmark years",
    } <= model_tables()["_Measures"]["measures"]


REPORT_TEXT_PREFIXES = (
    "Overview",
    "Population",
    "Economy",
    "Education",
    "Provinces",
    "Business",
    "Benchmark",
    "About",
    "Province detail",
)


def test_report_text_measures():
    measures = model_tables()["_Measures"]["measures"]
    for prefix in REPORT_TEXT_PREFIXES:
        for part in ("headline lead", "headline accent", "paragraph"):
            assert f"{prefix} {part}" in measures

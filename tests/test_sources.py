# ruff: noqa: E501 (TMDL fixture lines are long by nature)
from pathlib import Path

import pytest
import requests

from marche_stats import sources

EXPRESSIONS = """\
expression FocusRegion = "ITI3" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]
\tqueryGroup: Parameters

expression PeerRegions = "ITI1,ITI2" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]

expression ProvinceRegions = "ITI31,ITI32" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]

expression Country = "IT" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]

expression StartYear = 2009 meta [IsParameterQuery=true, Type="Number", IsParameterQueryRequired=true]

expression RepoRawBase = "https://raw.example/repo/main" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]

expression CompaniesSourceUrl = "https://opendata.example/stock.csv" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]
"""

TABLE = """\
table Population
\tpartition Population = m
\t\tmode: import
\t\tsource =
\t\t\t\tlet
\t\t\t\t    Source = fnEurostat(
\t\t\t\t        "demo_r_pjangrp3",
\t\t\t\t        "c[unit]=NR&c[sex]=T",
\t\t\t\t        {"EU", "NUTS2", "NUTS3"}
\t\t\t\t    ),
\t\t\t\t    Nuts = Csv.Document(Web.Contents("https://gisco-services.ec.europa.eu/nuts.csv")),
\t\t\t\t    Fc = Csv.Document(Web.Contents(RepoRawBase & "/powerbi/data/forecast.csv"))
\t\t\t\tin
\t\t\t\t    Source
"""

GISCO_OK = "CNTR_CODE,NUTS_ID\nIT,ITI3\nIT,ITI31\nIT,ITI32\n"
EUROSTAT_OK = "geo,TIME_PERIOD,OBS_VALUE\nITI3,2024,10\nITI3,2025,\n"
EUROSTAT_FAULT = (
    "<S:Fault><faultcode>150</faultcode><faultstring>INVALID_QUERY_DIMENSION_VALUE: "
    "The following values for dimension are not allowed: GEO=ITI31.</faultstring></S:Fault>"
)


class FakeResponse:
    def __init__(self, status_code: int = 200, text: str = ""):
        self.status_code = status_code
        self.text = text

    def close(self) -> None:
        pass


def fake_get(routes: dict[str, FakeResponse]):
    def get(url: str, **_kwargs):
        for key, response in routes.items():
            if key in url:
                return response
        return FakeResponse(404)

    return get


OK_ROUTES = {
    "gisco": FakeResponse(200, GISCO_OK),
    "ESTAT": FakeResponse(200, EUROSTAT_OK),
    "opendata.example": FakeResponse(200),
    "raw.example": FakeResponse(200),
}


@pytest.fixture
def definition(tmp_path: Path) -> Path:
    (tmp_path / "tables").mkdir()
    (tmp_path / "expressions.tmdl").write_text(EXPRESSIONS, encoding="utf-8")
    (tmp_path / "tables" / "Population.tmdl").write_text(TABLE, encoding="utf-8")
    return tmp_path


def test_parameters_are_read_from_expressions(definition):
    assert sources.parameters(definition) == {
        "FocusRegion": "ITI3",
        "PeerRegions": "ITI1,ITI2",
        "ProvinceRegions": "ITI31,ITI32",
        "Country": "IT",
        "StartYear": "2009",
        "RepoRawBase": "https://raw.example/repo/main",
        "CompaniesSourceUrl": "https://opendata.example/stock.csv",
    }


def test_eurostat_calls_are_found_across_lines(definition):
    assert sources.eurostat_calls(definition) == [
        sources.EurostatCall(
            "Population", "demo_r_pjangrp3", "c[unit]=NR&c[sex]=T", ("EU", "NUTS2", "NUTS3")
        )
    ]


def test_eurostat_url_lists_geo_codes_by_level(definition):
    call = sources.eurostat_calls(definition)[0]
    url = sources.eurostat_url(call, sources.parameters(definition))
    assert url == (
        "https://ec.europa.eu/eurostat/api/dissemination/sdmx/3.0/data/dataflow/ESTAT/"
        "demo_r_pjangrp3/1.0?c[geo]=EU27_2020,ITI3,ITI1,ITI2,ITI31,ITI32"
        "&c[unit]=NR&c[sex]=T&c[TIME_PERIOD]=ge:2009"
        "&format=csvdata&formatVersion=1.0&labels=id&compress=false"
    )


def test_check_passes_when_every_source_answers(definition):
    results = sources.check(definition, get=fake_get(OK_ROUTES))
    assert [r.source for r in results] == [
        "GISCO NUTS codes",
        "ProvinceRegions matches GISCO",
        "Eurostat demo_r_pjangrp3 (Population)",
        "Chamber of Commerce archive",
        "Repository file /powerbi/data/forecast.csv",
    ]
    assert all(r.ok for r in results)
    assert "latest 2024" in results[2].detail


def test_check_reports_the_eurostat_fault_message(definition):
    fault = EUROSTAT_FAULT.replace("not allowed", "not &apos;allowed&apos;")
    get = fake_get({**OK_ROUTES, "ESTAT": FakeResponse(400, fault)})
    eurostat = [r for r in sources.check(definition, get=get) if r.source.startswith("Eurostat")]
    assert not eurostat[0].ok
    assert "HTTP 400" in eurostat[0].detail
    assert "GEO=ITI31" in eurostat[0].detail
    assert "'allowed'" in eurostat[0].detail


def test_check_flags_provinces_that_differ_from_gisco(definition):
    gisco = GISCO_OK + "IT,ITI33\n"
    get = fake_get({**OK_ROUTES, "gisco": FakeResponse(200, gisco)})
    provinces = next(
        r for r in sources.check(definition, get=get) if r.source.startswith("ProvinceRegions")
    )
    assert not provinces.ok
    assert "ITI31,ITI32,ITI33" in provinces.detail


def test_report_prints_one_line_per_result():
    text = sources.report(
        [
            sources.Result("A", True, "fine", "https://a"),
            sources.Result("B", False, "HTTP 404", "https://b"),
        ]
    )
    assert text.splitlines() == ["OK    A: fine", "FAIL  B: HTTP 404", "      https://b"]


def test_check_fails_when_the_model_has_no_eurostat_calls(definition):
    (definition / "tables" / "Population.tmdl").write_text(
        TABLE.replace("fnEurostat(", "other("), encoding="utf-8"
    )
    results = sources.check(definition, get=fake_get(OK_ROUTES))
    failing = [r for r in results if not r.ok]
    assert [r.detail for r in failing] == ["no fnEurostat calls found in the model tables"]


def test_check_fails_when_the_model_has_no_gisco_source(definition):
    (definition / "tables" / "Population.tmdl").write_text(
        TABLE.replace("gisco-services.ec.europa.eu", "nuts.example"), encoding="utf-8"
    )
    results = sources.check(definition, get=fake_get(OK_ROUTES))
    provinces = next(r for r in results if r.source.startswith("ProvinceRegions"))
    assert not provinces.ok
    assert provinces.detail == "no GISCO source found in the model tables"


def test_unknown_level_is_a_failing_result_not_a_crash(definition):
    (definition / "tables" / "Population.tmdl").write_text(
        TABLE.replace('"NUTS3"', '"NUTS9"'), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="NUTS9.*EU, Country, NUTS2, NUTS3"):
        sources.geo_codes(sources.parameters(definition), ("NUTS9",))
    results = sources.check(definition, get=fake_get(OK_ROUTES))
    eurostat = next(r for r in results if r.source.startswith("Eurostat"))
    assert not eurostat.ok
    assert "NUTS9" in eurostat.detail


def test_malformed_csv_is_a_failing_result(definition):
    routes = {**OK_ROUTES, "gisco": FakeResponse(200, "a,b\n1,2\n")}
    routes["ESTAT"] = FakeResponse(200, "x,y\n1,2\n")
    results = sources.check(definition, get=fake_get(routes))
    provinces = next(r for r in results if r.source.startswith("ProvinceRegions"))
    assert not provinces.ok
    assert "NUTS_ID" in provinces.detail


def test_a_connection_error_fails_one_source_and_the_rest_still_run(definition):
    inner = fake_get(OK_ROUTES)

    def get(url, **kwargs):
        if "ESTAT" in url:
            raise requests.ConnectionError("boom")
        return inner(url, **kwargs)

    results = sources.check(definition, get=get)
    assert len(results) == 5
    failing = [r for r in results if not r.ok]
    assert [r.source for r in failing] == ["Eurostat demo_r_pjangrp3 (Population)"]
    assert "boom" in failing[0].detail

import pytest
import requests

from marche_stats import eurostat


def test_read_sdmx_keeps_dimensions_flags_and_missing_values(tmp_path):
    path = tmp_path / "x.csv"
    path.write_text(
        "DATAFLOW,LAST UPDATE,freq,unit,sex,geo,TIME_PERIOD,OBS_VALUE,OBS_FLAG,CONF_STATUS\n"
        "ESTAT:X(1.0),01/10/26,A,PC,T,ITI3,2024,7.7,u,\n"
        "ESTAT:X(1.0),01/10/26,A,PC,T,ITI3,2025,:,,\n"
        "ESTAT:X(1.0),01/10/26,A,PC,T,NA,2025,1.0,,\n"
    )
    frame = eurostat.read_sdmx(path)
    assert list(frame.columns) == ["unit", "sex", "geo", "year", "value", "flag"]
    assert frame["year"].tolist() == [2024, 2025, 2025]
    assert frame["value"].iloc[0] == 7.7
    assert frame["value"].isna().tolist() == [False, True, False]
    assert frame["flag"].tolist() == ["u", "", ""]
    assert frame["geo"].iloc[2] == "NA"  # a geo code, not a missing value


def test_regional_url_puts_every_comparison_geo_last():
    url = eurostat.dataset_url("gdp", "A.PPS_HAB_EU27_2020", 2013, eurostat.COMPARISON_GEOS)
    assert "/data/gdp/A.PPS_HAB_EU27_2020.ITI3+ITH5+ITI1+ITI2+ITI4+ITF1+IT+EU27_2020?" in url
    assert url.endswith("startPeriod=2013")


def test_synthetic_extracts_pass_the_coverage_check(eurostat_dir):
    for filename in eurostat.REGIONAL_DATASETS:
        eurostat.check_coverage(eurostat.read_sdmx(eurostat_dir / filename), filename)


def test_missing_geography_is_named(eurostat_dir):
    frame = eurostat.read_sdmx(eurostat_dir / "gdp.csv")
    frame = frame[~((frame["geo"] == "ITI2") & (frame["year"] == 2020))]
    with pytest.raises(eurostat.CoverageError, match="gdp.csv: missing ITI2 2020"):
        eurostat.check_coverage(frame, "gdp.csv")


def test_missing_value_counts_as_a_gap(eurostat_dir):
    frame = eurostat.read_sdmx(eurostat_dir / "gdp.csv")
    frame.loc[(frame["geo"] == "IT") & (frame["year"] == 2015), "value"] = float("nan")
    with pytest.raises(eurostat.CoverageError, match="IT 2015"):
        eurostat.check_coverage(frame, "gdp.csv")


def test_known_gap_is_allowed_only_for_its_file(eurostat_dir):
    deaths = eurostat.read_sdmx(eurostat_dir / "regional_deaths.csv")
    assert not ((deaths["geo"] == "EU27_2020") & (deaths["year"] == 2024)).any()
    eurostat.check_coverage(deaths, "regional_deaths.csv")
    with pytest.raises(eurostat.CoverageError, match="EU27_2020 2024"):
        eurostat.check_coverage(deaths, "gdp.csv")


def test_no_focus_data_is_an_error(eurostat_dir):
    frame = eurostat.read_sdmx(eurostat_dir / "gdp.csv")
    with pytest.raises(eurostat.CoverageError, match="no data for ITI3"):
        eurostat.check_coverage(frame[frame["geo"] != "ITI3"], "gdp.csv")


def test_http_error_names_dataset_and_url(monkeypatch, tmp_path):
    class Failing:
        def raise_for_status(self):
            raise requests.HTTPError("503 Service Unavailable")

    monkeypatch.setattr(eurostat.requests, "get", lambda url, timeout: Failing())
    with pytest.raises(
        eurostat.DownloadError, match=r"demo_r_pjanaggr3: download failed from https://"
    ):
        eurostat.download(tmp_path)


def test_xml_error_body_is_reported_not_parsed(monkeypatch, tmp_path):
    class XmlFault:
        content = b'<?xml version="1.0"?><S:Fault><faultstring>EXTRACTION_TOO_BIG</faultstring>'

        def raise_for_status(self):
            pass

    monkeypatch.setattr(eurostat.requests, "get", lambda url, timeout: XmlFault())
    with pytest.raises(eurostat.DownloadError, match="expected SDMX-CSV.*EXTRACTION_TOO_BIG"):
        eurostat.download(tmp_path)

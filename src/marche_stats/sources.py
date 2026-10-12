"""Check the data sources of the Power BI semantic model.

The Power Query code in the model's TMDL files is the one description of what the report
downloads. This module reads it, rebuilds each request and runs it, so a source that
changes (a dataset that drops a year, a file that moves) shows up before the next refresh.
"""

from __future__ import annotations

import csv
import io
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import requests

MODEL_DEFINITION = Path("marche-regional-profile.SemanticModel") / "definition"
EUROSTAT_BASE = "https://ec.europa.eu/eurostat/api/dissemination/sdmx/3.0/data/dataflow/ESTAT"
EUROSTAT_FORMAT = "format=csvdata&formatVersion=1.0&labels=id&compress=false"
TIMEOUT_SECONDS = 180

PARAMETER = re.compile(
    r'^expression (\w+) = (?:"([^"]*)"|(\d+)) meta \[IsParameterQuery=true', re.M
)
EUROSTAT_CALL = re.compile(r'fnEurostat\(\s*"([^"]+)"\s*,\s*"([^"]*)"\s*,\s*\{([^}]*)\}\s*\)')
WEB_LITERAL = re.compile(r'Web\.Contents\(\s*"(https://[^"]+)"')
REPO_FILE = re.compile(r'RepoRawBase\s*&\s*"([^"]+)"')


@dataclass(frozen=True)
class EurostatCall:
    table: str
    dataset: str
    filters: str
    levels: tuple[str, ...]


@dataclass(frozen=True)
class Result:
    source: str
    ok: bool
    detail: str
    url: str


def parameters(definition: Path) -> dict[str, str]:
    """Power Query parameters, as text, from expressions.tmdl."""
    text = (definition / "expressions.tmdl").read_text(encoding="utf-8")
    return {m[1]: m[2] if m[2] is not None else m[3] for m in PARAMETER.finditer(text)}


def _tables(definition: Path) -> dict[str, str]:
    return {
        path.stem: path.read_text(encoding="utf-8")
        for path in sorted((definition / "tables").glob("*.tmdl"))
    }


def eurostat_calls(definition: Path) -> list[EurostatCall]:
    """Every fnEurostat(dataset, filters, levels) call in the model's tables."""
    calls = []
    for table, text in _tables(definition).items():
        for m in EUROSTAT_CALL.finditer(text):
            levels = tuple(re.findall(r'"([^"]+)"', m[3]))
            calls.append(EurostatCall(table, m[1], m[2], levels))
    return calls


def geo_codes(params: dict[str, str], levels: tuple[str, ...]) -> list[str]:
    """Geo codes requested for each level, the same rule as fnEurostat in Power Query."""
    by_level = {
        "EU": ["EU27_2020"],
        "Country": [params["Country"]],
        "NUTS2": [params["FocusRegion"], *params["PeerRegions"].split(",")],
        "NUTS3": params["ProvinceRegions"].split(","),
    }
    return [code for level in levels for code in by_level[level]]


def eurostat_url(call: EurostatCall, params: dict[str, str]) -> str:
    parts = [
        f"c[geo]={','.join(geo_codes(params, call.levels))}",
        call.filters,
        f"c[TIME_PERIOD]=ge:{params['StartYear']}",
        EUROSTAT_FORMAT,
    ]
    return f"{EUROSTAT_BASE}/{call.dataset}/1.0?{'&'.join(p for p in parts if p)}"


def check_eurostat(call: EurostatCall, url: str, get: Callable) -> Result:
    name = f"Eurostat {call.dataset} ({call.table})"
    try:
        response = get(url, timeout=TIMEOUT_SECONDS)
    except requests.RequestException as exc:
        return Result(name, False, str(exc), url)
    if response.status_code != 200:
        fault = re.search(r"<faultstring>(.*?)</faultstring>", response.text, re.S)
        message = fault.group(1) if fault else response.text[:200]
        return Result(name, False, f"HTTP {response.status_code}: {message}", url)
    rows = [r for r in csv.DictReader(io.StringIO(response.text)) if r.get("OBS_VALUE")]
    if not rows:
        return Result(name, False, "no observations", url)
    latest = max(r["TIME_PERIOD"] for r in rows)
    return Result(name, True, f"{len(rows):,} observations, latest {latest}", url)


def check_file(name: str, url: str, get: Callable) -> Result:
    try:
        response = get(url, timeout=TIMEOUT_SECONDS, stream=True)
    except requests.RequestException as exc:
        return Result(name, False, str(exc), url)
    response.close()
    return Result(name, response.status_code == 200, f"HTTP {response.status_code}", url)


def check_provinces(params: dict[str, str], gisco_csv: str) -> Result:
    """ProvinceRegions must list exactly the NUTS 3 children of FocusRegion."""
    focus = params["FocusRegion"]
    children = sorted(
        r["NUTS_ID"]
        for r in csv.DictReader(io.StringIO(gisco_csv))
        if r["NUTS_ID"].startswith(focus) and len(r["NUTS_ID"]) == len(focus) + 1
    )
    configured = sorted(params["ProvinceRegions"].split(","))
    detail = f"GISCO: {','.join(children)}; parameter: {','.join(configured)}"
    return Result("ProvinceRegions matches GISCO", children == configured, detail, "")


def check(definition: Path, get: Callable = requests.get) -> list[Result]:
    """Request every source the model uses and report each one."""
    params = parameters(definition)
    text = "\n".join(_tables(definition).values())
    results = []
    for url in sorted(set(WEB_LITERAL.findall(text))):
        if "gisco-services" not in url:
            results.append(check_file(url, url, get))
            continue
        try:
            response = get(url, timeout=TIMEOUT_SECONDS)
        except requests.RequestException as exc:
            results.append(Result("GISCO NUTS codes", False, str(exc), url))
            continue
        ok = response.status_code == 200
        results.append(Result("GISCO NUTS codes", ok, f"HTTP {response.status_code}", url))
        if ok:
            results.append(check_provinces(params, response.text))
    for call in eurostat_calls(definition):
        results.append(check_eurostat(call, eurostat_url(call, params), get))
    results.append(check_file("Chamber of Commerce archive", params["CompaniesSourceUrl"], get))
    for relative in sorted(set(REPO_FILE.findall(text))):
        url = params["RepoRawBase"] + relative
        results.append(check_file(f"Repository file {relative}", url, get))
    return results


def report(results: list[Result]) -> str:
    lines = []
    for r in results:
        lines.append(f"{'OK  ' if r.ok else 'FAIL'}  {r.source}: {r.detail}")
        if not r.ok and r.url:
            lines.append(f"      {r.url}")
    return "\n".join(lines)

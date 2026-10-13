"""Parse the semantic model with the TMDL serializer that Power BI Desktop uses.

tools/tmdl-check is a small .NET program on Microsoft.AnalysisServices. It catches the
structure errors that stop Desktop from opening the project ("Invalid indentation", an
unknown property) and that the static checks in test_powerbi_model.py may miss. It does not
check DAX or Power Query. Skipped where the dotnet SDK is not installed.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

from marche_stats import sources

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "powerbi" / sources.MODEL_DEFINITION
PROJECT = ROOT / "tools" / "tmdl-check"


@pytest.fixture(scope="module")
def tmdl_check():
    dotnet = shutil.which("dotnet")
    if dotnet is None:
        pytest.skip("dotnet SDK not installed")
    out = PROJECT / "bin" / "test"
    build = subprocess.run(
        [dotnet, "build", str(PROJECT), "-c", "Release", "-o", str(out), "--nologo", "-v", "q"],
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert build.returncode == 0, build.stdout + build.stderr

    def run(definition: Path) -> subprocess.CompletedProcess:
        return subprocess.run(
            [dotnet, str(out / "tmdl-check.dll"), str(definition)],
            capture_output=True,
            text=True,
            timeout=120,
        )

    return run


def test_desktop_parses_the_model(tmdl_check):
    result = tmdl_check(MODEL)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.startswith("OK: ")


def test_a_property_after_a_child_object_fails(tmdl_check, tmp_path):
    # The error Desktop reported on Phase B: displayFolder after an annotation or
    # formatStringDefinition of the same measure.
    definition = tmp_path / "definition"
    shutil.copytree(MODEL, definition)
    measures = definition / "tables" / "_Measures.tmdl"
    with measures.open("a", encoding="utf-8", newline="\r\n") as file:
        file.write("\n\tmeasure 'Broken order' = 1\n")
        file.write("\t\tannotation Note = x\n")
        file.write("\t\tdisplayFolder: Checks\n")
    result = tmdl_check(definition)
    assert result.returncode == 1
    assert result.stdout.startswith("FAIL: ")

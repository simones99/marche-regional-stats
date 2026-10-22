"""The showcase: the hand-written page, assembled with the report exports it presents.

The page refers to the exports under report/; this module is the only place that maps
those paths to the files Power BI Desktop and export-pngs produce.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from marche_stats.pngs import PAGE_SLUGS

PDF_NAME = "marche-regional-profile.pdf"


def _report_copies(exports: Path) -> dict[str, Path]:
    """Path in the showcase -> report export it is copied from."""
    copies = {f"report/{slug}.png": exports / "png" / f"{slug}.png" for slug in PAGE_SLUGS}
    copies[f"report/{PDF_NAME}"] = exports / PDF_NAME
    return copies


def build(source: Path, exports: Path, out: Path) -> list[Path]:
    """Copy the showcase folder and the report exports into out; return the written paths.

    Raises FileNotFoundError, before writing anything, if a report export is missing.
    """
    exports_by_target = _report_copies(exports)
    missing = [path for path in exports_by_target.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(
            "missing report exports: "
            + ", ".join(str(path) for path in missing)
            + " (export the PDF from Power BI Desktop, then run export-pngs)"
        )
    copies = {
        path.relative_to(source).as_posix(): path
        for path in sorted(source.rglob("*"))
        if path.is_file()
    }
    copies.update(exports_by_target)
    written = []
    for name, path in copies.items():
        target = out / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        written.append(target)
    return written

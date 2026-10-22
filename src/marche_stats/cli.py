"""Command line entry point."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from marche_stats import (
    companies,
    eurostat,
    pbir,
    pngs,
    powerbi_export,
    report,
    report_layout,
    showcase,
    sources,
)

ROOT = Path(__file__).resolve().parents[2]
LOCKED = (
    "cannot replace {}: a file is locked — close Power BI Desktop"
    " (antivirus/OneDrive can also hold files briefly) and run again"
)


def _desktop_running() -> bool:
    """True if Power BI Desktop is open (Windows only)."""
    if sys.platform != "win32":
        return False
    try:
        listing = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq PBIDesktop.exe", "/NH"],
            capture_output=True,
            text=True,
            check=False,
        ).stdout
    except OSError:
        return False
    return "pbidesktop.exe" in listing.lower()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="marche-stats", description=__doc__)
    parser.add_argument(
        "step",
        choices=[
            "download",
            "report",
            "run",
            "export-powerbi",
            "export-pngs",
            "check-sources",
            "scaffold-report",
            "build-showcase",
        ],
    )
    parser.add_argument(
        "--companies",
        type=Path,
        default=ROOT / "data" / "raw" / "active_companies_marche.csv",
        help="active companies file (semicolon-separated, wide by month)",
    )
    parser.add_argument(
        "--eurostat-dir",
        type=Path,
        default=ROOT / "data" / "raw",
        help="folder for the Eurostat and GISCO files",
    )
    parser.add_argument("--docs", type=Path, default=ROOT / "docs", help="output folder")
    parser.add_argument("--powerbi", type=Path, default=ROOT / "powerbi", help="Power BI folder")
    parser.add_argument(
        "--pdf",
        type=Path,
        default=ROOT / "powerbi" / "exports" / "marche-regional-profile.pdf",
        help="PDF exported from Power BI Desktop (export-pngs)",
    )
    parser.add_argument(
        "--exports",
        type=Path,
        default=ROOT / "powerbi" / "exports",
        help="report exports: the PDF and png/ (build-showcase)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "build" / "showcase",
        help="folder the showcase is assembled into (build-showcase)",
    )
    parser.add_argument("--holdout", type=int, default=24, help="test months for SARIMA")
    parser.add_argument(
        "--force",
        action="append",
        default=[],
        choices=[p.key for p in report_layout.pages()],
        metavar="PAGE",
        help="scaffold-report: rewrite this page (repeatable)",
    )
    args = parser.parse_args(argv)
    geojson = args.eurostat_dir / "marche_nuts3.geojson"

    if args.step == "export-powerbi":
        powerbi_export.build(args.companies, args.powerbi / "data", geojson, holdout=args.holdout)
        return 0
    if args.step == "export-pngs":
        for path in pngs.export(args.pdf, args.pdf.parent / "png"):
            print(path)
        return 0
    if args.step == "build-showcase":
        try:
            written = showcase.build(ROOT / "showcase", args.exports, args.out)
        except FileNotFoundError as error:
            print(f"error: {error}", file=sys.stderr)
            return 1
        print("\n".join(str(path) for path in written))
        return 0
    if args.step == "scaffold-report":
        if _desktop_running():
            print(
                "warning: Power BI Desktop is open: close it without saving,"
                " or its next save may overwrite these pages",
                file=sys.stderr,
            )
        definition = args.powerbi / "marche-regional-profile.Report" / "definition"
        try:
            written = pbir.scaffold(report_layout.pages(), definition, force=args.force)
        except PermissionError as error:
            print(LOCKED.format(error.filename or definition), file=sys.stderr)
            return 1
        print("\n".join(f"wrote {name}" for name in written) or "no new pages")
        return 0
    if args.step == "check-sources":
        results = sources.check(args.powerbi / sources.MODEL_DEFINITION)
        print(sources.report(results))
        return 0 if all(r.ok for r in results) else 1
    if args.step in ("download", "run"):
        companies.download(args.companies)
        eurostat.download(args.eurostat_dir)
    if args.step in ("report", "run"):
        report.build(args.companies, args.eurostat_dir, args.docs, holdout=args.holdout)
    if args.step == "run":
        powerbi_export.build(args.companies, args.powerbi / "data", geojson, holdout=args.holdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

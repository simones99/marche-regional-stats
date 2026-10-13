"""Command line entry point."""

from __future__ import annotations

import argparse
from pathlib import Path

from marche_stats import companies, eurostat, powerbi_export, report, sources

ROOT = Path(__file__).resolve().parents[2]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="marche-stats", description=__doc__)
    parser.add_argument(
        "step", choices=["download", "report", "run", "export-powerbi", "check-sources"]
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
    parser.add_argument("--holdout", type=int, default=24, help="test months for SARIMA")
    args = parser.parse_args(argv)
    geojson = args.eurostat_dir / "marche_nuts3.geojson"

    if args.step == "export-powerbi":
        powerbi_export.build(args.companies, args.powerbi / "data", geojson, holdout=args.holdout)
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

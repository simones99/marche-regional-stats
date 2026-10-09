"""Command line entry point."""

from __future__ import annotations

import argparse
from pathlib import Path

from marche_stats import companies, eurostat, model, report

ROOT = Path(__file__).resolve().parents[2]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="marche-stats", description=__doc__)
    parser.add_argument("step", choices=["download", "report", "model", "run"])
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
    parser.add_argument(
        "--model-dir",
        type=Path,
        default=ROOT / "data" / "model",
        help="folder for the Power BI model tables",
    )
    parser.add_argument("--holdout", type=int, default=24, help="test months for SARIMA")
    args = parser.parse_args(argv)

    if args.step in ("download", "run"):
        companies.download(args.companies)
        eurostat.download(args.eurostat_dir)
    if args.step in ("report", "run"):
        report.build(args.companies, args.eurostat_dir, args.docs, holdout=args.holdout)
    if args.step in ("model", "run"):
        tables = model.build_tables(args.eurostat_dir)
        problems = model.check_contract(tables)
        if problems:
            raise SystemExit("model contract failed:\n" + "\n".join(problems))
        model.write_tables(tables, args.model_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

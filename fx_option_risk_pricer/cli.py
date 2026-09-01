from __future__ import annotations

import argparse
import csv
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from fx_option_risk_pricer.io import load_positions
from fx_option_risk_pricer.pricing import price_option


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate FX option price and Greek risk reports.")
    parser.add_argument("--input", required=True, type=Path, help="CSV file containing FX option positions.")
    parser.add_argument("--output-dir", default=Path("reports"), type=Path, help="Directory for timestamped reports.")
    parser.add_argument("--stdout", action="store_true", help="Print report rows to stdout.")
    return parser


def run(input_path: Path, output_dir: Path, print_stdout: bool = False) -> Path:
    positions = load_positions(input_path)
    results = [asdict(price_option(position)) for position in positions]

    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report_path = output_dir / f"fx_option_risk_{timestamp}.csv"

    with report_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)

    if print_stdout:
        for result in results:
            print(result)

    return report_path


def main() -> None:
    args = _build_parser().parse_args()
    report_path = run(args.input, args.output_dir, args.stdout)
    print(f"Wrote risk report: {report_path}")


if __name__ == "__main__":
    main()

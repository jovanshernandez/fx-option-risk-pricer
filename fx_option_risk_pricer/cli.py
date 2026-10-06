"""Command line entry point: ``fx-risk-pricer report`` and ``fx-risk-pricer implied-vol``."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from rich.console import Console

from fx_option_risk_pricer.io import load_positions, write_csv
from fx_option_risk_pricer.models import OptionType
from fx_option_risk_pricer.portfolio import aggregate_by_pair, market_spots, scenario_grid
from fx_option_risk_pricer.pricing import implied_vol, price_position
from fx_option_risk_pricer.report import render, save_heatmap

DEFAULT_SPOT_SHOCKS = "-5,-3,-2,-1,0,1,2,3,5"
DEFAULT_VOL_SHOCKS = "-3,-2,-1,0,1,2,3"


def _shocks(text: str) -> list[float]:
    """Parse a comma-separated list of percent / vol-point shocks into fractions."""
    try:
        return [float(x) / 100.0 for x in text.split(",") if x.strip()]
    except ValueError:
        raise argparse.ArgumentTypeError(f"expected comma-separated numbers, got {text!r}") from None


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fx-risk-pricer",
        description="Garman-Kohlhagen pricing, Greeks and scenario risk for a book of FX options.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    report = sub.add_parser("report", help="Price a positions CSV and print/save the risk report.")
    report.add_argument("positions", type=Path, help="CSV of option positions (see examples/positions.csv).")
    report.add_argument("--output-dir", type=Path, default=Path("reports"), help="Where CSVs and the heatmap go.")
    report.add_argument("--spot-shocks", type=_shocks, default=_shocks(DEFAULT_SPOT_SHOCKS),
                        help=f"Relative spot shocks in %% (default {DEFAULT_SPOT_SHOCKS}).")
    report.add_argument("--vol-shocks", type=_shocks, default=_shocks(DEFAULT_VOL_SHOCKS),
                        help=f"Absolute vol shocks in vol points (default {DEFAULT_VOL_SHOCKS}).")
    report.add_argument("--pair", help="Restrict the scenario grid to one pair, e.g. EURUSD.")

    iv = sub.add_parser("implied-vol", help="Solve for the GK implied volatility of one option price.")
    iv.add_argument("--price", type=float, required=True, help="Premium in quote ccy per 1 unit of base.")
    iv.add_argument("--spot", type=float, required=True)
    iv.add_argument("--strike", type=float, required=True)
    iv.add_argument("--maturity", type=float, required=True, help="Years (ACT/365).")
    iv.add_argument("--r-dom", type=float, required=True, help="Quote-currency rate, continuous.")
    iv.add_argument("--r-for", type=float, required=True, help="Base-currency rate, continuous.")
    iv.add_argument("--type", choices=[t.value for t in OptionType], required=True)
    return parser


def run_report(args: argparse.Namespace, console: Console) -> None:
    positions = load_positions(args.positions)
    spots = market_spots(positions)
    risks = [price_position(p) for p in positions]
    pairs = aggregate_by_pair(risks, spots)
    grid = scenario_grid(positions, args.spot_shocks, args.vol_shocks, args.pair.upper() if args.pair else None)

    render(console, risks, pairs, grid)

    out = args.output_dir
    grid_rows = [
        {"vol_shock": dv, **{f"spot_{ds:+.4f}": round(v, 2) for ds, v in zip(grid.spot_shocks, row)}}
        for dv, row in zip(grid.vol_shocks, grid.pnl_usd)
    ]
    written = [
        write_csv(out / "positions_risk.csv", risks),
        write_csv(out / "pair_risk.csv", pairs),
        write_csv(out / "scenario_grid.csv", grid_rows),
        save_heatmap(grid, out / "scenario_heatmap.png"),
    ]
    console.print()
    console.print("Wrote " + ", ".join(str(p) for p in written), style="dim", soft_wrap=True)


def run_implied_vol(args: argparse.Namespace, console: Console) -> None:
    vol = implied_vol(args.price, args.spot, args.strike, args.maturity, args.r_dom, args.r_for, OptionType(args.type))
    console.print(f"implied vol: {vol * 100:.4f}%")


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    console = Console()
    try:
        if args.command == "report":
            run_report(args, console)
        else:
            run_implied_vol(args, console)
    except (OSError, ValueError) as exc:
        console.print(f"[red]error:[/] {exc}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

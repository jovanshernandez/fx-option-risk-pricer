"""Book-level views: risk by currency pair and a spot x vol scenario grid."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Sequence

from fx_option_risk_pricer.models import OptionPosition, PositionRisk
from fx_option_risk_pricer.pricing import gk_price

REPORTING_CCY = "USD"
MIN_VOL = 1e-4


def market_spots(positions: Sequence[OptionPosition]) -> dict[str, float]:
    """One spot per pair; positions on the same pair must agree."""
    spots: dict[str, float] = {}
    for p in positions:
        seen = spots.setdefault(p.pair, p.spot)
        if abs(seen - p.spot) > 1e-12:
            raise ValueError(f"{p.trade_id}: spot {p.spot} for {p.pair} disagrees with {seen} on another trade")
    return spots


def usd_rate(ccy: str, spots: dict[str, float]) -> float:
    """USD value of 1 unit of ``ccy``, using spots of USD pairs in the book."""
    if ccy == REPORTING_CCY:
        return 1.0
    if f"{ccy}USD" in spots:
        return spots[f"{ccy}USD"]
    if f"USD{ccy}" in spots:
        return 1.0 / spots[f"USD{ccy}"]
    raise ValueError(f"no {ccy}USD or USD{ccy} spot in the book to convert {ccy} amounts to USD")


@dataclass(frozen=True)
class PairRisk:
    pair: str
    trades: int
    net_notional_base: float
    net_delta_base: float  # base ccy
    gamma_1pct_base: float  # base ccy per 1% spot move
    vega_usd: float  # per 1 vol point
    theta_usd: float  # per calendar day
    mtm_usd: float


def aggregate_by_pair(risks: Sequence[PositionRisk], spots: dict[str, float]) -> list[PairRisk]:
    """Net delta and gamma stay in each pair's base ccy; vega, theta, MTM convert to USD."""
    grouped: dict[str, list[PositionRisk]] = defaultdict(list)
    for r in risks:
        grouped[r.pair].append(r)

    out = []
    for pair in sorted(grouped):
        rows = grouped[pair]
        fx = usd_rate(pair[3:], spots)
        out.append(
            PairRisk(
                pair=pair,
                trades=len(rows),
                net_notional_base=sum(r.notional for r in rows),
                net_delta_base=sum(r.delta_base for r in rows),
                gamma_1pct_base=sum(r.gamma_1pct_base for r in rows),
                vega_usd=sum(r.vega for r in rows) * fx,
                theta_usd=sum(r.theta for r in rows) * fx,
                mtm_usd=sum(r.mtm for r in rows) * fx,
            )
        )
    return out


@dataclass(frozen=True)
class ScenarioGrid:
    spot_shocks: list[float]  # relative, 0.01 = base ccy +1% vs quote
    vol_shocks: list[float]  # absolute, 0.01 = +1 vol point
    pnl_usd: list[list[float]]  # [vol_index][spot_index]
    pairs: list[str]


def scenario_grid(
    positions: Sequence[OptionPosition],
    spot_shocks: Sequence[float],
    vol_shocks: Sequence[float],
    pair: str | None = None,
) -> ScenarioGrid:
    """Full revaluation P&L under instantaneous spot and vol shocks.

    Every pair's spot moves by the same relative shock and every vol by the same
    absolute shock; time and rates are held fixed. P&L is in quote currency,
    converted to USD at today's spots.
    """
    spots = market_spots(positions)
    book = [p for p in positions if pair is None or p.pair == pair]
    if not book:
        raise ValueError(f"no positions for pair {pair}")

    base_values = []
    for p in book:
        v0 = gk_price(p.spot, p.strike, p.maturity, p.domestic_rate, p.foreign_rate, p.volatility, p.option_type)
        base_values.append((p, v0, usd_rate(p.quote, spots)))

    grid = []
    for dv in vol_shocks:
        row = []
        for ds in spot_shocks:
            pnl = 0.0
            for p, v0, fx in base_values:
                v = gk_price(
                    p.spot * (1.0 + ds),
                    p.strike,
                    p.maturity,
                    p.domestic_rate,
                    p.foreign_rate,
                    max(p.volatility + dv, MIN_VOL),
                    p.option_type,
                )
                pnl += (v - v0) * p.notional * fx
            row.append(pnl)
        grid.append(row)
    return ScenarioGrid(list(spot_shocks), list(vol_shocks), grid, sorted({p.pair for p in book}))

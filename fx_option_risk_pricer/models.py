"""Typed records shared across pricing, aggregation and reporting."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class OptionType(str, Enum):
    CALL = "call"
    PUT = "put"


@dataclass(frozen=True)
class OptionPosition:
    """A European FX option on a pair quoted as BASEQUOTE (e.g. EURUSD = USD per 1 EUR).

    Garman-Kohlhagen treats the quote currency as domestic and the base currency
    as foreign, so ``domestic_rate`` is the quote-currency rate and
    ``foreign_rate`` is the base-currency rate (continuously compounded).
    ``notional`` is in base-currency units; negative means short.
    ``maturity`` is in years (ACT/365).
    """

    trade_id: str
    pair: str
    option_type: OptionType
    strike: float
    maturity: float
    notional: float
    spot: float
    domestic_rate: float
    foreign_rate: float
    volatility: float

    @property
    def base(self) -> str:
        return self.pair[:3]

    @property
    def quote(self) -> str:
        return self.pair[3:]


@dataclass(frozen=True)
class Greeks:
    """Per one unit of base-currency notional, values in quote currency."""

    price: float
    delta: float  # spot delta, dV/dS
    gamma: float  # d(delta)/dS
    vega: float  # per 1 vol point (0.01)
    theta: float  # per calendar day


@dataclass(frozen=True)
class PositionRisk:
    """Position-level risk: Greeks scaled by signed notional."""

    trade_id: str
    pair: str
    option_type: str
    strike: float
    maturity: float
    notional: float
    volatility: float
    price: float  # quote ccy per 1 unit of base
    delta_pct: float  # spot delta per unit, as a fraction (0.45 = 45 delta)
    mtm: float  # quote ccy
    delta_base: float  # base ccy
    gamma_1pct_base: float  # change in delta_base for a 1% spot move
    vega: float  # quote ccy per 1 vol point
    theta: float  # quote ccy per calendar day

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class OptionType(StrEnum):
    CALL = "call"
    PUT = "put"


@dataclass(frozen=True)
class OptionPosition:
    symbol: str
    spot: float
    strike: float
    maturity: float
    domestic_rate: float
    foreign_rate: float
    volatility: float
    option_type: OptionType
    notional: float = 1.0


@dataclass(frozen=True)
class RiskResult:
    symbol: str
    option_type: str
    price: float
    delta: float
    gamma: float
    vega: float
    theta: float
    notional_value: float

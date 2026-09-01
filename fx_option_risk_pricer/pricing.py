from __future__ import annotations

import math

from fx_option_risk_pricer.models import OptionPosition, OptionType, RiskResult


def _normal_cdf(value: float) -> float:
    return 0.5 * (1.0 + math.erf(value / math.sqrt(2.0)))


def _normal_pdf(value: float) -> float:
    return math.exp(-0.5 * value * value) / math.sqrt(2.0 * math.pi)


def _validate(position: OptionPosition) -> None:
    if position.spot <= 0:
        raise ValueError("spot must be positive")
    if position.strike <= 0:
        raise ValueError("strike must be positive")
    if position.maturity <= 0:
        raise ValueError("maturity must be positive")
    if position.volatility <= 0:
        raise ValueError("volatility must be positive")
    if position.notional <= 0:
        raise ValueError("notional must be positive")


def price_option(position: OptionPosition) -> RiskResult:
    """Price an FX option with the Garman-Kohlhagen model."""
    _validate(position)

    spot = position.spot
    strike = position.strike
    maturity = position.maturity
    domestic_rate = position.domestic_rate
    foreign_rate = position.foreign_rate
    volatility = position.volatility
    sqrt_t = math.sqrt(maturity)

    d1 = (
        math.log(spot / strike)
        + (domestic_rate - foreign_rate + 0.5 * volatility * volatility) * maturity
    ) / (volatility * sqrt_t)
    d2 = d1 - volatility * sqrt_t

    domestic_discount = math.exp(-domestic_rate * maturity)
    foreign_discount = math.exp(-foreign_rate * maturity)

    if position.option_type == OptionType.CALL:
        price = spot * foreign_discount * _normal_cdf(d1) - strike * domestic_discount * _normal_cdf(d2)
        delta = foreign_discount * _normal_cdf(d1)
        theta = (
            -(spot * foreign_discount * _normal_pdf(d1) * volatility) / (2 * sqrt_t)
            + foreign_rate * spot * foreign_discount * _normal_cdf(d1)
            - domestic_rate * strike * domestic_discount * _normal_cdf(d2)
        )
    else:
        price = strike * domestic_discount * _normal_cdf(-d2) - spot * foreign_discount * _normal_cdf(-d1)
        delta = -foreign_discount * _normal_cdf(-d1)
        theta = (
            -(spot * foreign_discount * _normal_pdf(d1) * volatility) / (2 * sqrt_t)
            - foreign_rate * spot * foreign_discount * _normal_cdf(-d1)
            + domestic_rate * strike * domestic_discount * _normal_cdf(-d2)
        )

    gamma = foreign_discount * _normal_pdf(d1) / (spot * volatility * sqrt_t)
    vega = spot * foreign_discount * _normal_pdf(d1) * sqrt_t

    return RiskResult(
        symbol=position.symbol,
        option_type=position.option_type.value,
        price=price,
        delta=delta,
        gamma=gamma,
        vega=vega,
        theta=theta / 365.0,
        notional_value=price * position.notional,
    )

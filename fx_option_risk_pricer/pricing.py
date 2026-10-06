"""Garman-Kohlhagen pricing, Greeks and an implied volatility solver."""

from __future__ import annotations

import math

from fx_option_risk_pricer.models import Greeks, OptionPosition, OptionType, PositionRisk

DAYS_PER_YEAR = 365.0
_SQRT_2PI = math.sqrt(2.0 * math.pi)


def _norm_cdf(x: float) -> float:
    return 0.5 * math.erfc(-x / math.sqrt(2.0))


def _norm_pdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / _SQRT_2PI


def _check_inputs(spot: float, strike: float, maturity: float, vol: float) -> None:
    if spot <= 0:
        raise ValueError("spot must be positive")
    if strike <= 0:
        raise ValueError("strike must be positive")
    if maturity <= 0:
        raise ValueError("maturity must be positive")
    if vol <= 0:
        raise ValueError("volatility must be positive")


def _d1_d2(spot: float, strike: float, maturity: float, r_dom: float, r_for: float, vol: float) -> tuple[float, float]:
    vol_sqrt_t = vol * math.sqrt(maturity)
    d1 = (math.log(spot / strike) + (r_dom - r_for + 0.5 * vol * vol) * maturity) / vol_sqrt_t
    return d1, d1 - vol_sqrt_t


def gk_price(
    spot: float,
    strike: float,
    maturity: float,
    r_dom: float,
    r_for: float,
    vol: float,
    option_type: OptionType,
) -> float:
    """Garman-Kohlhagen premium in quote currency per 1 unit of base currency."""
    _check_inputs(spot, strike, maturity, vol)
    d1, d2 = _d1_d2(spot, strike, maturity, r_dom, r_for, vol)
    sign = 1.0 if option_type is OptionType.CALL else -1.0
    df_dom = math.exp(-r_dom * maturity)
    df_for = math.exp(-r_for * maturity)
    return sign * (spot * df_for * _norm_cdf(sign * d1) - strike * df_dom * _norm_cdf(sign * d2))


def gk_greeks(
    spot: float,
    strike: float,
    maturity: float,
    r_dom: float,
    r_for: float,
    vol: float,
    option_type: OptionType,
) -> Greeks:
    """Price and analytic Greeks per 1 unit of base notional (see Greeks for units)."""
    _check_inputs(spot, strike, maturity, vol)
    d1, d2 = _d1_d2(spot, strike, maturity, r_dom, r_for, vol)
    sign = 1.0 if option_type is OptionType.CALL else -1.0
    sqrt_t = math.sqrt(maturity)
    df_dom = math.exp(-r_dom * maturity)
    df_for = math.exp(-r_for * maturity)
    pdf_d1 = _norm_pdf(d1)

    price = sign * (spot * df_for * _norm_cdf(sign * d1) - strike * df_dom * _norm_cdf(sign * d2))
    delta = sign * df_for * _norm_cdf(sign * d1)
    gamma = df_for * pdf_d1 / (spot * vol * sqrt_t)
    vega = spot * df_for * pdf_d1 * sqrt_t
    # Theta as value change from the passage of time (dV/dt = -dV/dT).
    theta = -spot * df_for * pdf_d1 * vol / (2.0 * sqrt_t) + sign * (
        r_for * spot * df_for * _norm_cdf(sign * d1) - r_dom * strike * df_dom * _norm_cdf(sign * d2)
    )
    return Greeks(price=price, delta=delta, gamma=gamma, vega=vega / 100.0, theta=theta / DAYS_PER_YEAR)


def price_position(position: OptionPosition) -> PositionRisk:
    """Price one position and scale its Greeks by signed base notional."""
    if position.notional == 0:
        raise ValueError(f"{position.trade_id}: notional must be non-zero")
    g = gk_greeks(
        position.spot,
        position.strike,
        position.maturity,
        position.domestic_rate,
        position.foreign_rate,
        position.volatility,
        position.option_type,
    )
    n = position.notional
    return PositionRisk(
        trade_id=position.trade_id,
        pair=position.pair,
        option_type=position.option_type.value,
        strike=position.strike,
        maturity=position.maturity,
        notional=n,
        volatility=position.volatility,
        price=g.price,
        delta_pct=g.delta,
        mtm=g.price * n,
        delta_base=g.delta * n,
        gamma_1pct_base=g.gamma * position.spot * 0.01 * n,
        vega=g.vega * n,
        theta=g.theta * n,
    )


def implied_vol(
    price: float,
    spot: float,
    strike: float,
    maturity: float,
    r_dom: float,
    r_for: float,
    option_type: OptionType,
    tol: float = 1e-12,
    max_iter: int = 100,
) -> float:
    """Solve for the GK volatility that reproduces ``price``.

    Newton's method on vega, falling back to bisection whenever a Newton step
    leaves the current bracket or vega is too small to trust.
    """
    _check_inputs(spot, strike, maturity, 1.0)
    df_dom = math.exp(-r_dom * maturity)
    df_for = math.exp(-r_for * maturity)
    forward_intrinsic = spot * df_for - strike * df_dom
    if option_type is OptionType.CALL:
        lower, upper = max(forward_intrinsic, 0.0), spot * df_for
    else:
        lower, upper = max(-forward_intrinsic, 0.0), strike * df_dom
    if not lower < price < upper:
        raise ValueError(f"price {price:.6g} is outside the no-arbitrage bounds ({lower:.6g}, {upper:.6g})")

    lo, hi = 1e-6, 5.0
    vol = 0.2
    for _ in range(max_iter):
        diff = gk_price(spot, strike, maturity, r_dom, r_for, vol, option_type) - price
        if abs(diff) <= tol * price:
            return vol
        if diff > 0:
            hi = vol
        else:
            lo = vol
        vega = gk_greeks(spot, strike, maturity, r_dom, r_for, vol, option_type).vega * 100.0
        step = vol - diff / vega if vega > 1e-12 else math.nan
        vol = step if lo < step < hi else 0.5 * (lo + hi)
        if hi - lo < tol:
            return vol
    raise ValueError("implied volatility did not converge")

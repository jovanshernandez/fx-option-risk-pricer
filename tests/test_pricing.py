import math

import pytest

from fx_option_risk_pricer.models import OptionPosition, OptionType
from fx_option_risk_pricer.pricing import gk_greeks, gk_price, implied_vol, price_position

CALL, PUT = OptionType.CALL, OptionType.PUT

# (spot, strike, maturity, r_dom, r_for, vol): ATM, ITM/OTM, long-dated, negative rates, high vol
CASES = [
    (1.1650, 1.1800, 0.25, 0.040, 0.020, 0.075),
    (148.50, 145.00, 0.50, 0.005, 0.040, 0.105),
    (1.3450, 1.2500, 2.00, 0.040, 0.040, 0.090),
    (0.9000, 0.9500, 0.75, -0.007, 0.030, 0.060),
    (20.000, 18.000, 0.10, 0.100, 0.045, 0.250),
]


def test_matches_published_reference_value() -> None:
    # Haug, The Complete Guide to Option Pricing Formulas: GK call = 0.0291
    price = gk_price(1.56, 1.60, 0.5, 0.06, 0.08, 0.12, CALL)
    assert price == pytest.approx(0.0291, abs=5e-5)


@pytest.mark.parametrize("spot,strike,t,rd,rf,vol", CASES)
def test_put_call_parity(spot, strike, t, rd, rf, vol) -> None:
    call = gk_price(spot, strike, t, rd, rf, vol, CALL)
    put = gk_price(spot, strike, t, rd, rf, vol, PUT)
    forward_value = spot * math.exp(-rf * t) - strike * math.exp(-rd * t)
    assert call - put == pytest.approx(forward_value, rel=1e-12, abs=1e-12)


@pytest.mark.parametrize("option_type", [CALL, PUT])
@pytest.mark.parametrize("spot,strike,t,rd,rf,vol", CASES)
def test_greeks_match_finite_differences(spot, strike, t, rd, rf, vol, option_type) -> None:
    g = gk_greeks(spot, strike, t, rd, rf, vol, option_type)

    def v(s=spot, tt=t, sigma=vol):
        return gk_price(s, strike, tt, rd, rf, sigma, option_type)

    hs = spot * 1e-4
    assert g.price == pytest.approx(v(), rel=1e-12)
    assert g.delta == pytest.approx((v(s=spot + hs) - v(s=spot - hs)) / (2 * hs), rel=1e-5, abs=1e-9)
    assert g.gamma == pytest.approx((v(s=spot + hs) - 2 * v() + v(s=spot - hs)) / hs**2, rel=1e-4)
    # vega is per 1 vol point (0.01), so scale dV/dsigma by 1/100
    hv = 1e-4
    assert g.vega == pytest.approx((v(sigma=vol + hv) - v(sigma=vol - hv)) / (2 * hv) / 100, rel=1e-5)
    # theta is per calendar day: value lost as maturity shrinks by one day
    day = 1 / 365
    assert g.theta == pytest.approx((v(tt=t - day / 2) - v(tt=t + day / 2)), rel=1e-4, abs=1e-12)


@pytest.mark.parametrize("spot,strike,t,rd,rf,vol", CASES)
def test_greek_conventions(spot, strike, t, rd, rf, vol) -> None:
    call = gk_greeks(spot, strike, t, rd, rf, vol, CALL)
    put = gk_greeks(spot, strike, t, rd, rf, vol, PUT)
    # spot delta: call - put = foreign discount factor
    assert call.delta - put.delta == pytest.approx(math.exp(-rf * t), rel=1e-12)
    assert 0 < call.delta < 1 and -1 < put.delta < 0
    assert call.gamma == pytest.approx(put.gamma) and call.gamma > 0
    assert call.vega == pytest.approx(put.vega) and call.vega > 0


@pytest.mark.parametrize("option_type", [CALL, PUT])
@pytest.mark.parametrize("spot,strike,t,rd,rf,vol", CASES)
def test_implied_vol_round_trip(spot, strike, t, rd, rf, vol, option_type) -> None:
    price = gk_price(spot, strike, t, rd, rf, vol, option_type)
    assert implied_vol(price, spot, strike, t, rd, rf, option_type) == pytest.approx(vol, abs=1e-8)


def test_implied_vol_far_otm_low_premium() -> None:
    price = gk_price(1.10, 1.25, 0.1, 0.02, 0.01, 0.08, CALL)
    assert 0 < price < 1e-5
    assert implied_vol(price, 1.10, 1.25, 0.1, 0.02, 0.01, CALL) == pytest.approx(0.08, abs=1e-8)


def test_implied_vol_rejects_price_below_intrinsic() -> None:
    with pytest.raises(ValueError, match="no-arbitrage"):
        implied_vol(0.001, 1.30, 1.10, 0.25, 0.04, 0.02, CALL)


def _position(notional: float, option_type: OptionType = CALL) -> OptionPosition:
    return OptionPosition("T1", "EURUSD", option_type, 1.18, 0.25, notional, 1.165, 0.04, 0.02, 0.075)


def test_position_risk_scales_with_signed_notional() -> None:
    long, short = price_position(_position(1_000_000)), price_position(_position(-1_000_000))
    g = gk_greeks(1.165, 1.18, 0.25, 0.04, 0.02, 0.075, CALL)

    assert long.mtm == pytest.approx(g.price * 1_000_000)
    assert long.delta_base == pytest.approx(g.delta * 1_000_000)
    assert long.gamma_1pct_base == pytest.approx(g.gamma * 1.165 * 0.01 * 1_000_000)
    assert long.vega == pytest.approx(g.vega * 1_000_000)
    for field in ("mtm", "delta_base", "gamma_1pct_base", "vega", "theta"):
        assert getattr(short, field) == pytest.approx(-getattr(long, field))


@pytest.mark.parametrize(
    "kwargs,message",
    [
        ({"spot": 0}, "spot must be positive"),
        ({"strike": -1}, "strike must be positive"),
        ({"maturity": 0}, "maturity must be positive"),
        ({"vol": 0}, "volatility must be positive"),
    ],
)
def test_rejects_invalid_inputs(kwargs, message) -> None:
    args = {"spot": 1.1, "strike": 1.1, "maturity": 0.5, "vol": 0.1} | kwargs
    with pytest.raises(ValueError, match=message):
        gk_price(args["spot"], args["strike"], args["maturity"], 0.02, 0.01, args["vol"], CALL)


def test_rejects_zero_notional() -> None:
    with pytest.raises(ValueError, match="notional"):
        price_position(_position(0))

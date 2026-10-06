from pathlib import Path

import pytest

from fx_option_risk_pricer.io import load_positions
from fx_option_risk_pricer.models import OptionPosition, OptionType
from fx_option_risk_pricer.portfolio import aggregate_by_pair, market_spots, scenario_grid, usd_rate
from fx_option_risk_pricer.pricing import price_position

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "positions.csv"


def _pos(pair: str, spot: float, notional: float = 1_000_000, trade_id: str = "T") -> OptionPosition:
    return OptionPosition(trade_id, pair, OptionType.CALL, spot, 0.5, notional, spot, 0.03, 0.02, 0.1)


def test_usd_rate_handles_both_quote_directions() -> None:
    spots = {"EURUSD": 1.20, "USDJPY": 150.0}
    assert usd_rate("USD", spots) == 1.0
    assert usd_rate("EUR", spots) == pytest.approx(1.20)
    assert usd_rate("JPY", spots) == pytest.approx(1 / 150.0)
    with pytest.raises(ValueError, match="CHF"):
        usd_rate("CHF", spots)


def test_market_spots_rejects_conflicting_spots() -> None:
    with pytest.raises(ValueError, match="disagrees"):
        market_spots([_pos("EURUSD", 1.10, trade_id="A"), _pos("EURUSD", 1.11, trade_id="B")])


def test_aggregation_nets_by_pair_and_converts_to_usd() -> None:
    positions = [
        _pos("EURUSD", 1.20, 2_000_000, "A"),
        _pos("EURUSD", 1.20, -500_000, "B"),
        _pos("USDJPY", 150.0, 1_000_000, "C"),
        _pos("GBPUSD", 1.30, 1_000_000, "D"),
        _pos("EURGBP", 0.85, 1_000_000, "E"),
    ]
    risks = [price_position(p) for p in positions]
    by_pair = {p.pair: p for p in aggregate_by_pair(risks, market_spots(positions))}

    eur = by_pair["EURUSD"]
    assert eur.trades == 2
    assert eur.net_notional_base == 1_500_000
    assert eur.net_delta_base == pytest.approx(risks[0].delta_base + risks[1].delta_base)
    assert eur.vega_usd == pytest.approx(risks[0].vega + risks[1].vega)
    # JPY-quoted vega converts at 1/USDJPY; GBP-quoted cross converts via GBPUSD
    assert by_pair["USDJPY"].vega_usd == pytest.approx(risks[2].vega / 150.0)
    assert by_pair["EURGBP"].mtm_usd == pytest.approx(risks[4].mtm * 1.30)


def test_scenario_grid_is_zero_at_origin_and_matches_delta_for_small_moves() -> None:
    positions = load_positions(EXAMPLE)
    spots = market_spots(positions)
    grid = scenario_grid(positions, [-0.0001, 0.0, 0.0001], [0.0])
    assert grid.pnl_usd[0][1] == pytest.approx(0.0, abs=1e-6)

    # first-order P&L = delta (base ccy) * spot * shock, converted from quote ccy to USD
    expected = sum(
        price_position(p).delta_base * p.spot * 0.0001 * usd_rate(p.quote, spots) for p in positions
    )
    central = (grid.pnl_usd[0][2] - grid.pnl_usd[0][0]) / 2
    assert central == pytest.approx(expected, rel=1e-4)


def test_scenario_grid_vol_shock_matches_vega() -> None:
    positions = load_positions(EXAMPLE)
    spots = market_spots(positions)
    risks = [price_position(p) for p in positions]
    total_vega_usd = sum(p.vega_usd for p in aggregate_by_pair(risks, spots))
    grid = scenario_grid(positions, [0.0], [-0.001, 0.001])
    assert (grid.pnl_usd[1][0] - grid.pnl_usd[0][0]) / 0.2 == pytest.approx(total_vega_usd, rel=1e-4)


def test_scenario_grid_can_filter_to_one_pair() -> None:
    positions = load_positions(EXAMPLE)
    grid = scenario_grid(positions, [0.01], [0.0], pair="USDJPY")
    assert grid.pairs == ["USDJPY"]
    with pytest.raises(ValueError, match="no positions"):
        scenario_grid(positions, [0.01], [0.0], pair="USDCHF")

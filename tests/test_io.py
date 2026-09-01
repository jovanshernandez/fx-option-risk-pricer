from pathlib import Path

from fx_option_risk_pricer.io import load_positions


def test_loads_example_positions() -> None:
    positions = load_positions(Path("data/example_positions.csv"))

    assert len(positions) == 3
    assert positions[0].symbol == "EURUSD"
    assert positions[0].notional == 1_000_000

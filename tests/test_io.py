from pathlib import Path

import pytest

from fx_option_risk_pricer.io import load_positions
from fx_option_risk_pricer.models import OptionType

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "positions.csv"
HEADER = "trade_id,pair,type,strike,maturity,notional,spot,r_dom,r_for,vol\n"


def test_loads_example_positions() -> None:
    positions = load_positions(EXAMPLE)

    assert len(positions) == 10
    first = positions[0]
    assert (first.trade_id, first.pair, first.option_type) == ("FXO-001", "EURUSD", OptionType.CALL)
    assert (first.base, first.quote) == ("EUR", "USD")
    assert any(p.notional < 0 for p in positions)


def _write(tmp_path: Path, body: str, header: str = HEADER) -> Path:
    path = tmp_path / "positions.csv"
    path.write_text(header + body, encoding="utf-8")
    return path


@pytest.mark.parametrize(
    "row,message",
    [
        ("A,EURUS,call,1.1,0.5,1e6,1.1,0.02,0.01,0.1\n", "row 2: pair"),
        ("A,EURUSD,straddle,1.1,0.5,1e6,1.1,0.02,0.01,0.1\n", "row 2: type"),
        ("A,EURUSD,call,abc,0.5,1e6,1.1,0.02,0.01,0.1\n", "row 2: strike must be a number"),
        ("A,EURUSD,call,1.1,0,1e6,1.1,0.02,0.01,0.1\n", "row 2: maturity must be positive"),
        ("A,EURUSD,call,1.1,0.5,0,1.1,0.02,0.01,0.1\n", "row 2: notional must be non-zero"),
    ],
)
def test_rejects_bad_rows(tmp_path: Path, row: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        load_positions(_write(tmp_path, row))


def test_reports_missing_columns(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="missing required columns: vol"):
        load_positions(_write(tmp_path, "", header=HEADER.replace(",vol", "")))


def test_trade_id_is_optional(tmp_path: Path) -> None:
    header = "pair,type,strike,maturity,notional,spot,r_dom,r_for,vol\n"
    positions = load_positions(_write(tmp_path, "usdjpy,PUT,145,0.5,-1e6,148.5,0.005,0.04,0.1\n", header))
    assert positions[0].trade_id == "row-2"
    assert positions[0].pair == "USDJPY"
    assert positions[0].option_type is OptionType.PUT

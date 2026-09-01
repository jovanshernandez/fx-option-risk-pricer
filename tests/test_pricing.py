import pytest

from fx_option_risk_pricer.models import OptionPosition, OptionType
from fx_option_risk_pricer.pricing import price_option


def test_prices_call_option() -> None:
    result = price_option(
        OptionPosition(
            symbol="EURUSD",
            spot=1.10,
            strike=1.15,
            maturity=0.25,
            domestic_rate=0.02,
            foreign_rate=0.01,
            volatility=0.12,
            option_type=OptionType.CALL,
            notional=1_000_000,
        )
    )

    assert result.symbol == "EURUSD"
    assert result.option_type == "call"
    assert result.price > 0
    assert 0 < result.delta < 1
    assert result.vega > 0
    assert result.notional_value > 0


def test_rejects_invalid_position() -> None:
    with pytest.raises(ValueError, match="spot must be positive"):
        price_option(
            OptionPosition(
                symbol="EURUSD",
                spot=0,
                strike=1.15,
                maturity=0.25,
                domestic_rate=0.02,
                foreign_rate=0.01,
                volatility=0.12,
                option_type=OptionType.CALL,
            )
        )

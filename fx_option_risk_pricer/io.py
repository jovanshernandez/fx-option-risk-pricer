from __future__ import annotations

from pathlib import Path

import pandas as pd

from fx_option_risk_pricer.models import OptionPosition, OptionType

REQUIRED_COLUMNS = {
    "symbol",
    "spot",
    "strike",
    "maturity",
    "r_dom",
    "r_for",
    "vol",
    "type",
}


def load_positions(path: Path) -> list[OptionPosition]:
    data = pd.read_csv(path)
    missing = REQUIRED_COLUMNS - set(data.columns)
    if missing:
        raise ValueError(f"missing required columns: {', '.join(sorted(missing))}")

    positions: list[OptionPosition] = []
    for row_number, row in enumerate(data.to_dict("records"), start=2):
        try:
            option_type = OptionType(str(row["type"]).lower())
        except ValueError as exc:
            raise ValueError(f"row {row_number}: type must be call or put") from exc

        notional = float(row.get("notional", 1.0))
        positions.append(
            OptionPosition(
                symbol=str(row["symbol"]).upper(),
                spot=float(row["spot"]),
                strike=float(row["strike"]),
                maturity=float(row["maturity"]),
                domestic_rate=float(row["r_dom"]),
                foreign_rate=float(row["r_for"]),
                volatility=float(row["vol"]),
                option_type=option_type,
                notional=notional,
            )
        )
    return positions

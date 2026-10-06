"""CSV loading with row-level validation, and CSV report writing."""

from __future__ import annotations

import csv
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Iterable

from fx_option_risk_pricer.models import OptionPosition, OptionType

REQUIRED_COLUMNS = ("pair", "type", "strike", "maturity", "notional", "spot", "r_dom", "r_for", "vol")


def _parse_float(row: dict[str, str], column: str, row_number: int) -> float:
    raw = (row.get(column) or "").strip()
    try:
        return float(raw)
    except ValueError:
        raise ValueError(f"row {row_number}: {column} must be a number, got {raw!r}") from None


def _parse_row(row: dict[str, str], row_number: int) -> OptionPosition:
    pair = (row.get("pair") or "").strip().upper()
    if len(pair) != 6 or not pair.isalpha():
        raise ValueError(f"row {row_number}: pair must be six letters like EURUSD, got {pair!r}")
    try:
        option_type = OptionType((row.get("type") or "").strip().lower())
    except ValueError:
        raise ValueError(f"row {row_number}: type must be call or put") from None

    values = {col: _parse_float(row, col, row_number) for col in REQUIRED_COLUMNS[2:]}
    for col in ("strike", "maturity", "spot", "vol"):
        if values[col] <= 0:
            raise ValueError(f"row {row_number}: {col} must be positive")
    if values["notional"] == 0:
        raise ValueError(f"row {row_number}: notional must be non-zero (negative = short)")

    return OptionPosition(
        trade_id=(row.get("trade_id") or "").strip() or f"row-{row_number}",
        pair=pair,
        option_type=option_type,
        strike=values["strike"],
        maturity=values["maturity"],
        notional=values["notional"],
        spot=values["spot"],
        domestic_rate=values["r_dom"],
        foreign_rate=values["r_for"],
        volatility=values["vol"],
    )


def load_positions(path: Path) -> list[OptionPosition]:
    with Path(path).open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        missing = [col for col in REQUIRED_COLUMNS if col not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"missing required columns: {', '.join(missing)}")
        positions = [_parse_row(row, n) for n, row in enumerate(reader, start=2)]
    if not positions:
        raise ValueError(f"{path}: no positions found")
    return positions


def write_csv(path: Path, rows: Iterable[object]) -> Path:
    """Write dataclass instances or dicts to CSV, one row each."""
    records = [asdict(r) if is_dataclass(r) else dict(r) for r in rows]  # type: ignore[arg-type]
    if not records:
        raise ValueError("nothing to write")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0].keys()))
        writer.writeheader()
        writer.writerows(records)
    return path


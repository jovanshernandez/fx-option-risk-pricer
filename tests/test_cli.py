import csv
from pathlib import Path

from fx_option_risk_pricer.cli import main

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "positions.csv"


def test_report_writes_csvs_and_heatmap(tmp_path: Path, capsys) -> None:
    code = main(["report", str(EXAMPLE), "--output-dir", str(tmp_path), "--spot-shocks=-2,0,2", "--vol-shocks=-1,0,1"])

    assert code == 0
    out = capsys.readouterr().out
    assert "Risk by currency pair" in out and "Scenario P&L" in out
    for name in ("positions_risk.csv", "pair_risk.csv", "scenario_grid.csv"):
        assert (tmp_path / name).stat().st_size > 0
    assert (tmp_path / "scenario_heatmap.png").read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"

    with (tmp_path / "scenario_grid.csv").open() as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 3 and len(rows[0]) == 4
    assert float(rows[1]["spot_+0.0000"]) == 0.0


def test_implied_vol_command(capsys) -> None:
    code = main(["implied-vol", "--price", "0.0291", "--spot", "1.56", "--strike", "1.60", "--maturity", "0.5",
                 "--r-dom", "0.06", "--r-for", "0.08", "--type", "call"])
    assert code == 0
    assert "implied vol: 12.0" in capsys.readouterr().out


def test_bad_input_returns_error(tmp_path: Path, capsys) -> None:
    bad = tmp_path / "bad.csv"
    bad.write_text("pair,type\nEURUSD,call\n", encoding="utf-8")
    assert main(["report", str(bad), "--output-dir", str(tmp_path)]) == 1
    assert "missing required columns" in capsys.readouterr().out

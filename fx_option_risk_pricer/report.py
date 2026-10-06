"""Terminal tables (rich) and the scenario heatmap (matplotlib)."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from rich.console import Console
from rich.table import Table

from fx_option_risk_pricer.models import PositionRisk
from fx_option_risk_pricer.portfolio import PairRisk, ScenarioGrid

LOSS, NEUTRAL, GAIN = "#e34948", "#f0efec", "#2a78d6"
SURFACE, INK, MUTED = "#fcfcfb", "#1a1a19", "#6b6a66"


def _amount(value: float) -> str:
    return "0" if abs(value) < 0.5 else f"{value:+,.0f}"


def _signed(value: float) -> str:
    style = "red" if value < -0.5 else "green" if value > 0.5 else ""
    return f"[{style}]{_amount(value)}[/]" if style else _amount(value)


def positions_table(risks: Sequence[PositionRisk]) -> Table:
    table = Table(title="Positions", title_justify="left", title_style="bold", header_style="bold cyan")
    for name in ("Trade", "Pair", "Type"):
        table.add_column(name)
    for name in ("Strike", "T (y)", "Notional", "Vol", "Delta", "MTM", "Delta base", "Gamma 1%", "Vega/pt", "Theta/day"):
        table.add_column(name, justify="right")
    for r in risks:
        table.add_row(
            r.trade_id,
            r.pair,
            r.option_type,
            f"{r.strike:.4f}" if r.strike < 20 else f"{r.strike:.2f}",
            f"{r.maturity:.2f}",
            f"{r.notional / 1e6:+.1f}M",
            f"{r.volatility * 100:.1f}%",
            f"{r.delta_pct * 100:+.1f}",
            _amount(r.mtm),
            _amount(r.delta_base),
            _amount(r.gamma_1pct_base),
            _amount(r.vega),
            _amount(r.theta),
        )
    table.caption = "Delta in % of notional. MTM, vega, theta in quote ccy; delta and gamma in base ccy."
    table.caption_justify = "left"
    return table


def pair_table(pairs: Sequence[PairRisk]) -> Table:
    table = Table(title="Risk by currency pair", title_justify="left", title_style="bold", header_style="bold cyan")
    table.add_column("Pair")
    for name in ("Trades", "Net notional", "Net delta", "Gamma 1%", "Vega USD/pt", "Theta USD/day", "MTM USD"):
        table.add_column(name, justify="right")
    for p in pairs:
        base = p.pair[:3]
        table.add_row(
            p.pair,
            str(p.trades),
            f"{_amount(p.net_notional_base)} {base}",
            f"{_signed(p.net_delta_base)} {base}",
            f"{_amount(p.gamma_1pct_base)} {base}",
            _amount(p.vega_usd),
            _amount(p.theta_usd),
            _amount(p.mtm_usd),
        )
    table.add_section()
    table.add_row(
        "[bold]Total[/]",
        str(sum(p.trades for p in pairs)),
        "",
        "",
        "",
        f"[bold]{_amount(sum(p.vega_usd for p in pairs))}[/]",
        f"[bold]{_amount(sum(p.theta_usd for p in pairs))}[/]",
        f"[bold]{_amount(sum(p.mtm_usd for p in pairs))}[/]",
    )
    return table


def _pct(x: float) -> str:
    return "0%" if abs(x) < 1e-12 else f"{x * 100:+g}%"


def _vol_pts(x: float) -> str:
    return "0 vol" if abs(x) < 1e-12 else f"{x * 100:+g} vol"


def scenario_table(grid: ScenarioGrid) -> Table:
    scope = "whole book" if len(grid.pairs) > 1 else grid.pairs[0]
    table = Table(
        title=f"Scenario P&L in USD ({scope}): spot shock across, vol shock down",
        title_justify="left",
        title_style="bold",
        header_style="bold cyan",
    )
    table.add_column("")
    for ds in grid.spot_shocks:
        table.add_column(_pct(ds), justify="right")
    for dv, row in zip(grid.vol_shocks, grid.pnl_usd):
        table.add_row(f"[bold]{_vol_pts(dv)}[/]", *(_signed(v) for v in row))
    return table


def render(console: Console, risks: Sequence[PositionRisk], pairs: Sequence[PairRisk], grid: ScenarioGrid) -> None:
    console.print(positions_table(risks))
    console.print()
    console.print(pair_table(pairs))
    console.print()
    console.print(scenario_table(grid))


def save_heatmap(grid: ScenarioGrid, path: Path) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
    from matplotlib.ticker import FuncFormatter

    values = grid.pnl_usd
    flat = [v for row in values for v in row]
    limit = max(abs(min(flat)), abs(max(flat)), 1.0)
    cmap = LinearSegmentedColormap.from_list("pnl", [LOSS, NEUTRAL, GAIN])
    norm = TwoSlopeNorm(vmin=-limit, vcenter=0.0, vmax=limit)

    n_rows, n_cols = len(grid.vol_shocks), len(grid.spot_shocks)
    fig, ax = plt.subplots(figsize=(1.0 * n_cols + 2.2, 0.62 * n_rows + 1.9), dpi=150)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)
    mesh = ax.pcolormesh(values, cmap=cmap, norm=norm, edgecolors=SURFACE, linewidth=2)

    for i, row in enumerate(values):
        for j, v in enumerate(row):
            strong = abs(v) > 0.55 * limit
            label = "0" if abs(v) < 500 else f"{v / 1e3:+,.0f}k"
            weight = "bold" if grid.spot_shocks[j] == 0 and grid.vol_shocks[i] == 0 else "normal"
            ax.text(j + 0.5, i + 0.5, label, ha="center", va="center", fontsize=8.5,
                    color="white" if strong else INK, fontweight=weight)

    ax.set_xticks([j + 0.5 for j in range(n_cols)], [_pct(s) for s in grid.spot_shocks])
    ax.set_yticks([i + 0.5 for i in range(n_rows)], [_vol_pts(v) for v in grid.vol_shocks])
    ax.tick_params(length=0, colors=MUTED, labelsize=9)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_xlabel("Spot shock (base ccy vs quote ccy, every pair)", color=MUTED, fontsize=9)
    ax.set_ylabel("Implied vol shock", color=MUTED, fontsize=9)
    scope = "whole book" if len(grid.pairs) > 1 else grid.pairs[0]
    ax.set_title(f"Scenario P&L, USD ({scope})", loc="left", color=INK, fontsize=12, pad=10)

    cbar = fig.colorbar(mesh, ax=ax, fraction=0.035, pad=0.02)
    cbar.outline.set_visible(False)
    cbar.ax.tick_params(colors=MUTED, labelsize=8, length=0)
    cbar.ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x / 1e3:+,.0f}k"))

    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, facecolor=SURFACE)
    plt.close(fig)
    return path

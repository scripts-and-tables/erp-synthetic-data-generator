"""Render animated GIFs that showcase the dataset unfolding over time.

Usage:
    python scripts/generate_animations.py [out_dir] [sample_dir]

Produces (in docs/branding/):
- data_unfolds.gif — monthly revenue + customer count, drawn year-by-year
                     with holiday spikes highlighted as they arrive
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.animation import FuncAnimation, PillowWriter

BRAND = {
    "bg":          "#0b1220",
    "bg_panel":    "#1e293b",
    "text":        "#e2e8f0",
    "text_dim":    "#94a3b8",
    "primary":     "#38bdf8",
    "accent":      "#f97316",
    "accent_2":    "#fbbf24",
    "good":        "#22c55e",
    "border":      "#334155",
}


def chart_data_unfolds(sample_dir: Path, out: Path) -> None:
    headers = pd.read_csv(sample_dir / "invoice_headers.csv",
                          parse_dates=["order_date"])
    customers = pd.read_csv(sample_dir / "customers.csv",
                            parse_dates=["created_at"])

    pos = headers[headers.is_return == 0].copy()
    pos["ym"] = pos["order_date"].dt.to_period("M").dt.to_timestamp()
    monthly_rev = pos.groupby("ym")["grand_total"].sum().reset_index()

    customers_sorted = customers.sort_values("created_at")
    customers_sorted["cum"] = np.arange(1, len(customers_sorted) + 1)

    # Resample customers to monthly granularity
    monthly_cust = (
        customers_sorted.set_index("created_at")["cum"]
        .resample("MS").last().ffill().fillna(0)
        .reset_index()
        .rename(columns={"created_at": "ym"})
    )
    df = monthly_rev.merge(monthly_cust, on="ym", how="left")
    df["cum"] = df["cum"].ffill().fillna(0)

    n_months = len(df)
    n_frames = min(n_months, 90)
    indices = np.linspace(0, n_months - 1, n_frames, dtype=int)

    plt.rcParams.update({
        "figure.facecolor": BRAND["bg"],
        "axes.facecolor": BRAND["bg"],
        "savefig.facecolor": BRAND["bg"],
        "text.color": BRAND["text"],
        "axes.labelcolor": BRAND["text_dim"],
        "axes.edgecolor": BRAND["border"],
        "axes.grid": True,
        "grid.alpha": 0.18,
        "grid.linestyle": "--",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "xtick.color": BRAND["text_dim"],
        "ytick.color": BRAND["text_dim"],
    })

    fig = plt.figure(figsize=(11, 4.5), dpi=90)

    # Title strip
    fig.text(0.05, 0.92, "ERP Synthetic Data Generator",
             fontsize=14, fontweight="bold", color=BRAND["text"])
    fig.text(0.05, 0.86, "Monthly revenue unfolding across 11 years (seed 42, 1,000 customers)",
             fontsize=10, color=BRAND["text_dim"])

    # KPI strip
    kpi_year = fig.text(0.78, 0.92, "", fontsize=14, fontweight="bold",
                        color=BRAND["accent_2"], ha="right")
    kpi_rev = fig.text(0.78, 0.86, "", fontsize=10, color=BRAND["text_dim"], ha="right")
    kpi_cust = fig.text(0.96, 0.86, "", fontsize=10, color=BRAND["primary"], ha="right")

    ax = fig.add_axes([0.07, 0.13, 0.88, 0.62])
    line_rev, = ax.plot([], [], color=BRAND["accent"], linewidth=1.8)
    fill_rev = [ax.fill_between(df["ym"][:0], 0, 0, color=BRAND["accent"], alpha=0.15)]
    holiday_dots = ax.scatter([], [], color=BRAND["accent_2"], s=24, zorder=5, alpha=0.9)

    ax.set_xlim(df["ym"].iloc[0], df["ym"].iloc[-1])
    ax.set_ylim(0, df["grand_total"].max() / 1000 * 1.10)
    ax.set_ylabel("Monthly revenue ($ thousands)", color=BRAND["text_dim"])
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    def init():
        line_rev.set_data([], [])
        holiday_dots.set_offsets(np.empty((0, 2)))
        kpi_year.set_text("")
        kpi_rev.set_text("")
        kpi_cust.set_text("")
        return line_rev, holiday_dots, kpi_year, kpi_rev, kpi_cust

    def update(frame_idx):
        i = indices[frame_idx]
        sub = df.iloc[: i + 1]
        line_rev.set_data(sub["ym"], sub["grand_total"] / 1000)

        # Replace fill_between (matplotlib doesn't update PolyCollection directly)
        for coll in fill_rev:
            coll.remove()
        fill_rev[0] = ax.fill_between(sub["ym"], 0, sub["grand_total"] / 1000,
                                      color=BRAND["accent"], alpha=0.15)

        # Highlight Nov/Dec spikes
        spikes = sub[(sub["ym"].dt.month.isin([11, 12]))]
        if not spikes.empty:
            holiday_dots.set_offsets(
                np.column_stack([
                    mdates.date2num(spikes["ym"]),
                    spikes["grand_total"].values / 1000,
                ])
            )

        cur = sub.iloc[-1]
        kpi_year.set_text(cur["ym"].strftime("%b %Y"))
        kpi_rev.set_text(f"revenue: ${cur['grand_total']/1000:,.0f}k")
        kpi_cust.set_text(f"customers: {int(cur['cum']):,}")
        return line_rev, fill_rev[0], holiday_dots, kpi_year, kpi_rev, kpi_cust

    anim = FuncAnimation(
        fig, update, init_func=init,
        frames=n_frames, interval=70, blit=False,
    )
    writer = PillowWriter(fps=14)
    out.parent.mkdir(parents=True, exist_ok=True)
    anim.save(out, writer=writer)
    plt.close(fig)


def main(out_dir: str = "docs/branding",
         sample_dir: str = "output_csv/sample") -> int:
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    sample = Path(sample_dir)

    print(f"writing animations to {out_path}/")
    chart_data_unfolds(sample, out_path / "data_unfolds.gif")
    size_kb = (out_path / "data_unfolds.gif").stat().st_size // 1024
    print(f"  ✓ data_unfolds.gif  ({size_kb} KB)")
    print("done")
    return 0


if __name__ == "__main__":
    out_dir = sys.argv[1] if len(sys.argv) > 1 else "docs/branding"
    sample_dir = sys.argv[2] if len(sys.argv) > 2 else "output_csv/sample"
    sys.exit(main(out_dir, sample_dir))

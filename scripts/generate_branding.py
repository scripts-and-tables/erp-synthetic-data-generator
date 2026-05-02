"""Generate branded README assets: hero banner, schema diagram, stats strip.

Usage:
    python scripts/generate_branding.py [out_dir]

Produces (under docs/branding/ by default):
- hero.png         — wide title banner with tagline + mini-sparklines
- schema.png       — entity-relationship diagram of the 6 CSVs
- stats_strip.png  — horizontal "stats cards" with the headline numbers
- features.png     — 3x3 feature highlights grid
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.patches as patches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

# Brand palette — deep navy + warm accent, similar to PyTorch/Polars/FastAPI vibe
BRAND = {
    "bg_top":     "#0b1220",
    "bg_bot":     "#1f2a4a",
    "accent":     "#f97316",   # warm orange
    "accent_2":   "#fbbf24",   # gold
    "primary":    "#38bdf8",   # cyan
    "primary_2":  "#818cf8",   # indigo
    "good":       "#22c55e",
    "bad":        "#ef4444",
    "muted":      "#94a3b8",
    "text":       "#e2e8f0",
    "text_dim":   "#94a3b8",
    "card_bg":    "#1e293b",
    "card_border":"#334155",
}

plt.rcParams.update({
    "savefig.dpi": 140,
    "savefig.bbox": "tight",
    "savefig.facecolor": BRAND["bg_top"],
    "figure.facecolor": BRAND["bg_top"],
    "axes.facecolor": BRAND["bg_top"],
    "font.family": ["DejaVu Sans"],
    "text.color": BRAND["text"],
    "axes.labelcolor": BRAND["text_dim"],
    "axes.edgecolor": BRAND["card_border"],
    "axes.spines.top": False,
    "axes.spines.right": False,
    "xtick.color": BRAND["text_dim"],
    "ytick.color": BRAND["text_dim"],
})


def _gradient_bg(ax, top_color: str, bot_color: str) -> None:
    """Fake a vertical gradient by drawing a thin pcolormesh as background."""
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    grad = np.linspace(0, 1, 256).reshape(-1, 1)
    cmap = plt.matplotlib.colors.LinearSegmentedColormap.from_list(
        "bg", [bot_color, top_color]
    )
    ax.imshow(grad, extent=(0, 1, 0, 1), aspect="auto",
              cmap=cmap, zorder=-1, interpolation="bilinear")
    ax.axis("off")


def chart_hero(out: Path, sample_dir: Path) -> None:
    """Wide banner with project title + tagline + 3 mini-sparklines."""
    fig = plt.figure(figsize=(14, 4.2))
    fig.patch.set_facecolor(BRAND["bg_top"])

    # Background gradient
    bg = fig.add_axes([0, 0, 1, 1])
    _gradient_bg(bg, BRAND["bg_top"], BRAND["bg_bot"])

    # Title block (left ~55%)
    ax_t = fig.add_axes([0.04, 0.20, 0.55, 0.7])
    ax_t.axis("off")
    ax_t.text(0, 0.78, "ERP Synthetic Data Generator",
              fontsize=30, fontweight="bold", color=BRAND["text"],
              transform=ax_t.transAxes, family="DejaVu Sans")
    ax_t.text(0, 0.50,
              "Realistic, multi-year retail data — from one Python command",
              fontsize=15, color=BRAND["primary"], transform=ax_t.transAxes)
    ax_t.text(0, 0.30,
              "AdventureWorks-style schema · 6 tables · cohorts · seasonality\n"
              "promotions · returns · multi-market · 100% reproducible",
              fontsize=11.5, color=BRAND["text_dim"], transform=ax_t.transAxes,
              linespacing=1.5)

    # Mini "chip" tags
    chips = [("python 3.10+", BRAND["primary"]),
             ("pandas · numpy", BRAND["primary_2"]),
             ("seed = 42 → byte-identical", BRAND["accent"])]
    x = 0.0
    for txt, color in chips:
        ax_t.text(x, 0.06, txt, fontsize=10, color=color,
                  transform=ax_t.transAxes,
                  bbox=dict(boxstyle="round,pad=0.4", facecolor="#0b1220",
                            edgecolor=color, linewidth=1.0))
        # Approximate width offset
        x += 0.013 * len(txt) + 0.04

    # Mini-sparklines on the right (load from sample if available)
    headers = pd.read_csv(sample_dir / "invoice_headers.csv",
                          parse_dates=["order_date"])
    pos = headers[headers.is_return == 0].copy()
    pos["ym"] = pos["order_date"].dt.to_period("M").dt.to_timestamp()
    monthly = pos.groupby("ym")["grand_total"].sum().reset_index()

    # Customers: cumulative
    customers = pd.read_csv(sample_dir / "customers.csv",
                            parse_dates=["created_at"])
    customers = customers.sort_values("created_at").reset_index(drop=True)
    cum = np.arange(1, len(customers) + 1)

    # Daily holiday strip for 2024 (zoomed)
    daily = pos[pos["order_date"].dt.year == 2024]
    daily_d = daily.groupby(daily["order_date"].dt.date)["grand_total"].sum()

    sparks = [
        ("Monthly revenue (11y)", monthly["ym"].values, monthly["grand_total"].values, BRAND["accent"]),
        ("Customer growth", customers["created_at"].values, cum, BRAND["primary"]),
        ("Daily revenue 2024", daily_d.index.values, daily_d.values, BRAND["accent_2"]),
    ]

    for i, (title, xs, ys, color) in enumerate(sparks):
        ax = fig.add_axes([0.62, 0.62 - i * 0.27, 0.34, 0.20])
        ax.set_facecolor("#101a30")
        ax.plot(xs, ys, color=color, linewidth=1.4)
        ax.fill_between(xs, ys, alpha=0.20, color=color)
        ax.set_title(title, fontsize=10, color=BRAND["text"], loc="left",
                     pad=4, fontweight="bold")
        ax.tick_params(axis="x", labelsize=7)
        ax.tick_params(axis="y", labelsize=7)
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_edgecolor(BRAND["card_border"])
            spine.set_linewidth(0.5)
        ax.spines["top"].set_visible(True)
        ax.spines["right"].set_visible(True)

    fig.savefig(out / "hero.png", facecolor=BRAND["bg_top"])
    plt.close(fig)


def chart_stats_strip(out: Path, sample_dir: Path) -> None:
    """Horizontal strip of 6 'stat cards' with the dataset's headline numbers."""
    headers = pd.read_csv(sample_dir / "invoice_headers.csv")
    lines = pd.read_csv(sample_dir / "sales_lines.csv")
    customers = pd.read_csv(sample_dir / "customers.csv")
    items = pd.read_csv(sample_dir / "items.csv")

    pos = headers[headers.is_return == 0]
    neg = headers[headers.is_return == 1]
    rev = pos.grand_total.sum()
    margin = (pos.merge(lines, on="invoice_id")["gross_margin"].sum() /
              pos.merge(lines, on="invoice_id")["line_total"].sum() * 100)

    stats = [
        (f"{len(customers):,}", "customers", BRAND["primary"]),
        (f"{len(pos):,}", "invoices", BRAND["primary_2"]),
        (f"{len(lines):,}", "sales lines", BRAND["accent"]),
        (f"${rev/1e6:.1f}M", "gross revenue", BRAND["accent_2"]),
        (f"{margin:.0f}%", "gross margin", BRAND["good"]),
        (f"{len(neg)/len(pos)*100:.1f}%", "returns share", BRAND["bad"]),
    ]

    fig, ax = plt.subplots(figsize=(14, 2.0))
    fig.patch.set_facecolor(BRAND["bg_top"])
    ax.set_facecolor(BRAND["bg_top"])
    ax.set_xlim(0, 6)
    ax.set_ylim(0, 1)
    ax.axis("off")

    for i, (val, label, color) in enumerate(stats):
        # Card background
        card = FancyBboxPatch((i + 0.07, 0.10), 0.86, 0.80,
                              boxstyle="round,pad=0.02,rounding_size=0.04",
                              facecolor=BRAND["card_bg"],
                              edgecolor=BRAND["card_border"], linewidth=1)
        ax.add_patch(card)
        # Accent stripe
        stripe = FancyBboxPatch((i + 0.07, 0.10), 0.04, 0.80,
                                boxstyle="round,pad=0,rounding_size=0.02",
                                facecolor=color, edgecolor="none")
        ax.add_patch(stripe)
        # Big value
        ax.text(i + 0.5, 0.62, val, fontsize=22, fontweight="bold",
                color=BRAND["text"], ha="center", va="center")
        # Label
        ax.text(i + 0.5, 0.30, label, fontsize=11,
                color=BRAND["text_dim"], ha="center", va="center")

    fig.savefig(out / "stats_strip.png", facecolor=BRAND["bg_top"])
    plt.close(fig)


def chart_schema(out: Path) -> None:
    """Entity-relationship diagram of the 6 CSVs.

    Layout:
      ┌──────────┐  ┌──────────────┐  ┌──────────┐
      │  items   │  │  promotions  │  │ stores   │  (DIM)
      └────┬─────┘  └──────┬───────┘  └────┬─────┘
           │               │               │
           │       ┌───────▼────────┐      │
           │       │ invoice_headers│◄─────┘     (FACT)
           │       └───────┬────────┘
           │               │
           │       ┌───────▼────────┐  ┌──────────┐
           └──────►│  sales_lines   │  │customers │  (FACT/DIM)
                   └────────────────┘  └──────────┘
    """
    fig, ax = plt.subplots(figsize=(15, 9))
    fig.patch.set_facecolor(BRAND["bg_top"])
    ax.set_facecolor(BRAND["bg_top"])
    ax.set_xlim(0, 15)
    ax.set_ylim(0, 9)
    ax.axis("off")

    BOX_W = 3.4

    def box(x, y, h, title, fields, color, badge):
        rect = FancyBboxPatch((x, y), BOX_W, h,
                              boxstyle="round,pad=0.05,rounding_size=0.10",
                              facecolor=BRAND["card_bg"],
                              edgecolor=color, linewidth=2.2, zorder=2)
        ax.add_patch(rect)
        header = FancyBboxPatch((x, y + h - 0.55), BOX_W, 0.55,
                                boxstyle="round,pad=0,rounding_size=0.10",
                                facecolor=color, edgecolor="none",
                                alpha=0.92, zorder=3)
        ax.add_patch(header)
        ax.text(x + 0.20, y + h - 0.27, title, fontsize=13, fontweight="bold",
                color="#0b1220", ha="left", va="center", zorder=4)
        ax.text(x + BOX_W - 0.20, y + h - 0.27, badge, fontsize=8.5,
                fontweight="bold", color="#0b1220", ha="right", va="center",
                zorder=4,
                bbox=dict(boxstyle="round,pad=0.25", facecolor="white",
                          edgecolor="none", alpha=0.55))
        for j, (fname, ftype) in enumerate(fields):
            yj = y + h - 0.95 - j * 0.32
            ax.text(x + 0.20, yj, fname,
                    fontsize=10, color=BRAND["text"], family="monospace",
                    ha="left", va="center", zorder=4)
            ax.text(x + BOX_W - 0.20, yj, ftype,
                    fontsize=9, color=BRAND["text_dim"], family="monospace",
                    ha="right", va="center", zorder=4)

    # Coordinates: 3 columns x 3 rows
    # x columns: 0.5 / 5.8 / 11.1
    COL_L = 0.5
    COL_M = 5.8
    COL_R = 11.1

    # Top row: 3 DIM tables
    box(COL_L, 6.6, 2.0, "items", [
        ("product_id", "PK"),
        ("subcategory", "str"),
        ("list_price", "money"),
        ("standard_cost", "money"),
    ], BRAND["primary"], "DIM")

    box(COL_M, 6.6, 2.0, "promotions", [
        ("promotion_id", "PK"),
        ("discount_pct", "float"),
        ("category_scope", "str"),
        ("start_date / end_date", "date"),
    ], BRAND["accent_2"], "DIM")

    box(COL_R, 6.6, 2.0, "stores", [
        ("store_id", "PK"),
        ("country / region", "str"),
        ("city", "str"),
        ("store_type", "enum"),
    ], BRAND["primary_2"], "DIM")

    # Middle row: invoice_headers (the central fact)
    box(COL_M, 3.5, 2.4, "invoice_headers", [
        ("invoice_id", "PK"),
        ("customer_id", "FK"),
        ("store_id", "FK"),
        ("promotion_id", "FK"),
        ("grand_total / tax / freight", "money"),
        ("is_return / reference_invoice_id", "0/1"),
    ], BRAND["accent"], "FACT")

    # Bottom row
    box(COL_M, 0.4, 2.2, "sales_lines", [
        ("line_id", "PK"),
        ("invoice_id", "FK"),
        ("product_id", "FK"),
        ("quantity / unit_price", "n / money"),
        ("line_total / gross_margin", "money"),
    ], BRAND["bad"], "FACT")

    box(COL_R, 0.4, 2.2, "customers", [
        ("customer_id", "PK"),
        ("cohort", "str"),
        ("price_sensitivity", "float"),
        ("yearly_income / country", "int / str"),
        ("demographics + geo", "..."),
    ], BRAND["good"], "DIM")

    # Arrows: anchor on box edges, label offset clearly
    def arrow(x1, y1, x2, y2, label=None, label_x_off=0.0, label_y_off=0.20,
              rad=0.05):
        a = FancyArrowPatch((x1, y1), (x2, y2),
                            arrowstyle="->,head_length=10,head_width=7",
                            color=BRAND["text_dim"], linewidth=1.3,
                            connectionstyle=f"arc3,rad={rad}",
                            zorder=1)
        ax.add_patch(a)
        if label:
            mx = (x1 + x2) / 2 + label_x_off
            my = (y1 + y2) / 2 + label_y_off
            ax.text(mx, my, label, fontsize=9.5,
                    color=BRAND["text"], ha="center", va="center",
                    family="monospace", zorder=5,
                    bbox=dict(boxstyle="round,pad=0.30",
                              facecolor=BRAND["bg_top"],
                              edgecolor=BRAND["card_border"],
                              linewidth=0.8))

    # Edge anchor helpers
    def bottom(col_x, y_top): return (col_x + BOX_W / 2, y_top)
    def top(col_x, y_bot):    return (col_x + BOX_W / 2, y_bot)
    def left(col_x, y_mid):   return (col_x, y_mid)
    def right(col_x, y_mid):  return (col_x + BOX_W, y_mid)

    # 1. promotions  →  invoice_headers (vertical)
    x1, y1 = bottom(COL_M, 6.6)
    x2, y2 = top(COL_M, 5.9)
    arrow(x1, y1, x2, y2, "promotion_id", label_x_off=1.4)

    # 2. items  →  sales_lines (long diagonal across)
    x1, y1 = bottom(COL_L, 6.6)
    x2, y2 = left(COL_M, 1.5)
    arrow(x1, y1, x2, y2, "product_id", label_x_off=-0.05, label_y_off=0.15, rad=-0.18)

    # 3. stores  →  invoice_headers
    x1, y1 = bottom(COL_R, 6.6)
    x2, y2 = right(COL_M, 4.7)
    arrow(x1, y1, x2, y2, "store_id", label_x_off=0.9, label_y_off=0.0, rad=-0.20)

    # 4. customers  →  invoice_headers
    x1, y1 = top(COL_R, 0.4 + 2.2)
    x2, y2 = right(COL_M, 4.0)
    arrow(x1, y1, x2, y2, "customer_id", label_x_off=0.9, label_y_off=0.0, rad=0.20)

    # 5. invoice_headers  →  sales_lines (vertical)
    x1, y1 = bottom(COL_M, 3.5)
    x2, y2 = top(COL_M, 0.4 + 2.2)
    arrow(x1, y1, x2, y2, "invoice_id", label_x_off=1.4)

    # Title
    ax.text(7.5, 8.85, "Schema — 4 dimensions + 2 facts, fully relational",
            fontsize=15, fontweight="bold", color=BRAND["text"],
            ha="center", va="bottom")

    # Legend
    legend_items = [(BRAND["primary"], "DIM"), (BRAND["accent"], "FACT")]
    lx = 13.4
    for i, (color, label) in enumerate(legend_items):
        circle = patches.Circle((lx, 8.55 - i * 0.35), 0.10,
                                facecolor=color, edgecolor="none")
        ax.add_patch(circle)
        ax.text(lx + 0.20, 8.55 - i * 0.35, label, fontsize=10,
                color=BRAND["text_dim"], va="center")

    fig.savefig(out / "schema.png", facecolor=BRAND["bg_top"])
    plt.close(fig)


def chart_features(out: Path) -> None:
    """3x3 grid of feature highlight cards."""
    # Use Unicode geometric shapes that DejaVu Sans supports (no emoji)
    features = [
        ("$", "Realistic pricing\n& margins",
         "list_price · standard_cost · multi-year inflation",
         BRAND["accent"]),
        ("★", "Holiday seasonality",
         "Black Friday · Christmas · Ramadan · Eid",
         BRAND["accent_2"]),
        ("◉", "Sticky cohorts",
         "6 segments — deterministic per (seed, customer_id)",
         BRAND["good"]),
        ("%", "Promotions & returns",
         "discount-aware lines · ~3% linked returns",
         BRAND["primary"]),
        ("◆", "Multi-market",
         "us · gcc · eu — locale, currency, VAT, holidays",
         BRAND["primary_2"]),
        ("⟲", "Reproducibility",
         "single --seed → byte-identical output",
         BRAND["bad"]),
    ]

    fig, axes = plt.subplots(2, 3, figsize=(14, 5))
    fig.patch.set_facecolor(BRAND["bg_top"])

    for ax, (icon, title, desc, color) in zip(axes.flat, features):
        ax.set_facecolor(BRAND["bg_top"])
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis("off")

        card = FancyBboxPatch((0.04, 0.08), 0.92, 0.84,
                              boxstyle="round,pad=0.02,rounding_size=0.04",
                              facecolor=BRAND["card_bg"],
                              edgecolor=BRAND["card_border"], linewidth=1)
        ax.add_patch(card)
        stripe = FancyBboxPatch((0.04, 0.84), 0.92, 0.08,
                                boxstyle="round,pad=0,rounding_size=0.02",
                                facecolor=color, edgecolor="none", alpha=0.90)
        ax.add_patch(stripe)
        # Icon: rounded square in figure coordinates so it looks square
        icon_bg = FancyBboxPatch((0.10, 0.43), 0.13, 0.24,
                                 boxstyle="round,pad=0,rounding_size=0.04",
                                 facecolor=color, edgecolor="none", alpha=0.92,
                                 transform=ax.transAxes)
        ax.add_patch(icon_bg)
        ax.text(0.165, 0.55, icon, fontsize=20, fontweight="bold",
                color="#0b1220", ha="center", va="center",
                transform=ax.transAxes)
        # Title
        ax.text(0.30, 0.62, title, fontsize=12.5, fontweight="bold",
                color=BRAND["text"], ha="left", va="center", linespacing=1.2)
        # Description
        ax.text(0.10, 0.26, desc, fontsize=10, color=BRAND["text_dim"],
                ha="left", va="center", linespacing=1.4)

    fig.suptitle("Six axes of realism", fontsize=15, fontweight="bold",
                 color=BRAND["text"], y=1.02)
    fig.tight_layout()
    fig.savefig(out / "features.png", facecolor=BRAND["bg_top"])
    plt.close(fig)


def main(out_dir: str = "docs/branding",
         sample_dir: str = "output_csv/sample") -> int:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    sample = Path(sample_dir)

    print(f"writing branding assets to {out}/")
    chart_hero(out, sample);          print("  ✓ hero.png")
    chart_stats_strip(out, sample);   print("  ✓ stats_strip.png")
    chart_schema(out);                print("  ✓ schema.png")
    chart_features(out);              print("  ✓ features.png")
    print("done")
    return 0


if __name__ == "__main__":
    out_dir = sys.argv[1] if len(sys.argv) > 1 else "docs/branding"
    sample_dir = sys.argv[2] if len(sys.argv) > 2 else "output_csv/sample"
    sys.exit(main(out_dir, sample_dir))

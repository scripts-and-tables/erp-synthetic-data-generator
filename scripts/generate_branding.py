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
    """Horizontal strip of stat cards with the dataset's headline numbers."""
    headers = pd.read_csv(sample_dir / "invoice_headers.csv")
    lines = pd.read_csv(sample_dir / "sales_lines.csv")
    customers = pd.read_csv(sample_dir / "customers.csv")

    pos = headers[headers.is_return == 0]
    neg = headers[headers.is_return == 1]
    rev = pos.grand_total.sum()
    margin = (pos.merge(lines, on="invoice_id")["gross_margin"].sum() /
              pos.merge(lines, on="invoice_id")["line_total"].sum() * 100)

    # Optional new tables
    n_tickets = 0
    n_nps = 0
    spend_total = 0.0
    if (sample_dir / "support_tickets.csv").exists():
        n_tickets = len(pd.read_csv(sample_dir / "support_tickets.csv"))
    if (sample_dir / "nps_surveys.csv").exists():
        n_nps = len(pd.read_csv(sample_dir / "nps_surveys.csv"))
    if (sample_dir / "marketing_spend.csv").exists():
        spend_total = pd.read_csv(sample_dir / "marketing_spend.csv")["spend_amount"].sum()

    stats = [
        (f"{len(customers):,}", "customers", BRAND["primary"]),
        (f"{len(pos):,}", "invoices", BRAND["primary_2"]),
        (f"{len(lines):,}", "sales lines", BRAND["accent"]),
        (f"${rev/1e6:.1f}M", "gross revenue", BRAND["accent_2"]),
        (f"{margin:.0f}%", "gross margin", BRAND["good"]),
        (f"{n_tickets:,}", "support tickets", "#0ea5e9"),
        (f"{n_nps:,}", "NPS surveys", "#ec4899"),
        (f"${spend_total/1e3:.0f}k", "marketing spend", "#a855f7"),
    ]

    n_cards = len(stats)
    fig, ax = plt.subplots(figsize=(16, 2.0))
    fig.patch.set_facecolor(BRAND["bg_top"])
    ax.set_facecolor(BRAND["bg_top"])
    ax.set_xlim(0, n_cards)
    ax.set_ylim(0, 1)
    ax.axis("off")

    for i, (val, label, color) in enumerate(stats):
        card = FancyBboxPatch((i + 0.07, 0.10), 0.86, 0.80,
                              boxstyle="round,pad=0.02,rounding_size=0.04",
                              facecolor=BRAND["card_bg"],
                              edgecolor=BRAND["card_border"], linewidth=1)
        ax.add_patch(card)
        stripe = FancyBboxPatch((i + 0.07, 0.10), 0.04, 0.80,
                                boxstyle="round,pad=0,rounding_size=0.02",
                                facecolor=color, edgecolor="none")
        ax.add_patch(stripe)
        ax.text(i + 0.5, 0.62, val, fontsize=18, fontweight="bold",
                color=BRAND["text"], ha="center", va="center")
        ax.text(i + 0.5, 0.30, label, fontsize=10,
                color=BRAND["text_dim"], ha="center", va="center")

    fig.savefig(out / "stats_strip.png", facecolor=BRAND["bg_top"])
    plt.close(fig)


def chart_schema(out: Path) -> None:
    """Entity-relationship diagram of all 9 CSVs."""
    fig, ax = plt.subplots(figsize=(17, 10))
    fig.patch.set_facecolor(BRAND["bg_top"])
    ax.set_facecolor(BRAND["bg_top"])
    ax.set_xlim(0, 17)
    ax.set_ylim(0, 10)
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
        ax.text(x + 0.20, y + h - 0.27, title, fontsize=12, fontweight="bold",
                color="#0b1220", ha="left", va="center", zorder=4)
        ax.text(x + BOX_W - 0.20, y + h - 0.27, badge, fontsize=8,
                fontweight="bold", color="#0b1220", ha="right", va="center",
                zorder=4,
                bbox=dict(boxstyle="round,pad=0.25", facecolor="white",
                          edgecolor="none", alpha=0.55))
        for j, (fname, ftype) in enumerate(fields):
            yj = y + h - 0.95 - j * 0.32
            ax.text(x + 0.20, yj, fname,
                    fontsize=9.5, color=BRAND["text"], family="monospace",
                    ha="left", va="center", zorder=4)
            ax.text(x + BOX_W - 0.20, yj, ftype,
                    fontsize=8.5, color=BRAND["text_dim"], family="monospace",
                    ha="right", va="center", zorder=4)

    # 4 columns: L, ML, MR, R
    COL_L  = 0.3
    COL_ML = 4.5
    COL_MR = 8.7
    COL_R  = 13.0

    # Top row (y=7.6): items, promotions, stores, marketing_spend
    box(COL_L, 7.6, 2.0, "items", [
        ("product_id", "PK"),
        ("subcategory", "str"),
        ("list_price", "money"),
        ("standard_cost", "money"),
    ], BRAND["primary"], "DIM")

    box(COL_ML, 7.6, 2.0, "promotions", [
        ("promotion_id", "PK"),
        ("discount_pct", "float"),
        ("start_date / end_date", "date"),
    ], BRAND["accent_2"], "DIM")

    box(COL_MR, 7.6, 2.0, "stores", [
        ("store_id", "PK"),
        ("city / latitude / longitude", "geo"),
        ("store_type", "enum"),
    ], BRAND["primary_2"], "DIM")

    box(COL_R, 7.6, 2.0, "marketing_spend", [
        ("month", "date"),
        ("channel", "enum"),
        ("spend_amount", "money"),
    ], "#a855f7", "DIM")

    # Middle row (y=4.4): invoice_headers central, support_tickets right
    box(COL_ML + 0.3, 4.4, 2.6, "invoice_headers", [
        ("invoice_id", "PK"),
        ("customer_id", "FK"),
        ("store_id / promotion_id", "FK"),
        ("subtotal / tax / freight", "money"),
        ("grand_total", "money"),
        ("is_return / reference", "0/1"),
    ], BRAND["accent"], "FACT")

    box(COL_R, 4.4, 2.6, "support_tickets", [
        ("ticket_id", "PK"),
        ("customer_id", "FK"),
        ("invoice_id", "FK"),
        ("category / priority", "enum"),
        ("resolution_hours", "float"),
        ("csat_score", "1-5"),
    ], "#0ea5e9", "FACT")

    # Bottom row (y=1.0): sales_lines, customers, nps_surveys
    box(COL_L + 0.5, 1.0, 2.6, "sales_lines", [
        ("line_id", "PK"),
        ("invoice_id", "FK"),
        ("product_id", "FK"),
        ("quantity / unit_price", "n/money"),
        ("line_total", "money"),
        ("gross_margin", "money"),
    ], BRAND["bad"], "FACT")

    box(COL_MR - 0.4, 1.0, 2.6, "customers", [
        ("customer_id", "PK"),
        ("cohort", "str"),
        ("acquisition_channel", "enum"),
        ("price_sensitivity", "float"),
        ("demographics + geo", "..."),
        ("yearly_income / country", "int/str"),
    ], BRAND["good"], "DIM")

    box(COL_R, 1.0, 2.6, "nps_surveys", [
        ("survey_id", "PK"),
        ("customer_id", "FK"),
        ("sent_at / response_at", "date"),
        ("score", "0-10"),
        ("nps_category", "enum"),
    ], "#ec4899", "FACT")

    # Arrows
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
            ax.text(mx, my, label, fontsize=9,
                    color=BRAND["text"], ha="center", va="center",
                    family="monospace", zorder=5,
                    bbox=dict(boxstyle="round,pad=0.25",
                              facecolor=BRAND["bg_top"],
                              edgecolor=BRAND["card_border"],
                              linewidth=0.8))

    HC_X = COL_ML + 0.3 + BOX_W / 2  # invoice_headers center x
    HC_TOP = 4.4 + 2.6
    HC_BOT = 4.4
    HC_L = COL_ML + 0.3
    HC_R = COL_ML + 0.3 + BOX_W

    # 1. promotions → invoice_headers (vertical short)
    arrow(COL_ML + BOX_W / 2, 7.6, HC_X - 0.5, HC_TOP, "promotion_id",
          label_x_off=1.0, label_y_off=0.00)

    # 2. stores → invoice_headers (down + left)
    arrow(COL_MR + BOX_W / 2, 7.6, HC_X + 0.5, HC_TOP, "store_id",
          label_x_off=0.5, label_y_off=0.00, rad=-0.10)

    # 3. items → sales_lines (long diagonal)
    SL_X = COL_L + 0.5 + BOX_W / 2
    arrow(COL_L + BOX_W, 7.6, SL_X, 1.0 + 2.6, "product_id",
          label_x_off=0.4, label_y_off=0.00, rad=-0.15)

    # 4. invoice_headers → sales_lines
    arrow(HC_L + 0.4, HC_BOT, SL_X + 0.6, 1.0 + 2.6, "invoice_id",
          label_x_off=-0.4, label_y_off=0.00, rad=-0.10)

    # 5. customers → invoice_headers
    CC_X = COL_MR - 0.4 + BOX_W / 2
    arrow(CC_X, 1.0 + 2.6, HC_R - 0.4, HC_BOT, "customer_id",
          label_x_off=0.4, label_y_off=0.00, rad=0.10)

    # 6. invoice_headers → support_tickets
    arrow(HC_R, HC_BOT + 1.5, COL_R, 4.4 + 1.5, "invoice_id",
          label_x_off=0.0, label_y_off=0.20, rad=0.0)

    # 7. customers → support_tickets
    ST_BOT = 4.4
    ST_X = COL_R + BOX_W / 2
    arrow(CC_X + 0.4, 1.0 + 2.6, ST_X - 0.4, ST_BOT, "customer_id",
          label_x_off=1.2, label_y_off=0.00, rad=0.20)

    # 8. customers → nps_surveys
    NPS_X = COL_R + BOX_W / 2
    arrow(CC_X + 0.6, 1.0 + 1.5, COL_R, 1.0 + 1.5, "customer_id",
          label_x_off=0.0, label_y_off=0.25, rad=0.0)

    # Title
    ax.text(8.5, 9.85, "Schema — 5 dimensions + 4 facts, fully relational",
            fontsize=15, fontweight="bold", color=BRAND["text"],
            ha="center", va="bottom")

    # Legend
    legend_items = [(BRAND["primary"], "DIM"), (BRAND["accent"], "FACT")]
    lx = 15.6
    for i, (color, label) in enumerate(legend_items):
        circle = patches.Circle((lx, 9.5 - i * 0.35), 0.10,
                                facecolor=color, edgecolor="none")
        ax.add_patch(circle)
        ax.text(lx + 0.20, 9.5 - i * 0.35, label, fontsize=10,
                color=BRAND["text_dim"], va="center")

    fig.savefig(out / "schema.png", facecolor=BRAND["bg_top"])
    plt.close(fig)


def chart_features(out: Path) -> None:
    """4x2 grid of feature highlight cards."""
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
        ("→", "Acquisition & CAC",
         "channel mix shifts over time · monthly marketing spend",
         "#a855f7"),
        ("◈", "Voice of customer",
         "support tickets with CSAT · quarterly NPS surveys",
         "#0ea5e9"),
    ]

    fig, axes = plt.subplots(2, 4, figsize=(17, 5))
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

    fig.suptitle("Eight axes of realism", fontsize=15, fontweight="bold",
                 color=BRAND["text"], y=1.02)
    fig.tight_layout()
    fig.savefig(out / "features.png", facecolor=BRAND["bg_top"])
    plt.close(fig)


def chart_phone_revenue(out: Path, sample_dir: Path) -> None:
    """Portrait dashboard: monthly revenue with holiday spikes + KPI."""
    headers = pd.read_csv(sample_dir / "invoice_headers.csv",
                          parse_dates=["order_date"])
    pos = headers[headers.is_return == 0].copy()
    pos["ym"] = pos["order_date"].dt.to_period("M").dt.to_timestamp()
    monthly = pos.groupby("ym")["grand_total"].sum().reset_index()
    last_year = monthly.tail(12)
    last_total = last_year["grand_total"].sum()
    prev_total = monthly.iloc[-24:-12]["grand_total"].sum()
    yoy = (last_total - prev_total) / prev_total * 100 if prev_total > 0 else 0

    fig = plt.figure(figsize=(4.0, 6.0), dpi=140)
    fig.patch.set_facecolor(BRAND["bg_top"])
    fig.text(0.08, 0.93, "SALES PULSE", fontsize=10, color=BRAND["text_dim"],
             fontweight="bold")
    fig.text(0.08, 0.88, "Last 12 months", fontsize=12, color=BRAND["text"])
    fig.text(0.08, 0.79, f"${last_total / 1e6:.2f}M", fontsize=32,
             fontweight="bold", color=BRAND["text"])
    yoy_color = BRAND["good"] if yoy >= 0 else BRAND["bad"]
    yoy_str = f"▲ {yoy:.1f}% YoY" if yoy >= 0 else f"▼ {abs(yoy):.1f}% YoY"
    fig.text(0.08, 0.74, yoy_str, fontsize=11, color=yoy_color,
             fontweight="bold")

    ax = fig.add_axes([0.10, 0.20, 0.84, 0.45])
    ax.set_facecolor("#101a30")
    ax.plot(monthly["ym"], monthly["grand_total"] / 1000,
            color=BRAND["accent"], linewidth=1.6)
    ax.fill_between(monthly["ym"], 0, monthly["grand_total"] / 1000,
                    color=BRAND["accent"], alpha=0.20)
    spikes = monthly[monthly["ym"].dt.month.isin([11, 12])]
    ax.scatter(spikes["ym"], spikes["grand_total"] / 1000,
               color=BRAND["accent_2"], s=14, zorder=5)
    ax.tick_params(axis="x", labelsize=8, colors=BRAND["text_dim"])
    ax.tick_params(axis="y", labelsize=8, colors=BRAND["text_dim"])
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(BRAND["card_border"])
    ax.spines["bottom"].set_color(BRAND["card_border"])
    ax.grid(axis="y", alpha=0.12, color=BRAND["text_dim"])

    fig.text(0.08, 0.10, "Holiday spikes",
             fontsize=10, color=BRAND["text_dim"], fontweight="bold")
    fig.text(0.08, 0.06, "Nov / Dec consistently 2–3× baseline, every year.",
             fontsize=9, color=BRAND["text_dim"])

    fig.savefig(out / "phone_revenue.png", facecolor=BRAND["bg_top"])
    plt.close(fig)


def chart_phone_cohorts(out: Path, sample_dir: Path) -> None:
    """Portrait dashboard: cohort distribution with retention pills."""
    customers = pd.read_csv(sample_dir / "customers.csv")
    counts = customers["cohort"].value_counts()
    order = ["LOYAL_HEAVY", "LOYAL_LIGHT", "GROWING", "DECLINING",
             "CHURN_RISK", "ONE_SHOT"]
    counts = counts.reindex([c for c in order if c in counts.index])
    color_for = {
        "LOYAL_HEAVY": BRAND["good"], "LOYAL_LIGHT": "#34d399",
        "GROWING": BRAND["primary"], "DECLINING": BRAND["accent"],
        "CHURN_RISK": BRAND["bad"], "ONE_SHOT": BRAND["muted"],
    }

    fig = plt.figure(figsize=(4.0, 6.0), dpi=140)
    fig.patch.set_facecolor(BRAND["bg_top"])
    fig.text(0.08, 0.93, "COHORT HEALTH", fontsize=10, color=BRAND["text_dim"],
             fontweight="bold")
    fig.text(0.08, 0.88, "All customers, all-time", fontsize=12,
             color=BRAND["text"])
    fig.text(0.08, 0.79, f"{counts.sum():,}", fontsize=32, fontweight="bold",
             color=BRAND["text"])
    fig.text(0.08, 0.74, "across 6 behavioral segments",
             fontsize=10, color=BRAND["text_dim"])

    ax = fig.add_axes([0.10, 0.16, 0.84, 0.50])
    ax.set_facecolor("#101a30")
    y_pos = np.arange(len(counts))[::-1]
    bars = ax.barh(y_pos, counts.values,
                   color=[color_for[c] for c in counts.index],
                   alpha=0.92, height=0.65)
    for bar, name, val in zip(bars, counts.index, counts.values):
        ax.text(val + counts.max() * 0.03, bar.get_y() + bar.get_height() / 2,
                f"{val}", va="center", color=BRAND["text"],
                fontsize=9, fontweight="bold")
    ax.set_yticks(y_pos)
    ax.set_yticklabels(counts.index, color=BRAND["text"], fontsize=9)
    ax.set_xticks([])
    for s in ax.spines.values():
        s.set_visible(False)

    fig.text(0.08, 0.06, "Sticky cohort assignment via seed ⊕ customer_id.",
             fontsize=9, color=BRAND["text_dim"])

    fig.savefig(out / "phone_cohorts.png", facecolor=BRAND["bg_top"])
    plt.close(fig)


def chart_phone_markets(out: Path) -> None:
    """Portrait dashboard: 3 markets with currency / VAT / weekend."""
    markets = [
        ("US",  "USD",  "8.75%", "Sat / Sun", BRAND["primary"], "Black Friday"),
        ("GCC", "AED",  "5.0%",  "Fri / Sat", BRAND["accent_2"], "Ramadan + Eid"),
        ("EU",  "EUR",  "20%",   "Sat / Sun", BRAND["primary_2"], "Boxing Week"),
    ]
    fig = plt.figure(figsize=(4.0, 6.0), dpi=140)
    fig.patch.set_facecolor(BRAND["bg_top"])
    fig.text(0.08, 0.93, "MARKETS", fontsize=10, color=BRAND["text_dim"],
             fontweight="bold")
    fig.text(0.08, 0.88, "Out of the box", fontsize=12, color=BRAND["text"])
    fig.text(0.08, 0.79, "3", fontsize=44, fontweight="bold", color=BRAND["text"])
    fig.text(0.08, 0.74, "preset markets · fully overridable",
             fontsize=10, color=BRAND["text_dim"])

    ax = fig.add_axes([0.0, 0.0, 1.0, 1.0])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    y_top = 0.66
    row_h = 0.13
    for i, (name, currency, vat, weekend, color, holidays) in enumerate(markets):
        y = y_top - i * row_h
        card = patches.FancyBboxPatch(
            (0.08, y - row_h * 0.85), 0.84, row_h * 0.80,
            boxstyle="round,pad=0,rounding_size=0.015",
            facecolor=BRAND["card_bg"], edgecolor=BRAND["card_border"],
            linewidth=1, transform=ax.transAxes,
        )
        ax.add_patch(card)
        # accent stripe
        stripe = patches.FancyBboxPatch(
            (0.08, y - row_h * 0.85), 0.018, row_h * 0.80,
            boxstyle="round,pad=0,rounding_size=0.005",
            facecolor=color, edgecolor="none", transform=ax.transAxes,
        )
        ax.add_patch(stripe)
        ax.text(0.13, y - 0.025, name, fontsize=14, fontweight="bold",
                color=BRAND["text"], transform=ax.transAxes, va="center")
        ax.text(0.30, y - 0.020, f"{currency} · VAT {vat}",
                fontsize=9, color=BRAND["text_dim"], transform=ax.transAxes,
                va="center")
        ax.text(0.30, y - 0.050, f"weekend {weekend}",
                fontsize=8, color=BRAND["text_dim"], transform=ax.transAxes,
                va="center")
        ax.text(0.62, y - 0.035, holidays, fontsize=8.5,
                color=color, transform=ax.transAxes, va="center",
                fontweight="bold")

    fig.text(0.08, 0.06, "Locale, currency, VAT, weekend, holidays",
             fontsize=9, color=BRAND["text_dim"])

    fig.savefig(out / "phone_markets.png", facecolor=BRAND["bg_top"])
    plt.close(fig)


def main(out_dir: str = "docs/branding",
         sample_dir: str = "output_csv/sample") -> int:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    sample = Path(sample_dir)

    print(f"writing branding assets to {out}/")
    chart_hero(out, sample);            print("  ✓ hero.png")
    chart_stats_strip(out, sample);     print("  ✓ stats_strip.png")
    chart_schema(out);                  print("  ✓ schema.png")
    chart_features(out);                print("  ✓ features.png")
    chart_phone_revenue(out, sample);   print("  ✓ phone_revenue.png")
    chart_phone_cohorts(out, sample);   print("  ✓ phone_cohorts.png")
    chart_phone_markets(out);           print("  ✓ phone_markets.png")
    print("done")
    return 0


if __name__ == "__main__":
    out_dir = sys.argv[1] if len(sys.argv) > 1 else "docs/branding"
    sample_dir = sys.argv[2] if len(sys.argv) > 2 else "output_csv/sample"
    sys.exit(main(out_dir, sample_dir))

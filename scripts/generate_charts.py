"""Generate showcase charts (PNGs) from a sample dataset.

Usage:
    python scripts/generate_charts.py [in_dir] [out_dir]

Renders ~9 charts that demonstrate the realism of the synthetic data:
- monthly revenue (seasonality + holiday spikes)
- daily revenue with Black Friday/Christmas markers (2023)
- cohort retention curves
- gross margin distribution
- promo lift (with vs without promo)
- returns share over time
- customer signup growth (logistic curve)
- cohort distribution
- top 10 products by revenue
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

plt.rcParams.update({
    "figure.dpi": 110,
    "savefig.dpi": 130,
    "savefig.bbox": "tight",
    "font.size": 11,
    "axes.titlesize": 13,
    "axes.titleweight": "bold",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.25,
    "grid.linestyle": "--",
    "figure.facecolor": "white",
})

PALETTE = {
    "primary": "#1f4e79",
    "accent": "#d97706",
    "muted": "#94a3b8",
    "good": "#059669",
    "bad": "#dc2626",
    "neutral": "#475569",
}


def load(in_dir: Path) -> dict[str, pd.DataFrame]:
    items = pd.read_csv(in_dir / "items.csv")
    customers = pd.read_csv(in_dir / "customers.csv", parse_dates=["created_at"])
    stores = pd.read_csv(in_dir / "stores.csv")
    promos = pd.read_csv(in_dir / "promotions.csv",
                        parse_dates=["start_date", "end_date"])
    headers = pd.read_csv(in_dir / "invoice_headers.csv",
                          parse_dates=["order_date", "ship_date", "due_date"])
    lines = pd.read_csv(in_dir / "sales_lines.csv")
    return {"items": items, "customers": customers, "stores": stores,
            "promos": promos, "headers": headers, "lines": lines}


def chart_monthly_revenue(d: dict, out: Path) -> None:
    h = d["headers"]
    h_pos = h[h.is_return == 0].copy()
    h_pos["ym"] = h_pos["order_date"].dt.to_period("M").dt.to_timestamp()
    monthly = h_pos.groupby("ym")["grand_total"].sum().reset_index()

    fig, ax = plt.subplots(figsize=(11, 4.5))
    ax.plot(monthly["ym"], monthly["grand_total"] / 1000,
            color=PALETTE["primary"], linewidth=1.6)
    ax.fill_between(monthly["ym"], 0, monthly["grand_total"] / 1000,
                    color=PALETTE["primary"], alpha=0.15)

    # Annotate the November/December spikes
    nov_dec = monthly[monthly["ym"].dt.month.isin([11, 12])]
    if not nov_dec.empty:
        peak = nov_dec.loc[nov_dec["grand_total"].idxmax()]
        ax.annotate(
            f"Holiday peak\n${peak['grand_total'] / 1000:,.0f}k",
            xy=(peak["ym"], peak["grand_total"] / 1000),
            xytext=(20, 25), textcoords="offset points",
            fontsize=10, color=PALETTE["accent"],
            arrowprops=dict(arrowstyle="->", color=PALETTE["accent"], lw=1),
        )

    ax.set_title("Monthly revenue — seasonality is built in")
    ax.set_xlabel("Month")
    ax.set_ylabel("Revenue ($ thousands)")
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    fig.tight_layout()
    fig.savefig(out / "monthly_revenue.png")
    plt.close(fig)


def chart_holiday_spikes(d: dict, out: Path) -> None:
    h = d["headers"]
    h_pos = h[h.is_return == 0].copy()
    one_year = h_pos[h_pos["order_date"].dt.year == 2023]
    daily = one_year.groupby(one_year["order_date"].dt.date)["grand_total"].sum()
    daily.index = pd.to_datetime(daily.index)

    fig, ax = plt.subplots(figsize=(11, 4.5))
    ax.plot(daily.index, daily.values, color=PALETTE["primary"],
            linewidth=0.9, alpha=0.85)
    ax.fill_between(daily.index, 0, daily.values,
                    color=PALETTE["primary"], alpha=0.10)

    # Black Friday 2023 = Nov 24, Christmas Eve = Dec 24, July 4
    markers = [
        (pd.Timestamp("2023-11-24"), "Black Friday"),
        (pd.Timestamp("2023-11-27"), "Cyber Monday"),
        (pd.Timestamp("2023-12-24"), "Christmas Eve"),
        (pd.Timestamp("2023-07-04"), "July 4"),
    ]
    for dt, label in markers:
        if dt in daily.index:
            v = daily.loc[dt]
            ax.scatter([dt], [v], color=PALETTE["accent"], s=42, zorder=5)
            ax.annotate(label, xy=(dt, v), xytext=(0, 10),
                        textcoords="offset points", ha="center",
                        fontsize=9, color=PALETTE["accent"])

    ax.set_title("Daily revenue, calendar year 2023 — holiday spikes are visible")
    ax.set_xlabel("Date")
    ax.set_ylabel("Revenue ($)")
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    fig.tight_layout()
    fig.savefig(out / "holiday_spikes_2023.png")
    plt.close(fig)


def chart_cohort_retention(d: dict, out: Path) -> None:
    customers = d["customers"][["customer_id", "created_at", "cohort"]].copy()
    customers["signup_year"] = customers["created_at"].dt.year
    headers = d["headers"][d["headers"].is_return == 0][["customer_id", "order_date"]].copy()
    df = headers.merge(customers, on="customer_id")
    df["months_since"] = (
        (df["order_date"].dt.year - df["created_at"].dt.year) * 12
        + (df["order_date"].dt.month - df["created_at"].dt.month)
    ).clip(lower=0)

    # By behavioral cohort (more interesting + larger N) instead of signup year
    cohort_size = customers["cohort"].value_counts()
    active = (
        df.groupby(["cohort", "months_since"])["customer_id"]
          .nunique().unstack(fill_value=0)
    )
    retention = active.div(cohort_size, axis=0) * 100
    # Smooth with 3-month rolling mean across columns to reveal underlying shape
    retention_smooth = retention.T.rolling(window=3, min_periods=1).mean().T

    fig, ax = plt.subplots(figsize=(11, 5))
    order = ["LOYAL_HEAVY", "LOYAL_LIGHT", "GROWING",
             "DECLINING", "CHURN_RISK", "ONE_SHOT"]
    colors = {"LOYAL_HEAVY": PALETTE["good"], "LOYAL_LIGHT": "#34d399",
              "GROWING": PALETTE["primary"], "DECLINING": PALETTE["accent"],
              "CHURN_RISK": PALETTE["bad"], "ONE_SHOT": PALETTE["muted"]}
    for cohort in order:
        if cohort not in retention_smooth.index:
            continue
        ser = retention_smooth.loc[cohort]
        ser = ser[ser.index <= 60]  # 5 years
        ax.plot(ser.index, ser.values,
                label=f"{cohort} (n={cohort_size[cohort]})",
                color=colors[cohort], linewidth=1.8)

    ax.set_title("Cohort retention — % of customers active N months after signup, by cohort")
    ax.set_xlabel("Months since signup")
    ax.set_ylabel("Monthly active customers (%, 3-mo smoothed)")
    ax.set_ylim(0, 100)
    ax.legend(loc="upper right", fontsize=9, framealpha=0.9, ncol=2)
    fig.tight_layout()
    fig.savefig(out / "cohort_retention.png")
    plt.close(fig)


def chart_gross_margin(d: dict, out: Path) -> None:
    lines = d["lines"]
    hdr = d["headers"][["invoice_id", "is_return"]]
    df = lines.merge(hdr, on="invoice_id")
    df = df[df["is_return"] == 0]
    df = df[df["line_total"] > 0]
    df["margin_pct"] = df["gross_margin"] / df["line_total"] * 100

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))

    axes[0].hist(df["margin_pct"], bins=50, color=PALETTE["good"], alpha=0.85,
                 edgecolor="white", linewidth=0.5)
    axes[0].axvline(df["margin_pct"].mean(), color=PALETTE["accent"],
                    linestyle="--", linewidth=1.5,
                    label=f"mean {df['margin_pct'].mean():.1f}%")
    axes[0].set_title("Gross margin distribution (per line)")
    axes[0].set_xlabel("Gross margin (%)")
    axes[0].set_ylabel("Lines")
    axes[0].legend(framealpha=0.9)

    by_cat = df.groupby(d["lines"].merge(d["items"][["product_id", "category"]], on="product_id")["category"])
    df2 = df.merge(d["items"][["product_id", "category"]], on="product_id")
    cat_margin = df2.groupby("category")["margin_pct"].mean().sort_values()
    bars = axes[1].barh(cat_margin.index, cat_margin.values,
                        color=PALETTE["primary"], alpha=0.85)
    for b, v in zip(bars, cat_margin.values):
        axes[1].text(v + 0.5, b.get_y() + b.get_height() / 2,
                     f"{v:.1f}%", va="center", fontsize=10,
                     color=PALETTE["neutral"])
    axes[1].set_title("Average gross margin by category")
    axes[1].set_xlabel("Gross margin (%)")
    axes[1].set_xlim(0, max(cat_margin.values) * 1.2)
    fig.tight_layout()
    fig.savefig(out / "gross_margin.png")
    plt.close(fig)


def chart_promo_lift(d: dict, out: Path) -> None:
    lines = d["lines"]
    hdr = d["headers"][["invoice_id", "is_return", "order_date"]]
    df = lines.merge(hdr, on="invoice_id")
    df = df[df["is_return"] == 0]
    df["ym"] = df["order_date"].dt.to_period("M").dt.to_timestamp()

    monthly = df.groupby("ym").agg(
        revenue=("line_total", "sum"),
        discount=("discount_amount", "sum"),
    ).reset_index()
    monthly["discount_share_pct"] = (
        monthly["discount"] / (monthly["revenue"] + monthly["discount"]) * 100
    )

    fig, ax = plt.subplots(figsize=(11, 4.5))
    ax.bar(monthly["ym"], monthly["discount"] / 1000, width=20,
           color=PALETTE["accent"], alpha=0.85,
           label="Total discount given ($k)")
    ax.set_xlabel("Month")
    ax.set_ylabel("Total discount given ($ thousands)", color=PALETTE["accent"])
    ax.tick_params(axis="y", labelcolor=PALETTE["accent"])
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    ax2 = ax.twinx()
    ax2.plot(monthly["ym"], monthly["discount_share_pct"],
             color=PALETTE["primary"], linewidth=1.6,
             label="Discount as % of gross revenue")
    ax2.set_ylabel("Discount share of gross revenue (%)",
                   color=PALETTE["primary"])
    ax2.tick_params(axis="y", labelcolor=PALETTE["primary"])
    ax2.grid(False)

    ax.set_title("Promotion impact — discounts spike during promo windows "
                 "(Black Friday, Boxing Week, seasonal sales)")
    fig.tight_layout()
    fig.savefig(out / "promo_lift.png")
    plt.close(fig)


def chart_returns_over_time(d: dict, out: Path) -> None:
    h = d["headers"].copy()
    h["q"] = h["order_date"].dt.to_period("Q").dt.to_timestamp()
    qg = h.groupby("q").agg(
        orders=("invoice_id", lambda s: (h.loc[s.index, "is_return"] == 0).sum()),
        returns=("invoice_id", lambda s: (h.loc[s.index, "is_return"] == 1).sum()),
    ).reset_index()
    qg["share"] = qg["returns"] / qg["orders"].replace(0, np.nan) * 100

    fig, ax = plt.subplots(figsize=(11, 4.2))
    ax.plot(qg["q"], qg["share"], color=PALETTE["bad"], linewidth=1.6,
            marker="o", markersize=4, label="Return share (%)")
    ax.fill_between(qg["q"], 0, qg["share"], color=PALETTE["bad"], alpha=0.10)
    ax.axhline(qg["share"].mean(), color=PALETTE["neutral"], linestyle="--",
               linewidth=1, label=f"avg {qg['share'].mean():.2f}%")
    ax.set_title("Returns share by quarter — stable around the configured rate")
    ax.set_xlabel("Quarter")
    ax.set_ylabel("Returns / orders (%)")
    ax.legend(framealpha=0.9)
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    fig.tight_layout()
    fig.savefig(out / "returns_over_time.png")
    plt.close(fig)


def chart_signup_curve(d: dict, out: Path) -> None:
    c = d["customers"].copy()
    c = c.sort_values("created_at")
    c["cum"] = np.arange(1, len(c) + 1)

    fig, ax = plt.subplots(figsize=(11, 4))
    ax.plot(c["created_at"], c["cum"], color=PALETTE["primary"], linewidth=1.8)
    ax.fill_between(c["created_at"], 0, c["cum"],
                    color=PALETTE["primary"], alpha=0.15)
    ax.set_title("Cumulative customer signups — logistic-growth curve, not uniform")
    ax.set_xlabel("Signup date")
    ax.set_ylabel("Cumulative customers")
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    fig.tight_layout()
    fig.savefig(out / "signup_curve.png")
    plt.close(fig)


def chart_cohort_distribution(d: dict, out: Path) -> None:
    c = d["customers"]
    counts = c["cohort"].value_counts()
    order = ["LOYAL_HEAVY", "LOYAL_LIGHT", "GROWING", "DECLINING",
             "CHURN_RISK", "ONE_SHOT"]
    counts = counts.reindex([x for x in order if x in counts.index])

    fig, ax = plt.subplots(figsize=(8.5, 4))
    colors = [PALETTE["good"], "#34d399", PALETTE["primary"],
              PALETTE["accent"], PALETTE["bad"], PALETTE["muted"]]
    bars = ax.bar(counts.index, counts.values, color=colors[:len(counts)],
                  alpha=0.9)
    for b, v in zip(bars, counts.values):
        ax.text(b.get_x() + b.get_width() / 2, v, f"{v}",
                ha="center", va="bottom", fontsize=10)
    ax.set_title(f"Customer cohort distribution (n={c.shape[0]})")
    ax.set_ylabel("Customers")
    ax.tick_params(axis="x", rotation=15)
    fig.tight_layout()
    fig.savefig(out / "cohort_distribution.png")
    plt.close(fig)


def chart_top_products(d: dict, out: Path) -> None:
    lines = d["lines"]
    hdr = d["headers"][["invoice_id", "is_return"]]
    df = lines.merge(hdr, on="invoice_id")
    df = df[df["is_return"] == 0]
    df = df.merge(d["items"][["product_id", "product_name", "category"]], on="product_id")
    top = df.groupby(["product_id", "product_name", "category"])["line_total"].sum() \
            .reset_index().sort_values("line_total", ascending=False).head(10)

    fig, ax = plt.subplots(figsize=(10, 5))
    cat_color = {"DEVICE": PALETTE["accent"], "REFILL": PALETTE["primary"],
                 "ACCESSORY": PALETTE["good"], "SPARE_PART": PALETTE["muted"]}
    bars = ax.barh(top["product_name"], top["line_total"] / 1000,
                   color=[cat_color.get(c, PALETTE["primary"]) for c in top["category"]],
                   alpha=0.85)
    for b, v in zip(bars, top["line_total"] / 1000):
        ax.text(v + 0.5, b.get_y() + b.get_height() / 2,
                f"${v:,.0f}k", va="center", fontsize=9,
                color=PALETTE["neutral"])
    ax.invert_yaxis()
    ax.set_title("Top 10 products by total revenue")
    ax.set_xlabel("Revenue ($ thousands)")

    # Legend
    from matplotlib.patches import Patch
    legend_handles = [Patch(facecolor=v, label=k, alpha=0.85)
                      for k, v in cat_color.items()]
    ax.legend(handles=legend_handles, loc="lower right", framealpha=0.9, fontsize=9)
    fig.tight_layout()
    fig.savefig(out / "top_products.png")
    plt.close(fig)


def main(in_dir: str = "output_csv/sample",
         out_dir: str = "docs/charts") -> int:
    in_path = Path(in_dir)
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    print(f"loading from {in_path}/")
    d = load(in_path)
    print(f"  customers={len(d['customers'])}  invoices={len(d['headers'])}  "
          f"lines={len(d['lines'])}")

    chart_monthly_revenue(d, out_path);     print("  ✓ monthly_revenue.png")
    chart_holiday_spikes(d, out_path);      print("  ✓ holiday_spikes_2023.png")
    chart_cohort_retention(d, out_path);    print("  ✓ cohort_retention.png")
    chart_gross_margin(d, out_path);        print("  ✓ gross_margin.png")
    chart_promo_lift(d, out_path);          print("  ✓ promo_lift.png")
    chart_returns_over_time(d, out_path);   print("  ✓ returns_over_time.png")
    chart_signup_curve(d, out_path);        print("  ✓ signup_curve.png")
    chart_cohort_distribution(d, out_path); print("  ✓ cohort_distribution.png")
    chart_top_products(d, out_path);        print("  ✓ top_products.png")
    print(f"all charts written to {out_path}/")
    return 0


if __name__ == "__main__":
    in_dir = sys.argv[1] if len(sys.argv) > 1 else "output_csv/sample"
    out_dir = sys.argv[2] if len(sys.argv) > 2 else "docs/charts"
    sys.exit(main(in_dir, out_dir))

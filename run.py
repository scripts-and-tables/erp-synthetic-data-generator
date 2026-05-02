"""CLI orchestrator: items + customers + stores + promotions + invoice headers
+ lines + marketing spend + support tickets + NPS surveys."""
from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

import pandas as pd

from src.cohorts import assign_cohort
from src.customers import generate_customers_df
from src.items import build_items_universe_df, sample_items_dataset_df
from src.marketing import build_marketing_spend_df
from src.markets import MARKETS, get_market
from src.promotions import build_promotions_df, build_promo_lookup
from src.rng_utils import make_rngs
from src.sales import generate_customer_sales
from src.stores import build_stores_df
from src.support import build_nps_surveys_df, build_support_tickets_df


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Generate synthetic ERP/CRM datasets (items, customers, "
                    "stores, promotions, invoice headers, sales lines)."
    )

    # Scale + dates
    p.add_argument("--n-customers", type=int, default=1000)
    p.add_argument("--date-from", default="2015-01-01",
                   help="Customers created_at start date (YYYY-MM-DD)")
    p.add_argument("--date-till", default="2025-12-31",
                   help="Sales end date (YYYY-MM-DD)")

    # Items sample sizes
    p.add_argument("--n-devices", type=int, default=5)
    p.add_argument("--n-accessories", type=int, default=10)
    p.add_argument("--n-spare-parts", type=int, default=8)
    p.add_argument("--n-refills", type=int, default=74)
    p.add_argument("--n-bulk-refills", type=int, default=1)

    # Customer field probabilities
    p.add_argument("--p-first-name", type=float, default=0.95)
    p.add_argument("--p-last-name", type=float, default=0.85)
    p.add_argument("--p-email", type=float, default=0.70)
    p.add_argument("--p-phone", type=float, default=0.80)
    p.add_argument("--p-email-opt-in", type=float, default=0.60)
    p.add_argument("--p-sms-opt-in", type=float, default=0.90)
    p.add_argument("--p-call-opt-in", type=float, default=0.75)

    # Realism knobs
    p.add_argument("--seed", type=int, default=42,
                   help="Master RNG seed; propagated to numpy + python random + Faker.")
    p.add_argument("--market", choices=sorted(MARKETS.keys()), default="us")
    p.add_argument("--vat-rate", type=float, default=None,
                   help="Override market default VAT.")
    p.add_argument("--currency", default=None, help="Override market default currency.")
    p.add_argument("--annual-inflation", type=float, default=None,
                   help="Override market default annual inflation rate (e.g. 0.03).")

    # Stores + promos
    p.add_argument("--n-stores", type=int, default=8)
    p.add_argument("--n-promotions-per-year", type=int, default=6)

    # Returns
    p.add_argument("--p-return", type=float, default=0.03)
    returns_group = p.add_mutually_exclusive_group()
    returns_group.add_argument("--enable-returns", dest="enable_returns",
                               action="store_true", default=True)
    returns_group.add_argument("--disable-returns", dest="enable_returns",
                               action="store_false")

    # Output
    p.add_argument("--out-dir", default="output_csv")

    return p.parse_args()


def _items_index_from_df(df_items: pd.DataFrame) -> dict[int, dict]:
    idx: dict[int, dict] = {}
    for rec in df_items.to_dict("records"):
        rec["_listed_from_date_obj"] = date.fromisoformat(str(rec["listed_from_date"]))
        idx[int(rec["product_id"])] = rec
    return idx


def main() -> None:
    print("data generation - started")
    args = parse_args()

    rngs = make_rngs(args.seed)
    market_cfg = get_market(
        args.market,
        vat_rate=args.vat_rate,
        currency=args.currency,
        annual_inflation=args.annual_inflation,
    )
    annual_inflation = float(market_cfg["inflation_default"])

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    date_from = date.fromisoformat(args.date_from)
    date_till = date.fromisoformat(args.date_till)
    if date_from > date_till:
        raise SystemExit("--date-from must be <= --date-till")

    # 1) Items
    print("  building items...")
    universe = build_items_universe_df()
    df_items = sample_items_dataset_df(
        universe,
        n_devices=args.n_devices,
        n_accessories=args.n_accessories,
        n_spare_parts=args.n_spare_parts,
        n_refills=args.n_refills,
        n_bulk_refills=args.n_bulk_refills,
        rng=rngs.py,
        currency=market_cfg["currency"],
        listed_from_floor=date_from,
        listing_window_days=365,
    )
    df_items.to_csv(out_dir / "items.csv", index=False)

    items_index = _items_index_from_df(df_items)
    device_ids = df_items[df_items.category == "DEVICE"].product_id.tolist()
    refill_ids = df_items[df_items.category == "REFILL"].product_id.tolist()
    accessory_ids = df_items[df_items.category == "ACCESSORY"].product_id.tolist()
    spare_ids = df_items[df_items.category == "SPARE_PART"].product_id.tolist()
    device_brand_pool = sorted(df_items[df_items.category == "DEVICE"].brand.unique().tolist())

    # 2) Stores
    print("  building stores...")
    df_stores = build_stores_df(
        market_cfg=market_cfg, n_stores=args.n_stores,
        rngs=rngs, opened_floor=date_from,
    )
    df_stores.to_csv(out_dir / "stores.csv", index=False)
    store_ids = df_stores["store_id"].tolist()

    # 3) Promotions
    print("  building promotions...")
    df_promos = build_promotions_df(
        date_from=date_from, date_till=date_till,
        market_cfg=market_cfg, n_per_year=args.n_promotions_per_year,
        rngs=rngs,
    )
    df_promos.to_csv(out_dir / "promotions.csv", index=False)
    promo_lookup = build_promo_lookup(
        df_promos, date_from=date_from, date_till=date_till,
        categories=["DEVICE", "REFILL", "ACCESSORY", "SPARE_PART"],
    )

    # 4) Customers
    print("  building customers...")
    df_customers = generate_customers_df(
        rngs=rngs,
        market_cfg=market_cfg,
        n_customers=args.n_customers,
        customers_created_at_start=args.date_from,
        customers_created_at_end=args.date_till,
        p_first_name=args.p_first_name,
        p_last_name=args.p_last_name,
        p_email=args.p_email,
        p_phone=args.p_phone,
        p_email_opt_in=args.p_email_opt_in,
        p_sms_opt_in=args.p_sms_opt_in,
        p_call_opt_in=args.p_call_opt_in,
        device_brand_pool=device_brand_pool,
    )
    df_customers.to_csv(out_dir / "customers.csv", index=False)

    # 5) Sales (streaming)
    print("  generating invoices and lines...")
    headers_path = out_dir / "invoice_headers.csv"
    lines_path = out_dir / "sales_lines.csv"
    headers_first = True
    lines_first = True
    line_id = 1

    n_total = len(df_customers)
    progress_every = max(1, n_total // 20)

    for i, cust in enumerate(df_customers.to_dict(orient="records"), start=1):
        cohort_spec = assign_cohort(
            int(cust["customer_id"]), rngs.seed, brand_pool=device_brand_pool,
        )
        # Per-customer deterministic RNG so customer order doesn't change output.
        from random import Random
        cust_rng = Random((rngs.seed * 2654435761) ^ (int(cust["customer_id"]) * 11400714819323198485) & 0xFFFFFFFFFFFFFFFF)

        headers, lines, line_id = generate_customer_sales(
            customer_id=int(cust["customer_id"]),
            sales_start_date=str(cust["created_at"]),
            sales_end_date=args.date_till,
            items_index=items_index,
            device_product_ids=device_ids,
            refill_product_ids=refill_ids,
            accessory_product_ids=accessory_ids,
            spare_part_product_ids=spare_ids,
            store_ids=store_ids,
            market_cfg=market_cfg,
            promo_lookup=promo_lookup,
            annual_inflation=annual_inflation,
            p_return=args.p_return,
            enable_returns=args.enable_returns,
            cohort_spec=cohort_spec,
            rng=cust_rng,
            line_id_start=line_id,
        )

        if headers:
            pd.DataFrame.from_records(headers).to_csv(
                headers_path, mode="w" if headers_first else "a",
                index=False, header=headers_first,
            )
            headers_first = False
        if lines:
            pd.DataFrame.from_records(lines).to_csv(
                lines_path, mode="w" if lines_first else "a",
                index=False, header=lines_first,
            )
            lines_first = False

        if i % progress_every == 0 or i == n_total:
            print(f"    customers processed: {i}/{n_total}")

    # If no headers were ever written, still produce empty files with headers
    if headers_first:
        pd.DataFrame(columns=[
            "invoice_id", "customer_id", "store_id", "order_date", "ship_date",
            "due_date", "subtotal", "discount_total", "tax_amount", "freight",
            "grand_total", "vat_rate", "currency", "payment_method",
            "promotion_id", "is_return", "reference_invoice_id", "n_lines",
        ]).to_csv(headers_path, index=False)
    if lines_first:
        pd.DataFrame(columns=[
            "line_id", "invoice_id", "product_id", "quantity", "unit_price",
            "discount_pct", "discount_amount", "extended_amount", "line_total",
            "unit_standard_cost", "line_cost", "gross_margin",
        ]).to_csv(lines_path, index=False)

    # 6) Marketing spend (independent of sales — purely calendar-driven)
    print("  building marketing spend...")
    df_marketing = build_marketing_spend_df(
        date_from=date_from, date_till=date_till,
        market_cfg=market_cfg, rngs=rngs,
    )
    df_marketing.to_csv(out_dir / "marketing_spend.csv", index=False)

    # 7) Support tickets and NPS surveys (need invoice headers as input)
    print("  building support tickets and NPS surveys...")
    df_headers = pd.read_csv(headers_path)
    from random import Random
    support_rng = Random((rngs.seed * 2654435761) ^ 0xC0FFEE)
    df_tickets = build_support_tickets_df(
        customers_df=df_customers, headers_df=df_headers,
        rng=support_rng, date_till=date_till,
    )
    df_tickets.to_csv(out_dir / "support_tickets.csv", index=False)

    nps_rng = Random((rngs.seed * 2654435761) ^ 0xBADF00D)
    df_nps = build_nps_surveys_df(
        customers_df=df_customers, headers_df=df_headers,
        rng=nps_rng, date_from=date_from, date_till=date_till,
    )
    df_nps.to_csv(out_dir / "nps_surveys.csv", index=False)

    print("data generation - completed")


if __name__ == "__main__":
    main()

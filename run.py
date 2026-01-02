import random
from pathlib import Path
import pandas as pd
import argparse

from src.items import build_items_universe_df, sample_items_dataset_df
from src.customers import generate_customers_df
from src.sales import generate_customer_sales_rows

# N_CUSTOMERS = 1_000 # 300_000
# DATE_FROM = "2015-01-01"
# DATE_TILL = "2025-12-31"

OUT_DIR = Path("output_csv")

def parse_args():
    p = argparse.ArgumentParser(description="Generate synthetic ERP/CRM datasets (items, customers, sales)")

    p.add_argument("--n-customers", type=int, default=1000, help="Number of customers to generate")

    # Date range
    p.add_argument("--date-from", default="2015-01-01", help="Customers created_at start date (YYYY-MM-DD)")
    p.add_argument("--date-till", default="2025-12-31", help="Sales end date (YYYY-MM-DD)")

    # Items sample sizes
    p.add_argument("--n-devices", type=int, default=5)
    p.add_argument("--n-accessories", type=int, default=10)
    p.add_argument("--n-spare-parts", type=int, default=8)
    p.add_argument("--n-refills", type=int, default=74)
    p.add_argument("--n-bulk-refills", type=int, default=1)

    # Customer field probabilities
    p.add_argument("--p-first-name", type=float, default=0.90)
    p.add_argument("--p-last-name", type=float, default=0.60)
    p.add_argument("--p-email", type=float, default=0.70)
    p.add_argument("--p-phone", type=float, default=0.80)

    # Opt-in probabilities (applied only if contact exists)
    p.add_argument("--p-email-opt-in", type=float, default=0.60)
    p.add_argument("--p-sms-opt-in", type=float, default=0.90)
    p.add_argument("--p-call-opt-in", type=float, default=0.75)

    # Locale
    p.add_argument("--faker-locale", default="en_US")

    return p.parse_args()

def main():
    print('data generation - started')

    args = parse_args()

    universe = build_items_universe_df()

    df_items = sample_items_dataset_df(
        universe,
        n_devices=args.n_devices,
        n_accessories=args.n_accessories,
        n_spare_parts=args.n_spare_parts,
        n_refills=args.n_refills,
        n_bulk_refills=args.n_bulk_refills,
    )
    df_items.to_csv(OUT_DIR / "items.csv", index=False)


    df_customers = generate_customers_df(
        faker_locale=args.faker_locale,
        n_customers=args.n_customers,
        customers_created_at_start=args.date_from,
        customers_created_at_end=args.date_till,
        p_first_name=args.p_first_name,
        p_last_name=args.p_last_name,
        p_email=args.p_email,
        p_phone=args.p_phone,
        p_email_opt_in=args.p_email_opt_in,   # only if email exists
        p_sms_opt_in=args.p_sms_opt_in,     # only if phone exists
        p_call_opt_in=args.p_call_opt_in,    # only if phone exists
        blank="",
    )
    df_customers.to_csv(OUT_DIR / "customers.csv", index=False)


    # SALES
    first_write = True
    for customer_dict in df_customers.to_dict(orient="records"):
        sales = generate_customer_sales_rows(
            customer_id=customer_dict["customer_id"],
            sales_start_date=customer_dict["created_at"],
            sales_end_date=args.date_till,
            device_product_ids=df_items[df_items.category=='DEVICE'].product_id.to_list(),
            refill_product_ids= df_items[df_items.category=='REFILL'].product_id.to_list(),
            accessory_product_ids=df_items[df_items.category=='ACCESSORY'].product_id.to_list(),
            spare_part_product_ids=df_items[df_items.category=='SPARE_PART'].product_id.to_list(),
            store_ids= list(range(101, 110)),
            p_buy_by_year= random.choice ([
                [0.05, 0.07, 0.08, 0.09],       # +++
                [0.04, 0.06, 0.07, 0.08],       # ++
                [0.02, 0.03, 0.04, 0.06],       # ++
                [0.01, 0.02, 0.03, 0.04],       # +
                [0.06, 0.04, 0.03, 0.02],       # -
                [0.03, 0.02, 0.015, 0.01],      # -
                [0.01, 0.008, 0.006, 0.004]     # -
            ]),
            p_close_day=random.choice([0.0001, 0.0002, 0.0003, 0.0004]),
            p_invoice_by_nth=random.choice([
                [1.00, 0.80, 0.50, 0.10],
                [1.00, 0.15, 0.05, 0.01],
                [1.00, 0.05, 0.01, 0.00],
                [1.00, 0.01],
                [1.00, 0.00],
            ]),
            p_device_by_nth=random.choice([
                [0.99, 0.10, 0.00],
                [0.90, 0.35, 0.15, 0.01],
                [0.95, 0.00],
            ]),
            refill_count_probs=random.choice([
                [0.95, 0.80, 0.50, 0.10],
                [0.90, 0.75, 0.60, 0.30],
                [0.85, 0.80, 0.20, 0.05],
                [0.70, 0.30, 0.10, 0.05],
                [0.60, 0.30, 0.10, 0.05],
            ]),
            p_refill_invoice=0.95,
            p_accessory_invoice=random.choice( [0.08, 0.06, 0.05, 0.03, 0.00]),
            p_spare_part_invoice=random.choice([0.10, 0.05, 0.03, 0.01, 0.00]),
            stop_invoices_on_lost_day=True)

        if not sales:
            continue

        df_chunk = pd.DataFrame.from_records(sales)

        mode = "w" if first_write else "a"
        df_chunk.to_csv(OUT_DIR / 'sales.csv', mode=mode, index=False, header=first_write)

        first_write = False
    print('data generation - completed')

if __name__ == "__main__":
    main()
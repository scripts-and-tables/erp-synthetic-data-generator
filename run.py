import random

from src.items import build_items_universe_df, sample_items_dataset_df
from src.customers import generate_customers_df
from src.sales import generate_customer_sales_rows

N_CUSTOMERS = 10_000 # 300_000
DATE_FROM = "2015-01-01"
DATE_TILL = "2025-12-31"

universe = build_items_universe_df()

df_items = sample_items_dataset_df(
    universe,
    n_devices=5,
    n_accessories=10,
    n_spare_parts=8,
    n_refills=74,
    n_bulk_refills=1,
)

df_customers = generate_customers_df(
    faker_locale="en_US",
    n_customers=N_CUSTOMERS,
    customers_created_at_start=DATE_FROM,
    customers_created_at_end=DATE_TILL,
    p_first_name=0.90,
    p_last_name=0.60,
    p_email=0.70,
    p_phone=0.80,
    p_email_opt_in=0.60,   # only if email exists
    p_sms_opt_in=0.90,     # only if phone exists
    p_call_opt_in=0.75,    # only if phone exists
    blank="",
)

sales_list = []
for customer_dict in df_customers.to_dict(orient="records"):
    sales = generate_customer_sales_rows(
        customer_id=customer_dict["customer_id"],
        sales_start_date=customer_dict["created_at"],
        sales_end_date=DATE_TILL,
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
    sales_list.append(sales)
from src.items import build_items_universe_df, sample_items_dataset_df
from src.customers import generate_customers_df

universe = build_items_universe_df()

df_items = sample_items_dataset_df(
    universe,
    seed=42,
    n_devices=5,
    n_accessories=10,
    n_spare_parts=8,
    n_refills=74,
    n_bulk_refills=1,
)

df_customers = generate_customers_df(
    seed=42,
    faker_locale="en_US",
    n_customers=300_000,
    customers_created_at_start="2015-01-01",
    customers_created_at_end="2025-12-31",
    p_first_name=0.90,
    p_last_name=0.60,
    p_email=0.70,
    p_phone=0.80,
    p_email_opt_in=0.60,   # only if email exists
    p_sms_opt_in=0.90,     # only if phone exists
    p_call_opt_in=0.75,    # only if phone exists
    blank="",
)

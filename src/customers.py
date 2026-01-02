import pandas as pd
import numpy as np
from faker import Faker
from datetime import date


def generate_customers_df(
    *,
    faker_locale: str,
    n_customers: int,
    customers_created_at_start: str,   # ISO 'YYYY-MM-DD'
    customers_created_at_end: str,     # ISO 'YYYY-MM-DD'
    p_first_name: float,
    p_last_name: float,
    p_email: float,
    p_phone: float,
    p_email_opt_in: float,             # applied ONLY when email is present
    p_sms_opt_in: float,               # applied ONLY when phone is present
    p_call_opt_in: float,              # applied ONLY when phone is present
    blank: str = "",
) -> pd.DataFrame:
    """
    Generate customers master dataset.

    Output columns:
      customer_id (int)           Sequential 1..N (after sorting by created_at)
      created_at (str)            ISO 'YYYY-MM-DD'
      first_name (str or blank)
      last_name (str or blank)
      email (str or blank)
      phone (str or blank)
      email_opt_in (0/1)          If email missing => 0
      sms_opt_in (0/1)            If phone missing => 0
      call_opt_in (0/1)           If phone missing => 0
    """
    n = int(n_customers)
    rng = np.random.default_rng()
    fake = Faker(faker_locale)

    # created_at uniform by day
    start = np.datetime64(date.fromisoformat(customers_created_at_start).isoformat(), "D")
    end = np.datetime64(date.fromisoformat(customers_created_at_end).isoformat(), "D")

    total_days = int((end - start).astype("timedelta64[D]").astype(int))
    offsets = rng.integers(0, total_days + 1, size=n, dtype=np.int32)
    created_at = (start + offsets.astype("timedelta64[D]")).astype("datetime64[D]")

    def gen_optional_strings(p, gen_func):
        mask = rng.random(n) < float(p)
        out = np.full(n, blank, dtype=object)
        k = int(mask.sum())
        if k > 0:
            out[mask] = [gen_func() for _ in range(k)]
        return out, mask

    first_name, _ = gen_optional_strings(p_first_name, fake.first_name)
    last_name, _ = gen_optional_strings(p_last_name, fake.last_name)
    email, email_mask = gen_optional_strings(p_email, fake.email)
    phone, phone_mask = gen_optional_strings(p_phone, fake.phone_number)

    # Opt-ins: only possible if contact exists; otherwise forced 0
    email_opt_in_arr = np.zeros(n, dtype=np.int8)
    if email_mask.any():
        email_opt_in_arr[email_mask] = (rng.random(int(email_mask.sum())) < float(p_email_opt_in)).astype(np.int8)

    sms_opt_in_arr = np.zeros(n, dtype=np.int8)
    call_opt_in_arr = np.zeros(n, dtype=np.int8)
    if phone_mask.any():
        m = int(phone_mask.sum())
        sms_opt_in_arr[phone_mask] = (rng.random(m) < float(p_sms_opt_in)).astype(np.int8)
        call_opt_in_arr[phone_mask] = (rng.random(m) < float(p_call_opt_in)).astype(np.int8)

    df = pd.DataFrame({
        "created_at": created_at.astype(str),  # ISO YYYY-MM-DD
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "phone": phone,
        "email_opt_in": email_opt_in_arr,
        "sms_opt_in": sms_opt_in_arr,
        "call_opt_in": call_opt_in_arr,
    })

    # Sort by created_at, then assign sequential customer_id starting at 1
    df = df.sort_values("created_at", kind="mergesort").reset_index(drop=True)
    df.insert(0, "customer_id", np.arange(1, len(df) + 1, dtype=np.int64))

    return df

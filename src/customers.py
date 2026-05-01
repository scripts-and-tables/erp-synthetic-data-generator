"""Customer master with demographics, geography, cohort, and growth-curve signups."""
from __future__ import annotations

from datetime import date
from typing import Any

import numpy as np
import pandas as pd
from faker import Faker

from .cohorts import assign_cohort
from .rng_utils import RNGs


_OCCUPATIONS = [
    ("Professional", 0.30),
    ("Skilled Manual", 0.20),
    ("Clerical", 0.15),
    ("Management", 0.10),
    ("Manual", 0.10),
    ("Student", 0.06),
    ("Retired", 0.05),
    ("Self-Employed", 0.04),
]
_EDUCATIONS = [
    ("High School", 0.30),
    ("Partial College", 0.20),
    ("Bachelors", 0.30),
    ("Graduate Degree", 0.12),
    ("Partial High School", 0.08),
]
_MARITAL = [("Single", 0.45), ("Married", 0.45), ("Divorced", 0.10)]
_GENDER = [("M", 0.50), ("F", 0.50)]


def _weighted_pick(rng: np.random.Generator, weights: list[tuple[str, float]]) -> str:
    labels = [w[0] for w in weights]
    probs = np.array([w[1] for w in weights], dtype=float)
    probs = probs / probs.sum()
    idx = int(rng.choice(len(labels), p=probs))
    return labels[idx]


def _signup_dates(rngs: RNGs, n: int, start: date, end: date) -> np.ndarray:
    """Logistic-growth signup curve: few early, ramp mid, plateau end."""
    total_days = max(1, (end - start).days)
    midpoint = 0.6
    steepness = 8.0
    u = rngs.np.uniform(0.001, 0.999, size=n)
    # Inverse logistic centered at `midpoint` with `steepness`.
    t = midpoint + (1.0 / steepness) * np.log(u / (1.0 - u))
    t = np.clip(t, 0.0, 1.0)
    offsets = (t * total_days).astype(np.int64)
    start64 = np.datetime64(start.isoformat(), "D")
    return (start64 + offsets.astype("timedelta64[D]")).astype("datetime64[D]")


def _income_lognormal(rng: np.random.Generator, n: int, country: str) -> np.ndarray:
    # Country-aware median income (rough); lognormal sigma ~0.55.
    median_by_country = {
        "US": 55_000, "DE": 45_000, "FR": 35_000, "IT": 30_000, "ES": 28_000,
        "AE": 90_000, "SA": 75_000, "QA": 95_000, "KW": 70_000, "OM": 40_000,
    }
    mu = np.log(median_by_country.get(country, 40_000))
    return np.round(rng.lognormal(mean=mu, sigma=0.55, size=n) / 1000.0) * 1000.0


def generate_customers_df(
    *,
    rngs: RNGs,
    market_cfg: dict[str, Any],
    n_customers: int,
    customers_created_at_start: str,
    customers_created_at_end: str,
    p_first_name: float = 0.95,
    p_last_name: float = 0.85,
    p_email: float = 0.70,
    p_phone: float = 0.80,
    p_email_opt_in: float = 0.60,
    p_sms_opt_in: float = 0.90,
    p_call_opt_in: float = 0.75,
    blank: str = "",
    device_brand_pool: list[str] | None = None,
) -> pd.DataFrame:
    """Generate customers master dataset with demographics, geography, cohort.

    Output columns (in order):
      customer_id, created_at, first_name, last_name, email, phone,
      email_opt_in, sms_opt_in, call_opt_in,
      gender, birth_year, marital_status, occupation, yearly_income,
      num_children, house_owner_flag, education,
      country, region, city, postal_code,
      cohort, price_sensitivity, brand_affinity, market
    """
    n = int(n_customers)
    rng_np = rngs.np
    rng_py = rngs.py
    fake = Faker(market_cfg["faker_locale"])
    Faker.seed(rngs.seed)

    start = date.fromisoformat(customers_created_at_start)
    end = date.fromisoformat(customers_created_at_end)
    if start > end:
        raise ValueError("customers_created_at_start must be <= customers_created_at_end")

    created_at = _signup_dates(rngs, n, start, end)

    def gen_optional(p: float, gen_func) -> tuple[np.ndarray, np.ndarray]:
        mask = rng_np.random(n) < float(p)
        out = np.full(n, blank, dtype=object)
        k = int(mask.sum())
        if k > 0:
            out[mask] = [gen_func() for _ in range(k)]
        return out, mask

    first_name, _ = gen_optional(p_first_name, fake.first_name)
    last_name, _ = gen_optional(p_last_name, fake.last_name)
    email, email_mask = gen_optional(p_email, fake.email)
    phone, phone_mask = gen_optional(p_phone, fake.phone_number)

    email_opt_in_arr = np.zeros(n, dtype=np.int8)
    if email_mask.any():
        email_opt_in_arr[email_mask] = (rng_np.random(int(email_mask.sum())) < float(p_email_opt_in)).astype(np.int8)

    sms_opt_in_arr = np.zeros(n, dtype=np.int8)
    call_opt_in_arr = np.zeros(n, dtype=np.int8)
    if phone_mask.any():
        m = int(phone_mask.sum())
        sms_opt_in_arr[phone_mask] = (rng_np.random(m) < float(p_sms_opt_in)).astype(np.int8)
        call_opt_in_arr[phone_mask] = (rng_np.random(m) < float(p_call_opt_in)).astype(np.int8)

    # Demographics (vectorized where possible)
    genders = np.array([_weighted_pick(rng_np, _GENDER) for _ in range(n)], dtype=object)
    occupations = np.array([_weighted_pick(rng_np, _OCCUPATIONS) for _ in range(n)], dtype=object)
    educations = np.array([_weighted_pick(rng_np, _EDUCATIONS) for _ in range(n)], dtype=object)
    marital = np.array([_weighted_pick(rng_np, _MARITAL) for _ in range(n)], dtype=object)

    # Age via beta(2,5) skewed-young, mapped to [18, 75]
    age_u = rng_np.beta(2.0, 4.0, size=n)
    ages = (18 + age_u * (75 - 18)).astype(int)
    current_year = max(end.year, start.year)
    birth_years = current_year - ages

    num_children = rng_np.choice([0, 1, 2, 3, 4], p=[0.45, 0.20, 0.20, 0.10, 0.05], size=n)
    house_owner = (rng_np.random(n) < 0.55).astype(np.int8)

    # Geography from market country pool
    country_pool = market_cfg["country_pool"]
    country_labels = [c for c, _ in country_pool]
    country_probs = np.array([w for _, w in country_pool], dtype=float)
    country_probs = country_probs / country_probs.sum()
    country_idx = rng_np.choice(len(country_labels), p=country_probs, size=n)
    countries = np.array([country_labels[i] for i in country_idx], dtype=object)

    regions = np.empty(n, dtype=object)
    cities = np.empty(n, dtype=object)
    postal_codes = np.empty(n, dtype=object)
    for i in range(n):
        # Faker locale doesn't always match country; fall back to generic city/region.
        try:
            cities[i] = fake.city()
        except Exception:
            cities[i] = ""
        try:
            regions[i] = fake.state() if hasattr(fake, "state") else ""
        except Exception:
            regions[i] = ""
        try:
            postal_codes[i] = fake.postcode() if hasattr(fake, "postcode") else fake.zipcode() if hasattr(fake, "zipcode") else ""
        except Exception:
            postal_codes[i] = ""

    # Income depends on country (vectorized per-country)
    yearly_income = np.zeros(n, dtype=float)
    for c in set(countries):
        idx = np.where(countries == c)[0]
        if len(idx):
            yearly_income[idx] = _income_lognormal(rng_np, len(idx), c)

    # Build dataframe
    df = pd.DataFrame({
        "created_at": created_at.astype(str),
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "phone": phone,
        "email_opt_in": email_opt_in_arr,
        "sms_opt_in": sms_opt_in_arr,
        "call_opt_in": call_opt_in_arr,
        "gender": genders,
        "birth_year": birth_years.astype(int),
        "marital_status": marital,
        "occupation": occupations,
        "yearly_income": yearly_income.astype(int),
        "num_children": num_children.astype(int),
        "house_owner_flag": house_owner,
        "education": educations,
        "country": countries,
        "region": regions,
        "city": cities,
        "postal_code": postal_codes,
    })

    df = df.sort_values("created_at", kind="mergesort").reset_index(drop=True)
    df.insert(0, "customer_id", np.arange(1, len(df) + 1, dtype=np.int64))

    # Cohort assignment (deterministic per customer_id + seed)
    cohorts = []
    sensitivities = []
    affinities = []
    for cid in df["customer_id"].tolist():
        info = assign_cohort(int(cid), rngs.seed, brand_pool=device_brand_pool)
        cohorts.append(info["cohort"])
        sensitivities.append(info["price_sensitivity"])
        affinities.append(info["brand_affinity"])

    df["cohort"] = cohorts
    df["price_sensitivity"] = sensitivities
    df["brand_affinity"] = affinities
    df["market"] = market_cfg["key"]

    return df


def cohort_for_customer(customer_id: int, seed: int,
                        brand_pool: list[str] | None = None) -> dict[str, Any]:
    """Re-derive a customer's full cohort spec without re-loading the DataFrame."""
    return assign_cohort(int(customer_id), int(seed), brand_pool=brand_pool)

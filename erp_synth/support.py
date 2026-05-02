"""Support tickets + NPS surveys — voice-of-customer data.

Both are generated *after* invoices, since they reference invoice activity:

- support_tickets.csv  → opened by customers within ~30 days of an invoice;
  category mix, CSAT score, and resolution time vary by category and cohort.
- nps_surveys.csv      → quarterly survey to customers active in trailing
  90 days; ~30% response rate; score skewed by cohort.
"""
from __future__ import annotations

import random
from datetime import date, timedelta
from typing import Any

import pandas as pd

_TICKET_CHANNELS = [("Email", 0.40), ("Chat", 0.30), ("Phone", 0.20),
                    ("WhatsApp", 0.07), ("Social", 0.03)]
_TICKET_CATEGORIES = [
    ("Delivery",   0.30),
    ("Quality",    0.20),
    ("Billing",    0.15),
    ("Return",     0.15),
    ("Setup help", 0.10),
    ("Account",    0.05),
    ("Other",      0.05),
]
_TICKET_PRIORITY = [("Low", 0.55), ("Medium", 0.30), ("High", 0.13), ("Urgent", 0.02)]

# Per-cohort ticket propensity — fraction of customers who file at least one ticket
_COHORT_TICKET_RATE = {
    "LOYAL_HEAVY": 0.35,   # they buy a lot, so absolute volume is highest
    "LOYAL_LIGHT": 0.15,
    "GROWING":     0.20,
    "DECLINING":   0.18,
    "CHURN_RISK":  0.30,
    "ONE_SHOT":    0.10,
}

# NPS score distribution by cohort (mean, std) — clipped to [0, 10]
_COHORT_NPS = {
    "LOYAL_HEAVY": (9.2, 1.0),
    "LOYAL_LIGHT": (8.4, 1.4),
    "GROWING":     (7.8, 1.6),
    "DECLINING":   (5.5, 2.5),
    "CHURN_RISK":  (3.8, 2.5),
    "ONE_SHOT":    (6.0, 2.5),
}


def _weighted(rng: random.Random, weights):
    total = sum(w for _, w in weights)
    x = rng.random() * total
    acc = 0.0
    for v, w in weights:
        acc += w
        if x <= acc:
            return v
    return weights[-1][0]


def _resolution_hours(rng: random.Random, category: str, priority: str) -> float:
    """Right-skewed resolution time depending on category/priority."""
    base = {
        "Delivery": 18, "Quality": 24, "Billing": 8,
        "Return": 36, "Setup help": 4, "Account": 6, "Other": 12,
    }.get(category, 12)
    pri_mult = {"Urgent": 0.3, "High": 0.6, "Medium": 1.0, "Low": 1.5}[priority]
    raw = base * pri_mult * rng.lognormvariate(0, 0.6)
    return round(min(raw, 24 * 14), 2)  # cap at 14 days


def build_support_tickets_df(*, customers_df: pd.DataFrame,
                             headers_df: pd.DataFrame,
                             rng: random.Random,
                             date_till: date) -> pd.DataFrame:
    """Generate tickets opened within 30 days of an invoice.

    Each (customer_id, invoice_id) has a small probability of triggering a
    ticket; that probability is gated by the customer's cohort propensity.
    """
    rows: list[dict[str, Any]] = []

    # Index headers by customer
    customer_cohort = dict(zip(customers_df["customer_id"].astype(int),
                               customers_df["cohort"]))

    pos_headers = headers_df[headers_df.is_return == 0].copy()
    pos_headers["order_date_dt"] = pd.to_datetime(pos_headers["order_date"]).dt.date

    # Per-customer ticket probability — uniform over their invoices
    ticket_id = 1
    for cid, group in pos_headers.groupby("customer_id"):
        cohort = customer_cohort.get(int(cid), "GROWING")
        # Probability that this customer files at least one ticket somewhere in their lifetime
        lifetime_p = _COHORT_TICKET_RATE.get(cohort, 0.20)
        if rng.random() >= lifetime_p:
            continue

        # Number of tickets — most ticket-filers file 1, some 2-3
        n_tickets = _weighted(rng, [(1, 0.65), (2, 0.22), (3, 0.09), (4, 0.04)])

        n_invoices = len(group)
        if n_invoices == 0:
            continue

        # Sample invoice indices for tickets
        picks = rng.sample(range(n_invoices), k=min(n_tickets, n_invoices))
        rows_list = group.iloc[picks].to_dict("records")

        for h in rows_list:
            opened = h["order_date_dt"] + timedelta(days=rng.randint(0, 30))
            if opened > date_till:
                continue
            channel = _weighted(rng, _TICKET_CHANNELS)
            category = _weighted(rng, _TICKET_CATEGORIES)
            priority = _weighted(rng, _TICKET_PRIORITY)
            res_hours = _resolution_hours(rng, category, priority)
            closed = opened + timedelta(hours=res_hours)
            if closed > date_till:
                closed_iso = ""
                res_hours_out = ""
            else:
                closed_iso = closed.isoformat() if isinstance(closed, date) else str(closed)
                res_hours_out = res_hours
            # CSAT: skewed toward high; penalized for high priority + delivery/return
            csat_base = 4.4 if category in ("Setup help", "Account", "Other") else 3.9
            if priority in ("High", "Urgent"):
                csat_base -= 0.4
            csat = max(1, min(5, round(rng.gauss(csat_base, 0.7))))

            rows.append({
                "ticket_id": f"T-{ticket_id:08d}",
                "customer_id": int(h["customer_id"]),
                "invoice_id": h["invoice_id"],
                "channel": channel,
                "category": category,
                "priority": priority,
                "opened_at": opened.isoformat(),
                "closed_at": closed_iso,
                "resolution_hours": res_hours_out,
                "csat_score": csat,
            })
            ticket_id += 1

    return pd.DataFrame(rows, columns=[
        "ticket_id", "customer_id", "invoice_id", "channel", "category",
        "priority", "opened_at", "closed_at", "resolution_hours", "csat_score",
    ])


def build_nps_surveys_df(*, customers_df: pd.DataFrame,
                         headers_df: pd.DataFrame,
                         rng: random.Random,
                         date_from: date,
                         date_till: date,
                         response_rate: float = 0.30) -> pd.DataFrame:
    """Quarterly NPS survey to customers with at least 1 invoice in trailing 90 days."""
    rows: list[dict[str, Any]] = []

    customer_cohort = dict(zip(customers_df["customer_id"].astype(int),
                               customers_df["cohort"]))

    pos = headers_df[headers_df.is_return == 0].copy()
    pos["order_date_dt"] = pd.to_datetime(pos["order_date"]).dt.date

    # Build a per-customer sorted list of order dates (just need the set of recent dates)
    cust_dates: dict[int, list[date]] = {}
    for cid, sub in pos.groupby("customer_id"):
        cust_dates[int(cid)] = sorted(sub["order_date_dt"].tolist())

    # Quarterly survey dates
    survey_dates = pd.date_range(start=date_from, end=date_till, freq="QE").to_pydatetime()
    survey_id = 1

    for sd in survey_dates:
        sd = sd.date() if hasattr(sd, "date") else sd
        cutoff = sd - timedelta(days=90)
        # Sample a fraction of customers to send to
        for cid, dates in cust_dates.items():
            # active in trailing 90d?
            recent = any(cutoff <= d <= sd for d in dates)
            if not recent:
                continue
            # 1/4 of active customers actually receive the survey each quarter
            if rng.random() >= 0.25:
                continue
            sent_at = sd
            # Did they respond?
            cohort = customer_cohort.get(cid, "GROWING")
            mu, sigma = _COHORT_NPS.get(cohort, (7.0, 2.0))
            # Higher NPS cohorts respond more
            cohort_response_boost = max(0.0, (mu - 5.0) / 10.0)
            p_respond = min(0.95, response_rate + cohort_response_boost)
            if rng.random() < p_respond:
                response_at = (sent_at + timedelta(days=rng.randint(0, 14))).isoformat()
                score = max(0, min(10, int(round(rng.gauss(mu, sigma)))))
                if score >= 9:
                    nps_cat = "Promoter"
                elif score >= 7:
                    nps_cat = "Passive"
                else:
                    nps_cat = "Detractor"
            else:
                response_at = ""
                score = ""
                nps_cat = ""

            rows.append({
                "survey_id": f"S-{survey_id:08d}",
                "customer_id": cid,
                "sent_at": sent_at.isoformat(),
                "response_at": response_at,
                "score": score,
                "nps_category": nps_cat,
            })
            survey_id += 1

    return pd.DataFrame(rows, columns=[
        "survey_id", "customer_id", "sent_at", "response_at", "score", "nps_category",
    ])

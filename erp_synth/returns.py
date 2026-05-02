"""Return-invoice generator."""
from __future__ import annotations

import random
from datetime import date, timedelta
from typing import Any


def maybe_generate_return(*, header: dict[str, Any], lines: list[dict[str, Any]],
                          rng: random.Random, p_return: float,
                          end_date: date,
                          next_invoice_seq: int) -> tuple[dict[str, Any], list[dict[str, Any]]] | None:
    """Optionally produce a return invoice for `header`.

    Returns (return_header, return_lines) on success or None if no return is
    issued. Picks a uniform-random subset of the original lines (1..n), negates
    quantity and money fields, and dates it 1..30 days after the original
    (clipped to `end_date`).
    """
    if rng.random() >= float(p_return):
        return None
    if not lines:
        return None

    delay = rng.randint(1, 30)
    orig_dt = date.fromisoformat(header["order_date"])
    ret_dt = orig_dt + timedelta(days=delay)
    if ret_dt > end_date:
        return None

    n_pick = rng.randint(1, len(lines))
    picked = rng.sample(lines, k=n_pick)

    ret_lines: list[dict[str, Any]] = []
    subtotal = 0.0
    discount_total = 0.0
    for line in picked:
        new_line = dict(line)
        new_line["quantity"] = -int(line["quantity"])
        new_line["extended_amount"] = -float(line["extended_amount"])
        new_line["discount_amount"] = -float(line["discount_amount"])
        new_line["line_total"] = -float(line["line_total"])
        new_line["line_cost"] = -float(line["line_cost"])
        new_line["gross_margin"] = -float(line["gross_margin"])
        ret_lines.append(new_line)
        subtotal += new_line["extended_amount"]
        discount_total += new_line["discount_amount"]

    vat_rate = float(header["vat_rate"])
    taxable = subtotal - discount_total
    tax = round(taxable * vat_rate, 2)
    # Returns refund any freight that was paid; for simplicity refund the same flat amount
    freight = -float(header["freight"])
    grand_total = round(taxable + tax + freight, 2)

    customer_id = int(header["customer_id"])
    ymd = ret_dt.strftime("%Y%m%d")
    invoice_id = f"{customer_id}-{ymd}-R{next_invoice_seq:06d}"

    ret_header = {
        "invoice_id": invoice_id,
        "customer_id": customer_id,
        "store_id": int(header["store_id"]),
        "order_date": ret_dt.isoformat(),
        "due_date": ret_dt.isoformat(),
        "ship_date": ret_dt.isoformat(),
        "subtotal": round(subtotal, 2),
        "discount_total": round(discount_total, 2),
        "tax_amount": tax,
        "freight": freight,
        "grand_total": grand_total,
        "vat_rate": vat_rate,
        "currency": header["currency"],
        "payment_method": header["payment_method"],
        "promotion_id": header.get("promotion_id", ""),
        "is_return": 1,
        "reference_invoice_id": header["invoice_id"],
        "n_lines": len(ret_lines),
    }

    for rl in ret_lines:
        rl["invoice_id"] = invoice_id

    return ret_header, ret_lines

"""Verify a generated dataset on disk.

Usage:
    python scripts/verify.py [out_dir]

Loads the 6 CSVs from out_dir (default: output_csv) and runs:
  - schema checks (exact column lists)
  - column-level invariants (signs, ranges, FK integrity)
  - aggregate sanity (margin range, returns share, FK closure)

Exits non-zero on the first failure.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd


EXPECTED_COLUMNS = {
    "items.csv": [
        "product_id", "product_name", "brand", "category", "subcategory",
        "gramm_g", "list_price", "standard_cost", "currency",
        "listed_from_date", "compatible_device_brand", "is_active",
    ],
    "customers.csv": [
        "customer_id", "created_at", "first_name", "last_name", "email",
        "phone", "email_opt_in", "sms_opt_in", "call_opt_in",
        "gender", "birth_year", "marital_status", "occupation",
        "yearly_income", "num_children", "house_owner_flag", "education",
        "country", "region", "city", "postal_code",
        "cohort", "price_sensitivity", "brand_affinity", "market",
    ],
    "stores.csv": [
        "store_id", "store_name", "country", "region", "city",
        "opened_date", "store_type",
    ],
    "promotions.csv": [
        "promotion_id", "name", "discount_pct", "category_scope",
        "start_date", "end_date", "market",
    ],
    "invoice_headers.csv": [
        "invoice_id", "customer_id", "store_id", "order_date", "ship_date",
        "due_date", "subtotal", "discount_total", "tax_amount", "freight",
        "grand_total", "vat_rate", "currency", "payment_method",
        "promotion_id", "is_return", "reference_invoice_id", "n_lines",
    ],
    "sales_lines.csv": [
        "line_id", "invoice_id", "product_id", "quantity", "unit_price",
        "discount_pct", "discount_amount", "extended_amount", "line_total",
        "unit_standard_cost", "line_cost", "gross_margin",
    ],
}


class Fail(Exception):
    pass


def assert_schema(df: pd.DataFrame, fname: str) -> None:
    expected = EXPECTED_COLUMNS[fname]
    actual = df.columns.tolist()
    if actual != expected:
        raise Fail(f"{fname} columns mismatch.\n"
                   f"  expected: {expected}\n"
                   f"  actual:   {actual}")


def main(out_dir: str = "output_csv") -> int:
    base = Path(out_dir)
    if not base.exists():
        raise Fail(f"out_dir {base} does not exist")

    print(f"Verifying {base}/")

    items = pd.read_csv(base / "items.csv")
    customers = pd.read_csv(base / "customers.csv")
    stores = pd.read_csv(base / "stores.csv")
    promos = pd.read_csv(base / "promotions.csv")
    headers = pd.read_csv(base / "invoice_headers.csv", dtype={"reference_invoice_id": str, "promotion_id": str})
    lines = pd.read_csv(base / "sales_lines.csv")

    headers["reference_invoice_id"] = headers["reference_invoice_id"].fillna("")
    headers["promotion_id"] = headers["promotion_id"].fillna("")

    # --- schema ---
    assert_schema(items, "items.csv")
    assert_schema(customers, "customers.csv")
    assert_schema(stores, "stores.csv")
    assert_schema(promos, "promotions.csv")
    assert_schema(headers, "invoice_headers.csv")
    assert_schema(lines, "sales_lines.csv")
    print("  schema: OK")

    # --- column-level invariants ---
    if (items["list_price"] <= 0).any():
        raise Fail("items.list_price has non-positive values")
    if (items["standard_cost"] <= 0).any():
        raise Fail("items.standard_cost has non-positive values")
    if (items["standard_cost"] >= items["list_price"]).any():
        raise Fail("items.standard_cost >= list_price for some rows (no margin)")

    non_ret = lines.merge(headers[["invoice_id", "is_return"]], on="invoice_id", how="left")
    pos_lines = non_ret[non_ret["is_return"] == 0]
    neg_lines = non_ret[non_ret["is_return"] == 1]

    if (pos_lines["quantity"] <= 0).any():
        raise Fail("non-return lines have qty<=0")
    if (pos_lines["line_total"] <= 0).any():
        raise Fail("non-return lines have line_total<=0")
    if not neg_lines.empty:
        if (neg_lines["quantity"] >= 0).any():
            raise Fail("return lines have qty>=0")
        if (neg_lines["line_total"] >= 0).any():
            raise Fail("return lines have line_total>=0")

    if (lines["unit_price"] <= 0).any():
        raise Fail("lines.unit_price has non-positive values")
    if (lines["discount_pct"] < 0).any() or (lines["discount_pct"] > 1).any():
        raise Fail("lines.discount_pct out of [0,1]")

    margin_check = (lines["line_total"] - lines["line_cost"] - lines["gross_margin"]).abs()
    if (margin_check > 0.02).any():
        raise Fail("gross_margin != line_total - line_cost (tolerance 0.02)")
    print("  column invariants: OK")

    # --- FK integrity ---
    cust_ids = set(customers["customer_id"].astype(int).tolist())
    store_ids = set(stores["store_id"].astype(int).tolist())
    prod_ids = set(items["product_id"].astype(int).tolist())
    promo_ids = set(promos["promotion_id"].astype(str).tolist()) | {""}
    inv_ids = set(headers["invoice_id"].astype(str).tolist())

    bad = headers[~headers["customer_id"].astype(int).isin(cust_ids)]
    if not bad.empty:
        raise Fail(f"{len(bad)} headers reference unknown customer_id")
    bad = headers[~headers["store_id"].astype(int).isin(store_ids)]
    if not bad.empty:
        raise Fail(f"{len(bad)} headers reference unknown store_id")
    bad = headers[~headers["promotion_id"].astype(str).isin(promo_ids)]
    if not bad.empty:
        raise Fail(f"{len(bad)} headers reference unknown promotion_id")
    bad = headers[(headers["is_return"] == 1) & (~headers["reference_invoice_id"].isin(inv_ids))]
    if not bad.empty:
        raise Fail(f"{len(bad)} return headers have orphan reference_invoice_id")
    bad = lines[~lines["invoice_id"].astype(str).isin(inv_ids)]
    if not bad.empty:
        raise Fail(f"{len(bad)} sales_lines reference unknown invoice_id")
    bad = lines[~lines["product_id"].astype(int).isin(prod_ids)]
    if not bad.empty:
        raise Fail(f"{len(bad)} sales_lines reference unknown product_id")
    print("  FK integrity: OK")

    # --- header totals reconciliation ---
    tot = lines.groupby("invoice_id", as_index=False).agg(
        sum_extended=("extended_amount", "sum"),
        sum_discount=("discount_amount", "sum"),
        sum_line=("line_total", "sum"),
    )
    h2 = headers.merge(tot, on="invoice_id", how="left").fillna(0.0)
    diff_subtotal = (h2["subtotal"] - h2["sum_extended"]).abs()
    diff_discount = (h2["discount_total"] - h2["sum_discount"]).abs()
    expected_grand = h2["sum_line"] + h2["tax_amount"] + h2["freight"]
    diff_grand = (h2["grand_total"] - expected_grand).abs()
    if (diff_subtotal > 0.05).any():
        raise Fail(f"max subtotal mismatch: {diff_subtotal.max():.4f}")
    if (diff_discount > 0.05).any():
        raise Fail(f"max discount_total mismatch: {diff_discount.max():.4f}")
    if (diff_grand > 0.05).any():
        raise Fail(f"max grand_total mismatch: {diff_grand.max():.4f}")
    print("  totals reconciliation: OK")

    # --- aggregate sanity ---
    n_orders = (headers["is_return"] == 0).sum()
    n_returns = (headers["is_return"] == 1).sum()
    if n_orders > 0:
        share = n_returns / n_orders
        # Loose bounds — generation may be stochastic at small N
        if not (0.005 <= share <= 0.10):
            raise Fail(f"return share {share:.3%} outside [0.5%, 10%]")
        print(f"  return share: {share:.2%}")

    pos = lines.merge(headers[["invoice_id", "is_return"]], on="invoice_id")
    pos = pos[pos["is_return"] == 0]
    if not pos.empty:
        margin = pos["gross_margin"].sum() / pos["line_total"].sum()
        if not (0.10 <= margin <= 0.70):
            raise Fail(f"overall gross margin {margin:.2%} outside [10%, 70%]")
        print(f"  overall gross margin: {margin:.2%}")

    # cohort stickiness: each customer has exactly one cohort
    cohort_per_cust = customers.groupby("customer_id")["cohort"].nunique()
    if (cohort_per_cust != 1).any():
        raise Fail("some customers have multiple cohort labels")
    print("  cohort stickiness: OK")

    print("ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "output_csv"
    try:
        sys.exit(main(out))
    except Fail as e:
        print(f"VERIFICATION FAILED: {e}", file=sys.stderr)
        sys.exit(1)

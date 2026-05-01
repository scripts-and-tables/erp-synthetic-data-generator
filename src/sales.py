"""Day-by-day per-customer sales generation: invoice headers + line items.

Returns two synchronized lists per customer: invoice headers (one per invoice)
and sales lines (many per invoice). Applies seasonality, line-level promo
discounts, inflation-adjusted pricing, store/payment selection, and optional
return invoices.
"""
from __future__ import annotations

import random
from datetime import date, timedelta
from typing import Any

from .pricing import unit_price_at_sale
from .promotions import lookup_promo
from .returns import maybe_generate_return
from .seasonality import combined_multiplier


HARD_MAX_INVOICES_PER_DAY = 50


def _month_start(d: date) -> date:
    return date(d.year, d.month, 1)


def _year_index_from_start(day_dt: date, start_ms: date) -> int:
    months = (day_dt.year - start_ms.year) * 12 + (day_dt.month - start_ms.month)
    return months // 12


def _value_by_index(values, idx: int) -> float:
    if not values:
        raise ValueError("List parameter must not be empty.")
    if idx < 0:
        idx = 0
    if idx >= len(values):
        return float(values[-1])
    return float(values[idx])


def _pick_one(rng: random.Random, values):
    if not values:
        raise ValueError("List must not be empty.")
    return values[rng.randrange(len(values))]


def _weighted_pick(rng: random.Random, weights: list[tuple[Any, float]]):
    total = sum(w for _, w in weights)
    x = rng.random() * total
    acc = 0.0
    for v, w in weights:
        acc += w
        if x <= acc:
            return v
    return weights[-1][0]


def _sample_refill_count(rng: random.Random, probs: list[float]) -> int:
    if not probs:
        raise ValueError("refill_count_probs must not be empty.")
    total = float(sum(probs))
    if total <= 0:
        raise ValueError("refill_count_probs must contain positive values.")
    x = rng.random() * total
    acc = 0.0
    for i, p in enumerate(probs):
        acc += float(p)
        if x <= acc:
            return i + 1
    return len(probs)


def _sample_qty_for_category(rng: random.Random, category: str) -> int:
    if category == "DEVICE":
        return 1
    if category == "REFILL":
        return _weighted_pick(rng, [(1, 0.55), (2, 0.25), (3, 0.12), (4, 0.05), (6, 0.03)])
    if category == "ACCESSORY":
        return _weighted_pick(rng, [(1, 0.80), (2, 0.20)])
    return 1


def _filter_by_brand(items_index: dict[int, dict], product_ids: list[int],
                     brand_affinity: str) -> list[int]:
    """If brand_affinity is set and any compatible products exist, prefer those."""
    if not brand_affinity:
        return product_ids
    same_brand = [pid for pid in product_ids
                  if items_index[pid].get("compatible_device_brand") == brand_affinity]
    return same_brand or product_ids


def _build_line(*, line_id: int, invoice_id: str, product_id: int, qty: int,
                items_index: dict[int, dict], sale_date: date,
                annual_inflation: float, promo_lookup: dict,
                price_sensitivity: float, rng: random.Random) -> dict[str, Any]:
    item = items_index[product_id]
    list_price = float(item["list_price"])
    listed_from = item["_listed_from_date_obj"]
    promo_id, promo_pct = lookup_promo(promo_lookup, sale_date, item["category"])

    # Price-sensitive customers occasionally skip a non-promo line if too expensive,
    # but here we keep the line and just recognize the discount.
    unit_price, discount_pct = unit_price_at_sale(
        list_price=list_price,
        listed_from=listed_from,
        sale_date=sale_date,
        annual_inflation=annual_inflation,
        promo_pct=promo_pct,
    )

    extended_amount = round(qty * unit_price, 2)
    discount_amount = round(extended_amount * discount_pct, 2)
    line_total = round(extended_amount - discount_amount, 2)
    unit_standard_cost = float(item["standard_cost"])
    line_cost = round(qty * unit_standard_cost, 2)
    gross_margin = round(line_total - line_cost, 2)

    return {
        "line_id": line_id,
        "invoice_id": invoice_id,
        "product_id": int(product_id),
        "quantity": int(qty),
        "unit_price": unit_price,
        "discount_pct": round(float(discount_pct), 4),
        "discount_amount": discount_amount,
        "extended_amount": extended_amount,
        "line_total": line_total,
        "unit_standard_cost": unit_standard_cost,
        "line_cost": line_cost,
        "gross_margin": gross_margin,
        "_promotion_id": promo_id,  # internal, used to choose header promo
    }


def _close_invoice(*, invoice_id: str, customer_id: int, store_id: int,
                   day_dt: date, lines: list[dict[str, Any]],
                   vat_rate: float, currency: str,
                   freight_flat: float, freight_free_above: float,
                   payment_method: str, rng: random.Random) -> dict[str, Any]:
    subtotal = round(sum(l["extended_amount"] for l in lines), 2)
    discount_total = round(sum(l["discount_amount"] for l in lines), 2)
    taxable = round(subtotal - discount_total, 2)
    tax = round(taxable * float(vat_rate), 2)
    freight = 0.0 if taxable >= float(freight_free_above) else float(freight_flat)
    grand_total = round(taxable + tax + freight, 2)

    # Header promotion = most-used promo in the invoice (mode), or "" if none.
    promo_counts: dict[str, int] = {}
    for l in lines:
        pid = l.get("_promotion_id", "")
        if pid:
            promo_counts[pid] = promo_counts.get(pid, 0) + 1
    header_promo = max(promo_counts, key=promo_counts.get) if promo_counts else ""

    # Strip internal helper field from lines
    for l in lines:
        l.pop("_promotion_id", None)

    # Due / ship dates: ship 0-3d after order, due net-30 from ship.
    ship_offset = rng.randint(0, 3)
    ship_dt = day_dt + timedelta(days=ship_offset)
    due_dt = ship_dt + timedelta(days=30)

    return {
        "invoice_id": invoice_id,
        "customer_id": int(customer_id),
        "store_id": int(store_id),
        "order_date": day_dt.isoformat(),
        "ship_date": ship_dt.isoformat(),
        "due_date": due_dt.isoformat(),
        "subtotal": subtotal,
        "discount_total": discount_total,
        "tax_amount": tax,
        "freight": freight,
        "grand_total": grand_total,
        "vat_rate": float(vat_rate),
        "currency": currency,
        "payment_method": payment_method,
        "promotion_id": header_promo,
        "is_return": 0,
        "reference_invoice_id": "",
        "n_lines": len(lines),
    }


def generate_customer_sales(
    *,
    customer_id: int,
    sales_start_date: str,
    sales_end_date: str,
    items_index: dict[int, dict],
    device_product_ids: list[int],
    refill_product_ids: list[int],
    accessory_product_ids: list[int],
    spare_part_product_ids: list[int],
    store_ids: list[int],
    market_cfg: dict[str, Any],
    promo_lookup: dict,
    annual_inflation: float,
    p_return: float,
    enable_returns: bool,
    cohort_spec: dict[str, Any],
    rng: random.Random,
    line_id_start: int = 1,
    stop_invoices_on_lost_day: bool = True,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
    """Generate (headers, lines, next_line_id) for a single customer.

    cohort_spec carries: p_buy_by_year, p_close_day, p_invoice_by_nth,
    p_device_by_nth, refill_count_probs, p_refill_invoice,
    p_accessory_invoice, p_spare_part_invoice, brand_affinity, price_sensitivity.
    """
    start_dt = date.fromisoformat(sales_start_date)
    end_dt = date.fromisoformat(sales_end_date)
    if start_dt > end_dt:
        raise ValueError("sales_start_date must be <= sales_end_date.")
    if not store_ids:
        raise ValueError("store_ids must not be empty.")

    p_buy_by_year = cohort_spec["p_buy_by_year"]
    p_close_day = float(cohort_spec["p_close_day"])
    p_invoice_by_nth = cohort_spec["p_invoice_by_nth"]
    p_device_by_nth = cohort_spec["p_device_by_nth"]
    refill_count_probs = cohort_spec["refill_count_probs"]
    p_refill_invoice = float(cohort_spec.get("p_refill_invoice", 0.95))
    p_accessory_invoice = float(cohort_spec.get("p_accessory_invoice", 0.05))
    p_spare_part_invoice = float(cohort_spec.get("p_spare_part_invoice", 0.05))
    brand_affinity = str(cohort_spec.get("brand_affinity", "") or "")
    price_sensitivity = float(cohort_spec.get("price_sensitivity", 0.5))

    devices_owned = 0
    invoice_seq = 0
    line_id = int(line_id_start)
    headers: list[dict[str, Any]] = []
    all_lines: list[dict[str, Any]] = []

    start_ms = _month_start(start_dt)
    day_dt = start_dt

    payment_methods = market_cfg["payment_methods"]
    vat_rate = float(market_cfg["vat_rate"])
    currency = market_cfg["currency"]
    freight_flat = float(market_cfg["freight_flat"])
    freight_free_above = float(market_cfg["freight_free_above"])

    # Brand-filtered product pools (sticky, cheap)
    devices_pool = _filter_by_brand(items_index, device_product_ids, brand_affinity)
    refills_pool = _filter_by_brand(items_index, refill_product_ids, brand_affinity)
    accessories_pool = _filter_by_brand(items_index, accessory_product_ids, brand_affinity)
    spare_pool = _filter_by_brand(items_index, spare_part_product_ids, brand_affinity)

    while day_dt <= end_dt:
        if rng.random() < p_close_day:
            if not stop_invoices_on_lost_day:
                lost_today_but_allow_sales = True
            else:
                break
        else:
            lost_today_but_allow_sales = False

        y_idx = _year_index_from_start(day_dt, start_ms)
        p_buy_day_base = _value_by_index(p_buy_by_year, y_idx)
        season_mult = combined_multiplier(day_dt, market_cfg)
        # price-sensitive customers respond a bit less to baseline buying urge
        sens_dampen = 1.0 - (0.20 * price_sensitivity)
        p_buy_day = max(0.0, min(1.0, p_buy_day_base * season_mult * sens_dampen))

        invoices_today = 0
        while invoices_today < HARD_MAX_INVOICES_PER_DAY:
            p_inv_nth = _value_by_index(p_invoice_by_nth, invoices_today)
            if rng.random() >= p_buy_day * p_inv_nth:
                break

            invoices_today += 1
            invoice_seq += 1
            store_id = _pick_one(rng, store_ids)
            ymd = day_dt.strftime("%Y%m%d")
            invoice_id = f"{customer_id}-{ymd}-{invoice_seq:06d}"
            payment_method = _weighted_pick(rng, payment_methods)

            # Decide composition
            p_dev = _value_by_index(p_device_by_nth, devices_owned)
            include_device = (rng.random() < p_dev) and bool(devices_pool)

            refill_pids: list[int] = []
            if refills_pool and rng.random() < p_refill_invoice:
                n_refills = _sample_refill_count(rng, refill_count_probs)
                for _ in range(n_refills):
                    refill_pids.append(_pick_one(rng, refills_pool))

            accessory_pid = (_pick_one(rng, accessories_pool)
                             if accessories_pool and rng.random() < p_accessory_invoice
                             else None)
            spare_pid = (_pick_one(rng, spare_pool)
                         if spare_pool and rng.random() < p_spare_part_invoice
                         else None)

            # Ensure at least one line
            if not include_device and not refill_pids and accessory_pid is None and spare_pid is None:
                if refills_pool:
                    refill_pids = [_pick_one(rng, refills_pool)]
                elif devices_pool:
                    include_device = True
                elif accessories_pool:
                    accessory_pid = _pick_one(rng, accessories_pool)
                elif spare_pool:
                    spare_pid = _pick_one(rng, spare_pool)
                else:
                    invoice_seq -= 1
                    continue

            invoice_lines: list[dict[str, Any]] = []

            def add(pid: int) -> None:
                nonlocal line_id
                cat = items_index[pid]["category"]
                qty = _sample_qty_for_category(rng, cat)
                line = _build_line(
                    line_id=line_id, invoice_id=invoice_id, product_id=pid, qty=qty,
                    items_index=items_index, sale_date=day_dt,
                    annual_inflation=annual_inflation, promo_lookup=promo_lookup,
                    price_sensitivity=price_sensitivity, rng=rng,
                )
                invoice_lines.append(line)
                line_id += 1

            if include_device:
                add(_pick_one(rng, devices_pool))
                devices_owned += 1
            for pid in refill_pids:
                add(pid)
            if accessory_pid is not None:
                add(accessory_pid)
            if spare_pid is not None:
                add(spare_pid)

            header = _close_invoice(
                invoice_id=invoice_id, customer_id=customer_id, store_id=store_id,
                day_dt=day_dt, lines=invoice_lines,
                vat_rate=vat_rate, currency=currency,
                freight_flat=freight_flat, freight_free_above=freight_free_above,
                payment_method=payment_method, rng=rng,
            )
            headers.append(header)
            all_lines.extend(invoice_lines)

            # Optional return tied to this invoice
            if enable_returns:
                ret = maybe_generate_return(
                    header=header, lines=invoice_lines, rng=rng,
                    p_return=p_return, end_date=end_dt,
                    next_invoice_seq=invoice_seq,
                )
                if ret is not None:
                    ret_header, ret_lines = ret
                    # assign new line_ids to the return lines
                    for rl in ret_lines:
                        rl["line_id"] = line_id
                        line_id += 1
                    headers.append(ret_header)
                    all_lines.extend(ret_lines)

        if lost_today_but_allow_sales:
            break
        day_dt += timedelta(days=1)

    return headers, all_lines, line_id

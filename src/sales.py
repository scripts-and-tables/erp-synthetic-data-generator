from datetime import date, timedelta
import random

def _month_start(d):
    return date(d.year, d.month, 1)


def _year_index_from_start(day_dt, start_ms):
    day_ms = _month_start(day_dt)
    months = (day_ms.year - start_ms.year) * 12 + (day_ms.month - start_ms.month)
    return months // 12  # 0 => year1, 1 => year2, ...


def _value_by_index(values, idx):
    if not values:
        raise ValueError("List parameter must not be empty.")
    if idx < 0:
        idx = 0
    if idx >= len(values):
        return float(values[-1])
    return float(values[idx])


def _pick_one(rng, values):
    if not values:
        raise ValueError("List must not be empty.")
    return values[rng.randrange(len(values))]


def _sample_refill_count(rng, probs):
    # probs[0] => 1 refill, probs[1] => 2 refills, ...
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


def _parse_iso_date(s):
    if not isinstance(s, str):
        raise TypeError("Date must be ISO string 'YYYY-MM-DD'.")
    return date.fromisoformat(s)


def generate_customer_sales_rows(
    *,
    customer_id: int,
    sales_start_date: str,
    sales_end_date: str,
    device_product_ids: list[int],
    refill_product_ids: list[int],
    accessory_product_ids: list[int],
    spare_part_product_ids: list[int],
    store_ids: list[int],

    # Day-based probabilities now:
    p_buy_by_year: list[float],      # interpreted as DAILY probability schedule by customer-year
    p_close_day: float,              # DAILY probability of becoming lost (lost decision date)

    # Multi-invoice-per-day:
    p_invoice_by_nth: list[float],   # multipliers for invoice order within the day (1st, 2nd, 3rd...)

    # Basket composition:
    p_device_by_nth: list[float],
    refill_count_probs: list[float],
    p_refill_invoice: float = 1.0,
    p_accessory_invoice: float = 0.0,
    p_spare_part_invoice: float = 0.0,

    # Optional behavior: if True -> no invoices on the day customer becomes lost
    stop_invoices_on_lost_day: bool = True,
) -> list[dict]:
    """
    Day-by-day sales generation for ONE customer.

    Invoice occurrence (per your rule):
      invoice k on a day happens with probability:
        p_buy_day(year_index) * p_invoice_by_nth[k-1]

    Lost logic (fully day-based):
      each day, customer becomes lost with probability p_close_day.
      If lost triggers, that date is the "lost decision date" and generation stops.

    Notes:
      - p_buy_by_year is treated as DAILY probability schedule (not monthly).
        (If you want monthly meaning again, we can reintroduce a conversion, but you asked for "everything by days".)
      - revenue is 0.0 for now.
      - quantity is negative for return invoices.
    """
    start_dt = _parse_iso_date(sales_start_date)
    end_dt = _parse_iso_date(sales_end_date)

    rng = random.Random()

    if start_dt > end_dt:
        raise ValueError("sales_start_date must be <= sales_end_date.")
    if not store_ids:
        raise ValueError("store_ids must be provided and non-empty.")
    if not p_buy_by_year:
        raise ValueError("p_buy_by_year must not be empty.")
    if not p_invoice_by_nth:
        raise ValueError("p_invoice_by_nth must not be empty.")
    if not p_device_by_nth:
        raise ValueError("p_device_by_nth must not be empty.")
    if not refill_count_probs:
        raise ValueError("refill_count_probs must not be empty.")

    devices_owned = 0
    invoice_seq = 0
    rows = []

    start_ms = _month_start(start_dt)
    day_dt = start_dt

    HARD_MAX_INVOICES_PER_DAY = 50  # safety cap

    while day_dt <= end_dt:
        # 1) Lost check (lost decision date)
        if rng.random() < float(p_close_day):
            if not stop_invoices_on_lost_day:
                # Allow invoices on lost day, but stop after generating today's invoices.
                lost_today_but_allow_sales = True
            else:
                # Strict: lost means no invoices on/after this date.
                break
        else:
            lost_today_but_allow_sales = False

        # 2) Daily buy probability from "year schedule"
        y_idx = _year_index_from_start(day_dt, start_ms)
        p_buy_day = _value_by_index(p_buy_by_year, y_idx)

        # 3) Generate 0..N invoices on this day
        invoices_today = 0
        while invoices_today < HARD_MAX_INVOICES_PER_DAY:
            p_inv_nth = _value_by_index(p_invoice_by_nth, invoices_today)  # 0=>1st, 1=>2nd...
            p_invoice_attempt = float(p_buy_day) * float(p_inv_nth)

            if rng.random() >= p_invoice_attempt:
                break

            invoices_today += 1
            invoice_seq += 1

            store_id = _pick_one(rng, store_ids)
            ymd = f"{day_dt.year:04d}{day_dt.month:02d}{day_dt.day:02d}"
            invoice_id = f"{customer_id}-{ymd}-{invoice_seq:06d}"

            # Device line?
            p_dev = _value_by_index(p_device_by_nth, devices_owned)
            include_device = (rng.random() < p_dev) and bool(device_product_ids)

            # Refill lines?
            refill_lines = []
            if refill_product_ids and (rng.random() < float(p_refill_invoice)):
                n_refills = _sample_refill_count(rng, refill_count_probs)
                for _ in range(n_refills):
                    refill_lines.append(_pick_one(rng, refill_product_ids))

            # Add-ons
            accessory_line = None
            if accessory_product_ids and (rng.random() < float(p_accessory_invoice)):
                accessory_line = _pick_one(rng, accessory_product_ids)

            spare_line = None
            if spare_part_product_ids and (rng.random() < float(p_spare_part_invoice)):
                spare_line = _pick_one(rng, spare_part_product_ids)

            # Ensure at least one line
            if not include_device and not refill_lines and accessory_line is None and spare_line is None:
                if refill_product_ids:
                    refill_lines = [_pick_one(rng, refill_product_ids)]
                elif device_product_ids:
                    include_device = True
                elif accessory_product_ids:
                    accessory_line = _pick_one(rng, accessory_product_ids)
                elif spare_part_product_ids:
                    spare_line = _pick_one(rng, spare_part_product_ids)
                else:
                    continue

            def add_line(prod_id):
                rows.append({
                    "invoice_id": invoice_id,
                    "customer_id": customer_id,
                    "invoice_date": day_dt.isoformat(),  # 'YYYY-MM-DD'
                    "product_id": int(prod_id),
                    "quantity": 1,
                    "revenue": 0.0,
                    "store_id": int(store_id),
                })

            if include_device:
                add_line(_pick_one(rng, device_product_ids))
                devices_owned += 1

            for pid in refill_lines:
                add_line(pid)

            if accessory_line is not None:
                add_line(accessory_line)

            if spare_line is not None:
                add_line(spare_line)

        # If customer became lost today but we allowed invoices on lost day, stop after today
        if lost_today_but_allow_sales:
            break

        day_dt += timedelta(days=1)

    return rows

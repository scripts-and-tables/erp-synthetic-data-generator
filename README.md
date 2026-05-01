# ERP Synthetic Data Generator

A configurable Python script that generates **realistic synthetic business data** for demos, testing, and analytics prototypes — especially when real ERP/CRM datasets are unavailable (or unavailable for long historical periods).

The generator is built around an **air-freshener / diffuser ecosystem** but produces an AdventureWorks-style relational schema that is generic enough to plug into any retail/CRM analytics workflow.

---

## Highlights

* **Realistic pricing & margins** — every item has a `list_price` and a `standard_cost`; line items expose `discount_pct`, `discount_amount`, `unit_price`, `extended_amount`, `line_total`, `line_cost`, and `gross_margin`.
* **Seasonality** — month-of-year curves, day-of-week weighting, and holiday spikes (Black Friday, Cyber Monday, Christmas, Independence Day for US/EU; Ramadan, Eid al-Fitr, Eid al-Adha, UAE National Day for GCC).
* **Customer demographics & cohorts** — gender, birth year, marital status, occupation, yearly income (lognormal, country-aware), education, geography. Each customer is permanently assigned to one of 6 behavioral cohorts (LOYAL_HEAVY, LOYAL_LIGHT, GROWING, DECLINING, ONE_SHOT, CHURN_RISK).
* **Promotions** — automatic promotion master with market-specific events (Black Friday week, Boxing Week, Ramadan Specials, Eid Sale, plus generic seasonal sales). Discounts are applied at the line level; the most-used promo on an invoice is recorded on its header.
* **Returns** — ~3% of orders generate a linked return invoice 1–30 days later with negated quantities and money fields (`is_return=1`, `reference_invoice_id`).
* **Inflation** — `unit_price` at sale time = `list_price × (1 + annual_inflation)^years_since_listing`, so a 10-year run shows realistic price drift.
* **Multi-market** — `--market {us,gcc,eu}` flag swaps locale, currency (USD / AED / EUR), VAT rate, payment methods, weekend definition (Sat-Sun vs Fri-Sat), and holiday calendar.
* **Reproducibility** — single `--seed` flag drives all RNGs (numpy, python `random`, Faker, pandas `.sample`). Same seed → identical CSVs.
* **Streaming output** — invoice headers and lines are appended per customer; safe for runs with millions of rows.

---

## What you get

Six CSVs in `--out-dir` (default `output_csv/`):

| File | Type | Rows |
|---|---|---|
| `items.csv` | master | one per SKU |
| `customers.csv` | master | one per customer |
| `stores.csv` | master | one per physical/online store |
| `promotions.csv` | master | one per promotion campaign |
| `invoice_headers.csv` | fact | one per invoice (incl. returns) |
| `sales_lines.csv` | fact | one per line item |

### Schema

#### `items.csv`
`product_id` (PK), `product_name`, `brand`, `category` (`DEVICE`/`REFILL`/`ACCESSORY`/`SPARE_PART`), `subcategory` (e.g. `Home Diffuser`, `Refill Small/Bulk`, `Mount`, `Cable`), `gramm_g`, `list_price`, `standard_cost`, `currency`, `listed_from_date`, `compatible_device_brand`, `is_active`.

#### `customers.csv`
Core: `customer_id` (PK), `created_at`, `first_name`, `last_name`, `email`, `phone`, `email_opt_in`, `sms_opt_in`, `call_opt_in`.
Demographics: `gender`, `birth_year`, `marital_status`, `occupation`, `yearly_income`, `num_children`, `house_owner_flag`, `education`.
Geography: `country`, `region`, `city`, `postal_code`.
Behavioral: `cohort`, `price_sensitivity` (0..1), `brand_affinity`, `market`.

#### `stores.csv`
`store_id` (PK), `store_name`, `country`, `region`, `city`, `opened_date`, `store_type` (Flagship/Standard/Kiosk/Online).

#### `promotions.csv`
`promotion_id` (PK), `name`, `discount_pct`, `category_scope` (`ALL` or one category), `start_date`, `end_date`, `market`.

#### `invoice_headers.csv`
`invoice_id` (PK), `customer_id` (FK), `store_id` (FK), `order_date`, `ship_date`, `due_date`, `subtotal`, `discount_total`, `tax_amount`, `freight`, `grand_total`, `vat_rate`, `currency`, `payment_method`, `promotion_id` (FK), `is_return`, `reference_invoice_id`, `n_lines`.

#### `sales_lines.csv`
`line_id` (PK), `invoice_id` (FK), `product_id` (FK), `quantity`, `unit_price`, `discount_pct`, `discount_amount`, `extended_amount`, `line_total`, `unit_standard_cost`, `line_cost`, `gross_margin`.

#### Foreign-key graph
```
sales_lines.invoice_id    → invoice_headers.invoice_id
sales_lines.product_id    → items.product_id
invoice_headers.customer_id  → customers.customer_id
invoice_headers.store_id     → stores.store_id
invoice_headers.promotion_id → promotions.promotion_id
invoice_headers.reference_invoice_id → invoice_headers.invoice_id  (returns only)
```

---

## Customer behavior model

Each customer is deterministically assigned (by hashing `seed ^ customer_id`) to one of six cohorts:

| Cohort | Buy probability | Lost rate | Refill basket | Notes |
|---|---|---|---|---|
| **LOYAL_HEAVY** | 6→10% / day, growing | very low | up to 5 refills | premium-friendly, low price sensitivity |
| **LOYAL_LIGHT** | 3→5% / day | very low | 1–4 refills | moderate price sensitivity |
| **GROWING** | 2→8% / day | low | 1–4 refills | new customer ramping up |
| **DECLINING** | 6→1% / day | medium | smaller baskets | losing interest |
| **ONE_SHOT** | spike then ~0 | high | small basket | bought once and gone |
| **CHURN_RISK** | 4→0.5% / day | high | small basket | most price-sensitive |

Cohorts also influence accessory/spare-part attach rates and sticky brand affinity. Daily buy probability is multiplied by `seasonality(date) × (1 - 0.20·price_sensitivity)`.

---

## Dependencies

* Python 3.10+
* `pandas`
* `numpy`
* `Faker`

```bash
pip install pandas numpy Faker
```

---

## Quick start

```bash
# See CLI help
python run.py -h

# Tiny smoke
python run.py --seed 42 --market us --n-customers 50 \
              --date-from 2022-01-01 --date-till 2024-12-31 \
              --out-dir /tmp/synth-smoke
python scripts/verify.py /tmp/synth-smoke

# Full run (US, 10 years, 1k customers, default seed)
python run.py --seed 42 --market us --n-customers 1000 \
              --date-from 2015-01-01 --date-till 2025-12-31

# GCC market
python run.py --seed 42 --market gcc --n-customers 1000 \
              --date-from 2018-01-01 --date-till 2024-12-31
```

---

## CLI parameters

### Scale & dates
* `--n-customers INT` (default `1000`) — primary scale driver.
* `--date-from YYYY-MM-DD` (default `2015-01-01`) — start of customer creation timeline; also inflation anchor floor.
* `--date-till YYYY-MM-DD` (default `2025-12-31`) — end of generation timeline.

### Market & realism
* `--seed INT` (default `42`) — propagated to numpy + python random + Faker; identical seeds → identical output.
* `--market {us,gcc,eu}` (default `us`) — locale, currency, VAT, holidays, payment methods.
* `--vat-rate FLOAT` — override market default (US `0.0875`, GCC `0.05`, EU `0.20`).
* `--currency STR` — override market default.
* `--annual-inflation FLOAT` — override market default (US `0.03`, GCC/EU `0.025`).

### Items
* `--n-devices INT` (default `5`)
* `--n-accessories INT` (default `10`)
* `--n-spare-parts INT` (default `8`)
* `--n-refills INT` (default `74`) — regular refills
* `--n-bulk-refills INT` (default `1`)

### Customer field probabilities
* `--p-first-name FLOAT` (default `0.95`)
* `--p-last-name FLOAT` (default `0.85`)
* `--p-email FLOAT` (default `0.70`)
* `--p-phone FLOAT` (default `0.80`)
* `--p-email-opt-in FLOAT` (default `0.60`) — only applied if email exists
* `--p-sms-opt-in FLOAT` (default `0.90`) — only applied if phone exists
* `--p-call-opt-in FLOAT` (default `0.75`) — only applied if phone exists

### Stores & promotions
* `--n-stores INT` (default `8`)
* `--n-promotions-per-year INT` (default `6`)

### Returns
* `--p-return FLOAT` (default `0.03`) — probability that any given non-return invoice spawns a linked return
* `--enable-returns` / `--disable-returns` (default `enable`)

### Output
* `--out-dir PATH` (default `output_csv`)

---

## Verification

`scripts/verify.py` checks an output directory against expected schemas and invariants:

* exact column lists per file
* sign + range invariants on `quantity`, `unit_price`, `discount_pct`, `gross_margin`
* foreign-key integrity across all 6 files (no orphans)
* invoice header reconciliation (`subtotal`, `discount_total`, `grand_total` match line aggregates within ±0.05)
* return share in [0.5%, 10%]
* overall gross margin in [10%, 70%]
* cohort label is stable per customer

```bash
python scripts/verify.py /path/to/out_dir
```

Exits non-zero on the first failure with a descriptive message.

---

## Disclaimer

All data produced by this project is **synthetic** and randomly generated. It does not contain real customer or company information.

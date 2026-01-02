# ERP Synthetic Data Generator

A configurable Python package that generates realistic **synthetic business data** for demos, testing, and analytics prototypes — especially when real ERP/CRM datasets are unavailable (or unavailable for long historical periods).

---

## Dataset context (the story)

This project simulates sales data for a company operating in the **air freshener** category (diffuser ecosystem).

### Product universe

The product catalog is intentionally simple, but business-realistic, and is split into **four product groups**:

* **Devices** — diffuser machines
* **Refills** — consumables/liquids used with devices
* **Accessories** — mounts, holders, stickers, add-ons
* **Spare parts** — caps, seals, wicks, adapters, etc.

### Customer behavior

Customer activity is generated **customer-by-customer** and **day-by-day**. As a result, customers naturally diverge:

* some buy once and disappear
* some become loyal and purchase refills repeatedly
* some increase/decrease purchase frequency over time
* some become dormant for long periods and later return
* some are permanently lost ("lost decision date")
* active customers can occasionally generate multiple invoices in the same day
* some invoices are **returns** (modeled as negative quantities / reversal invoices)

---

## What makes this dataset different

Compared to typical public retail datasets, this generator is designed to be:

* **Large-scale**: hundreds of thousands of customers and multi-year histories
* **Long-horizon**: designed to support **10–15+ years** of transactions
* **ERP-style and relational**: clean masters + facts with foreign keys
* **Behavioral (not uniform random)**: each customer forms a distinct pattern over time
* **Reproducible**: seeded randomness allows consistent regeneration of the same dataset version
* **Returns-aware**: transactions can include return/reversal behavior (negative quantities), which is important for real-world ERP analytics

This makes the dataset suitable for building and testing:

* CRM/ERP analytics dashboards
* segmentation and retention analysis
* churn/dormancy logic
* customer lifecycle models
* data engineering pipelines (masters + facts + keys)

---

## What you get

The generator produces three core tables:

1. **Products** (master)
2. **Customers** (master)
3. **Sales Transactions** (fact, invoice line-level)

---

## Data model

### `products`

| Column       |    Type |  PK |  FK | Notes                                                      |
| ------------ | ------: | :-: | :-: | ---------------------------------------------------------- |
| product_id   | INTEGER |  ✅  |     | Internal product identifier (1..N)                         |
| product_name |    TEXT |     |     | Descriptive name                                           |
| brand        |    TEXT |     |     | Brand label                                                |
| category     |    TEXT |     |     | One of: `DEVICE`, `REFILL`, `ACCESSORY`, `SPARE_PART`      |
| gramm_g      | INTEGER |     |     | Grammage in grams (blank/NULL allowed for non-consumables) |

### `customers`

| Column       |    Type |  PK |  FK | Notes                                           |
| ------------ | ------: | :-: | :-: | ----------------------------------------------- |
| customer_id  | INTEGER |  ✅  |     | Internal customer identifier (1..N)             |
| created_at   |    TEXT |     |     | ISO date `YYYY-MM-DD`                           |
| first_name   |    TEXT |     |     | Optional (configurable missingness)             |
| last_name    |    TEXT |     |     | Optional (configurable missingness)             |
| email        |    TEXT |     |     | Optional (configurable missingness)             |
| phone        |    TEXT |     |     | Optional (configurable missingness)             |
| email_opt_in | INTEGER |     |     | 0/1 (probability depends on email availability) |
| sms_opt_in   | INTEGER |     |     | 0/1 (probability depends on phone availability) |
| call_opt_in  | INTEGER |     |     | 0/1 (probability depends on phone availability) |

### `sales_transactions`

| Column       |    Type |  PK |             FK            | Notes                                                              |
| ------------ | ------: | :-: | :-----------------------: | ------------------------------------------------------------------ |
| invoice_id   |    TEXT |     |                           | Business invoice identifier (not guaranteed unique across sources) |
| customer_id  | INTEGER |     | ✅ `customers.customer_id` | Customer reference                                                 |
| invoice_date |    TEXT |     |                           | ISO date `YYYY-MM-DD`                                              |
| product_id   | INTEGER |     |  ✅ `products.product_id`  | Product reference                                                  |
| quantity     | NUMERIC |     |                           | Sign convention can be used for returns                            |
| revenue      | NUMERIC |     |                           | Net revenue amount (pricing model may be added/extended)           |
| store_id     | INTEGER |     |                           | Store identifier                                                   |

---

## Quick start

### Install (recommended)

These two commands do different things:

* `pip install -r requirements.txt` installs the Python dependencies (e.g., pandas, Faker).
* `pip install -e .` installs this repo as an **editable package**, so you can run it as `python -m gen_synt_data` from the project root while still editing the code.

From the repo root:

```bash
python -m pip install -r requirements.txt
python -m pip install -e .
```

Then run:

```bash
python -m gen_synt_data
```

If you prefer not to install the package in editable mode yet, you can still run the module by ensuring `src/` is on your Python path (for example via your IDE run configuration).

### Import in Python

```python
from gen_synt_data.items import generate_items_df
from gen_synt_data.customers import generate_customers_df
from gen_synt_data.transactions import generate_customer_sales_rows
```

---

## CLI parameters

The goal is to support both small demo runs and large-scale generation by overriding settings from the command line, for example:

```bash
python -m gen_synt_data --customers 300000 --years 15 --seed 42 --out data/input
```

(If a flag is not available yet, it will be added as the generator matures. The default profiles are designed to be usable out of the box.)

---

## Kaggle dataset (planned)

A generated dataset will be published on Kaggle so you can download:

* master data (customers, products)
* sales transactions (multi-year)

Once published, this README will include a link and dataset version details.

---

## Disclaimer

All data produced by this project is **synthetic** and randomly generated. It does not contain real customer or company information.

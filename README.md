# ERP Synthetic Data Generator

A configurable Python script that generates realistic **synthetic business data** for demos, testing, and analytics prototypes — especially when real ERP/CRM datasets are unavailable (or unavailable for long historical periods).

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
* some are permanently lost (a simulated “lost decision date”)
* active customers can occasionally generate multiple invoices in the same day

---

## What makes this dataset different

Compared to typical public retail datasets, this generator is designed to be:

* **Large-scale**: hundreds of thousands of customers and multi-year histories
* **Long-horizon**: designed to support **10–15+ years** of transactions
* **ERP-style and relational**: clean masters + facts with foreign keys
* **Behavioral (not uniform random)**: each customer forms a distinct pattern over time

This makes the dataset suitable for building and testing:

* CRM/ERP analytics dashboards
* segmentation and retention analysis
* churn/dormancy logic
* customer lifecycle models
* data engineering pipelines (masters + facts + keys)

---

## What you get

The generator produces three core tables (CSV):

1. **Products** (master)
2. **Customers** (master)
3. **Sales Transactions** (fact, invoice line-level)

---

## Data model

### `products`

| Column       | Type    | PK | FK | Notes                                                 |
| ------------ | ------- | -- | -- | ----------------------------------------------------- |
| product_id   | INTEGER | ✅  |    | Internal product identifier (1..N)                    |
| product_name | TEXT    |    |    | Descriptive name                                      |
| brand        | TEXT    |    |    | Brand label                                           |
| category     | TEXT    |    |    | One of: `DEVICE`, `REFILL`, `ACCESSORY`, `SPARE_PART` |
| gramm_g      | INTEGER |    |    | Grammage in grams (NULL allowed for non-consumables)  |

### `customers`

| Column       | Type    | PK | FK | Notes                                           |
| ------------ | ------- | -- | -- | ----------------------------------------------- |
| customer_id  | INTEGER | ✅  |    | Internal customer identifier (1..N)             |
| created_at   | TEXT    |    |    | ISO date `YYYY-MM-DD`                           |
| first_name   | TEXT    |    |    | Optional (configurable missingness)             |
| last_name    | TEXT    |    |    | Optional (configurable missingness)             |
| email        | TEXT    |    |    | Optional (configurable missingness)             |
| phone        | TEXT    |    |    | Optional (configurable missingness)             |
| email_opt_in | INTEGER |    |    | 0/1 (probability depends on email availability) |
| sms_opt_in   | INTEGER |    |    | 0/1 (probability depends on phone availability) |
| call_opt_in  | INTEGER |    |    | 0/1 (probability depends on phone availability) |

### `sales_transactions`

| Column       | Type    | PK | FK                        | Notes                                                       |
| ------------ | ------- | -- | ------------------------- | ----------------------------------------------------------- |
| invoice_id   | TEXT    |    |                           | Business invoice identifier                                 |
| customer_id  | INTEGER |    | ✅ `customers.customer_id` | Customer reference                                          |
| invoice_date | TEXT    |    |                           | ISO date `YYYY-MM-DD`                                       |
| product_id   | INTEGER |    | ✅ `products.product_id`   | Product reference                                           |
| quantity     | NUMERIC |    |                           | Quantity purchased                                          |
| revenue      | NUMERIC |    |                           | Net revenue amount (simple pricing model; extend as needed) |
| store_id     | INTEGER |    |                           | Store identifier                                            |

---

## Dependencies

This project is plain Python. Install what you need in your environment:

* `pandas`
* `Faker`

---

## Quick start

### 1) See CLI help

From the repo root:

```bash
python run.py -h
```

### 2) Generate data

Example:

```bash
python run.py --n-customers 1000 --date-from 2015-01-01 --date-till 2025-12-31
```

Outputs (CSV):

* `products.csv`
* `customers.csv`
* `sales_transactions.csv`

---

## CLI parameters

All generation is controlled via CLI flags on `run.py`.

### Core scale controls

* `--n-customers` *(int, default: 1000)*

  * Number of customers to generate.
  * Primary driver of dataset size.

* `--date-from` *(YYYY-MM-DD, default: 2015-01-01)*

  * Start of the customer creation timeline.
  * Customers will have `created_at` dates distributed across this range.

* `--date-till` *(YYYY-MM-DD, default: 2025-12-31)*

  * End of the generation timeline.
  * Transactions will be generated within the overall range according to customer creation dates and behavior.

More parameters are available on (use -h for help) and even more parameters are available on each function.

### Practical guidance for large runs

* **Start small** (e.g., `--n-customers 1000`) to validate the workflow.
* Then scale gradually (10k → 100k → 300k) and monitor runtime and disk size.
* For very large runs (millions of invoices), expect files that do not open in Excel (row limit) — use databases or parquet.


---

## Kaggle dataset (planned)

A generated dataset may be published on Kaggle later so you can download:

* master data (customers, products)
* sales transactions (multi-year)

Once published, this README will include the link.

---

## Disclaimer

All data produced by this project is **synthetic** and randomly generated. It does not contain real customer or company information.

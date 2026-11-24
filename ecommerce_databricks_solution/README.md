# E-commerce Sales Data Processing on Databricks

PySpark pipeline that loads orders, products and customers, cleans them, builds an enriched
order-level table and a profit aggregate, and reports profit views in SQL. Business logic lives
in a tested Python package; the notebooks only orchestrate.

## Layout

```
src/ecom_pipeline/
  schemas.py          explicit source schemas
  io.py               readers (JSON / CSV / Excel) and Delta writer
  transformations.py  pure PySpark transformations and data quality checks
notebooks/
  00_config.py           schema, paths and table names (widgets)
  01_raw_tables.py       Task 1: raw tables
  02_enriched_tables.py  Tasks 2 and 3: enriched customers, products and orders
  03_aggregate_table.py  Task 4: profit aggregate, with reconciliation
  04_sql_aggregates.sql  Task 5: SQL outputs
  05_run_tests.py        runs the pytest suite on the cluster
tests/
  conftest.py, test_transformations.py   19 unit tests
```

## How to run

1. Import the folder into Databricks as a Git folder (Repo), or upload it to the workspace.
2. Upload `Orders.json`, `Products.csv` and `Customer.xlsx` to a Unity Catalog volume,
   for example `/Volumes/main/ecom/raw_files`.
3. Set the widgets in `00_config` (`schema`, `source_path`).
4. Run notebooks `01` → `02` → `03` → `04`. Run `05` at any time to execute the tests.
5. To run the tests locally: `pip install pyspark pytest openpyxl pandas` then `pytest tests`.

## Tables

| Table | Grain | Notes |
|---|---|---|
| `raw_orders`, `raw_products`, `raw_customers` | As in source | snake_case columns plus `_source_file` and `_ingested_at` |
| `enriched_customers` | 1 row per customer_id | cleaned customer_name; null name or country set to `Unknown` |
| `enriched_products` | 1 row per product_id | deduplicated |
| `enriched_orders` | 1 row per order line (row_id) | profit rounded to 2 dp; customer name and country; category and sub-category; order_year |
| `agg_profit` | year × category × sub-category × customer | total_profit (2 dp), order_count |

## Data quality findings and how they're handled

| Issue found in the source | Handling |
|---|---|
| 60 customer names contain digits or symbols (`Gary567 Hansen`, `Pete@#$ Takahito`) or extra spaces | Keep letters, spaces, apostrophes and hyphens; collapse spaces; trim |
| 8 customers have a null name | Set to `Unknown` |
| 33 duplicated Product IDs (same category, different name or state) | Keep one row per id, so the order join cannot duplicate order lines and inflate profit |
| 204 orders reference products missing from Products.csv | Kept via LEFT join, with category and sub-category set to `Unknown`; counted in the DQ report |
| Dates stored as `d/M/yyyy` text | Parsed to DATE; unparseable dates fail the run |
| Column names contain spaces and hyphens | Converted to snake_case (Delta-compatible) |

Error handling:
- Explicit schemas with `FAILFAST` reads, so a changed source file stops the load.
- A data-quality report runs before enrichment; null order IDs or unparseable dates raise an error.
- A grain check (enriched row count = raw row count) and a reconciliation check (aggregate total = detail total) fail the notebook if broken.
- Overwrite writes keep reruns idempotent.

## Assumptions

- Profit is taken from the source `Profit` field, rounded to 2 decimal places at order-line level; aggregates sum the rounded values and round again.
- Year means the year of `Order Date`.
- Junk characters in names are data-entry noise and are removed (digits are not mapped back to letters, so `N0ra` becomes `Nra`).
- Orders with unknown products are kept so total profit stays complete; they appear under `Unknown` category.
- All customers are in the United States in this extract; the country column is still carried through as required.

## Performance notes

- The reference tables (about 800 customers and 1,800 products) are broadcast in joins, so there's no shuffle on the large side.
- The aggregate is built once at the finest grain; the SQL views roll it up instead of re-scanning orders.
- With larger volumes, `enriched_orders` could be partitioned by `order_year` and the raw load made incremental (Auto Loader + MERGE).

## Results on the provided data (local run)

- Orders: 9,994 raw → 9,994 enriched (no rows lost or duplicated)
- Total profit: 278,417.03 (detail and aggregate reconcile)
- Profit by year: 2014 39,185.75 · 2015 63,073.09 · 2016 65,073.23 · 2017 111,084.96

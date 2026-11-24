# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "6"
# dependencies = [
#   "openpyxl",
# ]
# ///
# MAGIC %md
# MAGIC # 01 · Raw tables (Task 1)
# MAGIC Load each source file as-is into a raw Delta table. Column names become snake_case and
# MAGIC audit columns (`_source_file`, `_ingested_at`) are added. No business logic is applied here.

# COMMAND ----------

# MAGIC %pip install openpyxl

# COMMAND ----------

# MAGIC %run ./00_config

# COMMAND ----------

import logging
from ecom_pipeline.io import read_customers, read_orders, read_products, write_table

log = logging.getLogger("raw")

sources = {
    T_RAW_ORDERS: lambda: read_orders(spark, ORDERS_PATH),
    T_RAW_PRODUCTS: lambda: read_products(spark, PRODUCTS_PATH),
    # pandas needs a local-style path: /Volumes/... works as-is; for DBFS use /dbfs/...
    T_RAW_CUSTOMERS: lambda: read_customers(spark, CUSTOMERS_PATH),
}

for table, reader in sources.items():
    try:
        df = reader()
        write_table(df, table)
        print(f"{table}: {spark.table(table).count()} rows")
    except Exception as e:
        log.error("Failed to load %s: %s", table, e)
        raise   # fail the job; don't let downstream run on partial data

# COMMAND ----------

display(spark.table(T_RAW_ORDERS).limit(5))
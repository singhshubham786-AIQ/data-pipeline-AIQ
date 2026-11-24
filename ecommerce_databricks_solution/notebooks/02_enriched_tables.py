# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "6"
# ///
# MAGIC %md
# MAGIC # 02 · Enriched tables (Tasks 2 and 3)
# MAGIC - **enriched_customers:** cleaned names (junk characters removed), one row per customer
# MAGIC - **enriched_products:** one row per product_id (the source has 33 duplicate ids)
# MAGIC - **enriched_orders:** order details, profit rounded to 2 dp, customer name and country,
# MAGIC   product category and sub-category

# COMMAND ----------

# MAGIC %run ./00_config

# COMMAND ----------

from ecom_pipeline.io import write_table
from ecom_pipeline.transformations import (
    assert_no_critical_issues, data_quality_report, enrich_customers,
    enrich_orders, enrich_products,
)

raw_orders = spark.table(T_RAW_ORDERS)
customers = enrich_customers(spark.table(T_RAW_CUSTOMERS))
products = enrich_products(spark.table(T_RAW_PRODUCTS))

# Data quality gate: log everything, fail only on critical issues
report = data_quality_report(raw_orders, customers, products)
print(report)
assert_no_critical_issues(report)

# COMMAND ----------

write_table(customers, T_ENR_CUSTOMERS)
write_table(products, T_ENR_PRODUCTS)

orders = enrich_orders(raw_orders, spark.table(T_ENR_CUSTOMERS), spark.table(T_ENR_PRODUCTS))
write_table(orders, T_ENR_ORDERS)

# Grain check: enrichment must not add or drop order lines
assert spark.table(T_ENR_ORDERS).count() == raw_orders.count(), "Order row count changed during enrichment"

# COMMAND ----------

display(spark.table(T_ENR_ORDERS).limit(10))
# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "6"
# ///
# MAGIC %md
# MAGIC # 03 · Aggregate table (Task 4)
# MAGIC Profit by **year, product category, product sub-category and customer**. This is the finest
# MAGIC grain; the SQL notebook rolls it up to coarser views.

# COMMAND ----------

# MAGIC %run ./00_config

# COMMAND ----------

from ecom_pipeline.io import write_table
from ecom_pipeline.transformations import aggregate_profit

agg = aggregate_profit(spark.table(T_ENR_ORDERS))
write_table(agg, T_AGG_PROFIT)

# Reconciliation: aggregate total must equal detail total
detail = spark.table(T_ENR_ORDERS).groupBy().sum("profit").first()[0]
total = spark.table(T_AGG_PROFIT).groupBy().sum("total_profit").first()[0]
assert round(detail, 2) == round(total, 2), f"Reconciliation failed: {detail} vs {total}"
print(f"Reconciled total profit: {round(total, 2)}")

# COMMAND ----------

display(spark.table(T_AGG_PROFIT).orderBy("order_year", "category", "sub_category").limit(20))
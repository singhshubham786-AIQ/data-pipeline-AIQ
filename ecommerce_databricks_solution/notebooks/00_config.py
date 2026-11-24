# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "6"
# ///
# MAGIC %md
# MAGIC # 00 · Configuration
# MAGIC Shared settings. Other notebooks load this with `%run ./00_config`.
# MAGIC
# MAGIC Upload the three source files to a Unity Catalog volume (or DBFS) and set `source_path` below.

# COMMAND ----------

dbutils.widgets.text("schema", "ecom", "Target schema")

dbutils.widgets.text(
    "source_path",
    "/Volumes/workspace/ecom/raw_files",
    "Source files folder"
)

SCHEMA = dbutils.widgets.get("schema")
SOURCE_PATH = dbutils.widgets.get("source_path").rstrip("/")

ORDERS_PATH = f"{SOURCE_PATH}/Orders.json"
PRODUCTS_PATH = f"{SOURCE_PATH}/Products.csv"
CUSTOMERS_PATH = f"{SOURCE_PATH}/Customer.xlsx"

T_RAW_ORDERS = f"{SCHEMA}.raw_orders"
T_RAW_PRODUCTS = f"{SCHEMA}.raw_products"
T_RAW_CUSTOMERS = f"{SCHEMA}.raw_customers"
T_ENR_CUSTOMERS = f"{SCHEMA}.enriched_customers"
T_ENR_PRODUCTS = f"{SCHEMA}.enriched_products"
T_ENR_ORDERS = f"{SCHEMA}.enriched_orders"
T_AGG_PROFIT = f"{SCHEMA}.agg_profit"

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")

# Make the src/ package importable (repo root -> src)
import os, sys
repo_root = os.path.abspath(os.path.join(os.getcwd(), ".."))
sys.path.insert(0, os.path.join(repo_root, "src"))

# COMMAND ----------

dbutils.widgets.removeAll()

# COMMAND ----------

spark.sql("""
    SELECT
        current_catalog() AS catalog_name,
        current_schema() AS schema_name
""").show(truncate=False)

# COMMAND ----------

spark.sql("SHOW CATALOGS").show(truncate=False)

# COMMAND ----------

spark.sql("SHOW SCHEMAS IN workspace").show(truncate=False)

# COMMAND ----------

spark.sql("""
    CREATE VOLUME IF NOT EXISTS workspace.ecom.raw_files
""")

# COMMAND ----------

spark.sql("""
    DESCRIBE VOLUME workspace.ecom.raw_files
""").show(truncate=False)

# COMMAND ----------



# COMMAND ----------

display(
    dbutils.fs.ls("/Volumes/workspace/ecom/raw_files")
)

# COMMAND ----------

dbutils.widgets.remove("source_path")

# COMMAND ----------

print("Catalog:", spark.sql("SELECT current_catalog()").first()[0])
print("Schema:", SCHEMA)
print("Source path:", SOURCE_PATH)

print("Orders:", ORDERS_PATH)
print("Products:", PRODUCTS_PATH)
print("Customers:", CUSTOMERS_PATH)

# COMMAND ----------

print("Schema:", SCHEMA)
print("Source path:", SOURCE_PATH)
print("Orders:", ORDERS_PATH)
"""Pure PySpark transformations.

Every function takes DataFrames and returns a DataFrame with no I/O, so each
one can be unit-tested with small in-memory DataFrames.
"""
import re
from functools import reduce

from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql.window import Window

UNKNOWN = "Unknown"


# --------------------------------------------------------------------------- #
# Generic helpers
# --------------------------------------------------------------------------- #
def to_snake_case(name: str) -> str:
    """'Sub-Category' -> 'sub_category', 'Order ID' -> 'order_id'."""
    name = re.sub(r"[^0-9a-zA-Z]+", "_", name.strip())
    return name.strip("_").lower()


def standardize_columns(df: DataFrame) -> DataFrame:
    """Rename every column to snake_case.

    Delta tables reject spaces in column names unless column mapping is on, and
    snake_case keeps downstream SQL simple.
    """
    return reduce(lambda acc, c: acc.withColumnRenamed(c, to_snake_case(c)),
                  df.columns, df)


def add_ingestion_metadata(df: DataFrame, source_file: str) -> DataFrame:
    """Audit columns for lineage on raw tables."""
    return (df.withColumn("_source_file", F.lit(source_file))
              .withColumn("_ingested_at", F.current_timestamp()))


# --------------------------------------------------------------------------- #
# Customers
# --------------------------------------------------------------------------- #
def clean_customer_name(col):
    """Keep letters, spaces, apostrophes and hyphens; collapse spaces; trim.

    'Gary567 Hansen' -> 'Gary Hansen', '   _Mike Vitt 12313orini' -> 'Mike Vitt orini'
    Empty or null results become 'Unknown'.
    """
    cleaned = F.regexp_replace(col, r"[^A-Za-z '\-]", "")
    cleaned = F.trim(F.regexp_replace(cleaned, r"\s+", " "))
    return F.when(cleaned.isNull() | (cleaned == ""), F.lit(UNKNOWN)).otherwise(cleaned)


def enrich_customers(raw_customers: DataFrame) -> DataFrame:
    """One clean row per customer_id."""
    w = Window.partitionBy("customer_id").orderBy(F.col("customer_name").asc_nulls_last())
    return (raw_customers
            .filter(F.col("customer_id").isNotNull())
            .withColumn("customer_id", F.trim("customer_id"))
            .withColumn("customer_name", clean_customer_name(F.col("customer_name")))
            .withColumn("country", F.coalesce(F.trim("country"), F.lit(UNKNOWN)))
            .withColumn("_rn", F.row_number().over(w))
            .filter("_rn = 1")
            .select("customer_id", "customer_name", "email", "phone", "segment",
                    "country", "city", "state",
                    F.col("postal_code").cast("string").alias("postal_code"), "region"))


# --------------------------------------------------------------------------- #
# Products
# --------------------------------------------------------------------------- #
def enrich_products(raw_products: DataFrame) -> DataFrame:
    """One row per product_id.

    The source repeats some product_ids (different name/state rows). Category
    and sub-category are consistent per id, so we keep one row per id. Without
    this, joining orders to products would duplicate order rows and inflate profit.
    """
    w = Window.partitionBy("product_id").orderBy("product_name", "state")
    return (raw_products
            .filter(F.col("product_id").isNotNull())
            .withColumn("product_id", F.trim("product_id"))
            .withColumn("category", F.coalesce(F.trim("category"), F.lit(UNKNOWN)))
            .withColumn("sub_category", F.coalesce(F.trim("sub_category"), F.lit(UNKNOWN)))
            .withColumn("_rn", F.row_number().over(w))
            .filter("_rn = 1")
            .select("product_id", "category", "sub_category", "product_name"))


# --------------------------------------------------------------------------- #
# Orders
# --------------------------------------------------------------------------- #

def parse_order_dates(raw_orders: DataFrame) -> DataFrame:
    """Convert d/M/yyyy strings to DateType. Invalid dates become null."""
    return (
        raw_orders
        .withColumn(
            "order_date",
            F.to_date(F.try_to_timestamp("order_date", F.lit("d/M/yyyy")))
        )
        .withColumn(
            "ship_date",
            F.to_date(F.try_to_timestamp("ship_date", F.lit("d/M/yyyy")))
        )
    )



def enrich_orders(raw_orders: DataFrame,
                  customers: DataFrame,
                  products: DataFrame) -> DataFrame:
    """Order-level table with customer and product attributes.

    - Profit is rounded to 2 decimal places.
    - LEFT joins keep every order. Orders whose product/customer is missing from
      the reference data get 'Unknown' instead of being silently dropped.
    - Grain stays one row per order line (row_id); reference tables are unique
      per key, so the joins cannot fan out.
    """
    orders = parse_order_dates(raw_orders).withColumn(
        "order_year", F.year("order_date"))

    return (orders.alias("o")
            .join(F.broadcast(customers.select("customer_id", "customer_name", "country")),
                  "customer_id", "left")
            .join(F.broadcast(products.select("product_id", "category", "sub_category")),
                  "product_id", "left")
            .select(
                "row_id", "order_id", "order_date", "order_year", "ship_date",
                "ship_mode", "customer_id",
                F.coalesce("customer_name", F.lit(UNKNOWN)).alias("customer_name"),
                F.coalesce("country", F.lit(UNKNOWN)).alias("country"),
                "product_id",
                F.coalesce("category", F.lit(UNKNOWN)).alias("category"),
                F.coalesce("sub_category", F.lit(UNKNOWN)).alias("sub_category"),
                "quantity", "price", "discount",
                F.round("profit", 2).alias("profit"),
            ))


# --------------------------------------------------------------------------- #
# Aggregates
# --------------------------------------------------------------------------- #
def aggregate_profit(enriched_orders: DataFrame) -> DataFrame:
    """Profit by year, category, sub-category and customer (finest grain).

    Coarser views (by year, by customer, ...) are rolled up from this table in SQL.
    """
    return (enriched_orders
            .groupBy("order_year", "category", "sub_category",
                     "customer_id", "customer_name")
            .agg(F.round(F.sum("profit"), 2).alias("total_profit"),
                 F.countDistinct("order_id").alias("order_count")))


# --------------------------------------------------------------------------- #
# Data quality
# --------------------------------------------------------------------------- #
def data_quality_report(raw_orders: DataFrame, customers: DataFrame,
                        products: DataFrame) -> dict:
    """Counts used for logging and for failing the run on critical issues."""
    return {
        "orders_total": raw_orders.count(),
        "orders_null_order_id": raw_orders.filter(F.col("order_id").isNull()).count(),
        "orders_unparseable_date": parse_order_dates(raw_orders)
            .filter(F.col("order_date").isNull()).count(),
        "orders_unknown_customer": raw_orders.join(customers, "customer_id", "left_anti").count(),
        "orders_unknown_product": raw_orders.join(products, "product_id", "left_anti").count(),
    }


def assert_no_critical_issues(report: dict) -> None:
    """Fail fast on issues that make the output wrong, not just incomplete."""
    critical = {k: report[k] for k in ("orders_null_order_id", "orders_unparseable_date")
                if report[k] > 0}
    if critical:
        raise ValueError(f"Critical data quality issues: {critical}")

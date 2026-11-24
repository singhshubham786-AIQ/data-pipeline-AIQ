"""Readers and writers. All I/O is kept here so transformations stay testable."""
import logging

import pandas as pd
from pyspark.sql import DataFrame, SparkSession

from .schemas import CUSTOMER_COLUMNS, ORDERS_SCHEMA, PRODUCTS_SCHEMA
from .transformations import add_ingestion_metadata, standardize_columns

log = logging.getLogger(__name__)


def read_orders(spark: SparkSession, path: str) -> DataFrame:
    """Orders.json is a single JSON array, so multiLine is required."""
    df = (spark.read.schema(ORDERS_SCHEMA)
          .option("multiLine", True)
          .option("mode", "FAILFAST")
          .json(path))
    return add_ingestion_metadata(standardize_columns(df), path)


def read_products(spark: SparkSession, path: str) -> DataFrame:
    """Product names contain commas, so quoting/escaping must be honoured."""
    df = (spark.read.schema(PRODUCTS_SCHEMA)
          .option("header", True)
          .option("quote", '"')
          .option("escape", '"')
          .option("mode", "FAILFAST")
          .csv(path))
    return add_ingestion_metadata(standardize_columns(df), path)


def read_customers(spark: SparkSession, path: str) -> DataFrame:
    """Excel via pandas + openpyxl (Spark has no built-in Excel reader).

    All columns are read as strings: 'phone' mixes numbers and text, and
    reading everything as text avoids type-inference surprises.
    On Databricks, read from a /Volumes/... or /dbfs/... local path.
    """
    pdf = pd.read_excel(path, dtype=str, engine="openpyxl")
    missing = set(CUSTOMER_COLUMNS) - set(pdf.columns)
    if missing:
        raise ValueError(f"Customer file is missing columns: {sorted(missing)}")
    pdf = pdf.where(pd.notnull(pdf), None)
    df = spark.createDataFrame(pdf[CUSTOMER_COLUMNS])
    return add_ingestion_metadata(standardize_columns(df), path)


def write_table(df: DataFrame, table_name: str, fmt: str = "delta") -> None:
    """Full-refresh write. Overwrite keeps reruns idempotent."""
    log.info("Writing %s", table_name)
    (df.write.format(fmt).mode("overwrite")
       .option("overwriteSchema", "true")
       .saveAsTable(table_name))

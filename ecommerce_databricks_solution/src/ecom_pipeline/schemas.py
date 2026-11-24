"""Explicit schemas for the source files.

Explicit schemas (instead of inferSchema) make reads deterministic, faster on
large files, and fail fast when a source changes shape.
"""
from pyspark.sql.types import (
    DoubleType, IntegerType, LongType, StringType, StructField, StructType,
)

ORDERS_SCHEMA = StructType([
    StructField("Row ID", LongType(), False),
    StructField("Order ID", StringType(), False),
    StructField("Order Date", StringType(), True),   # d/M/yyyy text in source
    StructField("Ship Date", StringType(), True),
    StructField("Ship Mode", StringType(), True),
    StructField("Customer ID", StringType(), True),
    StructField("Product ID", StringType(), True),
    StructField("Quantity", IntegerType(), True),
    StructField("Price", DoubleType(), True),
    StructField("Discount", DoubleType(), True),
    StructField("Profit", DoubleType(), True),
])

PRODUCTS_SCHEMA = StructType([
    StructField("Product ID", StringType(), False),
    StructField("Category", StringType(), True),
    StructField("Sub-Category", StringType(), True),
    StructField("Product Name", StringType(), True),
    StructField("State", StringType(), True),
    StructField("Price per product", DoubleType(), True),
])

# Customer.xlsx is read with pandas (Spark has no native Excel reader), every
# column as string, then cast where needed.
CUSTOMER_COLUMNS = [
    "Customer ID", "Customer Name", "email", "phone", "address", "Segment",
    "Country", "City", "State", "Postal Code", "Region",
]

import sys

import pytest
from pyspark.sql import SparkSession

sys.path.insert(
    0,
    "/Workspace/Users/shubhamsinghchouhan91@gmail.com/data-pipeline/ecommerce_assignment_PEI/ecommerce_databricks_solution/src"
)


@pytest.fixture(scope="session")
def spark():
    """Reuse the existing Databricks Spark session."""
    session = SparkSession.builder.getOrCreate()
    yield session
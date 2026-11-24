"""Unit tests for every transformation, using small hand-built DataFrames."""
import datetime as dt

import pytest
from pyspark.sql import Row

from ecom_pipeline.transformations import (
    UNKNOWN, aggregate_profit, assert_no_critical_issues, data_quality_report,
    enrich_customers, enrich_orders, enrich_products, parse_order_dates,
    standardize_columns, to_snake_case,
)


# ----------------------------- fixtures ------------------------------------ #
@pytest.fixture
def raw_customers(spark):
    return spark.createDataFrame([
        Row(customer_id="C1", customer_name="Gary567 Hansen", email="g@x.com", phone="1",
            segment="Consumer", country="United States", city="A", state="S",
            postal_code="1", region="West"),
        Row(customer_id="C2", customer_name="   _Pete@#$  Takahito  ", email=None, phone=None,
            segment="Corporate", country="United States", city="B", state="S",
            postal_code="2", region="East"),
        Row(customer_id="C3", customer_name=None, email=None, phone=None,
            segment="Consumer", country=None, city="C", state="S",
            postal_code="3", region="East"),
    ])


@pytest.fixture
def raw_products(spark):
    return spark.createDataFrame([
        Row(product_id="P1", category="Furniture", sub_category="Chairs",
            product_name="Chair A", state="NY", price_per_product=10.0),
        Row(product_id="P1", category="Furniture", sub_category="Chairs",
            product_name="Chair B", state="TX", price_per_product=12.0),   # duplicate id
        Row(product_id="P2", category="Technology", sub_category="Phones",
            product_name="Phone", state="CA", price_per_product=99.0),
    ])


@pytest.fixture
def raw_orders(spark):
    return spark.createDataFrame([
        Row(row_id=1, order_id="O1", order_date="21/8/2016", ship_date="25/8/2016",
            ship_mode="Std", customer_id="C1", product_id="P1", quantity=2,
            price=10.0, discount=0.0, profit=10.456),
        Row(row_id=2, order_id="O2", order_date="1/1/2017", ship_date="3/1/2017",
            ship_mode="Std", customer_id="C1", product_id="P2", quantity=1,
            price=99.0, discount=0.1, profit=-5.004),
        Row(row_id=3, order_id="O3", order_date="5/12/2016", ship_date="9/12/2016",
            ship_mode="Std", customer_id="C2", product_id="P1", quantity=1,
            price=10.0, discount=0.0, profit=2.5),
        Row(row_id=4, order_id="O4", order_date="7/7/2017", ship_date="8/7/2017",
            ship_mode="Std", customer_id="C9", product_id="P404", quantity=1,
            price=1.0, discount=0.0, profit=1.0),                         # unknown refs
    ])


# ----------------------------- helpers ------------------------------------- #
def test_to_snake_case():
    assert to_snake_case("Sub-Category") == "sub_category"
    assert to_snake_case("Order ID") == "order_id"
    assert to_snake_case(" Price per product ") == "price_per_product"


def test_standardize_columns(spark):
    df = spark.createDataFrame([(1, 2)], ["Row ID", "Sub-Category"])
    assert standardize_columns(df).columns == ["row_id", "sub_category"]


# ----------------------------- customers ----------------------------------- #
def test_customer_names_are_cleaned(raw_customers):
    names = {r.customer_id: r.customer_name for r in enrich_customers(raw_customers).collect()}
    assert names["C1"] == "Gary Hansen"
    assert names["C2"] == "Pete Takahito"      # symbols removed, spaces collapsed and trimmed
    assert names["C3"] == UNKNOWN              # null name


def test_customer_null_country_defaults(raw_customers):
    row = enrich_customers(raw_customers).filter("customer_id = 'C3'").first()
    assert row.country == UNKNOWN


def test_customers_unique_per_id(spark, raw_customers):
    dupes = raw_customers.unionByName(raw_customers)
    assert enrich_customers(dupes).count() == 3


# ----------------------------- products ------------------------------------ #
def test_products_deduplicated_per_id(raw_products):
    out = enrich_products(raw_products)
    assert out.count() == 2
    assert out.select("product_id").distinct().count() == out.count()


def test_products_keep_category(raw_products):
    row = enrich_products(raw_products).filter("product_id = 'P1'").first()
    assert (row.category, row.sub_category) == ("Furniture", "Chairs")


# ----------------------------- orders -------------------------------------- #
def test_order_dates_parsed(raw_orders):
    row = parse_order_dates(raw_orders).filter("order_id = 'O1'").first()
    assert row.order_date == dt.date(2016, 8, 21)


def test_invalid_date_becomes_null(spark):
    df = spark.createDataFrame([Row(order_date="31/2/2016", ship_date="bad")])
    row = parse_order_dates(df).first()
    assert row.order_date is None and row.ship_date is None


@pytest.fixture
def enriched(raw_orders, raw_customers, raw_products):
    return enrich_orders(raw_orders, enrich_customers(raw_customers), enrich_products(raw_products))


def test_enriched_keeps_order_grain(enriched, raw_orders):
    # duplicate product P1 must not fan out order rows
    assert enriched.count() == raw_orders.count()


def test_profit_rounded_to_two_decimals(enriched):
    profits = {r.order_id: r.profit for r in enriched.collect()}
    assert profits["O1"] == 10.46
    assert profits["O2"] == -5.0


def test_enriched_has_customer_and_product_attributes(enriched):
    row = enriched.filter("order_id = 'O1'").first()
    assert (row.customer_name, row.country) == ("Gary Hansen", "United States")
    assert (row.category, row.sub_category) == ("Furniture", "Chairs")
    assert row.order_year == 2016


def test_unknown_reference_data_not_dropped(enriched):
    row = enriched.filter("order_id = 'O4'").first()
    assert row is not None
    assert row.customer_name == UNKNOWN and row.category == UNKNOWN


# ----------------------------- aggregates ---------------------------------- #
def test_aggregate_profit_by_dimensions(enriched):
    agg = aggregate_profit(enriched)
    row = agg.filter("order_year = 2016 AND category = 'Furniture' AND customer_id = 'C1'").first()
    assert row.total_profit == 10.46
    assert row.order_count == 1


def test_aggregate_total_matches_detail(enriched):
    agg_total = aggregate_profit(enriched).groupBy().sum("total_profit").first()[0]
    detail_total = enriched.groupBy().sum("profit").first()[0]
    assert round(agg_total, 2) == round(detail_total, 2)


def test_aggregate_unique_per_grain(enriched):
    agg = aggregate_profit(enriched)
    keys = ["order_year", "category", "sub_category", "customer_id"]
    assert agg.count() == agg.select(*keys).distinct().count()


# ----------------------------- data quality -------------------------------- #
def test_dq_report_counts(raw_orders, raw_customers, raw_products):
    report = data_quality_report(raw_orders, enrich_customers(raw_customers),
                                 enrich_products(raw_products))
    assert report["orders_total"] == 4
    assert report["orders_unknown_customer"] == 1
    assert report["orders_unknown_product"] == 1
    assert report["orders_unparseable_date"] == 0


def test_critical_issues_raise():
    with pytest.raises(ValueError):
        assert_no_critical_issues({"orders_null_order_id": 1, "orders_unparseable_date": 0})


def test_no_critical_issues_passes():
    assert_no_critical_issues({"orders_null_order_id": 0, "orders_unparseable_date": 0})

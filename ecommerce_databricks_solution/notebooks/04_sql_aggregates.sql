-- Databricks notebook source
-- MAGIC %md
-- MAGIC # 04 · SQL aggregates (Task 5)
-- MAGIC Built on `ecom.agg_profit`. Change the schema name if you used a different one.

-- COMMAND ----------

-- 5.1 Profit by Year
SELECT order_year,
       ROUND(SUM(total_profit), 2) AS profit
FROM ecom.agg_profit
GROUP BY order_year
ORDER BY order_year;

-- COMMAND ----------

-- 5.2 Profit by Year + Product Category
SELECT order_year,
       category,
       ROUND(SUM(total_profit), 2) AS profit
FROM ecom.agg_profit
GROUP BY order_year, category
ORDER BY order_year, category;

-- COMMAND ----------

-- 5.3 Profit by Customer
SELECT customer_id,
       customer_name,
       ROUND(SUM(total_profit), 2) AS profit
FROM ecom.agg_profit
GROUP BY customer_id, customer_name
ORDER BY profit DESC;

-- COMMAND ----------

-- 5.4 Profit by Customer + Year
SELECT customer_id,
       customer_name,
       order_year,
       ROUND(SUM(total_profit), 2) AS profit
FROM ecom.agg_profit
GROUP BY customer_id, customer_name, order_year
ORDER BY customer_id, order_year;
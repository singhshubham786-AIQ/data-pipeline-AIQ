# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "6"
# ///
# MAGIC %md
# MAGIC # 05 · Unit tests
# MAGIC Runs the pytest suite in `tests/` on the cluster.

# COMMAND ----------

# MAGIC %pip install pytest

# COMMAND ----------

import os, sys, pytest

repo_root = os.path.abspath(os.path.join(os.getcwd(), ".."))
sys.path.insert(0, os.path.join(repo_root, "src"))
sys.dont_write_bytecode = True   # avoid __pycache__ writes in a read-only workspace

exit_code = pytest.main([os.path.join(repo_root, "tests"), "-v", "-p", "no:cacheprovider"])
print(f"Pytest exit code: {exit_code}")
assert exit_code == 0, "Unit tests failed"
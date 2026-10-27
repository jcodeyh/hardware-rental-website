"""Read-only access to gov.purchases in Azure SQL.

Auth is Entra-only: the Container App's system-assigned managed identity gets
an access token and hands it to the ODBC driver. There is no password anywhere.
Locally, DefaultAzureCredential falls back to your `az login` session.
"""
import os
import struct
import time
from datetime import date, timedelta

SQL_SERVER = os.getenv("SQL_SERVER", "haas-govdata-westus.database.windows.net")
SQL_DATABASE = os.getenv("SQL_DATABASE", "govdata")
ODBC_DRIVER = os.getenv("ODBC_DRIVER", "ODBC Driver 18 for SQL Server")

SQL_COPT_SS_ACCESS_TOKEN = 1256  # msodbcsql pre-connect attribute for an Entra token
TOKEN_SCOPE = "https://database.windows.net/.default"

# Serverless databases answer these while they resume from auto-pause.
RETRYABLE_SQL_ERRORS = ("40613", "40197", "40501", "49918", "HYT00", "08001")

TOP_N = 10
MIN_DATE = date(1900, 1, 1)
MAX_DATE = date(9999, 12, 30)

_credential = None


def _token_struct():
    global _credential
    if _credential is None:
        from azure.identity import DefaultAzureCredential
        _credential = DefaultAzureCredential()
    token = _credential.get_token(TOKEN_SCOPE).token.encode("utf-16-le")
    return struct.pack(f"<I{len(token)}s", len(token), token)


def connect(retries=6, wait_seconds=10):
    import pyodbc
    conn_str = (
        f"Driver={{{ODBC_DRIVER}}};Server=tcp:{SQL_SERVER},1433;Database={SQL_DATABASE};"
        "Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
    )
    for attempt in range(retries):
        try:
            return pyodbc.connect(conn_str, attrs_before={SQL_COPT_SS_ACCESS_TOKEN: _token_struct()})
        except pyodbc.Error as exc:
            if attempt == retries - 1 or not any(code in str(exc) for code in RETRYABLE_SQL_ERRORS):
                raise
            time.sleep(wait_seconds)


# Every query below filters on one government, so SQL Server only reads the
# matching branch of the gov.purchases UNION ALL view.
_FILTER = "government = ? AND record_date >= ? AND record_date < ?"

SQL_GOVERNMENTS = """
SELECT government, COUNT_BIG(*) AS records, MIN(record_date) AS first_date, MAX(record_date) AS last_date
FROM gov.purchases
GROUP BY government
ORDER BY government;
"""

SQL_HAS_UNIT_PRICE = """
SELECT CASE WHEN EXISTS (SELECT 1 FROM gov.purchases WHERE government = ? AND unit_price IS NOT NULL)
            THEN 1 ELSE 0 END;
"""

SQL_TOP_CATEGORIES = f"""
SELECT TOP ({TOP_N}) category,
       COUNT(*) AS purchases,
       SUM(CASE WHEN amount > 0 THEN amount END) AS total_amount
FROM gov.purchases
WHERE {_FILTER} AND category IS NOT NULL
GROUP BY category
ORDER BY COUNT(*) DESC, category;
"""

# Price rules (requirements 5.2): positive values only; median, 25th and 75th
# percentile (PERCENTILE_CONT interpolates, like numpy's default). The
# 3-purchase minimum and rounding are applied in Python.
SQL_TYPICAL_PRICES = f"""
WITH top_categories AS (
    SELECT TOP ({TOP_N}) category
    FROM gov.purchases
    WHERE {_FILTER} AND category IS NOT NULL
    GROUP BY category
    ORDER BY COUNT(*) DESC, category
),
vals AS (
    SELECT p.category,
           CAST(CASE WHEN ? = 1 THEN p.unit_price ELSE p.amount END AS float) AS v
    FROM gov.purchases p
    JOIN top_categories t ON t.category = p.category
    WHERE p.{_FILTER}
)
SELECT DISTINCT category,
       COUNT(*) OVER (PARTITION BY category) AS purchases,
       PERCENTILE_CONT(0.5)  WITHIN GROUP (ORDER BY v) OVER (PARTITION BY category) AS median,
       PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY v) OVER (PARTITION BY category) AS low,
       PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY v) OVER (PARTITION BY category) AS high
FROM vals
WHERE v > 0;
"""

SQL_TOP_VENDORS = f"""
SELECT TOP ({TOP_N}) vendor,
       COUNT(*) AS purchases,
       SUM(CASE WHEN amount > 0 THEN amount END) AS total_amount
FROM gov.purchases
WHERE {_FILTER} AND vendor IS NOT NULL
GROUP BY vendor
ORDER BY COUNT(*) DESC, vendor;
"""


class SqlRepository:
    """Runs the queries; returns plain dicts so the API layer stays testable."""

    def governments(self):
        with connect() as conn:
            rows = conn.cursor().execute(SQL_GOVERNMENTS).fetchall()
        return [
            {"government": r.government, "records": int(r.records),
             "first_date": r.first_date, "last_date": r.last_date}
            for r in rows
        ]

    def summary(self, government, date_from=None, date_to=None):
        start = date_from or MIN_DATE
        end = (date_to + timedelta(days=1)) if date_to else MAX_DATE  # `to` is inclusive
        f = (government, start, end)
        with connect() as conn:
            cur = conn.cursor()
            use_unit_price = cur.execute(SQL_HAS_UNIT_PRICE, government).fetchval()
            categories = cur.execute(SQL_TOP_CATEGORIES, *f).fetchall()
            prices = cur.execute(SQL_TYPICAL_PRICES, *f, use_unit_price, *f).fetchall()
            vendors = cur.execute(SQL_TOP_VENDORS, *f).fetchall()
        return {
            "price_basis": "unitPrice" if use_unit_price else "payment",
            "categories": [{"category": r.category, "purchases": r.purchases,
                            "total_amount": r.total_amount} for r in categories],
            "prices": {r.category: {"purchases": r.purchases, "median": r.median,
                                    "low": r.low, "high": r.high} for r in prices},
            "vendors": [{"vendor": r.vendor, "purchases": r.purchases,
                         "total_amount": r.total_amount} for r in vendors],
        }

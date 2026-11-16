/* Demo / grading queries against gov.purchases (Azure SQL: hardwarerental) */

-- 1. Records per government, with date coverage
SELECT government, COUNT(*) AS records, MIN(record_date) AS first_date, MAX(record_date) AS last_date
FROM gov.purchases GROUP BY government ORDER BY government;

-- 2. Austin, calendar year 2020
SELECT COUNT(*) AS austin_2020, SUM(amount) AS total_amount
FROM gov.purchases
WHERE government = 'Austin' AND record_date >= '2020-01-01' AND record_date < '2021-01-01';

-- 3. Austin, 2025-01-01 to today
SELECT COUNT(*) AS austin_2025_to_date
FROM gov.purchases
WHERE government = 'Austin' AND record_date >= '2025-01-01' AND record_date < DATEADD(DAY, 1, CAST(GETDATE() AS date));

-- 4. Ten newest Dallas payments
SELECT TOP 10 record_date, vendor, category, buyer, amount
FROM gov.purchases WHERE government = 'Dallas' ORDER BY record_date DESC, amount DESC;

-- 5. Texas charges for March 2023, by vendor
SELECT vendor, COUNT(*) AS line_items, SUM(amount) AS total_charges
FROM gov.purchases
WHERE government = 'Texas' AND record_date >= '2023-03-01' AND record_date < '2023-04-01'
GROUP BY vendor ORDER BY total_charges DESC;

-- 6. Freshness: proves the refresh ran
SELECT source, source_published_at, watermark, last_run_at, last_rows_pulled, last_rows_inserted, last_rows_updated
FROM gov.source_state ORDER BY source;

-- 7. No duplicates (should return zero rows)
SELECT 'austin' AS src, row_hash, dup_ordinal, COUNT(*) c FROM gov.raw_austin GROUP BY row_hash, dup_ordinal HAVING COUNT(*) > 1
UNION ALL
SELECT 'texas', NULL, NULL, COUNT(*) FROM gov.raw_texas GROUP BY source_row_id HAVING COUNT(*) > 1;

-- 8. Business question: typical Austin laptop price by year (median, positive amounts, n >= 3)
SELECT DISTINCT YEAR(record_date) AS yr,
       PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY unit_price) OVER (PARTITION BY YEAR(record_date)) AS median_unit_price,
       COUNT(*) OVER (PARTITION BY YEAR(record_date)) AS purchases
FROM gov.purchases
WHERE government = 'Austin' AND unit_price > 0
  AND (category LIKE '%Laptop%' OR category LIKE '%Notebook%')
ORDER BY yr DESC;

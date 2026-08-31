-- ============================================================
-- NOTEBOOK 1: DATA ENGINEERING CLEANING
-- Purpose: Fix data quality issues that are wrong regardless 
--          of business context (nulls, negatives, duplicates, 
--          orphan keys, type errors, logical impossibilities)
-- ============================================================

-- ============================================================
-- 1.1 CUSTOMERS: CLEAN
-- ============================================================

CREATE OR REPLACE TABLE workspace.demo.clean_customers AS
WITH deduplicated AS (
  SELECT *,
    ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY first_contract_date ASC) AS rn
  FROM workspace.demo.customers
),
filtered AS (
  SELECT * FROM deduplicated WHERE rn = 1
)
SELECT
  customer_id,
  company_name,
  industry,
  company_size,
  region,
  province,
  city,
  registration_date,
  first_contract_date,
  customer_source,
  is_internal_account,
  credit_tier
FROM filtered
WHERE 
  -- Remove rows with null customer_id
  customer_id IS NOT NULL
  -- Remove future registration dates (beyond 2025-12-31)
  AND registration_date <= '2025-12-31'
  -- Remove rows where first_contract_date is before registration_date
  AND first_contract_date >= registration_date
  -- Remove null industry (can't classify)
  AND industry IS NOT NULL
;

SELECT 'clean_customers' AS table_name, COUNT(*) AS row_count FROM workspace.demo.clean_customers;


-- ============================================================
-- 1.2 CONTRACTS: CLEAN
-- ============================================================

CREATE OR REPLACE TABLE workspace.demo.clean_contracts AS
WITH deduplicated AS (
  SELECT *,
    ROW_NUMBER() OVER (PARTITION BY contract_id ORDER BY sign_date ASC) AS rn
  FROM workspace.demo.contracts
),
filtered AS (
  SELECT * FROM deduplicated WHERE rn = 1
)
SELECT
  c.contract_id,
  c.customer_id,
  c.parent_contract_id,
  c.contract_sequence,
  c.sign_date,
  c.effective_date,
  c.expiry_date,
  c.product_line,
  c.product_edition,
  c.deployment_type,
  c.contract_type,
  c.payment_terms,
  -- Fix: recalculate discount rate from list and actual
  c.total_list_price,
  c.total_actual_price,
  CASE 
    WHEN c.total_list_price > 0 
    THEN ROUND(c.total_actual_price / c.total_list_price, 4)
    ELSE NULL 
  END AS calculated_discount_rate,
  c.currency,
  c.sales_rep_id,
  c.sales_channel,
  c.approval_status
FROM filtered c
-- Only keep contracts whose customer_id exists in clean_customers
INNER JOIN workspace.demo.clean_customers cust
  ON c.customer_id = cust.customer_id
WHERE
  -- Remove rejected/pending contracts
  c.approval_status = 'approved'
  -- Remove negative prices
  AND c.total_list_price >= 0
  AND c.total_actual_price >= 0
  -- Remove cases where actual price > 2x list price (clearly wrong)
  AND (c.total_list_price = 0 OR c.total_actual_price <= c.total_list_price * 2)
  -- Remove date inversions: effective must be before expiry
  AND c.effective_date < c.expiry_date
  -- Remove contracts with sign_date in the future
  AND c.sign_date <= '2025-12-31'
  -- Remove list_price = 0 but actual > 0 (data entry error)
  AND NOT (c.total_list_price = 0 AND c.total_actual_price > 0)
;

SELECT 'clean_contracts' AS table_name, COUNT(*) AS row_count FROM workspace.demo.clean_contracts;


-- ============================================================
-- 1.3 CONTRACT_MODULES: CLEAN
-- ============================================================

CREATE OR REPLACE TABLE workspace.demo.clean_contract_modules AS
WITH deduplicated AS (
  SELECT *,
    ROW_NUMBER() OVER (
      PARTITION BY contract_id, module_name 
      ORDER BY line_id ASC
    ) AS rn
  FROM workspace.demo.contract_modules
),
filtered AS (
  SELECT * FROM deduplicated WHERE rn = 1
)
SELECT
  f.line_id,
  f.contract_id,
  f.app_category,
  f.domain,
  f.module_name,
  f.unit_list_price,
  f.unit_actual_price,
  f.quantity,
  -- Recalculate line totals to fix inconsistencies
  ROUND(f.unit_list_price * f.quantity, 2) AS line_list_total,
  ROUND(f.unit_actual_price * f.quantity, 2) AS line_actual_total,
  f.is_bundled,
  f.is_first_purchase
FROM filtered f
-- Only keep modules whose contract_id exists in clean_contracts
INNER JOIN workspace.demo.clean_contracts c
  ON f.contract_id = c.contract_id
WHERE
  -- Remove null/fake module names
  f.module_name IS NOT NULL
  AND f.module_name NOT IN ('N/A', 'TBD', 'null', '')
  -- Remove negative unit prices
  AND f.unit_list_price >= 0
  AND f.unit_actual_price >= 0
  -- Remove zero quantity (unless bundled with zero price, which is valid)
  AND (f.quantity > 0 OR (f.is_bundled = true AND f.unit_actual_price = 0))
  -- Fix category mismatch: if app_category is core_finance, 
  -- domain should be finance-related
  AND NOT (
    f.app_category = 'core_finance' 
    AND f.domain NOT IN ('finance')
  )
;

SELECT 'clean_contract_modules' AS table_name, COUNT(*) AS row_count FROM workspace.demo.clean_contract_modules;


-- ============================================================
-- 1.4 LICENSED_USERS: CLEAN
-- ============================================================

CREATE OR REPLACE TABLE workspace.demo.clean_licensed_users AS
SELECT
  lu.license_id,
  lu.contract_id,
  lu.module_name,
  lu.user_type,
  lu.licensed_user_count,
  lu.unit_user_list_price,
  lu.unit_user_actual_price,
  -- Recalculate user_line_total
  ROUND(lu.licensed_user_count * lu.unit_user_actual_price, 2) AS user_line_total
FROM workspace.demo.licensed_users lu
-- Only keep rows whose contract_id exists in clean_contracts
INNER JOIN workspace.demo.clean_contracts c
  ON lu.contract_id = c.contract_id
WHERE
  -- Remove negative or zero user counts
  lu.licensed_user_count > 0
  -- Remove negative prices
  AND lu.unit_user_list_price >= 0
  AND lu.unit_user_actual_price >= 0
;

SELECT 'clean_licensed_users' AS table_name, COUNT(*) AS row_count FROM workspace.demo.clean_licensed_users;


-- ============================================================
-- 1.5 USAGE_ACTIVITY: CLEAN
-- ============================================================

CREATE OR REPLACE TABLE workspace.demo.clean_usage_activity AS
WITH deduplicated AS (
  SELECT *,
    ROW_NUMBER() OVER (
      PARTITION BY customer_id, module_name, activity_month 
      ORDER BY activity_id ASC
    ) AS rn
  FROM workspace.demo.usage_activity
),
filtered AS (
  SELECT * FROM deduplicated WHERE rn = 1
)
SELECT
  f.activity_id,
  f.customer_id,
  f.contract_id,
  f.product_edition,
  f.module_name,
  f.activity_month,
  -- Cap negative logins at 0
  GREATEST(f.monthly_logins, 0) AS monthly_logins,
  GREATEST(f.active_user_count, 0) AS active_user_count,
  GREATEST(f.feature_api_calls, 0) AS feature_api_calls,
  GREATEST(f.data_volume_mb, 0) AS data_volume_mb
FROM filtered f
-- Only keep rows whose contract exists
INNER JOIN workspace.demo.clean_contracts c
  ON f.contract_id = c.contract_id
WHERE
  -- Remove usage records before contract effective date
  f.activity_month >= DATE_TRUNC('month', c.effective_date)
  -- Remove usage with 0 logins but abnormally high API calls (bot/script)
  AND NOT (f.monthly_logins <= 0 AND f.feature_api_calls > 5000)
;

SELECT 'clean_usage_activity' AS table_name, COUNT(*) AS row_count FROM workspace.demo.clean_usage_activity;


-- ============================================================
-- 1.6 RENEWALS: CLEAN
-- ============================================================

CREATE OR REPLACE TABLE workspace.demo.clean_renewals AS
SELECT
  r.renewal_id,
  r.original_contract_id,
  r.new_contract_id,
  r.customer_id,
  r.renewal_due_date,
  r.renewal_decision_date,
  -- Fix contradictions: if renewed=yes but value=0, mark as no
  CASE 
    WHEN r.renewed = 'yes' AND r.renewal_annual_value = 0 THEN 'no'
    WHEN r.renewed = 'no' AND r.new_contract_id IS NOT NULL THEN 'yes'
    ELSE r.renewed
  END AS renewed,
  r.previous_annual_value,
  r.renewal_annual_value,
  r.price_change_pct,
  r.churn_reason
FROM workspace.demo.renewals r
-- Only keep rows whose original contract exists
INNER JOIN workspace.demo.clean_contracts c
  ON r.original_contract_id = c.contract_id
WHERE
  -- Remove negative previous values
  r.previous_annual_value >= 0
  -- Remove abnormally early decision dates (>180 days before due)
  AND DATEDIFF(r.renewal_due_date, r.renewal_decision_date) <= 180
;

SELECT 'clean_renewals' AS table_name, COUNT(*) AS row_count FROM workspace.demo.clean_renewals;


-- ============================================================
-- 1.7 CLEANING SUMMARY: before vs after row counts
-- ============================================================

SELECT 'customers' AS tbl, 
  (SELECT COUNT(*) FROM workspace.demo.customers) AS raw_rows,
  (SELECT COUNT(*) FROM workspace.demo.clean_customers) AS clean_rows,
  ROUND(1 - (SELECT COUNT(*) FROM workspace.demo.clean_customers) * 1.0 / (SELECT COUNT(*) FROM workspace.demo.customers), 4) AS pct_removed
UNION ALL
SELECT 'contracts',
  (SELECT COUNT(*) FROM workspace.demo.contracts),
  (SELECT COUNT(*) FROM workspace.demo.clean_contracts),
  ROUND(1 - (SELECT COUNT(*) FROM workspace.demo.clean_contracts) * 1.0 / (SELECT COUNT(*) FROM workspace.demo.contracts), 4)
UNION ALL
SELECT 'contract_modules',
  (SELECT COUNT(*) FROM workspace.demo.contract_modules),
  (SELECT COUNT(*) FROM workspace.demo.clean_contract_modules),
  ROUND(1 - (SELECT COUNT(*) FROM workspace.demo.clean_contract_modules) * 1.0 / (SELECT COUNT(*) FROM workspace.demo.contract_modules), 4)
UNION ALL
SELECT 'licensed_users',
  (SELECT COUNT(*) FROM workspace.demo.licensed_users),
  (SELECT COUNT(*) FROM workspace.demo.clean_licensed_users),
  ROUND(1 - (SELECT COUNT(*) FROM workspace.demo.clean_licensed_users) * 1.0 / (SELECT COUNT(*) FROM workspace.demo.licensed_users), 4)
UNION ALL
SELECT 'usage_activity',
  (SELECT COUNT(*) FROM workspace.demo.usage_activity),
  (SELECT COUNT(*) FROM workspace.demo.clean_usage_activity),
  ROUND(1 - (SELECT COUNT(*) FROM workspace.demo.clean_usage_activity) * 1.0 / (SELECT COUNT(*) FROM workspace.demo.usage_activity), 4)
UNION ALL
SELECT 'renewals',
  (SELECT COUNT(*) FROM workspace.demo.renewals),
  (SELECT COUNT(*) FROM workspace.demo.clean_renewals),
  ROUND(1 - (SELECT COUNT(*) FROM workspace.demo.clean_renewals) * 1.0 / (SELECT COUNT(*) FROM workspace.demo.renewals), 4)
;

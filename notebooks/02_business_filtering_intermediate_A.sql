-- ============================================================
-- NOTEBOOK 2: BUSINESS LOGIC FILTERING + INTERMEDIATE TABLE A
-- Purpose: Apply business rules to exclude non-standard records,
--          then aggregate to module-level summary table
-- ============================================================

-- ============================================================
-- 2.1 BUSINESS-FILTERED CONTRACTS
-- Exclude perpetual, trial, POC, internal accounts, 
-- short-term anomalies, non-CNY
-- ============================================================

CREATE OR REPLACE TABLE workspace.demo.biz_contracts AS
SELECT c.*
FROM workspace.demo.clean_contracts c
INNER JOIN workspace.demo.clean_customers cust
  ON c.customer_id = cust.customer_id
WHERE
  -- Only subscription contracts (exclude perpetual, trial, POC)
  c.contract_type = 'subscription'
  -- Exclude internal/test accounts
  AND cust.is_internal_account = false
  AND cust.company_name NOT LIKE '%Test%'
  AND cust.company_name NOT LIKE '%Demo%'
  -- Exclude abnormally short subscriptions (< 30 days)
  AND DATEDIFF(c.expiry_date, c.effective_date) >= 30
  -- Only CNY contracts
  AND c.currency = 'CNY'
;

SELECT 'biz_contracts' AS table_name, COUNT(*) AS row_count FROM workspace.demo.biz_contracts;


-- ============================================================
-- 2.2 ACTIVE CUSTOMER LOOKUP (by year)
-- A customer is "active" in a given year if they have at least
-- one month with logins > 0 AND active_user_count > 0
-- ============================================================

CREATE OR REPLACE TABLE workspace.demo.active_customers_by_year AS
SELECT
  ua.customer_id,
  YEAR(ua.activity_month) AS year,
  SUM(ua.monthly_logins) AS total_logins,
  MAX(ua.active_user_count) AS max_active_users,
  COUNT(DISTINCT CASE WHEN ua.monthly_logins > 0 AND ua.active_user_count > 0 
    THEN ua.activity_month END) AS active_months
FROM workspace.demo.clean_usage_activity ua
GROUP BY ua.customer_id, YEAR(ua.activity_month)
HAVING active_months >= 1
;

SELECT 'active_customers_by_year' AS table_name, COUNT(*) AS row_count FROM workspace.demo.active_customers_by_year;


-- ============================================================
-- 2.3 INTERMEDIATE TABLE A: MODULE-LEVEL SUMMARY
-- Grain: year x customer_type x product_line x product_edition
--        x app_category x domain x module_name
-- ============================================================

CREATE OR REPLACE TABLE workspace.demo.intermediate_module_summary AS
WITH contract_year AS (
  SELECT
    bc.*,
    YEAR(bc.sign_date) AS contract_year,
    CASE 
      WHEN YEAR(bc.sign_date) = YEAR(cust.first_contract_date) THEN 'new'
      ELSE 'existing'
    END AS customer_type,
    CASE
      WHEN bc.product_line IN ('CloudERP','SkyPlatform','NovaStar','NovaStarHR') THEN 'current'
      ELSE 'legacy'
    END AS product_category
  FROM workspace.demo.biz_contracts bc
  INNER JOIN workspace.demo.clean_customers cust
    ON bc.customer_id = cust.customer_id
),

module_detail AS (
  SELECT
    cy.contract_year,
    cy.customer_type,
    cy.product_category,
    cy.product_line,
    cy.product_edition,
    cy.customer_id,
    cm.app_category,
    cm.domain,
    cm.module_name,
    cm.unit_list_price,
    cm.unit_actual_price,
    cm.quantity,
    cm.line_list_total,
    cm.line_actual_total,
    cm.is_bundled
  FROM contract_year cy
  INNER JOIN workspace.demo.clean_contract_modules cm
    ON cy.contract_id = cm.contract_id
  WHERE cm.app_category != 'suite_mode'  -- exclude suite bundle placeholders
),

-- Count total active customers per year x customer_type x product_line
-- for adoption rate denominators
active_totals AS (
  SELECT
    cy.contract_year,
    cy.customer_type,
    cy.product_line,
    COUNT(DISTINCT cy.customer_id) AS total_customers_in_product_line
  FROM contract_year cy
  INNER JOIN workspace.demo.active_customers_by_year act
    ON cy.customer_id = act.customer_id
    AND cy.contract_year = act.year
  GROUP BY cy.contract_year, cy.customer_type, cy.product_line
),

-- Module-level aggregation
module_agg AS (
  SELECT
    md.contract_year AS year,
    md.customer_type,
    md.product_category,
    md.product_line,
    md.product_edition,
    md.app_category,
    md.domain,
    md.module_name,
    
    -- Price metrics
    ROUND(AVG(md.unit_list_price), 2) AS avg_module_list_price,
    ROUND(AVG(md.unit_actual_price), 2) AS avg_module_actual_price,
    ROUND(AVG(md.quantity), 2) AS avg_module_quantity,
    
    -- Customer counts
    COUNT(DISTINCT md.customer_id) AS module_customer_count,
    
    -- Discount rate
    ROUND(
      CASE WHEN SUM(md.line_list_total) > 0 
      THEN SUM(md.line_actual_total) / SUM(md.line_list_total) 
      ELSE NULL END, 
    4) AS module_discount_rate,
    
    -- Revenue
    ROUND(SUM(md.line_list_total), 2) AS module_list_revenue,
    ROUND(SUM(md.line_actual_total), 2) AS module_actual_revenue

  FROM module_detail md
  GROUP BY 
    md.contract_year, md.customer_type, md.product_category,
    md.product_line, md.product_edition, md.app_category,
    md.domain, md.module_name
)

SELECT
  ma.*,
  
  -- Adoption rate = module customers / total active customers in product line
  at.total_customers_in_product_line,
  ROUND(
    CASE WHEN at.total_customers_in_product_line > 0
    THEN ma.module_customer_count * 1.0 / at.total_customers_in_product_line
    ELSE NULL END,
  4) AS module_adoption_rate,

  -- Domain-level rollups (window functions)
  SUM(ma.module_list_revenue) OVER (
    PARTITION BY ma.year, ma.customer_type, ma.product_line, 
    ma.product_edition, ma.domain
  ) AS domain_list_revenue,
  
  SUM(ma.module_actual_revenue) OVER (
    PARTITION BY ma.year, ma.customer_type, ma.product_line, 
    ma.product_edition, ma.domain
  ) AS domain_actual_revenue,

  -- Product-line-level rollups
  SUM(ma.module_list_revenue) OVER (
    PARTITION BY ma.year, ma.customer_type, ma.product_line, 
    ma.product_edition
  ) AS edition_list_revenue,
  
  SUM(ma.module_actual_revenue) OVER (
    PARTITION BY ma.year, ma.customer_type, ma.product_line, 
    ma.product_edition
  ) AS edition_actual_revenue

FROM module_agg ma
LEFT JOIN active_totals at
  ON ma.year = at.contract_year
  AND ma.customer_type = at.customer_type
  AND ma.product_line = at.product_line
ORDER BY ma.year, ma.customer_type, ma.product_line, ma.product_edition, 
  ma.app_category, ma.domain, ma.module_name
;

SELECT 'intermediate_module_summary' AS table_name, COUNT(*) AS row_count 
FROM workspace.demo.intermediate_module_summary;

-- Quick sanity check: row counts by year
SELECT year, customer_type, COUNT(*) AS rows, 
  COUNT(DISTINCT product_line) AS product_lines,
  COUNT(DISTINCT module_name) AS modules,
  ROUND(SUM(module_actual_revenue), 0) AS total_actual_revenue
FROM workspace.demo.intermediate_module_summary
GROUP BY year, customer_type
ORDER BY year, customer_type;

-- ============================================================
-- NOTEBOOK 3: INTERMEDIATE TABLE B - CUSTOMER YEARLY PROFILE
-- Purpose: Build a customer x year wide table that tracks
--          module adoption, upsell/cross-sell, usage, and 
--          renewal outcomes for downstream analysis
-- ============================================================

-- ============================================================
-- 3.1 CUSTOMER YEARLY PROFILE
-- One row per customer per year
-- ============================================================

CREATE OR REPLACE TABLE workspace.demo.customer_yearly_profile AS
WITH yearly_contracts AS (
  SELECT
    bc.customer_id,
    YEAR(bc.sign_date) AS year,
    cust.company_size,
    cust.industry,
    cust.region,
    cust.first_contract_date,
    bc.product_line,
    bc.product_edition,
    COUNT(DISTINCT bc.contract_id) AS contract_count,
    ROUND(SUM(bc.total_actual_price), 2) AS total_annual_value,
    ROUND(SUM(bc.total_list_price), 2) AS total_list_value
  FROM workspace.demo.biz_contracts bc
  INNER JOIN workspace.demo.clean_customers cust
    ON bc.customer_id = cust.customer_id
  GROUP BY 
    bc.customer_id, YEAR(bc.sign_date), cust.company_size, 
    cust.industry, cust.region, cust.first_contract_date,
    bc.product_line, bc.product_edition
),

-- What modules does each customer have each year?
yearly_modules AS (
  SELECT
    bc.customer_id,
    YEAR(bc.sign_date) AS year,
    cm.app_category,
    cm.domain,
    cm.module_name,
    cm.is_first_purchase
  FROM workspace.demo.biz_contracts bc
  INNER JOIN workspace.demo.clean_contract_modules cm
    ON bc.contract_id = cm.contract_id
  WHERE cm.app_category != 'suite_mode'
),

-- Pivot module categories into boolean columns
module_flags AS (
  SELECT
    customer_id,
    year,
    COUNT(DISTINCT module_name) AS module_count,
    MAX(CASE WHEN app_category = 'core_finance' THEN 1 ELSE 0 END) AS has_core_finance,
    MAX(CASE WHEN app_category = 'advanced_finance' THEN 1 ELSE 0 END) AS has_advanced_finance,
    MAX(CASE WHEN domain = 'supply_chain' THEN 1 ELSE 0 END) AS has_supply_chain,
    MAX(CASE WHEN domain = 'manufacturing' THEN 1 ELSE 0 END) AS has_manufacturing,
    MAX(CASE WHEN domain = 'hr' THEN 1 ELSE 0 END) AS has_hr,
    MAX(CASE WHEN domain = 'platform' THEN 1 ELSE 0 END) AS has_platform,
    MAX(CASE WHEN domain = 'channel' THEN 1 ELSE 0 END) AS has_channel,
    MAX(CASE WHEN domain LIKE 'industry%' THEN 1 ELSE 0 END) AS has_industry_vertical,
    MAX(CASE WHEN domain = 'collaboration' THEN 1 ELSE 0 END) AS has_collaboration,
    MAX(CASE WHEN domain = 'product' THEN 1 ELSE 0 END) AS has_product_mgmt,
    MAX(CASE WHEN domain = 'quality' THEN 1 ELSE 0 END) AS has_quality,
    MAX(CASE WHEN domain = 'project' THEN 1 ELSE 0 END) AS has_project
  FROM yearly_modules
  GROUP BY customer_id, year
),

-- Previous year module flags for upsell/cross-sell detection
prev_year_flags AS (
  SELECT
    customer_id,
    year,
    has_core_finance,
    has_advanced_finance,
    has_supply_chain,
    has_manufacturing,
    has_hr,
    has_platform,
    has_channel,
    has_industry_vertical,
    LAG(has_advanced_finance) OVER (PARTITION BY customer_id ORDER BY year) AS prev_has_advanced_finance,
    LAG(has_supply_chain) OVER (PARTITION BY customer_id ORDER BY year) AS prev_has_supply_chain,
    LAG(has_manufacturing) OVER (PARTITION BY customer_id ORDER BY year) AS prev_has_manufacturing,
    LAG(has_hr) OVER (PARTITION BY customer_id ORDER BY year) AS prev_has_hr,
    LAG(has_platform) OVER (PARTITION BY customer_id ORDER BY year) AS prev_has_platform,
    LAG(has_channel) OVER (PARTITION BY customer_id ORDER BY year) AS prev_has_channel,
    LAG(has_industry_vertical) OVER (PARTITION BY customer_id ORDER BY year) AS prev_has_industry_vertical
  FROM module_flags
),

-- Usage summary per customer per year
yearly_usage AS (
  SELECT
    customer_id,
    YEAR(activity_month) AS year,
    ROUND(AVG(monthly_logins), 2) AS monthly_avg_logins,
    ROUND(AVG(active_user_count), 2) AS monthly_avg_active_users,
    SUM(feature_api_calls) AS total_api_calls
  FROM workspace.demo.clean_usage_activity
  GROUP BY customer_id, YEAR(activity_month)
),

-- Licensed user count per customer per year
yearly_licenses AS (
  SELECT
    bc.customer_id,
    YEAR(bc.sign_date) AS year,
    SUM(lu.licensed_user_count) AS total_licensed_users
  FROM workspace.demo.biz_contracts bc
  INNER JOIN workspace.demo.clean_licensed_users lu
    ON bc.contract_id = lu.contract_id
  GROUP BY bc.customer_id, YEAR(bc.sign_date)
),

-- Renewal outcome: did this customer renew next year?
renewal_outcome AS (
  SELECT
    r.customer_id,
    YEAR(r.renewal_due_date) AS renewal_year,
    MAX(CASE WHEN r.renewed = 'yes' THEN 1 ELSE 0 END) AS renewed_flag,
    MAX(r.churn_reason) AS churn_reason
  FROM workspace.demo.clean_renewals r
  GROUP BY r.customer_id, YEAR(r.renewal_due_date)
)

SELECT
  yc.customer_id,
  yc.year,
  
  -- Customer attributes
  CASE 
    WHEN yc.year = YEAR(yc.first_contract_date) THEN 'new'
    ELSE 'existing'
  END AS customer_type,
  yc.year - YEAR(yc.first_contract_date) AS tenure_years,
  yc.company_size,
  yc.industry,
  yc.region,
  yc.product_line,
  yc.product_edition,
  
  -- Contract value
  yc.contract_count,
  yc.total_annual_value,
  yc.total_list_value,
  ROUND(
    CASE WHEN yc.total_list_value > 0 
    THEN yc.total_annual_value / yc.total_list_value 
    ELSE NULL END,
  4) AS overall_discount,
  
  -- Module adoption
  COALESCE(mf.module_count, 0) AS module_count,
  COALESCE(mf.has_core_finance, 0) AS has_core_finance,
  COALESCE(mf.has_advanced_finance, 0) AS has_advanced_finance,
  COALESCE(mf.has_supply_chain, 0) AS has_supply_chain,
  COALESCE(mf.has_manufacturing, 0) AS has_manufacturing,
  COALESCE(mf.has_hr, 0) AS has_hr,
  COALESCE(mf.has_platform, 0) AS has_platform,
  COALESCE(mf.has_channel, 0) AS has_channel,
  COALESCE(mf.has_industry_vertical, 0) AS has_industry_vertical,
  COALESCE(mf.has_collaboration, 0) AS has_collaboration,
  COALESCE(mf.has_product_mgmt, 0) AS has_product_mgmt,
  COALESCE(mf.has_quality, 0) AS has_quality,
  COALESCE(mf.has_project, 0) AS has_project,
  
  -- How many major categories does this customer use?
  (COALESCE(mf.has_core_finance, 0) + COALESCE(mf.has_advanced_finance, 0) 
   + COALESCE(mf.has_supply_chain, 0) + COALESCE(mf.has_manufacturing, 0) 
   + COALESCE(mf.has_hr, 0) + COALESCE(mf.has_platform, 0) 
   + COALESCE(mf.has_channel, 0) + COALESCE(mf.has_industry_vertical, 0)
  ) AS module_category_count,
  
  -- Upsell: this year has advanced_finance, last year didn't
  CASE 
    WHEN COALESCE(pf.has_advanced_finance, 0) = 1 
      AND COALESCE(pf.prev_has_advanced_finance, 0) = 0 
    THEN 1 ELSE 0 
  END AS is_upsell_year,
  
  -- Cross-sell: this year has any non-finance domain that last year didn't
  CASE 
    WHEN (COALESCE(pf.has_supply_chain, 0) = 1 AND COALESCE(pf.prev_has_supply_chain, 0) = 0)
      OR (COALESCE(pf.has_manufacturing, 0) = 1 AND COALESCE(pf.prev_has_manufacturing, 0) = 0)
      OR (COALESCE(pf.has_hr, 0) = 1 AND COALESCE(pf.prev_has_hr, 0) = 0)
      OR (COALESCE(pf.has_platform, 0) = 1 AND COALESCE(pf.prev_has_platform, 0) = 0)
      OR (COALESCE(pf.has_channel, 0) = 1 AND COALESCE(pf.prev_has_channel, 0) = 0)
      OR (COALESCE(pf.has_industry_vertical, 0) = 1 AND COALESCE(pf.prev_has_industry_vertical, 0) = 0)
    THEN 1 ELSE 0
  END AS is_crosssell_year,
  
  -- Usage metrics
  COALESCE(yu.monthly_avg_logins, 0) AS monthly_avg_logins,
  COALESCE(yu.monthly_avg_active_users, 0) AS monthly_avg_active_users,
  COALESCE(yu.total_api_calls, 0) AS total_api_calls,
  CASE WHEN COALESCE(yu.monthly_avg_logins, 0) > 0 
    AND COALESCE(yu.monthly_avg_active_users, 0) > 0 
    THEN 1 ELSE 0 
  END AS is_active,
  
  -- Licensed users
  COALESCE(yl.total_licensed_users, 0) AS total_licensed_users,
  
  -- Renewal outcome (next year)
  COALESCE(ro.renewed_flag, NULL) AS renewed_next_year,
  ro.churn_reason,
  
  -- YoY value change
  LAG(yc.total_annual_value) OVER (
    PARTITION BY yc.customer_id ORDER BY yc.year
  ) AS prev_year_value,
  ROUND(
    CASE 
      WHEN LAG(yc.total_annual_value) OVER (PARTITION BY yc.customer_id ORDER BY yc.year) > 0
      THEN (yc.total_annual_value - LAG(yc.total_annual_value) OVER (PARTITION BY yc.customer_id ORDER BY yc.year))
        / LAG(yc.total_annual_value) OVER (PARTITION BY yc.customer_id ORDER BY yc.year)
      ELSE NULL
    END,
  4) AS yoy_value_change

FROM yearly_contracts yc
LEFT JOIN module_flags mf 
  ON yc.customer_id = mf.customer_id AND yc.year = mf.year
LEFT JOIN prev_year_flags pf 
  ON yc.customer_id = pf.customer_id AND yc.year = pf.year
LEFT JOIN yearly_usage yu 
  ON yc.customer_id = yu.customer_id AND yc.year = yu.year
LEFT JOIN yearly_licenses yl 
  ON yc.customer_id = yl.customer_id AND yc.year = yl.year
LEFT JOIN renewal_outcome ro 
  ON yc.customer_id = ro.customer_id AND yc.year = ro.renewal_year
ORDER BY yc.customer_id, yc.year
;

SELECT 'customer_yearly_profile' AS table_name, COUNT(*) AS row_count 
FROM workspace.demo.customer_yearly_profile;


-- ============================================================
-- 3.2 SANITY CHECKS
-- ============================================================

-- Check: customer type distribution by year
SELECT year, customer_type, COUNT(*) AS customers,
  ROUND(AVG(total_annual_value), 0) AS avg_annual_value,
  ROUND(AVG(module_count), 1) AS avg_modules
FROM workspace.demo.customer_yearly_profile
GROUP BY year, customer_type
ORDER BY year, customer_type;

-- Check: upsell and cross-sell rates by year (existing customers only)
SELECT year,
  COUNT(*) AS existing_customers,
  SUM(is_upsell_year) AS upsell_count,
  ROUND(AVG(is_upsell_year), 4) AS upsell_rate,
  SUM(is_crosssell_year) AS crosssell_count,
  ROUND(AVG(is_crosssell_year), 4) AS crosssell_rate
FROM workspace.demo.customer_yearly_profile
WHERE customer_type = 'existing'
GROUP BY year
ORDER BY year;

-- Check: renewal rate by module_category_count
SELECT 
  module_category_count,
  COUNT(*) AS customers,
  SUM(CASE WHEN renewed_next_year = 1 THEN 1 ELSE 0 END) AS renewed,
  ROUND(AVG(CASE WHEN renewed_next_year IS NOT NULL THEN renewed_next_year ELSE NULL END), 4) AS renewal_rate
FROM workspace.demo.customer_yearly_profile
WHERE renewed_next_year IS NOT NULL
GROUP BY module_category_count
ORDER BY module_category_count;

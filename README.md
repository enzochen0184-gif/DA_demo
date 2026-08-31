# SaaS Customer Analytics: Land & Expand Strategy

End-to-end data analytics project built on Databricks, demonstrating the complete pipeline from raw data cleaning to strategic business recommendations. Built using ~860,000 rows of synthetic data modelled on real enterprise SaaS operations.

## Business Question

How should a B2B SaaS company optimise its Land & Expand strategy to maximise customer lifetime value and reduce churn?

Enterprise SaaS companies typically acquire customers through a core product (Land), then grow revenue by selling premium features (Upsell to Advanced Finance) and adjacent modules (Cross-sell to Supply Chain, Manufacturing, HR etc). This project analyses which expansion paths drive the highest ARPU and retention.

## Project Structure

```
saas-churn-analytics-databricks/
├── README.md
├── notebooks/
│   ├── 01_data_engineering_cleaning.sql
│   ├── 02_business_filtering_intermediate_A.sql
│   ├── 03_intermediate_B_customer_profile.sql
│   ├── 04_land_expand_analysis.py
│   └── 05_churn_driver_analysis.py
└── data/
    └── generate_raw_data.py
```

## Data Architecture

### Raw Data: 6 Tables (~860K rows)

| Table | Rows | Description |
|---|---|---|
| customers | 20,000 | Company profiles, industry, region, credit tier |
| contracts | 68,957 | Subscription contracts with list price, actual price, product line, edition |
| contract_modules | 241,952 | Module-level line items with unit pricing (core finance, advanced finance, non-finance) |
| licensed_users | 96,780 | Per-module user licensing with named/concurrent types |
| usage_activity | 400,300 | Monthly login counts, active users, API calls per customer per module |
| renewals | 35,000 | Renewal decisions with churn reasons |

The raw data was generated using `data/generate_raw_data.py` with intentional data quality issues embedded for cleaning demonstration (see below).

### Product Hierarchy

- 7 product lines (CloudERP, SkyPlatform, NovaStar, NovaStarHR, LegacyEAS, LegacyHR, LegacyK3)
- 22 editions across public cloud, private cloud, and on-premise deployments
- 45+ modules grouped into core finance, advanced finance, and non-finance domains (supply chain, manufacturing, HR, platform, channel, industry verticals)

## Pipeline

### Step 1: Data Engineering Cleaning (Notebook 01)

Removed ~7% of records for data quality issues that are wrong regardless of business context:

| Issue | How detected | How fixed |
|---|---|---|
| Duplicate rows | ROW_NUMBER partitioned by primary key | Keep first occurrence |
| Negative amounts | WHERE total_actual_price >= 0 | Remove row |
| Orphan foreign keys | INNER JOIN to parent table | Remove row |
| Calculation mismatches | line_list_total != unit_price * quantity | Recalculate from unit price and quantity |
| Future dates | sign_date > '2025-12-31' | Remove row |
| Date inversions | effective_date > expiry_date | Remove row |
| String-type nulls | module_name IN ('N/A', 'TBD', 'null') | Remove row |
| Category mismatches | app_category = 'core_finance' but domain = 'manufacturing' | Remove row |
| Contradictory renewals | renewed = 'yes' but renewal_value = 0 | Fix renewed flag to 'no' |
| Bot/script activity | 0 logins but >5,000 API calls | Remove row |
| Rejected/pending contracts | approval_status != 'approved' | Remove row |

### Step 2: Business Logic Filtering (Notebook 02)

Excluded ~5% of remaining records for business reasons. These are valid data records that should not be included in a SaaS subscription analysis:

- **Perpetual contracts**: one-time purchases with no renewal cycle
- **Trial and POC contracts**: not real revenue
- **Internal test accounts**: flagged accounts + company names containing "Test" or "Demo"
- **Contracts shorter than 30 days**: anomalous short-term deals
- **Non-CNY currency contracts**: out of scope for domestic analysis

### Step 3: Intermediate Table A — Module-Level Summary (Notebook 02)

Aggregated by year x customer_type x product_line x edition x app_category x domain x module.

Key calculations:
- **Customer classification**: new vs existing based on first_contract_date vs current year
- **Active customer identification**: from usage_activity, requiring monthly_logins > 0 AND active_user_count > 0
- **Module adoption rate**: module customer count / total active customers in product line
- **Discount rate**: sum(actual) / sum(list) at module level
- **Revenue rollups**: module level -> domain level -> edition level using SQL window functions

### Step 4: Intermediate Table B — Customer Yearly Profile (Notebook 03)

One row per customer per year with:
- **Module adoption flags**: has_core_finance, has_advanced_finance, has_supply_chain, has_manufacturing, has_hr, has_platform, has_channel, has_industry_vertical
- **Upsell detection**: current year has advanced_finance, previous year did not (using LAG window function)
- **Cross-sell detection**: current year has any non-finance domain that previous year did not
- **Usage metrics**: monthly average logins, active users, API calls
- **Renewal outcome**: renewed_next_year as binary target variable
- **YoY value change**: compared to previous year using LAG

### Step 5: Land & Expand Analysis (Notebook 04)

Analysis of customer acquisition and expansion patterns:

**Landing Pattern**: Most new customers enter through Core Finance modules. Average new customer purchases 2-3 modules at first contract.

**Expansion Funnel**: Existing customers who both upsell (to Advanced Finance) and cross-sell (adding non-finance modules) show significantly higher ARPU compared to non-expanding customers.

**Cross-sell Paths**: Supply Chain and Platform modules are the most commonly cross-sold domains after the initial finance landing.

**Module Combination Analysis**: Built a heatmap of average ARPU by module pair to identify which combinations drive the highest customer value.

### Step 6: Churn Driver Analysis (Notebook 05)

Logistic regression model predicting renewal vs churn:

**Features used**: module_count, module_category_count, has_core_finance, has_advanced_finance, has_supply_chain, has_manufacturing, has_hr, has_platform, tenure_years, total_annual_value, overall_discount, monthly_avg_logins, monthly_avg_active_users, is_active, is_upsell_year, is_crosssell_year

**Key findings**:

Factors that increase renewal probability:
- Number of module categories adopted (strongest predictor)
- Monthly active usage (logins and active users)
- Having Advanced Finance modules (upsell)
- Customer tenure

Factors that increase churn probability:
- Single-module customers with low usage
- High discount rates (price-sensitive customers tend to be less sticky)

**Risk segmentation**: Customers segmented into High / Medium / Low risk tiers based on module count, activity, and tenure. High-risk customers (single module, inactive) showed substantially lower renewal rates than low-risk customers (3+ categories, active, 2+ year tenure).

## Recommendations

1. **Accelerate upsell in Year 2**: customers on Core Finance should be targeted for Advanced Finance upsell in their second year, as this is the strongest single predictor of long-term retention.

2. **Prioritise Supply Chain cross-sell**: after finance, Supply Chain modules show the most natural adoption path and the highest ARPU uplift when combined with finance.

3. **Track module_category_count as a health metric**: each additional module category is associated with higher renewal probability. This should be a KPI for Customer Success teams.

4. **Invest in activation, not just acquisition**: monthly active usage is a strong retention signal. Low-usage customers should receive proactive re-engagement before renewal conversations.

5. **Flag high-risk accounts early**: single-module, inactive customers should be surfaced to account managers 90 days before renewal for targeted intervention.

## Tools & Technologies

- **Databricks** (Free Edition) — Lakehouse platform for ETL, SQL analytics, and ML
- **SQL** — Data cleaning, transformation, window functions, multi-table joins
- **Python** — Statistical modelling and data visualisation
- **scikit-learn** — Logistic regression for churn prediction
- **matplotlib** — Charts and heatmaps

## About

Built by Enzo Chen as a portfolio project demonstrating end-to-end data analytics: data engineering (SQL cleaning, ETL pipeline design), business analysis (metric design, business logic filtering), statistical modelling (logistic regression), and strategic advisory (translating data findings into actionable business recommendations).

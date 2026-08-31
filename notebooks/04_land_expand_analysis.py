# Databricks notebook source

# COMMAND ----------

# MAGIC %md
# MAGIC # Land & Expand Analysis
# MAGIC **Objective:** Understand how customers evolve from initial purchase (Land) to upsell (advanced finance) and cross-sell (non-finance modules), and quantify the revenue impact of expansion.

# COMMAND ----------

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

# Load customer yearly profile
df = spark.table("workspace.demo.customer_yearly_profile").toPandas()
print(f"Total rows: {len(df):,}")
print(f"Years: {sorted(df['year'].unique())}")
print(f"Unique customers: {df['customer_id'].nunique():,}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Landing Pattern: What do customers buy first?

# COMMAND ----------

# First-year purchases only
first_year = df[df['customer_type'] == 'new'].copy()

# What modules do new customers land with?
landing_pattern = first_year.groupby('year').agg(
    total_new_customers=('customer_id', 'count'),
    pct_with_core_finance=('has_core_finance', 'mean'),
    pct_with_advanced_finance=('has_advanced_finance', 'mean'),
    pct_with_supply_chain=('has_supply_chain', 'mean'),
    pct_with_manufacturing=('has_manufacturing', 'mean'),
    pct_with_hr=('has_hr', 'mean'),
    pct_with_platform=('has_platform', 'mean'),
    avg_modules=('module_count', 'mean'),
    avg_annual_value=('total_annual_value', 'mean'),
).round(4)

print("=== New Customer Landing Pattern by Year ===")
print(landing_pattern.to_string())

# COMMAND ----------

# Visualize: what new customers land with
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

categories = ['Core\nFinance', 'Advanced\nFinance', 'Supply\nChain', 'Manufacturing', 'HR', 'Platform']
cols = ['pct_with_core_finance', 'pct_with_advanced_finance', 'pct_with_supply_chain',
        'pct_with_manufacturing', 'pct_with_hr', 'pct_with_platform']

# Latest year snapshot
latest_year = landing_pattern.index.max()
vals = [landing_pattern.loc[latest_year, c] for c in cols]
colors = ['#2c5f8a' if c == cols[0] else '#7bafd4' if c == cols[1] else '#b8d4e8' for c in cols]

ax1.bar(categories, vals, color=colors)
ax1.set_ylabel('% of New Customers')
ax1.set_title(f'Module Adoption at First Purchase ({latest_year})')
ax1.yaxis.set_major_formatter(mticker.PercentFormatter(1.0))

# Trend: avg modules at landing over time
ax2.plot(landing_pattern.index, landing_pattern['avg_modules'], 'o-', color='#2c5f8a', linewidth=2)
ax2.set_xlabel('Year')
ax2.set_ylabel('Avg Modules per New Customer')
ax2.set_title('Average Module Count at First Purchase')
ax2.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('/tmp/landing_pattern.png', dpi=150, bbox_inches='tight')
plt.show()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Expansion Funnel: Upsell & Cross-sell Rates

# COMMAND ----------

# Existing customers only
existing = df[df['customer_type'] == 'existing'].copy()

expand_by_year = existing.groupby('year').agg(
    existing_customers=('customer_id', 'count'),
    upsell_count=('is_upsell_year', 'sum'),
    upsell_rate=('is_upsell_year', 'mean'),
    crosssell_count=('is_crosssell_year', 'sum'),
    crosssell_rate=('is_crosssell_year', 'mean'),
    avg_annual_value=('total_annual_value', 'mean'),
).round(4)

print("=== Upsell & Cross-sell Rates by Year ===")
print(expand_by_year.to_string())

# COMMAND ----------

# Visualize: upsell vs cross-sell rates over time
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

ax1.plot(expand_by_year.index, expand_by_year['upsell_rate'], 's-', 
         color='#2c5f8a', linewidth=2, label='Upsell Rate')
ax1.plot(expand_by_year.index, expand_by_year['crosssell_rate'], 'o-', 
         color='#d4814a', linewidth=2, label='Cross-sell Rate')
ax1.set_xlabel('Year')
ax1.set_ylabel('Rate')
ax1.set_title('Upsell & Cross-sell Rates (Existing Customers)')
ax1.yaxis.set_major_formatter(mticker.PercentFormatter(1.0))
ax1.legend()
ax1.grid(True, alpha=0.3)

# Expansion impact on ARPU
expand_groups = existing.copy()
expand_groups['expand_type'] = 'No expansion'
expand_groups.loc[expand_groups['is_upsell_year'] == 1, 'expand_type'] = 'Upsell only'
expand_groups.loc[expand_groups['is_crosssell_year'] == 1, 'expand_type'] = 'Cross-sell only'
expand_groups.loc[
    (expand_groups['is_upsell_year'] == 1) & (expand_groups['is_crosssell_year'] == 1), 
    'expand_type'
] = 'Both'

arpu = expand_groups.groupby('expand_type')['total_annual_value'].mean().sort_values()
colors_arpu = {'No expansion': '#b8d4e8', 'Upsell only': '#7bafd4', 
               'Cross-sell only': '#d4814a', 'Both': '#2c5f8a'}
ax2.barh(arpu.index, arpu.values, color=[colors_arpu.get(x, '#999') for x in arpu.index])
ax2.set_xlabel('Average Annual Contract Value')
ax2.set_title('ARPU by Expansion Type')
ax2.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: f'{x:,.0f}'))

plt.tight_layout()
plt.savefig('/tmp/expansion_funnel.png', dpi=150, bbox_inches='tight')
plt.show()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Expansion Path Analysis: Which cross-sell paths are most common?

# COMMAND ----------

# For customers who cross-sold, what was added?
crosssell_customers = existing[existing['is_crosssell_year'] == 1].copy()

domain_cols = ['has_supply_chain', 'has_manufacturing', 'has_hr', 'has_platform', 
               'has_channel', 'has_industry_vertical']
domain_labels = ['Supply Chain', 'Manufacturing', 'HR', 'Platform', 'Channel', 'Industry Vertical']

crosssell_dist = {}
for col, label in zip(domain_cols, domain_labels):
    crosssell_dist[label] = crosssell_customers[col].mean()

crosssell_df = pd.Series(crosssell_dist).sort_values(ascending=True)

fig, ax = plt.subplots(figsize=(10, 5))
ax.barh(crosssell_df.index, crosssell_df.values, color='#d4814a')
ax.set_xlabel('% of Cross-sell Customers')
ax.set_title('Which Domains Are Most Commonly Cross-sold?')
ax.xaxis.set_major_formatter(mticker.PercentFormatter(1.0))
plt.tight_layout()
plt.savefig('/tmp/crosssell_paths.png', dpi=150, bbox_inches='tight')
plt.show()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Module Combination Heatmap: Which pairs drive highest ARPU?

# COMMAND ----------

# Build module pair matrix
module_bool_cols = ['has_core_finance', 'has_advanced_finance', 'has_supply_chain',
                    'has_manufacturing', 'has_hr', 'has_platform', 'has_channel']
module_labels_short = ['Core Fin', 'Adv Fin', 'Supply Chain', 'Mfg', 'HR', 'Platform', 'Channel']

# Average ARPU for customers with each pair
n = len(module_bool_cols)
heatmap_data = np.zeros((n, n))

for i in range(n):
    for j in range(n):
        mask = (existing[module_bool_cols[i]] == 1) & (existing[module_bool_cols[j]] == 1)
        if mask.sum() > 10:  # minimum sample
            heatmap_data[i][j] = existing.loc[mask, 'total_annual_value'].mean()
        else:
            heatmap_data[i][j] = np.nan

fig, ax = plt.subplots(figsize=(9, 7))
im = ax.imshow(heatmap_data, cmap='YlOrRd', aspect='auto')
ax.set_xticks(range(n))
ax.set_yticks(range(n))
ax.set_xticklabels(module_labels_short, rotation=45, ha='right')
ax.set_yticklabels(module_labels_short)
ax.set_title('Average ARPU by Module Combination (Existing Customers)')

# Add value labels
for i in range(n):
    for j in range(n):
        if not np.isnan(heatmap_data[i][j]):
            ax.text(j, i, f'{heatmap_data[i][j]:,.0f}', ha='center', va='center', fontsize=8)

plt.colorbar(im, label='Avg Annual Value')
plt.tight_layout()
plt.savefig('/tmp/module_heatmap.png', dpi=150, bbox_inches='tight')
plt.show()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Key Findings Summary

# COMMAND ----------

# Calculate key metrics for summary
total_new = len(first_year)
core_finance_landing = first_year['has_core_finance'].mean()
avg_landing_modules = first_year['module_count'].mean()
avg_upsell_rate = existing['is_upsell_year'].mean()
avg_crosssell_rate = existing['is_crosssell_year'].mean()

no_expand_arpu = existing[
    (existing['is_upsell_year'] == 0) & (existing['is_crosssell_year'] == 0)
]['total_annual_value'].mean()
both_arpu = existing[
    (existing['is_upsell_year'] == 1) & (existing['is_crosssell_year'] == 1)
]['total_annual_value'].mean()
arpu_uplift = (both_arpu / no_expand_arpu - 1) * 100 if no_expand_arpu > 0 else 0

print("=" * 60)
print("LAND & EXPAND ANALYSIS: KEY FINDINGS")
print("=" * 60)
print(f"\n1. LANDING PATTERN:")
print(f"   - {core_finance_landing:.1%} of new customers start with Core Finance")
print(f"   - Average {avg_landing_modules:.1f} modules at first purchase")
print(f"\n2. EXPANSION RATES (existing customers):")
print(f"   - Upsell rate (to Advanced Finance): {avg_upsell_rate:.1%}")
print(f"   - Cross-sell rate (adding non-finance): {avg_crosssell_rate:.1%}")
print(f"\n3. REVENUE IMPACT:")
print(f"   - No expansion ARPU: {no_expand_arpu:,.0f}")
print(f"   - Both upsell + cross-sell ARPU: {both_arpu:,.0f}")
print(f"   - Expansion uplift: +{arpu_uplift:.0f}%")
print(f"\n4. RECOMMENDATION:")
print(f"   - Focus sales efforts on upselling Core Finance customers")
print(f"     to Advanced Finance in year 2, then cross-selling")
print(f"     Supply Chain or Manufacturing modules in year 3+.")

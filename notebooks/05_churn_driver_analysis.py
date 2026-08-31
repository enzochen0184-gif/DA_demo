# Databricks notebook source

# COMMAND ----------

# MAGIC %md
# MAGIC # Churn Driver Analysis
# MAGIC **Objective:** Identify which factors most strongly predict customer renewal vs churn, and quantify the effect of module adoption, usage, and expansion on retention.

# COMMAND ----------

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score

# Load customer yearly profile
df = spark.table("workspace.demo.customer_yearly_profile").toPandas()

# Filter to rows where we know the renewal outcome
model_df = df[df['renewed_next_year'].notna()].copy()
model_df['renewed_next_year'] = model_df['renewed_next_year'].astype(int)
print(f"Rows with known renewal outcome: {len(model_df):,}")
print(f"Renewal rate: {model_df['renewed_next_year'].mean():.1%}")
print(f"Churn rate: {1 - model_df['renewed_next_year'].mean():.1%}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Renewal Rate by Key Dimensions

# COMMAND ----------

fig, axes = plt.subplots(2, 2, figsize=(14, 10))

# By module_category_count
grp = model_df.groupby('module_category_count')['renewed_next_year'].agg(['mean','count'])
grp = grp[grp['count'] >= 20]  # min sample
axes[0,0].bar(grp.index, grp['mean'], color='#2c5f8a')
axes[0,0].set_xlabel('Number of Module Categories')
axes[0,0].set_ylabel('Renewal Rate')
axes[0,0].set_title('Renewal Rate by Module Count')
axes[0,0].yaxis.set_major_formatter(mticker.PercentFormatter(1.0))
axes[0,0].axhline(y=model_df['renewed_next_year'].mean(), color='red', linestyle='--', alpha=0.5, label='Overall avg')
axes[0,0].legend()

# By tenure
grp = model_df.groupby('tenure_years')['renewed_next_year'].agg(['mean','count'])
grp = grp[grp['count'] >= 20]
axes[0,1].plot(grp.index, grp['mean'], 'o-', color='#2c5f8a', linewidth=2)
axes[0,1].set_xlabel('Tenure (Years)')
axes[0,1].set_ylabel('Renewal Rate')
axes[0,1].set_title('Renewal Rate by Customer Tenure')
axes[0,1].yaxis.set_major_formatter(mticker.PercentFormatter(1.0))
axes[0,1].grid(True, alpha=0.3)

# By has_advanced_finance
grp = model_df.groupby('has_advanced_finance')['renewed_next_year'].mean()
axes[1,0].bar(['No Advanced\nFinance', 'Has Advanced\nFinance'], grp.values, 
              color=['#b8d4e8', '#2c5f8a'])
axes[1,0].set_ylabel('Renewal Rate')
axes[1,0].set_title('Renewal Rate: Core vs Advanced Finance')
axes[1,0].yaxis.set_major_formatter(mticker.PercentFormatter(1.0))

# By is_active
grp = model_df.groupby('is_active')['renewed_next_year'].mean()
axes[1,1].bar(['Inactive', 'Active'], grp.values, color=['#d4814a', '#2c5f8a'])
axes[1,1].set_ylabel('Renewal Rate')
axes[1,1].set_title('Renewal Rate: Active vs Inactive Customers')
axes[1,1].yaxis.set_major_formatter(mticker.PercentFormatter(1.0))

plt.tight_layout()
plt.savefig('/tmp/renewal_dimensions.png', dpi=150, bbox_inches='tight')
plt.show()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Logistic Regression: Churn Driver Model

# COMMAND ----------

# Feature selection
features = [
    'module_count',
    'module_category_count',
    'has_core_finance',
    'has_advanced_finance',
    'has_supply_chain',
    'has_manufacturing',
    'has_hr',
    'has_platform',
    'tenure_years',
    'total_annual_value',
    'overall_discount',
    'monthly_avg_logins',
    'monthly_avg_active_users',
    'is_active',
    'is_upsell_year',
    'is_crosssell_year',
]

# Prepare data
X = model_df[features].copy()
y = model_df['renewed_next_year']

# Handle nulls
X = X.fillna(0)

# Remove infinite values
X = X.replace([np.inf, -np.inf], 0)

# Train/test split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Scale features for coefficient interpretability
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# Fit logistic regression
lr = LogisticRegression(max_iter=1000, random_state=42)
lr.fit(X_train_scaled, y_train)

# Model performance
y_pred = lr.predict(X_test_scaled)
y_prob = lr.predict_proba(X_test_scaled)[:, 1]
auc = roc_auc_score(y_test, y_prob)

print(f"Model AUC: {auc:.4f}")
print(f"\nClassification Report:")
print(classification_report(y_test, y_pred, target_names=['Churned', 'Renewed']))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Feature Importance: Odds Ratios

# COMMAND ----------

# Calculate odds ratios from coefficients
# For standardised coefficients, odds ratio = exp(coef) represents the 
# change in odds per 1 standard deviation increase in the feature
odds_ratios = np.exp(lr.coef_[0])
feature_importance = pd.DataFrame({
    'feature': features,
    'coefficient': lr.coef_[0],
    'odds_ratio': odds_ratios,
    'direction': ['Increases renewal' if c > 0 else 'Increases churn' for c in lr.coef_[0]]
}).sort_values('coefficient', ascending=True)

print("=== Odds Ratios (per 1 SD increase) ===")
print(feature_importance[['feature', 'odds_ratio', 'direction']].to_string(index=False))

# COMMAND ----------

# Visualize: coefficient plot
fig, ax = plt.subplots(figsize=(10, 8))

colors = ['#d4814a' if c < 0 else '#2c5f8a' for c in feature_importance['coefficient']]
ax.barh(feature_importance['feature'], feature_importance['coefficient'], color=colors)
ax.set_xlabel('Logistic Regression Coefficient (Standardised)')
ax.set_title('Churn Drivers: What Predicts Renewal vs Churn?')
ax.axvline(x=0, color='black', linewidth=0.5)

# Add legend
from matplotlib.patches import Patch
legend_elements = [Patch(facecolor='#2c5f8a', label='Increases renewal probability'),
                   Patch(facecolor='#d4814a', label='Increases churn probability')]
ax.legend(handles=legend_elements, loc='lower right')

plt.tight_layout()
plt.savefig('/tmp/churn_drivers.png', dpi=150, bbox_inches='tight')
plt.show()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Practical Insights: Renewal Rate by Risk Segments

# COMMAND ----------

# Create risk segments based on key drivers
model_df['risk_segment'] = 'Medium Risk'
model_df.loc[
    (model_df['module_category_count'] >= 3) & 
    (model_df['is_active'] == 1) & 
    (model_df['tenure_years'] >= 2), 
    'risk_segment'
] = 'Low Risk'
model_df.loc[
    (model_df['module_category_count'] <= 1) & 
    (model_df['is_active'] == 0), 
    'risk_segment'
] = 'High Risk'

risk_summary = model_df.groupby('risk_segment').agg(
    customer_count=('customer_id', 'count'),
    renewal_rate=('renewed_next_year', 'mean'),
    avg_annual_value=('total_annual_value', 'mean'),
    avg_modules=('module_count', 'mean'),
).round(4)

print("=== Customer Risk Segments ===")
print(risk_summary.to_string())

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

order = ['High Risk', 'Medium Risk', 'Low Risk']
colors_risk = {'High Risk': '#d4814a', 'Medium Risk': '#7bafd4', 'Low Risk': '#2c5f8a'}

# Renewal rate by segment
vals = [risk_summary.loc[s, 'renewal_rate'] if s in risk_summary.index else 0 for s in order]
ax1.bar(order, vals, color=[colors_risk[s] for s in order])
ax1.set_ylabel('Renewal Rate')
ax1.set_title('Renewal Rate by Risk Segment')
ax1.yaxis.set_major_formatter(mticker.PercentFormatter(1.0))

# Customer count by segment
vals = [risk_summary.loc[s, 'customer_count'] if s in risk_summary.index else 0 for s in order]
ax2.bar(order, vals, color=[colors_risk[s] for s in order])
ax2.set_ylabel('Number of Customers')
ax2.set_title('Customer Distribution by Risk Segment')

plt.tight_layout()
plt.savefig('/tmp/risk_segments.png', dpi=150, bbox_inches='tight')
plt.show()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Executive Summary & Recommendations

# COMMAND ----------

# Calculate key stats for summary
high_risk = risk_summary.loc['High Risk'] if 'High Risk' in risk_summary.index else None
low_risk = risk_summary.loc['Low Risk'] if 'Low Risk' in risk_summary.index else None

top_positive = feature_importance.sort_values('coefficient', ascending=False).head(3)
top_negative = feature_importance.sort_values('coefficient', ascending=True).head(3)

print("=" * 60)
print("CHURN DRIVER ANALYSIS: EXECUTIVE SUMMARY")
print("=" * 60)

print(f"\nMODEL PERFORMANCE: AUC = {auc:.3f}")

print(f"\nTOP 3 FACTORS THAT INCREASE RENEWAL:")
for _, row in top_positive.iterrows():
    print(f"  + {row['feature']}: odds ratio {row['odds_ratio']:.2f}x")

print(f"\nTOP 3 FACTORS THAT INCREASE CHURN:")
for _, row in top_negative.iterrows():
    print(f"  - {row['feature']}: odds ratio {row['odds_ratio']:.2f}x")

if high_risk is not None and low_risk is not None:
    print(f"\nRISK SEGMENTATION:")
    print(f"  High Risk: {high_risk['renewal_rate']:.1%} renewal rate, {int(high_risk['customer_count']):,} customers")
    print(f"  Low Risk:  {low_risk['renewal_rate']:.1%} renewal rate, {int(low_risk['customer_count']):,} customers")

print(f"\nRECOMMENDATIONS:")
print(f"  1. Prioritise re-engagement campaigns for single-module,")
print(f"     inactive customers (High Risk segment)")
print(f"  2. Accelerate cross-sell into Supply Chain or Manufacturing")
print(f"     for customers currently on Core Finance only")
print(f"  3. Track module_category_count as a leading indicator of")
print(f"     retention: each additional category is associated with")
print(f"     meaningfully higher renewal probability")
print(f"  4. Invest in onboarding and adoption programs to increase")
print(f"     monthly active usage, which is a strong retention signal")

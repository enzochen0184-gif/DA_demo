import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import os, random, string

np.random.seed(42)
random.seed(42)
OUT = '/home/claude/raw_data'
os.makedirs(OUT, exist_ok=True)

# ============================================================
# REFERENCE DATA
# ============================================================
INDUSTRIES = ['manufacturing','retail','finance','tech','construction',
              'real_estate','food_service','healthcare','logistics','other']
REGIONS = ['east','south','north','west','central']
PROVINCES = [f'P{str(i).zfill(2)}' for i in range(1,31)]
CITIES = [f'C{str(i).zfill(3)}' for i in range(1,101)]

PRODUCT_LINES = {
    'CloudERP': 'current',
    'SkyPlatform': 'current',
    'NovaStar': 'current',
    'NovaStarHR': 'current',
    'LegacyEAS': 'legacy',
    'LegacyHR': 'legacy',
    'LegacyK3': 'legacy',
}

EDITIONS = {
    'CloudERP': ['CE_Standard','CE_Enterprise_Public','CE_Enterprise_Private','CE_Enterprise_PrivateSub','CE_Flagship_Traditional','CE_Flagship_Suite'],
    'SkyPlatform': ['SP_Public','SP_Private','SP_PrivateSub'],
    'NovaStar': ['NS_Public','NS_Private','NS_PrivateSub'],
    'NovaStarHR': ['NH_Public','NH_Private','NH_PrivateSub'],
    'LegacyEAS': ['LE_Public','LE_Private','LE_PrivateSub'],
    'LegacyHR': ['LH_Public','LH_Private','LH_PrivateSub'],
    'LegacyK3': ['LK_Classic'],
}

DEPLOYMENT_MAP = {
    '_Public': 'public_cloud',
    '_Private': 'private_cloud',
    '_PrivateSub': 'private_cloud_subscription',
    '_Traditional': 'on_premise',
    '_Suite': 'private_cloud_subscription',
    '_Standard': 'public_cloud',
    '_Classic': 'on_premise',
}

def get_deployment(edition):
    for suffix, dep in DEPLOYMENT_MAP.items():
        if edition.endswith(suffix.replace('_','')):
            return dep
        if suffix.strip('_') in edition:
            return dep
    return 'private_cloud_subscription'

# Module definitions: (app_category, domain, module_name, base_list_price_range)
MODULES = [
    # Core Finance
    ('core_finance', 'finance', 'Financial_Accounting', (3000, 15000)),
    ('core_finance', 'finance', 'Bank_Integration', (2000, 10000)),
    # Advanced Finance
    ('advanced_finance', 'finance', 'Management_Accounting', (5000, 25000)),
    ('advanced_finance', 'finance', 'Tax_Management', (3000, 20000)),
    ('advanced_finance', 'finance', 'Treasury_Management', (8000, 30000)),
    ('advanced_finance', 'finance', 'Performance_Management', (10000, 40000)),
    # Supply Chain
    ('non_finance', 'supply_chain', 'Supply_Chain_Core', (5000, 20000)),
    ('non_finance', 'supply_chain', 'Supplier_Collaboration', (4000, 15000)),
    # Manufacturing
    ('non_finance', 'manufacturing', 'Manufacturing_Core', (6000, 25000)),
    ('non_finance', 'manufacturing', 'MES_Workshop', (3000, 12000)),
    ('non_finance', 'manufacturing', 'Barcode_Cloud', (1000, 5000)),
    # Platform / PaaS
    ('non_finance', 'platform', 'BOS_Platform', (2000, 10000)),
    ('non_finance', 'platform', 'Base_Platform', (2000, 8000)),
    ('non_finance', 'platform', 'Integration_Service', (5000, 30000)),
    ('non_finance', 'platform', 'Dev_Service', (3000, 20000)),
    ('non_finance', 'platform', 'Data_Service', (1000, 8000)),
    ('non_finance', 'platform', 'Workflow_Service', (2000, 12000)),
    ('non_finance', 'platform', 'AI_Service', (5000, 25000)),
    ('non_finance', 'platform', 'RPA_Service', (4000, 15000)),
    ('non_finance', 'platform', 'GPaaS_Foundation', (3000, 15000)),
    ('non_finance', 'platform', 'Lite_Apps', (500, 5000)),
    ('non_finance', 'platform', 'Value_Added_Service', (1000, 10000)),
    ('non_finance', 'platform', 'Middleware_Service', (5000, 20000)),
    ('non_finance', 'platform', 'Translation_Service', (2000, 8000)),
    ('non_finance', 'platform', 'Internationalization', (3000, 15000)),
    # HR
    ('non_finance', 'hr', 'Core_HR', (8000, 30000)),
    ('non_finance', 'hr', 'Payroll_Benefits', (5000, 20000)),
    ('non_finance', 'hr', 'Time_Attendance', (3000, 12000)),
    ('non_finance', 'hr', 'Talent_Acquisition', (4000, 15000)),
    ('non_finance', 'hr', 'Talent_Development', (5000, 18000)),
    ('non_finance', 'hr', 'Employee_Service', (2000, 8000)),
    ('non_finance', 'hr', 'Social_Insurance_Tax', (1000, 5000)),
    ('non_finance', 'hr', 'SOE_Personnel', (6000, 20000)),
    ('non_finance', 'hr', 'Performance_Goals', (4000, 15000)),
    # Channel
    ('non_finance', 'channel', 'Retail_Management', (8000, 30000)),
    ('non_finance', 'channel', 'Omnichannel_Marketing', (5000, 20000)),
    ('non_finance', 'channel', 'Retail_Cloud', (6000, 25000)),
    # Industry Verticals
    ('non_finance', 'industry_food', 'Restaurant_Cloud', (10000, 40000)),
    ('non_finance', 'industry_real_estate', 'RE_Procurement', (8000, 30000)),
    ('non_finance', 'industry_real_estate', 'RE_Cost', (5000, 20000)),
    ('non_finance', 'industry_real_estate', 'RE_Project', (6000, 25000)),
    ('non_finance', 'industry_construction', 'Construction_Project', (8000, 30000)),
    ('non_finance', 'industry_construction', 'Engineering_Project', (6000, 20000)),
    ('non_finance', 'industry_steel', 'Steel_Industry', (10000, 40000)),
    # Product
    ('non_finance', 'product', 'PLM_Cloud', (8000, 25000)),
    # Quality
    ('non_finance', 'quality', 'Quality_Cloud', (5000, 18000)),
    # Project
    ('non_finance', 'project', 'Project_Cloud', (6000, 22000)),
    # Collaboration
    ('non_finance', 'collaboration', 'Collaboration_Cloud', (3000, 12000)),
    ('non_finance', 'collaboration', 'Smart_Collaboration', (5000, 18000)),
    # Suite
    ('suite_mode', 'suite', 'Basic_Suite', (0, 0)),
    ('suite_mode', 'suite', 'Professional_Suite', (0, 0)),
    ('suite_mode', 'suite', 'Advanced_Suite', (0, 0)),
]

MODULE_NAMES = [m[2] for m in MODULES]
MODULE_LOOKUP = {m[2]: m for m in MODULES}

# Which modules go with which product lines (simplified)
PL_MODULE_WEIGHTS = {
    'CloudERP': ['Financial_Accounting','Bank_Integration','Management_Accounting','Tax_Management',
                 'Supply_Chain_Core','Manufacturing_Core','MES_Workshop','Barcode_Cloud','BOS_Platform',
                 'Base_Platform','Data_Service','Lite_Apps','PLM_Cloud','Retail_Management',
                 'Omnichannel_Marketing','Restaurant_Cloud','Quality_Cloud'],
    'SkyPlatform': ['Integration_Service','Dev_Service','Data_Service','Workflow_Service','AI_Service',
                    'RPA_Service','GPaaS_Foundation','Value_Added_Service','Middleware_Service',
                    'Translation_Service','Internationalization','Base_Platform','Lite_Apps'],
    'NovaStar': ['Financial_Accounting','Bank_Integration','Management_Accounting','Tax_Management',
                 'Treasury_Management','Performance_Management','Supply_Chain_Core','Supplier_Collaboration',
                 'Manufacturing_Core','Quality_Cloud','Project_Cloud','Collaboration_Cloud',
                 'Omnichannel_Marketing','RE_Procurement','RE_Cost','RE_Project',
                 'Construction_Project','Engineering_Project','Steel_Industry'],
    'NovaStarHR': ['Core_HR','Payroll_Benefits','Time_Attendance','Talent_Acquisition',
                   'Talent_Development','Employee_Service','Social_Insurance_Tax','SOE_Personnel','Performance_Goals'],
    'LegacyEAS': ['Financial_Accounting','Bank_Integration','Tax_Management','BOS_Platform',
                  'Supply_Chain_Core','Manufacturing_Core','RE_Procurement','Construction_Project'],
    'LegacyHR': ['Core_HR','Payroll_Benefits','Time_Attendance','Talent_Acquisition',
                 'Talent_Development','Employee_Service','Social_Insurance_Tax','Performance_Goals'],
    'LegacyK3': ['Financial_Accounting','Supply_Chain_Core','Manufacturing_Core','Restaurant_Cloud'],
}

print("Generating customers...")
# ============================================================
# TABLE 1: CUSTOMERS
# ============================================================
N_CUST = 20000
cust_ids = [f'CUS-{str(i).zfill(6)}' for i in range(1, N_CUST+1)]
reg_dates = pd.to_datetime('2012-01-01') + pd.to_timedelta(np.random.randint(0, 365*12, N_CUST), unit='D')
first_contract_offsets = np.random.randint(30, 365*3, N_CUST)
first_contract_dates = reg_dates + pd.to_timedelta(first_contract_offsets, unit='D')

customers = pd.DataFrame({
    'customer_id': cust_ids,
    'company_name': [f'Company_{i:05d}' for i in range(1, N_CUST+1)],
    'industry': np.random.choice(INDUSTRIES, N_CUST, p=[0.25,0.12,0.10,0.15,0.08,0.05,0.05,0.08,0.07,0.05]),
    'company_size': np.random.choice(['large','mid','small'], N_CUST, p=[0.15,0.35,0.50]),
    'region': np.random.choice(REGIONS, N_CUST, p=[0.30,0.25,0.20,0.10,0.15]),
    'province': np.random.choice(PROVINCES, N_CUST),
    'city': np.random.choice(CITIES, N_CUST),
    'registration_date': reg_dates,
    'first_contract_date': first_contract_dates,
    'customer_source': np.random.choice(['direct','partner','referral','online'], N_CUST, p=[0.35,0.30,0.15,0.20]),
    'is_internal_account': np.random.choice([True, False], N_CUST, p=[0.015, 0.985]),
    'credit_tier': np.random.choice(['A','B','C','D'], N_CUST, p=[0.30,0.40,0.20,0.10]),
})

# Anomalies for customers
# 1. first_contract_date before registration_date
idx = np.random.choice(N_CUST, 200, replace=False)
customers.loc[idx, 'first_contract_date'] = customers.loc[idx, 'registration_date'] - pd.to_timedelta(np.random.randint(30, 365, 200), unit='D')

# 2. Duplicate customer_ids
dup_idx = np.random.choice(range(500, N_CUST), 80, replace=False)
for i in dup_idx:
    customers.loc[i, 'customer_id'] = customers.loc[np.random.randint(0,500), 'customer_id']

# 3. Null industry
null_idx = np.random.choice(N_CUST, 50, replace=False)
customers.loc[null_idx, 'industry'] = np.nan

# 4. Future registration dates
fut_idx = np.random.choice(N_CUST, 30, replace=False)
customers.loc[fut_idx, 'registration_date'] = pd.to_datetime('2027-06-15') + pd.to_timedelta(np.random.randint(0, 365, 30), unit='D')

# 5. Test accounts
test_idx = np.random.choice(N_CUST, 100, replace=False)
customers.loc[test_idx, 'company_name'] = [f'Test_Company_{i}' for i in range(100)]
customers.loc[test_idx, 'is_internal_account'] = False  # not flagged, needs business logic to catch

customers.to_csv(f'{OUT}/customers.csv', index=False)
print(f"  customers: {len(customers)} rows")

print("Generating contracts...")
# ============================================================
# TABLE 2: CONTRACTS
# ============================================================
contracts_list = []
con_id = 0
valid_cust_ids = customers['customer_id'].unique()

for cust_id in valid_cust_ids:
    cust_row = customers[customers['customer_id'] == cust_id].iloc[0]
    first_date = cust_row['first_contract_date']
    if pd.isna(first_date) or first_date > pd.Timestamp('2025-12-31'):
        continue
    
    start_year = max(first_date.year, 2015)
    # Choose primary product line
    pl = np.random.choice(list(PRODUCT_LINES.keys()), p=[0.35,0.10,0.15,0.08,0.12,0.10,0.10])
    editions = EDITIONS[pl]
    edition = np.random.choice(editions)
    
    # Number of years active (1 to however many years until 2025)
    max_years = min(2025 - start_year + 1, 8)
    if max_years <= 0:
        max_years = 1
    n_years = np.random.randint(1, max_years + 1)
    
    parent_id = None
    for seq in range(1, n_years + 1):
        con_id += 1
        yr = start_year + seq - 1
        if yr > 2025:
            break
        sign_d = pd.Timestamp(f'{yr}-01-01') + pd.to_timedelta(np.random.randint(0, 300), unit='D')
        eff_d = sign_d + pd.to_timedelta(np.random.randint(0, 30), unit='D')
        duration = np.random.choice([12, 24, 36], p=[0.6, 0.25, 0.15])
        exp_d = eff_d + pd.DateOffset(months=duration)
        
        list_price = np.random.lognormal(mean=10.5, sigma=1.2)
        discount = np.random.uniform(0.3, 1.0)
        actual_price = list_price * discount
        
        cid = f'CON-{str(con_id).zfill(6)}'
        contracts_list.append({
            'contract_id': cid,
            'customer_id': cust_id,
            'parent_contract_id': parent_id,
            'contract_sequence': seq,
            'sign_date': sign_d,
            'effective_date': eff_d,
            'expiry_date': exp_d,
            'product_line': pl,
            'product_edition': edition,
            'deployment_type': get_deployment(edition),
            'contract_type': np.random.choice(['subscription','perpetual','trial','poc'], p=[0.88,0.05,0.04,0.03]),
            'payment_terms': np.random.choice(['annual','quarterly','monthly','one_time'], p=[0.60,0.20,0.15,0.05]),
            'total_list_price': round(list_price, 2),
            'total_actual_price': round(actual_price, 2),
            'currency': np.random.choice(['CNY','USD','SGD'], p=[0.97,0.02,0.01]),
            'sales_rep_id': f'REP-{np.random.randint(1,200):03d}',
            'sales_channel': np.random.choice(['direct','partner'], p=[0.6,0.4]),
            'approval_status': np.random.choice(['approved','pending','rejected'], p=[0.92,0.05,0.03]),
        })
        parent_id = cid
    
    if con_id >= 70000:
        break

contracts = pd.DataFrame(contracts_list)

# Anomalies for contracts
n_con = len(contracts)
print(f"  contracts base: {n_con} rows")

# 1. Negative actual price
idx = np.random.choice(n_con, min(300, n_con), replace=False)
contracts.loc[idx, 'total_actual_price'] = -abs(contracts.loc[idx, 'total_actual_price'])

# 2. List price = 0 but actual > 0
idx = np.random.choice(n_con, min(150, n_con), replace=False)
contracts.loc[idx, 'total_list_price'] = 0

# 3. effective_date > expiry_date
idx = np.random.choice(n_con, min(200, n_con), replace=False)
contracts.loc[idx, 'expiry_date'] = contracts.loc[idx, 'effective_date'] - pd.to_timedelta(np.random.randint(30, 365, len(idx)), unit='D')

# 4. Orphan customer_ids
idx = np.random.choice(n_con, min(100, n_con), replace=False)
contracts.loc[idx, 'customer_id'] = [f'CUS-{np.random.randint(90000,99999):06d}' for _ in range(len(idx))]

# 5. Duplicate contract_ids
dup_idx = np.random.choice(range(1000, n_con), min(80, n_con-1000), replace=False)
for i in dup_idx:
    contracts.loc[i, 'contract_id'] = contracts.loc[np.random.randint(0,1000), 'contract_id']

# 6. actual > list × 2
idx = np.random.choice(n_con, min(50, n_con), replace=False)
contracts.loc[idx, 'total_actual_price'] = contracts.loc[idx, 'total_list_price'] * np.random.uniform(2.1, 5.0, len(idx))

contracts.to_csv(f'{OUT}/contracts.csv', index=False)
print(f"  contracts: {len(contracts)} rows")

print("Generating contract_modules...")
# ============================================================
# TABLE 3: CONTRACT_MODULES
# ============================================================
modules_list = []
line_id = 0
for _, con in contracts.iterrows():
    pl = con['product_line']
    if pl not in PL_MODULE_WEIGHTS:
        continue
    available = PL_MODULE_WEIGHTS[pl]
    
    # Land: always start with core finance for CloudERP/NovaStar/LegacyEAS/LegacyK3
    if pl in ['CloudERP','NovaStar','LegacyEAS','LegacyK3']:
        # Core finance always included
        n_extra = np.random.choice([0,1,2,3,4,5], p=[0.05,0.20,0.30,0.25,0.15,0.05])
        selected = ['Financial_Accounting']
        if con['contract_sequence'] > 1 and np.random.random() < 0.4:
            # Upsell: add advanced finance
            adv = [m for m in available if MODULE_LOOKUP.get(m, (None,))[0] == 'advanced_finance']
            if adv:
                selected.extend(np.random.choice(adv, min(len(adv), np.random.randint(1,3)), replace=False).tolist())
        if con['contract_sequence'] > 1 and np.random.random() < 0.35:
            # Cross-sell: add non-finance
            non_fin = [m for m in available if m not in selected and MODULE_LOOKUP.get(m, (None,))[0] == 'non_finance']
            if non_fin:
                selected.extend(np.random.choice(non_fin, min(len(non_fin), n_extra), replace=False).tolist())
        else:
            extras = [m for m in available if m not in selected]
            if extras and n_extra > 0:
                selected.extend(np.random.choice(extras, min(len(extras), n_extra), replace=False).tolist())
    else:
        n_mods = np.random.randint(1, min(6, len(available)+1))
        selected = np.random.choice(available, n_mods, replace=False).tolist()
    
    for mod_name in selected:
        line_id += 1
        mod_info = MODULE_LOOKUP.get(mod_name, ('non_finance','other',mod_name,(1000,10000)))
        price_range = mod_info[3]
        unit_list = np.random.uniform(price_range[0], price_range[1]) if price_range[1] > 0 else 0
        discount = np.random.uniform(0.3, 1.0)
        unit_actual = unit_list * discount
        qty = np.random.choice([1,2,3,4,5,6], p=[0.40,0.25,0.15,0.10,0.05,0.05])
        is_bundled = mod_info[0] == 'suite_mode'
        
        modules_list.append({
            'line_id': f'LIN-{str(line_id).zfill(7)}',
            'contract_id': con['contract_id'],
            'app_category': mod_info[0],
            'domain': mod_info[1],
            'module_name': mod_name,
            'unit_list_price': round(unit_list, 2),
            'unit_actual_price': round(unit_actual, 2),
            'quantity': qty,
            'line_list_total': round(unit_list * qty, 2),
            'line_actual_total': round(unit_actual * qty, 2),
            'is_bundled': is_bundled,
            'is_first_purchase': con['contract_sequence'] == 1,
        })

modules = pd.DataFrame(modules_list)
n_mod = len(modules)
print(f"  contract_modules base: {n_mod} rows")

# Anomalies
# 1. line_list_total != unit_list_price * quantity
idx = np.random.choice(n_mod, min(1500, n_mod), replace=False)
modules.loc[idx, 'line_list_total'] = modules.loc[idx, 'line_list_total'] * np.random.uniform(0.5, 1.8, len(idx))

# 2. quantity = 0 but amount > 0
idx = np.random.choice(n_mod, min(800, n_mod), replace=False)
modules.loc[idx, 'quantity'] = 0

# 3. Negative unit_list_price
idx = np.random.choice(n_mod, min(400, n_mod), replace=False)
modules.loc[idx, 'unit_list_price'] = -abs(modules.loc[idx, 'unit_list_price'])

# 4. Null/fake module names
idx = np.random.choice(n_mod, min(300, n_mod), replace=False)
modules.loc[idx[:100], 'module_name'] = np.nan
modules.loc[idx[100:200], 'module_name'] = 'N/A'
modules.loc[idx[200:], 'module_name'] = 'TBD'

# 5. Orphan contract_ids
idx = np.random.choice(n_mod, min(200, n_mod), replace=False)
modules.loc[idx, 'contract_id'] = [f'CON-{np.random.randint(900000,999999):06d}' for _ in range(len(idx))]

# 6. Category mismatch
idx = np.random.choice(n_mod, min(500, n_mod), replace=False)
modules.loc[idx, 'app_category'] = 'core_finance'
modules.loc[idx, 'domain'] = np.random.choice(['manufacturing','hr','channel'], len(idx))

# 7. Duplicate rows
dup_idx = np.random.choice(n_mod, min(100, n_mod), replace=False)
dups = modules.loc[dup_idx].copy()
modules = pd.concat([modules, dups], ignore_index=True)

modules.to_csv(f'{OUT}/contract_modules.csv', index=False)
print(f"  contract_modules: {len(modules)} rows")

print("Generating licensed_users...")
# ============================================================
# TABLE 4: LICENSED_USERS
# ============================================================
users_list = []
lic_id = 0
# Sample ~60% of contract_modules rows to have user licenses
sample_idx = np.random.choice(len(modules), int(len(modules)*0.4), replace=False)
for i in sample_idx:
    row = modules.iloc[i]
    lic_id += 1
    user_count = np.random.choice([1,5,10,20,50,100,200,500], p=[0.10,0.20,0.25,0.20,0.12,0.08,0.03,0.02])
    user_list_p = np.random.uniform(50, 2000)
    user_disc = np.random.uniform(0.4, 1.0)
    users_list.append({
        'license_id': f'LIC-{str(lic_id).zfill(6)}',
        'contract_id': row['contract_id'],
        'module_name': row['module_name'],
        'user_type': np.random.choice(['named','concurrent'], p=[0.7,0.3]),
        'licensed_user_count': user_count,
        'unit_user_list_price': round(user_list_p, 2),
        'unit_user_actual_price': round(user_list_p * user_disc, 2),
        'user_line_total': round(user_list_p * user_disc * user_count, 2),
    })

licensed_users = pd.DataFrame(users_list)
n_lic = len(licensed_users)
print(f"  licensed_users base: {n_lic} rows")

# Anomalies
idx = np.random.choice(n_lic, min(500, n_lic), replace=False)
licensed_users.loc[idx, 'licensed_user_count'] = np.random.choice([-1, -5, 0], len(idx))

idx = np.random.choice(n_lic, min(300, n_lic), replace=False)
licensed_users.loc[idx, 'user_line_total'] = licensed_users.loc[idx, 'user_line_total'] * np.random.uniform(0.3, 2.5, len(idx))

idx = np.random.choice(n_lic, min(200, n_lic), replace=False)
licensed_users.loc[idx, 'contract_id'] = [f'CON-{np.random.randint(900000,999999):06d}' for _ in range(len(idx))]

licensed_users.to_csv(f'{OUT}/licensed_users.csv', index=False)
print(f"  licensed_users: {len(licensed_users)} rows")

print("Generating usage_activity...")
# ============================================================
# TABLE 5: USAGE_ACTIVITY
# ============================================================
usage_list = []
act_id = 0
# For each valid contract, generate monthly usage
sampled_contracts = contracts.sample(min(15000, len(contracts)))
for _, con in sampled_contracts.iterrows():
    eff = con['effective_date']
    exp = con['expiry_date']
    if pd.isna(eff) or pd.isna(exp):
        continue
    try:
        months = pd.date_range(start=eff, end=min(exp, pd.Timestamp('2025-12-31')), freq='MS')
    except:
        continue
    if len(months) == 0:
        continue
    months = months[:24]  # cap at 24 months
    
    pl = con['product_line']
    if pl not in PL_MODULE_WEIGHTS:
        continue
    mods = np.random.choice(PL_MODULE_WEIGHTS[pl], min(2, len(PL_MODULE_WEIGHTS[pl])), replace=False)
    
    for month in months:
        for mod in mods:
            act_id += 1
            logins = max(0, int(np.random.lognormal(3, 1.5)))
            users = max(0, int(logins * np.random.uniform(0.1, 0.5)))
            usage_list.append({
                'activity_id': f'ACT-{str(act_id).zfill(7)}',
                'customer_id': con['customer_id'],
                'contract_id': con['contract_id'],
                'product_edition': con['product_edition'],
                'module_name': mod,
                'activity_month': month,
                'monthly_logins': logins,
                'active_user_count': users,
                'feature_api_calls': max(0, int(np.random.lognormal(5, 2))),
                'data_volume_mb': round(max(0, np.random.lognormal(3, 1.5)), 2),
            })
            if act_id >= 400000:
                break
        if act_id >= 400000:
            break
    if act_id >= 400000:
        break

usage = pd.DataFrame(usage_list)
n_usage = len(usage)
print(f"  usage_activity base: {n_usage} rows")

# Anomalies
idx = np.random.choice(n_usage, min(2000, n_usage), replace=False)
usage.loc[idx, 'monthly_logins'] = -np.random.randint(1, 100, len(idx))

idx = np.random.choice(n_usage, min(1000, n_usage), replace=False)
usage.loc[idx, 'activity_month'] = usage.loc[idx, 'activity_month'] - pd.to_timedelta(np.random.randint(60, 365, len(idx)), unit='D')

idx = np.random.choice(n_usage, min(300, n_usage), replace=False)
dups = usage.loc[idx].copy()
usage = pd.concat([usage, dups], ignore_index=True)

# No logins but high API calls
idx = np.random.choice(n_usage, min(3000, n_usage), replace=False)
usage.loc[idx, 'monthly_logins'] = 0
usage.loc[idx, 'feature_api_calls'] = np.random.randint(1000, 50000, len(idx))

usage.to_csv(f'{OUT}/usage_activity.csv', index=False)
print(f"  usage_activity: {len(usage)} rows")

print("Generating renewals...")
# ============================================================
# TABLE 6: RENEWALS
# ============================================================
renewals_list = []
ren_id = 0
sub_contracts = contracts[contracts['contract_type'] == 'subscription']
for _, con in sub_contracts.iterrows():
    exp = con['expiry_date']
    if pd.isna(exp):
        continue
    ren_id += 1
    renewed = np.random.choice(['yes','no'], p=[0.75,0.25])
    prev_val = abs(con['total_actual_price'])
    if renewed == 'yes':
        change = np.random.uniform(-0.1, 0.2)
        ren_val = prev_val * (1 + change)
        reason = None
        new_cid = f'CON-{np.random.randint(100000,899999):06d}'
    else:
        ren_val = 0
        reason = np.random.choice(['price','competitor','no_budget','product_fit','merged','closed'],
                                  p=[0.25,0.20,0.20,0.15,0.10,0.10])
        new_cid = None
    
    due_date = exp
    decision_date = due_date - pd.to_timedelta(np.random.randint(0, 60), unit='D')
    
    renewals_list.append({
        'renewal_id': f'REN-{str(ren_id).zfill(6)}',
        'original_contract_id': con['contract_id'],
        'new_contract_id': new_cid,
        'customer_id': con['customer_id'],
        'renewal_due_date': due_date,
        'renewal_decision_date': decision_date,
        'renewed': renewed,
        'previous_annual_value': round(prev_val, 2),
        'renewal_annual_value': round(ren_val, 2),
        'price_change_pct': round(change if renewed == 'yes' else 0, 4),
        'churn_reason': reason,
    })
    if ren_id >= 35000:
        break

renewals = pd.DataFrame(renewals_list)
n_ren = len(renewals)
print(f"  renewals base: {n_ren} rows")

# Anomalies
idx = np.random.choice(n_ren, min(200, n_ren), replace=False)
renewals.loc[idx, 'renewed'] = 'yes'
renewals.loc[idx, 'renewal_annual_value'] = 0

idx = np.random.choice(n_ren, min(150, n_ren), replace=False)
renewals.loc[idx, 'renewed'] = 'no'
renewals.loc[idx, 'new_contract_id'] = [f'CON-{np.random.randint(100000,899999):06d}' for _ in range(len(idx))]

idx = np.random.choice(n_ren, min(100, n_ren), replace=False)
renewals.loc[idx, 'renewal_decision_date'] = renewals.loc[idx, 'renewal_due_date'] - pd.to_timedelta(np.random.randint(200, 400, len(idx)), unit='D')

idx = np.random.choice(n_ren, min(80, n_ren), replace=False)
renewals.loc[idx, 'previous_annual_value'] = -abs(renewals.loc[idx, 'previous_annual_value'])

idx = np.random.choice(n_ren, min(50, n_ren), replace=False)
renewals.loc[idx, 'original_contract_id'] = [f'CON-{np.random.randint(900000,999999):06d}' for _ in range(len(idx))]

renewals.to_csv(f'{OUT}/renewals.csv', index=False)
print(f"  renewals: {len(renewals)} rows")

# ============================================================
# SUMMARY
# ============================================================
print("\n=== GENERATION COMPLETE ===")
total = len(customers) + len(contracts) + len(modules) + len(licensed_users) + len(usage) + len(renewals)
print(f"Total rows: {total:,}")
for name, df in [('customers', customers), ('contracts', contracts), 
                  ('contract_modules', modules), ('licensed_users', licensed_users),
                  ('usage_activity', usage), ('renewals', renewals)]:
    size_mb = os.path.getsize(f'{OUT}/{name}.csv') / 1024 / 1024
    print(f"  {name}: {len(df):,} rows, {len(df.columns)} cols, {size_mb:.1f} MB")

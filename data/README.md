# Data

The raw data for this project is generated using `generate_raw_data.py`. This script creates ~860,000 rows of synthetic data modelled on real enterprise SaaS operations.

## How to generate

```bash
pip install numpy pandas
python generate_raw_data.py
```

This produces 6 CSV files in a `raw_data/` directory:

| File | Rows | Size |
|---|---|---|
| customers.csv | 20,000 | ~1.8 MB |
| contracts.csv | 68,957 | ~11.2 MB |
| contract_modules.csv | 241,952 | ~25.4 MB |
| licensed_users.csv | 96,780 | ~6.7 MB |
| usage_activity.csv | 400,300 | ~34.8 MB |
| renewals.csv | 35,000 | ~3.1 MB |

Upload these CSVs to Databricks and run the notebooks in order (01 through 05).

## Intentional data quality issues

The generated data includes realistic data quality problems for cleaning demonstration:

- ~7% of records have data engineering issues (duplicates, negatives, orphan keys, calculation mismatches, future dates, string nulls, category mismatches)
- ~5% of records require business logic exclusion (perpetual contracts, trials, test accounts, short-term deals, non-standard currency)
- ~2% of issues are only discoverable through cross-table joins (usage before contract start, active users exceeding licensed count, contradictory renewal flags)

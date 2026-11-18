# Financial Data Migration and Validation Pipeline

Python + SQL pipeline that migrates a messy legacy CSV of financial transactions into PostgreSQL,
rejects invalid records with a documented reason, and proves afterwards that the database matches the source.

## What it does
1. **Extract** the CSV as raw text (no type guessing)
2. **Transform**: trim spaces, normalize CR/DR to CREDIT/DEBIT, parse dates and amounts
3. **Validate** against data quality rules (missing values, invalid dates/amounts/types/currencies, duplicates, out-of-range amounts)
4. **Load** valid rows into PostgreSQL in one transaction (safe to re-run), and log rejected rows with reasons
5. **Reconcile**: row counts, control totals per currency/type, and field-by-field comparison
6. **Report**: Markdown reconciliation report

## Results on the sample data (synthetic)
514 rows read, 427 loaded, 87 rejected. See `docs/sample_report.md`.

## How to run
pip install -r requirements.txt
python tools/generate_sample_data.py
# create a database named migration_demo, then run sql/schema.sql in it
python load_to_postgres.py
python run_reconciliation.py

## Design decisions
- Money uses Decimal in Python and NUMERIC(14,2) in PostgreSQL, never float
- Amounts with more than 2 decimals are rejected, not rounded
- Database constraints (primary key, foreign key, CHECK) act as a second line of defence
- Loads use ON CONFLICT DO NOTHING, so re-running does not create duplicates
- Slash dates are read day-first (03/04/2025 = 3 April)

## Possible improvements
Quarantine all copies of conflicting duplicates, add automated tests, support chunked reading of very large files.
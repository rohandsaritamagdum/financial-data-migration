import getpass
import os

import pandas as pd
import psycopg2
from psycopg2.extras import Json, execute_values

from validation import validate_rows

SOURCE = "data/legacy_transactions.csv"

# Never type your password into code that goes to GitHub.
password = os.environ.get("DB_PASSWORD") or getpass.getpass("PostgreSQL password: ")

# 1. Read and validate (Steps 1-3, now reused from validation.py)
df = pd.read_csv(SOURCE, dtype=str, keep_default_na=False)
valid, rejected = validate_rows(df)
print(f"Rows read: {len(df)} | valid: {len(valid)} | rejected: {len(rejected)}")

# 2. Connect to PostgreSQL
conn = psycopg2.connect(
    host="localhost", port=5432, dbname="migration_demo", user="postgres", password=password
)

try:
    # "with conn" = one transaction: it commits if everything works,
    # and rolls back EVERYTHING if any line fails.
    with conn:
        with conn.cursor() as cur:

            # 3. Log the start of this run
            cur.execute(
                "INSERT INTO migration_runs (source_file, rows_read) VALUES (%s, %s) RETURNING run_id",
                (SOURCE, len(df)),
            )
            run_id = cur.fetchone()[0]
            print(f"Started run {run_id}")

            # 4. Accounts first (transactions point to them)
            accounts = {}
            for r in valid:
                accounts.setdefault(r["account_no"], (r["account_no"], r["customer_name"], r["branch_code"]))
            if accounts:
                execute_values(
                    cur,
                    "INSERT INTO accounts (account_no, customer_name, branch_code) VALUES %s "
                    "ON CONFLICT (account_no) DO NOTHING",
                    list(accounts.values()),
                )

            # 5. Transactions. ON CONFLICT DO NOTHING makes re-running safe.
            inserted = []
            if valid:
                rows = [
                    (r["txn_id"], r["account_no"], r["txn_date"], r["txn_type"],
                     r["amount"], r["currency"], run_id)
                    for r in valid
                ]
                inserted = execute_values(
                    cur,
                    "INSERT INTO transactions (txn_id, account_no, txn_date, txn_type, amount, "
                    "currency, migrated_run_id) VALUES %s ON CONFLICT (txn_id) DO NOTHING "
                    "RETURNING txn_id",
                    rows,
                    fetch=True,
                )

            # 6. Rejected rows are kept, with the reasons
            if rejected:
                rejected_rows = [
                    (run_id, r["row"], r["txn_id"] or None, r["codes"], r["details"], Json(r["raw"]))
                    for r in rejected
                ]
                execute_values(
                    cur,
                    "INSERT INTO rejected_records (run_id, source_row, txn_id, rules, details, raw_record) "
                    "VALUES %s",
                    rejected_rows,
                )

            # 7. Close the run record
            loaded = len(inserted)
            cur.execute(
                "UPDATE migration_runs SET finished_at = now(), status = %s, rows_valid = %s, "
                "rows_rejected = %s, rows_loaded = %s, rows_already_present = %s WHERE run_id = %s",
                ("COMPLETED", len(valid), len(rejected), loaded, len(valid) - loaded, run_id),
            )

    print(f"Loaded (new): {loaded} | already in database: {len(valid) - loaded}")
    print("Done. Check the tables in pgAdmin.")
finally:
    conn.close()
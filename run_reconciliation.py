import getpass
import os
import sys

import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor

from reconcile import compare
from validation import validate_rows
from report import write_report

SOURCE = "data/legacy_transactions.csv"
password = os.environ.get("DB_PASSWORD") or getpass.getpass("PostgreSQL password: ")

# What we MEANT to load
df = pd.read_csv(SOURCE, dtype=str, keep_default_na=False)
valid, rejected = validate_rows(df)

# What is ACTUALLY in the database
conn = psycopg2.connect(
    host="localhost", port=5432, dbname="migration_demo", user="postgres", password=password
)
try:
    with conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            "SELECT txn_id, account_no, txn_date, txn_type, amount, currency "
            "FROM transactions WHERE txn_id = ANY(%s)",
            ([r["txn_id"] for r in valid],),
        )
        target = [dict(row) for row in cur.fetchall()]
finally:
    conn.close()

missing, mismatches, totals_table = compare(valid, target)
all_passed = True

# ---- Check 1: row accounting ----
ok = len(df) == len(valid) + len(rejected)
all_passed &= ok
print("CHECK 1  Row accounting")
print(f"  read {len(df)} = valid {len(valid)} + rejected {len(rejected)}  ->  {'PASS' if ok else 'FAIL'}")

# ---- Check 2: nothing missing ----
ok = not missing
all_passed &= ok
print("\nCHECK 2  Every valid row reached the database")
print(f"  expected {len(valid)}, found {len(valid) - len(missing)}  ->  {'PASS' if ok else 'FAIL'}")
for txn_id in missing:
    print(f"    missing: {txn_id}")

# ---- Check 3: control totals ----
ok = all(row["match"] for row in totals_table)
all_passed &= ok
print("\nCHECK 3  Control totals (count and sum per currency/type)")
print(f"  {'Currency':<9}{'Type':<8}{'Source':>18}{'Database':>18}  Match")
for row in totals_table:
    src = f"{row['source_count']} / {row['source_sum']:.2f}"
    tgt = f"{row['target_count']} / {row['target_sum']:.2f}"
    print(f"  {row['currency']:<9}{row['type']:<8}{src:>18}{tgt:>18}  {'yes' if row['match'] else 'NO'}")
print(f"  ->  {'PASS' if ok else 'FAIL'}")

# ---- Check 4: field by field ----
ok = not mismatches
all_passed &= ok
print("\nCHECK 4  Field-by-field comparison")
print(f"  {len(mismatches)} difference(s)  ->  {'PASS' if ok else 'FAIL'}")
for txn_id, field, source_value, target_value in mismatches:
    print(f"    {txn_id}: {field} was {source_value} in the file but {target_value} in the database")

os.makedirs("reports", exist_ok=True)
write_report("reports/reconciliation_report.md", source=SOURCE, rows_read=len(df), valid=valid,
             rejected=rejected, missing=missing, mismatches=mismatches,
             totals_table=totals_table, passed=all_passed)
print("\nReport written to reports/reconciliation_report.md")

print("\nRECONCILIATION", "PASSED" if all_passed else "FAILED")
sys.exit(0 if all_passed else 1)
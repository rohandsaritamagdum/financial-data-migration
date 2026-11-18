from collections import Counter
from datetime import date

import pandas as pd

from cleaning import clean_text, normalize_type, parse_amount, parse_date

ALLOWED_CURRENCIES = ["USD", "EUR", "GBP", "INR"]
VALID_TYPES = ["CREDIT", "DEBIT"]

df = pd.read_csv("data/legacy_transactions.csv", dtype=str, keep_default_na=False)

valid_rows = []
rejected_rows = []
seen_ids = {}  # txn_id -> the row number where we first saw it

for number, row in df.iterrows():
    row_number = number + 1          # humans count from 1
    reasons = []                     # every rule this row breaks

    account = clean_text(row["ACCT_NO"]).upper()
    txn_id = clean_text(row["TXN_ID"]).upper()
    txn_date = parse_date(row["TXN_DATE"])
    txn_type = normalize_type(row["TXN_TYPE"])
    amount = parse_amount(row["AMOUNT"])
    currency = clean_text(row["CURRENCY"]).upper()

    # Rule: required fields must not be blank
    if account == "":
        reasons.append("MISSING_ACCOUNT")

    # Rule: date must be a real date, and not in the future
    if clean_text(row["TXN_DATE"]) == "":
        reasons.append("MISSING_DATE")
    elif txn_date is None:
        reasons.append("INVALID_DATE")
    elif txn_date > date.today():
        reasons.append("FUTURE_DATE")

    # Rule: type must be CREDIT or DEBIT
    if txn_type not in VALID_TYPES:
        reasons.append("INVALID_TXN_TYPE")

    # Rule: amount must be a number greater than zero
    if clean_text(row["AMOUNT"]) == "":
        reasons.append("MISSING_AMOUNT")
    elif amount is None:
        reasons.append("INVALID_AMOUNT")
    elif amount <= 0:
        reasons.append("NON_POSITIVE_AMOUNT")

    # Rule: currency must be on the allowed list
    if currency not in ALLOWED_CURRENCIES:
        reasons.append("INVALID_CURRENCY")

    # Rule: each transaction id may appear only once
    if txn_id in seen_ids:
        reasons.append(f"DUPLICATE_TXN_ID (first seen in row {seen_ids[txn_id]})")
    else:
        seen_ids[txn_id] = row_number

    if reasons:
        rejected_rows.append({"row": row_number, "txn_id": txn_id, "reasons": "; ".join(reasons)})
    else:
        valid_rows.append(row_number)

# ---- Report ----
print(f"Rows read:  {len(df)}")
print(f"Valid:      {len(valid_rows)}   (rows {valid_rows})")
print(f"Rejected:   {len(rejected_rows)}")
print()

for item in rejected_rows:
    print(f"  Row {item['row']} ({item['txn_id'] or 'no id'}): {item['reasons']}")

print()
counts = Counter(r.split(" ")[0] for item in rejected_rows for r in item["reasons"].split("; "))
for reason, count in sorted(counts.items()):
    print(f"  {reason}: {count}")

# Safety check: nothing may disappear
assert len(df) == len(valid_rows) + len(rejected_rows), "Some rows were lost!"
print("\nCheck passed: rows read = valid + rejected")

pd.DataFrame(rejected_rows).to_csv("data/rejected_records.csv", index=False)
print("Wrote data/rejected_records.csv")
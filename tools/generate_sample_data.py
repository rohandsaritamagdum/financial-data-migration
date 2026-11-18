#!/usr/bin/env python3
"""Generate a deliberately messy 'legacy system' CSV export plus a manifest of
exactly which defects were injected, so the pipeline can be checked against known answers.

  python tools/generate_sample_data.py              # writes data/legacy_transactions.csv
  python tools/generate_sample_data.py --rows 2000 --seed 7
"""
from __future__ import annotations

import argparse
import csv
import json
import random
from collections import Counter
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

COLUMNS = ["ACCT_NO", "CUSTOMER_NAME", "TXN_ID", "TXN_DATE", "TXN_TYPE", "AMOUNT",
           "CURRENCY", "BRANCH_CODE"]
FIRST = ["Aarav", "Priya", "Rohan", "Sneha", "Vikram", "Anita", "Karan", "Meera", "Arjun", "Divya"]
LAST = ["Sharma", "Patil", "Deshmukh", "Joshi", "Kulkarni", "Iyer", "Nair", "Singh", "Rao", "Gupta"]
BRANCHES = ["PUN01", "MUM02", "DEL03", "BLR04", "HYD05"]
CURRENCIES = ["USD", "EUR", "GBP", "INR"]

# (name, rule the pipeline should report, how many rows). Each defect hits its own
# rows, so every rejected row breaks exactly one rule.
DEFECTS = [
    ("missing_account", "MISSING_REQUIRED", 12),
    ("missing_amount", "MISSING_REQUIRED", 8),
    ("unparseable_date", "INVALID_DATE", 10),
    ("future_date", "FUTURE_DATE", 6),
    ("negative_amount", "NON_POSITIVE_AMOUNT", 8),
    ("zero_amount", "NON_POSITIVE_AMOUNT", 5),
    ("invalid_txn_type", "INVALID_TXN_TYPE", 6),
    ("invalid_currency", "INVALID_CURRENCY", 6),
    ("non_numeric_amount", "INVALID_AMOUNT", 5),
    ("too_many_decimals", "AMOUNT_PRECISION", 4),
    ("amount_out_of_range", "AMOUNT_OUT_OF_RANGE", 3),
]
EXACT_DUPLICATES = 10
CONFLICTING_DUPLICATES = 4   # each creates a pair; both rows get quarantined
ACCOUNT_NAME_CONFLICTS = 3


def _pad(text: str, rng: random.Random) -> str:
    return f"  {text} " if rng.random() < 0.08 else text


def _format_row(base: dict, rng: random.Random) -> dict:
    d: date = base["date"]
    date_text = rng.choice([d.isoformat(), d.strftime("%d/%m/%Y"), d.strftime("%d-%m-%Y")])
    amount: Decimal = base["amount"]
    amount_text = rng.choice([f"{amount:.2f}", f"{amount:.2f}", f"{amount:,.2f}", f"${amount:,.2f}"])
    type_text = rng.choice(
        ["CREDIT", "credit", "CR", "Cr"] if base["type"] == "CREDIT" else ["DEBIT", "debit", "DR", "Dr"])
    return {
        "ACCT_NO": _pad(base["account"]["account_no"], rng),
        "CUSTOMER_NAME": _pad(base["account"]["customer_name"], rng),
        "TXN_ID": base["txn_id"],
        "TXN_DATE": date_text,
        "TXN_TYPE": type_text,
        "AMOUNT": amount_text,
        "CURRENCY": rng.choice([base["currency"], base["currency"], base["currency"].lower()]),
        "BRANCH_CODE": base["account"]["branch_code"],
    }


def _mutate(defect: str, row: dict, rng: random.Random) -> None:
    if defect == "missing_account":
        row["ACCT_NO"] = ""
    elif defect == "missing_amount":
        row["AMOUNT"] = ""
    elif defect == "unparseable_date":
        row["TXN_DATE"] = rng.choice(["31/02/2025", "2025-13-45", "not a date", "00/00/0000"])
    elif defect == "future_date":
        row["TXN_DATE"] = "2099-01-01"
    elif defect == "negative_amount":
        row["AMOUNT"] = "-" + row["AMOUNT"].lstrip("$").replace(",", "").strip()
    elif defect == "zero_amount":
        row["AMOUNT"] = "0.00"
    elif defect == "invalid_txn_type":
        row["TXN_TYPE"] = rng.choice(["TRANSFER", "XFER", "?"])
    elif defect == "invalid_currency":
        row["CURRENCY"] = rng.choice(["XXX", "US", "123", "USDD"])
    elif defect == "non_numeric_amount":
        row["AMOUNT"] = rng.choice(["12O.50", "abc", "N/A", "1.2.3"])
    elif defect == "too_many_decimals":
        row["AMOUNT"] = "100.567"
    elif defect == "amount_out_of_range":
        row["AMOUNT"] = "1000000000000.00"
    else:
        raise ValueError(defect)


def generate(rows: int = 500, seed: int = 42) -> tuple[list[dict], dict]:
    rng = random.Random(seed)
    accounts = [{"account_no": f"AC{100000 + i}",
                 "customer_name": f"{rng.choice(FIRST)} {rng.choice(LAST)}",
                 "branch_code": rng.choice(BRANCHES)} for i in range(40)]

    bases, csv_rows = [], []
    for i in range(rows):
        base = {
            "account": rng.choice(accounts),
            "txn_id": f"TXN{i + 1:06d}",
            "date": date(2024, 1, 1) + timedelta(days=rng.randrange(0, 730)),
            "type": rng.choice(["CREDIT", "DEBIT"]),
            "amount": Decimal(rng.randrange(500, 2_500_000)) / 100,
            "currency": rng.choice(CURRENCIES),
        }
        bases.append(base)
        csv_rows.append(_format_row(base, rng))

    # Hand out disjoint sets of rows to each defect.
    order = list(range(rows))
    rng.shuffle(order)
    cursor = 0

    def take(count: int) -> list[int]:
        nonlocal cursor
        chosen = order[cursor:cursor + count]
        cursor += count
        return chosen

    expected_rules: Counter = Counter()
    single_defect_rows = 0
    for defect, rule, count in DEFECTS:
        for idx in take(count):
            _mutate(defect, csv_rows[idx], rng)
        expected_rules[rule] += count
        single_defect_rows += count

    exact_sources = take(EXACT_DUPLICATES)
    conflict_sources = take(CONFLICTING_DUPLICATES)

    # Same account, different customer name (one row per distinct account).
    used_accounts, conflict_rows = set(), []
    while len(conflict_rows) < ACCOUNT_NAME_CONFLICTS:
        idx = take(1)[0]
        acct = bases[idx]["account"]["account_no"]
        if acct in used_accounts:
            continue
        used_accounts.add(acct)
        conflict_rows.append(idx)
        csv_rows[idx]["CUSTOMER_NAME"] = bases[idx]["account"]["customer_name"] + " Jr"

    for idx in exact_sources:                      # identical repeat of an earlier row
        csv_rows.append(dict(csv_rows[idx]))
    for idx in conflict_sources:                   # same txn_id, different amount
        clone = dict(csv_rows[idx])
        clone["AMOUNT"] = f"{bases[idx]['amount'] + Decimal('1.00'):.2f}"
        csv_rows.append(clone)

    expected_rules["DUPLICATE_EXACT"] = EXACT_DUPLICATES
    expected_rules["DUPLICATE_CONFLICT"] = CONFLICTING_DUPLICATES * 2
    rejected = single_defect_rows + EXACT_DUPLICATES + CONFLICTING_DUPLICATES * 2
    manifest = {
        "rows_total": len(csv_rows),
        "expected_rejected": rejected,
        "expected_valid": len(csv_rows) - rejected,
        "expected_rule_row_counts": dict(sorted(expected_rules.items())),
        "expected_account_conflict_warnings": ACCOUNT_NAME_CONFLICTS,
    }
    return csv_rows, manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--rows", type=int, default=500)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", default="data/legacy_transactions.csv")
    args = parser.parse_args()

    csv_rows, manifest = generate(args.rows, args.seed)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(csv_rows)
    manifest_path = out.with_suffix(".manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Wrote {len(csv_rows)} rows to {out}")
    print(f"Wrote expected-results manifest to {manifest_path}")


if __name__ == "__main__":
    main()
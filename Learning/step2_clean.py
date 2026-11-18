import re
from datetime import datetime
from decimal import Decimal

import pandas as pd

DATE_FORMATS = ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"]
TYPE_ALIASES = {"CREDIT": "CREDIT", "CR": "CREDIT", "DEBIT": "DEBIT", "DR": "DEBIT"}


def clean_text(value):
    """Remove spaces at the start and end, and collapse repeated spaces."""
    return re.sub(r"\s+", " ", value).strip()


def parse_date(value):
    """Turn text into a real date. Return None if it is not a real date."""
    text = clean_text(value)
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    return None


def parse_amount(value):
    """Turn text like '1,200.50' into a number. Return None if it is not a number."""
    text = clean_text(value).replace(",", "").replace("$", "")
    try:
        return Decimal(text)
    except Exception:
        return None


def normalize_type(value):
    """Turn 'dr', 'Dr', 'DR' into 'DEBIT'. Unknown words are kept (in capitals)."""
    key = clean_text(value).upper()
    return TYPE_ALIASES.get(key, key)


df = pd.read_csv("data/legacy_transactions.csv", dtype=str, keep_default_na=False)

for number, row in df.iterrows():
    print(f"Row {number}:")
    print("  account :", repr(row["ACCT_NO"]), "->", repr(clean_text(row["ACCT_NO"]).upper()))
    print("  date    :", repr(row["TXN_DATE"]), "->", parse_date(row["TXN_DATE"]))
    print("  type    :", repr(row["TXN_TYPE"]), "->", normalize_type(row["TXN_TYPE"]))
    print("  amount  :", repr(row["AMOUNT"]), "->", parse_amount(row["AMOUNT"]))

clean_df = pd.DataFrame({
    "account_no": df["ACCT_NO"].map(lambda v: clean_text(v).upper()),
    "txn_date": df["TXN_DATE"].map(parse_date),
    "txn_type": df["TXN_TYPE"].map(normalize_type),
    "amount": df["AMOUNT"].map(parse_amount),
    "currency": df["CURRENCY"].map(lambda v: clean_text(v).upper()),
})
clean_df.to_csv("data/cleaned_preview.csv", index=False)
print("Wrote data/cleaned_preview.csv")
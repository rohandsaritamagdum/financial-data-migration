from datetime import date

from cleaning import clean_text, normalize_type, parse_amount, parse_date

ALLOWED_CURRENCIES = ["USD", "EUR", "GBP", "INR"]
VALID_TYPES = ["CREDIT", "DEBIT"]


def validate_rows(df):
    """Check every row. Returns (valid_rows, rejected_rows)."""
    valid = []
    rejected = []
    seen_ids = {}  # txn_id -> row number where we first saw it

    for number, row in df.iterrows():
        row_number = number + 1
        codes = []    # short reason codes, e.g. INVALID_DATE
        notes = []    # readable explanations

        def fail(code, message):
            codes.append(code)
            notes.append(f"{code}: {message}")

        account = clean_text(row["ACCT_NO"]).upper()
        txn_id = clean_text(row["TXN_ID"]).upper()
        txn_date = parse_date(row["TXN_DATE"])
        txn_type = normalize_type(row["TXN_TYPE"])
        amount = parse_amount(row["AMOUNT"])
        currency = clean_text(row["CURRENCY"]).upper()

        if account == "":
            fail("MISSING_ACCOUNT", "account number is blank")

        if clean_text(row["TXN_DATE"]) == "":
            fail("MISSING_DATE", "date is blank")
        elif txn_date is None:
            fail("INVALID_DATE", f"cannot read '{row['TXN_DATE']}' as a real date")
        elif txn_date > date.today():
            fail("FUTURE_DATE", f"{txn_date} is in the future")

        if txn_type not in VALID_TYPES:
            fail("INVALID_TXN_TYPE", f"'{row['TXN_TYPE']}' is not CREDIT or DEBIT")

        if clean_text(row["AMOUNT"]) == "":
            fail("MISSING_AMOUNT", "amount is blank")
        elif amount is None:
            fail("INVALID_AMOUNT", f"'{row['AMOUNT']}' is not a number")
        elif amount <= 0:
            fail("NON_POSITIVE_AMOUNT", f"amount {amount} must be greater than zero")
        elif abs(amount) >= 1000000000000:
            fail("AMOUNT_OUT_OF_RANGE", f"amount {amount} is too large for NUMERIC(14,2)")
        elif amount.as_tuple().exponent < -2:
            fail("AMOUNT_PRECISION", f"amount {amount} has more than 2 decimal places")

        if currency not in ALLOWED_CURRENCIES:
            fail("INVALID_CURRENCY", f"'{row['CURRENCY']}' is not an allowed currency")

        if txn_id in seen_ids:
            fail("DUPLICATE_TXN_ID", f"first seen in row {seen_ids[txn_id]}")
        else:
            seen_ids[txn_id] = row_number

        if codes:
            rejected.append({
                "row": row_number,
                "txn_id": txn_id,
                "codes": codes,
                "details": "; ".join(notes),
                "raw": row.to_dict(),
            })
        else:
            valid.append({
                "row": row_number,
                "account_no": account,
                "customer_name": clean_text(row["CUSTOMER_NAME"]),
                "branch_code": clean_text(row["BRANCH_CODE"]).upper(),
                "txn_id": txn_id,
                "txn_date": txn_date,
                "txn_type": txn_type,
                "amount": amount,
                "currency": currency,
            })

    return valid, rejected
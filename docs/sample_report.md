# Migration Reconciliation Report

- **Source file:** `data/legacy_transactions.csv`
- **Generated:** 2026-11-18 11:43:17
- **Result:** PASSED

## Row accounting

| Metric | Rows |
|---|---|
| Read from source | 514 |
| Passed validation | 427 |
| Rejected | 87 |
| Missing from database | 0 |
| Field mismatches | 0 |

## Rejections by reason

| Reason | Rows |
|---|---|
| AMOUNT_OUT_OF_RANGE | 3 |
| AMOUNT_PRECISION | 4 |
| DUPLICATE_TXN_ID | 14 |
| FUTURE_DATE | 6 |
| INVALID_AMOUNT | 5 |
| INVALID_CURRENCY | 6 |
| INVALID_DATE | 10 |
| INVALID_TXN_TYPE | 6 |
| MISSING_ACCOUNT | 12 |
| MISSING_AMOUNT | 8 |
| NON_POSITIVE_AMOUNT | 13 |

## Control totals

| Currency | Type | Source count | Database count | Source total | Database total | Match |
|---|---|---|---|---|---|---|
| EUR | CREDIT | 50 | 50 | 604015.69 | 604015.69 | yes |
| EUR | DEBIT | 63 | 63 | 769011.69 | 769011.69 | yes |
| GBP | CREDIT | 56 | 56 | 734889.07 | 734889.07 | yes |
| GBP | DEBIT | 56 | 56 | 695997.55 | 695997.55 | yes |
| INR | CREDIT | 48 | 48 | 603626.65 | 603626.65 | yes |
| INR | DEBIT | 50 | 50 | 696564.57 | 696564.57 | yes |
| USD | CREDIT | 48 | 48 | 630952.05 | 630952.05 | yes |
| USD | DEBIT | 56 | 56 | 722762.26 | 722762.26 | yes |

import pandas as pd

df = pd.read_csv("data/legacy_transactions.csv", dtype=str, keep_default_na=False)

print(df)
print(len(df), "rows")
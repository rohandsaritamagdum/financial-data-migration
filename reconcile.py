from collections import defaultdict
from decimal import Decimal

COMPARE_FIELDS = ["account_no", "txn_date", "txn_type", "amount", "currency"]


def normalize(field, value):
    """Make source and database values comparable (10.5 and 10.50 are the same)."""
    if field == "amount":
        return f"{Decimal(value):.2f}"
    if field == "txn_date":
        return value.isoformat()
    return str(value).strip()


def control_totals(records):
    """Count and add up amounts for each (currency, type) pair."""
    totals = defaultdict(lambda: [0, Decimal("0")])
    for r in records:
        key = (r["currency"], r["txn_type"])
        totals[key][0] += 1
        totals[key][1] += r["amount"]
    return {key: (count, total) for key, (count, total) in sorted(totals.items())}


def compare(source, target):
    """Compare what we meant to load (source) with what is in the database (target).

    Returns (missing_ids, mismatches, totals_table).
    """
    source_by_id = {r["txn_id"]: r for r in source}
    target_by_id = {r["txn_id"]: r for r in target if r["txn_id"] in source_by_id}

    missing = sorted(set(source_by_id) - set(target_by_id))

    mismatches = []
    for txn_id in sorted(set(source_by_id) & set(target_by_id)):
        for field in COMPARE_FIELDS:
            s = normalize(field, source_by_id[txn_id][field])
            t = normalize(field, target_by_id[txn_id][field])
            if s != t:
                mismatches.append((txn_id, field, s, t))

    source_totals = control_totals(source_by_id.values())
    target_totals = control_totals(target_by_id.values())
    totals_table = []
    for key in sorted(set(source_totals) | set(target_totals)):
        s_count, s_sum = source_totals.get(key, (0, Decimal("0")))
        t_count, t_sum = target_totals.get(key, (0, Decimal("0")))
        totals_table.append({
            "currency": key[0], "type": key[1],
            "source_count": s_count, "target_count": t_count,
            "source_sum": s_sum, "target_sum": t_sum,
            "match": s_count == t_count and s_sum == t_sum,
        })
    return missing, mismatches, totals_table
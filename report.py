from collections import Counter
from datetime import datetime


def write_report(path, *, source, rows_read, valid, rejected, missing, mismatches, totals_table, passed):
    """Write a readable Markdown reconciliation report."""
    reasons = Counter(code for r in rejected for code in r["codes"])
    lines = [
        "# Migration Reconciliation Report",
        "",
        f"- **Source file:** `{source}`",
        f"- **Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- **Result:** {'PASSED' if passed else 'FAILED'}",
        "",
        "## Row accounting",
        "",
        "| Metric | Rows |",
        "|---|---|",
        f"| Read from source | {rows_read} |",
        f"| Passed validation | {len(valid)} |",
        f"| Rejected | {len(rejected)} |",
        f"| Missing from database | {len(missing)} |",
        f"| Field mismatches | {len(mismatches)} |",
        "",
        "## Rejections by reason",
        "",
        "| Reason | Rows |",
        "|---|---|",
    ]
    lines += [f"| {reason} | {count} |" for reason, count in sorted(reasons.items())]
    lines += [
        "",
        "## Control totals",
        "",
        "| Currency | Type | Source count | Database count | Source total | Database total | Match |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in totals_table:
        lines.append(
            f"| {row['currency']} | {row['type']} | {row['source_count']} | {row['target_count']} | "
            f"{row['source_sum']:.2f} | {row['target_sum']:.2f} | {'yes' if row['match'] else 'NO'} |"
        )
    if mismatches:
        lines += ["", "## Differences", "", "| Transaction | Field | In file | In database |", "|---|---|---|---|"]
        lines += [f"| {t} | {f} | {s} | {d} |" for t, f, s, d in mismatches]
    if missing:
        lines += ["", "## Missing from database", "", ", ".join(missing)]
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")
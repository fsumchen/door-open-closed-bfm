#!/usr/bin/env python3
"""Evaluate a standardized nearest-centroid baseline on explicitly held-out captures."""
import argparse, csv, json, statistics
from collections import Counter
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("windows", type=Path)
    p.add_argument("--test-sessions", nargs="+", required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--status", default="exploratory_only_same_day_holdout")
    p.add_argument("--warning", default="Same-day capture holdout only; not a different-day generalization result.")
    a = p.parse_args()
    with a.windows.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    test_ids = set(a.test_sessions)
    train = [r for r in rows if r["session_id"] not in test_ids]
    test = [r for r in rows if r["session_id"] in test_ids]
    if not train or not test:
        raise SystemExit("The selected test sessions or remaining training set is empty")
    columns = [k for k in rows[0] if k.endswith("_mean") or k.endswith("_sd")]
    labels = sorted({r["door_state"] for r in train})
    if len(labels) < 2:
        raise SystemExit("Training data must contain both door-state classes")
    means = [statistics.mean(float(r[c]) for r in train) for c in columns]
    scales = [statistics.pstdev(float(r[c]) for r in train) or 1.0 for c in columns]
    centroids = {
        label: [
            statistics.mean((float(r[c]) - m) / s for r in train if r["door_state"] == label)
            for c, m, s in zip(columns, means, scales)
        ]
        for label in labels
    }
    matrix = {actual: {predicted: 0 for predicted in labels} for actual in labels}
    for row in test:
        x = [(float(row[c]) - m) / s for c, m, s in zip(columns, means, scales)]
        prediction = min(labels, key=lambda lab: sum((u - v) ** 2 for u, v in zip(x, centroids[lab])))
        matrix[row["door_state"]][prediction] += 1
    correct = sum(matrix[label][label] for label in labels)
    result = {
        "status": a.status,
        "method": "standardized nearest centroid",
        "test_sessions": sorted(test_ids),
        "train_windows": len(train),
        "test_windows": len(test),
        "train_class_counts": dict(Counter(r["door_state"] for r in train)),
        "test_class_counts": dict(Counter(r["door_state"] for r in test)),
        "confusion_matrix_actual_rows_predicted_columns": matrix,
        "accuracy": correct / len(test),
        "warning": a.warning,
    }
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(a.output.read_text())


if __name__ == "__main__":
    main()

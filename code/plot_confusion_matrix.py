#!/usr/bin/env python3
"""Render a compact SVG confusion matrix from an evaluation JSON file."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evaluation", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = json.loads(args.evaluation.read_text(encoding="utf-8"))
    matrix = result["confusion_matrix_actual_rows_predicted_columns"]
    labels = list(matrix)
    values = [matrix[actual][predicted] for actual in labels for predicted in labels]
    maximum = max(values) or 1

    def shade(value: int) -> str:
        light = int(246 - 130 * value / maximum)
        return f"rgb({light},{light + 5},{min(255, light + 9)})"

    cell = 126
    svg = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="420" height="400" viewBox="0 0 420 400">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<style>text{font-family:Arial,sans-serif;fill:#182230}.title{font-size:20px;font-weight:700}.axis{font-size:14px;font-weight:600}.label{font-size:15px}.count{font-size:34px;font-weight:700}</style>',
        '<text x="210" y="34" text-anchor="middle" class="title">Different-day holdout confusion matrix</text>',
        '<text x="210" y="66" text-anchor="middle" class="axis">Predicted door state</text>',
        '<text x="24" y="233" text-anchor="middle" class="axis" transform="rotate(-90 24 233)">Actual door state</text>',
    ]
    left, top = 150, 112
    for j, predicted in enumerate(labels):
        x = left + j * cell + cell / 2
        svg.append(f'<text x="{x}" y="98" text-anchor="middle" class="label">{predicted}</text>')
    for i, actual in enumerate(labels):
        y = top + i * cell + cell / 2 + 5
        svg.append(f'<text x="138" y="{y}" text-anchor="end" class="label">{actual}</text>')
        for j, predicted in enumerate(labels):
            value = matrix[actual][predicted]
            x, y0 = left + j * cell, top + i * cell
            svg.append(f'<rect x="{x}" y="{y0}" width="{cell}" height="{cell}" fill="{shade(value)}" stroke="#ffffff" stroke-width="3"/>')
            svg.append(f'<text x="{x + cell / 2}" y="{y0 + cell / 2 + 12}" text-anchor="middle" class="count">{value}</text>')
    accuracy = 100 * result["accuracy"]
    svg.append(f'<text x="210" y="375" text-anchor="middle" class="label">{accuracy:.1f}% accuracy, {result["test_windows"]} held-out windows</text>')
    svg.append('</svg>')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(svg) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

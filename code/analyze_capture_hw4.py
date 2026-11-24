#!/usr/bin/env python3
"""Summarize a Wi-Fi BFM capture and create Figure A using tshark."""

from __future__ import annotations

import argparse
import csv
import shutil
import subprocess
from collections import Counter
from pathlib import Path


def fields(tshark: str, capture: Path, display_filter: str, names: list[str]) -> list[list[str]]:
    command = [tshark, "-r", str(capture), "-Y", display_filter, "-T", "fields", "-E", "separator=\t", "-E", "quote=n"]
    for name in names:
        command.extend(["-e", name])
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    return [line.split("\t") for line in result.stdout.splitlines() if line]


def svg_figure(counts: Counter[int], duration: float, output: Path, pause: float | None, resume: float | None) -> None:
    width, height = 1200, 620
    left, right, top, bottom = 90, 1150, 60, 520
    plot_w, plot_h = right - left, bottom - top
    max_rate = max(8, ((max(counts.values(), default=0) + 3) // 4) * 4)

    def x_at(seconds: float) -> float:
        return left + plot_w * seconds / duration

    def y_at(rate: float) -> float:
        return bottom - plot_h * rate / max_rate

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<style>text{font-family:Arial,Helvetica,sans-serif;fill:#172033}.axis{stroke:#374151;stroke-width:1.5}.grid{stroke:#d7dee8;stroke-width:1}.line{fill:none;stroke:#2463a6;stroke-width:2}.marker{stroke:#c2410c;stroke-width:2;stroke-dasharray:7 6}.small{font-size:13px}.label{font-size:16px}.title{font-size:22px;font-weight:bold}</style>',
        f'<text x="{width/2}" y="30" text-anchor="middle" class="title">Beamforming reports per second</text>',
    ]
    for tick in range(0, max_rate + 1, 2):
        y = y_at(tick)
        parts.append(f'<line x1="{left}" y1="{y:.1f}" x2="{right}" y2="{y:.1f}" class="grid"/>')
        parts.append(f'<text x="{left-14}" y="{y+5:.1f}" text-anchor="end" class="small">{tick}</text>')
    for tick in range(0, int(duration) + 1, 30):
        x = x_at(tick)
        parts.append(f'<line x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{bottom}" class="grid"/>')
        parts.append(f'<text x="{x:.1f}" y="{bottom+24}" text-anchor="middle" class="small">{tick}</text>')
    parts.extend([
        f'<line x1="{left}" y1="{bottom}" x2="{right}" y2="{bottom}" class="axis"/>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{bottom}" class="axis"/>',
        f'<text x="{(left+right)/2}" y="{height-24}" text-anchor="middle" class="label">Time from capture start (seconds)</text>',
        f'<text x="24" y="{(top+bottom)/2}" text-anchor="middle" class="label" transform="rotate(-90 24 {(top+bottom)/2})">Reports per second (1-second bins)</text>',
    ])
    if pause is not None:
        x = x_at(pause)
        parts.append(f'<line x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{bottom}" class="marker"/>')
        parts.append(f'<text x="{x+6:.1f}" y="{top+18}" class="small">Video paused ({pause:g}s)</text>')
    if resume is not None:
        x = x_at(resume)
        parts.append(f'<line x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{bottom}" class="marker"/>')
        parts.append(f'<text x="{x+6:.1f}" y="{top+38}" class="small">Video resumed ({resume:g}s)</text>')
    points = []
    for second in range(int(duration) + 1):
        points.append(f'{x_at(second):.1f},{y_at(counts[second]):.1f}')
    parts.append(f'<polyline points="{" ".join(points)}" class="line"/>')
    parts.append('</svg>')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(parts), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("capture", type=Path)
    parser.add_argument("--duration", type=float, default=360.0)
    parser.add_argument("--pause-start", type=float)
    parser.add_argument("--resume", type=float)
    parser.add_argument("--tshark", default=shutil.which("tshark") or "tshark")
    parser.add_argument("--figure", type=Path, default=Path("figures/figureA_reports_per_second.svg"))
    parser.add_argument("--csv", type=Path, default=Path("figures/figureA_reports_per_second.csv"))
    args = parser.parse_args()

    ndpa = fields(args.tshark, args.capture, "wlan.fc.type_subtype == 0x0015", ["frame.number"])
    reports = fields(
        args.tshark,
        args.capture,
        "wlan.fc.type_subtype == 0x000e && (wlan.vht.compressed_beamforming_report || wlan.he.action.he_mimo_control)",
        ["frame.time_relative", "wlan.fixed.category_code", "wlan.sa", "wlan.da"],
    )
    per_second: Counter[int] = Counter()
    categories: Counter[str] = Counter()
    clients: Counter[tuple[str, str]] = Counter()
    for row in reports:
        timestamp = float(row[0])
        category, source, destination = (row + [""] * 4)[1:4]
        per_second[int(timestamp)] += 1
        categories[category] += 1
        clients[(category, source)] += 1

    svg_figure(per_second, args.duration, args.figure, args.pause_start, args.resume)
    args.csv.parent.mkdir(parents=True, exist_ok=True)
    with args.csv.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["relative_second", "beamforming_reports"])
        for second in range(int(args.duration) + 1):
            writer.writerow([second, per_second[second]])
    print(f"NDPA frames: {len(ndpa)} ({len(ndpa)/args.duration:.3f}/s)")
    print(f"BFM reports: {len(reports)} ({len(reports)/args.duration:.3f}/s)")
    print(f"Report categories: {dict(sorted(categories.items()))}")
    print(f"Figure: {args.figure}")
    print(f"Per-second data: {args.csv}")
    # Deliberately do not print MAC addresses; the report must use short device labels.
    print("Pair report counts by category are available in the generated report table.")


if __name__ == "__main__":
    main()

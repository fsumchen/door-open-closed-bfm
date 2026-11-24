#!/usr/bin/env python3
"""Decode HE 2x2 feedback from two captures and draw the HW4 Part 3 figures.

Requires tshark. The selected captures in this project use HE feedback, 40 MHz,
and a two-antenna/two-stream feedback format. Raw packet captures stay local.
"""

from __future__ import annotations

import argparse
import csv
import math
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


ANGLE_RE = re.compile(r"(-?\d+),\s*φ11:(\d+),\s*ψ21:(\d+)")


@dataclass
class Report:
    time: float
    phi: list[int]
    psi: list[int]


def parse_capture(tshark: str, capture: Path, ap: str, client: str) -> list[Report]:
    display_filter = (
        "wlan.fc.type_subtype == 0x000e && wlan.fixed.category_code == 30 && "
        f"wlan.sa == {client} && wlan.da == {ap} && wlan.he.action.he_mimo_control"
    )
    command = [
        tshark, "-n", "-r", str(capture), "-Y", display_filter, "-T", "fields",
        "-E", "separator=/t", "-E", "occurrence=a", "-E", "aggregator=;",
        "-e", "frame.time_relative", "-e", "wlan.he.action.he_mimo_control.scidx",
    ]
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    reports: list[Report] = []
    for line in result.stdout.splitlines():
        fields = line.split("\t", 1)
        if len(fields) != 2:
            continue
        matches = ANGLE_RE.findall(fields[1])
        if len(matches) != 122:
            raise ValueError(f"Expected 122 HE tones, found {len(matches)} in {capture} at {fields[0]}s")
        # HE 40 MHz uses 122 data-tone groups, indexed in steps of four.
        indices = [int(item[0]) for item in matches]
        expected = list(range(-244, 0, 4)) + list(range(4, 248, 4))
        if indices != expected:
            raise ValueError(f"Unexpected tone indices in {capture} at {fields[0]}s")
        reports.append(Report(float(fields[0]), [int(x[1]) for x in matches], [int(x[2]) for x in matches]))
    if not reports:
        raise ValueError(f"No HE reports found for the selected AP-client pair in {capture}")
    return reports


def physical_angles(report: Report) -> tuple[list[float], list[float]]:
    # IEEE compressed-angle quantizer midpoint mapping, codebook 1 (phi=6, psi=4).
    phi = [360.0 * (v + 0.5) / 64.0 for v in report.phi]
    psi = [90.0 * (v + 0.5) / 16.0 for v in report.psi]
    return phi, psi


def music_spectrum(report: Report, angle_grid: list[int]) -> list[float]:
    """Two-element ULA MUSIC spectrum from the 2x1 vector in each HE tone."""
    r00 = r11 = 0.0
    r01 = 0j
    for p, s in zip(report.phi, report.psi):
        phi = math.pi * (p + 0.5) / 32.0
        psi = math.pi * (s + 0.5) / 32.0
        # Wi-BFI Givens reconstruction for the first column of V, Nr=2.
        x0 = complex(math.cos(psi) * math.cos(phi), math.cos(psi) * math.sin(phi))
        x1 = complex(math.sin(psi), 0.0)
        r00 += abs(x0) ** 2
        r11 += abs(x1) ** 2
        r01 += x0 * x1.conjugate()
    n = len(report.phi)
    r00, r11, r01 = r00 / n, r11 / n, r01 / n
    disc = math.sqrt(max(0.0, (r00 - r11) ** 2 + 4.0 * abs(r01) ** 2))
    lo, hi = 0.5 * (r00 + r11 - disc), 0.5 * (r00 + r11 + disc)
    gap = max(hi - lo, 1e-12)
    # Signal-subspace projector (largest eigenvalue); noise projector is I-Ps.
    ps00, ps11 = (r00 - lo) / gap, (r11 - lo) / gap
    ps01 = r01 / gap
    output = []
    for deg in angle_grid:
        phase = -math.pi * math.sin(math.radians(deg))
        a0, a1 = 1 / math.sqrt(2), complex(math.cos(phase), math.sin(phase)) / math.sqrt(2)
        # aᴴ (I-Ps) a
        signal_proj = (
            (a0 * (ps00 * a0 + ps01 * a1)).real
            + (a1.conjugate() * (ps01.conjugate() * a0 + ps11 * a1)).real
        )
        denominator = max(1.0 - signal_proj, 1e-9)
        output.append(1.0 / denominator)
    return output


def viridis(value: float) -> str:
    stops = [(68, 1, 84), (59, 82, 139), (33, 145, 140), (94, 201, 98), (253, 231, 37)]
    v = max(0.0, min(1.0, value)) * (len(stops) - 1)
    i = min(int(v), len(stops) - 2)
    f = v - i
    rgb = tuple(round(stops[i][k] * (1 - f) + stops[i + 1][k] * f) for k in range(3))
    return "#%02x%02x%02x" % rgb


def svg_heatmap(reports: list[Report], output: Path, title: str) -> None:
    width, height = 1120, 620
    left, right, top, bottom = 95, 1000, 70, 520
    plot_w, plot_h = right - left, bottom - top
    tmax = 60.0
    rows = len(reports[0].phi)
    cell_h = plot_h / rows
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<style>text{font-family:Arial,Helvetica,sans-serif;fill:#172033}.axis{stroke:#374151;stroke-width:1.4}.grid{stroke:#d7dee8;stroke-width:1}.title{font-size:21px;font-weight:bold}.label{font-size:15px}.small{font-size:12px}</style>',
        f'<text x="560" y="32" text-anchor="middle" class="title">{title}</text>',
    ]
    for col, report in enumerate(reports):
        phi, _ = physical_angles(report)
        previous = reports[col - 1].time if col else 0.0
        following = reports[col + 1].time if col + 1 < len(reports) else tmax
        start_t = max(0.0, 0.5 * (previous + report.time))
        end_t = min(tmax, 0.5 * (report.time + following))
        x = left + start_t / tmax * plot_w
        cell_w = max(0.3, (end_t - start_t) / tmax * plot_w)
        for row, value in enumerate(phi):
            y = bottom - (row + 1) * cell_h
            parts.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{cell_w+0.5:.2f}" height="{cell_h+0.2:.2f}" fill="{viridis(value/360.0)}"/>')
    for sec in range(0, 61, 10):
        x = left + sec / tmax * plot_w
        parts.append(f'<line x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{bottom}" class="grid"/>')
        parts.append(f'<text x="{x:.1f}" y="{bottom+22}" text-anchor="middle" class="small">{sec}</text>')
    low_freq, high_freq = 5270 - 244 * 0.078125, 5270 + 244 * 0.078125
    for mhz in [5251, 5260, 5270, 5280, 5289]:
        row = (mhz - low_freq) / (high_freq - low_freq)
        y = bottom - row * plot_h
        parts.append(f'<line x1="{left}" y1="{y:.1f}" x2="{right}" y2="{y:.1f}" class="grid"/>')
        parts.append(f'<text x="{left-10}" y="{y+4:.1f}" text-anchor="end" class="small">{mhz}</text>')
    parts.extend([
        f'<line x1="{left}" y1="{bottom}" x2="{right}" y2="{bottom}" class="axis"/>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{bottom}" class="axis"/>',
        f'<text x="{(left+right)/2}" y="{height-32}" text-anchor="middle" class="label">Time from capture start (seconds)</text>',
        f'<text x="24" y="{(top+bottom)/2}" text-anchor="middle" class="label" transform="rotate(-90 24 {(top+bottom)/2})">Subcarrier frequency (MHz)</text>',
        '<text x="1020" y="83" class="small">φ₁₁ (degrees)</text>',
    ])
    for j in range(101):
        y = top + j * plot_h / 100
        parts.append(f'<rect x="1020" y="{y:.1f}" width="22" height="{plot_h/100+0.2:.1f}" fill="{viridis(1-j/100)}"/>')
    for deg in [360, 270, 180, 90, 0]:
        y = top + (1 - deg / 360) * plot_h
        parts.append(f'<text x="1050" y="{y+4:.1f}" class="small">{deg}</text>')
    parts.append('</svg>')
    output.write_text("\n".join(parts), encoding="utf-8")


def svg_music(reports: list[Report], output: Path) -> None:
    width, height = 1120, 620
    left, right, top, bottom = 95, 1000, 70, 520
    plot_w, plot_h = right - left, bottom - top
    angles = list(range(-90, 91))
    spectra = [music_spectrum(report, angles) for report in reports]
    db = [[10 * math.log10(max(v, 1e-12)) for v in row] for row in spectra]
    # Normalize each time slice so motion-induced peak changes are visible.
    normalized = [[max(-25.0, v - max(row)) for v in row] for row in db]
    cell_h = plot_h / len(angles)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<style>text{font-family:Arial,Helvetica,sans-serif;fill:#172033}.axis{stroke:#374151;stroke-width:1.4}.grid{stroke:#d7dee8;stroke-width:1}.title{font-size:21px;font-weight:bold}.label{font-size:15px}.small{font-size:12px}</style>',
        '<text x="560" y="32" text-anchor="middle" class="title">MUSIC angle spectrum during the walking capture</text>',
        '<text x="560" y="54" text-anchor="middle" class="small">Walking throughout 0–60 s, including the return trip</text>',
    ]
    for col, report in enumerate(reports):
        previous = reports[col - 1].time if col else 0.0
        following = reports[col + 1].time if col + 1 < len(reports) else 60.0
        start_t = max(0.0, 0.5 * (previous + report.time))
        end_t = min(60.0, 0.5 * (report.time + following))
        x = left + start_t / 60.0 * plot_w
        cell_w = max(0.3, (end_t - start_t) / 60.0 * plot_w)
        for row, value in enumerate(normalized[col]):
            y = bottom - (row + 1) * cell_h
            parts.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{cell_w+0.5:.2f}" height="{cell_h+0.2:.2f}" fill="{viridis((value+25.0)/25.0)}"/>')
    for sec in range(0, 61, 10):
        x = left + sec / 60.0 * plot_w
        parts.append(f'<line x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{bottom}" class="grid"/>')
        parts.append(f'<text x="{x:.1f}" y="{bottom+22}" text-anchor="middle" class="small">{sec}</text>')
    for deg in range(-90, 91, 30):
        y = bottom - (deg + 90) / 180 * plot_h
        parts.append(f'<line x1="{left}" y1="{y:.1f}" x2="{right}" y2="{y:.1f}" class="grid"/>')
        parts.append(f'<text x="{left-10}" y="{y+4:.1f}" text-anchor="end" class="small">{deg}</text>')
    parts.extend([
        f'<line x1="{left}" y1="{bottom}" x2="{right}" y2="{bottom}" class="axis"/>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{bottom}" class="axis"/>',
        f'<text x="{(left+right)/2}" y="{height-32}" text-anchor="middle" class="label">Time from capture start (seconds)</text>',
        f'<text x="24" y="{(top+bottom)/2}" text-anchor="middle" class="label" transform="rotate(-90 24 {(top+bottom)/2})">Angle (degrees)</text>',
        '<text x="1020" y="83" class="small">Relative</text><text x="1020" y="99" class="small">power</text>',
    ])
    for j in range(101):
        y = top + j * plot_h / 100
        parts.append(f'<rect x="1020" y="{y:.1f}" width="22" height="{plot_h/100+0.2:.1f}" fill="{viridis(1-j/100)}"/>')
    parts.append('<text x="1050" y="74" class="small">0 dB</text><text x="1050" y="440" class="small">−25 dB</text>')
    parts.append('</svg>')
    output.write_text("\n".join(parts), encoding="utf-8")


def write_csv(reports: list[Report], output: Path) -> None:
    with output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(["time_s", "subcarrier_index", "frequency_MHz", "phi11_raw", "psi21_raw", "phi11_degrees"])
        for report in reports:
            phi_deg, _ = physical_angles(report)
            for i, (p, s, deg) in enumerate(zip(report.phi, report.psi, phi_deg)):
                sc = list(range(-244, 0, 4)) + list(range(4, 248, 4))
                writer.writerow([f"{report.time:.6f}", sc[i], f"{5270 + sc[i] * 0.078125:.6f}", p, s, f"{deg:.4f}"])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("still", type=Path)
    parser.add_argument("walking", type=Path)
    parser.add_argument("--ap", required=True, help="AP MAC address, used only as a local capture filter")
    parser.add_argument("--client", required=True, help="beamformee MAC address, used only as a local capture filter")
    parser.add_argument("--tshark", default=shutil.which("tshark") or "tshark")
    parser.add_argument("--output-dir", type=Path, default=Path("figures"))
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    still = parse_capture(args.tshark, args.still, args.ap, args.client)
    walking = parse_capture(args.tshark, args.walking, args.ap, args.client)
    svg_heatmap(still, args.output_dir / "figureB_still.svg", "Still capture: φ₁₁ across frequency and time")
    svg_heatmap(walking, args.output_dir / "figureB_walking.svg", "Walking capture: φ₁₁ across frequency and time")
    svg_music(walking, args.output_dir / "figureC_music.svg")
    write_csv(still, args.output_dir / "part3_still_angles.csv")
    write_csv(walking, args.output_dir / "part3_walking_angles.csv")
    print("AP: Ruckus-AP; beamformee: Unknown-Private-2 (inferred from matching HE 2x2 / 122-tone / codebook parameters)")
    print(f"Still reports: {len(still)} in 60 s ({len(still)/60:.2f}/s)")
    print(f"Walking reports: {len(walking)} in 60 s ({len(walking)/60:.2f}/s)")
    print("Files: figureB_still.svg, figureB_walking.svg, figureC_music.svg, part3_*_angles.csv")


if __name__ == "__main__":
    main()

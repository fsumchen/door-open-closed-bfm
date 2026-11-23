#!/usr/bin/env python3
"""Export the selected client's VHT compressed-BFM per-tone angle codes."""
from __future__ import annotations
import argparse
import csv
import json
import re
import shutil
import subprocess
from pathlib import Path

ANGLE_RE = re.compile(r"(-?\d+),\s*φ11:(\d+),\s*ψ21:(\d+)")

def intervals_for(labels_path: Path, session: str):
    rows = []
    with labels_path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["session_id"] != session or row["certainty"] == "point_only":
                continue
            rows.append({"start": float(row["start_s"]), "end": float(row["end_s"]), "state": row["door_state"], "certainty": row["certainty"]})
    return rows

def state_at(t: float, intervals, margin: float):
    for i, item in enumerate(intervals):
        if item["start"] <= t < item["end"]:
            # Discard data immediately after a state transition.
            if i > 0 and t < item["start"] + margin:
                return None
            # Discard data immediately before the next transition.
            if i + 1 < len(intervals) and t >= item["end"] - margin:
                return None
            return item["state"], item["certainty"]
    return None

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--capture", required=True, type=Path)
    ap.add_argument("--session", required=True)
    ap.add_argument("--client", required=True, help="Phone Wi-Fi address, used only as a local filter")
    ap.add_argument("--ap", required=True, help="AP BSSID, used only as a local filter")
    ap.add_argument("--labels", type=Path, default=Path("data/labels/session_intervals.csv"))
    ap.add_argument("--output", required=True, type=Path)
    ap.add_argument("--transition-margin", type=float, default=5.0)
    ap.add_argument("--tshark", default=shutil.which("tshark") or "tshark")
    args = ap.parse_args()
    intervals = intervals_for(args.labels, args.session)
    if not intervals:
        raise SystemExit(f"No interval labels recorded for {args.session}")
    filt = ("wlan.fc.type_subtype == 0x000e && "
            f"wlan.ta == {args.client} && wlan.ra == {args.ap} && "
            "wlan.vht.compressed_beamforming_report.scidx")
    cmd = [args.tshark, "-n", "-r", str(args.capture), "-Y", filt, "-T", "fields",
           "-E", "separator=/t", "-E", "occurrence=a", "-E", "aggregator=;",
           "-e", "frame.time_relative", "-e", "wlan.vht.mimo_control.chanwidth",
           "-e", "wlan.vht.compressed_beamforming_report.scidx"]
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    kept = 0
    with args.output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["session_id", "time_s", "door_state", "label_certainty", "vht_width_code", "tone_count", "scidx", "phi_code", "psi_code", "phi_deg", "psi_deg"])
        for line in result.stdout.splitlines():
            fields = line.split("\t", 2)
            if len(fields) != 3:
                continue
            t = float(fields[0])
            label = state_at(t, intervals, args.transition_margin)
            if label is None:
                continue
            state, certainty = label
            matches = ANGLE_RE.findall(fields[2])
            if not matches:
                continue
            scidx = [int(x[0]) for x in matches]
            phi = [int(x[1]) for x in matches]
            psi = [int(x[2]) for x in matches]
            writer.writerow([args.session, f"{t:.6f}", state, certainty, fields[1], len(scidx),
                             json.dumps(scidx, separators=(",", ":")),
                             json.dumps(phi, separators=(",", ":")),
                             json.dumps(psi, separators=(",", ":")),
                             json.dumps([round(360*(v+0.5)/64, 4) for v in phi], separators=(",", ":")),
                             json.dumps([round(90*(v+0.5)/16, 4) for v in psi], separators=(",", ":"))])
            kept += 1
    print(f"Wrote {kept} labeled BFM reports to {args.output}")
    if kept == 0:
        raise SystemExit("No reports landed inside labeled intervals after transition exclusion")

if __name__ == "__main__":
    main()

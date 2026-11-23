# Door State Sensing from Wi-Fi Beamforming Feedback

This project investigates whether beamforming feedback (BFM) sent by the author's iPhone to a Ruckus access point can distinguish a door-open state from a door-closed state.

## Verified capture setup

- Ubuntu laptop with Intel AX211 Wi-Fi 6E adapter (`iwlwifi`), station interface `wlp0s20f3`, PHY `phy0`.
- A separate virtual monitor interface, `mon0`, is created on `phy0`; the station interface is not converted to monitor mode in place.
- Target AP used for successful captures: Ruckus, channel 44, primary 5220 MHz, monitor width 80 MHz, center 5210 MHz.
- The iPhone's BFM reports were confirmed in the capture and Wireshark decoded per-tone φ/ψ angle values.

## Capture and recovery

Install `iw`, `dumpcap`, and `tshark` while Ubuntu is online. The laptop loses normal Wi-Fi during monitor capture; the iPhone remains connected to the AP.

```bash
if sudo bash scripts/enter_monitor.sh wlp0s20f3 44 80MHz 5220 5210; then
  sudo dumpcap -i mon0 -a duration:720 -w /tmp/door-session.pcapng
fi
sudo bash scripts/recover_managed.sh wlp0s20f3
sudo chown "$USER:$USER" /tmp/door-session.pcapng
```

Run `dumpcap` only after the enter script confirms `mon0` is monitor mode on channel 44 at 80 MHz, center 5210 MHz. Always recover after capture. Keep raw packet captures outside Git.

## Data and current status

Three raw 12-minute captures from the same day are available locally and are excluded from the repository. Session 1 has only a point label note, so its 916 extracted phone reports are retained as unlabeled data. Sessions 2 and 3 have interval labels. Only selected BFM reports from the user's phone are included as derived data.

- Session 2: closed from 0–65 s; open from 65 s to end, based on the supplied notes.
- Session 3: open from 0–83 s; closed from 83 s to end, based on the supplied notes.
- After a 5-second transition margin, the extractor yielded 648 session-2 reports (4 closed / 644 open) and 1,636 session-3 reports (76 open / 1,560 closed).

The current data is highly imbalanced within each session, collected on one day, and depends on the assumption that no later unreported state changes occurred. These are collection limitations, not results to hide. Collect balanced alternating blocks across more sessions and days before final evaluation. Split by whole session/day; report a confusion matrix and failure cases.

## Decode

The captured phone reports are VHT compressed BFM. The monitor was tuned to 80 MHz, while observed reports included 40 MHz VHT feedback (108 tones); one report in session 3 had 20 MHz feedback (52 tones). The HW4 Part 3 script is an HE 40 MHz example and is retained only as a reference.

```bash
python3 code/extract_bfm.py \
  --capture /path/to/local/capture.pcapng \
  --session day1-session2 \
  --client PHONE_MAC --ap AP_BSSID \
  --labels data/labels/session_intervals.csv \
  --output data/derived/session.csv
```

The MAC arguments are local display filters and are not written into derived output. Use vendor plus short device names in any paper; do not publish raw captures or full MAC addresses.

## Layout

- `scripts/`: monitor mode and managed-mode recovery.
- `code/`: BFM extraction and HW4 reference analysis.
- `data/labels/`: timestamped door-state intervals.
- `data/derived/`: selected phone BFM data, no raw capture files.
- `docs/`: capture setup and sanitized troubleshooting log.
- `paper/`: paper source/PDF to be added.

## Exploratory processing

The extractor, window maker, baseline, and figures use Python's standard library (plus `tshark` for PCAP decoding):

```bash
python3 code/make_windows.py data/derived/day1-session2.csv data/derived/day1-session3.csv \
  --window-seconds 30 --min-reports 5 --min-purity 0.8 \
  --output data/derived/windows-30s.csv
python3 code/evaluate_loso.py data/derived/windows-30s.csv \
  --output data/derived/exploratory_loso.json
python3 code/plot_bfm_heatmaps.py data/derived/day1-session2.csv \
  --output paper/figures/session2_phi_heatmap.svg
```

The current window data has 35 windows: session 2 contributes 14 open windows; session 3 contributes 19 closed and 2 open windows. The exploratory leave-one-session-out baseline has no valid two-class training/test coverage and is explicitly not a final evaluation.

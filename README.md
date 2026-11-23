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

The optional `scripts/capture_session.sh` helper scans for a target phone and captures a single state. It requires `PHONE_MAC` to be entered locally at runtime; the address is not stored in the repository. Record the label and setup notes for each capture.

## Data and current status

Five collection blocks from 23 November 2026 are represented in derived data: the original three 12-minute sessions plus two new paired experiments, each with separate five-minute open and closed captures. Raw PCAP files are local only and excluded from this package. Session 1 has only a point label note, so its 916 extracted phone reports remain unlabeled. The two original labeled sessions use a single reported transition each; the four new captures are single-state runs labeled from the user's capture notes.

- Session 2: closed from 0–65 s; open from 65 s to end, based on the supplied notes.
- Session 3: open from 0–83 s; closed from 83 s to end, based on the supplied notes.
- After a 5-second transition margin, the extractor yielded 648 session-2 reports (4 closed / 644 open) and 1,636 session-3 reports (76 open / 1,560 closed).
- New five-minute captures: env1 open 1,504 reports; env1 closed 3,183; env2 open 2,303; env2 closed 2,090. All four pass the phone-to-AP VHT category-21 BFM filter. Env1's open and closed captures used different Ruckus AP radios; env2 used the same AP radio for both states.

The derived dataset now has 11,364 labeled reports across the original interval-labeled sessions and four new single-state captures, plus 916 unlabeled reports. All data is from one day. The two original sessions remain imbalanced and partly rely on assumed end states; the new five-minute captures provide balanced class coverage, but env1 changes AP radio with door state. Current evaluation is exploratory only. Collect a matched session on a different day before final evaluation; split by whole capture/session and report a confusion matrix and failure cases.

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
  data/derived/day1-env1-open.csv data/derived/day1-env1-closed.csv \
  data/derived/day1-env2-open.csv data/derived/day1-env2-closed.csv \
  --window-seconds 30 --min-reports 5 --min-purity 0.8 \
  --output data/derived/windows-30s-current.csv
python3 code/evaluate_loso.py data/derived/windows-30s-current.csv \
  --output data/derived/exploratory_loso_current.json
python3 code/evaluate_group_holdout.py data/derived/windows-30s-current.csv \
  --test-sessions day1-env2-open day1-env2-closed \
  --output data/derived/exploratory_env2_holdout.json
python3 code/plot_bfm_heatmaps.py data/derived/day1-session2.csv \
  --output paper/figures/session2_phi_heatmap.svg
```

The updated window data has 75 windows. Capture-level leave-one-session-out folds average 22.0% accuracy, but most held-out captures contain one class. A paired env2 holdout has 20 test windows (10 per class) and 95.0% accuracy (closed: 10/10; open: 9/10); it is still a same-day exploratory result, and env1 changes AP radio with door state. Neither result is final performance. The different-day session is still needed for a credible generalization evaluation.

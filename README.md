# Door State Sensing from Wi-Fi Beamforming Feedback

This project investigates whether beamforming feedback (BFM) sent by the author's iPhone to a Ruckus access point can distinguish a door-open state from a door-closed state.

## Verified capture setup

- Ubuntu laptop with Intel AX211 Wi-Fi 6E adapter (`iwlwifi`), station interface `wlp0s20f3`, PHY `phy0`.
- A separate virtual monitor interface, `mon0`, is created on `phy0`; the station interface is not converted to monitor mode in place.
- Target AP used for the final day-3 captures: Ruckus, channel 64, primary 5320 MHz, monitor width 80 MHz, center 5290 MHz.
- The iPhone's BFM reports were confirmed in the capture and Wireshark decoded per-tone φ/ψ angle values.

## Capture and recovery

Install `iw`, `dumpcap`, and `tshark` while Ubuntu is online. The laptop loses normal Wi-Fi during monitor capture; the iPhone remains connected to the AP.

```bash
export PHONE_MAC='YOUR_PHONE_WIFI_MAC'
bash scripts/capture_session.sh open 300 day3
# Set the door state to closed while preserving phone placement and traffic.
bash scripts/capture_session.sh closed 300 day3
```

The helper checks the known monitor configuration, captures for the requested duration, and invokes managed-mode recovery on exit. Keep raw packet captures outside Git.

The `scripts/capture_session.sh` helper captures a single labeled state using the verified channel-64 configuration. It requires `PHONE_MAC` to be entered locally at runtime; the address is not stored in the repository. Record the label and setup notes for each capture.

## Final held-out evaluation

The final test set contains two five-minute open/closed capture pairs collected on 24 November 2026. All four captures used the observed Ruckus BSSID on channel 64. After filtering to the author’s iPhone VHT BFM reports, the four files contain 2,577 open, 3,106 closed, 2,341 open, and 2,770 closed reports. The raw PCAPs remain local and are excluded by `.gitignore`.

Windows are 30 seconds long and are split by complete capture. Training uses the 75 existing 23 November windows; testing uses 39 windows from all four 24 November captures (19 open and 20 closed). The standardized nearest-centroid baseline obtained 39/39 correct predictions (100.0%): closed [20, 0] and open [0, 19], where rows are actual and columns are predicted. This result is a different-day holdout, but the files are still separate single-state blocks; the paper discusses that remaining confound.

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

## Reproduce the final processing

The extractor, window maker, baseline, and figures use Python's standard library (plus `tshark` for PCAP decoding):

```bash
python3 code/make_windows.py data/derived/day1-session2.csv data/derived/day1-session3.csv \
  data/derived/day1-env1-open.csv data/derived/day1-env1-closed.csv \
  data/derived/day1-env2-open.csv data/derived/day1-env2-closed.csv \
  data/derived/day3-pair1-open.csv data/derived/day3-pair1-closed.csv \
  data/derived/day3-pair2-open.csv data/derived/day3-pair2-closed.csv \
  --window-seconds 30 --min-reports 5 --min-purity 0.8 \
  --output data/derived/windows-30s-final.csv
python3 code/evaluate_group_holdout.py data/derived/windows-30s-final.csv \
  --test-sessions day3-pair1-open day3-pair1-closed day3-pair2-open day3-pair2-closed \
  --status different_day_holdout \
  --warning 'Training captures were collected on 23 November; held-out captures were collected on 24 November.' \
  --output data/derived/final_day3_holdout.json
python3 code/plot_confusion_matrix.py data/derived/final_day3_holdout.json \
  --output paper/figures/day3_holdout_confusion_matrix.svg
```

The final output contains 114 labeled windows. The archived day-1 diagnostics remain available for comparison, but `final_day3_holdout.json` is the reportable evaluation: a complete different-day holdout with both classes represented.

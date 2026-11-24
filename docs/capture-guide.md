# Door-state BFM capture guide

This guide records the verified setup for the apartment Ruckus AP and the author's iPhone. Keep raw capture files local; the shared apartment network contains other residents' traffic.

## Known-good setup

- Ubuntu adapter: Intel AX211 / `iwlwifi`; station interface `wlp0s20f3`; PHY `phy0`.
- Use separate virtual monitor interface `mon0`; converting `wlp0s20f3` in place gave zero-packet runs.
- Target AP: Ruckus, channel 44 / 5220 MHz, monitor width 80 MHz / center 5210 MHz.
- `iw` explicit-frequency syntax on this machine requires numeric width `80`: the script accepts `80MHz` and translates it.
- The AP/client BFM report itself advertises VHT report width in the frame; this is separate from monitor radio tuning.

## Capture one labeled session

Connect the phone to the target Ruckus AP and run a consistent downlink workload (same video throughout). Keep phone, AP, laptop, and door geometry fixed. Start the session with one door state, then alternate every 60 seconds. Record each state transition as elapsed seconds from capture start. Exclude a 5-second margin on both sides of each transition when labeling.

```bash
cd ~/Downloads
if sudo bash ./enter_monitor.sh wlp0s20f3 44 80MHz 5220 5210; then
  sudo dumpcap -i mon0 -a duration:720 -w /tmp/door-dayN-sessionN.pcapng
fi
sudo bash ./recover_managed.sh wlp0s20f3
sudo chown ubuntu:ubuntu /tmp/door-dayN-sessionN.pcapng
```

Check the `mon0` output says channel 44, width 80 MHz, center1 5210 MHz before capturing. If setup fails, do not start `dumpcap`; run recovery. Store raw `.pcapng` files outside Git and outside the shared repository.

## Verify and extract own-device BFM

```bash
tshark -r /path/to/capture.pcapng \
  -Y 'wlan.ta == PHONE_MAC && wlan.fc.type_subtype == 0x000e'
```

Use the repository extractor to export only the selected phone-to-AP VHT BFM reports and apply the timestamp labels:

```bash
python3 code/extract_bfm.py \
  --capture /path/to/local/capture.pcapng \
  --session day1-session2 \
  --client PHONE_MAC --ap AP_BSSID \
  --labels data/labels/session_intervals.csv \
  --output data/derived/day1-session2.csv
```

Replace `PHONE_MAC` and `AP_BSSID` locally; do not put the full addresses in public documentation. The extractor writes per-report SCIDX, phi/psi codes, angle values, report-width code, and label certainty. It drops unlabeled reports and a five-second margin around recorded transitions.

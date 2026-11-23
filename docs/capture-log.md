# BFM monitor capture log — 23 November 2026

## Result

A 60-second monitor-mode capture on channel 44 successfully captured compressed beamforming feedback (BFM) sent by the target iPhone to the Ruckus access point. The verified file was `/tmp/mon0-ch44-active.pcapng`.

- Capture interface: `mon0`, created on `phy0`
- Primary interface: `wlp0s20f3` (kept available for managed-mode recovery)
- Channel: 44
- Primary frequency: 5220 MHz
- Channel width: 80 MHz
- Center frequency: 5210 MHz
- Packets captured by `dumpcap`: 49,497; packets dropped: 0
- Capture file timestamps: 2026-11-23 00:23:56.654337 UTC through 00:24:56.614235 UTC
- BFM reports from the iPhone: 22 (`wlan.fc.type_subtype == 0x000e`)
- NDPA frames in the full capture: 24 (`wlan.fc.type_subtype == 0x0015`)
- Frames involving the iPhone address in the full capture: 11,261
- Approximate BFM rate in this session: 22 / 60 = 0.37 reports per second

The 22 BFM reports were transmitted by the iPhone to the Ruckus AP. Wireshark decoded a report’s feedback matrix into per-subcarrier φ11 and ψ21 angle values. This confirms both packet capture and report decoding for this AP/client pair.

## Local device details

- Ubuntu Wi-Fi interface: `wlp0s20f3`
- PHY: `phy0` (`iw` reports `wiphy 0`)
- Adapter: Intel Wi-Fi 6E AX211 160 MHz 2x2, PCI ID `8086:51f0`, subsystem `8086:0094`
- Kernel driver: `iwlwifi`
- The PHY listed monitor mode among supported interface modes.
- A P2P-device interface also existed on `phy0`.
- The SSID was `Velocity Wi-Fi`; the confirmed capture AP was a Ruckus AP on channel 44.

Local correlation addresses (keep this section private; replace with vendor plus short device names before sharing or publishing):

- iPhone Wi-Fi address: `[REDACTED-MAC]`
- Ruckus AP BSSID used in the successful capture: `[REDACTED-MAC]`

The apartment Wi-Fi scan showed multiple AP radios advertising `Velocity Wi-Fi` on different channels, including 11, 44, 60, 108, and 124. The phone was confirmed on the channel-44 Ruckus AP for the successful run. The scan command was:

```bash
nmcli -f SSID,BSSID,CHAN,FREQ,SIGNAL dev wifi list
```

## Why the separate `mon0` interface was used

Changing the primary station interface `wlp0s20f3` in place to monitor mode repeatedly produced zero received packets in the tests. The adapter accepted the monitor type and channel, but those attempts did not yield usable BFM captures. A later test using `HT20` did capture packets, but an in-place mode switch was not the reliable setup.

The working arrangement leaves `wlp0s20f3` as the primary station interface, brings it down during capture, and creates a separate virtual monitor interface named `mon0` on the same PHY. The capture then runs on `mon0`. Recovery deletes `mon0`, brings the primary interface back up, and restarts services that were active before capture.

The script saves service state under `/var/tmp/bfm-monitor-<uid>-wlp0s20f3.state`. If setup fails after this state is saved, run recovery before another attempt.

## Important `iw` syntax detail

The installed `iw` accepts channel widths in two forms depending on the command:

- `iw dev mon0 set channel 44 HT20` for a 20 MHz channel.
- For explicit 80 MHz frequency tuning, this installed version requires a numeric width: `iw dev mon0 set freq 5220 80 5210`.

Passing `80MHz` to `set freq` produced an `iw` usage error. The updated `enter_monitor.sh` accepts the familiar width token `80MHz` plus primary and center frequencies, then translates the width to numeric `80` for the explicit-frequency command. The successful `iw dev mon0 info` output was:

```text
Interface mon0
type monitor
channel 44 (5220 MHz), width: 80 MHz, center1: 5210 MHz
```

## Exact successful 80 MHz capture commands

The following sequence produced the 60-second BFM capture. Keep the iPhone connected to the target AP and generate steady downlink traffic on the phone while capturing (the test used an active-traffic session).

```bash
cd ~/Downloads
if sudo bash ./enter_monitor.sh wlp0s20f3 44 80MHz 5220 5210; then
  sudo dumpcap -i mon0 -a duration:60 -w /tmp/mon0-ch44-active.pcapng
fi
sudo bash ./recover_managed.sh wlp0s20f3
sudo chown ubuntu:ubuntu /tmp/mon0-ch44-active.pcapng
```

Only run `dumpcap` if the enter script exits successfully and reports the expected channel and width. Recovery should run after capture, including after an interrupted capture. The computer has no normal Wi-Fi internet access while monitor capture is active; the phone remains associated to the AP.

The preceding 15-second setup check used the same channel and width and captured 8,315 packets with zero drops, but it contained no BFM reports from the phone. The 60-second active-traffic capture produced the 22 reports.

## How the BFM result was verified

With the capture file readable by the Ubuntu user, this filter listed compressed BFM reports transmitted by the iPhone:

```bash
tshark -r /tmp/mon0-ch44-active.pcapng \
  -Y 'wlan.ta == [REDACTED-MAC] && wlan.fc.type_subtype == 0x000e'
```

It returned 22 frames. The displayed receiver was the Ruckus AP. A broader check for iPhone traffic used:

```bash
tshark -r /tmp/mon0-ch44-active.pcapng \
  -Y 'wlan.addr == [REDACTED-MAC]'
```

A filter for all NDPA frames was:

```bash
tshark -r /tmp/mon0-ch44-active.pcapng \
  -Y 'wlan.fc.type_subtype == 0x0015'
```

The BFM filter is the decisive check for reports from the phone; NDPA frames are sounding announcements and may be sent by the AP rather than the phone.

## Troubleshooting history and lessons

- The interface’s original managed-mode channel changed during the troubleshooting period: it was observed on channels 124 and 108. The nearby scan also showed multiple `Velocity Wi-Fi` radios. Capture must be tuned to the AP radio/channel used by the phone; SSID alone is not enough when the same SSID is broadcast on several radios.
- A command containing the literal placeholder `<ACTIVE_CHANNEL>` did not execute the monitor script. Bash treated `<` as input redirection and reported `ACTIVE_CHANNEL: No such file or directory`. The following `dumpcap` therefore ran in managed mode and captured 5,081 packets. That was not a monitor-mode result.
- The script initially defaulted to `20MHz`; `iw set channel` rejected that token. The correct 20 MHz token is `HT20`. The script default was changed to `HT20`.
- The `mon0` setup initially passed `80MHz` to `iw set freq`, which this installed `iw` rejected. The explicit-frequency form was corrected to pass numeric `80`.
- Do not continue to `dumpcap` if setup prints an `iw` usage error or fails to show the expected monitor interface/channel/width. Recover first, fix the setup, then retry.
- A root-owned capture file may be unreadable to ordinary `tshark`; change ownership after recovery with `sudo chown ubuntu:ubuntu <capture-file>`.

## Data handling and next project step

The raw `.pcapng` files stay local and must not be pushed to Git. They can contain traffic from other apartment Wi-Fi clients. For project data, extract and retain only the target phone’s BFM reports and derived features, associate reports with door-state labels from timestamp notes, and identify devices in the paper as vendor plus a short name rather than full MAC addresses.

The current demonstrated report rate is about 0.37 reports/s. Use windows long enough to contain multiple reports, collect repeated open/closed periods in multiple sessions, and hold out complete sessions (preferably a different day) for evaluation. The HW4 angle parser was written for a specific 40 MHz HE format; verify the 80 MHz report’s format before using that parser unchanged.

## Project collection: day1-session1

User-provided label note: `45: closed door`. Logged as an elapsed-time marker at 00:45 with the door closed; this does not establish the full interval boundaries for the closed label. Add an end time or next transition marker before assigning packet labels to the interval.

Capture command and setup were the successful channel-44 / 80 MHz `mon0` procedure above, with a 720-second limit and output `/tmp/door-day1-session1.pcapng`.

- `dumpcap` reported 389,492 packets and zero drops.
- The capture spans 2026-11-23 00:36:19.619 UTC to 00:48:19.616 UTC (12 minutes).
- The capture contains 916 compressed BFM reports transmitted by the iPhone (about 1.27 reports/s) and 78 NDPA frames overall.
- The first and last detected iPhone BFM report offsets were approximately 12.747 s and 638.443 s into the capture.
- Raw capture remains at `/tmp/door-day1-session1.pcapng` and should stay local.

## Project collection: day1-session2

The second 12-minute capture completed on `mon0` at channel 44, 80 MHz, center frequency 5210 MHz.

- Capture file: `/tmp/door-day1-session2.pcapng`
- `dumpcap` reported 827,793 packets and zero drops.
- The recovery script removed `mon0` and restored managed Wi-Fi.
- Label timeline: 00:00–01:05 closed; open begins at 01:05. The open interval continues until the next noted transition.
- Phone-specific BFM count is not yet recorded here.
- The terminal command attempted to change ownership of `door-day1-session1.pcapng` instead of session 2. Session 2 may therefore remain root-owned until corrected.

## Experiment limitation and future work

All initial collection sessions are being gathered on the same day. This limits evidence that the door-state model generalizes across days, changing multipath conditions, or other environmental conditions. In the paper, report this as a limitation; session-held-out evaluation can still reduce leakage, but it is not a substitute for a different-day test. Future collection should repeat both door states on multiple days and under varied conditions while keeping the phone/AP geometry documented.

A final same-day session is planned as `day1-session3`; record its actual start, end, and door-state transition times when available.

## Additional labeled captures — 23 November 2026

Four five-minute single-state captures were collected after the earlier 12-minute sessions. Raw captures remain local under `/tmp` and are not included in the repository. Each was checked with the phone-transmitter, VHT action-category 21 filter before extraction.

| Capture | UTC interval | Door label | Phone BFM reports | AP consistency |
|---|---|---|---:|---|
| `door-open-5m.pcapng` | 16:45:28–16:50:28 | Open | 1,504 | AP radio A |
| `door-closed-5m.pcapng` | 16:55:03–17:00:03 | Closed | 3,183 | AP radio B (different from open) |
| `door-open-env2.pcapng` | 17:18:18–17:23:17 | Open | 2,303 | AP radio A |
| `door-closed-env2.pcapng` | 17:25:51–17:30:49 | Closed | 2,090 | AP radio A (same as paired open capture) |

The first pair is confounded by a change in AP radio between states. The second pair uses the same AP radio and provides the cleaner same-day comparison. The four labels are single-state reports from the user; each capture contributes 300 seconds. Derived report CSVs omit MAC addresses. The original raw test `/tmp/mon0-ch44-active.pcapng` captured 10,253 packets with zero drops but contained no frames matching the logged phone address, so it is not included in the labeled dataset.

The new derived files are `data/derived/day1-env1-open.csv`, `day1-env1-closed.csv`, `day1-env2-open.csv`, and `day1-env2-closed.csv`. Their report counts are 1,504, 3,183, 2,303, and 2,090, respectively. Do not publish raw captures or full device addresses.

## Project sessions extracted for the repository

Raw source PCAPs remain outside this repo. The local capture log was extended with these results:

- `day1-session2`: 827,793 captured packets, zero drops, 655 iPhone BFM reports before transition exclusion. After the five-second margin, 648 labeled reports remained (4 closed, 644 open).
- `day1-session3`: 925k packets by `capinfos`, 1,667 iPhone BFM reports before transition exclusion. After the margin, 1,636 labeled reports remained (76 open, 1,560 closed).
- Both sessions were on 23 November 2026, channel 44, 80 MHz monitor tuning, center 5210 MHz. Available label transitions are 01:05 (closed to open) in session 2 and 01:23 (open to closed) in session 3. End-of-session states assume no further unreported changes.
- `day1-session3` produced 1,666 VHT reports with 108 tones and one report with 52 tones. The report's VHT channel-width field is captured separately from the monitor tuning width.

The label distribution is highly imbalanced and correlated with session: session 2 is almost entirely open after the transition; session 3 is almost entirely closed after its transition. Collect more alternating blocks and additional days before treating any model metric as a final result.

## Recovered project session 1

The raw file `door-day1-session1.pcapng` was recovered from Downloads and copied to the local archive at `~/Documents/bfm-data/door-day1-session1.pcapng`; it is still excluded from Git.

- Capture timestamps: 2026-11-23 00:36:19.619 UTC through 00:48:19.616 UTC; 12 minutes.
- 389,492 packets, zero drops; radiotap frequency 5220 MHz (channel 44).
- 916 BFM reports from the target iPhone to the Ruckus AP and 78 NDPA frames overall.
- The notes say `45: closed door`. This is kept as a point observation at 00:45, not expanded into an interval because the surrounding state boundaries are unknown.
- The target AP BSSID differed from the later sessions' AP radio; all addresses remain redacted in this document.
- The 916 BFM reports are exported in `data/derived/day1-session1-unlabeled.csv` for exploration only; they are excluded from labeled windows.

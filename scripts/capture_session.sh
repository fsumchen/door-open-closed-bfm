#!/usr/bin/env bash
set -euo pipefail

IFACE="wlp0s20f3"
PHONE_MAC="${PHONE_MAC:-}"
STATE="${1:-}"          # "open" or "closed"
DURATION="${2:-300}"    # seconds (default: 300 = 5 mins)
TAG="${3:-day2}"        # optional environment label

# Verified on 24 November 2026 by a monitor scan for the target iPhone:
# channel 64, primary 5320 MHz, 80 MHz block centered at 5290 MHz.
CHANNEL=64
FREQ_MHZ=5320
CENTER1_MHZ=5290

if [[ "$STATE" != "open" && "$STATE" != "closed" ]]; then
  echo "Usage: bash scripts/capture_session.sh <open|closed> [duration_sec] [env_tag]"
  exit 1
fi
if [[ -z "$PHONE_MAC" ]]; then
  echo "Set PHONE_MAC to the phone's current Wi-Fi address for this network; do not commit the address." >&2
  echo 'Enter it locally with: read -r -p "Phone Wi-Fi address: " PHONE_MAC; export PHONE_MAC' >&2
  echo "Then rerun: bash scripts/capture_session.sh open 300 env1" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
OUT_DIR="$REPO_DIR/captures"
mkdir -p "$OUT_DIR"

TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
TMP_FILE="/tmp/door_${STATE}_${TAG}_${TIMESTAMP}.pcapng"
FINAL_FILE="$OUT_DIR/door_${STATE}_${TAG}_${TIMESTAMP}.pcapng"

cleanup() {
  sudo bash "$SCRIPT_DIR/recover_managed.sh" "$IFACE" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "=== 1. Creating monitor interface on channel $CHANNEL ($FREQ_MHZ MHz, 80 MHz center $CENTER1_MHZ MHz) ==="
sudo bash "$SCRIPT_DIR/enter_monitor.sh" "$IFACE" "$CHANNEL" 80MHz "$FREQ_MHZ" "$CENTER1_MHZ"
iw dev mon0 info | grep -E "channel|width"

echo "=== 2. Capturing [$STATE | $TAG] for ${DURATION}s ==="
# Capture the monitor interface without a BPF address filter. The verified runs
# in capture-log.md used this form; the phone-only filter is applied afterward.
sudo dumpcap -i mon0 -a "duration:${DURATION}" -w "$TMP_FILE"

sudo bash "$SCRIPT_DIR/recover_managed.sh" "$IFACE" >/dev/null
sudo mv "$TMP_FILE" "$FINAL_FILE"
sudo chown ubuntu:ubuntu "$FINAL_FILE"

BFM_COUNT=$(tshark -r "$FINAL_FILE" -Y "wlan.ta == $PHONE_MAC && wlan.fc.type_subtype == 0x000e && wlan.fixed.category_code == 21" | wc -l | tr -d ' ')
echo "=== Done! Saved $FINAL_FILE ($BFM_COUNT VHT BFM frames) ==="

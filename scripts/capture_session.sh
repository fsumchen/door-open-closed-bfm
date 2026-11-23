#!/usr/bin/env bash
set -euo pipefail

IFACE="wlp0s20f3"
PHONE_MAC="${PHONE_MAC:-}"
STATE="${1:-}"          # "open" or "closed"
DURATION="${2:-300}"    # seconds (default: 300 = 5 mins)
TAG="${3:-env1}"        # optional environment label

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

get_80mhz_params() {
  case "$1" in
    36)  echo "5180 5210" ;;
    40)  echo "5200 5210" ;;
    44)  echo "5220 5210" ;;
    48)  echo "5240 5210" ;;
    52)  echo "5260 5290" ;;
    56)  echo "5280 5290" ;;
    60)  echo "5300 5290" ;;
    64)  echo "5320 5290" ;;
    100) echo "5500 5530" ;;
    104) echo "5520 5530" ;;
    108) echo "5540 5530" ;;
    112) echo "5560 5530" ;;
    116) echo "5580 5610" ;;
    120) echo "5600 5610" ;;
    124) echo "5620 5610" ;;
    128) echo "5640 5610" ;;
    132) echo "5660 5690" ;;
    136) echo "5680 5690" ;;
    140) echo "5700 5690" ;;
    144) echo "5720 5690" ;;
    149) echo "5745 5775" ;;
    153) echo "5765 5775" ;;
    157) echo "5785 5775" ;;
    161) echo "5805 5775" ;;
    *)   echo "" ;;
  esac
}

echo "=== 1. Scanning 5 GHz channels for phone ($PHONE_MAC) ==="
echo "(Make sure video/download is actively playing on your phone)"
sudo bash "$SCRIPT_DIR/enter_monitor.sh" "$IFACE" 44 HT20 >/dev/null

DETECTED_CH=""
CANDIDATES=(153 104 124 44 56 60 100 132 140 36 40 48 52 64 108 112 116 120 128 136 144 149 157 161)

for ch in "${CANDIDATES[@]}"; do
  sudo iw dev mon0 set channel "$ch" HT20 2>/dev/null || continue
  if sudo timeout 2.5 tshark -i mon0 -Y "wlan.addr == $PHONE_MAC" -c 1 >/dev/null 2>&1; then
    DETECTED_CH="$ch"
    break
  fi
done

if [[ -z "$DETECTED_CH" ]]; then
  echo "ERROR: Could not find $PHONE_MAC on any 5 GHz channel."
  exit 1
fi

PARAMS="$(get_80mhz_params "$DETECTED_CH")"
FREQ_MHZ="$(echo "$PARAMS" | awk '{print $1}')"
CENTER1_MHZ="$(echo "$PARAMS" | awk '{print $2}')"

echo "=== 2. Switching mon0 directly to Channel $DETECTED_CH ($FREQ_MHZ MHz, 80MHz center $CENTER1_MHZ MHz) ==="
sudo iw dev mon0 set freq "$FREQ_MHZ" 80 "$CENTER1_MHZ"
iw dev mon0 info | grep -E "channel|width"

echo "=== 3. Capturing [$STATE | $TAG] for ${DURATION}s ==="
sudo dumpcap -i mon0 -f "wlan host $PHONE_MAC" -a "duration:${DURATION}" -w "$TMP_FILE"

sudo bash "$SCRIPT_DIR/recover_managed.sh" "$IFACE" >/dev/null
sudo mv "$TMP_FILE" "$FINAL_FILE"
sudo chown ubuntu:ubuntu "$FINAL_FILE"

BFM_COUNT=$(tshark -r "$FINAL_FILE" -Y "wlan.ta == $PHONE_MAC && wlan.fc.type_subtype == 0x000e && wlan.fixed.category_code == 21" | wc -l | tr -d ' ')
echo "=== Done! Saved $FINAL_FILE ($BFM_COUNT VHT BFM frames) ==="

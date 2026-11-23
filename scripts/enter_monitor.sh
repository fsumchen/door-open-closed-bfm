#!/usr/bin/env bash
set -Eeuo pipefail
if [[ $EUID -ne 0 ]]; then echo "Run with sudo: sudo $0 INTERFACE CHANNEL [WIDTH [FREQ_MHZ CENTER1_MHZ]]" >&2; exit 1; fi
if [[ $# -lt 2 || $# -gt 5 || ( $# -eq 4 ) ]]; then echo "Usage: sudo $0 INTERFACE CHANNEL [WIDTH [FREQ_MHZ CENTER1_MHZ]]" >&2; exit 2; fi
iface=$1; channel=$2; width=${3:-HT20}
[[ $iface =~ ^[[:alnum:]_.:-]+$ && $channel =~ ^[0-9]+$ ]] || { echo "Invalid interface or channel" >&2; exit 2; }
if [[ $# -eq 5 ]]; then
  freq=$4; center1=$5
  [[ $freq =~ ^[0-9]+$ && $center1 =~ ^[0-9]+$ && $width == 80MHz ]] || { echo "FREQ_MHZ and CENTER1_MHZ are numeric and require WIDTH=80MHz" >&2; exit 2; }
fi
command -v iw >/dev/null || { echo "iw is required" >&2; exit 1; }
ip link show dev "$iface" >/dev/null || { echo "No interface named $iface" >&2; exit 1; }
phy=$(iw dev "$iface" info | awk '$1=="wiphy" {print "phy"$2; exit}')
[[ -n $phy ]] || { echo "Could not determine PHY for $iface" >&2; exit 1; }
state="/var/tmp/bfm-monitor-${SUDO_UID:-0}-${iface}.state"
[[ ! -e $state ]] || { echo "Saved state exists; run recover_managed.sh $iface first" >&2; exit 1; }
nm_active=0; wpas_active=0
systemctl is-active --quiet NetworkManager && nm_active=1 || true
systemctl is-active --quiet wpa_supplicant && wpas_active=1 || true
printf '%s\n%s\n%s\n%s\n' "$iface" "$phy" "$nm_active" "$wpas_active" > "$state"; chmod 600 "$state"
trap 'echo "Setup failed; run sudo $(dirname "$0")/recover_managed.sh '"$iface"'" >&2' ERR
(( nm_active == 0 )) || systemctl stop NetworkManager
(( wpas_active == 0 )) || systemctl stop wpa_supplicant
pkill -x wpa_supplicant 2>/dev/null || true
ip link set dev "$iface" down
if iw dev mon0 info >/dev/null 2>&1; then iw dev mon0 del; fi
iw phy "$phy" interface add mon0 type monitor
ip link set dev mon0 up
if [[ $# -eq 5 ]]; then
  # This iw version's explicit-frequency syntax takes numeric width (80),
  # while the set-channel syntax accepts the token 80MHz.
  iw dev mon0 set freq "$freq" 80 "$center1"
else
  iw dev mon0 set channel "$channel" "$width"
fi
iw dev mon0 info
trap - ERR
echo "Monitor mode ready on mon0 (PHY $phy). Capture with: sudo dumpcap -i mon0 ..."

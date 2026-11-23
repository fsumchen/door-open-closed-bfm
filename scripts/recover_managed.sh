#!/usr/bin/env bash
set -Eeuo pipefail
if [[ $EUID -ne 0 ]]; then echo "Run with sudo: sudo $0 INTERFACE" >&2; exit 1; fi
[[ $# -eq 1 ]] || { echo "Usage: sudo $0 INTERFACE" >&2; exit 2; }
iface=$1
state="/var/tmp/bfm-monitor-${SUDO_UID:-0}-${iface}.state"
if [[ -r $state ]]; then
  mapfile -t saved < "$state"
  [[ ${#saved[@]} -eq 4 && ${saved[0]} == "$iface" ]] || { echo "Invalid saved state; leaving it in place" >&2; exit 1; }
  phy=${saved[1]}; nm_active=${saved[2]}; wpas_active=${saved[3]}
else
  echo "No saved state for $iface; attempting managed-mode recovery" >&2
  phy=$(iw dev "$iface" info 2>/dev/null | awk '$1=="wiphy" {print "phy"$2; exit}' || true)
  nm_active=1; wpas_active=0
fi
ip link set dev mon0 down 2>/dev/null || true
if iw dev mon0 info >/dev/null 2>&1; then iw dev mon0 del; fi
ip link set dev "$iface" down 2>/dev/null || true
iw dev "$iface" set type managed 2>/dev/null || true
ip link set dev "$iface" up
if [[ $nm_active == 1 ]]; then systemctl start NetworkManager; nmcli device set "$iface" managed yes || true; fi
if [[ $wpas_active == 1 ]]; then systemctl start wpa_supplicant; fi
rm -f "$state"
echo "Removed mon0 and restored managed Wi-Fi on $iface."

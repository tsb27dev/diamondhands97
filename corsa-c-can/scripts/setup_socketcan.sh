#!/usr/bin/env bash
# Uso: sudo scripts/setup_socketcan.sh [can0] [500000]
# Adaptadores SLCAN (CANable, USB-serial): sudo slcand -o -c -s6 /dev/ttyACM0 can0 && sudo ip link set can0 up
set -euo pipefail
IF=${1:-can0}; BR=${2:-500000}
ip link set "$IF" down 2>/dev/null || true
# listen-only: NUNCA transmite -> seguro para a 1.ª captura
ip link set "$IF" type can bitrate "$BR" listen-only on
ip link set "$IF" up
echo "$IF a ${BR} bit/s em modo listen-only"

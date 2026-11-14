#!/usr/bin/env bash
# Testa débitos comuns em listen-only e diz qual recebe tramas.  Uso: sudo scripts/probe_bitrate.sh can0
IF=${1:-can0}
for BR in 500000 250000 125000 100000 95238 83333 33333; do
  ip link set "$IF" down 2>/dev/null
  ip link set "$IF" type can bitrate "$BR" listen-only on 2>/dev/null || { echo "$BR: não suportado"; continue; }
  ip link set "$IF" up
  N=$(timeout 3 candump -n 20 "$IF" 2>/dev/null | wc -l)
  echo "$BR bit/s -> $N tramas em 3 s"
done
ip link set "$IF" down

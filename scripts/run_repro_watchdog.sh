#!/usr/bin/env bash
# Keep the CPU reproduction running until results/p0/s2pinn_repro_seed42.json exists.
# The runner resumes from results/p0/ckpt/ after any interruption.
cd "$(dirname "$0")/.." || exit 1
OUT=results/p0/s2pinn_repro_seed42.json
LOG=results/p0/s2pinn_repro_seed42.stdout
tries=0
while [ ! -f "$OUT" ] && [ "$tries" -lt 20 ]; do
  tries=$((tries + 1))
  echo "[watchdog] $(date -u +%FT%TZ) start attempt $tries" >> "$LOG"
  python3 experiments/p0_reproduce_s2pinn_resumable.py --seed 42 >> "$LOG" 2>&1
  echo "[watchdog] $(date -u +%FT%TZ) runner exited with $?" >> "$LOG"
  sleep 5
done
echo "[watchdog] $(date -u +%FT%TZ) done (result present: $([ -f "$OUT" ] && echo yes || echo no))" >> "$LOG"

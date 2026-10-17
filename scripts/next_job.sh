#!/usr/bin/env bash
# Pop the next command from a queue file (under a lock) and run it in the foreground; exit when it ends.
# Run several copies as tracked background tasks to keep that many jobs in flight. Every queued command
# is a single resumable process that stops itself within two hours.
Q=$1
cmd=$(flock "$Q.lock" bash -c 'l=$(head -n 1 "$0"); [ -n "$l" ] && sed -i 1d "$0"; printf "%s" "$l"' "$Q")
[ -z "$cmd" ] && { echo "queue empty"; exit 0; }
echo "$(date -u +%FT%TZ) $cmd" >> "$Q.taken"
echo "running: $cmd"
bash -c "$cmd"
echo "exit $?: $cmd"

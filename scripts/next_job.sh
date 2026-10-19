#!/usr/bin/env bash
# Pop the next command from a queue file (under a lock) and run it in the foreground; exit when it ends.
# Run several copies (the worker loops) to keep that many jobs in flight. Every queued command is a single
# resumable process. After each job: a non-zero exit is appended to <queue>.errors, and the result rows are
# committed and pushed (scripts/persist_rows.sh, log in <queue dir>/persist.log).
Q=$1
cmd=$(flock "$Q.lock" bash -c 'l=$(head -n 1 "$0"); [ -n "$l" ] && sed -i 1d "$0"; printf "%s" "$l"' "$Q")
[ -z "$cmd" ] && { echo "queue empty"; exit 0; }
echo "$(date -u +%FT%TZ) $cmd" >> "$Q.taken"
echo "running: $cmd"
bash -c "$cmd"
rc=$?
echo "exit $rc: $cmd"
[ $rc -ne 0 ] && echo "$(date -u +%FT%TZ) exit $rc: $cmd" >> "$Q.errors"
"$(dirname "$0")/persist_rows.sh" >> "$(dirname "$Q")/persist.log" 2>&1
exit 0

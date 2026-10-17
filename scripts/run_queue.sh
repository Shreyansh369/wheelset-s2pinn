#!/usr/bin/env bash
# Run the commands of a queue file (one per line) while keeping at most MAXP experiment processes
# (python3 experiments/...) running on the machine, counting processes started by other queues too.
# Usage: scripts/run_queue.sh QUEUE_FILE [MAXP]
Q=$1; MAXP=${2:-4}
while IFS= read -r cmd; do
  [ -z "$cmd" ] && continue
  while [ "$(pgrep -fc '^python3 experiments/')" -ge "$MAXP" ]; do sleep 30; done
  setsid bash -c "$cmd" < /dev/null &
  sleep 20
done < "$Q"
wait
echo QUEUE_DONE > "$Q.done"

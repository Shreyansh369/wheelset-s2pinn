# Row sessions of preregistration v2 (docs/preregistration_v2_addendum.md)

Session sN (N = 1, 2, 3) runs the jobs of `docs/queues_v2/sN.txt` at the pinned commit and pushes result rows
to `claude/rows-sN`. Instructions given to each sibling session (N filled in):

1. Rules.
   - Never edit, add or delete code, config or docs.
   - Never push any branch other than `claude/rows-sN`; never touch `main`; open no pull request.
   - Commit only through `scripts/persist_rows.sh`, which commits `results/**/*.jsonl` and nothing else.
2. Setup.
   - `git checkout -B claude/rows-sN`, then check that `git rev-parse HEAD` equals the pinned commit.
   - Check that `python3 -c "import numpy, scipy, yaml"` works. If it fails, run `pip install -r requirements.txt`.
   - `mkdir -p results/p5/logs results/p4/logs`
   - `cp docs/queues_v2/sN.txt results/p4/logs/queue_v2_sN.txt` (the copy is ignored by git and is consumed by
     the workers).
3. Start 4 worker loops, as one command:

   ```
   for i in 1 2 3 4; do setsid nohup bash -c 'export ROWS_BRANCH=claude/rows-sN; while out=$(scripts/next_job.sh results/p4/logs/queue_v2_sN.txt); echo "$out"; ! echo "$out" | grep -q "queue empty"; do :; done' > results/p4/logs/loop_$i.log 2>&1 < /dev/null & sleep 2; done
   ```
4. Keepalive.
   - Run `sleep 6600; uptime` as a tracked background task, and start it again each time it completes, until the
     queue is empty and no job runs.
   - Schedule a check-in for every 60 minutes with send_later, with the same instructions. At each check-in:
     - Run `uptime` and `pgrep -fa "python3 experiments/"`.
     - If the container restarted (uptime small, no jobs): put the last 4 lines of
       `results/p4/logs/queue_v2_sN.txt.taken` (without the time stamp) back at the front of the queue file (every
       job is resumable), and restart the 4 loops and the keepalive.
     - Run `ROWS_BRANCH=claude/rows-sN scripts/persist_rows.sh` if any `results/**/*.jsonl` is uncommitted.
5. Time stop: at or after 2026-11-03T06:00:00Z, empty the queue file and stop the loops and their jobs (`pkill -f
   next_job.sh; pkill -f "python3 experiments/"`). Then run persist_rows once and stop re-arming. Also stop when
   the queue is empty and the last job has finished.

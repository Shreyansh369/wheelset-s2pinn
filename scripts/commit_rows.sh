#!/usr/bin/env bash
# Commit and push new or changed Monte Carlo result rows (results/**/*.jsonl, *.json), never queue bookkeeping
# and never the kappa sensitivity-SE or diagnostic rows (sing_se*, diag_*), which are committed on their own.
cd "$(dirname "$0")/.."
F=$(git status --porcelain --untracked-files=all | awk '{print $2}' | grep -E '^results/.*\.(jsonl|json)$' | grep -v '/logs/' | grep -v '/sing_se' | grep -v '/diag_')
[ -n "$F" ] && git add -f $F
git diff --cached --quiet || git commit -qm "Run rows (in progress)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01QcCntpHGDKF5PSbkToAw92"
git push -q origin "$(git rev-parse --abbrev-ref HEAD)" 2>&1 | tail -1
git status --short | head -3

#!/usr/bin/env bash
# Commit and push new or changed Monte Carlo result rows (results/**/*.jsonl, *.json), never queue bookkeeping.
cd "$(dirname "$0")/.."
F=$(git status --porcelain --untracked-files=all | awk '{print $2}' | grep -E '^results/.*\.(jsonl|json)$' | grep -v '/logs/')
[ -n "$F" ] && git add -f $F
git diff --cached --quiet || git commit -qm "Run rows (in progress)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01V5EtpPw7FACY4tWAT9s6jG"
git push -q origin "$(git rev-parse --abbrev-ref HEAD)" 2>&1 | tail -1
git status --short | head -3

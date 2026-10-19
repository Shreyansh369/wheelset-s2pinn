#!/usr/bin/env bash
# Commit and push the Monte Carlo result rows (results/**/*.jsonl, never logs) to the work branch, so that they
# reach GitHub even when no session is attached. Called by scripts/next_job.sh after every job. Serialised by
# a repository lock (.git/rows.lock; take the same lock for manual commits). Commits only these
# paths (git commit --only), so anything else staged or modified in the tree is left alone. Diagnostic rows
# (diag_*) go in their own commit. Push: 3 tries with backoff. Never pushes any branch but the work branch.
cd "$(dirname "$0")/.." || exit 1
BR=claude/inspiring-cori-690nu3
exec 9>"$(git rev-parse --git-dir)/rows.lock"
flock -w 600 9 || { echo "$(date -u +%FT%TZ) lock timeout"; exit 1; }
[ "$(git rev-parse --abbrev-ref HEAD)" = "$BR" ] || { echo "$(date -u +%FT%TZ) not on $BR; nothing committed"; exit 1; }
rows=$(git status --porcelain --untracked-files=all -- results | awk '{print $NF}' | grep -E '\.jsonl$' | grep -v '/logs/')
for grp in diag other; do
  if [ $grp = diag ]; then F=$(printf '%s\n' $rows | grep '/diag_'); else F=$(printf '%s\n' $rows | grep -v '/diag_'); fi
  [ -z "$F" ] && continue
  for i in 1 2 3; do
    git add -f -- $F && git commit -q --only -m "Run rows ($grp, automatic)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01QcCntpHGDKF5PSbkToAw92" -- $F && break
    sleep $((2 ** i))
  done
done
for i in 1 2 3; do
  if git push -q origin "$BR" 2>/dev/null; then echo "$(date -u +%FT%TZ) pushed $(git rev-parse --short HEAD)"; exit 0; fi
  sleep $((2 ** i))
done
echo "$(date -u +%FT%TZ) PUSH FAILED after 3 tries"; exit 1

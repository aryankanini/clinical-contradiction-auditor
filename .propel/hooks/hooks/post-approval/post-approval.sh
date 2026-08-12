#!/usr/bin/env bash
# Propel gated-run merge hook. NOT a Claude Code lifecycle hook (unlike the
# context_tracker_* / knowledge_map hooks in this folder, which fire on
# UserPromptSubmit/PostToolUse/etc via settings.json) -- this one is invoked
# explicitly by the calling orchestrator (e.g. concept-validation.md) when a
# CompleteRunStep/SubmitGateDecision response carries a `hook` object.
#
# The server has no repo access and no gh auth, so it emits a directive and
# verifies the receipt this script prints on stdout.
#   post-approval.sh <run_id> <step_id> <decision> <actor> <artifact>...
#
# AUTO_MERGE/BASE come from the response's hook.autoMerge / hook.base.
# Merge policy splits by actor: human approval may auto-merge behind required
# checks; system auto-approval opens a PR and waits.
set -euo pipefail

RUN_ID=${1:?run_id required}; STEP_ID=${2:?step_id required}
DECISION=${3:?decision required}; ACTOR=${4:?actor required}
shift 4
ARTIFACTS=("$@")
AUTO_MERGE=${AUTO_MERGE:-false}
BASE=${BASE:-main}
BRANCH="propel/${RUN_ID}/${STEP_ID}"

if [ ${#ARTIFACTS[@]} -eq 0 ]; then
  echo "no artifacts to commit" >&2; exit 1
fi
command -v gh >/dev/null || { echo "gh CLI not found on PATH" >&2; exit 1; }

# Idempotent: branch name derives from run_id/step_id, so re-runs are safe.
git checkout -b "$BRANCH" 2>/dev/null || git checkout "$BRANCH"

# Explicit paths only -- never `git add -A`. Payoff of the run's frozen
# path_context: scratch files cannot be swept into the commit.
git add -- "${ARTIFACTS[@]}"
git commit -m "propel(${STEP_ID}): ${DECISION} by ${ACTOR} [run:${RUN_ID}]" || true
git push -u origin "$BRANCH"

PR_URL=$(gh pr create --base "$BASE" --head "$BRANCH" \
  --title "Propel ${STEP_ID} — ${RUN_ID}" \
  --body "Approved by ${ACTOR}. Run: ${RUN_ID}. Artifacts: ${ARTIFACTS[*]}" \
  2>/dev/null || gh pr view "$BRANCH" --json url -q .url)

MERGED=false
if [ "$AUTO_MERGE" = "true" ]; then
  # --auto queues behind required checks. NEVER --admin: bypasses the checks
  # being claimed as enforcement.
  gh pr merge "$PR_URL" --squash --auto --delete-branch
  MERGED=queued
fi

printf '{"pr_url":"%s","branch":"%s","sha":"%s","merged":"%s","actor":"%s"}\n' \
  "$PR_URL" "$BRANCH" "$(git rev-parse HEAD)" "$MERGED" "$ACTOR"

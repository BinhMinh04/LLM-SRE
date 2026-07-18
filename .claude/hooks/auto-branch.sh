#!/usr/bin/env bash
# PreToolUse guard (matcher: Edit|Write|Bash). If HEAD is on a protected branch
# (main/master), auto-create and switch to a feature branch before any change
# lands there. No-op if already off main/master or outside a git repo.
cat >/dev/null 2>&1 || true

dir="${CLAUDE_PROJECT_DIR:-$(pwd)}"
git -C "$dir" rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0

branch=$(git -C "$dir" rev-parse --abbrev-ref HEAD 2>/dev/null)
if [[ "$branch" == "main" || "$branch" == "master" ]]; then
  # Fallback only - a properly named feature/fix/chore/... branch should have
  # been created deliberately before this ever fires. Rename or merge this one.
  new_branch="chore/auto-$(date +%Y%m%d-%H%M%S)"
  if git -C "$dir" checkout -b "$new_branch" >/dev/null 2>&1; then
    printf '{"systemMessage":"Protected branch \\"%s\\" detected — auto-created fallback \\"%s\\" before continuing. Rename it to match the task (feature/fix/chore/...) before committing."}' "$branch" "$new_branch"
  fi
fi
exit 0

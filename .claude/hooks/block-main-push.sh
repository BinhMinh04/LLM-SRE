#!/usr/bin/env bash
# PreToolUse guard (matcher: Bash). Denies any `git push` that targets main/master,
# whether because HEAD is currently on that branch or the command explicitly
# references it as a push destination (e.g. `git push origin HEAD:main`).
input=$(cat)
cmd=$(printf '%s' "$input" | jq -r '.tool_input.command // ""' 2>/dev/null)

case "$cmd" in
  *"git push"*) ;;
  *) exit 0 ;;
esac

dir="${CLAUDE_PROJECT_DIR:-$(pwd)}"

protected=false

if [[ "$cmd" =~ (^|[[:space:]:])(main|master)([[:space:]]|$) ]]; then
  # Explicit destination is main/master (e.g. `git push origin main`,
  # `git push origin HEAD:main`) - protected no matter what HEAD is.
  protected=true
else
  # No explicit main/master token. Only fall back to "current branch" when
  # the command doesn't name a different branch explicitly (bare `git push`,
  # `git push origin`, `git push origin HEAD`) - otherwise a push to some
  # other named branch while HEAD happens to be on main must not be blocked.
  rest=$(printf '%s' "$cmd" | sed -E 's/.*git push//; s/(--force-with-lease|--set-upstream|--force|--tags|--verbose|-u|-f|-v)//g')
  explicit_other=false
  for t in $rest; do
    case "$t" in
      origin|HEAD|"") ;;
      *) explicit_other=true ;;
    esac
  done
  if [[ "$explicit_other" == false ]]; then
    branch=$(git -C "$dir" rev-parse --abbrev-ref HEAD 2>/dev/null)
    [[ "$branch" == "main" || "$branch" == "master" ]] && protected=true
  fi
fi

if [[ "$protected" == true ]]; then
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"Direct push to main/master is blocked by repo policy. Push the feature branch and open a PR instead."}}'
fi
exit 0

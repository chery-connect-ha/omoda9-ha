#!/usr/bin/env bash
# tools/pr.sh — the way a change lands in this repository.
#
#   ./tools/pr.sh "<commit message>"                    # branch inferred from the message
#   ./tools/pr.sh -b fix/name-of-the-behaviour "<msg>"  # explicit branch
#   ./tools/pr.sh --continue                            # branch and commit already made
#   ./tools/pr.sh --draft ...                           # open the pull request as a draft
#   ./tools/pr.sh --authorized "<what you were told>" ...   # for agents, see below
#   ./tools/pr.sh --evidence none ...          # backend | not-mine | none — never "hardware"
#
# `master` is protected and the rules say every change goes through a pull request,
# including from the people who wrote the rules. This script is where the gates in
# rules.sh run IN ORDER — and the order is itself a rule: the secret gate runs AFTER the
# commit and BEFORE the push, because against staged-only changes it sees nothing.
#
# You do not have to use this. `git push` and `gh pr create` are in AGENTS.md and work
# fine. This just refuses to let you forget something.
set -uo pipefail
_HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$_HERE/rules.sh"
cd "$R_ROOT"
rules_cmdline "$@"

R_REPO="${OMODA9_REPO:-chery-connect-ha/omoda9-ha}"
BASE="master"

BRANCH=""; MSG=""; CONTINUE=0; DRAFT=0
while [ $# -gt 0 ]; do
  case "$1" in
    -b|--branch)   BRANCH="${2:?}"; shift 2;;
    --continue)    CONTINUE=1; shift;;
    --draft)       DRAFT=1; shift;;
    --authorized)  R_AUTHORIZED="${2:?the sentence with which you were given the go-ahead}"; shift 2;;
    --evidence)    R_EVIDENCE_KIND="${2:?one of: backend | not-mine | none}"; shift 2;;
    -h|--help)     sed -n '2,16p' "$0"; exit 0;;
    -*)            _die "unknown option: $1 (a misspelled flag used to become the commit message)";;
    *)             [ -z "$MSG" ] || _die "two commit messages: '$MSG' and '$1'. One only, in quotes.";
                   MSG="$1"; shift;;
  esac
done
_no_shortcuts
R_TOKEN="$(rules_token)"
[ -n "$R_TOKEN" ] || _die "no GitHub token. Set GH_TOKEN, or run 'gh auth login' once."

printf '%s== pr.sh - landing a change under the rules ==%s\n\n' "$R_BOLD" "$R_NC"

# ── 0. starting state ──────────────────────────────────────────────────────────────
gate_tools
git fetch -q origin "$BASE" || warn "fetch failed: working against the local origin/$BASE ref"
gate_private_material_out
gate_tools_visible

# ── 1. R01 · never on master ───────────────────────────────────────────────────────
BR_NOW="$(git rev-parse --abbrev-ref HEAD)"
case "$(printf '%s' "$BR_NOW" | tr 'A-Z' 'a-z')" in
  master|main)
    [ "$CONTINUE" = "0" ] || require R01 "--continue from '$BR_NOW': there is no branch to push that is not master."
    if [ -z "$BRANCH" ]; then
      # ⚠️ First line only: a message written the way the project asks (title, blank line,
      # body) produced a multi-line branch name and the script died.
      BRANCH="fix/$(export LC_ALL=C; printf '%s' "${MSG:-change}" | sed -n 1p | tr '[:upper:]' '[:lower:]' \
        | sed 's/[^a-z0-9]\{1,\}/-/g; s/^-//; s/-$//' | cut -c1-40)"
      # LC_ALL=C above: in a UTF-8 locale the [a-z] class also collates accented letters
      # and they ended up in the branch name. And a message with no alphanumerics ("!!!")
      # gave "fix/", which git rejects with an error that explains nothing.
      [ "$BRANCH" = "fix/" ] && BRANCH="fix/change-$(date +%H%M%S)"
    fi
    printf "you are on '%s': moving the work onto %s%s%s (master stays untouched)\n" "$BR_NOW" "$R_BOLD" "$BRANCH" "$R_NC"
    git switch -q -c "$BRANCH" 2>/dev/null || git switch -q "$BRANCH" 2>/dev/null \
      || _die "cannot create branch $BRANCH"
    ;;
esac
BR_NOW="$(git rev-parse --abbrev-ref HEAD)"
gate_not_on_master

# ── 2. commit ──────────────────────────────────────────────────────────────────────
if [ "$CONTINUE" = "0" ] && [ -n "$(git status --porcelain)" ]; then
  [ -n "$MSG" ] || _die "there are uncommitted changes but no commit message.
       Write it for whoever runs 'git blame' in a year, not for yourself today."
  gate_no_trailer "$MSG"
  gate_stage_clean                  # R14 — before the git add, not after
  git add -A
  git commit -q --cleanup=verbatim -m "$MSG" || _die "commit failed"
  ok "commit made"
fi
gate_no_trailer_in_commits "origin/$BASE"

NEW_COMMITS="$(git rev-list --count "origin/$BASE"..HEAD)"
[ "$NEW_COMMITS" -gt 0 ] || _die "no commit beyond origin/$BASE: there is nothing to propose."

# ── 3. gates on the content ────────────────────────────────────────────────────────
gate_core_without_ha            # R11
gate_no_model_names             # R21
gate_suite                      # R12
gate_secrets                    # R02 + R22 — after the commit, before the push
gate_shared_code "origin/$BASE" # R06 — a warning, not a block

FILE_N="$(git diff --name-only "origin/$BASE"...HEAD | wc -l)"
if [ "$FILE_N" -gt 12 ] || [ "$NEW_COMMITS" -gt 8 ]; then
  warn "R13 · $FILE_N files, $NEW_COMMITS commits: a change nobody can read is not reviewable."
  warn "     If these are separate behaviours, open them one at a time. (Judgement, not a measurement: not stopping you.)"
fi

# ── 4. R07 · the evidence declaration ──────────────────────────────────────────────
R_EVIDENCE=""; R_LABELS=""
gate_field_test

# ── 4b. R25 · whose work is it that this text claims ───────────────────────────────
# R07 says what a piece of evidence is worth; R25 says WHO produced it. In a project where
# none of us writes code by hand, "I read it" and "the agent I drive read it" are not the
# same claim, and letting them blur makes a sentence weigh more than it earned.
R_ATTRIBUTION=""
gate_attribution "$(git log --format='%s%n%b' "origin/$BASE"..HEAD; printf '%s\n' "$R_EVIDENCE")"

# ── 5. push the BRANCH ─────────────────────────────────────────────────────────────
printf '%s==> pushing %s%s\n' "$R_BLUE" "$BR_NOW" "$R_NC"
# push_safe gets the REAL arguments (R01/R09 inspect them normalised) and authenticates
# with an ephemeral header: no URL carrying the token, so no token in .git/config (R22).
push_safe origin "HEAD:refs/heads/$BR_NOW" || _die "push failed.
       No force, on purpose: if the branch has diverged, 'git fetch origin && git merge origin/$BASE'."
git fetch -q origin "$BR_NOW" 2>/dev/null && git branch -q --set-upstream-to="origin/$BR_NOW" 2>/dev/null || true
ok "branch pushed to origin"

# Where the branch actually landed. If `origin` is your own fork, the pull request still
# has to be opened against the upstream repository, and the API then wants `owner:branch`
# as the head — with a bare branch name it answers "No commits between ..." and the run
# ends with the work pushed and no pull request.
ORIGIN_URL="$(git remote get-url origin 2>/dev/null || true)"
ORIGIN_SLUG="$(printf '%s' "$ORIGIN_URL" | sed -E 's#^(https://[^/]+/|git@[^:]+:)##; s#\.git$##')"
# ⚠️ Only treat it as a slug if it actually looks like one. A remote that is a local path
# ("../mirror.git") left `${ORIGIN_SLUG%%/*}` as ".." and the head became "..:branch".
# Found by running this against a sandbox remote, not by reading it.
printf '%s' "$ORIGIN_SLUG" | grep -qE '^[A-Za-z0-9][A-Za-z0-9._-]*/[A-Za-z0-9][A-Za-z0-9._-]*$' || ORIGIN_SLUG=""
HEAD_REF="$BR_NOW"
if [ -n "$ORIGIN_SLUG" ] && [ "$ORIGIN_SLUG" != "$R_REPO" ]; then
  HEAD_REF="${ORIGIN_SLUG%%/*}:$BR_NOW"
  warn "origin is $ORIGIN_SLUG, not $R_REPO: opening the pull request from a fork ($HEAD_REF)."
  echo "      Note: a beta build is never cut from a fork — a member publishes it by hand."
fi

# ── 6. the pull request ────────────────────────────────────────────────────────────
TITLE="$(printf '%s' "${MSG:-$(git log -1 --format=%s)}" | head -1)"
BODY_F="$(mktemp)"; trap 'rm -f "$BODY_F" "${PAYLOAD:-}" "${RESP:-}"' EXIT
TEMPLATE=".github/PULL_REQUEST_TEMPLATE.md"
if [ -f "$TEMPLATE" ]; then
  # The repository's template is the shape reviewers expect: fill it in, do not replace it
  # with an invention of your own.
  {
    echo "## What changes, and why"; echo
    git log --reverse --format='- %s' "origin/$BASE"..HEAD
    echo; echo "## Evidence"; echo
    echo "${R_EVIDENCE:-not declared}"
    [ -n "${R_ATTRIBUTION:-}" ] && { echo; echo "${R_ATTRIBUTION}"; }
    echo; echo "## Checks"; echo
    if [ "${R_SUITE_SKIPPED:-0}" = "1" ]; then
      echo "- [ ] Suite green — **not run locally**: no interpreter with pytest on this machine, CI is the gate (\`AGENTS.md\`)"
      echo "- [ ] Entity count unchanged — same, checked by CI"
    else
      echo "- [x] Suite green (\`pytest tests/ -q\`) — R12 gate in \`tools/pr.sh\`"
      echo "- [x] Entity count unchanged — \`tests/test_entity_count.py\`, inside the suite"
    fi
    echo "- [x] No VIN, token, certificate, account id or raw capture — R02 gate (\`tools/check-secrets.sh\`, whole history)"
    echo "- [ ] Fails open: nothing here can take away a function that worked for somebody"
    echo "- [ ] Design docs updated if this contradicts them"
  } > "$BODY_F"
else
  { git log --reverse --format='- %s' "origin/$BASE"..HEAD; echo; echo "${R_EVIDENCE:-not declared}"
    [ -n "${R_ATTRIBUTION:-}" ] && { echo; echo "${R_ATTRIBUTION}"; } || true; } > "$BODY_F"
fi
[ "${R_NEEDS_READ:-0}" = "1" ] && {
  { echo; echo "## Read requested"; echo
    echo "This touches shared code, so I am asking for a read from somebody who is not the author (R06)."
    echo "The merge is not blocked: if the week elapses, I merge and label it \`merged-unread\` (R20)."
  } >> "$BODY_F"; }

printf '%s==> opening the pull request%s\n' "$R_BLUE" "$R_NC"
PAYLOAD="$(mktemp)"; RESP="$(mktemp)"
python3 - "$TITLE" "$BODY_F" "$HEAD_REF" "$BASE" "$DRAFT" > "$PAYLOAD" <<'PY'
import json, sys
t, f, head, base, draft = sys.argv[1:6]
print(json.dumps({"title": t, "body": open(f, encoding="utf-8").read(),
                  "head": head, "base": base, "draft": draft == "1"}))
PY
CODE="$(_curl_gh -s -o "$RESP" -w '%{http_code}' -X POST \
        "https://api.github.com/repos/${R_REPO}/pulls" -d @"$PAYLOAD")"
NUM="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1])).get("number") or "")' "$RESP" 2>/dev/null || true)"
if [ -z "$NUM" ]; then
  NUM="$(_gh "pulls?head=$(printf '%s' "$HEAD_REF" | sed "s#^\([^:]*\)\$#${R_REPO%%/*}:\1#")&state=open" \
        | python3 -c 'import json,sys;d=json.load(sys.stdin);print(d[0]["number"] if d else "")' 2>/dev/null || true)"
  if [ -n "$NUM" ]; then
    echo "    pull request #$NUM already open on this branch: updated by the push."
  else
    { echo "HTTP $CODE"; sed 's|^|  \| |' "$RESP"; echo
      echo "The branch IS on GitHub: the work is not lost, only the pull request is missing."
      echo "Open it by hand from:  https://github.com/${R_REPO}/compare/${BASE}...${BR_NOW}?expand=1"; } >&2
    _die "could not open the pull request."
  fi
else
  ok "pull request #$NUM opened"
fi

if [ -n "${R_LABELS:-}" ]; then
  _curl_gh -s -o /dev/null -X POST "https://api.github.com/repos/${R_REPO}/issues/${NUM}/labels" \
    -d "$(python3 -c 'import json,sys;print(json.dumps({"labels":sys.argv[1].split(",")}))' "$R_LABELS")"
  echo "    label: $R_LABELS"
fi

echo
printf '%shttps://github.com/%s/pull/%s%s\n\n' "$R_BOLD" "$R_REPO" "$NUM" "$R_NC"
echo "Now: CI runs on the pull request."
[ "${R_NEEDS_READ:-0}" = "1" ] && echo "Ask for the R06 read - but nobody is blocking the merge."
echo "To get it onto a real car BEFORE it lands: put the 'beta' label on the pull request (R16),"
echo "and whoever owns that car installs it from HACS with 'Show beta versions'."
echo "Tags and releases are not made from here: './tools/release.sh prepare' then 'publish'."

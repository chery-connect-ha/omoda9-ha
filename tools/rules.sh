#!/usr/bin/env bash
# tools/rules.sh — the rules of this repository, in a form a machine can enforce.
#
# This is NOT documentation. It is the library that `pr.sh`, `release.sh` and
# `check-secrets.sh` load, and every gate in it corresponds to a rule written down in
# CONTRIBUTING.md, AGENTS.md, docs/field-test.md or SECURITY.md. Where a rule has no
# prose behind it, it says so: those are house rules of the maintainer who wrote this
# file, not decisions of the group, and `./tools/rules.sh list` prints them as such.
#
# Direct use:
#   ./tools/rules.sh list       # the rulebook: id, severity, source, whether it has a gate
#   ./tools/rules.sh check      # preflight: never asks for a derogation, just reports
#   ./tools/rules.sh log        # every derogation ever granted
#
# As a library:  . tools/rules.sh
#
# ───────────────────────────── THE RULE ABOUT THE RULES ─────────────────────────────
# A failing gate STOPS the script. The only way past it is a **derogation**:
#   * the dialogue happens on /dev/tty, not on stdin/stdout, so `| tee` cannot break it
#     and a pipe cannot feed it;
#   * you must type an exact phrase containing a **one-time code printed right then**, so
#     somebody who cannot see the screen cannot prepare it in advance;
#   * you must give a reason of at least 20 characters;
#   * the line goes into DEROGATIONS.log, and **if the log cannot be written the
#     derogation is not granted**: no derogation without a trace.
#
# There is a second door, for agents — see `--authorized` below. It is narrower on
# purpose: it opens only for NORMAL-severity rules.
#
# ⚠️ HONESTY ABOUT THE LIMITS — read this before trusting this file.
# No local mechanism can tell a person apart from a program that sees the same terminal.
# `script -qec`, `expect`, `tmux send-keys` and a CI runner with a pty can all read the
# one-time code and type it back. What this file actually guarantees is:
#   1. a derogation cannot happen BY ACCIDENT — not from a pipe, not from cron, not from
#      an agent that has not deliberately built itself a fake terminal;
#   2. every derogation leaves a written line, or it does not happen.
# That is a high kerb and an honest register, not a wall. Anyone who writes "unbypassable"
# is doing the thing this project forbids in writing: claiming a check they do not have.
set -uo pipefail

# ── where things are ────────────────────────────────────────────────────────────────
# ⚠️ Do NOT assume this file sits at the top of the working tree. It lives in tools/, so
# every path is resolved from the repository root, found through git. An earlier version
# used `dirname "$0"` and, the moment the scripts moved into a subdirectory, looked for
# custom_components/ inside tools/ and reported that core/ had ceased to exist.
R_TOOLS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
R_ROOT="$(git -C "$R_TOOLS_DIR" rev-parse --show-toplevel 2>/dev/null || true)"
if [ -z "$R_ROOT" ]; then
  echo "tools/rules.sh: not inside a git working tree ($R_TOOLS_DIR). Nothing to check." >&2
  return 1 2>/dev/null || exit 1
fi
DEROGATIONS_LOG="$R_ROOT/DEROGATIONS.log"
# Extra secret patterns that are specific to one person or one machine (a surname in an
# e-mail, home paths, the names of private infrastructure). They must NOT be committed —
# writing them here would publish exactly what they exist to catch — so they live in a
# gitignored file. See tools/private-patterns.example.txt.
R_PRIVATE_PATTERNS="$R_TOOLS_DIR/private-patterns.txt"

# The REAL command line of whoever called us. Inside `ask_derogation`, "$*" is the
# function's own arguments: the register used to say "pr.sh R10", which does not say what
# was derogated. The caller declares it right after sourcing, with `rules_cmdline "$@"`.
R_CMDLINE="$(basename "${0}")"
rules_cmdline() { R_CMDLINE="$(basename "${0}") $*"; }

# Read-only mode: `check` turns it on. A preflight that opens the derogation dialogue is
# not a preflight — and a subshell does not help: it prevents the exit, not the prompt and
# not the write to the register.
R_PREFLIGHT=0

# Set by a caller's `--authorized "<phrase>"`. See `ask_derogation`.
R_AUTHORIZED="${R_AUTHORIZED:-}"

# Set by gate_suite when no interpreter with pytest could be found, so that pr.sh can
# say so in the pull request — which is what AGENTS.md asks for.
R_SUITE_SKIPPED=0

R_RED=$'\e[31m'; R_GREEN=$'\e[32m'; R_YELLOW=$'\e[33m'; R_BLUE=$'\e[36m'; R_NC=$'\e[0m'; R_BOLD=$'\e[1m'

# ══════════════════════════════ THE RULEBOOK ══════════════════════════════
# id|severity|text|source
# HIGH   = the damage leaves this room and reaches somebody who is not in it.
# NORMAL = the damage stays at home (internal quality, wasted work, discipline).
#
# A source that begins with "house rule" has NO prose behind it in this repository. It is
# the practice of the maintainer who wrote these scripts, kept here because the gate is
# useful — not a decision anybody else has agreed to. Argue with them; they are not
# smuggled in as project rules.
R_RULES=(
"R01|HIGH|Never push to 'master'. Every change lands as a pull request, including from the people who wrote the rules, and including releases.|CONTRIBUTING.md \"Never\" · AGENTS.md \"The commands\" · branch protection, active since 2026-08-22 (#2)"
"R02|HIGH|Never a secret in the repository: VIN, token, certificate, tUserId, account identifier, e-mail, phone number, raw capture. Not in code, not in tests, not pasted into an issue. The gate is check-secrets.sh, run AFTER the commit and BEFORE the push: against staged-only changes it sees nothing and passes falsely.|CONTRIBUTING.md \"Never\" · AGENTS.md \"Invariants\" · SECURITY.md"
"R03|HIGH|CI green is a precondition, not a hope: HACS validation, Hassfest and the test suite must be green on the EXACT commit being published.|CONTRIBUTING.md \"It lands\" · branch protection (3 required checks)"
"R04|HIGH|The changelog is written for people who are not programmers, in the '## [Non rilasciato]' section, in two language blocks with the same content. Never generate_release_notes. This is the text HACS shows to EVERY user at update time.|house rule: the maintainer's release practice. Not in CONTRIBUTING.md or AGENTS.md; AGENTS.md \"Cutting a release\" currently suggests --generate-notes, which contradicts it"
"R05|HIGH|At most one stable release every 2 weeks: each tag costs every user a HACS notification and a Home Assistant restart. Work accumulates in '[Non rilasciato]'. Exceptions: data loss, account lockout, security.|house rule, from measured history (45 releases in 30 days, 62% of them less than an hour apart). Not in CONTRIBUTING.md or AGENTS.md"
"R06|NORMAL|Shared code (core/, coordinator.py, authentication, signing, the entity model) asks for a read by somebody who is not the author. The merge is NEVER blocked and required approvals on GitHub are deliberately zero: the block sits on the stable release. Nobody approves because they own the organisation.|CONTRIBUTING.md \"It lands\" (\"Merging is never blocked. Only the last step is.\")"
"R07|HIGH|Never claim a hardware check you do not have. 'The backend answered OK' is layer 1 and speaks about us; only a state field on the car changing, at a time you can point to, is layer 2 and speaks about the car. Code written for a car nobody owns still merges, labelled unverified-hardware, and a stable release must NAME it rather than folding it in quietly.|CONTRIBUTING.md \"Never\" and \"It becomes stable\" · AGENTS.md \"don't overstate evidence\" · docs/field-test.md"
"R08|HIGH|A stable release without the omoda9.zip asset is worse than no release: hacs.json sets zip_release, so HACS lists the version and then fails to install it.|AGENTS.md \"Cutting a release\" · hacs.json"
"R09|HIGH|Never force-push and never rewrite published history. To bring an already-pushed branch up to date use merge, not rebase. On master the protection forbids deletions too.|AGENTS.md \"Never\" and \"When master has moved on\" · branch protection"
"R10|NORMAL|Never AI co-authorship trailers in commit messages. How this project credits its tools is a decision for the group, not an assistant's default.|AGENTS.md \"Save the work\""
"R11|NORMAL|No Home Assistant imports inside core/: the protocol logic must stay runnable without HA installed, which is what lets the sandbox exercise a change without an instance.|AGENTS.md \"Invariants\""
"R12|HIGH|Fail open: if something cannot be read, is unrecognised or times out, send exactly what was sent before (full request, historic endpoint). The worst an untested path may do is fail to help. Never remove or narrow an entity or a command that worked. The entity count is a test.|AGENTS.md \"Invariants\" · tests/test_entity_count.py"
"R13|NORMAL|One behaviour per pull request. A change nobody can read is not reviewable, and asking for review of an unreadable diff is theatre.|CONTRIBUTING.md \"Keep changes small\""
"R14|NORMAL|Private material stays out of the repository: credentials, certificates, tokens, raw captures, the legacy bridge, personal handover notes, derogation and comment logs. The tooling itself is NOT private any more: it lives in tools/ and is meant to be read and run by everybody.|CONTRIBUTING.md \"Never\" · SECURITY.md · superseding the maintainer's earlier house rule that kept these scripts out of the repository"
"R15|HIGH|Never send a command to the car or the backend, not even a read-only one, without an explicit go-ahead from the person whose car it is.|house rule for agent-driven work. Not in AGENTS.md; consistent in spirit with CONTRIBUTING.md \"Never\""
"R16|NORMAL|Never cut a release in order to test. To test: the suite, your own instance, or the 'beta' label on the pull request, which builds a pre-release installable from HACS.|AGENTS.md \"Get it onto a real car\" · CONTRIBUTING.md \"It ships\" · .github/workflows/beta.yml (#12)"
"R17|NORMAL|The single source of truth is this repository. Never edit the installed copy under the Home Assistant config directory: that fix dies at the next HACS update and nobody ever sees it again.|house rule, but it generalises to anyone developing an HA integration. Not in CONTRIBUTING.md or AGENTS.md"
"R18|NORMAL|After publishing, say explicitly to the car owner that the next step is theirs: HACS - update - restart Home Assistant.|house rule about how an agent hands back to the person it works for. Not in CONTRIBUTING.md or AGENTS.md"
"R19|HIGH|Before a STABLE release, every model in the blast radius must have a field test: a report from somebody who owns that car, in the form of docs/field-test.md. It is the only gate the sources call real.|CONTRIBUTING.md \"It becomes stable\" (\"This is the only real gate\")"
"R20|NORMAL|A read is promised within one week. If nobody reads it, the author merges it themselves and labels it merged-unread: the rule must fail loudly instead of stopping everyone.|CONTRIBUTING.md \"The one-week rule\""
"R21|HIGH|No model names as code paths: a new car is data plus capabilities discovered at runtime, not an if model == ... If you need one, you have found an architecture problem: say so instead of encoding it.|AGENTS.md \"Invariants\""
"R22|HIGH|A GitHub token must never be committed nor left in .git/config. Pushing uses an authentication that is not written to disk.|derived from AGENTS.md \"Invariants\" (no secrets) and \"I committed something secret\" · SECURITY.md"
"R23|HIGH|The version in manifest.json must already match the tag being published: HACS installs that package under that number.|AGENTS.md \"Cutting a release\""
"R24|NORMAL|After an update, check on the running instance: Home Assistant RUNNING, the entity count that tests/test_entity_count.py asserts, none of them unavailable. Count only once HA is RUNNING: during start-up you see none, and that is not a fault.|tests/test_entity_count.py for the number; the post-update inspection itself is a house rule"
"R25|HIGH|Who did the work: a person or an agent. Every claim of work done (I read, I checked, I counted, I tested) must say whether a person did it or an agent under their guidance. 'I read it' and 'the agent I drive read it' are not the same claim, and letting them blur makes a sentence weigh more than it earned. Applies to commit messages, pull request bodies, release notes and issue comments.|CONTRIBUTING.md \"Never\" (\"Say you read something when your agent read it\", merged in #28) · AGENTS.md \"don't overstate evidence\" · convention adopted by @drake69 in #7"
"R26|HIGH|Before publishing a reply, re-read the thread: if somebody wrote AFTER the draft was saved, stop. The comparison is mechanical - the draft's last-modified time against the comments' timestamps - because time always passes between writing and publishing, and the more careful the message the more time that is.|from a real mistake on 2026-08-24: a request for a review published 38 minutes after that review had already been given. Enforced only in the maintainer's local drafting tool, which is not part of this repository"
)

rule_row()      { local id="$1" r; for r in "${R_RULES[@]}"; do [ "${r%%|*}" = "$id" ] && { echo "$r"; return 0; }; done; return 1; }
rule_text()     { rule_row "$1" | cut -d'|' -f3; }
rule_source()   { rule_row "$1" | cut -d'|' -f4; }
rule_severity() { rule_row "$1" | cut -d'|' -f2; }

# ══════════════════════════════ THE GATE ══════════════════════════════

_die() { printf '%s%sSTOP.%s %s\n' "$R_RED" "$R_BOLD" "$R_NC" "$*" >&2; exit 1; }

# Trying to get past the gate through the environment is itself a reason to stop.
# ⚠️ R_PY and R_PREFLIGHT are on this list because they WERE the shortcut: the first chose
# the interpreter for the suite (R_PY=/bin/true meant R12 green without running a test),
# the second turns derogations off. Found by an adversarial review on 2026-08-24.
_no_shortcuts() {
  local v
  # Only variables this file does not set itself: a "already checked" memo would itself be
  # settable from the environment, i.e. the shortcut for skipping the shortcut check.
  for v in OMODA9_DEROGA OMODA9_FORCE OMODA9_SKIP_GATE SKIP_CHECKS R_PY R_PYTEST; do
    if [ -n "${!v:-}" ]; then
      _die "environment variable $v is set: that is a shortcut, not a derogation.
       Derogations are typed by hand at a terminal, or authorised with --authorized.
       Unset it and run again."
    fi
  done
}

# ask_derogation <ID> — returns 0 if granted; otherwise exits.
ask_derogation() {
  local id="$1" severity text source phrase reason expected nonce
  severity="$(rule_severity "$id")"; text="$(rule_text "$id")"; source="$(rule_source "$id")"

  { echo
    printf '%s%s== RULE %s - NOT SATISFIED ============================%s\n' "$R_RED" "$R_BOLD" "$id" "$R_NC"
    printf '%s|%s %s\n' "$R_RED" "$R_NC" "$text"
    printf '%s|%s %ssource:%s %s\n' "$R_RED" "$R_NC" "$R_BLUE" "$R_NC" "$source"
    printf '%s============================================================%s\n' "$R_RED" "$R_NC"
  } >&2

  # In preflight nobody is asked anything: report and leave.
  [ "${R_PREFLIGHT:-0}" = "1" ] && _die "(preflight: rule $id is not satisfied)"

  # ── the narrow door, for agents ───────────────────────────────────────────────────
  # An agent has no /dev/tty, so without this every failing gate is a wall with no
  # recourse — and a tool that can only be used when everything is already green is a
  # tool nobody uses. What --authorized carries is the sentence the person said in the
  # conversation. This script CANNOT verify it: whoever runs the script types it. What is
  # still true: it opens only for NORMAL rules, and it is written down verbatim.
  if [ -n "${R_AUTHORIZED:-}" ]; then
    if [ "$severity" = "HIGH" ]; then
      _die "rule $id is HIGH severity: --authorized does not open it.
       The damage it prevents does not stay at home. This one needs a person at a terminal."
    fi
    [ "${#R_AUTHORIZED}" -ge 10 ] || _die "the authorisation phrase is too short to mean anything."
    printf '%s\t%s\t%s\t%s\t%s\n' \
      "$(_now)" "$(id -un)" "$id" "$R_CMDLINE" "AUTHORIZED: $R_AUTHORIZED" \
      >> "$DEROGATIONS_LOG" \
      || _die "cannot write $DEROGATIONS_LOG: no derogation without a trace."
    { printf '%sRule %s waived on this authorisation:%s "%s"\n' "$R_YELLOW" "$id" "$R_NC" "$R_AUTHORIZED"
      printf '%s(the script cannot verify it — it is recorded word for word in %s)%s\n' \
        "$R_YELLOW" "$(basename "$DEROGATIONS_LOG")" "$R_NC"; } >&2
    return 0
  fi

  # The dialogue lives on /dev/tty, not on stdin/stdout, so `| tee log` cannot break it and
  # a pipe cannot feed it. If /dev/tty is not there, there is nobody to ask.
  # ⚠️ `[ -r /dev/tty ]` is not enough: the node exists and is readable by permission even
  # when the process has no controlling terminal, and the open then fails with ENXIO,
  # printing a bash error and carrying on with an empty answer. So we try to OPEN it.
  if ! { exec 3<>/dev/tty; } 2>/dev/null; then
    { echo; echo "No terminal (/dev/tty unavailable): there is nobody here who could derogate."
      echo "That covers agents, cron, pipes and non-interactive sessions, on purpose."
      echo "For a NORMAL-severity rule, re-run with: --authorized \"<what you were told>\""; } >&2
    _die "rule $id cannot be derogated in this context. It needs a person at a terminal."
  fi

  # One-time code: somebody who cannot see the screen cannot prepare the phrase in advance.
  nonce="$(tr -dc 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789' </dev/urandom | head -c4)"
  if [ "$severity" = "HIGH" ]; then
    { echo
      printf '%sThis rule is HIGH severity: the damage it prevents does NOT stay at home.\n' "$R_YELLOW"
      printf 'It reaches somebody who is not in this room - a HACS user, the owner of a car\n'
      printf 'that is not yours, anybody reading the public repository. What lands on GitHub\n'
      printf 'must be treated as public forever.%s\n' "$R_NC"; } >&3
    expected="I WAIVE $id $nonce AND I TAKE RESPONSIBILITY"
  else
    expected="I WAIVE $id $nonce"
  fi

  { echo
    echo "To waive it, type this phrase EXACTLY (or press Enter to stop):"
    printf '    %s%s%s\n' "$R_BOLD" "$expected" "$R_NC"
    printf '> '; } >&3
  IFS= read -r phrase <&3 || phrase=""
  [ "$phrase" = "$expected" ] || _die "phrase did not match: no derogation. Rule $id stands."

  { echo "Reason (at least 20 characters, it stays in the register):"; printf '> '; } >&3
  IFS= read -r reason <&3 || reason=""
  [ "${#reason}" -ge 20 ] || _die "reason too short: no derogation. A derogation without a written reason is not a decision, it is an oversight."

  # ⚠️ No derogation without a trace: if the register cannot be written, it does not count.
  printf '%s\t%s\t%s\t%s\t%s\n' \
    "$(_now)" "$(id -un)" "$id" "$R_CMDLINE" "$reason" >> "$DEROGATIONS_LOG" \
    || _die "cannot write $DEROGATIONS_LOG: no derogation without a trace."
  printf '%sDerogation %s granted and recorded in %s.%s\n\n' \
    "$R_YELLOW" "$id" "$(basename "$DEROGATIONS_LOG")" "$R_NC" >&2
  exec 3>&-
  return 0
}

# `date -Is` is GNU-only; this form works on BSD/macOS too.
_now() { date -u +%Y-%m-%dT%H:%M:%SZ; }

require() {
  local id="$1"; shift
  printf '%sx%s %s\n' "$R_RED" "$R_NC" "$*" | sed '2,$s/^/      /' >&2
  ask_derogation "$id"
}
ok()   { printf '%s+%s %s\n' "$R_GREEN" "$R_NC" "$*"; }
warn() { printf '%s!%s %s\n' "$R_YELLOW" "$R_NC" "$*"; }

# ══════════════════════════ BASIC TOOLS ══════════════════════════

# What the gates take for granted. `zip(1)` is NOT installed everywhere: found by an
# adversarial review that simulated `publish` to the end and got a tag and a release
# published with ZERO assets — exactly what R08 calls "worse than no release". The archive
# is therefore built with python, which the scripts already require.
gate_tools() {
  local c missing=""
  for c in git curl python3; do command -v "$c" >/dev/null || missing="$missing $c"; done
  [ -n "$missing" ] && _die "missing indispensable tools:$missing"
  ok "tools present (the archive is built with python, not with zip(1))"
}

# ── the token must never touch the disk or the command line (R22) ───────────────────
# curl: the token is passed as a config file on stdin, not with `-H` on the command line,
# which /proc/<pid>/cmdline exposes to anyone on the machine.
_curl_gh() { # $@ = curl arguments, without authentication
  # ⚠️ `set -u` inside a command substitution kills the SUBSHELL, not the script: an unset
  # R_TOKEN became an empty response, and the R03 gate then diagnosed "CI never ran"
  # instead of "I have no token". Better to die saying the truth.
  : "${R_TOKEN:?a GitHub token is needed (GH_TOKEN, GITHUB_TOKEN, or \`gh auth login\`)}"
  : "${R_REPO:?the repository name is needed}"
  printf 'header = "Authorization: token %s"\nheader = "Accept: application/vnd.github+json"\n' "$R_TOKEN" \
    | curl --config - "$@"
}
_gh() { _curl_gh -sfL "https://api.github.com/repos/${R_REPO}/$1" 2>/dev/null; }

# Where a token comes from, in order. `gh auth token` is listed because AGENTS.md tells
# contributors to run `gh auth login`, and a tool that then demands a second, hand-made PAT
# is a tool people work around.
rules_token() {
  local t="${GH_TOKEN:-${GITHUB_TOKEN:-}}"
  [ -n "$t" ] || t="$(gh auth token 2>/dev/null || true)"
  printf '%s' "$t"
}

# git: authentication goes in a header, NEVER in a URL — a URL with the token in it lands
# in .git/config on the first `push -u` and stays there (R22).
_git_push() { # $@ = git push arguments (no -u, no URL)
  local auth
  # `base64 -w0` is GNU-only and fails on macOS; `base64 | tr -d '\n'` works on both.
  auth="$(printf 'x-access-token:%s' "$R_TOKEN" | base64 | tr -d '\n')"
  git -C "$R_ROOT" -c "http.extraHeader=Authorization: Basic $auth" push "$@"
}

# ══════════════════════════════ THE GATES ══════════════════════════════

# ── R01 / R09 — the only place anything is pushed from ──────────────────────────────
# ⚠️ There used to be two gates that inspected strings DIFFERENT from the ones handed to
# git: `gate_never_push_master "$BR"` got the short name while git got
# `HEAD:refs/heads/<br>`, and the force check ran AFTER a `git tag -f`. Now there is one
# door and it receives the real arguments.
push_safe() { # $@ = exactly what you want to hand to git push
  local a ref
  for a in "$@"; do
    case "$a" in
      -f|--force|--force-*|--mirror|--delete|--prune|+*)
        require R09 "argument '$a': this is how somebody else's history gets lost." ;;
    esac
    # every refspec: look at the DESTINATION, after the colon, normalised.
    case "$a" in -*) continue;; esac
    ref="${a##*:}"; ref="${ref#refs/heads/}"; ref="${ref#refs/tags/}"
    case "$(printf '%s' "$ref" | tr 'A-Z' 'a-z')" in
      master|main) require R01 "this would push to '$ref'. master is reached only through a pull request." ;;
    esac
  done
  ok "R01/R09 · push allowed: $*"
  _git_push "$@"
}

gate_not_on_master() {
  local br; br="$(git -C "$R_ROOT" rev-parse --abbrev-ref HEAD)"
  case "$(printf '%s' "$br" | tr 'A-Z' 'a-z')" in
    master|main) require R01 "you are on branch '$br': nothing is committed or pushed from here." ;;
    *) ok "R01 · working branch: $br" ;;
  esac
}

# ── R02 / R22 — secrets ─────────────────────────────────────────────────────────────
gate_secrets() {
  printf '%s==> R02 · secret gate (check-secrets.sh over the whole history)%s\n' "$R_BLUE" "$R_NC"
  if [ ! -x "$R_TOOLS_DIR/check-secrets.sh" ]; then
    require R02 "tools/check-secrets.sh is missing or not executable: the gate cannot even run."
  else
    local out rc
    out="$("$R_TOOLS_DIR/check-secrets.sh" 2>&1)"; rc=$?
    if [ "$rc" -ne 0 ] || ! grep -q 'RESULT: PASS' <<<"$out"; then
      tail -40 <<<"$out" >&2
      require R02 "check-secrets.sh did not pass (exit $rc)."
    else
      grep -q 'PASS with warnings' <<<"$out" && warn "R02 · PASS with warnings: re-read the '!' lines from check-secrets.sh"
      ok "R02 · no secret in HEAD or in the history"
    fi
  fi
  gate_token_not_in_git_config
}

# check-secrets.sh scans the history and the working tree: .git/config is neither, so it
# was a structural blind spot — and it is exactly where the PAT landed on the first
# `push -u`.
gate_token_not_in_git_config() {
  local dirty
  dirty="$(git -C "$R_ROOT" config --local --list 2>/dev/null \
           | grep -iE '(https?://[^:@[:space:]]+:[^@[:space:]]+@)|gh[pousr]_[A-Za-z0-9]{20,}' || true)"
  if [ -n "$dirty" ]; then
    require R22 "there is a credential in cleartext in .git/config:$(printf '\n%s' "$(sed 's/:[^:@]*@/:***@/' <<<"$dirty")")
Remove it with: git config --local --unset <key>"
  else
    ok "R22 · no credential in .git/config"
  fi
}

# ── R03 — CI green on the exact commit ──────────────────────────────────────────────
gate_ci_green() { # $1 = sha
  local sha="${1:?}" json verdict
  printf '%s==> R03 · CI on commit %s%s\n' "$R_BLUE" "${sha:0:8}" "$R_NC"
  if ! json="$(_gh "commits/$sha/check-runs?per_page=100")"; then
    require R03 "could not ask GitHub for the CI status (network, token or permissions).
The gate fails closed: without an answer, nothing is published."
    return 0
  fi
  verdict="$(python3 - "$json" <<'PY'
import json, sys
try:
    d = json.loads(sys.argv[1] or "")
except Exception:
    print("NOJSON"); raise SystemExit
runs = d.get("check_runs") or []
expected = {"HACS validation", "Hassfest", "Suite di test"}
seen = {}
for r in runs:
    n = r["name"]
    if n not in seen or (r.get("started_at") or "") > (seen[n].get("started_at") or ""):
        seen[n] = r
missing = expected - set(seen)
if missing:
    print("MISSING:" + ",".join(sorted(missing))); raise SystemExit
bad = [n for n in expected if seen[n].get("status") != "completed"
       or seen[n].get("conclusion") != "success"]
print("RED:" + ",".join(sorted(bad)) if bad else "GREEN")
PY
)"
  case "$verdict" in
    GREEN)     ok "R03 · the three required checks are green on ${sha:0:8}" ;;
    NOJSON)    require R03 "could not read the CI status from GitHub (the gate fails closed)." ;;
    MISSING:*) require R03 "checks absent on ${sha:0:8}: ${verdict#MISSING:} (did CI ever run on this commit?)" ;;
    RED:*)     require R03 "checks NOT green on ${sha:0:8}: ${verdict#RED:}" ;;
    *)         require R03 "CI verdict could not be interpreted: $verdict" ;;
  esac
}

# ── R04 — changelog, human and in both languages ────────────────────────────────────
gate_changelog() { # $1 = LITERAL heading to inspect (e.g. "## v1.13.1")
  local heading="${1:-## [Non rilasciato]}" f="$R_ROOT/CHANGELOG.md" body it en
  printf '%s==> R04 · changelog%s\n' "$R_BLUE" "$R_NC"
  body="$(awk -v v="$heading" 'index($0,v)==1 {f=1;next} /^## /{f=0} f' "$f")"
  if ! grep -qE '[[:alnum:]]' <<<"$body"; then
    require R04 "section '$heading' of the CHANGELOG is empty: there is nothing to show the user in HACS."
    return 0
  fi
  it="$(awk '/^### .*Italiano/{f=1;next} /^###? /{f=0} f' <<<"$body" | grep -cE '^[-*]' || true)"
  en="$(awk '/^### .*English/{f=1;next}  /^###? /{f=0} f' <<<"$body" | grep -cE '^[-*]' || true)"
  if [ "${it:-0}" -eq 0 ] || [ "${en:-0}" -eq 0 ]; then
    require R04 "changelog is not bilingual: Italian entries=${it:-0}, English=${en:-0}. HACS shows one single text to everybody, so both must be there."
  elif [ "$it" -ne "$en" ]; then
    warn "R04 · IT=$it EN=$en entries: the two sections should say the same thing, check."
  else
    ok "R04 · bilingual changelog, $it entries per language"
  fi
}

# ── which tags count as a RELEASE ───────────────────────────────────────────────────
# .github/workflows/beta.yml (#12) cuts pre-releases from a pull request labelled 'beta',
# tagged vX.Y.Z-beta.N. Those are not releases: they are the pull request made installable.
# Counting them as releases does two things, both silent:
#   * R05 would see "0 days since the last release" the day after every beta and block
#     every stable for two weeks — a gate that always fires is the surest way to teach
#     people to derogate;
#   * the evidence inventory in release.sh (R07/R19) would start from the beta instead of
#     the last stable: pull requests merged before it would fall outside the release body,
#     and with an empty inventory R19 — the only gate the sources call real — would not
#     fire at all.
# Right-anchored: `v1.13.0` matches, `v1.13.0-beta.3` does not.
R_TAG_RELEASE='^v[0-9]+\.[0-9]+\.[0-9]+([[:space:]]|$)'

# ── R05 — cadence ───────────────────────────────────────────────────────────────────
gate_cadence() { # $1 = (optional) the version being published, NOT to be counted
  local exclude="${1:-}" last days
  printf '%s==> R05 · distance from the last release%s\n' "$R_BLUE" "$R_NC"
  # ⚠️ Excluding the in-flight tag is not a detail: a half-failed attempt leaves the local
  # tag behind, and on the retry the cadence gate blocked the recovery of your OWN broken
  # release. Found in adversarial review on 2026-08-24.
  last="$(git -C "$R_ROOT" for-each-ref --sort=-creatordate \
            --format='%(refname:short) %(creatordate:unix)' refs/tags \
          | grep -E "$R_TAG_RELEASE" \
          | grep -v "^v${exclude} " | head -1 | awk '{print $2}')"
  if [ -z "$last" ]; then ok "R05 · no previous tag"; return 0; fi
  days=$(( ( $(date +%s) - last ) / 86400 ))
  if [ "$days" -lt 14 ]; then
    require R05 "$days days since the last release (minimum 14). If this is data loss, account lockout or security, derogate and write that in the reason."
  else
    ok "R05 · $days days since the last release"
  fi
}

# ── R06 — a read by somebody else: reported, not blocked (the source says so) ────────
R_SHARED_RE='^custom_components/omoda9/(core/|coordinator\.py|config_flow\.py|__init__\.py|const\.py|entity\.py)'
gate_shared_code() { # $1 = base
  local base="${1:-origin/master}" touched
  touched="$(git -C "$R_ROOT" diff --name-only "$base"...HEAD | grep -E "$R_SHARED_RE" || true)"
  if [ -n "$touched" ]; then
    warn "R06 · touches shared code:"
    sed 's/^/      /' <<<"$touched"
    echo "      -> ask for a read from somebody who is not the author. The merge is not blocked:"
    echo "         if nobody reads it within a week, merge and label it 'merged-unread' (R20)."
    R_NEEDS_READ=1
  else
    ok "R06 · no shared file touched"
    R_NEEDS_READ=0
  fi
}

# ── R07 — the evidence declaration ──────────────────────────────────────────────────
# R_EVIDENCE_KIND lets a caller (an agent, with no terminal) state the evidence instead of
# falling back to the safest claim. ⚠️ It deliberately CANNOT say "verified on hardware":
# that answer means somebody watched a car, and nothing running without a person present is
# in a position to say so. The other three answers only ever weaken a claim, so letting a
# script make them costs nothing — while defaulting a documentation change to
# `unverified-hardware` puts a false line in the next release notes, which is the failure
# this rule exists to prevent.
R_EVIDENCE_KIND="${R_EVIDENCE_KIND:-}"
gate_field_test() {
  local r d
  case "$R_EVIDENCE_KIND" in
    backend)  R_EVIDENCE="**Backend only** - the request was accepted; nobody watched the car act."
              R_LABELS="unverified-hardware"
              ok "R07 · declared: backend only"; return 0 ;;
    not-mine) R_EVIDENCE="**Not testable by me** - written for a model the author does not own."
              R_LABELS="unverified-hardware"
              ok "R07 · declared: model not owned"; return 0 ;;
    none)     R_EVIDENCE="**No runtime behaviour** - docs, tests, CI: nothing a user can see changes."
              R_LABELS=""
              ok "R07 · declared: no runtime behaviour"; return 0 ;;
    hardware) _die "R07: 'verified on hardware' cannot be declared from a flag. It means somebody
       watched the car do it, so it is answered at a terminal, by that person." ;;
    ?*)       _die "R07: unknown evidence '$R_EVIDENCE_KIND' (use: backend | not-mine | none)." ;;
  esac
  if ! { exec 3<>/dev/tty; } 2>/dev/null; then
    R_EVIDENCE="Not declared: pull request opened without a terminal."
    R_LABELS="unverified-hardware"
    warn "R07 · no terminal and no --evidence: the PR is born labelled unverified-hardware,"
    echo "      the only safe claim. If nothing a user can see changes, say so: --evidence none"
    return 0
  fi
  { echo
    printf '%sR07 - the only question that matters (docs/field-test.md):%s\n' "$R_BOLD" "$R_NC"
    echo "  1) I watched the CAR do it: I know which state field changed, and when."
    echo "  2) I only saw the BACKEND answer OK."
    echo "  3) I do not own that model: I could not test it."
    echo "  4) No runtime behaviour (docs, tests, CI)."
    printf '> [1/2/3/4] '; } >&3
  IFS= read -r r <&3 || r=3
  case "$r" in
    1) printf "   Which field changed, and at what time? > " >&3; IFS= read -r d <&3
       R_EVIDENCE="**Verified on hardware** - observed on the car: $d"; R_LABELS="" ;;
    2) R_EVIDENCE="**Backend only** - the request was accepted; nobody watched the car act."
       R_LABELS="unverified-hardware" ;;
    4) R_EVIDENCE="**No runtime behaviour** - docs, tests, CI: nothing a user can see changes."
       R_LABELS="" ;;
    *) R_EVIDENCE="**Not testable by me** - written for a model the author does not own."
       R_LABELS="unverified-hardware" ;;
  esac
  exec 3>&-
  ok "R07 · declaration recorded"
}

# ── R10 — no AI trailers ────────────────────────────────────────────────────────────
# ⚠️ The previous regex looked for the substring 'AI' and blocked "...@gmail.com" and
# "@hotmail.it" (a human co-author could no longer land anything), while letting Gemini,
# Cursor and "Assisted-by:" through. Now the subjects are listed.
_TRAILER_RE='(^|[[:space:]])(co-authored-by|assisted-by|generated-by):[[:space:]]*[^[:space:]]*(claude|anthropic|openai|gpt|copilot|gemini|cursor|codex|devin|aider|llm)|generated with[[:space:]]*\[?(claude|gpt|copilot)'
gate_no_trailer() { # $1 = the TEXT of the message (never a filename)
  if grep -qEi "$_TRAILER_RE" <<<"${1:-}"; then
    require R10 "the commit message carries an AI co-authorship trailer."
  else
    ok "R10 · no AI trailer in the message"
  fi
}
gate_no_trailer_in_commits() { # $1 = base
  local dirty
  dirty="$(git -C "$R_ROOT" log --format='%H %s%n%b' "${1:-origin/master}"..HEAD | grep -Ei "$_TRAILER_RE" || true)"
  [ -n "$dirty" ] && require R10 "AI trailer in a commit that is already made:$(printf '\n%s' "$dirty")" \
                  || ok "R10 · no AI trailer in this branch's commits"
}

# ── R11 / R21 — architecture invariants ─────────────────────────────────────────────
gate_core_without_ha() {
  local core="$R_ROOT/custom_components/omoda9/core" h
  # ⚠️ Without this line the gate went green when core/ no longer existed: grep failed,
  # `|| true` zeroed it, and absence looked like compliance.
  [ -d "$core" ] || { require R11 "custom_components/omoda9/core/ does not exist: the gate does not know what to look at."; return 0; }
  h="$(grep -rnE '^[[:space:]]*(from|import)[[:space:]]+homeassistant|import_module\(["'"'"']homeassistant|__import__\(["'"'"']homeassistant' "$core" 2>/dev/null || true)"
  [ -n "$h" ] && require R11 "Home Assistant imported inside core/:$(printf '\n%s' "$h")" \
              || ok "R11 · core/ does not import Home Assistant"
}
gate_no_model_names() {
  local cc="$R_ROOT/custom_components/omoda9" h
  [ -d "$cc" ] || return 0
  h="$(grep -rnEi 'if[^:]*\b(model|modello|marca|brand)\b[^:]*==[[:space:]]*["'"'"'](omoda|jaecoo|j7|e5|c5)' "$cc" 2>/dev/null || true)"
  [ -n "$h" ] && require R21 "a model name used as a code path:$(printf '\n%s' "$h")" \
              || ok "R21 · no model name used as a code path"
}

# ── R12 — the suite, and with it the entity count ───────────────────────────────────
# ⚠️ The interpreter is NOT taken from the environment: `R_PY=/bin/true` made this gate
# pass without running a single test, and it was the variable the rulebook swore did not
# exist. Known locations are searched instead — none of them absolute, so this works on
# somebody else's machine.
_find_python() {
  local p
  for p in "${VIRTUAL_ENV:-}/bin/python" \
           "$R_ROOT/.venv/bin/python" "$R_ROOT/.venv-test/bin/python" \
           "$R_ROOT/venv/bin/python" "$R_ROOT/env/bin/python" \
           python3.14 python3.13 python3; do
    [ "$p" = "/bin/python" ] && continue
    command -v "$p" >/dev/null 2>&1 || [ -x "$p" ] || continue
    "$p" -c 'import pytest' >/dev/null 2>&1 && { printf '%s' "$p"; return 0; }
  done
  return 1
}
gate_suite() {
  printf '%s==> R12 · test suite%s\n' "$R_BLUE" "$R_NC"
  local py out rc
  if ! py="$(_find_python)"; then
    # ⚠️ This case is a WARNING, not a stop, and the source is explicit about it:
    # AGENTS.md, "Run the checks locally if you can" — "If the local Python is older, skip
    # it and let CI be the gate - that is why CI exists - but say so in the pull request."
    # pr.sh reads R_SUITE_SKIPPED and says so in the body. A red suite still stops.
    R_SUITE_SKIPPED=1
    warn "R12 · no interpreter with pytest here (tried \$VIRTUAL_ENV, .venv, .venv-test, venv, env, python3.14/3.13/3)."
    echo "      Home Assistant needs Python 3.13+. CI is the gate; the pull request will say the"
    echo "      suite did not run locally, which is what AGENTS.md asks for."
    return 0
  fi
  out="$(cd "$R_ROOT" && "$py" -m pytest tests/ -q 2>&1)"; rc=$?
  if [ "$rc" -ne 0 ]; then
    tail -25 <<<"$out" >&2
    require R12 "the suite is not green. 'Green in a follow-up' does not count: green in the pull request that changes the behaviour."
  else
    ok "R12 · $(grep -oE '[0-9]+ passed' <<<"$out" | tail -1) ($py)"
  fi
}

# ── R14 — private material stays out of the repository ──────────────────────────────
# ⚠️ Two families, anchored differently, and the difference is NOT pedantry: half of the
# private filenames collide with real modules of the component (core/commands.py,
# core/session.py, core/wake.py). Anchored everywhere, the gate declared "private material
# in the repository" on eleven legitimate files and blocked every pull request.
#   - family 1: unambiguous names -> anywhere in the tree;
#   - family 2: names that collide with the component -> ONLY at the root, which is where
#     the untracked private material lives.
# Note what is NOT here any more: rules.sh, pr.sh, release.sh, check-secrets.sh. They used
# to be private and are now part of the repository, in tools/. The root-anchored entries
# still catch the maintainer's stale copies at the top of the working tree.
_PRIVATE_RE='(^|/)(omoda9\.env|\.mqtt_cred|token\.json)|(^|/)certs_eu/|(^|/)(DEROGATIONS|DEROGHE|COMMENTI)\.log$|(^|/)private-patterns\.txt$|(^|/)ha_bridge\.py$|\.bak_|(^|/)(HANDOFF_[^/]*|AUDIT_REPORT|PATCH_1\.0|ENTITA_HA|SHARING_TODO|REGOLE)\.md$|^(regole|deploy|check_secrets)\.sh$|^(rules|pr|release)\.sh$|^hacs_refresh\.py$|^(commands|login_omoda|omoda|omoda_auth|probe|prova_token|provision|session|tsp_sign|wake|captcha_solver)\.py$'
gate_private_material_out() {
  local inside
  # -z + core.quotePath=false: without them, a file called "odd release.sh" is quoted by
  # git and the pattern anchor no longer matches.
  inside="$(git -C "$R_ROOT" -c core.quotePath=false ls-files -z | tr '\0' '\n' | grep -Ei "$_PRIVATE_RE" || true)"
  [ -n "$inside" ] && require R14 "private material tracked in the repository:$(printf '\n%s' "$inside")" \
                   || ok "R14 · no private material is tracked"
}
# ── R14, the other direction: the tooling must be VISIBLE to git ────────────────────
# ⚠️ This gate exists because of a real, silent failure while these scripts were being
# moved into tools/. The maintainer's .git/info/exclude carried bare entries — `pr.sh`,
# `release.sh` — from the years when they were private. A gitignore pattern **without a
# slash matches at any depth**, so `tools/pr.sh` and `tools/release.sh` were ignored, and
# every `git add -A` dropped them without a word. The commit looked fine and two of the
# five files simply were not in it. Anybody who copies an old exclude file inherits the
# same trap, which is why it is checked rather than remembered.
gate_tools_visible() {
  local ignored
  ignored="$(cd "$R_ROOT" && git check-ignore tools/* 2>/dev/null || true)"
  if [ -n "$ignored" ]; then
    require R14 "git is IGNORING part of the tooling, so it would silently never be committed:$(printf '\n%s' "$ignored")
Almost certainly a leftover entry in .gitignore or .git/info/exclude written without a
leading slash (\`pr.sh\` instead of \`/pr.sh\`), which matches at any depth."
  else
    ok "R14 · git can see the whole of tools/"
  fi
}

# Call this BEFORE every `git add`: what is about to go in, not what is already in.
# ⚠️ `--untracked-files=all` and `-z` are not refinements: with the normal listing a new
# directory appears as 'stuff/' (and the files inside escape) and a name with a space is
# quoted and split — 'omoda9.env backup' went through untouched.
gate_stage_clean() {
  local new f
  new=""
  while IFS= read -r -d '' line; do
    f="${line:3}"
    grep -qEi "$_PRIVATE_RE" <<<"$f" && new="$new$f"$'\n'
  done < <(git -C "$R_ROOT" -c core.quotePath=false status --porcelain -z --untracked-files=all)
  if [ -n "$new" ]; then
    printf '%s      (add them to .gitignore, or remove the files)%s\n' "$R_YELLOW" "$R_NC" >&2
    require R14 "a 'git add -A' would take private material into the repository:$(printf '\n%s' "$new")"
  else
    ok "R14 · no private material would end up in the commit"
  fi
}

# ── R23 — manifest and tag ──────────────────────────────────────────────────────────
# `grep -oP` is GNU-only (and a JSON file deserves a JSON parser).
manifest_version() {
  python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["version"])' \
    "$R_ROOT/custom_components/omoda9/manifest.json"
}
gate_manifest_matches_tag() { # $1 = X.Y.Z
  local v; v="$(manifest_version)"
  [ "$v" = "$1" ] && ok "R23 · manifest $v = tag v$1" \
                  || require R23 "the manifest says $v but the tag would be v$1: HACS would install a package that does not match the version."
}

# ── R25 — who did the work: a person or an agent ────────────────────────────────────
# ⚠️ This gate CANNOT verify an attribution: no program knows who actually read a file. It
# can do one thing, and it is the thing that helps: stop a sentence going out WITHOUT
# saying. It asks, records, and moves on. Calling it "verification" would be the very
# thing this rule forbids.
# Stated limit: it recognises explicit first person ("I checked", "ho verificato"), NOT
# impersonal forms ("Verified: 107 entities"), which are ambiguous by construction and
# would produce so many false positives that they would only teach people to ignore it.
_CLAIM_RE=$'\\b(i|we)( have|\'ve)? +(read|verified|checked|tested|measured|counted|ran|run|reviewed|confirmed|inspected|reproduced|observed|audited|traced|diffed|found|wrote|written)\\b|\\b(ho|abbiamo) +(letto|riletto|verificat[oi]|controllat[oi]|provat[oi]|testat[oi]|misurat[oi]|contat[oi]|guardat[oi]|eseguit[oi]|lanciat[oi]|confrontat[oi]|revisionat[oi]|ispezionat[oi]|analizzat[oi]|riprodott[oi]|osservat[oi]|collaudat[oi]|visto|scritto|trovato|scoperto)\\b'
_ATTRIB_RE='agent[ei]?\b|claude|\bllm\b|assistant|assistente|automated|by hand|myself|personally|a mano|di persona|in prima persona'

R_ATTRIBUTION=""
lint_attribution() { # $1 = TEXT. Prints the lines that claim work without saying whose.
  grep -nEi "$_CLAIM_RE" <<<"${1:-}" | grep -vEi "$_ATTRIB_RE" || true
}

gate_attribution() { # $1 = TEXT (never a filename). Fills R_ATTRIBUTION.
  local lines r
  lines="$(lint_attribution "${1:-}")"
  R_ATTRIBUTION=""
  if [ -z "$lines" ]; then
    ok "R25 · no claim of work done that needs attributing"
    return 0
  fi
  if ! { exec 3<>/dev/tty; } 2>/dev/null; then
    # ⚠️ If the text ALREADY carries an explicit attribution somewhere (a paragraph at the
    # end, as somebody following the convention by hand would write), stamping "not
    # stated" over it would be a falsehood written by the tool that exists to prevent one.
    # The lines are still shown: they are for whoever re-reads, not for deciding.
    if grep -qEi "$_ATTRIB_RE" <<<"${1:-}"; then
      R_ATTRIBUTION=""
      warn "R25 · no terminal, but the text already says who did what. Lines to re-read:"
      sed 's/^/      /' <<<"$lines"
      return 0
    fi
    R_ATTRIBUTION='> *Attribution (R25): not stated - this text was produced without a terminal, so treat the claims above as unattributed.*'
    warn "R25 · no terminal: these claims go out UNATTRIBUTED:"
    sed 's/^/      /' <<<"$lines"
    return 0
  fi
  { echo
    printf '%sR25 - who did the work this text claims?%s\n' "$R_BOLD" "$R_NC"
    echo "  Lines claiming work done without saying by whom:"
    sed 's/^/      /' <<<"$lines"
    echo
    echo "  1) Me, by hand."
    echo "  2) The agent I drive, on my machine. The decisions stay mine."
    echo "  3) Mixed, and the text already distinguishes them line by line."
    printf '> [1/2/3] '; } >&3
  IFS= read -r r <&3 || r=""
  exec 3>&-
  case "$r" in
    1) R_ATTRIBUTION='> *Attribution (R25): I read and checked this myself.*' ;;
    2) R_ATTRIBUTION='> *Attribution (R25): the reading, the counts and the cross-checks in this message were done by the agent I drive, on my machine. What follows from them - the decisions - is mine.*' ;;
    3) R_ATTRIBUTION='> *Attribution (R25): person and agent are distinguished inline - each claim above says which.*' ;;
    *) R_ATTRIBUTION='> *Attribution (R25): not stated.*'
       warn "R25 · no choice made: the text goes out unattributed." ;;
  esac
  ok "R25 · attribution recorded"
}

# Non-interactive variant, for text addressed to USERS rather than to the team (release
# notes): name the lines and let the person decide. Blocking a stable release over a
# sentence of prose would be disproportionate and would only teach people to derogate —
# the same reasoning by which R07 does not block on a silent pull request.
warn_attribution() { # $1 = TEXT, $2 = where
  local lines; lines="$(lint_attribution "${1:-}")"
  if [ -n "$lines" ]; then
    warn "R25 · in $2 there are claims of work done that do not say whose:"
    sed 's/^/      /' <<<"$lines"
    echo "      -> attribute them in the text, or know that they go out like this."
  else
    ok "R25 · $2: nothing to attribute"
  fi
}

# ── R02 applied to a TEXT — a secret pasted into an issue is as public as one in the repo
# check-secrets.sh looks at git; a comment never passes through git. Same values, same
# patterns, applied to the draft BEFORE it becomes a web page. Kept here as a library
# function: the maintainer's local drafting tool uses it, and so can yours.
lint_secrets_in_text() { # $1 = TEXT. Prints the findings; returns 1 if any.
  local text="${1:-}" found="" d p
  while IFS='|' read -r d p; do
    case "$d" in ''|'#'*) continue ;; esac
    grep -qEi -- "$p" <<<"$text" && found+="  · $d"$'\n'
  done <<'PAT'
PEM private key|BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY
GitHub token|gh[pousr]_[A-Za-z0-9]{20,}
JWT|\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}
VIN (17 chars)|\b[A-HJ-NPR-Z0-9]{17}\b
tUserId (long numeric)|\b3660[0-9]{14,}\b
e-mail address|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}
international phone number|\+[1-9][0-9]{1,3}[ .-]?[0-9]{6,12}\b
long hex string (key? id?)|\b[0-9a-f]{32,}\b
private IPv4 address|\b(10|192\.168|172\.(1[6-9]|2[0-9]|3[01]))\.[0-9]{1,3}\.[0-9]{1,3}\b
PAT
  # Anything specific to one person or one machine lives in a gitignored file, because
  # writing it here would publish exactly what it exists to catch.
  if [ -f "$R_PRIVATE_PATTERNS" ]; then
    while IFS='|' read -r d p; do
      case "$d" in ''|'#'*) continue ;; esac
      [ -n "$p" ] || continue
      grep -qEi -- "$p" <<<"$text" && found+="  · $d (from tools/private-patterns.txt)"$'\n'
    done < "$R_PRIVATE_PATTERNS"
  fi
  if [ -n "$found" ]; then
    printf '%s' "$found"
    return 1
  fi
  return 0
}

# ══════════════════════════════ CLI ══════════════════════════════
_list() {
  printf '%sRULEBOOK - omoda9-ha%s\n' "$R_BOLD" "$R_NC"
  echo "Who may derogate: a person at a terminal, with a one-time code and a written reason."
  echo "Agents: --authorized \"<what you were told>\", for NORMAL-severity rules only."
  echo "Stated limit: a fake pty can imitate the terminal. See the comment at the top of this file."
  echo
  local r id s t f
  for r in "${R_RULES[@]}"; do
    IFS='|' read -r id s t f <<<"$r"
    if [ "$s" = "HIGH" ]; then printf '%s%s%s %s[%s]%s' "$R_RED" "$R_BOLD" "$id" "$R_RED" "$s" "$R_NC"
    else printf '%s%s%s [%s]' "$R_BOLD" "$id" "$R_NC" "$s"; fi
    case "$id" in
      R15|R16|R17|R18|R20|R24) printf '  %s(no gate: it is for the person working, not for the script)%s' "$R_YELLOW" "$R_NC" ;;
      R26) printf '  %s(no gate here: it lives in the maintainer'"'"'s local drafting tool)%s' "$R_YELLOW" "$R_NC" ;;
      R25) printf '  %s(a gate that asks and records: it does not verify)%s' "$R_YELLOW" "$R_NC" ;;
      R06|R13) printf '  %s(warning, not a block)%s' "$R_YELLOW" "$R_NC" ;;
    esac
    case "$f" in house*) printf '  %s(HOUSE RULE: no prose behind it in this repository)%s' "$R_YELLOW" "$R_NC" ;; esac
    echo; echo "   $t"; printf '   %ssource:%s %s\n\n' "$R_BLUE" "$R_NC" "$f"
  done
}

_check() {
  R_PREFLIGHT=1
  printf '%sPreflight - read-only, no derogation is ever asked for%s\n\n' "$R_BOLD" "$R_NC"
  printf 'branch: %s · HEAD: %s\n' "$(git -C "$R_ROOT" rev-parse --abbrev-ref HEAD)" "$(git -C "$R_ROOT" rev-parse --short HEAD)"
  local dirty; dirty="$(git -C "$R_ROOT" status --porcelain | wc -l)"
  [ "$dirty" -gt 0 ] && warn "$dirty modified files, not committed" || ok "clean tree"
  echo
  local g
  for g in gate_tools gate_private_material_out gate_tools_visible gate_stage_clean gate_core_without_ha \
           gate_no_model_names gate_token_not_in_git_config; do
    ( $g ) || printf '%s   ^ %s is not satisfied%s\n' "$R_RED" "$g" "$R_NC"
  done
  # ⚠️ gate_changelog is deliberately NOT in that list. It belongs to a release: on a
  # freshly released master the '[Non rilasciato]' section is legitimately empty, and a
  # preflight that comes out red every single day is a preflight people stop reading —
  # which is the same failure mode as a gate that always fires. Here it is reported.
  local unreleased
  unreleased="$(awk '/^## \[Non rilasciato\]/{f=1;next} /^## /{f=0} f' "$R_ROOT/CHANGELOG.md" | grep -cE '^[-*]' || true)"
  if [ "${unreleased:-0}" -eq 0 ]; then
    ok "changelog · nothing unreleased yet (R04 is checked when you cut a release)"
  else
    ok "changelog · ${unreleased} unreleased entries (R04 checks both languages at release time)"
  fi
  ( gate_no_trailer_in_commits origin/master ) || printf '%s   ^ AI trailers present%s\n' "$R_RED" "$R_NC"
  echo
  echo "(the suite and the secret gate run from ./tools/pr.sh or ./tools/release.sh: they are slow)"
}

if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
  case "${1:-list}" in
    list|rules)  _list ;;
    check)       _check ;;
    log)         [ -f "$DEROGATIONS_LOG" ] && cat "$DEROGATIONS_LOG" || echo "no derogation has ever been granted." ;;
    *) echo "Usage: $0 [list|check|log]" >&2; exit 1 ;;
  esac
fi

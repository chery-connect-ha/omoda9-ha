#!/usr/bin/env bash
# tools/check-secrets.sh — proof that no confidential data is, or ever has been, tracked
# in git. This repository is public: what goes in stays in, and a commit that is deleted
# from a branch is still reachable from the reflog and from anybody's fork.
#
# It scans the WHOLE history, not just HEAD, and the working tree as well — including
# files git has never seen, because the case this gate exists to catch is a note somebody
# has just written and not yet added.
#
# It contains NO secrets itself. Structural patterns are generic; anything specific to one
# person or one machine (a surname inside an e-mail, home paths, the names of private
# infrastructure) is read from tools/private-patterns.txt, which is gitignored. Writing
# those here would publish exactly what they exist to catch.
#
# Usage:  ./tools/check-secrets.sh
# Exit:   0 = PASS (nothing found)   ·   1 = FAIL (found something, do NOT publish)
#         2 = cannot run (not a git working tree, git missing)
set -uo pipefail

TOOLS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
command -v git >/dev/null || { echo "git is missing"; exit 2; }
ROOT="$(git -C "$TOOLS_DIR" rev-parse --show-toplevel 2>/dev/null || true)"
[ -n "$ROOT" ] || { echo "not inside a git working tree"; exit 2; }
cd "$ROOT"
PRIVATE_PATTERNS="$TOOLS_DIR/private-patterns.txt"

RED=$'\e[31m'; GRN=$'\e[32m'; YEL=$'\e[33m'; NC=$'\e[0m'
fail=0; warn=0
hit()  { echo "${RED}x FAIL${NC} $1"; fail=1; }
ok()   { echo "${GRN}+${NC} $1"; }
note() { echo "${YEL}!${NC} $1"; warn=1; }
# A warning must mean "something to look at". Two of the inputs are optional local files,
# and a fresh clone legitimately has neither: reporting their absence as a warning would
# make every single run end in "PASS with warnings", which teaches people to stop reading
# the warnings that matter.
info() { echo "${YEL}i${NC} $1"; }

# ⚠️ Patterns below are written so they cannot match THEMSELVES. `[/]root/` matches the
# path but the literal text "[/]root/" does not, so this file does not permanently trip
# its own gate. (Before this, every run reported five hits inside the tooling itself and
# the result was "PASS with warnings" forever — a warning that always fires is a warning
# people learn to ignore.)

echo "== 1) Confidential files tracked NOW (HEAD) =="
TRACKED=$(git ls-files | grep -iE '(^|/)(omoda9\.env|\.mqtt_cred|token\.json|private-patterns\.txt)$|/certs_eu/|\.pem$|\.key$|(^|/)data/|_diag\.jsonl' | grep -v 'example' || true)
if [ -n "$TRACKED" ]; then hit "confidential files are tracked:"; echo "$TRACKED"; else ok "no confidential file tracked now"; fi

echo "== 2) Confidential files tracked IN THE PAST (whole history) =="
HIST=$(git log --all --pretty=format: --name-only --diff-filter=A 2>/dev/null | sort -u \
       | grep -iE '(^|/)(omoda9\.env|\.mqtt_cred|token\.json|private-patterns\.txt)$|/certs_eu/|\.pem$|\.key$|(^|/)data/|_diag\.jsonl' \
       | grep -v 'example' || true)
if [ -n "$HIST" ]; then hit "confidential files present in past commits (exposed the moment anyone clones):"; echo "$HIST"; else ok "no confidential file anywhere in the history"; fi

echo "== 3) Real values from your local env file, searched across the WHOLE history =="
# omoda9.env is gitignored and holds this installation's real values. They are the only
# ones no generic pattern can recognise. Loaded in a subshell and never printed.
if [ ! -f omoda9.env ]; then
  info "omoda9.env absent (normal unless you run the integration from this checkout):
    the exact-value match on your own PIN, VIN, tUserId and phone number is not running."
else
  set -a; . ./omoda9.env 2>/dev/null || true; set +a
  ALLREV=$(git rev-list --all 2>/dev/null)
  checkval() { # $1=name $2=value
    local name="$1" val="$2"
    [ -z "$val" ] && return 0
    [ "${#val}" -lt 4 ] && return 0   # too short -> false positives
    # ⚠️ History AND working tree, and `--untracked` in BOTH places. This gate runs before
    # the commit, so history alone lets through exactly what is about to be published; and
    # without `--untracked` git grep only looks at files it already knows, while the case
    # to catch is a NEW file. A real PIN pasted into a brand-new test file — which is what
    # happened on 2026-08-02 — would have gone through untouched.
    if { git grep -I -n -F "$val" $ALLREV -- . 2>/dev/null
         git grep -I -n -F --untracked "$val" -- . 2>/dev/null; } | head -1 | grep -q .; then
      hit "the value of $name appears in git (history or working tree)"
    else
      ok "$name: no match"
    fi
  }
  # Only genuinely secret values. Usernames are not secrets and produce false positives.
  for k in OMODA_EMAIL OMODA_PHONE OMODA_PIN PIN TUSERID VIN HA_MQTT_PASS; do
    checkval "$k" "$(eval echo "\${$k:-}")"
  done
fi

echo "== 4) Structural patterns across the WHOLE history =="
ALLREV=${ALLREV:-$(git rev-list --all 2>/dev/null)}
_scan() {
  git grep -I -nE "$1" $ALLREV -- . 2>/dev/null
  git grep -I -nE --untracked "$1" -- . 2>/dev/null
}
genpat() { # $1=description $2=regex $3=(optional) extra allowance, THIS pattern only
  # The extra allowance is per-pattern and NOT global: widening the shared allowlist would
  # also soften the checks on tokens, PEM keys and e-mail, which must stay strict.
  # NB the allowlist filters by LINE -> the marker (VIN_PLACEHOLDER, PHONE_PLACEHOLDER)
  # must be on the same line as the value, not in a comment above it.
  # ⚠️ KNOWN BLIND SPOT, measured rather than assumed: the base allowance below is shared
  # by every pattern, so ANY line containing the word "example" is exempt from all of
  # them. A real address pasted as `someone@example.com` goes through. It is the price of
  # not failing on every fixture, and it is written here so nobody mistakes the gate for
  # more than it is.
  local skip='example|placeholder|REPLACE_ME|FAKE_|VIN_PLACEHOLDER|PHONE_PLACEHOLDER'
  [ -n "${3:-}" ] && skip="$skip|$3"
  if _scan "$2" | grep -v -iE "$skip" | head -1 | grep -q .; then
    hit "$1 (pattern: $2)"
    _scan "$2" | grep -v -iE "$skip" | head -3
  else ok "no match: $1"; fi
}
genpat "GitHub token"            'gh[pousr]_[A-Za-z0-9]{20,}'
genpat "private key PEM"         'BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY'
# The suite's synthetic VINs start with LZZ (tests/fixtures.py). Only that family is
# allowed through: the exact-value check on the real VIN (section 3) is untouched and is
# the one that counts. Reason for the allowance: the allowlist works by LINE, and a test
# line carrying a fake VIN without the VIN_PLACEHOLDER marker failed the gate.
genpat "VIN-shaped (L + 16)"     '\bL[A-HJ-NPR-Z0-9]{16}\b'  '\bLZZ[A-HJ-NPR-Z0-9]{14}\b'
genpat "tUserId (long numeric)"  '\b3660[0-9]{14,}\b'
genpat "JWT"                     '\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}'
# ── Phone numbers (since v1.8: SMS login carries them into code, tests and logs) ──
# A phone number is personal data exactly as an e-mail is. Several shapes, because whoever
# pastes one from a real session writes it bare, with a country code, or with separators.
# For a FAKE number in a test use tests/fixtures.py (FX.PHONE), never a literal.
# ⚠️ These shapes are Italian-leaning. A UK or Danish number is caught only by the
# international form: if you contribute from another country, add your own local shape to
# tools/private-patterns.txt.
genpat "bare Italian mobile"     '\b3[0-9]{9}\b'
genpat "phone with +39"          '(\+|00)39[ ._-]?3[0-9]{2}[ ._-]?[0-9]{3}[ ._-]?[0-9]{4}'
genpat "phone with separators"   '\b3[0-9]{2}[ .-][0-9]{3}[ .-][0-9]{3,4}\b'
genpat "international phone"     '\+[1-9][0-9]{1,3}[ .-]?[0-9]{6,12}\b'

echo "== 4b) Your own patterns (tools/private-patterns.txt) =="
if [ ! -f "$PRIVATE_PATTERNS" ]; then
  info "tools/private-patterns.txt absent: your name, your paths and your machine names are NOT being checked."
  echo "    Copy tools/private-patterns.example.txt to tools/private-patterns.txt and fill it in."
else
  n=0
  while IFS='|' read -r desc pat; do
    case "$desc" in ''|'#'*) continue ;; esac
    [ -n "$pat" ] || continue
    n=$((n+1))
    genpat "$desc" "$pat"
  done < "$PRIVATE_PATTERNS"
  [ "$n" -gt 0 ] || info "tools/private-patterns.txt is empty."
fi

echo "== 5) .gitignore consistency (the rules have to be there) =="
for pat in 'omoda9.env' 'certs_eu/' 'token.json' '.mqtt_cred' 'data/' '*_diag.jsonl' 'DEROGATIONS.log' 'tools/private-patterns.txt'; do
  grep -qF "$pat" .gitignore 2>/dev/null && ok ".gitignore covers '$pat'" \
    || hit ".gitignore does NOT cover '$pat'"
done
# and: if the confidential files exist here, they must actually be ignored
for f in omoda9.env token.json .mqtt_cred tools/private-patterns.txt $(ls -1 *_diag.jsonl 2>/dev/null); do
  if [ -e "$f" ]; then
    git check-ignore -q "$f" && ok "$f present and genuinely ignored" \
      || hit "$f present but NOT ignored by git"
  fi
done

echo "== 6) Soft info-disclosure (not secrets, but a leak in a public repository) =="
# Warning, not failure. Patterns are self-avoiding (see the note at the top).
SOFT='\b(10|192[.]168|172[.](1[6-9]|2[0-9]|3[01]))[.][0-9]{1,3}[.][0-9]{1,3}\b|[/]ro{2}t/|[/]home/[a-z_][a-z0-9_-]*/|[/]Users/[A-Za-z]|qm guest e[x]ec|pct e[x]ec|\bVM[I]D\b'
# One allowance, and only one: `/root/.local/...` is where pip puts a package INSIDE the
# Home Assistant container. It is documentation about Home Assistant, not about anybody's
# machine, and without this the check would report it forever — a warning that always
# fires is a warning people learn to ignore.
SOFT_OK='[/]ro{2}t/\.local'
SOFTHITS=$(git grep -nIE "$SOFT" -- '*.md' '*.py' '*.sh' '*.yml' '*.yaml' 2>/dev/null | grep -cvE "$SOFT_OK")
if [ "$SOFTHITS" -gt 0 ]; then
  note "$SOFTHITS internal references (private IPs, home paths, virtualisation commands) in tracked files:"
  git ls-files '*.md' '*.py' '*.sh' '*.yml' '*.yaml' | while read -r f; do
    n=$(grep -E "$SOFT" "$f" 2>/dev/null | grep -cvE "$SOFT_OK")
    [ "${n:-0}" -gt 0 ] && echo "    $n  $f"
  done
  echo "    -> these say what your machine looks like. Scrub them before they are merged:"
  echo "       once on GitHub they are public forever, in the history as well."
else
  ok "no internal reference in tracked files"
fi

echo "-----------------------------------------------"
if [ "$fail" = "1" ]; then
  echo "${RED}RESULT: FAIL - do not push. Clean the history and ROTATE whatever leaked.${NC}"
  exit 1
elif [ "$warn" = "1" ]; then
  echo "${YEL}RESULT: PASS with warnings - read the '!' lines above before going on.${NC}"
  exit 0
else
  echo "${GRN}RESULT: PASS - no secret in HEAD or in the history.${NC}"
  exit 0
fi

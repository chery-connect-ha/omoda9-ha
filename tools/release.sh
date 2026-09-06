#!/usr/bin/env bash
# tools/release.sh — cutting a release, in TWO acts, because `master` is protected.
#
#   ./tools/release.sh status                        where we are, touching nothing
#   ./tools/release.sh prepare <X.Y.Z|patch|minor|major>
#        Bumps the version in the manifest, dates the '[Non rilasciato]' section of the
#        CHANGELOG, commits on 'release/vX.Y.Z' and opens the pull request. Never touches
#        master.
#   ./tools/release.sh publish [X.Y.Z]
#        AFTER that pull request has been merged: checks CI is green on the exact commit,
#        builds and VALIDATES the archive, then tags, creates the release, uploads the zip
#        and names whatever nobody could try on a real car.
#   ./tools/release.sh abort <X.Y.Z>                 undoes a bad 'prepare', locally only
#
# Options:  --authorized "<what you were told>"      for agents; NORMAL-severity rules only
#
# A pre-release from a pull request is the `beta` label, not this script (R16).
set -uo pipefail
_HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$_HERE/rules.sh"
cd "$R_ROOT"
rules_cmdline "$@"

R_REPO="${OMODA9_REPO:-chery-connect-ha/omoda9-ha}"
SRC_DIR="custom_components/omoda9"
MANIFEST="$SRC_DIR/manifest.json"
CHANGELOG="CHANGELOG.md"
ZIP_NAME="omoda9.zip"        # must match "filename" in hacs.json
BASE="master"
UNRELEASED="## [Non rilasciato]"

ARGS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --authorized) R_AUTHORIZED="${2:?the sentence with which you were given the go-ahead}"; shift 2;;
    *)            ARGS+=("$1"); shift;;
  esac
done
set -- "${ARGS[@]:-}"
_no_shortcuts
R_TOKEN="$(rules_token)"
[ -n "$R_TOKEN" ] || _die "no GitHub token. Set GH_TOKEN, or run 'gh auth login' once."

ACTION="${1:-status}"; shift || true

# Everything transient in one directory, removed whatever happens.
TMPD="$(mktemp -d)"; trap 'rm -rf "$TMPD"' EXIT

# Only release tags: the pre-releases cut by beta.yml (vX.Y.Z-beta.N) are not published
# versions. See R_TAG_RELEASE in rules.sh for why counting them does silent damage.
_last_tag() { git for-each-ref --sort=-creatordate --format='%(refname:short)' refs/tags \
                | grep -E "$R_TAG_RELEASE" | sed -n 1p; }

# ⚠️ The changelog section is extracted by LITERAL prefix comparison, never by regex.
# `awk '$0 ~ "^## v"NEW'` treated the dots as wildcards and did not anchor on the right:
# with NEW=1.5.1 the release body swallowed v1.5.10...v1.5.19 as well — eleven versions
# concatenated, and that text is what HACS shows to every user. The trailing space is the
# right-hand anchor.
_changelog_section() { # $1 = "## [Non rilasciato]" or "## v1.13.1"
  awk -v v="$1 " 'index($0,v)==1 {f=1;next} /^## /{f=0} f' "$CHANGELOG" \
    | sed '/./,$!d' | sed -e :a -e '/^[[:space:]]*$/{$d;N;ba' -e '}'
}

# ══════════════════════════════ STATUS ══════════════════════════════
if [ "$ACTION" = "status" ]; then
  printf '%sRelease status%s\n' "$R_BOLD" "$R_NC"
  echo "  manifest:      $(manifest_version)"
  echo "  last tag:      $(_last_tag)"
  echo "  branch:        $(git rev-parse --abbrev-ref HEAD)"
  git fetch -q origin "$BASE" --tags 2>/dev/null || true
  echo "  remote master: $(git rev-parse --short "origin/$BASE" 2>/dev/null)"
  echo
  R_PREFLIGHT=1
  ( gate_changelog ) || true
  ( gate_cadence )   || true
  echo
  echo "Next:  ./tools/release.sh prepare <patch|minor|major|X.Y.Z>"
  exit 0
fi

# ══════════════════════════════ ABORT ══════════════════════════════
# This exists because an interrupted 'prepare' left the operator on a release branch with
# the changes staged, and every retry died from there: a state the script itself refused
# to start from. LOCAL only: it touches nothing on GitHub.
if [ "$ACTION" = "abort" ]; then
  V="${1:?usage: $0 abort X.Y.Z}"
  git switch -q "$BASE" 2>/dev/null || true
  git restore -q --staged --worktree . 2>/dev/null || true
  git branch -qD "release/v$V" 2>/dev/null && echo "  branch release/v$V removed" || true
  git tag -d "v$V" 2>/dev/null && echo "  local tag v$V removed" || true
  ok "local state cleaned. Nothing on GitHub was touched."
  exit 0
fi

# ══════════════════════════════ PREPARE ══════════════════════════════
if [ "$ACTION" = "prepare" ]; then
  printf '%s== release · act 1: preparing the pull request ==%s\n\n' "$R_BOLD" "$R_NC"
  gate_tools
  git fetch -q origin "$BASE" --tags || warn "fetch failed: working against local refs"
  [ -z "$(git status --porcelain)" ] || _die "there are uncommitted changes. Land them first with ./tools/pr.sh:
       a release is not the place to slip in unreviewed work."

  # The current version is read from ORIGIN/MASTER: the release branch is cut from there,
  # and a local manifest that is ahead would compute the wrong number.
  git show "origin/$BASE:$MANIFEST" > "$TMPD/manifest.json"
  CUR="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["version"])' "$TMPD/manifest.json")"
  case "${1:-}" in
    patch|minor|major)
      IFS=. read -r MA MI PA <<<"$CUR"
      case "$1" in patch) PA=$((PA+1));; minor) MI=$((MI+1)); PA=0;; major) MA=$((MA+1)); MI=0; PA=0;; esac
      NEW="$MA.$MI.$PA" ;;
    *) NEW="${1:-}" ;;
  esac
  # ⚠️ Real validation, not a glob: `[0-9]*.[0-9]*.[0-9]*` accepted `1.2.3&x`, and `&` in a
  # sed replacement expands to the whole match — the manifest and the changelog came out
  # of the attempt corrupted.
  [[ "$NEW" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] \
    || _die "invalid version: '${NEW}'. Usage: $0 prepare <X.Y.Z | patch|minor|major>   (current: $CUR)"
  git rev-parse -q --verify "refs/tags/v$NEW" >/dev/null && _die "tag v$NEW already exists."

  printf '\n%s==> version: %s -> %s  (from origin/%s)%s\n' "$R_BLUE" "$CUR" "$NEW" "$BASE" "$R_NC"
  BR="release/v$NEW"
  BR_START="$(git rev-parse --abbrev-ref HEAD)"
  # If we die halfway, go back where we started: no hybrid state, no release edits left
  # staged and following the operator back onto master.
  _restore() { git switch -q "$BR_START" 2>/dev/null || true
               git restore -q --staged --worktree . 2>/dev/null || true
               git branch -qD "$BR" 2>/dev/null || true; rm -rf "$TMPD"; }
  trap _restore EXIT

  if git rev-parse -q --verify "refs/heads/$BR" >/dev/null; then
    git switch -q "$BR" || _die "cannot switch to $BR"
    if [ "$(git rev-list --count "origin/$BASE".."$BR")" -gt 0 ]; then
      warn "branch $BR already exists and has commits of its own: continuing on it."
    else
      git reset -q --hard "origin/$BASE"
    fi
  else
    git switch -q -c "$BR" "origin/$BASE" || _die "cannot create branch $BR"
  fi
  gate_not_on_master

  # The gates judge the content of the BRANCH, i.e. what will end up in the tag.
  gate_private_material_out
  gate_changelog "$UNRELEASED"
  # R25 — while the text is still editable: who did what the changelog claims?
  warn_attribution "$(_changelog_section "$UNRELEASED")" "the notes for this version"
  gate_cadence "$NEW"
  gate_core_without_ha
  gate_no_model_names
  gate_suite

  # python, not sed: `sed -i` without a suffix is GNU-only and fails on macOS, and a JSON
  # file deserves a JSON parser.
  python3 - "$MANIFEST" "$NEW" <<'PY'
import json, sys
p, new = sys.argv[1], sys.argv[2]
raw = open(p, encoding="utf-8").read()
d = json.loads(raw)
old = d["version"]
# Rewrite only the version string, leaving key order and formatting exactly as they are:
# hassfest checks the order of the keys in this file.
i = raw.index('"version"')
j = raw.index(old, i)
open(p, "w", encoding="utf-8").write(raw[:j] + new + raw[j+len(old):])
PY
  python3 - "$CHANGELOG" "$NEW" "$(date +%Y-%m-%d)" "$UNRELEASED" <<'PY'
import sys
p, new, date, unreleased = sys.argv[1:5]
lines = open(p, encoding="utf-8").read().split("\n")
for i, l in enumerate(lines):
    if l.startswith(unreleased):
        lines[i:i+1] = [unreleased, "", f"## v{new} — {date}"]
        break
else:
    raise SystemExit(f"heading {unreleased!r} not found in {p}")
open(p, "w", encoding="utf-8").write("\n".join(lines))
PY
  gate_manifest_matches_tag "$NEW"
  # Safety net: the section just dated must actually contain text.
  _changelog_section "## v$NEW" | grep -qE '[[:alnum:]]' \
    || require R04 "after dating it, section '## v$NEW' is empty: the text you read in the gate is not the text about to be tagged (work not yet merged into $BASE?)."

  MSG="release: v$NEW"
  gate_no_trailer "$MSG"
  git add "$MANIFEST" "$CHANGELOG"
  git commit -q --cleanup=verbatim -m "$MSG" || _die "commit failed"
  gate_secrets                                    # R02 + R22, after the commit, before the push

  push_safe origin "HEAD:refs/heads/$BR" || _die "pushing the branch failed"
  trap 'rm -rf "$TMPD"' EXIT                      # from here on the branch must survive

  BODY="$TMPD/pr.md"
  { echo "Bumps the version to **v$NEW** and dates the changelog section HACS will show."
    echo; echo "No code changes: only \`manifest.json\` and \`CHANGELOG.md\`."
    echo; echo "## Evidence"; echo
    echo "**No runtime behaviour** - nothing a user can see changes in this pull request."
    echo; echo "Merge once CI is green, and **then** \`./tools/release.sh publish $NEW\` tags it,"
    echo "creates the release and uploads \`$ZIP_NAME\`."; } > "$BODY"
  RESP="$TMPD/pr.json"
  _curl_gh -s -o "$RESP" -X POST "https://api.github.com/repos/${R_REPO}/pulls" \
    -d "$(python3 -c 'import json,sys;print(json.dumps({"title":sys.argv[1],"body":open(sys.argv[2],encoding="utf-8").read(),"head":sys.argv[3],"base":sys.argv[4]}))' "$MSG" "$BODY" "$BR" "$BASE")"
  NUM="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1])).get("number") or "")' "$RESP" 2>/dev/null || true)"
  echo
  [ -n "$NUM" ] && ok "pull request https://github.com/${R_REPO}/pull/${NUM}" \
                || warn "pull request not opened automatically: open it on GitHub from branch $BR"
  echo
  printf '%sNow:%s wait for the three green checks, merge the pull request, then:\n' "$R_BOLD" "$R_NC"
  echo "   git switch $BASE && git pull && ./tools/release.sh publish $NEW"
  echo "If something went wrong here:  ./tools/release.sh abort $NEW"
  exit 0
fi

# ══════════════════════════════ PUBLISH ══════════════════════════════
[ "$ACTION" = "publish" ] || _die "usage: $0 [status|prepare|publish|abort]"

printf '%s== release · act 2: publishing ==%s\n\n' "$R_BOLD" "$R_NC"
gate_tools
git fetch -q origin "$BASE" --tags || warn "fetch failed"

BR_NOW="$(git rev-parse --abbrev-ref HEAD)"
[ "$BR_NOW" = "$BASE" ] || _die "you are on '$BR_NOW': a tag goes on $BASE, on the commit already merged.
       git switch $BASE && git pull"
[ -z "$(git status --porcelain)" ] || _die "dirty tree: what gets published is exactly what is on master, nothing more."
SHA="$(git rev-parse HEAD)"
[ "$SHA" = "$(git rev-parse "origin/$BASE")" ] || _die "your master is not the tip of origin/$BASE. 'git pull' and run again."

NEW="${1:-$(manifest_version)}"
[[ "$NEW" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || _die "invalid version: '$NEW'"
gate_manifest_matches_tag "$NEW"                       # R23
gate_private_material_out                              # R14
gate_cadence "$NEW"                                    # R05, without counting the in-flight tag
gate_ci_green "$SHA"                                   # R03, on the EXACT commit
gate_secrets                                           # R02 + R22

# ── R04 · the release body = the human changelog for THIS version ──────────────────
NOTES="$TMPD/notes.md"
_changelog_section "## v$NEW" > "$NOTES"
grep -qE '[[:alnum:]]' "$NOTES" \
  || require R04 "there is no '## v$NEW' section with text in the CHANGELOG: HACS would show an empty body."
{ grep -q 'Italiano' "$NOTES" && grep -q 'English' "$NOTES"; } \
  || require R04 "the notes for v$NEW are not bilingual."

# ── R25 · do the notes say whose work they claim? ─────────────────────────────────
# No block here: it names them, BEFORE anything becomes public. The gate that asks sits
# where the text speaks to the team (pr.sh), not where it speaks to the end user.
warn_attribution "$(cat "$NOTES")" "the body of release v$NEW"

# ── R07 / R19 · evidence: an inventory of everything merged since the last tag ─────
printf '%s==> R07/R19 · evidence inventory since the last tag%s\n' "$R_BLUE" "$R_NC"
# ⚠️ Release tags only: a beta cut yesterday from a pull request would shorten this window
# enough to leave out the very changes that must be named, and with an empty inventory the
# R19 gate below would not fire at all.
PREV="$(git for-each-ref --sort=-creatordate --format='%(refname:short) %(creatordate:unix)' refs/tags \
        | grep -E "$R_TAG_RELEASE" \
        | grep -v "^v${NEW} " | sed -n 1p | awk '{print $1}')"
SINCE="$(git log -1 --format=%cI "$PREV" 2>/dev/null || echo '1970-01-01T00:00:00Z')"
echo "    since tag ${PREV:-(none)} ($SINCE)"
INV="$TMPD/inventory.tsv"
# ⚠️ Paginate until we pass the date: a single page sorted by update time leaves out
# precisely the oldest pull requests of the period, i.e. the ones most at risk of not
# being named.
: > "$TMPD/prs.json"
PAGE=1
while [ "$PAGE" -le 10 ]; do
  _gh "pulls?state=closed&base=${BASE}&per_page=100&page=${PAGE}&sort=updated&direction=desc" > "$TMPD/p.json" || break
  N="$(python3 -c 'import json,sys;print(len(json.load(open(sys.argv[1]))))' "$TMPD/p.json" 2>/dev/null || echo 0)"
  cat "$TMPD/p.json" >> "$TMPD/prs.json"; printf '\n' >> "$TMPD/prs.json"
  [ "$N" -lt 100 ] && break
  PAGE=$((PAGE+1))
done
python3 - "$TMPD/prs.json" "$SINCE" > "$INV" <<'PY'
import json, sys
prs, seen = [], set()
for block in open(sys.argv[1], encoding="utf-8").read().split("\n["):
    b = block if block.startswith("[") else "[" + block
    try: prs.extend(json.loads(b))
    except Exception: pass
since = sys.argv[2]
for p in prs:
    if p["number"] in seen: continue
    seen.add(p["number"])
    if not p.get("merged_at") or p["merged_at"] <= since: continue
    labels = {l["name"] for l in p.get("labels", [])}
    state = ("UNVERIFIED" if "unverified-hardware" in labels
             else "VERIFIED" if any(l.startswith("verified:") for l in labels) else "SILENT")
    print(f"{state}\t{p['number']}\t{p['title']}")
PY
UNVER="$(grep -c '^UNVERIFIED' "$INV" || true)"
VER="$(grep -c '^VERIFIED' "$INV" || true)"
SILENT="$(grep -c '^SILENT' "$INV" || true)"
echo "    tried on a car: ${VER:-0} · not testable: ${UNVER:-0} · no declaration: ${SILENT:-0}"

# Unlabelled pull requests do NOT block: no source asks for it, and a gate that fires on
# every release only teaches people to derogate. They are named, and counted as unverified.
if [ "${SILENT:-0}" -gt 0 ]; then
  warn "R07 · ${SILENT} pull requests say nothing about evidence; treating them as unverified:"
  grep '^SILENT' "$INV" | awk -F'\t' '{print "      #"$2" "$3}'
fi
if [ "${UNVER:-0}" -gt 0 ] || [ "${SILENT:-0}" -gt 0 ]; then
  { echo; echo "---"; echo
    echo "### 🇮🇹 Non provato su un'auto"
    echo "In questa versione ci sono modifiche che **nessuno ha potuto provare su una vettura reale**:"
    grep -E '^(UNVERIFIED|SILENT)' "$INV" | awk -F'\t' '{print "- #"$2" - "$3}'
    echo
    echo "### 🇬🇧 Not verified on hardware"
    echo "This release contains changes **nobody was able to test on a real car**:"
    grep -E '^(UNVERIFIED|SILENT)' "$INV" | awk -F'\t' '{print "- #"$2" - "$3}'
  } >> "$NOTES"
  warn "R07 · named in the release body, not hidden"
fi
# R19 — the only gate the sources call real.
if [ "${VER:-0}" -eq 0 ] && [ "$(wc -l < "$INV")" -gt 0 ]; then
  require R19 "none of the pull requests merged since the last tag carries a field test (verified:<model>).
A stable release is a statement to strangers: it needs at least one report from somebody who owns the car,
in the form of docs/field-test.md. To get one: put the 'beta' label on the pull request and ask."
fi

# ── R08 · the archive is built and VALIDATED BEFORE anything is tagged ─────────────
# ⚠️ It used to tag, create the release, and only then build the zip — with `zip(1)`, which
# is not installed everywhere. Measured in a sandbox: tag and release published, zero
# assets, i.e. exactly what R08 calls "worse than no release". python always exists here,
# and nothing becomes public until the archive is ready.
printf '%s==> R08 · building %s (before publishing anything)%s\n' "$R_BLUE" "$ZIP_NAME" "$R_NC"
ZIP="$TMPD/$ZIP_NAME"
python3 - "$SRC_DIR" "$ZIP" <<'PY'
import os, subprocess, sys, zipfile
src, out = sys.argv[1], sys.argv[2]
# TRACKED files only: what is not in git has been reviewed by nobody and cannot go into a
# package that installs itself in somebody else's home.
files = subprocess.run(["git", "ls-files", "-z", "--", src], capture_output=True, check=True
                       ).stdout.decode().split("\0")
files = [f for f in files if f and not f.endswith((".pyc", ".pyo"))]
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for f in files:
        z.write(f, os.path.relpath(f, src))   # component contents at the ROOT of the archive
with zipfile.ZipFile(out) as z:
    names = z.namelist()
    assert "manifest.json" in names, "manifest.json is not at the root of the archive"
    assert z.testzip() is None, "archive is corrupt"
print(f"    {len(names)} files, archive valid")
PY
[ -s "$ZIP" ] || _die "archive not created: publishing nothing."

# ── tag ────────────────────────────────────────────────────────────────────────────
printf '%s==> tag v%s on %s%s\n' "$R_BLUE" "$NEW" "${SHA:0:8}" "$R_NC"
# No `-f`: moving an already-published tag is rewriting published history (R09), and the
# gate could not see it because the forcing was in `git tag`, not in the push.
if git rev-parse -q --verify "refs/tags/v$NEW" >/dev/null; then
  [ "$(git rev-list -1 "v$NEW")" = "$SHA" ] || require R09 "tag v$NEW already exists and points at a different commit: moving it would rewrite published history."
else
  git tag "v$NEW" "$SHA" || _die "creating the tag failed"
fi
push_safe origin "refs/tags/v$NEW" || _die "pushing the tag failed"

# ── GitHub Release ─────────────────────────────────────────────────────────────────
printf '%s==> GitHub Release (body = the human changelog)%s\n' "$R_BLUE" "$R_NC"
RESP="$TMPD/rel.json"
CODE="$(_curl_gh -s -o "$RESP" -w '%{http_code}' -X POST "https://api.github.com/repos/${R_REPO}/releases" \
  -d "$(python3 -c 'import json,sys;print(json.dumps({"tag_name":"v"+sys.argv[1],"name":"v"+sys.argv[1],"body":open(sys.argv[2],encoding="utf-8").read()}))' "$NEW" "$NOTES")")"
REL_ID="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1])).get("id") or "")' "$RESP" 2>/dev/null || true)"
if [ -z "$REL_ID" ]; then
  REL_ID="$(_gh "releases/tags/v${NEW}" | python3 -c 'import json,sys;print(json.load(sys.stdin).get("id") or "")' 2>/dev/null || true)"
  [ -n "$REL_ID" ] && echo "    release v$NEW already exists (id $REL_ID): reusing it" || {
    sed 's/^/  | /' "$RESP" >&2
    _die "GitHub Release NOT created (HTTP $CODE). ⚠️ Tag v$NEW is already published:
       fix and run again (the script reuses the tag), or create the release by hand."
  }
fi

# ── R08 · upload the asset. The old one is deleted ONLY once the new one is up ─────
printf '%s==> asset %s%s\n' "$R_BLUE" "$ZIP_NAME" "$R_NC"
UP="$TMPD/up.json"
_upload() { # $1 = asset name
  _curl_gh -s -o "$UP" -w '%{http_code}' -X POST -H "Content-Type: application/zip" \
    --data-binary @"$ZIP" "https://uploads.github.com/repos/${R_REPO}/releases/${REL_ID}/assets?name=$1"; }
UPC="$(_upload "$ZIP_NAME")"
if ! grep -q '"browser_download_url"' "$UP"; then
  # Retrying after a hiccup: a namesake is already there. ⚠️ It used to delete first and
  # upload second: if the second attempt failed, a release that had a good zip was left
  # with none. Now the new one goes up under a temporary name, and only once it is there
  # is the old one deleted and the new one renamed.
  UPC="$(_upload "${ZIP_NAME}.new")"
  NEW_ID="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1])).get("id") or "")' "$UP" 2>/dev/null || true)"
  if [ -n "$NEW_ID" ]; then
    OLD="$(_gh "releases/${REL_ID}/assets" | python3 -c "import json,sys;print(next((a['id'] for a in json.load(sys.stdin) if a['name']=='${ZIP_NAME}'),''))" 2>/dev/null || true)"
    [ -n "$OLD" ] && _curl_gh -s -o /dev/null -X DELETE "https://api.github.com/repos/${R_REPO}/releases/assets/${OLD}"
    _curl_gh -s -o "$UP" -X PATCH "https://api.github.com/repos/${R_REPO}/releases/assets/${NEW_ID}" \
      -d "$(python3 -c 'import json,sys;print(json.dumps({"name":sys.argv[1]}))' "$ZIP_NAME")"
  fi
fi
grep -q '"browser_download_url"' "$UP" \
  && ok "R08 · $ZIP_NAME is on the release" \
  || { sed 's/^/  | /' "$UP" >&2
       require R08 "uploading $ZIP_NAME failed (HTTP $UPC): with zip_release set, HACS cannot install this version.
Upload it by hand onto release v$NEW before telling anybody about it."; }

# ── R18 · the sentence that cannot be skipped ─────────────────────────────────────
echo
printf '%s%sPublished v%s.%s  https://github.com/%s/releases/tag/v%s\n\n' "$R_GREEN" "$R_BOLD" "$NEW" "$R_NC" "$R_REPO" "$NEW"
printf '%s================================================================%s\n' "$R_BOLD" "$R_NC"
printf '%s NOW IT IS THEIR TURN: HACS -> Omoda 9 / Jaecoo -> Update ->%s\n' "$R_BOLD" "$R_NC"
printf '%s restart Home Assistant. Say it to them in those words.%s\n' "$R_BOLD" "$R_NC"
printf '%s================================================================%s\n' "$R_BOLD" "$R_NC"
echo " After the restart, once HA is RUNNING: the entity count asserted by"
echo " tests/test_entity_count.py, none of them unavailable (R24)."

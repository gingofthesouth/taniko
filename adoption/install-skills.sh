#!/bin/sh
# install-skills.sh — install the Tāniko adoption skills for your agent tool(s).
#
# Usage:
#   adoption/install-skills.sh --tool claude|copilot|codex|opencode|cursor|all [--target DIR] [--user]
#
#   --tool     which agent tool to install for (or 'all')
#   --target   adopting repository root (default: current directory)
#   --user     claude only: install to ~/.claude/skills instead of the repo
#
# Where files land:
#   claude    <target>/.claude/skills/<name>/SKILL.md   (--user: ~/.claude/skills/)
#   copilot   <target>/.github/skills/<name>/SKILL.md
#   codex     <target>/.agents/skills/<name>.md + an index section in AGENTS.md
#   opencode  same as codex (both read AGENTS.md)
#   cursor    <target>/.cursor/rules/<name>.mdc
#
# The AGENTS.md index is maintained idempotently between the
# <!-- taniko-skills-start --> and <!-- taniko-skills-end --> markers;
# everything outside the markers is left untouched.

set -eu

SELF_DIR=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
SRC="$SELF_DIR/skills"
SKILLS="taniko-validate-run taniko-review-agent-work taniko-red-green taniko-protect-gates taniko-debug-verify-failure"
START='<!-- taniko-skills-start -->'
END='<!-- taniko-skills-end -->'

usage() {
    sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'
}

TOOL='' TARGET='.' USER_INSTALL=0
while [ $# -gt 0 ]; do
    case "$1" in
        --tool)   [ $# -ge 2 ] || { echo "error: --tool needs a value" >&2; exit 2; }
                  TOOL=$2; shift 2 ;;
        --target) [ $# -ge 2 ] || { echo "error: --target needs a value" >&2; exit 2; }
                  TARGET=$2; shift 2 ;;
        --user)   USER_INSTALL=1; shift ;;
        -h|--help) usage; exit 0 ;;
        *) echo "error: unknown argument: $1" >&2; usage >&2; exit 2 ;;
    esac
done

case "$TOOL" in
    claude|copilot|codex|opencode|cursor|all) ;;
    '') echo "error: --tool is required" >&2; usage >&2; exit 2 ;;
    *)  echo "error: unknown tool '$TOOL'" >&2; usage >&2; exit 2 ;;
esac
if [ "$USER_INSTALL" = 1 ] && [ "$TOOL" != claude ]; then
    echo "error: --user applies to --tool claude only" >&2; exit 2
fi
[ -d "$SRC" ] || { echo "error: skills source not found at $SRC" >&2; exit 2; }
[ -d "$TARGET" ] || { echo "error: target '$TARGET' is not a directory" >&2; exit 2; }

INSTALLED=''
note() {
    INSTALLED="${INSTALLED}  $1
"
}

copy_to() { # src dst
    mkdir -p "$(dirname "$2")"
    cp "$1" "$2"
    note "$2"
}

one_liner() { # skill name -> first clause of its frontmatter description
    d=$(sed -n 's/^description: //p' "$SRC/$1/SKILL.md")
    printf '%s\n' "${d%% — *}"
}

update_agents_index() { # path-to-AGENTS.md, repo-relative skills dir
    f=$1 rel=$2
    block="$START
## Tāniko skills
Read the matching skill before the activity it names. Installed by Tāniko's
install-skills.sh — do not edit between these markers; re-run it to refresh.
"
    for s in $SKILLS; do
        block="$block- $rel/$s.md — $(one_liner "$s")
"
    done
    block="$block$END"
    tmp="$f.taniko-tmp"
    if [ -f "$f" ]; then
        awk -v start="$START" -v end="$END" '
            index($0, start) { skip = 1; next }
            index($0, end)   { skip = 0; next }
            !skip { lines[++n] = $0 }
            END { while (n > 0 && lines[n] == "") n--
                  for (i = 1; i <= n; i++) print lines[i] }
        ' "$f" > "$tmp"
    else
        : > "$tmp"
    fi
    if [ -s "$tmp" ]; then printf '\n' >> "$tmp"; fi
    printf '%s\n' "$block" >> "$tmp"
    mv "$tmp" "$f"
    note "$f (index maintained between markers)"
}

install_claude() {
    if [ "$USER_INSTALL" = 1 ]; then base="$HOME/.claude/skills"; else base="$TARGET/.claude/skills"; fi
    for s in $SKILLS; do copy_to "$SRC/$s/SKILL.md" "$base/$s/SKILL.md"; done
}
install_copilot() {
    # Copilot project skills: .github/skills/<name>/SKILL.md (on-demand injection).
    # NOT .github/instructions/*.instructions.md — that surface is always-applied
    # and expects applyTo frontmatter these skills deliberately don't carry.
    for s in $SKILLS; do copy_to "$SRC/$s/SKILL.md" "$TARGET/.github/skills/$s/SKILL.md"; done
}
install_agentsmd() { # codex and opencode share this convention
    for s in $SKILLS; do copy_to "$SRC/$s/SKILL.md" "$TARGET/.agents/skills/$s.md"; done
    update_agents_index "$TARGET/AGENTS.md" ".agents/skills"
}
install_cursor() {
    for s in $SKILLS; do copy_to "$SRC/$s/SKILL.md" "$TARGET/.cursor/rules/$s.mdc"; done
}

case "$TOOL" in
    claude)         install_claude ;;
    copilot)        install_copilot ;;
    codex|opencode) install_agentsmd ;;
    cursor)         install_cursor ;;
    all)            install_claude
                    install_copilot
                    install_agentsmd   # covers codex AND opencode
                    install_cursor ;;
esac

printf 'Installed:\n%s' "$INSTALLED"
if [ "$TOOL" = all ] || [ "$TOOL" = codex ] || [ "$TOOL" = opencode ]; then
    printf '(codex and opencode share the .agents/skills + AGENTS.md convention)\n'
fi
printf '\nNext step: finish tamper isolation — read and follow the taniko-protect-gates\nskill (deny rules for every protected glob; it ends in a checklist).\n'

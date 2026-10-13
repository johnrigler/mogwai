#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$root"

# Verify plain Bash works without Daisy or ALP.
source scripts/mogwai.bash
declare -F m.file.fix m.pick >/dev/null
if declare -F d.s >/dev/null || declare -F a.s >/dev/null; then
    echo "Unexpected dependency on Daisy or ALP" >&2
    exit 1
fi

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
cd "$work"
printf 'one\r\ntwo\r\n' > './-My Report (Final).TXT'
plan=$(m.file.fix --dry-run -- './-My Report (Final).TXT')
[[ $plan == *'My-Report-Final.TXT'* && -e './-My Report (Final).TXT' ]]
target=$(printf '%s\n' './-My Report (Final).TXT' | m.file.fix)
[[ $target == './My-Report-Final.TXT' && ! -e './-My Report (Final).TXT' ]]
[[ $(cat "$target") == $'one\ntwo' ]]
if grep -q $'\r' "$target"; then
    echo "CRLF remained in text file" >&2
    exit 1
fi

# Never rewrite original PDF content.
printf '%%PDF-1.4\r\nBinary\x00\r\n' > './Bad Document.pdf'
cp './Bad Document.pdf' before.pdf
printf '%s\n' './Bad Document.pdf' | m.file.fix >/dev/null
cmp -s before.pdf './Bad-Document.pdf'

# Reject collisions and symlinks.
printf old > './Name-File.txt'
printf new > './Name File.txt'
if m.file.fix './Name File.txt' >/dev/null 2>&1; then
    echo "Collision not refused" >&2
    exit 1
fi
[[ $(cat './Name-File.txt') == old && $(cat './Name File.txt') == new ]]
ln -s 'Name File.txt' 'Another File.txt'
if m.file.fix 'Another File.txt' >/dev/null 2>&1; then
    echo "Symlink not refused" >&2
    exit 1
fi

cat > editor-ok <<'SH'
#!/usr/bin/env bash
sed 's/^  The second  choice with spaces$/x The second  choice with spaces/' "$1" > "$1.edit"
cat "$1.edit" > "$1"
SH
chmod +x editor-ok
choice=$(printf '%s\n' 'First choice' 'The second  choice with spaces' 'extra' |
    MOGWAI_PICK_EDITOR="$work/editor-ok" m.pick)
[[ $choice == 'The second  choice with spaces' ]]

cat > editor-none <<'SH'
#!/usr/bin/env bash
exit 0
SH
chmod +x editor-none
if printf '%s\n' one two | MOGWAI_PICK_EDITOR="$work/editor-none" m.pick >/dev/null 2>&1; then
    echo "Missing choice not detected" >&2
    exit 1
fi
cat > editor-many <<'SH'
#!/usr/bin/env bash
sed 's/^  /x /' "$1" > "$1.edit"
cat "$1.edit" > "$1"
SH
chmod +x editor-many
if printf '%s\n' one two | MOGWAI_PICK_EDITOR="$work/editor-many" m.pick >/dev/null 2>&1; then
    echo "Multiple choices not rejected" >&2
    exit 1
fi
printf 'Mogwai shell tests passed.\n'

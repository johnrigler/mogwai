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
sed 's/^  \(\[000002\] \)/x \1/' "$1" > "$1.edit"
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
sed 's/^  \(\[[0-9][0-9][0-9][0-9][0-9][0-9]\] \)/x \1/' "$1" > "$1.edit"
cat "$1.edit" > "$1"
SH
chmod +x editor-many
if printf '%s\n' one two | MOGWAI_PICK_EDITOR="$work/editor-many" m.pick >/dev/null 2>&1; then
    echo "Multiple choices not rejected" >&2
    exit 1
fi

# Regression: adding an x marker must not become leading spaces in output.
printf 'shot' > 'Screen Shot 2024-08-17 at 11.13.38 PM.png'
cat > editor-insert <<'SH'
#!/usr/bin/env bash
sed 's/^  \(\[000001\] \)/x  \1/' "$1" > "$1.edit"
cat "$1.edit" > "$1"
SH
chmod +x editor-insert
result=$(printf '%s\n' 'Screen Shot 2024-08-17 at 11.13.38 PM.png' |
    MOGWAI_PICK_EDITOR="$work/editor-insert" m.pick | m.file.fix)
[[ $result == ./Screen-Shot-2024-08-17-at-11.13.38-PM.png ]]
[[ -f ./Screen-Shot-2024-08-17-at-11.13.38-PM.png ]]

# Lossless NUL mode handles leading spaces and embedded newlines.
name=$(printf ' odd\nfile.png_')
name=${name%_}
printf 'pixel' > "./$name"
printf '%s\0' "./$name" |
    MOGWAI_PICK_EDITOR="$work/editor-insert" m.pick -0 | m.file.fix -0 > selected.bin
IFS= read -r -d '' picked < selected.bin
[[ $picked == './odd-file.png' ]]
[[ $(wc -c < selected.bin) -eq 15 ]]
[[ $(cat './odd-file.png') == pixel ]]
# Every successful change is audited in .log.txt without changing stdout.
[[ -f .log.txt && $(wc -l < .log.txt) -eq 4 ]]
old=$(printf '%q' '-My Report (Final).TXT')
new=$(printf '%q' 'My-Report-Final.TXT')
grep -Fq -- "$old"$'\t'"$new" .log.txt
grep -Fq $'\tm.file.fix\trename+crlf\t' .log.txt
grep -Fq $'\tm.file.fix\trename\t' .log.txt
# Repeating an already normalized path is a no-op and creates no new entry.
m.file.fix './odd-file.png' >/dev/null
[[ $(wc -l < .log.txt) -eq 4 ]]
# The hidden audit log is reserved and cannot be silently renamed.
if m.file.fix ./.log.txt >/dev/null 2>&1; then
    echo "Audit log was renamed" >&2
    exit 1
fi
[[ -f .log.txt && $(wc -l < .log.txt) -eq 4 ]]
# Each directory gets its own audit log; previews don't create one.
mkdir -p nested
printf 'inside' > 'nested/Some File.txt'
m.file.fix --dry-run 'nested/Some File.txt' >/dev/null
[[ ! -e nested/.log.txt ]]
m.file.fix 'nested/Some File.txt' >/dev/null
[[ -f nested/Some-File.txt && -f nested/.log.txt ]]
[[ $(wc -l < nested/.log.txt) -eq 1 ]]
grep -Fq -- 'Some\\ File.txt' nested/.log.txt
# Refuse a planted .log.txt symlink before changing a file.
mkdir -p hostile
printf 'outside' > outside.log
ln -s ../outside.log hostile/.log.txt
printf 'test' > 'hostile/Has Space.txt'
if m.file.fix 'hostile/Has Space.txt' >/dev/null 2>&1; then
    echo "Audit log symlink was followed" >&2
    exit 1
fi
[[ -f 'hostile/Has Space.txt' && ! -e 'hostile/Has-Space.txt' ]]
[[ $(cat outside.log) == outside ]]
printf 'Mogwai shell tests passed.\n'

#!/usr/bin/env bash
# Publish plain-text inventories of the public transaction archive.
set -euo pipefail
if [[ -f "$HOME/.config/mogwai/bsv.env" ]]; then
    source "$HOME/.config/mogwai/bsv.env"
fi
root="${1:-${CHISEL_DATA_ROOT:-$HOME/chisel_data}}"
cd -- "$root/transactions"
umask 022
export LC_ALL=C
shopt -s nullglob
# Serialize runs; the lock lives outside the published directory.
state="${XDG_STATE_HOME:-$HOME/.local/state}/mogwai"
mkdir -p -- "$state"
exec 9>"$state/publish-files.lock"
flock -n 9 || exit 0
tmp=""
trap '[[ -z "$tmp" ]] || rm -f -- "$tmp"' EXIT
dirs=()
for dir in */; do
    name="${dir%/}"
    [[ ! -L "$name" && "$name" =~ ^[A-Za-z0-9][A-Za-z0-9_-]*$ ]] || continue
    tmp=$(mktemp -- "$name/.files.tmp.XXXXXXXX")
    find "$name" -maxdepth 1 -type f -printf '%f\n' |
        awk '/^(0[xX])?[0-9a-fA-F]{64}\.json$/ || /^[1-9A-HJ-NP-Za-km-z]{1,45}-[0-9a-fA-F]{12}\.json$/' |
        sort -u > "$tmp"
    chmod 644 "$tmp"
    if ! cmp -s -- "$tmp" "$name/.files"; then
        mv -fT -- "$tmp" "$name/.files"
    else
        rm -f -- "$tmp"
    fi
    tmp=""
    dirs+=("$name")
done
tmp=$(mktemp -- .files.tmp.XXXXXXXX)
if (("${#dirs[@]}")); then printf '%s\n' "${dirs[@]}" | sort -u > "$tmp"; fi
chmod 644 "$tmp"
if ! cmp -s -- "$tmp" .files; then mv -fT -- "$tmp" .files; else rm -f -- "$tmp"; fi
tmp=""
printf 'Published inventories for %s currency directories in %s\n' "${#dirs[@]}" "$PWD"

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
# Each operation is explicitly checked: errexit is suppressed inside an if.
publish_currency() {
    local name="$1"
    tmp=$(mktemp -- "$name/.files.tmp.XXXXXXXX") || return 1
    if ! find "$name" -maxdepth 1 -type f -printf '%f\n' |
        awk '/^(0[xX])?[0-9a-fA-F]{64}\.json$/ || /^[1-9A-HJ-NP-Za-km-z]{1,45}-[0-9a-fA-F]{12}\.json$/' |
        sort -u > "$tmp"; then
        return 1
    fi
    chmod 644 "$tmp" || return 1
    if ! cmp -s -- "$tmp" "$name/.files"; then
        mv -fT -- "$tmp" "$name/.files" || return 1
    else
        rm -f -- "$tmp" || return 1
    fi
    tmp=""
}
dirs=()
failed=()
published=0
for dir in */; do
    name="${dir%/}"
    [[ ! -L "$name" && "$name" =~ ^[A-Za-z0-9][A-Za-z0-9_-]*$ ]] || continue
    # Keep every real currency directory discoverable, even if its inventory
    # could not be refreshed. Readers can use the last inventory or HTTP fallback.
    dirs+=("$name")
    if publish_currency "$name"; then
        printf 'OK: %s\n' "$name"
        published=$((published + 1))
    else
        if [[ -n "$tmp" ]]; then rm -f -- "$tmp" || true; fi
        tmp=""
        failed+=("$name")
        if [[ -f "$name/.files" && -r "$name/.files" ]]; then
            printf 'WARNING: %s: refresh failed; keeping previous .files\n' "$name" >&2
        else
            printf 'WARNING: %s: refresh failed; no readable .files; continuing\n' "$name" >&2
        fi
    fi
done
tmp=$(mktemp -- .files.tmp.XXXXXXXX)
if (("${#dirs[@]}")); then printf '%s\n' "${dirs[@]}" | sort -u > "$tmp"; fi
chmod 644 "$tmp"
if ! cmp -s -- "$tmp" .files; then mv -fT -- "$tmp" .files; else rm -f -- "$tmp"; fi
tmp=""
printf 'Published inventories for %s of %s currency directories in %s\n' "$published" "${#dirs[@]}" "$PWD"
if (("${#failed[@]}")); then
    printf 'Partial publication: failed currencies: %s\n' "${failed[*]}" >&2
    exit 1
fi

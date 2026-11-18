#!/usr/bin/env bash
# Copy Mogwai's public config examples into private local paths.
# Does not overwrite existing files or restart any services.
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
install -d -m 700 "$HOME/.config/mogwai"
install -d -m 700 "$HOME/.config/fileproxy"

copy_if_missing() {
  local from="$1" to="$2"
  if [[ -e "$to" || -L "$to" ]]; then
    printf 'PRESERVED: %s\n' "$to"
  else
    install -m 600 "$from" "$to"
    printf 'CREATED: %s\n' "$to"
  fi
}

copy_if_missing "$repo_root/config-examples/ledgers.json" "$HOME/.config/mogwai/ledgers.json"
copy_if_missing "$repo_root/config-examples/pinata.json" "$HOME/.config/mogwai/pinata.json"
copy_if_missing "$repo_root/config-examples/fileproxy.json" "$HOME/.config/fileproxy/config.json"

printf '\nEdit only what you use. The ledger reader currently supports read-only Polygon.\n'
printf 'Do not copy signing keys into these files or expose them through FileProxy.\n'

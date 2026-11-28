#!/usr/bin/env bash
set -euo pipefail
tools_dir=$(cd -- "$(dirname -- "$0")" && pwd)
config_file="$HOME/.config/mogwai/bsv.env"
if [[ -f "$config_file" ]]; then source "$config_file"; fi
db_file="${BSV_DB:-$HOME/.local/state/mogwai/bsv-index.sqlite3}"
data_root="${CHISEL_DATA_ROOT:-$HOME/chisel_data}"
export_dir="${BSV_EXPORT_DIR:-$data_root/bsv}"
action="${1:-audit}"
if (( $# )); then shift; fi
exec python3 "$tools_dir/bsv_custodian.py" "$action" --db "$db_file" --data-root "$data_root" --feed-dir "$export_dir/custodian" "$@"

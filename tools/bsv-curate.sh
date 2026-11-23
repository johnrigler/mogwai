#!/usr/bin/env bash
# Read the same BSV database and root settings as tools/bsv.sh.
set -euo pipefail
tools_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
config_file="$HOME/.config/mogwai/bsv.env"
if [[ -f "$config_file" ]]; then
    source "$config_file"
fi
db_file="${BSV_DB:-$HOME/.local/state/mogwai/bsv-index.sqlite3}"
data_root="${CHISEL_DATA_ROOT:-$HOME/chisel_data}"
export_dir="${BSV_EXPORT_DIR:-$data_root/bsv}"
python3 "$tools_dir/bsv_curator.py" --db "$db_file" --data-root "$data_root" --export-dir "$export_dir" "$@"

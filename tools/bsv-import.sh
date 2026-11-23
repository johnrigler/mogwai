#!/usr/bin/env bash
# Reuse the scanner's configured archive root; imported records add no coverage.
set -euo pipefail
tools_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
config_file="$HOME/.config/mogwai/bsv.env"
if [[ -f "$config_file" ]]; then
    source "$config_file"
fi
python3 "$tools_dir/bsv_recovery_import.py" --data-root "${CHISEL_DATA_ROOT:-$HOME/chisel_data}" "$@"

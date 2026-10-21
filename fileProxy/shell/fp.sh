# Source from Bash after cloning Mogwai.
# Works from any working directory and keeps the Python CLI in one place.
# Example: source ~/mogwai/fileProxy/shell/fp.sh
: "${FILEPROXY_HOME:=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)}"
fp ()
{
    local fileproxy_dir="${FILEPROXY_HOME:-$HOME/mogwai/fileProxy}"
    python3 "$fileproxy_dir/fp.py" "$@"
}

#!/usr/bin/env bash
# Control the standalone BSV scanner without installing a system service.
set -euo pipefail

tools_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
scanner="$tools_dir/bsv_indexer.py"
state_dir="${XDG_STATE_HOME:-$HOME/.local/state}/mogwai/bsv-daemon"
pid_file="$state_dir/daemon.pid"
log_file="$state_dir/daemon.log"
config_file="$HOME/.config/mogwai/bsv.env"
if [[ -f "$config_file" ]]; then
    source "$config_file"
fi
db_file="${BSV_DB:-$HOME/.local/state/mogwai/bsv-index.sqlite3}"
export_dir="${BSV_EXPORT_DIR:-$state_dir/public}"

running() {
    local -a command=()
    [[ -f "$pid_file" ]] || return 1
    read -r pid < "$pid_file" || return 1
    [[ "$pid" =~ ^[1-9][0-9]*$ ]] && kill -0 "$pid" 2>/dev/null || return 1
    [[ -r "/proc/$pid/cmdline" ]] || return 1
    mapfile -d '' -t command < "/proc/$pid/cmdline" 2>/dev/null || return 1
    # A stale PID file must never signal an unrelated process.
    [[ "${command[1]:-}" == "$scanner" && "${command[2]:-}" == daemon ]]
}

action="${1:-status}"
if (( $# )); then shift; fi
case "$action" in
    start|stop|status) ;;
    *) echo "Usage: bash tools/bsv.sh {start|stop|status} [daemon options]" >&2; exit 2 ;;
esac
mkdir -p -- "$state_dir"
# Serialize control commands. The detached scanner must not inherit this lock.
exec 9>"$state_dir/control.lock"
flock 9

case "$action" in
    start)
        if running; then
            echo "BSV scanner is already running (PID $pid). Log: $log_file"
            exit 0
        fi
        rm -f -- "$pid_file"
        mkdir -p -- "$(dirname -- "$db_file")" "$export_dir"
        # Covers a scanner started by hand, cron or systemd as well.
        exec 8>"$db_file.lock"
        if ! flock -n 8; then
            echo "BSV database is in use by another scanner: $db_file" >&2
            exit 1
        fi
        flock -u 8
        exec 8>&-
        PYTHONUNBUFFERED=1 nohup python3 "$scanner" daemon --db "$db_file" --export-dir "$export_dir" "$@" \
            </dev/null >>"$log_file" 2>&1 9>&- &
        pid=$!
        printf '%s\n' "$pid" > "$pid_file"
        sleep 0.3
        if ! running; then
            rm -f -- "$pid_file"
            echo "BSV scanner exited during startup. Check: $log_file" >&2
            tail -n 10 -- "$log_file" >&2
            exit 1
        fi
        echo "Started BSV scanner (PID $pid)."
        echo "Log: $log_file"
        echo "Export: $export_dir"
        ;;
    stop)
        if ! running; then
            rm -f -- "$pid_file"
            echo "No managed BSV scanner is running."
            exit 0
        fi
        echo "Stopping BSV scanner (PID $pid); waiting for the current request and export."
        kill -TERM "$pid"
        for (( attempt=0; attempt<90; attempt++ )); do
            if ! running; then
                rm -f -- "$pid_file"
                echo "Stopped BSV scanner. Saved checkpoints will resume on start."
                exit 0
            fi
            sleep 0.5
        done
        echo "Stop requested; scanner is still shutting down. Check: $log_file" >&2
        exit 1
        ;;
    status)
        if running; then
            echo "BSV scanner is running (PID $pid)."
        else
            echo "No managed BSV scanner is running."
        fi
        echo "Log: $log_file"
        python3 "$scanner" status --db "$db_file" 9>&-
        ;;
esac

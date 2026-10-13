#!/usr/bin/env bash
# Mogwai shell helpers. Source this file; no ALP or Daisy dependency.
# m.file.fix: newline-delimited paths from stdin or positional arguments.
# m.pick: choose a line in a text editor, preserving its original whitespace.

_m.file.name ()
{
    local name=$1
    LC_ALL=C printf '%s' "$name" |
        LC_ALL=C sed -E 's/[[:space:]]+/-/g; s/[^A-Za-z0-9._-]+/-/g; s/-+/-/g; s/-+\././g; s/\.-+/./g; s/^[._-]+//; s/[._-]+$//'
}

_m.file.one ()
{
    local original=$1 dry_run=$2 from dir base fixed target temp='' cr=$'\r'
    # Convert a leading-dash argument to an unambiguous relative path.
    from=$original
    [[ $from != -* ]] || from="./$from"
    if [[ ! -f $from || -L $from ]]; then
        printf 'm.file.fix: not a regular file: %s\n' "$original" >&2
        return 1
    fi
    dir=${from%/*}
    [[ $dir != "$from" ]] || dir=.
    base=${from##*/}
    if [[ $dir =~ [[:space:]] ]]; then
        printf 'm.file.fix: rename whitespace-containing parent first: %s\n' "$dir" >&2
        return 1
    fi
    fixed=$(_m.file.name "$base") || return
    if [[ -z $fixed || $fixed == . || $fixed == .. ]]; then
        printf 'm.file.fix: cannot derive a safe name: %s\n' "$original" >&2
        return 1
    fi
    target=$dir/$fixed
    if [[ $target != "$from" && ( -e $target || -L $target ) ]]; then
        printf 'm.file.fix: destination exists, refusing: %s\n' "$target" >&2
        return 1
    fi
    # Only recognized text formats have line endings normalized.
    # Binary/PDF/image bytes are never modified.
    local text_file=0 convert=0
    case ${base##*.} in
        txt|text|md|markdown|csv|tsv|json|jsonl|html|htm|css|js|mjs|cjs|ts|sh|bash|py|php|xml|yaml|yml|ini|cfg|conf|log|sql|svg|TXT|CSV|MD|JSON|HTML|SH)
            text_file=1 ;;
    esac
    if (( text_file )); then
        if LC_ALL=C grep -Iq . "$from"; then
            if LC_ALL=C grep -q "$cr" "$from"; then convert=1; fi
        fi
    fi
    if (( dry_run )); then
        printf 'm.file.fix: %s -> %s%s\n' "$original" "$target" "$([[ $convert == 1 ]] && printf ' [CRLF -> LF]')"
        return 0
    fi
    if (( convert )); then
        temp=$(mktemp "$dir/.mogwai-fix.XXXXXXXX") || return
        if ! cp -p "$from" "$temp"; then rm -f "$temp"; return 1; fi
        if ! sed "s/${cr}\$//" "$from" > "$temp"; then
            rm -f "$temp"
            return 1
        fi
        if [[ $target == "$from" ]]; then
            mv "$temp" "$from" || { rm -f "$temp"; return 1; }
        else
            # Hardlink creation fails if another process already owns target.
            ln "$temp" "$target" || { rm -f "$temp"; return 1; }
            rm -f "$temp" "$from"
        fi
    elif [[ $target != "$from" ]]; then
        ln "$from" "$target" || return 1
        rm -f "$from"
    fi
    printf '%s\n' "$target"
}

m.file.fix ()
{
    local dry_run=0 path failure=0
    if [[ ${1:-} == --dry-run ]]; then dry_run=1; shift; fi
    if [[ ${1:-} == -- ]]; then shift; fi
    if (( $# )); then
        for path in "$@"; do
            _m.file.one "$path" "$dry_run" || failure=1
        done
    else
        if [[ -t 0 ]]; then
            printf 'usage: m.file.fix [--dry-run] [--] FILE ...\n' >&2
            printf 'or: find . -type f -print | m.file.fix\n' >&2
            return 2
        fi
        while IFS= read -r path || [[ -n $path ]]; do
            [[ -n $path ]] || continue
            _m.file.one "$path" "$dry_run" || failure=1
        done
    fi
    return "$failure"
}

m.pick ()
{
    local editor=${MOGWAI_PICK_EDITOR:-${VISUAL:-${EDITOR:-vi}}}
    local tmp line selected='' marks=0 status=0
    (( $# == 0 )) || { printf 'usage: lines | m.pick\n' >&2; return 2; }
    if [[ -t 0 ]]; then
        printf 'm.pick: provide newline-delimited choices on stdin\n' >&2
        return 2
    fi
    tmp=$(mktemp "${TMPDIR:-/tmp}/mogwai-pick.XXXXXXXX") || return
    # The two-space prefix makes selection unambiguous even when a real
    # option begins with x. Replace the FIRST space with x in the editor.
    while IFS= read -r line || [[ -n $line ]]; do
        printf '  %s\n' "$line" >> "$tmp"
    done
    if [[ ! -s $tmp ]]; then
        rm -f "$tmp"
        printf 'm.pick: no choices on stdin\n' >&2
        return 1
    fi
    printf 'm.pick: replace the first space of ONE line with x, then save and quit.\n' >&2
    if ( : </dev/tty ) 2>/dev/null; then
        "$editor" "$tmp" </dev/tty >/dev/tty || status=$?
    else
        "$editor" "$tmp" || status=$?
    fi
    if (( status )); then
        rm -f "$tmp"
        printf 'm.pick: editor exited with status %s\n' "$status" >&2
        return "$status"
    fi
    while IFS= read -r line || [[ -n $line ]]; do
        if [[ $line == 'x '* ]]; then
            ((marks+=1))
            selected=${line:2}
        fi
    done < "$tmp"
    rm -f "$tmp"
    if (( marks != 1 )); then
        printf 'm.pick: expected exactly one x-marked line; got %s\n' "$marks" >&2
        return 1
    fi
    printf '%s\n' "$selected"
}

#!/usr/bin/env bash
# Mogwai shell helpers. Source this file; no ALP or Daisy dependency.
# m.file.fix: newline-delimited paths from stdin or positional arguments.
# m.pick: choose a line in a text editor, preserving its original whitespace.

_m.file.name ()
{
    local name=$1 nl cr tab
    printf -v nl '\n'
    printf -v cr '\r'
    printf -v tab '\t'
    name=${name//$nl/-}
    name=${name//$cr/-}
    name=${name//$tab/-}
    LC_ALL=C printf '%s' "$name" |
        LC_ALL=C sed -E 's/[[:space:]]+/-/g; s/[^A-Za-z0-9._-]+/-/g; s/-+/-/g; s/-+\././g; s/\.-+/./g; s/^[._-]+//; s/[._-]+$//'
}

_m.file.one ()
{
    local original=$1 dry_run=$2 output_null=$3 from dir base fixed target temp='' cr
    printf -v cr '\r'
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
    if (( output_null )); then printf '%s\0' "$target"; else printf '%s\n' "$target"; fi
}

m.file.fix ()
{
    local dry_run=0 null_mode=0 path failure=0
    while (( $# )); do
        case $1 in
            --dry-run) dry_run=1; shift ;;
            -0|--null) null_mode=1; shift ;;
            --) shift; break ;;
            *) break ;;
        esac
    done
    if (( $# )); then
        for path in "$@"; do
            _m.file.one "$path" "$dry_run" "$null_mode" || failure=1
        done
    else
        if [[ -t 0 ]]; then
            printf 'usage: m.file.fix [--dry-run] [-0|--null] [--] FILE ...\n' >&2
            printf 'or: find . -type f -print0 | m.pick -0 | m.file.fix -0\n' >&2
            return 2
        fi
        if (( null_mode )); then
            while IFS= read -r -d '' path; do
                [[ -n $path ]] || continue
                _m.file.one "$path" "$dry_run" "$null_mode" || failure=1
            done
        else
            while IFS= read -r path || [[ -n $path ]]; do
                [[ -n $path ]] || continue
                _m.file.one "$path" "$dry_run" "$null_mode" || failure=1
            done
        fi
    fi
    return "$failure"
}

# Mark a numbered editor row; return the original bytes, not menu whitespace.
# NUL mode allows lossless paths from find -print0.
m.pick ()
{
    local null_mode=0 editor=${MOGWAI_PICK_EDITOR:-${VISUAL:-${EDITOR:-vi}}}
    local tmp item display line details='' id n marks=0 selected='' status=0
    local -a choices=() shown=()
    case ${1:-} in
        -0|--null) null_mode=1; shift ;;
    esac
    (( $# == 0 )) || { printf 'usage: lines | m.pick [-0|--null]\n' >&2; return 2; }
    [[ ! -t 0 ]] || { printf 'm.pick: provide candidates on stdin\n' >&2; return 2; }

    if (( null_mode )); then
        while IFS= read -r -d '' item; do
            [[ -n $item ]] && choices+=("$item")
        done
    else
        while IFS= read -r item || [[ -n $item ]]; do
            [[ -n $item ]] && choices+=("$item")
        done
    fi
    ((${#choices[@]})) || { printf 'm.pick: no choices supplied\n' >&2; return 1; }

    tmp=$(mktemp "${TMPDIR:-/tmp}/mogwai-pick.XXXXXXXX") || return
    for ((n=0; n<${#choices[@]}; n++)); do
        item=${choices[n]}
        # Display controls visibly; the true path stays in choices.
        display=${item//$'\n'/\\n}
        display=${display//$'\r'/\\r}
        display=${display//$'\t'/\\t}
        details=''
        if [[ -e $item || -L $item ]]; then
            if details=$(stat -c '%d:%i' -- "$item" 2>/dev/null); then
                details=" [dev:ino $details]"
            elif details=$(stat -f '%d:%i' -- "$item" 2>/dev/null); then
                details=" [dev:ino $details]"
            else details=''; fi
        fi
        shown+=("$display$details")
        printf '  [%06d] %s\n' "$((n+1))" "${shown[n]}" >> "$tmp"
    done

    printf 'm.pick: mark ONE row with x at column 1, then save and quit.\n' >&2
    if ( : </dev/tty ) 2>/dev/null; then
        "$editor" "$tmp" </dev/tty >/dev/tty || status=$?
    else
        "$editor" "$tmp" || status=$?
    fi
    if ((status)); then
        rm -f -- "$tmp"
        printf 'm.pick: editor returned status %s\n' "$status" >&2
        return "$status"
    fi

    while IFS= read -r line || [[ -n $line ]]; do
        # Replaced first space: x [ID]; inserted marker: x  [ID].
        if [[ $line =~ ^x[[:space:]]+\[([0-9]{6})\]\ (.*)$ ]]; then
            id=$((10#${BASH_REMATCH[1]}))
            if ((id < 1 || id > ${#choices[@]})) || [[ ${BASH_REMATCH[2]} != "${shown[id-1]}" ]]; then
                printf 'm.pick: marked row was altered or invalid\n' >&2
                rm -f -- "$tmp"
                return 1
            fi
            ((marks+=1))
            selected=${choices[id-1]}
        fi
    done < "$tmp"
    rm -f -- "$tmp"
    ((marks==1)) || { printf 'm.pick: expected one x-marked row, got %s\n' "$marks" >&2; return 1; }
    if ((null_mode)); then
        printf '%s\0' "$selected"
    else
        printf '%s\n' "$selected"
    fi
}

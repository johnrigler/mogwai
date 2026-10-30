- () 
{ 
    echo "$*"
}
-- () 
{ 
    echo -n "$*"
}

_d.fs () 
{ 
    d.fs "$@"
}
a.date () 
{ 
    :;
    if [[ -z $1 ]]; then
        date;
        : "adffffffffffffff";
    else
        date "+%"$1;
        - "zzzzzzz ";
    fi;
    : date "+%u"
}
a.date.W () 
{ 
    date "+%W"
}
a.date.w () 
{ 
    date "+%w"
}
a.date.yyyy () 
{ 
    date "+%Y"
}
a.dir () 
{ 
    cd -- "${_ALP_:?source alp.bash first}"
}
a.e () 
{ 
    : B='$'"$1";
    : eval echo "$1=$(echo $B)";
    eval echo "$1=$(echo '$'$1)"
}
a.env () 
{ 
    __T=a.env;
    : : Shows _ALP_ Environment Variables;
    env | grep '_ALP'
}
a.eval () 
{ 
    : : Reload ALP functions or a module, then restore the curated helpers;
    local _alp_eval_dir;
    if [[ $# == 0 ]]; then
        _alp_eval_dir="$_ALP_/functions";
    else
        if [[ -d "$1" ]]; then
            _alp_eval_dir=$1;
        else
            _alp_eval_dir="$_ALP_/$1/functions";
        fi;
    fi;
    local _alp_eval_status=0;
    alp2 "$_alp_eval_dir" || _alp_eval_status=$?;
    . "$_ALP_/core.bash" || return;
    return "$_alp_eval_status"
}
a.f () 
{ 
    local _alp_f_name;
    _alp_f_name=$(a.name "${1:-}") || return;
    declare -f -- "$_alp_f_name"
}
a.fS () 
{ 
    a.save "${1:-}" "${2:-.}" a.S
}
a.fs () 
{ 
    a.save "${1:-}" "${2:-.}" a.s
}
a.fss () 
{ 
    a.save "${1:-}" "${2:-.}" a.ss
}
a.h () 
{ 
    : : Capture the previous history command as a function without running it;
    local _alp_history_name=${1:-} _alp_history_body _alp_history_definition;
    [[ $# == 1 && "$_alp_history_name" =~ ^[A-Za-z_.-][A-Za-z0-9_.-]*$ ]] || { 
        printf 'usage: a.h function.name\n' 1>&2;
        return 2
    };
    _alp_history_body=$(builtin fc -ln -1 -1) || return;
    if [[ -z "$_alp_history_body" || "$_alp_history_body" =~ ^[[:space:]]*a\.h([[:space:]]|$) ]]; then
        printf 'a.h: no preceding command to capture\n' 1>&2;
        return 1;
    fi;
    printf '%s\n' "$_alp_history_body" | bash -n || return;
    _alp_history_definition=$(printf '%s ()\n{\n%s\n}\n' "$_alp_history_name" "$_alp_history_body");
    eval "$_alp_history_definition"
}
a.index () 
{ 
    : : Index a directory without executing its contents;
    local _alp_index_dir _alp_index_mode _alp_index_tmp _alp_index_path;
    local _alp_index_name _alp_index_base _alp_index_action LC_ALL=C;
    _alp_index_dir=$(cd -- "${1:-.}" && pwd -P) || return;
    _alp_index_mode=${2:-functions};
    case "$_alp_index_mode" in 
        functions | scripts | view)

        ;;
        *)
            printf 'a.index: mode must be functions, scripts, or view\n' 1>&2;
            return 2
        ;;
    esac;
    _alp_index_tmp=$(mktemp "$_alp_index_dir/.files.txt.XXXXXX") || return;
    { 
        printf '# ALP mode: %s\n' "$_alp_index_mode";
        printf '# action<TAB>relative path; legacy plain paths mean source\n';
        for _alp_index_path in "$_alp_index_dir"/*;
        do
            [[ -e "$_alp_index_path" ]] || continue;
            _alp_index_name=${_alp_index_path##*/};
            _alp_index_base=$_alp_index_name;
            if [[ "$_alp_index_base" =~ ^(.+)-[0-9]+(\.[0-9]+)?$ ]]; then
                _alp_index_base=${BASH_REMATCH[1]};
            fi;
            [[ "$_alp_index_name" == alp-view.html ]] && continue;
            case "$_alp_index_name" in 
                *'	'* | *'
'* | *''*)
                    printf 'a.index: unsupported filename: %q\n' "$_alp_index_name" 1>&2;
                    continue
                ;;
            esac;
            _alp_index_action=view;
            if [[ -d "$_alp_index_path" ]]; then
                _alp_index_action=directory;
            else
                if [[ -f "$_alp_index_path" ]]; then
                    case "$_alp_index_mode" in 
                        scripts)
                            case "$_alp_index_base" in 
                                *.sh | *.bash | *.py | *.js | *.mjs)
                                    _alp_index_action=script
                                ;;
                                *)
                                    [[ -x "$_alp_index_path" ]] && _alp_index_action=script
                                ;;
                            esac
                        ;;
                        functions)
                            case "$_alp_index_base" in 
                                *.sh | *.bash)
                                    _alp_index_action=source
                                ;;
                                *.py | *.js | *.mjs)
                                    _alp_index_action=script
                                ;;
                                README | LICENSE | *.md | *.txt | *.json | *.html | *.css | *.transactions | *.png | *.jpg | *.jpeg | *.gif | *.pdf | *.sqlite)

                                ;;
                                *)
                                    if [[ "$_alp_index_name" =~ ^.+-[0-9]+(\.[0-9]+)?$ ]]; then
                                        _alp_index_action=source;
                                    else
                                        if LC_ALL=C grep -Eq '^[[:space:]]*(function[[:space:]]+)?[A-Za-z_.-][A-Za-z0-9_.-]*[[:space:]]*\([[:space:]]*\)' "$_alp_index_path"; then
                                            _alp_index_action=source;
                                        fi;
                                    fi
                                ;;
                            esac
                        ;;
                    esac;
                else
                    continue;
                fi;
            fi;
            printf '%s\t%s\n' "$_alp_index_action" "$_alp_index_name";
        done
    } > "$_alp_index_tmp";
    if ! mv -- "$_alp_index_tmp" "$_alp_index_dir/.files.txt"; then
        rm -f -- "$_alp_index_tmp";
        return 1;
    fi;
    printf '%s\n' "$_alp_index_dir/.files.txt"
}
a.l () 
{ 
    declare -F | while read -r _alp_l_declare _alp_l_flag _alp_l_name; do
        [[ "$_alp_l_name" == a.* ]] && printf '%s\n' "$_alp_l_name";
        :;
    done
}
a.make () 
{ 
    __T='a.make';
    : : Build new ALP file.;
    _FILE="alp.bash";
    a.dir;
    - "::() { :; }" > $_FILE;
    a.f alp >> $_FILE;
    a.l | while read CMD; do
        a.f $CMD;
    done >> $_FILE;
    a.back
}
a.mkmod () 
{ 
    __T=a.mkmod;
    : : Create ALP Module, takes two variables: DIR PRE;
    export _ALP_MODULE="$1";
    a.dir;
    source $_ALP_MODULE.bash;
    function _a.mkmod () 
    { 
        NAME="$_ALP_MODULE".a.$1;
        declare -f a.$1;
        - "$NAME () { __T=$NAME; :: $2 ; $3; }" > $$;
        source $$;
        rm $$
    };
    _a.mkmod dir "Change to module home directory" "cd $_A_MODULE/"'$1';
    CMD="declare -F | grep 'declare -f $_A_MODULE_PRE.' | cut -c 12-";
    _a.mkmod l "List module functions" "$CMD"
}
a.mod () 
{ 
    __T=a.mod;
    : : Set ALP Module, takes one variable;
    : This is a level of recursion which;
    : is interesting, but not currently;
    : implemented;
    : use with care;
    export _ALP_MOD="$1";
    if [[ $_ALP_MOD != 'alp' ]]; then
        _FILE=$_ALP_/$_ALP_MOD.bash;
        touch $_FILE;
        source $_FILE;
        function _a.mod () 
        { 
            NAME="$1.$2";
            - $NAME;
            - "$NAME () { __T=$NAME; :: $3 ; $4; }" > $$;
            source $$;
            rm $$;
            declare -f $NAME
        };
        CMD="declare -F | grep 'declare -f $_ALP_MOD' | cut -c 12-";
        _a.mod $_ALP_MOD l "List module functions" "$CMD";
    fi
}
a.name () 
{ 
    local _alp_name=${1:-};
    [[ -n "$_alp_name" ]] || { 
        printf 'usage: a.name function-or-snapshot\n' 1>&2;
        return 2
    };
    if ! declare -F -- "$_alp_name" > /dev/null; then
        _alp_name=${_alp_name##*/};
        if [[ "$_alp_name" =~ ^(.+)-[0-9]+(\.[0-9]+)?$ ]]; then
            _alp_name=${BASH_REMATCH[1]};
        fi;
    fi;
    declare -F -- "$_alp_name" > /dev/null || { 
        printf 'ALP: no function: %s\n' "$_alp_name" 1>&2;
        return 1
    };
    printf '%s\n' "$_alp_name"
}
a.pre () 
{ 
    : YYYY/MMWw;
    T=$(a.dte);
    mkdir -p ~/$1/$T;
    : Create a script file with date stamp;
    WD=$(pwd);
    : Move into Directory;
    cd ~/$1/$T;
    script $(a.tme);
    pwd;
    cd $WD
}
a.run () 
{ 
    : : Run one script entry explicitly, with arguments;
    local _alp_run_dir _alp_run_name _alp_run_base _alp_run_line _alp_run_found=0;
    [[ $# -ge 2 ]] || { 
        printf 'usage: a.run directory script [arguments...]\n' 1>&2;
        return 2
    };
    _alp_run_dir=$(cd -- "$1" && pwd -P) || return;
    _alp_run_name=$2;
    _alp_run_base=$_alp_run_name;
    if [[ "$_alp_run_base" =~ ^(.+)-[0-9]+(\.[0-9]+)?$ ]]; then
        _alp_run_base=${BASH_REMATCH[1]};
    fi;
    shift 2;
    [[ -f "$_alp_run_dir/.files.txt" ]] || { 
        printf 'a.run: index this directory first\n' 1>&2;
        return 1
    };
    while IFS= read -r _alp_run_line || [[ -n "$_alp_run_line" ]]; do
        _alp_run_line=${_alp_run_line%''};
        [[ "$_alp_run_line" == "script"'	'"$_alp_run_name" ]] && _alp_run_found=1;
    done < "$_alp_run_dir/.files.txt";
    [[ $_alp_run_found == 1 ]] || { 
        printf 'a.run: not a script entry: %s\n' "$_alp_run_name" 1>&2;
        return 1
    };
    case "$_alp_run_name" in 
        '' | /* | .. | ../* | */../* | */..)
            printf 'a.run: invalid relative path\n' 1>&2;
            return 2
        ;;
    esac;
    ( cd -- "$_alp_run_dir" || exit;
    if [[ -x "$_alp_run_name" ]]; then
        "./$_alp_run_name" "$@";
    else
        case "$_alp_run_base" in 
            *.sh | *.bash)
                bash -- "$_alp_run_name" "$@"
            ;;
            *.py)
                python3 -- "$_alp_run_name" "$@"
            ;;
            *.js | *.mjs)
                printf 'a.run: add a shebang and executable permission to choose the JavaScript runtime\n' 1>&2;
                exit 2
            ;;
            *)
                printf 'a.run: script needs a shebang and executable permission\n' 1>&2;
                exit 2
            ;;
        esac;
    fi )
}
a.s () 
{ 
    : : BSD sum checksum and block count, preserving the existing format;
    local _alp_sum _alp_blocks;
    read -r _alp_sum _alp_blocks < <(LC_ALL=C sum) || return;
    printf '%s.%s\n' "$_alp_sum" "$_alp_blocks"
}
a.save () 
{ 
    : : Save any function namespace using a selected checksum function;
    local _alp_save_name _alp_save_dir _alp_save_hash _alp_save_tmp _alp_save_file;
    _alp_save_name=$(a.name "${1:-}") || return;
    [[ "$_alp_save_name" != *[!A-Za-z0-9_.-]* ]] || { 
        printf 'a.save: unsupported filename: %s\n' "$_alp_save_name" 1>&2;
        return 2
    };
    _alp_save_dir=$(cd -- "${2:-.}" && pwd -P) || return;
    declare -F -- "${3:-a.s}" > /dev/null || { 
        printf 'a.save: no checksum function: %s\n' "${3:-a.s}" 1>&2;
        return 1
    };
    _alp_save_tmp=$(mktemp "$_alp_save_dir/.alp-save.XXXXXX") || return;
    if ! declare -f -- "$_alp_save_name" > "$_alp_save_tmp"; then
        rm -f -- "$_alp_save_tmp";
        return 1;
    fi;
    _alp_save_hash=$("${3:-a.s}" < "$_alp_save_tmp") || { 
        rm -f -- "$_alp_save_tmp";
        return 1
    };
    [[ "$_alp_save_hash" =~ ^[0-9]+(\.[0-9]+)?$ ]] || { 
        printf 'a.save: invalid checksum\n' 1>&2;
        rm -f -- "$_alp_save_tmp";
        return 1
    };
    _alp_save_file="$_alp_save_name-$_alp_save_hash";
    if [[ -e "$_alp_save_dir/$_alp_save_file" ]]; then
        if ! cmp -s -- "$_alp_save_tmp" "$_alp_save_dir/$_alp_save_file"; then
            printf 'a.save: checksum collision: %s\n' "$_alp_save_file" 1>&2;
            rm -f -- "$_alp_save_tmp";
            return 1;
        fi;
        rm -f -- "$_alp_save_tmp";
    else
        mv -- "$_alp_save_tmp" "$_alp_save_dir/$_alp_save_file" || { 
            rm -f -- "$_alp_save_tmp";
            return 1
        };
    fi;
    if [[ "${2:-.}" == . ]]; then
        printf '%s\n' "$_alp_save_file";
    else
        printf '%s\n' "$_alp_save_dir/$_alp_save_file";
    fi
}
a.sbdir () 
{ 
    __T='a.sbdir';
    : : Create an initial sbshell structure;
    mkdir $1;
    cd $1;
    ln -s ../index.php;
    ln -s ../style.css;
    cd ..;
    chmod g-w $1
}
a.sectail () 
{ 
    : a.sectail;
    tail -f /var/log/apache2/modsec_audit.log
}
a.shoctal () 
{ 
    local _alp_octal_line;
    while IFS= read -r _alp_octal_line || [[ -n "$_alp_octal_line" ]]; do
        [[ "$_alp_octal_line" =~ ^[0-9]+$ ]] || return 2;
        printf '%o\n' "$((10#$_alp_octal_line))" | tr '01234567' '23456789';
    done
}
a.ss () 
{ 
    : : Preserve the original short SHA-1 shifted-octal format;
    local _alp_sha _alp_digest;
    _alp_sha=$(shasum) || return;
    _alp_digest=${_alp_sha:0:4};
    printf '02';
    printf '%o\n' "$((16#$_alp_digest))" | tr '01234567' '23456789'
}
a.tme () 
{ 
    date "+%H%M"
}
a.v () 
{ 
    : : 'Edit a live definition; only reload after Bash syntax validation';
    local _alp_edit_name _alp_edit_tmp _alp_edit_editor=${VISUAL:-${EDITOR:-vi}};
    _alp_edit_name=$(a.name "${1:-}") || return;
    _alp_edit_tmp=$(mktemp "${TMPDIR:-/tmp}/alp-edit.XXXXXX") || return;
    declare -f -- "$_alp_edit_name" > "$_alp_edit_tmp" || { 
        rm -f -- "$_alp_edit_tmp";
        return 1
    };
    if ! "$_alp_edit_editor" "$_alp_edit_tmp"; then
        rm -f -- "$_alp_edit_tmp";
        return 1;
    fi;
    if ! bash -n -- "$_alp_edit_tmp"; then
        printf 'a.v: definition unchanged; edited text is in %s\n' "$_alp_edit_tmp" 1>&2;
        return 1;
    fi;
    if . "$_alp_edit_tmp"; then
        rm -f -- "$_alp_edit_tmp";
        printf '%s\n' "$_alp_edit_name";
    else
        printf 'a.v: source failed; edited text is in %s\n' "$_alp_edit_tmp" 1>&2;
        return 1;
    fi
}
a.v_ () 
{ 
    t=$(- $1 | sed 's/-.*$//');
    mv $(a.fs $t) $$.bash;
    for x in vim source rm;
    do
        $x $$.bash;
    done;
    - $t
}
a.web () 
{ 
    : : Copy the static source viewer into an indexed directory;
    local _alp_web_dir _alp_web_template;
    _alp_web_dir=$(cd -- "${1:-.}" && pwd -P) || return;
    _alp_web_template="${_ALP_:-}/web/alp-view.html";
    [[ -f "$_alp_web_template" ]] || { 
        printf 'a.web: source alp.bash first\n' 1>&2;
        return 1
    };
    [[ -f "$_alp_web_dir/.files.txt" ]] || a.index "$_alp_web_dir" "${2:-functions}" > /dev/null || return;
    if [[ "$_alp_web_dir/alp-view.html" != "$_alp_web_template" ]]; then
        cp -- "$_alp_web_template" "$_alp_web_dir/alp-view.html" || return;
    fi;
    [[ -e "$_alp_web_dir/.nojekyll" ]] || : > "$_alp_web_dir/.nojekyll" || return;
    printf '%s\n' "$_alp_web_dir/alp-view.html"
}
alp () 
{ 
    : copyright 2020 DCxSECRETxBEACHxSoLUTioNSzzzY84D1u;
    : dogecoin:3f00bfca5133b8e68bab5146628157d3ca21de92221a712627bc1e02e5c74500;
    : license QmNprJ78ovcUuGMoMFiihK7GBpCmH578JU8hm43uxYQtBw;
    function :: () 
    { 
        :
    };
    : Welcome to ALP
}
alp2 () 
{ 
    : : Load manifest source entries into the calling shell;
    local _alp_load_dir _alp_load_manifest _alp_load_line _alp_load_action;
    local _alp_load_name _alp_load_path _alp_load_status=0;
    _alp_load_dir=$(cd -- "${1:-${_ALP2_:-${HOME}/alp2}}" && pwd -P) || return;
    _alp_load_manifest="$_alp_load_dir/.files.txt";
    if [[ ! -f "$_alp_load_manifest" ]]; then
        a.index "$_alp_load_dir" "${2:-functions}" > /dev/null || return;
    else
        if [[ $# -gt 1 ]]; then
            printf 'alp2: .files.txt already exists; use a.index to change its mode\n' 1>&2;
            return 2;
        fi;
    fi;
    _ALP2_=$_alp_load_dir;
    while IFS= read -r _alp_load_line || [[ -n "$_alp_load_line" ]]; do
        _alp_load_line=${_alp_load_line%''};
        [[ "$_alp_load_line" =~ ^[[:space:]]*$ || "$_alp_load_line" =~ ^[[:space:]]*# ]] && continue;
        _alp_load_action=source;
        _alp_load_name=$_alp_load_line;
        if [[ "$_alp_load_line" == *'	'* ]]; then
            _alp_load_action=${_alp_load_line%%'	'*};
            _alp_load_name=${_alp_load_line#*'	'};
        fi;
        case "$_alp_load_action" in 
            view | script | directory)
                continue
            ;;
            source)

            ;;
            *)
                printf 'alp2: unknown action: %s\n' "$_alp_load_action" 1>&2;
                _alp_load_status=1;
                continue
            ;;
        esac;
        case "$_alp_load_name" in 
            '' | /* | .. | ../* | */../* | */..)
                printf 'alp2: invalid relative path: %s\n' "$_alp_load_name" 1>&2;
                _alp_load_status=1;
                continue
            ;;
        esac;
        _alp_load_path="$_alp_load_dir/$_alp_load_name";
        if [[ ! -f "$_alp_load_path" ]]; then
            printf 'alp2: missing %s\n' "$_alp_load_path" 1>&2;
            _alp_load_status=1;
        else
            if ! bash -n -- "$_alp_load_path"; then
                printf 'alp2: invalid Bash: %s\n' "$_alp_load_path" 1>&2;
                _alp_load_status=1;
            else
                if . "$_alp_load_path"; then
                    :;
                else
                    printf 'alp2: source failed: %s\n' "$_alp_load_path" 1>&2;
                    _alp_load_status=1;
                fi;
            fi;
        fi;
    done < "$_alp_load_manifest";
    return "$_alp_load_status"
}
asdf () 
{ 
    - 'jkl';
    python3 /home/john/sbshell/mogwai/server.py .
}
d () 
{ 
    un DCx "$*"
}
d.F () 
{ 
    : inherited from a.F in alp;
    : this needs to do full search of "d.";
    : section;
    : use dash as executor;
    declare -F -- $1;
    function d.F- () 
    { 
        declare -F | grep $1
    }
}
d._zed () 
{ 
    : the shoctal for an empty file;
    - 02377293
}
d.c () 
{ 
    local color=${1:-reset} code pattern='^[0-9]+(;[0-9]+)*m?$';
    case "$color" in 
        list | help)
            printf '%-10s %-6s  %-15s %s\n' 'Color' 'Sample' 'Bright color' 'Sample';
            for color in black red green yellow blue purple aqua white;
            do
                printf '%-10s %sABC\033[0m     %-15s %sABC\033[0m\n' "$color" "$(d.c "$color")" "bright-$color" "$(d.c "bright-$color")";
            done;
            printf '\nAliases: magenta=purple, cyan=aqua, gray/grey=bright-black.\n';
            printf 'Bright magenta/cyan aliases are also supported.\n';
            printf 'Styles: %sbold\033[0m, %sunderline\033[0m.\n' "$(d.c bold)" "$(d.c underline)";
            printf 'unset/reset/off/normal (or no argument): reset all formatting.\n';
            printf 'default: restore the default foreground color only.\n';
            return
        ;;
        black)
            code=30
        ;;
        red | error)
            code=31
        ;;
        green)
            code=32
        ;;
        yellow)
            code=33
        ;;
        blue)
            code=34
        ;;
        purple | magenta)
            code=35
        ;;
        aqua | cyan)
            code=36
        ;;
        white)
            code=37
        ;;
        gray | grey | bright-black)
            code=90
        ;;
        bright-red)
            code=91
        ;;
        bright-green)
            code=92
        ;;
        bright-yellow)
            code=93
        ;;
        bright-blue)
            code=94
        ;;
        bright-purple | bright-magenta)
            code=95
        ;;
        bright-aqua | bright-cyan)
            code=96
        ;;
        bright-white)
            code=97
        ;;
        bold)
            code=1
        ;;
        underline)
            code=4
        ;;
        unset | reset | off | normal)
            code=0
        ;;
        default)
            code=39
        ;;
        *)
            if [[ ! $color =~ $pattern ]]; then
                printf 'd.c: unknown color: %s; use d.c list\n' "$color" 1>&2;
                return 2;
            fi;
            code=${color%m}
        ;;
    esac;
    printf '\033[%sm' "$code"
}
d.c.cros () 
{ 
    local MODE FG;
    case "$1" in 
        -p | prompt)
            MODE=prompt;
            shift
        ;;
    esac;
    case "${1:-reset}" in 
        black)
            FG='30m'
        ;;
        bold)
            FG='1m'
        ;;
        underline)
            FG='4m'
        ;;
        error | red)
            FG='31m'
        ;;
        green)
            FG='32m'
        ;;
        yellow)
            FG='33m'
        ;;
        blue)
            FG='34m'
        ;;
        purple)
            FG='35m'
        ;;
        aqua | cyan)
            FG='36m'
        ;;
        reset | off)
            FG='0m'
        ;;
        *)
            FG="${1:-0m}"
        ;;
    esac;
    if [ "$MODE" = prompt ]; then
        if [ -z "${DAISY_PS1_ORIG+x}" ]; then
            DAISY_PS1_ORIG=$PS1;
        fi;
        if [ "$FG" = '0m' ]; then
            PS1=$DAISY_PS1_ORIG;
            printf '\033[0m';
            return;
        fi;
        PS1="${DAISY_PS1_ORIG}"'\[\033['"$FG"'\]';
        return;
    fi;
    printf '\033[%s' "$FG"
}
d.c.set () 
{ 
    _DC_DIR="/home/john/daisy/2026/v269m_corpus_full"
}
d.corpus () 
{ 
    : add corpus to daisy, which is;
    : how I organize things in the;
    : shell
}
d.date () 
{ 
    :;
    if [[ -z $1 ]]; then
        date;
    else
        date "+%"$1;
    fi;
    : date "+%u";
    :;
    function d.date_ () 
    { 
        : specific code;
        date "+%Y/%W%u/"
    }
}
d.dir () 
{ 
    cd $DAISY_LOC
}
d.env () 
{ 
    - "DAISY_DIR"=$DAISY_DIR
}
d.f () 
{ 
    if [ -z "$1" ]; then
        printf '%s\n' "usage: d.f function.name" 1>&2;
        return 1;
    fi;
    declare -f -- $(echo -n "$1" | sed 's/-.*//')
}
d.fs () 
{ 
    : : Save a live function using the existing Daisy checksum format;
    local _d_save_name=${1:-} _d_save_dir _d_save_tmp _d_save_hash _d_save_file;
    [[ -n "$_d_save_name" ]] || { 
        printf 'usage: d.fs function.name [directory]\n' 1>&2;
        return 2
    };
    if ! declare -F -- "$_d_save_name" > /dev/null; then
        _d_save_name=${_d_save_name##*/};
        if [[ "$_d_save_name" =~ ^(.+)-[0-9]+(\.[0-9]+)?$ ]]; then
            _d_save_name=${BASH_REMATCH[1]};
        fi;
    fi;
    declare -F -- "$_d_save_name" > /dev/null || { 
        printf 'd.fs: no function: %s\n' "$_d_save_name" 1>&2;
        return 1
    };
    [[ "$_d_save_name" != *[!A-Za-z0-9_.-]* ]] || { 
        printf 'd.fs: unsupported filename\n' 1>&2;
        return 2
    };
    _d_save_dir=$(cd -- "${2:-.}" && pwd -P) || return;
    declare -F d.s > /dev/null || { 
        printf 'd.fs: load d.s first\n' 1>&2;
        return 1
    };
    _d_save_tmp=$(mktemp "$_d_save_dir/.daisy-save.XXXXXX") || return;
    declare -f -- "$_d_save_name" > "$_d_save_tmp" || { 
        rm -f -- "$_d_save_tmp";
        return 1
    };
    _d_save_hash=$(d.s < "$_d_save_tmp") || { 
        rm -f -- "$_d_save_tmp";
        return 1
    };
    [[ "$_d_save_hash" =~ ^[0-9]+$ ]] || { 
        printf 'd.save: invalid checksum\n' 1>&2;
        rm -f -- "$_d_save_tmp";
        return 1
    };
    _d_save_file="$_d_save_name-$_d_save_hash";
    if [[ -e "$_d_save_dir/$_d_save_file" ]]; then
        if ! cmp -s -- "$_d_save_tmp" "$_d_save_dir/$_d_save_file"; then
            printf 'd.fs: checksum collision: %s\n' "$_d_save_file" 1>&2;
            rm -f -- "$_d_save_tmp";
            return 1;
        fi;
        rm -f -- "$_d_save_tmp";
    else
        mv -- "$_d_save_tmp" "$_d_save_dir/$_d_save_file" || { 
            rm -f -- "$_d_save_tmp";
            return 1
        };
    fi;
    if [[ "${2:-.}" == . ]]; then
        printf '%s\n' "$_d_save_file";
    else
        printf '%s\n' "$_d_save_dir/$_d_save_file";
    fi
}
d.fs.inert () 
{ 
    local SRC="$1";
    local NAME="${2:-daisy.inert.packet}";
    [ -f "$SRC" ] || { 
        printf '%s\n' "d.fs.inert: file not found: $SRC" 1>&2;
        return 1
    };
    printf '%s () \n' "$NAME";
    printf '{ \n';
    printf '    --- inert.source;\n';
    printf '    - "file: %s";\n' "$SRC";
    printf '    - "mode: inert import";\n';
    printf '    - "execute: no";\n';
    printf '    :;\n';
    LC_ALL=C tr -d '\000' < "$SRC" | sed -E 's/\x1b\[[0-?]*[ -\/]*[@-~]//g; s/\x1b\][^\x07]*(\x07|\x1b\\)//g' | while IFS= read -r line; do
        case "$line" in 
            "")
                printf '    :;\n'
            ;;
            *)
                line=${line//\\/\\\\};
                line=${line//\"/\\\"};
                printf '    - "%s";\n' "$line"
            ;;
        esac;
    done;
    printf '} \n'
}
d.fs.inert2 () 
{ 
    local SRC="$1";
    local NAME="${2:-daisy.inert.packet}";
    local LINE;
    [ -f "$SRC" ] || { 
        printf '%s\n' "d.fs.inert2: file not found: $SRC" 1>&2;
        return 1
    };
    printf '%s () \n' "$NAME";
    printf '{ \n';
    printf '    --- inert.source;\n';
    printf '    - "file: %s";\n' "$SRC";
    printf '    - "mode: inert import";\n';
    printf '    - "execute: no";\n';
    printf '    :;\n';
    d.strip.ansi < "$SRC" | while IFS= read -r LINE; do
        LINE=${LINE//\\/\\\\};
        LINE=${LINE//\"/\\\"};
        case "$LINE" in 
            "")
                printf '    :;\n'
            ;;
            *)
                printf '    - "%s";\n' "$LINE"
            ;;
        esac;
    done;
    printf '} \n'
}
d.grok () 
{ 
    cat chatgpt.response__Daisy_26a | grep '()' | grep -v printf
}
d.h () 
{ 
    : d.h;
    : : herstory;
    : : transforms the previous shell command into a function;
    : : usage: d.h d.name;
    local name;
    local raw;
    local body;
    local def;
    name="$1";
    if [ -z "$name" ]; then
        printf '%s\n' "usage: d.h function.name" 1>&2;
        return 1;
    fi;
    case "$name" in 
        [0-9]* | *[!A-Za-z0-9_.]*)
            printf '%s\n' "d.h: bad function name: $name" 1>&2;
            printf '%s\n' "d.h: allowed: letters numbers underscore dot" 1>&2;
            return 1
        ;;
    esac;
    raw=$(HISTTIMEFORMAT= history 2 | head -1);
    body=$(printf '%s\n' "$raw" | sed 's/^[[:space:]]*[0-9][0-9]*[[:space:]]*//');
    if [ -z "$body" ]; then
        printf '%s\n' "d.h: could not read previous command" 1>&2;
        return 1;
    fi;
    case "$body" in 
        d.h | d.h\ * | "$name")
            printf '%s\n' "d.h: previous command looks recursive" 1>&2;
            return 1
        ;;
    esac;
    def=$(printf '%s\n' "$name ()" "{" "    $body;" "}");
    printf '%s\n' "$def";
    eval "$def"
}
d.list () 
{ 
    declare -F | grep -v " _" | grep "d."
}
d.ls () 
{ 
    ls -lt ../../../daisy/d.f-02*
}
d.mv () 
{ 
    : e='-';
    : change in shell;
    while read o; do
        t=$(- $o | sed "s/ /-/g");
        t=$(- $t | sed "s/,//g");
        $e $o $t;
    done
}
d.now () 
{ 
    cd $D_NOW;
    function d.now_ () 
    { 
        - $D_NOW
    }
}
d.only () 
{ 
    d.f $1 > $$;
    cat $$;
    echo "d.f-*";
    mv $$ "XXXX-"$(cat $$ | d.s)
}
d.pull () 
{ 
    if (( $# > 1 )); then
        printf '%s\n' 'Usage: d.pull [CONFIG_JSON]' 1>&2;
        return 2;
    fi;
    python3 - "$@" <<'PY'
import json
import shutil
import subprocess
import sys
from pathlib import Path

try:
    config_path = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else Path.home() / "config.json"
    projects = json.loads(config_path.read_text(encoding="utf-8"))["projects"]
    if not isinstance(projects, dict):
        raise ValueError("projects must be an object")
    plan = []
    for key, project in projects.items():
        if not isinstance(project, dict) or not isinstance(project.get("path"), str) or not project["path"].strip():
            raise ValueError(f"projects.{key}.path must be a nonempty string")
        path = Path(project["path"]).expanduser()
        plan.append((key, (path if path.is_absolute() else Path.home() / path).resolve()))
    if not shutil.which("git"):
        raise ValueError("git is not installed")
except (OSError, UnicodeError, ValueError, KeyError, TypeError, RuntimeError) as error:
    print(f"d.pull: {error}", file=sys.stderr)
    sys.exit(2)

counts = dict(updated=0, unchanged=0, skipped=0, failed=0)
seen = set()
for key, path in plan:
    print(f"\n[{key}] {path}", flush=True)
    if path in seen:
        print("SAME checkout already handled")
        continue
    seen.add(path)
    if not path.is_dir():
        print("SKIP: directory does not exist")
        counts["skipped"] += 1
        continue

    def git(*args):
        return subprocess.run(["git", *args], cwd=path, capture_output=True, text=True)

    try:
        root = git("rev-parse", "--show-toplevel")
        if root.returncode or Path(root.stdout.strip()).resolve() != path:
            print("SKIP: path is not the root of a Git checkout")
            counts["skipped"] += 1
            continue
        branch = git("symbolic-ref", "--quiet", "--short", "HEAD")
        if branch.returncode:
            print("SKIP: detached HEAD")
            counts["skipped"] += 1
            continue
        active = False
        for marker in ("MERGE_HEAD", "CHERRY_PICK_HEAD", "REVERT_HEAD", "rebase-merge", "rebase-apply", "sequencer"):
            marker_path = git("rev-parse", "--git-path", marker)
            if marker_path.returncode:
                raise RuntimeError(marker_path.stderr.strip())
            if (path / marker_path.stdout.strip()).exists():
                active = True
                break
        if active:
            print("SKIP: a merge, rebase or cherry-pick is in progress")
            counts["skipped"] += 1
            continue
        status = git("status", "--porcelain", "--untracked-files=all")
        if status.returncode:
            raise RuntimeError(status.stderr.strip())
        if status.stdout:
            print("SKIP: local changes or untracked files")
            counts["skipped"] += 1
            continue
        upstream = git("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}")
        if upstream.returncode:
            print("SKIP: current branch has no upstream")
            counts["skipped"] += 1
            continue
        before = git("rev-parse", "HEAD").stdout.strip()
        print(f"{branch.stdout.strip()} <- {upstream.stdout.strip()}", flush=True)
        # Fetch follows this branch's configured remote. Fast-forward only;
        # also refuse to overwrite ignored local data with incoming files.
        fetched = subprocess.run(["git", "fetch"], cwd=path)
        if fetched.returncode:
            counts["failed"] += 1
            print("FAIL: fetch failed", flush=True)
            continue
        merged = subprocess.run([
            "git", "merge", "--ff-only", "--no-autostash",
            "--no-overwrite-ignore", "@{upstream}"
        ], cwd=path)
        if merged.returncode:
            counts["failed"] += 1
            print("FAIL: fast-forward refused; local work retained", flush=True)
            continue
        after = git("rev-parse", "HEAD").stdout.strip()
        result = "updated" if before != after else "unchanged"
        counts[result] += 1
        print(result.upper(), flush=True)
    except (OSError, RuntimeError) as error:
        counts["failed"] += 1
        print(f"FAIL: {error}", flush=True)

print("\nd.pull: " + ", ".join(f"{value} {key}" for key, value in counts.items()))
sys.exit(1 if counts["skipped"] or counts["failed"] else 0)
PY

}
d.rigler.ltc () 
{ 
    ID="LcudkPQzLuuqsnzHSmJ7iLREaHStvPKRVb";
    RSA="~/.ssh/"$ID"_rsa";
    LOGIN=$ID"@rigler.org";
    ssh -i $RSA $LOGIN "$*"
}
d.rigler.ltc.t () 
{ 
    ID="LcudkPQzLuuqsnzHSmJ7iLREaHStvPKRVb";
    RSA="~/.ssh/"$ID"_rsa";
    LOGIN=$ID"@rigler.org";
    ssh -T -i $RSA $LOGIN "$*"
}
d.s () 
{ 
    : : Creates a shasum extension;
    t=$(shasum | cut -c 1-4);
    sum=$(printf "%o" "$((16#$t))");
    printf '%s\n' "$sum" | tr '01234567' '23456789' | while read -r a; do
        printf '02%-6s\n' "$a" | tr ' ' '0';
    done
}
d.script () 
{ 
    ( script_size=$(stty size) || exit;
    trap 'stty cols "${script_size##* }"' EXIT;
    stty cols 80 || exit;
    COLUMNS=80 script -q -f "$(date +%G%m%d-W%V-%u-%H%M%S).unixTs" )
}
d.strip.ansi () 
{ 
    LC_ALL=C tr -d '\000' | perl -pe 's/\e\[[0-?]*[ -\/]*[@-~]//g; s/\e\][^\a]*(?:\a|\e\\)//g'
}
d.tar () 
{ 
    cd ~/daisy;
    tar -cvf "chisel-"$1 scripts/2026/$(a.date.w) 2026/chisel-$2.tar
}
d.v () 
{ 
    function d.v. () 
    { 
        : this is my main repl;
        : editor;
        : because vim gets loaded;
        : into memory, it is;
        : really fast;
        : i suggest that you;
        : become a proficient;
        : typist and use vim
    };
    t=$(- $1 | sed 's/-.*$//');
    cp $(d.fs $t) $$.bash;
    for x in vim source rm;
    do
        $x $$.bash;
    done;
    - $t
}
d.v_ () 
{ 
    : home - i have no home;
    declare -F | grep "home" | while read z z t; do
        - $t;
    done
}
d.yt () 
{ 
    function yt.playlists () 
    { 
        yt-dlp --flat-playlist --dump-single-json 'https://www.youtube.com/@johnrigler7271/playlists' | jq -r '.entries[] | [.id, .title] | @tsv'
    };
    function yt.list () 
    { 
        playlist_id=$1;
        yt-dlp --flat-playlist --dump-single-json "https://www.youtube.com/playlist?list=$playlist_id" | jq -r '.entries[] | [.id, .title] | @tsv'
    }
}
d.yt.splinters () 
{ 
    : https://youtu.be/AxYQCWyBVk0?si=gJ7_qn5c3dMFb1N9;
    : QmbFMke1KXqnYyBBWxB74N4c5SBnJMVAiMNRcGu6x1AwQH;
    TITLE="I Walk on guilded splinters";
    function d.yt.splinters () 
    { 
        : https://youtu.be/AxYQCWyBVk0?si=gJ7_qn5c3dMFb1N9;
        : QmbFMke1KXqnYyBBWxB74N4c5SBnJMVAiMNRcGu6x1AwQH;
        TITLE="I Walk on guilded splinters"
    }
}
daisy () 
{ 
    : Historical DAISY collection;
    : Definitions from daisy.lib and dated snapshots;
    function - () 
    { 
        echo "$*"
    };
    function d.c.set () 
    { 
        _DC_DIR="/home/john/daisy/2026/v269m_corpus_full"
    };
    function d.dir () 
    { 
        cd $DAISY_LOC
    };
    function d.env () 
    { 
        - "DAISY_DIR"=$DAISY_DIR
    };
    function d.f () 
    { 
        if [ -z "$1" ]; then
            printf '%s\n' "usage: d.f function.name" 1>&2;
            return 1;
        fi;
        declare -f -- $(echo -n "$1" | sed 's/-.*//')
    };
    function d.fs () 
    { 
        : : Save a live function using the existing Daisy checksum format;
        local _d_save_name=${1:-} _d_save_dir _d_save_tmp _d_save_hash _d_save_file;
        [[ -n "$_d_save_name" ]] || { 
            printf 'usage: d.fs function.name [directory]\n' 1>&2;
            return 2
        };
        if ! declare -F -- "$_d_save_name" > /dev/null; then
            _d_save_name=${_d_save_name##*/};
            if [[ "$_d_save_name" =~ ^(.+)-[0-9]+(\.[0-9]+)?$ ]]; then
                _d_save_name=${BASH_REMATCH[1]};
            fi;
        fi;
        declare -F -- "$_d_save_name" > /dev/null || { 
            printf 'd.fs: no function: %s\n' "$_d_save_name" 1>&2;
            return 1
        };
        [[ "$_d_save_name" != *[!A-Za-z0-9_.-]* ]] || { 
            printf 'd.fs: unsupported filename\n' 1>&2;
            return 2
        };
        _d_save_dir=$(cd -- "${2:-.}" && pwd -P) || return;
        declare -F d.s > /dev/null || { 
            printf 'd.fs: load d.s first\n' 1>&2;
            return 1
        };
        _d_save_tmp=$(mktemp "$_d_save_dir/.daisy-save.XXXXXX") || return;
        declare -f -- "$_d_save_name" > "$_d_save_tmp" || { 
            rm -f -- "$_d_save_tmp";
            return 1
        };
        _d_save_hash=$(d.s < "$_d_save_tmp") || { 
            rm -f -- "$_d_save_tmp";
            return 1
        };
        [[ "$_d_save_hash" =~ ^[0-9]+$ ]] || { 
            printf 'd.save: invalid checksum\n' 1>&2;
            rm -f -- "$_d_save_tmp";
            return 1
        };
        _d_save_file="$_d_save_name-$_d_save_hash";
        if [[ -e "$_d_save_dir/$_d_save_file" ]]; then
            if ! cmp -s -- "$_d_save_tmp" "$_d_save_dir/$_d_save_file"; then
                printf 'd.fs: checksum collision: %s\n' "$_d_save_file" 1>&2;
                rm -f -- "$_d_save_tmp";
                return 1;
            fi;
            rm -f -- "$_d_save_tmp";
        else
            mv -- "$_d_save_tmp" "$_d_save_dir/$_d_save_file" || { 
                rm -f -- "$_d_save_tmp";
                return 1
            };
        fi;
        if [[ "${2:-.}" == . ]]; then
            printf '%s\n' "$_d_save_file";
        else
            printf '%s\n' "$_d_save_dir/$_d_save_file";
        fi
    };
    function _d.fs () 
    { 
        d.fs "$@"
    };
    function d.h () 
    { 
        : d.h;
        : : herstory;
        : : transforms the previous shell command into a function;
        : : usage: d.h d.name;
        local name;
        local raw;
        local body;
        local def;
        name="$1";
        if [ -z "$name" ]; then
            printf '%s\n' "usage: d.h function.name" 1>&2;
            return 1;
        fi;
        case "$name" in 
            [0-9]* | *[!A-Za-z0-9_.]*)
                printf '%s\n' "d.h: bad function name: $name" 1>&2;
                printf '%s\n' "d.h: allowed: letters numbers underscore dot" 1>&2;
                return 1
            ;;
        esac;
        raw=$(HISTTIMEFORMAT= history 2 | head -1);
        body=$(printf '%s\n' "$raw" | sed 's/^[[:space:]]*[0-9][0-9]*[[:space:]]*//');
        if [ -z "$body" ]; then
            printf '%s\n' "d.h: could not read previous command" 1>&2;
            return 1;
        fi;
        case "$body" in 
            d.h | d.h\ * | "$name")
                printf '%s\n' "d.h: previous command looks recursive" 1>&2;
                return 1
            ;;
        esac;
        def=$(printf '%s\n' "$name ()" "{" "    $body;" "}");
        printf '%s\n' "$def";
        eval "$def"
    };
    function d.only () 
    { 
        d.f $1 > $$;
        cat $$;
        echo "d.f-*";
        mv $$ "XXXX-"$(cat $$ | d.s)
    };
    function d.rigler.ltc () 
    { 
        ID="LcudkPQzLuuqsnzHSmJ7iLREaHStvPKRVb";
        RSA="~/.ssh/"$ID"_rsa";
        LOGIN=$ID"@rigler.org";
        ssh -i $RSA $LOGIN "$*"
    };
    function d.rigler.ltc.t () 
    { 
        ID="LcudkPQzLuuqsnzHSmJ7iLREaHStvPKRVb";
        RSA="~/.ssh/"$ID"_rsa";
        LOGIN=$ID"@rigler.org";
        ssh -T -i $RSA $LOGIN "$*"
    };
    function d.s () 
    { 
        : : Creates a shasum extension;
        t=$(shasum | cut -c 1-4);
        sum=$(printf "%o" "$((16#$t))");
        printf '%s\n' "$sum" | tr '01234567' '23456789' | while read -r a; do
            printf '02%-6s\n' "$a" | tr ' ' '0';
        done
    };
    function d.v () 
    { 
        function d.v. () 
        { 
            : this is my main repl;
            : editor;
            : because vim gets loaded;
            : into memory, it is;
            : really fast;
            : i suggest that you;
            : become a proficient;
            : typist and use vim
        };
        t=$(- $1 | sed 's/-.*$//');
        cp $(d.fs $t) $$.bash;
        for x in vim source rm;
        do
            $x $$.bash;
        done;
        - $t
    };
    : Additional historical DAISY functions;
    function d.ls () 
    { 
        ls -lt ../../../daisy/d.f-02*
    };
    function d.F () 
    { 
        : inherited from a.F in alp;
        : this needs to do full search of "d.";
        : section;
        : use dash as executor;
        declare -F -- $1;
        function d.F- () 
        { 
            declare -F | grep $1
        }
    };
    function d.c () 
    { 
        local FG;
        case "${1:-reset}" in 
            black)
                FG='30m'
            ;;
            bold)
                FG='1m'
            ;;
            underline)
                FG='4m'
            ;;
            error | red)
                FG='31m'
            ;;
            green)
                FG='32m'
            ;;
            yellow)
                FG='33m'
            ;;
            blue)
                FG='34m'
            ;;
            purple)
                FG='35m'
            ;;
            aqua)
                FG='36m'
            ;;
            reset | off)
                FG='0m'
            ;;
            *)
                FG="$1"
            ;;
        esac;
        printf '\033[%s' "$FG"
    };
    function d.c.cros () 
    { 
        local MODE FG;
        case "$1" in 
            -p | prompt)
                MODE=prompt;
                shift
            ;;
        esac;
        case "${1:-reset}" in 
            black)
                FG='30m'
            ;;
            bold)
                FG='1m'
            ;;
            underline)
                FG='4m'
            ;;
            error | red)
                FG='31m'
            ;;
            green)
                FG='32m'
            ;;
            yellow)
                FG='33m'
            ;;
            blue)
                FG='34m'
            ;;
            purple)
                FG='35m'
            ;;
            aqua | cyan)
                FG='36m'
            ;;
            reset | off)
                FG='0m'
            ;;
            *)
                FG="${1:-0m}"
            ;;
        esac;
        if [ "$MODE" = prompt ]; then
            if [ -z "${DAISY_PS1_ORIG+x}" ]; then
                DAISY_PS1_ORIG=$PS1;
            fi;
            if [ "$FG" = '0m' ]; then
                PS1=$DAISY_PS1_ORIG;
                printf '\033[0m';
                return;
            fi;
            PS1="${DAISY_PS1_ORIG}"'\[\033['"$FG"'\]';
            return;
        fi;
        printf '\033[%s' "$FG"
    };
    function d.fs.inert () 
    { 
        local SRC="$1";
        local NAME="${2:-daisy.inert.packet}";
        [ -f "$SRC" ] || { 
            printf '%s\n' "d.fs.inert: file not found: $SRC" 1>&2;
            return 1
        };
        printf '%s () \n' "$NAME";
        printf '{ \n';
        printf '    --- inert.source;\n';
        printf '    - "file: %s";\n' "$SRC";
        printf '    - "mode: inert import";\n';
        printf '    - "execute: no";\n';
        printf '    :;\n';
        LC_ALL=C tr -d '\000' < "$SRC" | sed -E 's/\x1b\[[0-?]*[ -\/]*[@-~]//g; s/\x1b\][^\x07]*(\x07|\x1b\\)//g' | while IFS= read -r line; do
            case "$line" in 
                "")
                    printf '    :;\n'
                ;;
                *)
                    line=${line//\\/\\\\};
                    line=${line//\"/\\\"};
                    printf '    - "%s";\n' "$line"
                ;;
            esac;
        done;
        printf '} \n'
    };
    function d.fs.inert2 () 
    { 
        local SRC="$1";
        local NAME="${2:-daisy.inert.packet}";
        local LINE;
        [ -f "$SRC" ] || { 
            printf '%s\n' "d.fs.inert2: file not found: $SRC" 1>&2;
            return 1
        };
        printf '%s () \n' "$NAME";
        printf '{ \n';
        printf '    --- inert.source;\n';
        printf '    - "file: %s";\n' "$SRC";
        printf '    - "mode: inert import";\n';
        printf '    - "execute: no";\n';
        printf '    :;\n';
        d.strip.ansi < "$SRC" | while IFS= read -r LINE; do
            LINE=${LINE//\\/\\\\};
            LINE=${LINE//\"/\\\"};
            case "$LINE" in 
                "")
                    printf '    :;\n'
                ;;
                *)
                    printf '    - "%s";\n' "$LINE"
                ;;
            esac;
        done;
        printf '} \n'
    };
    function d.grok () 
    { 
        cat chatgpt.response__Daisy_26a | grep '()' | grep -v printf
    };
    function d.strip.ansi () 
    { 
        LC_ALL=C tr -d '\000' | perl -pe 's/\e\[[0-?]*[ -\/]*[@-~]//g; s/\e\][^\a]*(?:\a|\e\\)//g'
    };
    function d._zed () 
    { 
        : the shoctal for an empty file;
        - 02377293
    };
    function d.now () 
    { 
        cd $D_NOW;
        function d.now_ () 
        { 
            - $D_NOW
        }
    };
    function d.tar () 
    { 
        cd ~/daisy;
        tar -cvf "chisel-"$1 scripts/2026/$(a.date.w) 2026/chisel-$2.tar
    };
    function d.mv () 
    { 
        : e='-';
        : change in shell;
        while read o; do
            t=$(- $o | sed "s/ /-/g");
            t=$(- $t | sed "s/,//g");
            $e $o $t;
        done
    };
    function d.yt () 
    { 
        function yt.playlists () 
        { 
            yt-dlp --flat-playlist --dump-single-json 'https://www.youtube.com/@johnrigler7271/playlists' | jq -r '.entries[] | [.id, .title] | @tsv'
        };
        function yt.list () 
        { 
            playlist_id=$1;
            yt-dlp --flat-playlist --dump-single-json "https://www.youtube.com/playlist?list=$playlist_id" | jq -r '.entries[] | [.id, .title] | @tsv'
        }
    };
    function d.v_ () 
    { 
        : home - i have no home;
        declare -F | grep "home" | while read z z t; do
            - $t;
        done
    };
    function d.yt.splinters () 
    { 
        : https://youtu.be/AxYQCWyBVk0?si=gJ7_qn5c3dMFb1N9;
        : QmbFMke1KXqnYyBBWxB74N4c5SBnJMVAiMNRcGu6x1AwQH;
        TITLE="I Walk on guilded splinters";
        function d.yt.splinters () 
        { 
            : https://youtu.be/AxYQCWyBVk0?si=gJ7_qn5c3dMFb1N9;
            : QmbFMke1KXqnYyBBWxB74N4c5SBnJMVAiMNRcGu6x1AwQH;
            TITLE="I Walk on guilded splinters"
        }
    }
}
db.getblockcount () 
{ 
    echo "select max(height) from block;" | mysql dimecash | tail -1
}
dc () 
{ 
    if [[ -n $1 ]]; then
        currency=$1;
    else
        - $currency;
    fi
}
dc.digibyte.payment () 
{ 
    while true; do
        /usr/local/bin/digibyte-cli listreceivedbyaddress | jq .[0] | grep "^    \"" | cut -c 6-69 | while read A; do
            /usr/local/bin/digibyte-cli gettransaction $A;
        done | grep "^  \"amo" | cut -c 15-22 > /tmp/$$;
        cd /var/www/html/dgb/jobs;
        ls 0* 2> /dev/null | while read pending; do
            grep $pending /tmp/$$;
            if [[ $? -eq 0 ]]; then
                tx=$(. $pending);
                mv $pending $tx;
                echo $tx;
            fi;
        done;
        rm /tmp/$$;
        sleep 4;
    done
}
dc.listtransactions () 
{ 
    $(dc)-cli listtransactions > $_ALP_/$(dc).transactions
}
deliver_motd () 
{ 
    [[ -n "${SSH_TTY:-}" ]] && return 0;
    local COUNTER_INITIAL=10;
    local COUNTER_MAX=15;
    local user_data=${XDG_DATA_DIR:-"${HOME}/.local/share"};
    local motd_file="$user_data/cros-motd";
    mkdir -p "$user_data" 2> /dev/null || exit 1;
    local counter=-1;
    if [[ -f "$motd_file" ]]; then
        { 
            counter=$(< "$motd_file") 2> /dev/null && [[ "$counter" =~ ^[0-9]+$ ]]
        } 2> /dev/null || counter=-1;
    fi;
    if ((counter < COUNTER_INITIAL || counter > COUNTER_MAX)); then
        echo "$COUNTER_INITIAL" > ${motd_file};
        counter=$COUNTER_INITIAL;
    fi;
    if ((counter < COUNTER_MAX)); then
        counter=$((counter + 1));
        echo $counter > "$motd_file";
        print_message;
        if ((counter == COUNTER_MAX)); then
            echo "    (this message will not be repeated again)";
        else
            ((counter == (COUNTER_MAX-1))) && s='' || s='s';
            remaining=$((COUNTER_MAX-counter));
            echo "    (this message will be repeated $remaining more time$s).";
            echo "    (to silence this message, run the following in this terminal):";
            echo "        echo $COUNTER_MAX >\"$motd_file\"";
        fi;
    fi
}
dequote () 
{ 
    eval printf %s "$1" 2> /dev/null
}
fp () 
{ 
    local fileproxy_dir="${FILEPROXY_HOME:-$HOME/mogwai/fileProxy}";
    python3 "$fileproxy_dir/fp.py" "$@"
}
git.clone () 
{ 
    REPO="johnrigler";
    NAME=$1;
    git clone https://github.com/$REPO/$NAME
}
git.fix () 
{ 
    cd .git;
    cat config;
    -;
    - url = git@github.com:johnrigler/$1.git
}
ipfs.add () 
{ 
    ipfs add $1 2> /dev/null | xargs -n1 | grep "Qm"
}
ipfs.decode () 
{ 
    cat > $$;
    echo "-----------------------------";
    T=$(cat $$ | xargs -n1 | egrep 'DDx|DEx' | sort | cut -c 4-26 | xargs -n2 | sed 's/ //g');
    echo "$T";
    echo "https://ipfs.io/ipfs/$T"
}
ipfs.io () 
{ 
    echo https://ipfs.io/ipfs/$1
}
ipfs.make () 
{ 
    : arg1 currency;
    : arg2 CID;
    : arg3 name;
    : arg4 medium;
    IPFS=$(basename $2);
    FIRST=$(echo $IPFS | cut -c 1-23);
    LAST=$(echo $IPFS | cut -c 24-);
    echo "$1-cli sendmany \"\" \"{\\";
    echo \\\"$(un DAx ipfs)\\\"":0.00001132,\\";
    echo \\\"$(un DBx "$3")\\\"":0.00001132,\\";
    while read LINE; do
        echo \\\"$(un DCx "$LINE")\\\"":0.00001000,\\";
    done;
    echo \\\"$(un DDx$FIRST)\\\"":0.00001000,\\";
    echo \\\"$(un DEx$LAST)\\\"":0.00001132}\""
}
ipfs.redir () 
{ 
    echo "<head> <meta http-equiv='Refresh' content='0; url=$1' /> </head>" | ipfs add 2> /dev/null | xargs -n1 | grep "^Qm" | head -1
}
m.pull () 
{ 
    if (( $# > 1 )); then
        printf '%s\n' 'Usage: m.pull [CONFIG_JSON]' 1>&2;
        return 2;
    fi;
    python3 - "$@" <<'PY'
import json
import shutil
import subprocess
import sys
from pathlib import Path

try:
    config_path = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else Path.home() / "config.json"
    projects = json.loads(config_path.read_text(encoding="utf-8"))["projects"]
    if not isinstance(projects, dict):
        raise ValueError("projects must be an object")
    plan = []
    for key, project in projects.items():
        if not isinstance(project, dict) or not isinstance(project.get("path"), str) or not project["path"].strip():
            raise ValueError(f"projects.{key}.path must be a nonempty string")
        path = Path(project["path"]).expanduser()
        plan.append((key, (path if path.is_absolute() else Path.home() / path).resolve()))
    if not shutil.which("git"):
        raise ValueError("git is not installed")
except (OSError, UnicodeError, ValueError, KeyError, TypeError, RuntimeError) as error:
    print(f"m.pull: {error}", file=sys.stderr)
    sys.exit(2)

counts = dict(updated=0, unchanged=0, skipped=0, failed=0)
seen = set()
for key, path in plan:
    print(f"\n[{key}] {path}", flush=True)
    if path in seen:
        print("SAME checkout already handled")
        continue
    seen.add(path)
    if not path.is_dir():
        print("SKIP: directory does not exist")
        counts["skipped"] += 1
        continue

    def git(*args):
        return subprocess.run(["git", *args], cwd=path, capture_output=True, text=True)

    try:
        root = git("rev-parse", "--show-toplevel")
        if root.returncode or Path(root.stdout.strip()).resolve() != path:
            print("SKIP: path is not the root of a Git checkout")
            counts["skipped"] += 1
            continue
        branch = git("symbolic-ref", "--quiet", "--short", "HEAD")
        if branch.returncode:
            print("SKIP: detached HEAD")
            counts["skipped"] += 1
            continue
        active = False
        for marker in ("MERGE_HEAD", "CHERRY_PICK_HEAD", "REVERT_HEAD", "rebase-merge", "rebase-apply", "sequencer"):
            marker_path = git("rev-parse", "--git-path", marker)
            if marker_path.returncode:
                raise RuntimeError(marker_path.stderr.strip())
            if (path / marker_path.stdout.strip()).exists():
                active = True
                break
        if active:
            print("SKIP: a merge, rebase or cherry-pick is in progress")
            counts["skipped"] += 1
            continue
        status = git("status", "--porcelain", "--untracked-files=all")
        if status.returncode:
            raise RuntimeError(status.stderr.strip())
        if status.stdout:
            print("SKIP: local changes or untracked files")
            counts["skipped"] += 1
            continue
        upstream = git("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}")
        if upstream.returncode:
            print("SKIP: current branch has no upstream")
            counts["skipped"] += 1
            continue
        before = git("rev-parse", "HEAD").stdout.strip()
        print(f"{branch.stdout.strip()} <- {upstream.stdout.strip()}", flush=True)
        # Fetch follows this branch's configured remote. Fast-forward only;
        # also refuse to overwrite ignored local data with incoming files.
        fetched = subprocess.run(["git", "fetch"], cwd=path)
        if fetched.returncode:
            counts["failed"] += 1
            print("FAIL: fetch failed", flush=True)
            continue
        merged = subprocess.run([
            "git", "merge", "--ff-only", "--no-autostash",
            "--no-overwrite-ignore", "@{upstream}"
        ], cwd=path)
        if merged.returncode:
            counts["failed"] += 1
            print("FAIL: fast-forward refused; local work retained", flush=True)
            continue
        after = git("rev-parse", "HEAD").stdout.strip()
        result = "updated" if before != after else "unchanged"
        counts[result] += 1
        print(result.upper(), flush=True)
    except (OSError, RuntimeError) as error:
        counts["failed"] += 1
        print(f"FAIL: {error}", flush=True)

print("\nm.pull: " + ", ".join(f"{value} {key}" for key, value in counts.items()))
sys.exit(1 if counts["skipped"] or counts["failed"] else 0)
PY

}
print_message () 
{ 
    cat <<-END
NOTICE:
    Recently it has become necessary to deprecate some features of crostini,
    including:
      * UI-based installation of .deb packages. Installation via aptitude is
        the default path, but there are also visual package managers which
        may be used.
      * UI-based Debian release upgrade. Please refer to release notes for
        the release in question for upgrade instructions.
      * Multi-container support.

    For the most up-to-date news, please visit
    https://developers.google.com/chromeos/app-development/develop/news

    PSA: In order to mitigate the Januscape kernel exploit (see:
    https://github.com/V4bel/Januscape), nested virtualization has been
    disabled for host kernel versions 5.10 and 5.15. To check your host
    kernel version, you can navigate to chrome://system, find the entry named
    'uname', and if it looks something like 'Linux localhost 5.10.XXXX' or
    'Linux localhost 5.15.XXX' nested virtualization will be disabled

END

}
quote () 
{ 
    local quoted=${1//\'/\'\\\'\'};
    printf "'%s'" "$quoted"
}
quote_readline () 
{ 
    local ret;
    _quote_readline_by_ref "$1" ret;
    printf %s "$ret"
}
un () 
{ 
    local _alp_un_prefix=${1:-};
    [[ $# -gt 0 ]] || return 2;
    shift;
    python3 "$_UN_/unspendable.py" "$_alp_un_prefix" "$*"
}
d.removeSpaces () 
{ 
    ls | while read t; do
        u=$(- $t | sed 's/ /_/g');
        mv "$t" "$u" 2> /dev/null;
    done
}
d.removeParenthesis () 
{ 
    ls | while read t; do
        u=$(- $t | sed 's/(/_/g' | sed 's/)/_/g');
        mv "$t" "$u" 2> /dev/null;
    done
}
m.start () 
{ 
    php8.2 -S 127.0.0.1:$1 -t . /home/john/mogwai/sbshell/cruff/index.php
}
 

d.f () 
{ 
    declare -f -- $(echo -n "$1" | sed 's/-.*//')
}

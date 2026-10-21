__sb.alp () 
{ 
    COMMAND=$1;
    shift 1;
    while [[ -n "$*" ]]; do
        - alp $COMMAND $1;
        T=/tmp/$$;
        echo "$COMMAND.$1() { $COMMAND $1; }" >> $T;
        shift 1;
    done;
    source $T;
    - cat $T;
    rm $T
}

_sb.init alp

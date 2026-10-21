sb.dsh () 
{ 
    while read HOST; do
        ( echo $HOST;
        ssh -qn $HOST "$*" ) | xargs -n100;
    done
}

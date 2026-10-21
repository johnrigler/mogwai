sb.runfor () 
{ 
    ARG1=$1;
    shift;
    echo $* | xargs -n1 | while read X; do
        echo "$ARG1 $X > $X";
    done
}

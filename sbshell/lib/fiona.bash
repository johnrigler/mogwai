__sb.fiona () 
{ 
    - this should execute any word with a period or comma in the middle, and print;
    - anything else.;
    while read LINE; do
        echo $LINE | xargs -n1 | fiona.grep ".\.." RED;
    done
}

_sb.init fiona

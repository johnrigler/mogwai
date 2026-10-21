__sb.fiona.grep () 
{ 
    echo "$1 .....";
    grep --color=auto "$1" > /dev/null;
    if [[ $? -eq 0 ]]; then
        echo "...... $2 ......";
    fi
}

_sb.init fiona.grep

sb.checkip () 
{ 
    -1 google.com $1;
    host $ARG1 > /dev/null 2>&1;
    if [ $? -eq 0 ]; then
        host $ARG1 | grep --color=auto -v IPv6 | awk '{ print  $1,$4 }' | sed 's/.softlayer.local//g';
    fi
}

d.script () 
{ 
    ( script_size=$(stty size) || exit;
    trap 'stty cols "${script_size##* }"' EXIT;
    stty cols 80 || exit;
    COLUMNS=80 script -q -f "$(date +%G%m%d-W%V-%u-%H%M%S).unixTs" )
}

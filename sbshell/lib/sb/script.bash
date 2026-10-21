sb.script () 
{   

export _SBSHELL=$_SBDIR/lib/_script.bash
export _SBLOCAL_INIT=$_SBDIR/lib/init/$1.init

edit $_SBLOCAL_INIT

    cat $_SBSHELL $_SBLOCAL_INIT > $$
    echo >> $$
    echo "sb.info" >> $$
    OPTS="--flush --force --append"
    script $OPTS -c "bash -rcfile $$ " $$.ts
    (
    echo "<pre>"
    cat $$.ts
    echo "</pre>" ) >> $_SBFILE
    
    rm $$ $$.ts
    sb.color white
}

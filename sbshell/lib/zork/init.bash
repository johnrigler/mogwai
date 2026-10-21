__sb.zork.init () 
{ 
    env | sed 's/=/ /g' | while read A B; do
        echo unset $A | egrep --color=auto -v 'PATH|HOME';
    done > $$;
    . $$;
    rm $$;
    export HOME="/home/john";
    cd $HOME/.sbshell/zork
}

_sb.init zork.init

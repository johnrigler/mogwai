__sb.make.makerspace () 
{ 
    export MAKERSPACE=$SB_HOME/modules/makerspace;
    mkdir -p $MAKERSPACE/$1;
    vi $MAKERSPACE/$1/$2
}

_sb.init make.makerspace

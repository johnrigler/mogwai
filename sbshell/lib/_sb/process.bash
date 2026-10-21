_sb.process () 
{ 
    case $2 in 
        "--edit")
            declare -f $1 | sed 's/--color=auto//g' > ~/$$;
            vi ~/$$;
            source ~/$$;
            echo "edited $1";
#            _sb.init $1;
            rm ~/$$
        ;;
        "help")
            declare -f $1 | grep "^    -"
        ;;
        "base")
            declare -f $1
        ;;
        "save")
            CMD=`echo "$1" | cut -c 6-`;
            TARGET=`echo $CMD | sed 's/\./\//'`;
            TARGETFILE=`echo "$_SBDIR/lib/$TARGET".bash`;
            declare -f $1 > $TARGETFILE;
            echo >> $TARGETFILE;
            echo "_sb.init $CMD" >> $TARGETFILE
        ;;
        "test")
            --.eval;
            $*;
            --.off
        ;;
        *)
            $*
        ;;
    esac

    . $_SBDIR/lib/sb/color.bash

}

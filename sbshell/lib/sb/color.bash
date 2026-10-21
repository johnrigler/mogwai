sb.color () 
{ 
    : color Changed the color in the shell or web version;
    : color Possible colors are white,bold,underline,error,red,green,yellow,blue,purple,aqua;
    if [ -n $1 ]; then
        case $1 in 
            black)
                FG='00m'
            ;;
            bold)
                FG='01m'
            ;;
            underline)
                FG='04m'
            ;;
            error)
                FG='31m'
            ;;
            red)
                FG='31m'
            ;;
            green)
                FG='32m'
            ;;
            yellow)
                FG='33m'
            ;;
            blue)
                FG='34m'
            ;;
            purple)
                FG='35m'
            ;;
            aqua)
                FG='36m'
            ;;
        esac;
        printf "\033[$FG";
    fi

}

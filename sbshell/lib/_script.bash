---() { echo $* ; }
-() { echo $* ; }


sb.color () 
{ 
    : color Changed the color in the shell or web version;
    : color Possible colors are white,bold,underline,error,red,green,yellow,blue,purple,aqua;
    if [ -n $1 ]; then
        case $1 in 
            white)
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

sb.color green 

echo "welcome to the shell.." 

sb.color aqua

sb.hodor() {

while true
do
echo -n .
sleep 10
done

}

sb.grabname () 
{ 
    NAME=`ps -ef | grep --color=auto LOG | head -1 | sed 's/^.*LOG/LOG/' | sed 's/.ts//'`
    . /home/jrigler/softball/fabreq/"$NAME".init
}

knife.search.role.is_netproxy () 
{ 
    knife search role:is_netproxy -i ;
}

sb.env () 
{ 
    env | grep --color=auto _FABREQ
}

sb.date.HM () 
{ 
    date "+%H%M"
}

sb.date.YWw () 
{ 
    date "+%Y%W%w"
}

sb.info () 
{
    echo "welcome"
}

sb.web() {

#WEEK=`date +%W`
DAY=`date +%w`
#export _SBWEB=/var/www/html/jrigler-2018/$WEEK

if [[ -n $2 ]]
  then
  export _SBFILE="$_SBWEB/$1"_$2.php
  else 
  export _SBFILE="$_SBWEB/$DAY"_$1.php
  fi

sb.env

}

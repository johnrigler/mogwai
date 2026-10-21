_sb.init () 
{ 

    : load with __sb. prefix
    (
    echo -n "__sb."
    while read LINE
      do
      echo $LINE
      done
    ) > $$ < $1
    source $$ 

 ORIGINAL=`head -1 $$ | cut -c 6- | sed "s/(.*//g"`

   : overload stub over original name
   EVAL="$ORIGINAL() { _sb.process __sb.$ORIGINAL ARGS; }";
   EVAL=`echo $EVAL | sed 's/ARGS/$*/'`;
   eval $EVAL

}

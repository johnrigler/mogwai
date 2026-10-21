#!/bin/bash
## Sbshell version 4 

#  Covered by Apache License
#  12/14/2015
#
#

#echo "Copyright 2015 Secret Beach Solutions

#Licensed under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License.
#You may obtain a copy of the License at

 #   http://www.apache.org/licenses/LICENSE-2.0

#Unless required by applicable law or agreed to in writing, software
#distributed under the License is distributed on an "AS IS" BASIS,
#WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#See the License for the specific language governing permissions and
#limitations under the License."


alias edit=vi

export _SBFILE="sb.bash"
export _SBLIB="${BASH_SOURCE[0]}"
export _SBDIR=`echo $_SBLIB | sed "s/$_SBFILE//g"`


CHECK=`echo $_SBLIB | cut -c 1`

if [[ $CHECK != '/' ]]
  then
  echo "Failed to load. Sourced path must be fully qualified..."
  else


- () {
return;
}

-- () {
return;
}

--.off() { return;
 }

--.eval () {

--() { eval $*; }

}

-1() { 

if [[ -n $2 ]]
then
ARG1=$2
else 
ARG1=$1;
fi

if [[ $2 == 'test' ]]
then
ARG1=$1
fi

}

-2() {

if [[ -n $2 ]]
then
ARG2=$2
else
ARG2=$1;
fi

}
-3() {

if [[ -n $2 ]]
then
ARG3=$2
else
ARG3=$1;
fi

}

_sb.pass() {
    _SBUSER=`whoami`;
    echo -n "Enter password for $_SBUSER:  ";
    read -s __SBPWD

}


-pass() {

if [[ ! -n $__SBPWD ]]
then
_sb.pass
fi
}

_sb.save () {

  CMD=`echo "$1" | cut -c 6-`
  TARGET=`echo $CMD | sed 's/\./\//'`
  TARGETFILE=`echo $_SBDIR"lib/$TARGET".bash`
  mkdir -p $_SBDIR"lib/$TARGET
  declare -f $1 > $TARGETFILE
  echo >> $TARGETFILE
  echo "_sb.init $CMD" >> $TARGETFILE
  rmdir $_SBDIR"lib/$TARGET

}


_sb.process () {

case $2 in
"edit")
  declare -f $1 | sed 's/--color=auto//g' > /tmp/$$
  edit /tmp/$$
  source /tmp/$$
  echo "edited $1"
  _sb.process.derive $1 
  rm /tmp/$$
  #_sb.save $1
 
  ;;
"help")
  declare -f $1 | grep "^    -"
  ;;
"base")
  declare -f $1
  ;;
"save")
  CMD=`echo "$1" | cut -c 6-`
  TARGET=`echo $CMD | sed 's/\./\//'`
  TARGETFILE=`echo "$_SBDIR/lib/$TARGET".bash`
  declare -f $1 > $TARGETFILE
  echo >> $TARGETFILE
  echo "_sb.init $CMD" >> $TARGETFILE
  ;;
 "test")
 --.eval
 $*
 --.off
  ;;

 *)
  $*
  ;;
esac

}

---() {

_sb.init $1

}

_sb.edit() {

edit $_SBLIB 
source $_SBLIB

}

_sb.env() {

env | grep "SB"

}

function _sb.init() {

#declare -f __sb.$1 > /tmp/$$

echo "--- $1 ----"
#DEST=`head -1 /tmp/$$ | awk '{ print $1 }' | sed 's/^__sb.//g' | sed 's/\./\//g'`
#mv /tmp/$$ "$_SBPATH/$DEST".bash

EVAL="$1() { _sb.process __sb.$1 ARGS; }"

EVAL=`echo $EVAL | sed 's/ARGS/$*/'`
eval $EVAL

}

function _sb.sprocess.derive() {

BASE=`echo $1 | cut -c 6-`
EVAL="$BASE() { _sb.process $1 ARGS; }"
EVAL=`echo $EVAL | sed 's/ARGS/$*/'`
#_sb.init $BASE
eval $EVAL
}

function _sb.load() {

cd $_SBDIR/lib

find $1 | grep bash | xargs -n1 cat > $$
source $$
rm $$

find $1 | grep bash | xargs -n1 head -1  | grep "__sb" | sed 's/function //g' | sed 's/(.*//g' | while read FUNCTION
  do
  _sb.derive $FUNCTION
  done

}

fi

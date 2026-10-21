#!/bin/bash


. ~/.sbshell/mt.ini

mt_vi() {

sb_mvi mt

}

mt_feh() {

feh $1

}

mt_motd() {


echo "This is the minetest module."


}

mt_env() {

echo "--------------------------------"
env | grep "^MT_"
echo "-----------------"

}

mt_world() {

export MT_WORLD="$1"
mt_init

}

mt_ls_worlds() {

ls $MT_T/worlds

}

mt_go() {

minetest --world $MT_WORLD

}

mt_select() {

sqlite3 -line $MT_DB "select data from blocks where pos=$1" | cut -c 9-

#blocks pos data

}

mt_update() {

sqlite3 -line $MT_DB "update blocks set data='$2' where pos='$1'"

}

mt_pos_ls() {


sqlite3 -line $MT_DB "select pos from blocks" | cut -c 9- | grep [0-9]

}



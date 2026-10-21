__sb.db.d () 
{ 
    echo "\d $1" | _db.toggle | grep --color=auto -v sequence | egrep --color=auto '+|'
}

_sb.init db.d

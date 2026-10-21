__sb.db.date () 
{ 
    echo "select extract ('epoch' from now());" | _db.toggle | grep --color=auto '\.' | sed 's/\..*//' | cut -c 2-
}

_sb.init db.date

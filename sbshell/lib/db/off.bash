__sb.db.off () 
{ 
    function _db.toggle () 
    { 
        while read LINE; do
            echo "$LINE";
        done
    }
}

_sb.init db.off

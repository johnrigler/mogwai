__sb.db.on () 
{ 
    function _db.toggle () 
    { 
        sudo -u postgres psql nahcprod
    }
}

_sb.init db.on

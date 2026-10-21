__sb.db.show.all.grants () 
{ 
    echo "SELECT sql_grants FROM common_schema.sql_show_grants;" | _db.toggle
}

_sb.init db.show.all.grants

sb.pass () 
{ 
    _SBUSER=`whoami`;
    echo -n "Enter password for $_SBUSER:  ";
    read -s __SBPWD;
    export __SBPWD
}

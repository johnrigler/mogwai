sb.jira() {

: connect to jira as user and create cookie in local dir
curl https://jira/softlayer.local/login.jsp \
  --data os_username=jrigler --data os_password="$_SBPWD"  \
  --data submit=yes --insecure --cookie-jar jira.cookies 

}

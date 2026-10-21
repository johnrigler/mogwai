_sb.source() {

ls *.bash | while read SCRIPT
  do
  echo "# $SCRIPT"
  echo source $SCRIPT
  done > $$

  source $$
  rm $$

}

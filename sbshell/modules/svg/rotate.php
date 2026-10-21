<?php 

$xoff=20;
$yoff=20;

include 'svg_lib.php';

refresh();

lasersaurheader();

//cross(472,240);

for ( $x = 0 ; $x < 360 ; $x = $x + 90 )
  {
  line(200,200,210,200,$x,205,230); // horizontal marker
  }
svgclose();

?>

<?php 

$xoff=20;
$yoff=20;

include 'svg_lib.php';

lasersaurheader();
//cross(472,240);
//line(10,140,506,140); // horizontal marker
//line(255,20,255,258); // vertical marker
//line(20,20,255,258);
//line(20,255,255,20);
/// split face
line(10,160,506,160); // split face
// cups
cup_3( 128,140 );
cup_3( 256,140 );
cup_3( 386,140 );
fingerhole( 40,120 );
fingerhole( 468,120 );
fingerhole( 255,238 ); // bottom hole
airhole( 470,32 );
surface(472,224,10); // made 4 bigger for snugger fit
svgclose();

?>

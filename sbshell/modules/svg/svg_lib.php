<?php 

$xoff=20;
$yoff=20;


# 24 by 48 lasersaur

function lasersaurheader() {

echo '<?xml version="1.0" encoding="UTF-8" ?>
<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">
<svg width="1220mm" height="610mm" viewBox="0 0 1220 610" 
version="1.1" xmlns="http://www.w3.org/2000/svg">';


}

function refresh() {

if (php_sapi_name() != 'cli' ) {
echo "<meta http-equiv='refresh' content='10'>";
  }
}

function svgclose() {

echo '</svg>
';

}

function airhole( $x, $y ) {

$size=4;

echo "<circle cx='$x' cy='$y' r='$size' 
              stroke='blue' stroke-width='2' fill='none' />\n";


}

function fingerhole( $x, $y ) {

$size=12;

echo "<circle cx='$x' cy='$y' r='$size' 
              stroke='brown' stroke-width='2' fill='none' />\n";

}

function line( $x1, $y1, $x2, $y2 , $rotation=0 , $xrot=0, $yrot=0  ) {


echo "<line x1='$x1' y1='$y1' x2='$x2' y2='$y2' 
     style='stroke:rgb(255,0,0);stroke-width:2'
              transform = 'rotate($rotation $xrot $yrot)'

      />\n";

}

function tooth_x( $x, $y, $w, $h, $off ) {

$x1 = $x - $w;
$x2 = $x + $w;
$y1 = $y - $h;
$y2 = $y + $h;

$midleft = $x1 + $w - $off;
$midright = $x2 - $w + $off;

line ( $x1, $y1, $midleft, $y1 );
line ( $x2, $y1, $midright, $y1 );
line ( $midleft, $y1, $midleft, $y1 );
line ( $midright, $y1, $midright, $y1 );
line ( $midleft, $y1, $midright, $y1 );

}

function tooth_y( $x , $y , $w ,$h, $off) {

$x1 = $x - $w;
$x2 = $x + $w;
$y1 = $y - $h;
$y2 = $y + $h;

$midtop = $y1 + $h - $off;
$midbottom = $y2 + $h + $off;

line ($x2, $y2, $x1, $y2);
line ($x1, $y1, $x1, $y2);
line ($x1, $y1, $x2, $y1);
line ($x2, $y1, $x2, $midtop); 
line ($x2, $y2, $x2, $midbottom);


}

function tooth_poly_x( $x, $y ) {

$height = 16;
$y2 = $y + $height;

tooth_x($x,$y,20,8,8);
tooth_x($x,$y2,16,10,10);

}

function tooth_poly_y( $x, $y ) {

$width = 16;
$x2 = $x + $width;

tooth_y($x,$y,10,10,8);
tooth_y($x2,$y,8,8,10);

}

function cross( $x, $y ) {

$xoff = 20;
$yoff = 20;

line($xoff,$yoff,$x + $xoff,$y + $yoff);
line($xoff,$y + $yoff,$x + $xoff,$yoff);

}


function cup( $x , $y, $size ) {

echo "<circle cx='$x' cy='$y' r='$size' stroke='green'
              stroke-width='2' 
              fill='none' />\n";

}

function cup_2   ( $x, $y ) { cup ($x , $y, 27); }
function cup_3   ( $x, $y ) { cup ($x, $y, 36); }
function cup_375 ( $x, $y ) { cup ($x, $y, 48); }
function cup_4   ( $x, $y ) { cup ($x , $y, 53); }
function cup_5   ( $x, $y ) { cup ($x ,$y, 66); }
function cup_6   ( $x, $y ) { cup ($x, $y, 78); }

function cup_4_down ( $x, $y )

{

cup_2 ( $x, $y );
cup_3 ( $x, $y );

}


function text( $x, $y, $message ) {

echo "
<text x='$x' y='$y' fill='red' 
  transform='rotate(0 0,0)'>$message</text>";

}

$unit="mm";
$val=10;
$h=1100;
$hm=$h*-1;
$v=500;
$vm=$v*-1;

$sw=1;

//echo "<svg width=1200$unit height=600$unit viewBox='0 0 1200 600' >\n";

function surface( $h , $v , $val) {

$unit="";
$hm=$h*-1;
$vm=$v*-1;

$sw=1;

$xoff=20;
$yoff=20;


echo "<path fill='none' stroke='black' stroke-width='$sw'  d='";
echo"
M$xoff,$yoff 
h$h a$val,$val 0 0 1 $val,$val 
v$v a$val,$val 0 0 1 -$val,$val 
h$hm a$val,$val 0 0 1 -$val,-$val 
v$vm a$val,$val 0 0 1 $val,-$val
'/>\n\n"; 

}

function square( $x , $y , $size, $val) {

$unit="";
$hm=$x*-1;
$vm=$y*-1;

$sw=1;

$xoff=190;
$yoff=70;


echo "<path fill='none' stroke='purple' stroke-width='$sw'  d='";
echo"
M$xoff,$yoff 
h$x a$val,$val 0 0 1 $val,$val 
v$y a$val,$val 0 0 1 -$val,$val 
h$hm a$val,$val 0 0 1 -$val,-$val 
v$vm a$val,$val 0 0 1 $val,-$val
'/>\n\n";

}


?>

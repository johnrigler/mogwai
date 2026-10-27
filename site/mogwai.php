<?php

// create a 200*200 image

$full = 200;

$img = imagecreatetruecolor($full, $full);

// allocate some colors
$grey   =  imagecolorallocate($img, 100, 100, 100);
$white  =  imagecolorallocate($img, 255, 255, 255);
$white1 =  imagecolorallocate($img, 200, 200, 200);
$red    =  imagecolorallocate($img, 255,   0,   0);
$green  =  imagecolorallocate($img,   0, 255,   0);
$green1 =  imagecolorallocate($img,   0, 200,   0);
$blue   =  imagecolorallocate($img,   0,   0, 255);
$blue1  =  imagecolorallocate($img,   0,   0, 200);

$mid = $full / 2;

imagefilledrectangle($img,0,0,$full,$full,$grey);

for($x = 0; $x < 180; $x++)
{
	$c = 255 - $x;
	imagearc($img, $mid, $mid, $full-$x, $full-$x, 0, 360, imagecolorallocate($img, $c, $c, $c));
};

for($x = 0; $x < 50; $x++)
{
        $c = 255 - $x*2;
        imagearc($img, 60, 75, 200-$c, 200-$c, 0, 360, imagecolorallocate($img, 0, $c, 0));
};

for($x = 0; $x < 180; $x++)
{
        $c = 255 - $x;
    //    imagearc($img, $mid, $mid, $full-$x, $full-$x, 0, 360, imagecolorallocate($img, $c, $c, $c));
};



imagearc($img, $mid, $mid, 150-$x, 150-$x, 25, 155, $red);
// left and then the right eye
//imagearc($img,  60,  75,  50-$x,  50-$x,  0, 360, $green);
imagearc($img, 140,  75,  50-$x,  50-$x,  0, 360, $blue);
 

for($x = 16; $x < 30; $x++)
{
// draw the head
//imagearc($img, $mid, $mid, $full-$x, $full-$x,  0, 360, $white1);
// mouth
imagearc($img, $mid, $mid, 150-$x, 150-$x, 25, 155, $red);
// left and then the right eye
// imagearc($img,  60,  75,  50-$x,  50-$x,  0, 360, $green1);
imagearc($img, 140,  75,  50-$x,  50-$x,  0, 360, $blue1);
}
 

// output image in the browser
header("Content-type: image/png");
imagepng($img);

// free memory
imagedestroy($img);

?>

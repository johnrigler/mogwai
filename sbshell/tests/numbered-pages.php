<?php
// Run: php8.2 sbshell/tests/numbered-pages.php
// Exercise the actual router in a child PHP process because index.php exits.
function check($ok, $message){ if(!$ok) throw new RuntimeException($message); }
$root = sys_get_temp_dir() . "/sb-numbered-" . bin2hex(random_bytes(5));
mkdir($root);
$router = realpath(__DIR__ . "/../cruff/index.php");
function render_page($root, $router, $page = null){
	$code = '$_SERVER["DOCUMENT_ROOT"]=' . var_export($root, true)
		. ';$_SERVER["REQUEST_URI"]="/";$_SERVER["QUERY_STRING"]="";';
	if($page !== null) $code .= '$_GET["page"]=' . var_export((string)$page, true) . ';';
	$code .= 'include ' . var_export($router, true) . ';';
	$process = proc_open([PHP_BINARY, '-d', 'display_errors=1', '-r', $code],
		[0=>['pipe','r'], 1=>['pipe','w'], 2=>['pipe','w']], $pipes);
	if(!is_resource($process)) throw new RuntimeException("Cannot start PHP renderer.");
	fclose($pipes[0]);
	$html = stream_get_contents($pipes[1]);
	$error = stream_get_contents($pipes[2]);
	fclose($pipes[1]); fclose($pipes[2]);
	$exit = proc_close($process);
	check($exit === 0, "Renderer failed: " . $error);
	return $html;
}
try{
	file_put_contents("$root/1_04.php", "<p>FOURTH-INCLUDE</p>");
	file_put_contents("$root/1_02.php", "<p>SECOND-INCLUDE</p>");
	file_put_contents("$root/1_03.php", "<?php echo '<strong>THIRD-INCLUDE</strong>'; ?>");
	file_put_contents("$root/1_01.php", "<p>FIRST-INCLUDE</p>");
	file_put_contents("$root/1_05.ts", "-->> echo TRANSCRIPT-MARKER\r\nTRANSCRIPT-MARKER\r\n");
	file_put_contents("$root/2_01.php", "<p>NEXT-PAGE</p>");
	file_put_contents("$root/readme.md", "# Ordinary file");
	$html = render_page($root, $router);
	$start = strpos($html, '<article class="sb-document">');
	check($start !== false, "Assembled page must exist.");
	$product = substr($html, $start);
	$markers = ['FIRST-INCLUDE', 'SECOND-INCLUDE', 'THIRD-INCLUDE', 'FOURTH-INCLUDE', 'TRANSCRIPT-MARKER'];
	$positions = array_map(fn($word) => strpos($product, $word), $markers);
	check(!in_array(false, $positions, true), "All five source sections must render.");
	check($positions === array_values(array_unique($positions))
		&& $positions === array_values(array_sort_by_position($positions)), "Sections must use numeric order.");
	check(str_contains($product, '<strong>THIRD-INCLUDE</strong>'), "PHP sections must execute via include.");
	check(str_contains($product, 'class="script-log"'), "A .ts transcript must use the transcript viewer.");
	check(str_contains($product, '?page=2'), "Next links to the next numbered page.");
	check(str_contains($product, 'Page 1 of 2'), "The current page count is visible.");
	$other = render_page($root, $router, 2);
	$other = substr($other, strpos($other, '<article class="sb-document">'));
	check(str_contains($other, "NEXT-PAGE") && !str_contains($other, "FIRST-INCLUDE"), "Page 2 shows its own content.");
	check(str_contains($other, '?page=1'), "Previous links back to page 1.");
	echo "SB Shell numbered PHP sections, ordered transcript and page navigation passed.\n";
}finally{
	foreach(glob("$root/*") ?: [] as $file) unlink($file);
	rmdir($root);
}
function array_sort_by_position($values){sort($values); return $values;}

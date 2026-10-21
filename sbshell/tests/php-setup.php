<?php
// Run with the PHP configuration to check; also run with -n for missing modules.
require_once __DIR__ . "/../cruff/check.php";
function check($condition, $message){ if(!$condition) throw new RuntimeException($message); }
$root = sys_get_temp_dir() . "/sbshell-setup-" . bin2hex(random_bytes(6));
mkdir($root);
try{
	$checks = sb_php_checks($root);
	check($checks["Archive readable"][0] && $checks["Catalog writable"][0], "A new writable archive is usable.");
	check(scandir($root) === [".", ".."], "Checking must not create archive files.");
	check($checks["SQLite3"][0] === class_exists("SQLite3"), "SQLite3 must be tested or reported missing.");
	$gd = function_exists("gd_info") ? gd_info() : [];
	check($checks["GD / PNG"][0] === (!empty($gd["PNG Support"]) && function_exists("imagepng")), "PNG encoding must work or be reported missing.");
	check(sb_php_ready($checks) === ($checks["SQLite3"][0] && $checks["GD / PNG"][0]), "Readiness needs the catalog and requested graphics support.");
	$missing = sb_php_checks($root . "/does-not-exist");
	check(!$missing["Archive readable"][0] && !$missing["Catalog writable"][0] && !sb_php_ready($missing), "A missing archive must not report ready.");
	mkdir($root . "/catalog.sqlite3");
	check(!sb_php_checks($root)["Catalog writable"][0], "A directory cannot be used as a catalog file.");
	rmdir($root . "/catalog.sqlite3");
	file_put_contents($root . "/catalog.sqlite3", "leave this file unchanged");
	sb_php_checks($root);
	check(file_get_contents($root . "/catalog.sqlite3") === "leave this file unchanged", "The checker must not open or rewrite an existing catalog.");
	ob_start(); sb_php_setup_page($root); $html = ob_get_clean();
	check(strpos($html, "SB Shell PHP setup") !== false && strpos($html, "SB_PHP=php" . PHP_MAJOR_VERSION . "." . PHP_MINOR_VERSION) !== false, "The browser report must match the serving PHP version.");
	check(strpos($html, "memory database tested") !== false && strpos($html, "GD / PNG") !== false, "Report both actual catalog and graphics capabilities.");
	echo "PHP setup: capabilities, missing modules, archive paths, read-only checking and browser report passed.\n";
}finally{
	if(is_file($root . "/catalog.sqlite3")) unlink($root . "/catalog.sqlite3");
	if(is_dir($root . "/catalog.sqlite3")) rmdir($root . "/catalog.sqlite3");
	rmdir($root);
}

<?php
// Shared by the terminal checker and the PHP process serving the archive.
function sb_php_checks($root){
	$sqlite = false;
	if(class_exists("SQLite3")){
		try{
			$db = new SQLite3(":memory:");
			$db->enableExceptions(true);
			$sqlite = $db->exec("CREATE TABLE test (value TEXT); INSERT INTO test VALUES ('ok')")
				&& $db->querySingle("SELECT value FROM test") === "ok";
			$db->close();
		}catch(Throwable $error){ /* Report an unavailable extension without stopping the check. */ }
	}
	$gd = function_exists("gd_info") ? gd_info() : [];
	$png = false;
	if(!empty($gd["PNG Support"]) && function_exists("imagecreatetruecolor") && function_exists("imagepng")){
		ob_start();
		try{
			$image = imagecreatetruecolor(1, 1);
			$png = imagepng($image) && substr(ob_get_contents(), 0, 8) === "\x89PNG\r\n\x1a\n";
			imagedestroy($image);
		}catch(Throwable $error){ /* Keep the report usable when GD cannot create an image. */ }
		finally { ob_end_clean(); }
	}
	$root = realpath($root);
	$readable = $root && is_dir($root) && is_readable($root);
	$writable = $readable && is_writable($root)
		&& (!file_exists($root . "/catalog.sqlite3") || (is_file($root . "/catalog.sqlite3") && is_writable($root . "/catalog.sqlite3")));
	// Each row is: available, purpose, needed for the base setup.
	return [
		"PHP 8.0+" => [PHP_VERSION_ID >= 80000, "Directory viewer and numbered-part assembly", true],
		"SQLite3" => [$sqlite, "Catalog and saved document names (memory database tested)", true],
		"GD / PNG" => [$png, "Graphics generation (a PNG is encoded in memory)", true],
		"GD / JPEG" => [!empty($gd["JPEG Support"]) && function_exists("imagejpeg"), "JPEG graphics", false],
		"GD / FreeType" => [!empty($gd["FreeType Support"]) && function_exists("imagettftext"), "TrueType text in graphics", false],
		"Fileinfo" => [function_exists("mime_content_type"), "File-type metadata; otherwise the catalog uses a generic type", false],
		"SHA-256" => [function_exists("hash_algos") && in_array("sha256", hash_algos()), "File fingerprints", true],
		"JSON" => [function_exists("json_encode") && function_exists("json_decode"), "Browser refresh responses and terminal recordings", true],
		"Archive readable" => [(bool)$readable, "Read the checked directory", true],
		"Catalog writable" => [(bool)$writable, "Create/update catalog.sqlite3 and its journal in that directory", true]
	];
}

function sb_php_ready($checks){
	foreach($checks as $check) if($check[2] && !$check[0]) return false;
	return true;
}

function sb_php_packages(){
	$php = "php" . PHP_MAJOR_VERSION . "." . PHP_MINOR_VERSION;
	return "$php-cli $php-common $php-sqlite3 $php-gd";
}

function sb_php_setup_page($root){
	$checks = sb_php_checks($root);
	$ready = sb_php_ready($checks);
	$escape = function($value){ return htmlspecialchars($value, ENT_QUOTES | ENT_SUBSTITUTE, "UTF-8"); };
	header("Content-Type: text/html; charset=utf-8");
	header("Cache-Control: no-store");
?>
<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SB Shell PHP setup</title>
<style>
body { max-width:900px; margin:24px auto; padding:0 16px; color:#172433; background:#fafcfe; font:16px/1.5 system-ui,sans-serif; }
a { color:#135da8; } h1 { font-size:1.6rem; }
code, pre { font:14px/1.5 monospace; overflow-wrap:anywhere; }
pre { padding:12px; background:#eaf0f5; white-space:pre-wrap; }
table { width:100%; border-collapse:collapse; table-layout:fixed; }
th, td { padding:10px 5px; border-bottom:1px solid #cbd5df; text-align:left; vertical-align:top; overflow-wrap:anywhere; }
th:first-child { width:90px; } th:nth-child(2) { width:30%; }
td:first-child { white-space:nowrap; }
.ok { color:#1a6333; } .missing { color:#a12121; } .optional { color:#735114; }
.status { padding:12px; background:<?= $ready ? "#e5f3e8" : "#fff0dc" ?>; }
@media (max-width:500px) { body { padding:0 10px; } table { font-size:13px; } th:first-child { width:76px; } }
</style>
<nav><a href="/">Back to files</a> · <a href="?sb-check=1">Check again</a></nav>
<h1>SB Shell PHP setup</h1>
<p class="status"><?= $ready ? "Base setup ready, including SQLite3 and GD / PNG." : "Base setup incomplete. See the missing checks below." ?></p>
<p>PHP <?= $escape(PHP_VERSION) ?> · <?= $escape(PHP_SAPI) ?><br>
Binary: <code><?= $escape(PHP_BINARY) ?></code><br>
Configuration: <code><?= $escape(php_ini_loaded_file() ?: "No php.ini loaded") ?></code><br>
Archive: <code><?= $escape($root) ?></code></p>
<table>
<thead><tr><th>Status</th><th>Check</th><th>Used for</th></tr></thead>
<tbody>
<?php foreach($checks as $name => $check){ $status = $check[0] ? "OK" : ($check[2] ? "MISSING" : "OPTIONAL"); ?>
<tr><td class="<?= strtolower($status) ?>"><?= $status ?></td><td><?= $escape($name) ?></td><td><?= $escape($check[1]) ?></td></tr>
<?php } ?>
</tbody></table>
<h2>Penguin / Debian / Ubuntu</h2>
<p>Run the installer in a terminal on the machine serving SB Shell. It installs the modules for this PHP version and reruns these checks:</p>
<pre><?= $escape("SB_PHP=php" . PHP_MAJOR_VERSION . "." . PHP_MINOR_VERSION . " bash " . escapeshellarg(dirname(__DIR__) . "/setup") . " install " . escapeshellarg($root)) ?></pre>
<p>The matching packages are <code><?= $escape(sb_php_packages()) ?></code>. If they are already installed, the installer also enables SQLite3, GD and Fileinfo for terminal PHP and its built-in server.</p>
<p>Restart the PHP process serving SB Shell, then use <strong>Check again</strong>. For <code>php -S</code>, stop it with Ctrl+C and rerun its launch command. Apache or PHP-FPM needs its own service restart.</p>
<p>These results describe the PHP process serving this page. A terminal can use another PHP version or configuration. Permission failures need access to the displayed archive directory and any existing catalog; installing extensions does not change those permissions.</p>
<p>GD is included in the graphics setup. Existing image and PDF previews display through the browser and still work without GD. Optional rows identify additional capabilities, rather than blocking file browsing.</p>
</html>
<?php
}

if(PHP_SAPI === "cli" && realpath($_SERVER["SCRIPT_FILENAME"] ?? "") === __FILE__){
	$root = $argv[1] ?? getcwd();
	$checks = sb_php_checks($root);
	echo "SB Shell PHP setup\nPHP " . PHP_VERSION . " (" . PHP_SAPI . ")\nBinary: " . PHP_BINARY
		. "\nConfiguration: " . (php_ini_loaded_file() ?: "No php.ini loaded") . "\nDirectory: " . $root . "\n\n";
	foreach($checks as $name => $check){
		$status = $check[0] ? "OK" : ($check[2] ? "MISSING" : "OPTIONAL");
		echo "[$status] $name: " . $check[1] . "\n";
	}
	echo "\nPenguin packages for this PHP: " . sb_php_packages() . "\n";
	echo "The browser's PHP setup link checks the actual server and archive.\n";
	echo sb_php_ready($checks) ? "Base setup ready.\n" : "Base setup incomplete.\n";
	exit(sb_php_ready($checks) ? 0 : 1);
}

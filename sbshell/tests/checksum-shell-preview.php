<?php
// Run: php sbshell/tests/checksum-shell-preview.php
require_once __DIR__ . "/../cruff/preview.php";
function check($ok, $message){ if(!$ok) throw new RuntimeException($message); }
$root = sys_get_temp_dir() . "/sb-shell-preview-" . bin2hex(random_bytes(5));
mkdir($root);
$file = "$root/sb.find-43742.1";
try{
	$source = <<<'BASH'
sb.find ()
{
    # Treat this as Bash even though the suffix is numeric.
    local root="${1:-.}"
    printf '<script>not executable</script>\n'
}
BASH;
	file_put_contents($file, $source . "\n");
	check(sb_code_language($file) === "bash", "A checksum-suffixed Bash function must be recognized by its content.");
	check(sb_preview_type($file) === "code", "The shell function must be previewable as code.");

	ob_start();
	sb_preview($file, rawurlencode(basename($file)));
	$preview = ob_get_clean();
	check(str_contains($preview, 'sb-code-label">bash'), "The inline source panel must identify Bash.");
	check(str_contains($preview, 'sb-syn-keyword">local</span>'), "The Bash function must receive syntax highlighting.");
	check(str_contains($preview, '&lt;script&gt;') && !str_contains($preview, '<script>not executable</script>'),
		"Source must be escaped and never executed.");

	// Exercise the directory renderer rather than relying on the isolated classifier alone.
	$router = realpath(__DIR__ . "/../cruff/index.php");
	$code = '$_SERVER["DOCUMENT_ROOT"]=' . var_export($root, true)
		. ';$_SERVER["REQUEST_URI"]="/";$_SERVER["QUERY_STRING"]="";include ' . var_export($router, true) . ';';
	$proc = proc_open([PHP_BINARY, '-d', 'display_errors=1', '-r', $code],
		[0=>['pipe','r'], 1=>['pipe','w'], 2=>['pipe','w']], $pipes);
	check(is_resource($proc), "Cannot start PHP directory renderer.");
	fclose($pipes[0]);
	$page = stream_get_contents($pipes[1]);
	$error = stream_get_contents($pipes[2]);
	fclose($pipes[1]); fclose($pipes[2]);
	check(proc_close($proc) === 0, "Directory renderer failed: " . $error);
	check(preg_match('/SB Shell v\\d+\\.\\d+\\.\\d+/', $page), "The hamburger menu must show a version.");
	check(str_contains($page, 'data-file="sb.find-43742.1"'), "The checksum shell script must expand inline.");
	check(str_contains($page, 'sb-code-label">bash'), "The directory must render the highlighted Bash source.");
	check(str_contains($page, 'Highlighted source page') && str_contains($page, 'Original source'),
		"The full highlighted view and original file must remain accessible.");
	echo "SB Shell checksum-named Bash preview and hamburger version passed.\n";
}finally{
	foreach(glob("$root/*") ?: [] as $path) unlink($path);
	foreach(glob("$root/.*") ?: [] as $path) if(is_file($path)) unlink($path);
	rmdir($root);
}

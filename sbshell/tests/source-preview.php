<?php
// Run: php8.2 sbshell/tests/source-preview.php
require_once __DIR__ . "/../cruff/preview.php";
function check($ok, $message){ if(!$ok) throw new RuntimeException($message); }
foreach([
	"notes.md"=>"markdown", "capture.unixTs"=>"script", "capture.ts"=>"script",
	"run.sh"=>"code", "main.py"=>"code", "chisel.js"=>"code", "scene.gd"=>"code",
	"config.json"=>"code", "data.yaml"=>"code", "query.sql"=>"code",
	"readme.txt"=>"text", "scan.pdf"=>"pdf", "photo.png"=>"image",
] as $name=>$type) check(sb_preview_type($name) === $type, "$name must be $type");
$dir = sys_get_temp_dir() . "/sb-source-" . bin2hex(random_bytes(5));
mkdir($dir);
try{
	$script = $dir . "/runner";
	file_put_contents($script, "#!/usr/bin/env bash\nif true; then echo 'ready'; fi\n");
	check(sb_preview_type($script) === "code", "Extensionless shebang must be recognized.");
	check(sb_code_language($script) === "bash", "Shebang selects Bash.");
	$binary = $dir . "/opaque";
	file_put_contents($binary, "\x00\x01\x02\x03");
	check(sb_preview_type($binary) === "", "Unknown binary cannot become a text preview.");
	$source = '<script>alert(1)</script>' . "\n" . "if true; then # demo";
	$html = sb_code_highlight($source, "bash");
	check(!str_contains($html, "<script>") && str_contains($html, "&lt;script&gt;"), "Escape all source.");
	check(str_contains($html, 'class="sb-syn-keyword"'), "Bash keyword is colored.");
	check(str_contains($html, 'class="sb-syn-comment"'), "Shell comment is colored.");
	$bt = chr(96);
	$md = "# Heading\n\nText with ~~deletion~~ and {$bt}*literal*{$bt}.\n\n"
		. "| Name | Value |\n| --- | --- |\n| alpha | **one** |\n\n"
		. $bt.$bt.$bt."bash\n".'echo "hi" # demo'."\n".$bt.$bt.$bt
		. "\n\n<script>not HTML</script>";
	ob_start(); sb_markdown($md); $html = ob_get_clean();
	check(str_contains($html, "<h1>Heading</h1>"), "Markdown heading.");
	check(str_contains($html, "<del>deletion</del>"), "Markdown strikethrough.");
	check(str_contains($html, "<code>*literal*</code>"), "Inline code stays literal.");
	check(str_contains($html, "<table>") && str_contains($html, "<th>Name</th>")
		&& str_contains($html, "<strong>one</strong>"), "Markdown tables.");
	check(str_contains($html, 'sb-code-label">bash') && str_contains($html, "sb-syn-comment"), "Colored code fences.");
	check(!str_contains($html, "<script>") && str_contains($html, "&lt;script&gt;"), "Markdown is escaped.");
	echo "SB Shell source preview and Markdown checks passed.\n";
} finally {
	foreach(glob($dir . "/*") as $file) unlink($file);
	rmdir($dir);
}

<?php
// Run with: php8.2 tests/week-directory.php
require_once __DIR__ . "/../cruff/catalog.php";
require_once __DIR__ . "/../cruff/preview.php";
function check($condition, $message){ if(!$condition) throw new RuntimeException($message); }
$sb_root = sys_get_temp_dir() . "/sbshell-week-" . bin2hex(random_bytes(6));
mkdir($sb_root . "/42/sub", 0777, true);
mkdir($sb_root . "/43");
mkdir($sb_root . "/42/.hidden");
$week = $sb_root . "/42";
file_put_contents($week . "/notes.md", "# Notes\n\n**Bold** and `literal *code*`\n\n- one\n- two\n\n```php\n<?php echo 'literal'; ?>\n```\n");
file_put_contents($week . "/scan.PNG", base64_decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII="));
file_put_contents($week . "/letter.pdf", "%PDF-1.4\noriginal\n");
file_put_contents($week . "/session.unixTs", "-->> echo hi\r\n\x1b[32mhi\x1b[0m\r\n");
file_put_contents($week . "/sub/item.txt", "nested");
file_put_contents($sb_root . "/43/other.txt", "other week");
file_put_contents($week . "/.hidden/private.txt", "hidden");
file_put_contents($week . "/files.txt", "generated");
file_put_contents($week . "/catalog.sqlite3", "nested catalog");
file_put_contents($week . "/catalog.sqlite3-wal", "sidecar");
symlink($week . "/scan.PNG", $week . "/linked.png");
symlink($sb_root . "/43", $week . "/linked-dir");
function records(){
	$db = sb_catalog(); $result = [];
	$rows = $db->query("SELECT * FROM files ORDER BY path");
	while($row = $rows->fetchArray(SQLITE3_ASSOC)) $result[$row["path"]] = $row;
	$db->close(); return $result;
}
try{
	sb_catalog_scan($sb_root);
	check(is_file($sb_root . "/catalog.sqlite3"), "Browsing creates a real SQLite catalog.");
	$rows = records();
	check(count($rows) === 6, "Scan includes nested files and skips hidden/generated files and symlinks.");
	check($rows["42/scan.PNG"]["sha256"] === hash_file("sha256", $week . "/scan.PNG", true), "Store the full file hash.");
	$db = sb_catalog();
	check($db->querySingle("PRAGMA integrity_check") === "ok", "The database must pass SQLite integrity checks.");
	check($db->querySingle("SELECT min(length(sha256)) FROM files") === 32, "Store 32-byte digests.");
	check($db->querySingle("SELECT typeof(sha256) FROM files LIMIT 1") === "blob", "Digests must be binary.");
	$db->close();
	$stamp = sb_directory_stamp($sb_root);
	sb_catalog_scan($sb_root);
	check(sb_directory_stamp($sb_root) === $stamp, "Catalog writes and journal dates must not trigger a refresh loop.");
	sb_save_document("42/letter.pdf", "Letter", hash_file("sha256", $week . "/letter.pdf", true));
	check(sb_directory_stamp($sb_root) !== $stamp, "A saved document name must change the refresh semaphore.");
	$db = sb_catalog(true);
	$db->exec("UPDATE files SET root='daisy2026'; INSERT INTO metadata VALUES ('generatedAt','FileProxy scan')");
	$db->exec("UPDATE files SET iso_year=2026,iso_week=42,date_convention='existing' WHERE path='42/notes.md'");
	$db->close();
	$other = records()["43/other.txt"];
	$stamp = sb_directory_stamp($week);
	// Equal size and timestamp must still be rehashed for a recent write.
	file_put_contents($week . "/notes.md", str_repeat("x", filesize($week . "/notes.md")));
	rename($week . "/sub/item.txt", $week . "/sub/renamed.txt");
	unlink($week . "/scan.PNG");
	file_put_contents($week . "/new.md", "new");
	check(sb_directory_stamp($week) !== $stamp, "File additions and removals must change the refresh semaphore.");
	sb_catalog_scan($week);
	$rows = records();
	check(!isset($rows["42/scan.PNG"]) && !isset($rows["42/sub/item.txt"]), "Deleted and renamed paths must be removed.");
	check(isset($rows["42/new.md"], $rows["42/sub/renamed.txt"]), "New and renamed paths must be indexed.");
	check($rows["42/notes.md"]["sha256"] === hash_file("sha256", $week . "/notes.md", true), "Same-size recent writes must update the hash.");
	check($rows["42/notes.md"]["iso_year"] === 2026, "Preserve existing date metadata.");
	check($rows["43/other.txt"] === $other, "Refreshing one week must preserve all rows in other weeks.");
	check($rows["42/new.md"]["root"] === "daisy2026", "Reuse FileProxy's root alias.");
	$oldTime = filemtime($week . "/notes.md") - 300;
	touch($week . "/notes.md", $oldTime);
	sb_catalog_scan($week);
	file_put_contents($week . "/notes.md", str_repeat("y", filesize($week . "/notes.md")));
	touch($week . "/notes.md", $oldTime);
	sb_catalog_scan($week);
	check(records()["42/notes.md"]["sha256"] === hash_file("sha256", $week . "/notes.md", true), "A page load must verify bytes even if a tool preserves size and timestamp.");
	check(sb_document_path("Letter") === $week . "/letter.pdf", "Scanning must preserve saved document names.");
	$db = sb_catalog();
	check($db->querySingle("SELECT value FROM metadata WHERE key='generatedAt'") === "FileProxy scan", "Preserve FileProxy metadata.");
	$db->close();
	foreach(["png"=>"image", "PDF"=>"pdf", "md"=>"markdown", "unixTs"=>"script"] as $extension=>$type){
		check(sb_preview_type("file." . $extension) === $type, "Recognize " . $extension . " previews.");
	}
	ob_start(); sb_preview("letter.pdf", "letter.pdf", true); $html = ob_get_clean();
	check(str_contains($html, 'data-src="letter.pdf?raw=1"') && str_contains($html, 'type="application/pdf"'), "PDF preview uses lazy original bytes.");
	ob_start(); sb_markdown("# Title\n\n**bold** `*literal*`\n\n- item\n\n```\n<script>alert(1)</script>\n```\n\n[x](javascript:alert)\n\n<script>raw</script>"); $html = ob_get_clean();
	check(str_contains($html, '<h1>Title</h1>') && str_contains($html, '<strong>bold</strong>'), "Render Markdown structure.");
	check(str_contains($html, '<code>*literal*</code>') && str_contains($html, '<li>item</li>'), "Preserve inline code and lists.");
	check(!str_contains($html, '<script>') && !str_contains($html, 'href="javascript:'), "Source markup and script URLs must remain literal.");
	echo "Week directory: SQLite creation, updates, deletion, subtree preservation, FileProxy compatibility and preview rendering passed.\n";
}finally{
	foreach(new RecursiveIteratorIterator(new RecursiveDirectoryIterator($sb_root, FilesystemIterator::SKIP_DOTS), RecursiveIteratorIterator::CHILD_FIRST) as $entry){
		if($entry->isLink() || !$entry->isDir()) unlink($entry->getPathname()); else rmdir($entry->getPathname());
	}
	rmdir($sb_root);
}

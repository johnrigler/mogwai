<?php
// Run with: php8.2 tests/document-names.php
require_once __DIR__ . "/../cruff/catalog.php";
if(!class_exists("SQLite3")){
	fwrite(STDERR, "Enable PHP's SQLite3 extension before running this check.\n");
	exit(1);
}
function check($condition, $message){ if(!$condition) throw new RuntimeException($message); }
$sb_root = sys_get_temp_dir() . "/sbshell-names-" . bin2hex(random_bytes(6));
$sb_url = "/42/packet/";
mkdir($sb_root . "/42/packet/Centro", 0777, true);
$path = "42/packet/Centro/welcome letter.pdf";
$file = $sb_root . "/" . $path;
file_put_contents($file, "%PDF-1.4\noriginal source\n");
$digest = hash_file("sha256", $file, true);
try{
	check(sb_document_names() === [], "A new archive has no saved names.");
	check(!file_exists($sb_root . "/catalog.sqlite3"), "Reading must not create a catalog.");
	$name = "Centro's résumé & welcome letter";
	sb_save_document($path, $name, $digest);
	check(sb_document_names()[$path] === $name, "Names must persist between database opens.");
	check(sb_document_path($name) === $file, "A saved name must resolve to its source.");
	check(sb_document_url($name) === "Centro/welcome%20letter.pdf", "Rendered links must be relative to the page.");
	$sb_url = "/42/other/";
	check(sb_document_url($name) === "../packet/Centro/welcome%20letter.pdf", "Names must work from sibling pages.");
	$db = sb_catalog(true);
	check($db->querySingle("SELECT length(sha256) FROM sb_documents") === 32, "Store full SHA-256 as 32 bytes.");
	check($db->querySingle("SELECT typeof(sha256) FROM sb_documents") === "blob", "Hashes must be SQLite BLOBs.");
	$db->exec("INSERT INTO metadata VALUES ('generatedAt', 'original scan')");
	$db->exec("INSERT INTO files(root,path,bytes,mtime_ns,sha256,mime) VALUES ('archive','existing.txt',1,1,zeroblob(32),'text/plain')");
	$db->close();
	sb_save_document($path, "Welcome letter", $digest);
	check(sb_document_path("WELCOME LETTER") === $file, "Names ignore ASCII letter case.");
	try { sb_document_path($name); throw new RuntimeException("Old name still resolved."); }
	catch(RuntimeException $error){ check($error->getCode() === 404, "Renaming must replace the former name."); }
	try { sb_save_document("other.pdf", "welcome LETTER", $digest); throw new RuntimeException("Duplicate name was saved."); }
	catch(RuntimeException $error){ check($error->getCode() === 409, "Another document cannot take an existing name."); }
	$db = sb_catalog();
	check($db->querySingle("SELECT count(*) FROM files") === 1, "Naming must preserve FileProxy's file rows.");
	check($db->querySingle("SELECT value FROM metadata WHERE key='generatedAt'") === "original scan", "Naming must preserve scan metadata.");
	$db->close();
	file_put_contents($file, "%PDF-1.4\nchanged source\n");
	try { sb_document_path("Welcome letter"); throw new RuntimeException("Changed bytes were accepted."); }
	catch(RuntimeException $error){ check($error->getCode() === 409, "Changed bytes must require an updated reference."); }
	sb_save_document($path, "Welcome letter", hash_file("sha256", $file, true));
	check(sb_document_path("Welcome letter") === $file, "Saving again accepts the current file.");
	echo "Document names: persistence, relative URLs, renaming, duplicate names, binary hashes, file integrity and catalog preservation passed.\n";
}finally{
	foreach(new RecursiveIteratorIterator(new RecursiveDirectoryIterator($sb_root, FilesystemIterator::SKIP_DOTS), RecursiveIteratorIterator::CHILD_FIRST) as $entry){
		if($entry->isDir()) rmdir($entry->getPathname()); else unlink($entry->getPathname());
	}
	rmdir($sb_root);
}

<?php
// Run with php8.2 -n tests/clipboard.php; saving .clip needs no extensions.
require_once __DIR__ . "/../cruff/clipboard.php";
require_once __DIR__ . "/../cruff/catalog.php";
function check($condition, $message){ if(!$condition) throw new RuntimeException($message); }
$sb_root = sys_get_temp_dir() . "/sbshell-clip-" . bin2hex(random_bytes(6));
mkdir($sb_root . "/42/sub", 0777, true);
mkdir($sb_root . "/43");
file_put_contents($sb_root . "/42/alpha one.md", "alpha");
file_put_contents($sb_root . "/42/zeta.txt", "zeta");
file_put_contents($sb_root . "/43/other.txt", "other");
try{
	$stamp = sb_directory_stamp($sb_root);
	check(!is_file($sb_root . "/42/.clip"), "No clipboard exists before the first copy.");
	check(sb_save_clipboard("42/", ["zeta.txt", "alpha one.md", "sub/"]) === 3, "Save files and directory references.");
	$expected = $sb_root . "/42/zeta.txt\n" . $sb_root . "/42/alpha one.md\n" . $sb_root . "/42/sub/\n";
	check(file_get_contents($sb_root . "/42/.clip") === $expected, "Write plain absolute paths in order, with spaces and one final newline.");
	check(sb_directory_stamp($sb_root) === $stamp, "Saving hidden .clip files must not trigger refresh loops.");
	sb_save_clipboard("43/", ["other.txt"]);
	check(file_get_contents($sb_root . "/42/.clip") === $expected, "Another directory must keep a separate selection.");
	check(file_get_contents($sb_root . "/43/.clip") === $sb_root . "/43/other.txt\n", "Write the file in the viewed directory.");
	foreach([["../other.txt"], ["/etc/passwd"], ["missing.txt"], ["zeta.txt", "missing.txt"], [".clip"], ["catalog.sqlite3"], "not a list"] as $invalid){
		try { sb_save_clipboard("42/", $invalid); throw new LogicException("Invalid selection accepted."); }
		catch(RuntimeException $error){ check(in_array($error->getCode(), [400,409]), "Reject invalid selections before replacing the file."); }
		check(file_get_contents($sb_root . "/42/.clip") === $expected, "A rejected copy must preserve the previous list.");
	}
	file_put_contents($sb_root . "/42/two\nlines.txt", "source");
	try { sb_save_clipboard("42/", ["two\nlines.txt"]); throw new LogicException("Multiline path accepted."); }
	catch(RuntimeException $error){ check($error->getCode() === 400, "Paths must remain one per line."); }
	sb_save_clipboard("42/", ["zeta.txt", "zeta.txt"]);
	check(file_get_contents($sb_root . "/42/.clip") === $sb_root . "/42/zeta.txt\n", "A new selection replaces the list and removes duplicates.");
	sb_save_clipboard("42/", []);
	check(file_get_contents($sb_root . "/42/.clip") === "", "An empty selection writes an empty file.");
	unlink($sb_root . "/42/.clip");
	symlink($sb_root . "/43/.clip", $sb_root . "/42/.clip");
	try { sb_save_clipboard("42/", ["zeta.txt"]); throw new LogicException("Existing symlink replaced."); }
	catch(RuntimeException $error){ check($error->getCode() === 409, "Preserve an existing deliberate .clip symlink."); }
	check(is_link($sb_root . "/42/.clip"), "Keep the existing link intact.");
	check(glob($sb_root . "/42/.clip-*") === [], "Leave no temporary clipboard files behind.");
	echo "Directory .clip: plain paths, order, spaces, independent directories, replacement, validation, empty lists, refresh stability and symlink preservation passed.\n";
}finally{
	foreach(new RecursiveIteratorIterator(new RecursiveDirectoryIterator($sb_root, FilesystemIterator::SKIP_DOTS), RecursiveIteratorIterator::CHILD_FIRST) as $entry){
		if($entry->isDir() && !$entry->isLink()) rmdir($entry->getPathname()); else unlink($entry->getPathname());
	}
	rmdir($sb_root);
}

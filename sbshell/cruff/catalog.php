<?php
// Named documents share the archive's FileProxy catalog.
function sb_catalog($write = false){
	$path = $GLOBALS["sb_root"] . "/catalog.sqlite3";
	if(!$write && !is_file($path)) return null;
	if(!class_exists("SQLite3")) throw new RuntimeException("Enable PHP's SQLite3 extension to save and use document names.");
	$db = new SQLite3($path, $write ? SQLITE3_OPEN_READWRITE | SQLITE3_OPEN_CREATE : SQLITE3_OPEN_READONLY);
	$db->enableExceptions(true);
	$db->busyTimeout(3000);
	if($write){
		// Keep a new catalog readable by FileProxy before its first scan.
		$db->exec("CREATE TABLE IF NOT EXISTS files (
			root TEXT NOT NULL, path TEXT NOT NULL, bytes INTEGER NOT NULL,
			mtime_ns INTEGER NOT NULL, sha256 BLOB NOT NULL CHECK(length(sha256) = 32),
			mime TEXT NOT NULL, iso_year INTEGER, iso_week INTEGER,
			iso_day INTEGER, date_convention TEXT, PRIMARY KEY(root, path)
		);
		CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
		CREATE TABLE IF NOT EXISTS sb_documents (
			path TEXT PRIMARY KEY, name TEXT NOT NULL COLLATE NOCASE UNIQUE,
			sha256 BLOB NOT NULL CHECK(length(sha256) = 32), updated_at TEXT NOT NULL
		);");
	}
	return $db;
}

// A cheap change semaphore: file dates/sizes and directory membership, not DB writes.
function sb_directory_stamp($directory){
	clearstatcache();
	$hash = hash_init("sha256");
	$walk = new RecursiveIteratorIterator(new RecursiveCallbackFilterIterator(
		new RecursiveDirectoryIterator($directory, FilesystemIterator::SKIP_DOTS),
		fn($entry) => $entry->getFilename()[0] !== "."
			&& !in_array($entry->getFilename(), ["catalog.sqlite3", "files.txt"])
			&& !str_starts_with($entry->getFilename(), "catalog.sqlite3-")
	), RecursiveIteratorIterator::SELF_FIRST);
	foreach($walk as $entry){
		$path = $entry->getPathname();
		hash_update($hash, $path . "\0");
		if($entry->isLink()) hash_update($hash, readlink($path) . "\0");
		// Directory dates include SQLite journal creation; names already track entries.
		if($entry->isFile()){
			$stat = stat($path);
			if($stat) hash_update($hash, $stat["mtime"] . ":" . $stat["ctime"] . ":" . $stat["size"] . ":" . $stat["ino"] . "\0");
		}
	}
	try { hash_update($hash, json_encode(sb_document_names(), JSON_INVALID_UTF8_SUBSTITUTE)); }
	catch(Throwable $error) { /* File changes can still be checked without SQLite. */ }
	return hash_final($hash);
}

// Refresh the browsed subtree in the same catalog used by FileProxy and names.
function sb_catalog_scan($directory){
	clearstatcache();
	$db = sb_catalog(true);
	$roots = [];
	$rows = $db->query("SELECT DISTINCT root FROM files");
	while($row = $rows->fetchArray(SQLITE3_ASSOC)) $roots[] = $row["root"];
	$root = count($roots) === 1 ? $roots[0] : basename($GLOBALS["sb_root"]);
	$prefix = ltrim(substr($directory, strlen($GLOBALS["sb_root"])), "/");
	if($prefix !== "") $prefix .= "/";
	$stmt = $db->prepare("SELECT * FROM files WHERE root=:root AND substr(path,1,length(:prefix))=:prefix");
	$stmt->bindValue(":root", $root, SQLITE3_TEXT);
	$stmt->bindValue(":prefix", $prefix, SQLITE3_TEXT);
	$rows = $stmt->execute();
	$old = [];
	while($row = $rows->fetchArray(SQLITE3_ASSOC)) $old[$row["path"]] = $row;
	$stmt->close();
	$put = $db->prepare("INSERT INTO files(root,path,bytes,mtime_ns,sha256,mime)
		VALUES (:root,:path,:bytes,:mtime,:sha256,:mime)
		ON CONFLICT(root,path) DO UPDATE SET bytes=excluded.bytes, mtime_ns=excluded.mtime_ns,
		sha256=excluded.sha256, mime=excluded.mime");
	$remove = $db->prepare("DELETE FROM files WHERE root=:root AND path=:path");
	$walk = new RecursiveIteratorIterator(new RecursiveCallbackFilterIterator(
		new RecursiveDirectoryIterator($directory, FilesystemIterator::SKIP_DOTS),
		fn($entry) => $entry->getFilename()[0] !== "." && !$entry->isLink()
			&& !in_array($entry->getFilename(), ["catalog.sqlite3", "files.txt"])
			&& !str_starts_with($entry->getFilename(), "catalog.sqlite3-")
	));
	$db->exec("BEGIN IMMEDIATE");
	try{
		foreach($walk as $entry){
			if(!$entry->isFile()) continue;
			$path = substr($entry->getPathname(), strlen($GLOBALS["sb_root"]) + 1);
			$previous = $old[$path] ?? null;
			unset($old[$path]);
			$bytes = $entry->getSize();
			$mtime = $entry->getMTime();
			$digest = hash_file("sha256", $entry->getPathname(), true);
			if($digest === false) throw new RuntimeException("Cannot read " . $path);
			// Only page loads scan contents; polling uses the cheap date semaphore.
			if($previous && $previous["bytes"] === $bytes && $previous["sha256"] === $digest
				&& intdiv($previous["mtime_ns"], 1000000000) === $mtime) continue;
			$put->bindValue(":root", $root, SQLITE3_TEXT);
			$put->bindValue(":path", $path, SQLITE3_TEXT);
			$put->bindValue(":bytes", $bytes, SQLITE3_INTEGER);
			$put->bindValue(":mtime", $mtime * 1000000000, SQLITE3_INTEGER);
			$put->bindValue(":sha256", $digest, SQLITE3_BLOB);
			$mime = function_exists("mime_content_type") ? mime_content_type($entry->getPathname()) : false;
			$put->bindValue(":mime", $mime ?: "application/octet-stream", SQLITE3_TEXT);
			$put->execute();
		}
		foreach($old as $path => $row){
			$remove->bindValue(":root", $root, SQLITE3_TEXT);
			$remove->bindValue(":path", $path, SQLITE3_TEXT);
			$remove->execute();
		}
		$db->exec("INSERT OR REPLACE INTO metadata VALUES ('sbScannedAt', strftime('%Y-%m-%dT%H:%M:%SZ','now'))");
		$db->exec("COMMIT");
	}catch(Throwable $error){
		$db->exec("ROLLBACK");
		throw $error;
	}finally{
		$put->close();
		$remove->close();
		$db->close();
	}
}

function sb_document_names(){
	$db = sb_catalog();
	if(!$db) return [];
	$names = [];
	if($db->querySingle("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='sb_documents'")){
		$rows = $db->query("SELECT path, name FROM sb_documents ORDER BY path");
		while($row = $rows->fetchArray(SQLITE3_ASSOC)) $names[$row["path"]] = $row["name"];
	}
	$db->close();
	return $names;
}

function sb_save_document($path, $name, $sha256){
	$name = trim($name);
	if(!preg_match('/\A[^\x00-\x1f\x7f]{1,200}\z/u', $name)){
		throw new RuntimeException("Use a name of 1–200 characters on one line.", 400);
	}
	$db = sb_catalog(true);
	$stmt = $db->prepare("INSERT INTO sb_documents(path, name, sha256, updated_at)
		VALUES (:path, :name, :sha256, strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
		ON CONFLICT(path) DO UPDATE SET name=excluded.name, sha256=excluded.sha256, updated_at=excluded.updated_at");
	$stmt->bindValue(":path", $path, SQLITE3_TEXT);
	$stmt->bindValue(":name", $name, SQLITE3_TEXT);
	$stmt->bindValue(":sha256", $sha256, SQLITE3_BLOB);
	try{
		$stmt->execute();
	}catch(Exception $error){
		if($db->lastErrorCode() === 19) throw new RuntimeException("That name already belongs to another document.", 409);
		throw $error;
	}finally{
		$stmt->close();
		$db->close();
	}
}

function sb_document_path($name){
	$db = sb_catalog();
	if(!$db || !$db->querySingle("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='sb_documents'")){
		throw new RuntimeException("Document name not found.", 404);
	}
	$stmt = $db->prepare("SELECT path, sha256 FROM sb_documents WHERE name=:name");
	$stmt->bindValue(":name", $name, SQLITE3_TEXT);
	$row = $stmt->execute()->fetchArray(SQLITE3_ASSOC);
	$stmt->close();
	$db->close();
	if(!$row) throw new RuntimeException("Document name not found.", 404);
	$path = $row["path"];
	if(str_starts_with($path, "/") || in_array("..", explode("/", $path), true) || str_contains($path, "\0")){
		throw new RuntimeException("The saved document path is invalid.", 409);
	}
	$file = $GLOBALS["sb_root"] . "/" . $path;
	if(!is_file($file)) throw new RuntimeException("The named document is missing from its saved path.", 404);
	if(!hash_equals($row["sha256"], hash_file("sha256", $file, true))){
		throw new RuntimeException("The document contents have changed. Open the file and save its name again to update the reference.", 409);
	}
	return $file;
}

function sb_document_url($name){
	// Resolve while PHP renders, leaving an ordinary relative asset URL for export.
	$file = sb_document_path($name);
	$to = explode("/", substr($file, strlen($GLOBALS["sb_root"]) + 1));
	$from = array_values(array_filter(explode("/", rawurldecode($GLOBALS["sb_url"] ?? "/")), "strlen"));
	while($from && $to && $from[0] === $to[0]){
		array_shift($from);
		array_shift($to);
	}
	return str_repeat("../", count($from)) . implode("/", array_map("rawurlencode", $to));
}

<?php
// Each viewed directory keeps its selected paths in an ordinary .clip file.
function sb_save_clipboard($prefix, $files){
	if(!is_array($files) || array_values($files) !== $files){
		throw new RuntimeException("Send a list of selected filenames.", 400);
	}
	$directory = rtrim(rtrim($GLOBALS["sb_root"], "/") . "/" . $prefix, "/") ?: "/";
	$paths = [];
	foreach($files as $file){
		if(!is_string($file)) throw new RuntimeException("Each selection must be a filename.", 400);
		$leaf = rtrim($file, "/");
		if($leaf === "" || $leaf[0] === "." || basename($leaf) !== $leaf || str_contains($leaf, "\0")
			|| $leaf === "catalog.sqlite3" || str_starts_with($leaf, "catalog.sqlite3-")){
			throw new RuntimeException("Select entries from the current directory.", 400);
		}
		$path = rtrim($directory, "/") . "/" . $leaf;
		if(strpbrk($path, "\r\n") !== false) throw new RuntimeException("Clipboard paths must fit on one line.", 400);
		if(!is_file($path) && !is_dir($path)) throw new RuntimeException("The selected entry is missing: " . $file, 409);
		if(is_dir($path)) $path .= "/";
		$paths[$path] = true;
	}
	$clip = rtrim($directory, "/") . "/.clip";
	if(is_link($clip) || (file_exists($clip) && !is_file($clip))){
		throw new RuntimeException("The directory's .clip must be a regular file.", 409);
	}
	if(!is_dir($directory) || !is_writable($directory)) throw new RuntimeException("Cannot write .clip in this directory.");
	// Rename a complete file into place so shell readers never see a partial list.
	$temporary = @tempnam($directory, ".clip-");
	if($temporary === false) throw new RuntimeException("Cannot write .clip in this directory.");
	$text = $paths ? implode("\n", array_keys($paths)) . "\n" : "";
	try{
		if(dirname($temporary) !== realpath($directory)
			|| @file_put_contents($temporary, $text) !== strlen($text)
			|| !@rename($temporary, $clip)){
			throw new RuntimeException("Could not save .clip in this directory.");
		}
	}finally { if(is_file($temporary)) unlink($temporary); }
	return count($paths);
}

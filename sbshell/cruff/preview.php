<?php
require_once __DIR__ . "/highlight.php";
function sb_preview_type($file){
	$extension = strtolower(pathinfo($file, PATHINFO_EXTENSION));
	if(in_array($extension, ["png", "jpg", "jpeg", "gif", "webp", "svg"])) return "image";
	if(in_array($extension, ["md", "markdown"])) return "markdown";
	if(in_array($extension, ["unixts", "ts", "script"])) return "script";
	if($extension === "pdf") return "pdf";
	if(in_array($extension, ["sh","bash","zsh","ksh","py","rb","pl","js","mjs","cjs","jsx","tsx","php","html","htm","xml","css","scss","json","jsonl","yaml","yml","toml","ini","conf","cfg","sql","gd","gdshader","c","h","cpp","hpp","rs","go","diff","patch"])) return "code";
	if(in_array($extension, ["txt","log","csv","tsv","text"])) return "text";
	if(!is_file($file) || !is_readable($file) || filesize($file) > 512 * 1024) return "";
	$sample = @file_get_contents($file, false, null, 0, 512);
	if(!is_string($sample) || preg_match('/[\x00-\x08\x0b\x0c\x0e-\x1f]/', $sample)) return "";
	return sb_code_language($file) === "text" ? "text" : "code";
}

function sb_preview($file, $url, $lazy = false){
	$type = sb_preview_type($file);
	if(in_array($type, ["markdown", "code", "text"])) sb_code_styles();
	$label = htmlspecialchars($file, ENT_QUOTES | ENT_SUBSTITUTE, "UTF-8");
	$url = htmlspecialchars($url, ENT_QUOTES | ENT_SUBSTITUTE, "UTF-8");
	$source = $lazy ? "data-src" : "src";
	if($type === "image"){
		echo '<img class="sb-image" ' . $source . '="' . $url . '" alt="' . $label . '">';
		if($lazy) echo '<noscript><img class="sb-image" src="' . $url . '" alt="' . $label . '"></noscript>';
	}elseif($type === "pdf"){
		echo '<object class="sb-pdf" ' . ($lazy ? "data-src" : "data") . '="' . $url . '?raw=1" type="application/pdf" aria-label="' . $label . '">';
		echo '<p><a href="' . $url . '?raw=1" target="_blank" rel="noopener">Open PDF / print</a></p></object>';
	}elseif($type === "markdown"){
		echo '<div class="sb-markdown">';
		sb_markdown(file_get_contents($file));
		echo '</div>';
	}elseif($type === "code" || $type === "text"){
		sb_code_file($file);
	}elseif($type === "script"){
		include_once __DIR__ . "/script.php";
		script_log($file);
	}
}

// Small, literal Markdown preview: headings, paragraphs, lists, quotes and fences.
// Escape source HTML; links accept relative paths and ordinary web/mail URLs.
function sb_markdown_inline($text){
	$text = htmlspecialchars($text, ENT_QUOTES | ENT_SUBSTITUTE, "UTF-8");
	$literal = [];
	$text = preg_replace_callback('/`([^`]+)`/', function($match) use (&$literal){
		$key = "\x1a" . count($literal) . "\x1a";
		$literal[$key] = '<code>' . $match[1] . '</code>';
		return $key;
	}, $text);
	$text = preg_replace_callback('/(!?)\[([^\]]+)\]\(([^\s)]+)\)/', function($match){
		$url = html_entity_decode($match[3], ENT_QUOTES, "UTF-8");
		if(preg_match('/^[a-z][a-z0-9+.-]*:/i', $url) && !preg_match('/^(https?|mailto):/i', $url)) return $match[0];
		if($match[1] === "!") return '<img src="' . $match[3] . '" alt="' . $match[2] . '" loading="lazy">';
		return '<a href="' . $match[3] . '">' . $match[2] . '</a>';
	}, $text);
	$text = preg_replace('/\*\*(.+?)\*\*/', '<strong>$1</strong>', $text);
	$text = preg_replace('/(?<!\*)\*([^*]+)\*(?!\*)/', '<em>$1</em>', $text);
	$text = preg_replace('/~~(.+?)~~/', '<del>$1</del>', $text);
	return strtr($text, $literal);
}

function sb_markdown($source){
	$paragraph = [];
	$list = $fence = $fenceLanguage = "";
	$fenceLines = [];
	$flush = function() use (&$paragraph){
		if($paragraph) echo '<p>' . sb_markdown_inline(implode("\n", $paragraph)) . "</p>\n";
		$paragraph = [];
	};
	foreach(explode("\n", str_replace(["\r\n", "\r"], "\n", $source)) as $line){
		if(preg_match('/^\s*(`{3,}|~{3,})(.*)$/', $line, $match)){
			if($fence === ""){
				$flush();
				if($list) echo "</$list>\n";
				$list = "";
				$fence = $match[1];
				$fenceLanguage = preg_split('/\\s+/', trim($match[2]))[0] ?: 'text';
				$fenceLines = [];
			}elseif($match[1][0] === $fence[0] && strlen($match[1]) >= strlen($fence) && trim($match[2]) === ""){
				sb_code(implode("\n", $fenceLines), $fenceLanguage);
				$fence = "";
			}else $fenceLines[] = $line;
			continue;
		}
		if($fence !== ""){
			$fenceLines[] = $line;
			continue;
		}
		$item = preg_match('/^\s*(?:([-+*])|\d+[.)])\s+(.+)$/', $line, $match);
		if($list && (!$item || $list !== ($match[1] ? "ul" : "ol"))){ echo "</$list>\n"; $list = ""; }
		if($item){
			$flush();
			if(!$list){ $list = $match[1] ? "ul" : "ol"; echo "<$list>\n"; }
			echo '<li>' . sb_markdown_inline($match[2]) . "</li>\n";
		}elseif(preg_match('/^(#{1,6})\s+(.+)$/', $line, $match)){
			$flush();
			$level = strlen($match[1]);
			echo "<h$level>" . sb_markdown_inline($match[2]) . "</h$level>\n";
		}elseif(preg_match('/^\s*>\s?(.*)$/', $line, $match)){
			$flush();
			echo '<blockquote>' . sb_markdown_inline($match[1]) . "</blockquote>\n";
		}elseif(preg_match('/^\s*(?:-{3,}|\*{3,}|_{3,})\s*$/', $line)){
			$flush(); echo "<hr>\n";
		}elseif(trim($line) === "") $flush();
		else $paragraph[] = $line;
	}
	$flush();
	if($list) echo "</$list>\n";
	if($fence) sb_code(implode("\n", $fenceLines), $fenceLanguage);
}

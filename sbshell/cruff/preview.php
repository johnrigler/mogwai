<?php
function sb_preview_type($file){
	$extension = strtolower(pathinfo($file, PATHINFO_EXTENSION));
	if(in_array($extension, ["png", "jpg", "jpeg", "gif", "webp", "svg"])) return "image";
	if(in_array($extension, ["md", "markdown"])) return "markdown";
	if(in_array($extension, ["unixts", "ts", "script"])) return "script";
	return $extension === "pdf" ? "pdf" : "";
}

function sb_preview($file, $url, $lazy = false){
	$type = sb_preview_type($file);
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
	return strtr($text, $literal);
}

function sb_markdown($source){
	$paragraph = [];
	$list = $fence = "";
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
				echo '<pre><code>';
			}elseif($match[1][0] === $fence[0] && strlen($match[1]) >= strlen($fence) && trim($match[2]) === ""){
				echo "</code></pre>\n";
				$fence = "";
			}else echo htmlspecialchars($line, ENT_NOQUOTES | ENT_SUBSTITUTE, "UTF-8") . "\n";
			continue;
		}
		if($fence !== ""){
			echo htmlspecialchars($line, ENT_NOQUOTES | ENT_SUBSTITUTE, "UTF-8") . "\n";
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
	if($fence) echo "</code></pre>\n";
}

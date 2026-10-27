<?php
// Compact, dependency-free syntax highlighting for local files and Markdown fences.
function sb_code_language($file){
	$ext = strtolower(pathinfo($file, PATHINFO_EXTENSION));
	$map = [
		"sh"=>"bash", "bash"=>"bash", "zsh"=>"bash", "ksh"=>"bash",
		"py"=>"python", "rb"=>"ruby", "pl"=>"perl",
		"js"=>"javascript", "mjs"=>"javascript", "cjs"=>"javascript", "jsx"=>"javascript", "tsx"=>"javascript",
		"php"=>"php", "html"=>"html", "htm"=>"html", "xml"=>"html",
		"css"=>"css", "scss"=>"css", "json"=>"json", "jsonl"=>"json",
		"yaml"=>"yaml", "yml"=>"yaml", "toml"=>"ini", "ini"=>"ini", "conf"=>"ini", "cfg"=>"ini",
		"sql"=>"sql", "gd"=>"gdscript", "gdshader"=>"gdscript",
		"c"=>"c", "h"=>"c", "cpp"=>"c", "hpp"=>"c", "rs"=>"rust", "go"=>"go",
		"txt"=>"text", "log"=>"text", "csv"=>"text", "tsv"=>"text", "diff"=>"diff", "patch"=>"diff",
	];
	if(isset($map[$ext])) return $map[$ext];
	$base = strtolower(basename($file));
	if(in_array($base, ["makefile", "dockerfile", "justfile"])) return "bash";
	if(in_array($base, [".gitignore", ".editorconfig"])) return "ini";
	if(is_file($file)){
		$head = @file_get_contents($file, false, null, 0, 256);
		if(is_string($head) && str_starts_with($head, "#!")){
			if(str_contains($head, "python")) return "python";
			if(str_contains($head, "php")) return "php";
			if(str_contains($head, "node")) return "javascript";
			return "bash";
		}
	}
	return "text";
}
function sb_code_escape($value){
	return htmlspecialchars($value, ENT_QUOTES | ENT_SUBSTITUTE, "UTF-8");
}
function sb_code_highlight($source, $language){
	$language = strtolower($language);
	$hash = in_array($language, ["bash", "python", "ruby", "perl", "yaml", "ini", "gdscript"]);
	$comment = match($language){
		"html" => '<!--[\s\S]*?-->',
		"sql" => '--[^\n]*|/\*[\s\S]*?\*/',
		"css" => '\/\*[\s\S]*?\*\/',
		"json", "text", "diff" => '(?!)',
		default => $hash ? '#[^\n]*' : '\/\/[^\n]*|\/\*[\s\S]*?\*\/|(?m:^[ \t]*#[^\n]*)',
	};
	$keywords = [
		"bash" => "if|then|elif|else|fi|for|while|until|do|done|case|esac|in|function|local|export|return|source|declare|readonly|unset|select",
		"python" => "and|as|assert|async|await|break|class|continue|def|del|elif|else|except|False|finally|for|from|global|if|import|in|is|lambda|None|not|or|pass|raise|return|True|try|while|with|yield",
		"javascript" => "async|await|break|case|catch|class|const|continue|default|delete|do|else|export|extends|false|finally|for|from|function|if|import|in|instanceof|let|new|null|of|return|static|super|switch|this|throw|true|try|typeof|undefined|var|void|while|yield|interface|type",
		"php" => "array|as|break|case|catch|class|const|continue|declare|default|do|echo|else|elseif|empty|extends|false|final|finally|fn|for|foreach|function|global|if|include|include_once|instanceof|interface|isset|match|namespace|new|null|private|protected|public|require|require_once|return|static|switch|throw|true|try|use|while",
		"sql" => "alter|and|as|asc|by|case|create|delete|desc|distinct|drop|else|end|exists|from|group|having|in|index|insert|into|is|join|left|like|limit|not|null|on|or|order|outer|primary|right|select|set|table|then|union|update|values|when|where",
		"gdscript" => "and|as|assert|await|break|class|class_name|const|continue|elif|else|enum|extends|false|for|func|if|in|is|match|not|null|or|pass|preload|return|self|signal|static|super|true|var|while",
		"c" => "auto|bool|break|case|char|class|const|continue|default|delete|do|double|else|enum|extern|false|float|for|if|inline|int|long|namespace|new|nullptr|private|protected|public|return|short|signed|sizeof|static|struct|switch|template|this|throw|true|typedef|union|unsigned|using|virtual|void|while",
		"rust" => "as|async|await|break|const|continue|crate|dyn|else|enum|false|fn|for|if|impl|in|let|loop|match|mod|move|mut|pub|ref|return|self|Self|static|struct|super|trait|true|type|unsafe|use|where|while",
		"go" => "break|case|chan|const|continue|default|defer|else|fallthrough|false|for|func|go|goto|if|import|interface|map|nil|package|range|return|select|struct|switch|true|type|var",
	];
	$parts = ["(?P<comment>$comment)"];
	if($language === "json") $parts[] = '(?P<key>"(?:\\\\.|[^"\\\\])*"(?=\s*:))';
	elseif(in_array($language, ["yaml","ini"])) $parts[] = '(?P<key>(?m:^[ \t]*[A-Za-z_][\w.-]*(?=\s*[:=])))';
	elseif($language === "html") $parts[] = '(?P<key></?[A-Za-z][\w:-]*|/?>|\b[\w:-]+(?=\s*=))';
	$parts[] = '(?P<string>"(?:\\\\.|[^"\\\\])*"|\'(?:\\\\.|[^\'\\\\])*\'|\x60(?:\\\\.|[^\x60\\\\])*\x60)';
	if(in_array($language, ["bash","php","javascript","perl","ruby"])) $parts[] = '(?P<variable>\$(?:\{[^}\n]+\}|[A-Za-z_]\w*|[!?@#*$0-9]))';
	if(isset($keywords[$language])) $parts[] = '(?P<keyword>\b(?:' . $keywords[$language] . ')\b)';
	$parts[] = '(?P<number>\b(?:0x[0-9a-fA-F]+|\d+(?:\.\d+)?)\b)';
	$pattern = '~' . implode('|', $parts) . '~im';
	if(!preg_match_all($pattern, $source, $matches, PREG_SET_ORDER | PREG_OFFSET_CAPTURE | PREG_UNMATCHED_AS_NULL)) return sb_code_escape($source);
	$out = ""; $offset = 0;
	foreach($matches as $match){
		$token = $match[0][0]; $start = $match[0][1];
		$out .= sb_code_escape(substr($source, $offset, $start - $offset));
		$class = "";
		foreach(["comment","key","string","variable","keyword","number"] as $type){
			if(isset($match[$type][0]) && $match[$type][1] >= 0){ $class = $type; break; }
		}
		$out .= $class ? '<span class="sb-syn-' . $class . '">' . sb_code_escape($token) . '</span>' : sb_code_escape($token);
		$offset = $start + strlen($token);
	}
	return $out . sb_code_escape(substr($source, $offset));
}
function sb_code($source, $language = "text"){
	$language = strtolower(preg_replace('/[^a-z0-9_+-]/i', '', $language)) ?: "text";
	echo '<div class="sb-code"><div class="sb-code-label">' . sb_code_escape($language) . '</div><pre><code>' . sb_code_highlight($source, $language) . '</code></pre></div>';
}
function sb_code_file($file){
	if(!is_readable($file)){ echo '<p>File cannot be read.</p>'; return; }
	if(filesize($file) > 512 * 1024){ echo '<p>Preview limited to 512 KiB. Open the original file to read it in full.</p>'; return; }
	$source = file_get_contents($file);
	if($source === false || str_contains($source, "\0")){ echo '<p>Binary or unreadable file.</p>'; return; }
	sb_code($source, sb_code_language($file));
}
function sb_code_styles(){
	static $done = false;
	if($done) return;
	$done = true;
	echo '<style>
.sb-code{max-width:100%;margin:1em 0;border:1px solid #344454;border-radius:6px;overflow:hidden;background:#151a20;color:#d6dee6}
.sb-code-label{padding:5px 12px;background:#25303a;color:#adbac6;font:12px/1.5 ui-monospace,monospace}
.sb-code pre{box-sizing:border-box;margin:0;padding:12px 14px;overflow:auto;white-space:pre;tab-size:4;color:inherit;background:transparent;font:14px/1.55 ui-monospace,SFMono-Regular,Consolas,monospace}
.sb-code code{font:inherit;background:transparent;color:inherit;padding:0}
.sb-syn-comment{color:#8594a3;font-style:italic}
.sb-syn-string{color:#a8d59b}
.sb-syn-keyword{color:#c6a0f6;font-weight:600}
.sb-syn-key{color:#8cc9e7}
.sb-syn-variable{color:#e6bd79}
.sb-syn-number{color:#efb681}
@media print{.sb-code{border-color:#777;background:#fff;color:#111}.sb-code-label{background:#eee;color:#333}.sb-code pre{overflow:visible;white-space:pre-wrap;overflow-wrap:anywhere;font-size:9pt}.sb-code span{color:#111!important}}
</style>';
}

<?php
// This file also works as the router passed to php -S.
$sb_root = realpath(($_SERVER["DOCUMENT_ROOT"] ?? "") ?: getcwd());
require_once dirname(__DIR__, 2) . "/profiles/store.php";
$mogwai_profiles_enabled = mogwai_profiles_local();
header("Cache-Control: no-store");
if(isset($_GET["mogwai-profiles"])){
	include dirname(__DIR__, 2) . "/profiles/index.php";
	exit();
}
if(isset($_GET["mogwai-signatures"])){
	include dirname(__DIR__, 2) . "/signatures/index.php";
	exit();
}
if(isset($_GET["sb-check"])){
	require_once __DIR__ . "/check.php";
	sb_php_setup_page($sb_root);
	exit();
}
require_once __DIR__ . "/catalog.php";
if(isset($_GET["document"])){
	try{
		if(!is_string($_GET["document"])) throw new RuntimeException("Enter a document name.", 400);
		$file = sb_document_path($_GET["document"]);
		$path = substr($file, strlen($sb_root) + 1);
		$url = "/" . implode("/", array_map("rawurlencode", explode("/", $path)));
		header("Location: " . $url . (isset($_GET["raw"]) ? "?raw=1" : ""));
	}catch(Throwable $error){
		http_response_code(in_array($error->getCode(), [400,404,409]) ? $error->getCode() : 500);
		echo htmlspecialchars($error->getMessage());
	}
	exit();
}
$sb_path = rawurldecode(explode("?", $_SERVER["REQUEST_URI"] ?? "/", 2)[0]);
if(in_array("..", explode("/", $sb_path), true) || str_contains($sb_path, "\0")){
	http_response_code(404);
	exit("Directory not found.");
}
$sb_target = realpath($sb_root . $sb_path);
$sb_index = $sb_target === __FILE__;
if($sb_index){
	// A symlinked index belongs to its URL directory, not this source directory.
	$sb_path = dirname($sb_path);
	$sb_target = realpath($sb_root . $sb_path);
}elseif(PHP_SAPI === "cli-server" && is_file($sb_target ?: "")){
	if(strtolower(pathinfo($sb_path, PATHINFO_EXTENSION)) === "pdf" && !isset($_GET["raw"])){
		include __DIR__ . "/document.php";
		exit();
	}
	return false;
}
if(!$sb_target || !is_dir($sb_target) || !chdir($sb_target)){
	http_response_code(404);
	exit("Directory not found.");
}
$sb_parts = array_values(array_filter(explode("/", $sb_path), fn($part) => $part !== "" && $part !== "."));
$sb_url = "/";
foreach($sb_parts as $part) $sb_url .= rawurlencode($part) . "/";
if(!$sb_index && !str_ends_with($sb_path, "/")){
	$query = $_SERVER["QUERY_STRING"] ?? "";
	header("Location: " . $sb_url . ($query === "" ? "" : "?" . $query));
	exit();
}
if(isset($_GET["sb-refresh"])){
	header("Content-Type: application/json; charset=utf-8");
	header("Cache-Control: no-store");
	try { echo json_encode(["stamp" => sb_directory_stamp($sb_target)]); }
	catch(Throwable $error){ http_response_code(503); echo json_encode(["error" => $error->getMessage()]); }
	exit();
}
if(isset($_GET["sb-clipboard"])){
	header("Content-Type: application/json; charset=utf-8");
	header("Cache-Control: no-store");
	try{
		if(($_SERVER["REQUEST_METHOD"] ?? "GET") !== "POST") throw new RuntimeException("Use Copy selected to save the clipboard.", 405);
		if(strtolower(trim(explode(";", $_SERVER["CONTENT_TYPE"] ?? "")[0])) !== "application/json"){
			throw new RuntimeException("Send the selection as JSON.", 415);
		}
		$origin = $_SERVER["HTTP_ORIGIN"] ?? "";
		$scheme = !empty($_SERVER["HTTPS"]) && $_SERVER["HTTPS"] !== "off" ? "https" : "http";
		if(($origin && strtolower(rtrim($origin, "/")) !== $scheme . "://" . strtolower($_SERVER["HTTP_HOST"]))
			|| ($_SERVER["HTTP_SEC_FETCH_SITE"] ?? "") === "cross-site"){
			throw new RuntimeException("Copy the selection from this archive's own page.", 403);
		}
		$input = json_decode(file_get_contents("php://input"), true, 512, JSON_THROW_ON_ERROR);
		require_once __DIR__ . "/clipboard.php";
		$count = sb_save_clipboard(ltrim(rawurldecode($sb_url), "/"), $input["files"] ?? null);
		echo json_encode(["count" => $count]);
	}catch(Throwable $error){
		$status = $error instanceof JsonException ? 400 : $error->getCode();
		http_response_code(in_array($status, [400,403,405,409,415]) ? $status : 500);
		if($status === 405) header("Allow: POST");
		echo json_encode(["error" => $error instanceof JsonException ? "Invalid selection JSON." : $error->getMessage()]);
	}
	exit();
}

// A numbered page contains its ordered sections, regardless of the source format.
$sb_pages = [];
foreach(glob("[0-9]*_*.*") ?: [] as $file){
	if(!is_file($file) || !preg_match('/^([0-9]+)_([0-9]+)\\.[^.]+$/', $file, $number)) continue;
	$sb_pages[(int)$number[1]][(int)$number[2]][] = $file;
}
ksort($sb_pages, SORT_NUMERIC);
foreach($sb_pages as &$sections){
	ksort($sections, SORT_NUMERIC);
	foreach($sections as &$files) sort($files, SORT_NATURAL);
	unset($files);
}
unset($sections);
$sb_page_numbers = array_keys($sb_pages);
$sb_page = $sb_page_numbers[0] ?? 1;
if(isset($_GET["page"]) && is_string($_GET["page"]) && ctype_digit($_GET["page"])
	&& isset($sb_pages[(int)$_GET["page"]])) $sb_page = (int)$_GET["page"];
$sb_page_at = array_search($sb_page, $sb_page_numbers, true);
$sb_prev = $sb_page_numbers[$sb_page_at - 1] ?? null;
$sb_next = $sb_page_numbers[$sb_page_at + 1] ?? null;
require_once __DIR__ . "/preview.php";
$sb_dirs = $sb_files = [];
$sb_names = [];
$sb_catalog_error = "";
try{
	sb_catalog_scan(rtrim($sb_root . rawurldecode($sb_url), "/") ?: "/");
}catch(Throwable $error){ $sb_catalog_error = $error->getMessage(); }
try { $sb_names = sb_document_names(); } catch(Throwable $error) { $sb_catalog_error = $error->getMessage(); }
$sb_stamp = "";
try { $sb_stamp = sb_directory_stamp($sb_target); } catch(Throwable $error) { /* Retry on the next directory load. */ }
foreach(scandir(".") as $file){
	if($file[0] === "." || realpath($file) === __FILE__) continue;
	if($file === "catalog.sqlite3" || str_starts_with($file, "catalog.sqlite3-")) continue;
	if(is_dir($file)) $sb_dirs[] = $file . "/";
	elseif(is_file($file)) $sb_files[] = $file;
}
?>
<!doctype html>
<html>
<head>
 <meta http-equiv="content-type" content="text/html;charset=UTF-8">
 <meta name="viewport" content="width=device-width,initial-scale=1">
 <title>John Rigler</title>
 		<link rel="stylesheet" type="text/css" href="/style.css">

</head>
<body>
<style>
.sb-navigation, .refresh-control { font:14px/1.5 system-ui,sans-serif; color:#273749; margin:10px 16px; }
.sb-navigation a { color:#135da8; text-decoration:underline; }
.sb-navigation summary { cursor:pointer; }
.sb-toolbar { position:sticky; top:0; z-index:100; background:#fff; border-bottom:1px solid #d1d5da; padding:4px 0; }
.sb-toolbar .sb-navigation, .sb-toolbar .refresh-control { margin:6px 16px; }
.sb-toolbar-top { display:flex; align-items:center; gap:8px; }
.sb-toolbar-top .sb-breadcrumbs { min-width:0; overflow-wrap:anywhere; }
.sb-menu { position:relative; flex-shrink:0; margin:0 16px 0 auto; font:14px/1.5 system-ui,sans-serif; }
.sb-menu > summary { display:flex; align-items:center; justify-content:center; width:36px; height:36px; list-style:none; cursor:pointer; font-size:24px; background:#fff; border:1px solid #d1d5da; border-radius:4px; }
.sb-menu > summary::-webkit-details-marker { display:none; }
.sb-menu > summary:focus-visible { outline:2px solid #135da8; outline-offset:2px; }
.sb-menu-links { position:absolute; right:0; top:calc(100% + 4px); min-width:210px; background:#fff; border:1px solid #d1d5da; border-radius:4px; box-shadow:0 4px 12px #0002; }
.sb-menu-links a { display:block; padding:10px 14px; color:#135da8; text-decoration:none; }
.sb-menu-links a:hover, .sb-menu-links a:focus-visible { background:#eef2f6; }
.sb-menu-links .refresh-control { margin:0; padding:10px 14px; border-top:1px solid #d1d5da; }
.sb-menu-links .refresh-control label { display:flex; align-items:flex-start; gap:6px; cursor:pointer; }
.sb-menu-links .refresh-control input { flex-shrink:0; margin:4px 0 0; }
.sb-file-controls { display:flex; flex-wrap:wrap; align-items:center; gap:6px; margin:6px 16px; font:14px/1.5 system-ui,sans-serif; }
.sb-file-controls[hidden] { display:none; }
.sb-file-controls button { font:inherit; padding:5px 10px; cursor:pointer; }
.sb-file-controls button:disabled { opacity:.5; cursor:default; }
#sb-selected-count { margin-left:auto; color:#526170; }
#sb-clipboard-status { color:#526170; overflow-wrap:anywhere; }
#sb-clipboard-status[data-error] { color:#9c2424; }
.sb-table { width:100%; table-layout:fixed; border-collapse:collapse; margin-top:10px; }
.sb-table th, .sb-table td { padding:8px; border-bottom:1px solid #ddd; text-align:left; vertical-align:top; overflow-wrap:anywhere; }
.sb-table th { background:#e6e6e6; font-weight:600; }
.sb-table tbody > tr:nth-child(odd) { background:#fff; }
.sb-table tbody > tr:nth-child(even) { background:#f1f1f1; }
.sb-table .sb-selection { width:38px; text-align:center; }
.sb-select-label { display:flex; align-items:center; justify-content:center; min-height:32px; cursor:pointer; }
.sb-select { width:18px; height:18px; margin:0; cursor:pointer; }
.sb-table .sb-tags { width:20%; color:#526170; }
.sb-file > a { display:inline-block; padding:6px 0; }
.sb-file small { color:#526170; }
.sb-entry { margin:0; }
.sb-entry > summary { padding:6px 0; }
.sb-preview { min-width:0; padding:8px 0 16px; }
.sb-file-actions { margin:4px 0 10px; }
.sb-image, .sb-markdown img { max-width:100%; height:auto; }
.sb-image:not([src]) { display:none; }
.sb-pdf { display:block; width:100%; height:75vh; min-height:320px; border:1px solid #b8c3cf; }
.sb-pdf-fallback { height:auto; min-height:0; padding:0 12px; box-sizing:border-box; }
.sb-markdown { box-sizing:border-box; color:#253341; font:16px/1.7 system-ui,sans-serif; max-width:85ch; padding:8px 4px 24px; }
.sb-markdown h1,.sb-markdown h2,.sb-markdown h3,.sb-markdown h4 { color:#173c5b; line-height:1.3; margin:1.45em 0 .55em; font-weight:700; }
.sb-markdown h1 { font-size:1.9em; padding-bottom:.25em; border-bottom:2px solid #b5c9d9; }
.sb-markdown h2 { font-size:1.45em; padding-bottom:.25em; border-bottom:1px solid #d1dce5; }
.sb-markdown h3 { font-size:1.2em; }
.sb-markdown p { margin:.85em 0 1.1em; }
.sb-markdown a { color:#0d63a6; text-decoration-color:#8ab5d4; text-underline-offset:2px; }
.sb-markdown ul,.sb-markdown ol { margin:.65em 0 1.1em; padding-left:1.8em; }
.sb-markdown li { padding-left:.12em; }
.sb-markdown li + li { margin-top:.25em; }
.sb-markdown :not(pre) > code { color:#873d65; background:#edf1f5; border-radius:3px; padding:.1em .3em; font: .88em ui-monospace,SFMono-Regular,Consolas,monospace; overflow-wrap:anywhere; }
.sb-markdown pre { padding:12px; background:#eef2f6; overflow:auto; white-space:pre; }
.sb-markdown blockquote { margin:1.25em 0; padding:.15em 1.1em; color:#506477; background:#f2f6f9; border-left:4px solid #7ea9c7; }
.sb-markdown blockquote p { margin:.4em 0; }
.sb-markdown hr { border:0; border-top:1px solid #cbd7e0; margin:2em 0; }
.sb-markdown table { border-collapse:collapse; margin:1.2em 0; width:100%; display:block; overflow-x:auto; font-size:.94em; }
.sb-markdown th,.sb-markdown td { padding:7px 11px; border:1px solid #d0d9e2; text-align:left; }
.sb-markdown th { color:#173c5b; background:#e9f0f5; }
.sb-markdown tr:nth-child(even) { background:#f7f9fb; }
.sb-markdown .sb-code pre { background:transparent; }

.sb-catalog-error { margin:10px 16px; color:#9c2424; font:14px/1.5 system-ui,sans-serif; }
.sb-document { max-width:960px; margin:20px auto 64px; padding:0 18px; color:#263443; }
.sb-document > h1 { font:700 26px/1.3 system-ui,sans-serif; margin:12px 0 8px; }
.sb-page-nav { display:flex; align-items:center; gap:16px; flex-wrap:wrap; margin:14px 0; padding:10px 0; font:14px/1.4 system-ui,sans-serif; border-block:1px solid #d1d5da; }
.sb-page-nav a { color:#135da8; }
.sb-page-nav [aria-disabled] { color:#84919e; }
.sb-page-nav strong { font-weight:600; margin-right:auto; }
.sb-section-nav { display:flex; flex-wrap:wrap; gap:8px; margin:18px 0 28px; font:14px system-ui,sans-serif; }
.sb-section-nav a { display:inline-block; padding:5px 10px; color:#135da8; border:1px solid #c1cdd9; border-radius:4px; text-decoration:none; }
.sb-numbered-section { margin:28px 0 36px; scroll-margin-top:80px; }
.sb-numbered-section > h2 { display:flex; align-items:baseline; flex-wrap:wrap; gap:12px; font:600 20px/1.4 system-ui,sans-serif; border-bottom:1px solid #cbd6df; padding-bottom:6px; }
.sb-numbered-section > h2 small { font:13px/1.4 ui-monospace,monospace; color:#637384; }

@media (max-width:500px) {
  .sb-navigation, .sb-toolbar .sb-navigation, .sb-toolbar .refresh-control, .sb-file-controls { margin-left:6px; margin-right:6px; }
  .sb-menu { margin-right:6px; }
  .sb-table th, .sb-table td { padding:6px 4px; }
  .sb-table .sb-selection { width:30px; }
  .sb-table .sb-tags { width:58px; }
}
@media print {
  .sb-page-nav, .sb-section-nav { display:none !important; }
  .sb-document { max-width:none; margin:0; padding:0; }
  .sb-numbered-section { break-inside:auto; }
  .sb-numbered-section > h2 { break-after:avoid; }
  .sb-toolbar, .sb-assembled-files, .sb-directory > summary, .sb-table thead,
  .sb-selection, .sb-tags, .sb-file-actions, .sb-entry:not([open]), .sb-catalog-error { display:none !important; }
  .sb-directory { margin:0; padding:0; }
  .sb-table, .sb-table tbody, .sb-table tr, .sb-table td.sb-file { display:block; width:auto; margin:0; padding:0; border:0; background:transparent !important; }
  .sb-table tbody > tr:not(:has(.sb-entry[open])) { display:none; }
  .sb-entry > summary { font-weight:bold; }
  .sb-navigation { color:#000; }
  .sb-markdown pre { white-space:pre-wrap; overflow-wrap:anywhere; }
}
</style>
<header class="sb-toolbar">
<div class="sb-toolbar-top">
<nav class="sb-navigation sb-breadcrumbs" aria-label="Breadcrumbs">
<?php
$sb_crumbs = ["/" => basename($sb_root) ?: "Home"];
$sb_link = "/";
foreach($sb_parts as $part){
	$sb_link .= rawurlencode($part) . "/";
	$sb_crumbs[$sb_link] = $part;
}
foreach($sb_crumbs as $link => $label){
	if($link !== "/") echo ' <span aria-hidden="true">/</span> ';
	if($link === $sb_url) echo '<span aria-current="page">' . htmlspecialchars($label) . '</span>';
	else echo '<a href="' . $link . '">' . htmlspecialchars($label) . '</a>';
}
?>
</nav>
<details class="sb-menu" id="sb-menu">
<summary aria-label="Menu" title="Menu"><span aria-hidden="true">☰</span></summary>
<nav class="sb-menu-links" aria-label="Settings">
<?php if($mogwai_profiles_enabled){ ?><a href="<?= $sb_url ?>?mogwai-profiles=1&amp;return=<?= rawurlencode($sb_url) ?>">People and correspondence</a><?php } ?>
<?php if($mogwai_profiles_enabled){ ?><a href="<?= $sb_url ?>?mogwai-signatures=1">Signing identities</a><?php } ?>
<a href="<?= $sb_url ?>?sb-check=1">PHP setup</a>
<div class="refresh-control">
<label><input type="checkbox" id="auto-refresh" data-stamp="<?php echo $sb_stamp; ?>" checked><span>Auto-refresh<br><small>Check every 10 seconds</small></span></label>
</div>
</nav>
</details>
</div>
<div class="sb-file-controls" id="sb-file-controls" role="group" aria-label="Directory controls" hidden>
<button type="button" id="sb-select-all">Select all</button>
<button type="button" id="sb-unselect-all">Unselect all</button>
<button type="button" id="sb-copy-selected" disabled>Copy selected</button>
<button type="button" id="sb-expand-selected" disabled>Expand selected</button>
<button type="button" id="sb-expand-all">Expand all</button>
<button type="button" id="sb-collapse-all">Collapse all</button>
<span id="sb-clipboard-status" role="status" aria-live="polite"></span>
<span id="sb-selected-count" role="status" aria-live="polite">0 selected</span>
</div>
</header>
<?php if($sb_catalog_error){ ?>
<p class="sb-catalog-error" role="status">Catalog update failed: <?php echo htmlspecialchars($sb_catalog_error); ?> <a href="<?= $sb_url ?>?sb-check=1">Check PHP setup</a>.</p>
<?php } ?>
<details class="sb-navigation sb-directory<?php if($sb_pages) echo ' sb-assembled-files'; ?>" id="sb-directory"<?php if(!$sb_pages) echo " open"; ?>>
<summary>Files and directories</summary>
<?php if($sb_dirs || $sb_files){ ?>
<table class="sb-table" aria-label="Files and directories">
<thead><tr><th scope="col" class="sb-selection">Select</th><th scope="col">File or directory</th><th scope="col" class="sb-tags">Tags</th></tr></thead>
<tbody>
<?php
foreach(array_merge($sb_dirs, $sb_files) as $file){
	$link = $sb_url . rawurlencode(rtrim($file, "/")) . (str_ends_with($file, "/") ? "/" : "");
	$relative = ltrim(rawurldecode($sb_url), "/") . $file;
	$label = $sb_names[$relative] ?? $file;
	echo '<tr><td class="sb-selection"><label class="sb-select-label"><input type="checkbox" class="sb-select" value="' . htmlspecialchars($file) . '" aria-label="Select ' . htmlspecialchars($label) . '"></label></td><td class="sb-file">';
	if(is_file($file) && sb_preview_type($file)){
		echo '<details class="sb-entry" data-file="' . htmlspecialchars($file) . '"><summary>' . htmlspecialchars($label);
		if($label !== $file) echo ' <small>(' . htmlspecialchars($file) . ')</small>';
		echo '</summary><div class="sb-preview"><p class="sb-file-actions"><a href="' . $link . '">Open file</a>';
		if(sb_preview_type($file) === "pdf") echo ' · <a href="' . $link . '?raw=1" target="_blank" rel="noopener">Open original PDF / print</a>';
		echo '</p>';
		sb_preview($file, rawurlencode($file), true);
		echo '</div></details>';
	}else{
		echo '<a href="' . $link . '">' . htmlspecialchars($label) . '</a>';
		if($label !== $file) echo ' <small>(' . htmlspecialchars($file) . ')</small>';
	}
	echo '</td><td class="sb-tags"></td></tr>' . "\n";
}
?>
</tbody></table>
<?php }else{ ?>
<p>This directory is empty.</p>
<?php } ?>
</details>
<script>
<?php readfile(__DIR__ . "/directory.js"); ?>
</script>
<?php
if($sb_pages){
	// Previous/Next move between numbered pages; the individual files are sections.
	$sb_pager = '<nav class="sb-page-nav" aria-label="Page navigation">';
	$sb_pager .= $sb_prev === null ? '<span aria-disabled="true">← Previous</span>'
		: '<a href="' . $sb_url . '?page=' . $sb_prev . '">← Previous</a>';
	$sb_pager .= '<strong>Page ' . $sb_page . ' of ' . count($sb_page_numbers) . '</strong>';
	$sb_pager .= $sb_next === null ? '<span aria-disabled="true">Next →</span>'
		: '<a href="' . $sb_url . '?page=' . $sb_next . '">Next →</a>';
	$sb_pager .= '</nav>';
?>
<article class="sb-document">
<h1>Page <?= $sb_page ?></h1>
<?= $sb_pager ?>
<nav class="sb-section-nav" aria-label="Sections">
<?php foreach($sb_pages[$sb_page] as $number => $files){ ?>
<a href="#sb-part-<?= $sb_page ?>-<?= $number ?>"><?= str_pad((string)$number, 2, "0", STR_PAD_LEFT) ?></a>
<?php } ?>
</nav>
<?php foreach($sb_pages[$sb_page] as $number => $files){ ?>
<section class="sb-numbered-section" id="sb-part-<?= $sb_page ?>-<?= $number ?>">
<h2><span>Section <?= str_pad((string)$number, 2, "0", STR_PAD_LEFT) ?></span>
<small><?= htmlspecialchars(implode(" · ", $files), ENT_QUOTES | ENT_SUBSTITUTE, "UTF-8") ?></small></h2>
<?php foreach($files as $file){
	// PHP parts are authored output fragments, not highlighted source previews.
	if(strtolower(pathinfo($file, PATHINFO_EXTENSION)) === "php") include $file;
	elseif(sb_preview_type($file)) sb_preview($file, rawurlencode($file));
	else echo '<p><a href="' . htmlspecialchars(rawurlencode($file), ENT_QUOTES) . '">Open ' . htmlspecialchars($file, ENT_QUOTES | ENT_SUBSTITUTE, "UTF-8") . '</a></p>';
} ?>
</section>
<?php } ?>
<?= $sb_pager ?>
</article>
<?php } ?>
</body>
</html>
<?php
exit();
?>


<?php

function typescript_color( $a ,$b ){  

echo "[$a;$b]";
}

// Clear session information

unset($_SESSION['host']);
unset($_SESSION['W']);
?>

<!-- Begin Menu Choices -->
<div class=contentsframe>

<table>
<tr><td>John Rigler<td><?php include "banner.php"; ?>
</table>
<br>
<br>
<br>

<?php
// map this directory

$dir = opendir(".");

while(false != ($file = readdir($dir))) 
{
if($file == "images")continue;
if($file == "hide")continue;
if($file == "cgi-bin")continue;
if($file == ".")continue;
if($file == "..")continue;

$files [] = $file;
}

sort($files);

foreach($files as $file)
{

if(is_dir($file) == 1)$dirs [] = $file;
if(is_file($file) == 1)
  if(is_numeric($file[0]))
    {
    $files [] = $file;
    $sections[$file[0]] []= $file;
    }

}

// Read the format 

$format=($_GET[format]);

// figure out what page this is. 

$thispage=($_GET[page]);

if (! $thispage)$thispage=1;

if($thispage==1)
   {
   $nextpage = 2;
   }
   else
   {
   $nextpage = $thispage + 1;
   $prevpage = $thispage - 1;
   }

// Draw out the path

$length = strlen($_SERVER[DOCUMENT_ROOT]);
$cwd = getcwd();

if ($cwd[1] == ":") 
	{
	$path = explode('\\',substr($cwd,$length));
	}
	else
	{
	$path = explode('/',substr($cwd,$length));
	}

if($format != "htmldoc")
{
foreach($path as $index => $directory)
  {
  $countup = 0;
  $urlpath [] = "/" . $directory;
  echo "<div class=shortspacing style='float:left'>
   <div class=contentsbox>
      <a href=";
  while($countup <= $index)
	{
	$trimmed = $urlpath[$countup];
	echo $trimmed;
	if($index == 0)
		{ 
		$urlpath[0] = "";
		$directory = "home";
		}
		
	$countup++;
	}

	echo " style=color:white> $directory</a> 
    </div>
  </div>
";

	if ($countup > 3)echo "</div><div class=contentsbox>";
  } 
}

//echo "</div>";




?>
</div>

<!-- End Menu Choices -->

<!-- Begin Table of Contents -->

<?php 

if(count($dirs) > 0)
  {
  echo "<div class=contentsframe>";
  foreach($dirs as $subdir)
   {

?>
  <!-- Begin Table of Contents Entry -->
  <div class=shortspacing>
    <div class=contentsbox><a style='color:white' href=<?php echo "$subdir > $subdir"; ?></a></div>

  </div>
  <div class=spacing>
  <p><?php if( file_exists("$subdir/desc.php"))include "$subdir/desc.php"; ?></p>
  <hr>
  <!-- End Table of Contents Entry -->

  </div>
<?php   } ?>
</div>
<?php } ?>

<!-- End Table of Contents -->

<div style='border:none;background-color: transparent'>

<?php 
if($format != "htmldoc")
{
 if($sections[$prevpage])
	$visibility="visible";
	else
	$visibility="hidden";

	echo "<div class=shortspacing style='float:left;visibility: $visibility '>
      <div class=contentsbox>
    <a href=?page=$prevpage style='color:white'> Prev </a>
      </div>
   </div>";


if($sections[$nextpage])
        $visibility="visible";
        else
        $visibility="hidden";

  echo "<div class=shortspacing style='border:none;float:left;visibility: $visibility '>
      <div class=contentsbox style='border:none'>
      <a href=?page=$nextpage style='color:white'> Next </a>
      </div>
   </div>
</div>";
}

?>

<!-- End Forward/Back Choices -->


  <!-- Begin Body -->


<?php

//   }


if($sections[$thispage])
{
echo "<div class=bodyframe>";


$before = array("[0m","[40;31;01m","[01;32m","[01;34m","[01;36m" );
$after = array("</span>","<span class=color40_31_01>","<span class=color32>","<span class=color34>","<span class=color36>");
$colors = array();
$target = array();

$colors[0] ="";
$colors[31]="[31m";
$colors[32]="[32m";
$colors[33]="[33m";
$colors[99]="[00m";
$target[31]="<span class=color31>";
$target[32]="<span class=color32>";
$target[33]="<span class=color33>";
$target[99]="</span>";

foreach ($sections[$thispage] as $file)
  {
  list($prefix,$postfix) = explode(".",$file);
  list($page,$section) = explode("-",$prefix);
  if($page == $thispage)
  {
    if($postfix == "ts")
      {
      echo "<pre>";
			$lines = file($file);
      foreach ($lines as $line)
        {
				//typescript_color(4,5);
        $line = str_replace($before,$after,$line);
        $line = str_replace($colors,$target,$line);
 				echo "$line<span class=normal>";
        }
      echo "</pre>";
      }

    if($postfix == "php")
        {
        if($format != "htmldoc")echo "<div class=spacing><span class=section>$section</span>";
        include "$file";
        echo "</div>";
        }
    if($postfix == "png")
        if($format != "htmldoc")echo "
<div class=spacing><span class=section>$section</span>
  <div>
   <img src=$file>
  </div>
</div>
";
   }
  }
 }

echo "<pre>";
print_r($_SESSION);
echo "</pre>";

?>
   </div>
 </div>
</body>
</html>

<?php
$sb_relative = implode("/", array_filter(explode("/", $sb_path), fn($part) => $part !== "" && $part !== "."));
$sb_file_url = "/" . implode("/", array_map("rawurlencode", explode("/", $sb_relative)));
$sb_digest = hash_file("sha256", $sb_target, true);
$sb_name = "";
$sb_error = "";
try{
	if(!class_exists("SQLite3")) throw new RuntimeException("Enable PHP's SQLite3 extension to save and use document names.");
	$names = sb_document_names();
	$sb_name = $names[$sb_relative] ?? "";
	if(($_SERVER["REQUEST_METHOD"] ?? "GET") === "POST"){
		if(!is_string($_POST["name"] ?? null) || !is_string($_POST["sha256"] ?? null)){
			throw new RuntimeException("Enter a document name and reload the page before saving.", 400);
		}
		$sb_name = trim($_POST["name"]);
		$origin = $_SERVER["HTTP_ORIGIN"] ?? "";
		$scheme = !empty($_SERVER["HTTPS"]) && $_SERVER["HTTPS"] !== "off" ? "https" : "http";
		if(($origin && strtolower(rtrim($origin, "/")) !== $scheme . "://" . strtolower($_SERVER["HTTP_HOST"]))
			|| ($_SERVER["HTTP_SEC_FETCH_SITE"] ?? "") === "cross-site"){
			throw new RuntimeException("Save the name from this document's own page.", 403);
		}
		if(!hash_equals(bin2hex($sb_digest), (string)($_POST["sha256"] ?? ""))){
			throw new RuntimeException("The file changed while this page was open. Reload it before saving.", 409);
		}
		sb_save_document($sb_relative, $sb_name, $sb_digest);
		header("Location: " . $sb_file_url . "?saved=1", true, 303);
		exit();
	}
}catch(Throwable $error){
	$sb_error = $error->getMessage();
	if(($_SERVER["REQUEST_METHOD"] ?? "GET") === "POST"){
		http_response_code(in_array($error->getCode(), [400,403,409]) ? $error->getCode() : 500);
	}
}
$sb_parts = explode("/", $sb_relative);
$sb_crumbs = ["/" => basename($sb_root) ?: "Home"];
$sb_link = "/";
foreach($sb_parts as $index => $part){
	$sb_link .= rawurlencode($part) . ($index < count($sb_parts) - 1 ? "/" : "");
	$sb_crumbs[$sb_link] = $part;
}
?>
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title><?php echo htmlspecialchars($sb_name ?: basename($sb_target)); ?></title>
<style>
* { box-sizing:border-box; }
body { margin:0; height:100vh; display:flex; flex-direction:column; font:15px/1.5 system-ui,sans-serif; color:#243449; background:#eef2f6; }
header { padding:12px 20px; background:white; border-bottom:1px solid #cbd5e1; }
nav { font-size:13px; overflow-wrap:anywhere; margin-bottom:10px; }
a { color:#135da8; }
form { display:flex; align-items:end; flex-wrap:wrap; gap:10px; }
label { flex:1 1 260px; max-width:600px; }
input { display:block; width:100%; font:inherit; padding:7px 10px; border:1px solid #8c9caf; border-radius:4px; }
button { font:inherit; padding:8px 20px; border:0; border-radius:4px; background:#135da8; color:white; cursor:pointer; }
.actions { display:flex; gap:16px; flex-wrap:wrap; margin-top:8px; font-size:13px; }
.status { margin:8px 0 0; font-size:13px; }
.error { color:#9c2424; }
iframe { flex:1; width:100%; min-height:320px; border:0; }
@media print { header { display:none !important; } body { height:auto; } iframe { height:100vh; } }
</style>
</head>
<body>
<header>
<nav aria-label="Breadcrumbs">
<?php
foreach($sb_crumbs as $link => $label){
	if($link !== "/") echo ' <span aria-hidden="true">/</span> ';
	if($link === $sb_file_url) echo '<span aria-current="page">' . htmlspecialchars($label) . '</span>';
	else echo '<a href="' . $link . '">' . htmlspecialchars($label) . '</a>';
}
?>
</nav>
<form method="post" action="<?php echo $sb_file_url; ?>">
<label>Document name
<input name="name" value="<?php echo htmlspecialchars($sb_name); ?>" maxlength="200" placeholder="Give this document a name" required>
</label>
<input type="hidden" name="sha256" value="<?php echo bin2hex($sb_digest); ?>">
<button type="submit">Save name</button>
</form>
<?php if($sb_error){ ?>
<p class="status error" role="alert"><?php echo htmlspecialchars($sb_error); ?></p>
<?php }elseif(isset($_GET["saved"])){ ?>
<p class="status" role="status">Name saved.</p>
<?php } ?>
<div class="actions">
<a href="<?php echo $sb_file_url; ?>?raw=1" target="_blank" rel="noopener">Open original PDF / print</a>
<?php if($sb_name && !$sb_error){ ?>
<a href="/?document=<?php echo rawurlencode($sb_name); ?>">Reference by name</a>
<?php } ?>
</div>
</header>
<iframe src="<?php echo $sb_file_url; ?>?raw=1" title="<?php echo htmlspecialchars($sb_name ?: basename($sb_target)); ?>"></iframe>
</body>
</html>

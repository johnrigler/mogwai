<?php
// File viewer for shell source requested through the PHP development-server router.
// The original bytes remain available through ?raw=1.
require_once __DIR__ . "/preview.php";
$sb_file_url = "/" . implode("/", array_map("rawurlencode", array_values(array_filter(explode("/", $sb_path), fn($part) => $part !== ""))));
$sb_parent_url = dirname($sb_file_url);
if($sb_parent_url !== "/") $sb_parent_url .= "/";
$sb_title = basename($sb_target);
header("Content-Type: text/html; charset=utf-8");
?>
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title><?= htmlspecialchars($sb_title, ENT_QUOTES | ENT_SUBSTITUTE, "UTF-8") ?> · SB Shell</title>
<style>
body { margin:0; padding:0; font:15px/1.5 system-ui,sans-serif; background:#eef2f6; color:#243449; }
header { display:flex; align-items:center; gap:18px; flex-wrap:wrap; padding:12px 20px; background:#fff; border-bottom:1px solid #cbd5e1; }
header strong { overflow-wrap:anywhere; }
a { color:#135da8; }
main { max-width:1150px; margin:16px auto; padding:0 16px 24px; }
main .sb-code { margin:0; }
@media print { header { display:none; } body { background:#fff; } main { max-width:none; margin:0; padding:0; } }
</style>
</head>
<body>
<header>
<a href="<?= htmlspecialchars($sb_parent_url, ENT_QUOTES | ENT_SUBSTITUTE, "UTF-8") ?>">← Directory</a>
<strong><?= htmlspecialchars($sb_title, ENT_QUOTES | ENT_SUBSTITUTE, "UTF-8") ?></strong>
<a href="<?= htmlspecialchars($sb_file_url, ENT_QUOTES | ENT_SUBSTITUTE, "UTF-8") ?>?raw=1">Raw file</a>
</header>
<main>
<?php sb_code_styles(); sb_code_file($sb_target); ?>
</main>
</body>
</html>

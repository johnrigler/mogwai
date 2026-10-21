<?php
require_once __DIR__ . "/store.php";
if(!mogwai_profiles_local()){
	http_response_code(403); exit("Open People and correspondence through the local Mogwai listener.");
}
header("Cache-Control: no-store");
header("X-Frame-Options: DENY");
header("Content-Security-Policy: frame-ancestors 'none'; form-action 'self'");
header("Referrer-Policy: no-referrer");
session_name("mogwai_profiles");
session_start(["cookie_httponly" => true, "cookie_samesite" => "Strict", "use_strict_mode" => true]);
$_SESSION["csrf"] ??= bin2hex(random_bytes(32));
$escape = fn($value) => htmlspecialchars((string)$value, ENT_QUOTES | ENT_SUBSTITUTE, "UTF-8");
$back = $_GET["return"] ?? "/";
if(!is_string($back) || !str_starts_with($back,"/") || str_starts_with($back,"//") || preg_match('/[\x00-\x20\\\\]/', $back)) $back = "/";
$message = $error = "";
if(($_SERVER["REQUEST_METHOD"] ?? "GET") === "POST"){
	$origin = $_SERVER["HTTP_ORIGIN"] ?? "";
	$scheme = !empty($_SERVER["HTTPS"]) && $_SERVER["HTTPS"] !== "off" ? "https" : "http";
	$token = $_POST["csrf"] ?? "";
	if(!is_string($token) || !hash_equals($_SESSION["csrf"],$token)
		|| ($origin !== "" && strtolower($origin) !== $scheme . "://" . strtolower($_SERVER["HTTP_HOST"]))
		|| ($_SERVER["HTTP_SEC_FETCH_SITE"] ?? "") === "cross-site"){
		http_response_code(403); exit("Reload this local form before saving.");
	}
	try{ mogwai_profiles_save($_POST); $message = "Saved. Return to the letter to load the saved values."; }
	catch(InvalidArgumentException $problem){ http_response_code(400); $error = $problem->getMessage(); }
	catch(Throwable $problem){ http_response_code(500); $error = "Could not save the home database. Check its location, permissions and PHP SQLite3 support."; }
}
try{ $data = mogwai_profiles_read(); $database = mogwai_home_db_path(); }
catch(Throwable $problem){
	http_response_code(500);
	exit("Cannot open home profiles. Check HOME, MOGWAI_HOME_DB, the database location and PHP SQLite3 support.");
}
// Keep a rejected form editable without changing the stored record.
if($error !== ""){
	foreach(MOGWAI_PEOPLE as $id => $label){
		foreach(MOGWAI_PERSON_FIELDS as $key){
			$value = $_POST["people"][$id][$key] ?? null;
			if(is_string($value)) $data["people"][$id][$key] = $value;
		}
	}
	foreach(MOGWAI_LETTER_FIELDS as $key){
		$value = $_POST["letter"][$key] ?? null;
		if(is_string($value)) $data["letter"][$key] = $value;
	}
}
?>
<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Mogwai — People and correspondence</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#f3f3f0;color:#171717;font:16px/1.45 system-ui,sans-serif}
main{max-width:880px;margin:auto;padding:24px 16px 48px}h1{font-size:26px;margin:18px 0 8px}h2{font-size:20px;margin:0 0 14px}
a{color:#135da8}code{overflow-wrap:anywhere}.people{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}
fieldset{min-width:0;border:1px solid #bbb;background:white;border-radius:4px;padding:20px;margin:0 0 20px}
label{display:block;margin:12px 0}input,select{display:block;width:100%;font:inherit;padding:9px;border:1px solid #888;border-radius:3px;margin-top:4px}
button{font:inherit;background:#234d72;color:white;border:0;border-radius:3px;padding:12px 18px;cursor:pointer}
.status{padding:12px;border-left:4px solid #28643e;background:#e7f1e8}.error{border-color:#a32424;background:#fff0ed}
.muted{color:#505050;font-size:14px}.actions{position:sticky;bottom:0;padding:12px 0;background:#f3f3f0;display:flex;align-items:center;gap:20px}
@media(max-width:620px){.people{grid-template-columns:1fr}fieldset{padding:16px}.actions{flex-wrap:wrap}}
</style></head><body><main>
<a href="<?= $escape($back) ?>">← Back to the letter or directory</a>
<h1>People and correspondence</h1>
<p>Saved in <code><?= $escape($database) ?></code>. The NCS letter reads these values when you open it locally.</p>
<?php if($message){ ?><p class="status" role="status"><?= $escape($message) ?></p><?php } ?>
<?php if($error){ ?><p class="status error" role="alert"><?= $escape($error) ?></p><?php } ?>
<form method="post" autocomplete="off">
<input type="hidden" name="csrf" value="<?= $escape($_SESSION["csrf"]) ?>">
<div class="people">
<?php foreach(MOGWAI_PEOPLE as $id => $label){ $person = $data["people"][$id]; ?>
<fieldset><h2><?= $escape($label) ?></h2>
<label>Full legal name<input name="people[<?= $id ?>][legal_name]" value="<?= $escape($person["legal_name"]) ?>" maxlength="200"></label>
<label>Date of birth<input type="date" name="people[<?= $id ?>][dob]" value="<?= $escape($person["dob"]) ?>"></label>
<label>Social Security number<input type="password" inputmode="numeric" name="people[<?= $id ?>][ssn]" value="<?= $escape($person["ssn"]) ?>" maxlength="11" autocomplete="off"></label>
<label>Experian report number <span class="muted">(optional)</span><input name="people[<?= $id ?>][experian_report_number]" value="<?= $escape($person["experian_report_number"]) ?>" maxlength="200"></label>
</fieldset>
<?php } ?>
</div>
<fieldset><h2>NCS dispute letter</h2>
<p class="muted">Choose which saved person goes in each slot. Blank fields stay editable placeholders in the letter.</p>
<?php foreach(["person1" => "Lessee 1", "person2" => "Lessee 2"] as $key => $label){ ?>
<label><?= $label ?><select name="letter[<?= $key ?>]">
<option value="">Not assigned</option>
<?php foreach(MOGWAI_PEOPLE as $id => $name){ ?><option value="<?= $id ?>"<?= $data["letter"][$key] === $id ? " selected" : "" ?>><?= $escape($name) ?></option><?php } ?>
</select></label>
<?php } ?>
<label>Current mailing address<input name="letter[mailing_address]" value="<?= $escape($data["letter"]["mailing_address"]) ?>" maxlength="300"></label>
<label>City, state ZIP<input name="letter[city_state_zip]" value="<?= $escape($data["letter"]["city_state_zip"]) ?>" maxlength="200"></label>
<label>Correspondence date<input type="date" name="letter[letter_date]" value="<?= $escape($data["letter"]["letter_date"]) ?>"></label>
</fieldset>
<div class="actions"><button type="submit">Save home profiles</button><a href="<?= $escape($back) ?>">Return and reload saved values</a></div>
<p class="muted">The home database is stored locally with owner-only file permissions. It is not an encrypted vault. Filling the letter also fills the identifying fields in a PDF you print from it.</p>
</form></main></body></html>

<?php
require_once dirname(__DIR__) . "/profiles/store.php";
if(!mogwai_profiles_local()){
	http_response_code(403); exit("Open Signing identities through the local Mogwai listener.");
}
header("Cache-Control: no-store");
header("X-Frame-Options: DENY");
header("Content-Security-Policy: frame-ancestors 'none'; form-action 'self'");
header("Referrer-Policy: no-referrer");
session_name("mogwai_signatures");
session_start(["cookie_httponly" => true, "cookie_samesite" => "Strict", "use_strict_mode" => true]);
$_SESSION["csrf"] ??= bin2hex(random_bytes(32));
$escape = fn($value) => htmlspecialchars((string)$value, ENT_QUOTES | ENT_SUBSTITUTE, "UTF-8");

function mogwai_signature_request($data){
	// Apply the shared home DB location checks before starting the local tool.
	mogwai_home_db_path();
	$python = getenv("MOGWAI_SIGNATURE_PYTHON") ?: rtrim(getenv("HOME") ?: "", "/") . "/.venvs/mogwai-signatures/bin/python";
	if(!is_file($python) && !getenv("MOGWAI_SIGNATURE_PYTHON")) $python = "python3";
	$process = proc_open([$python, __DIR__ . "/workbench.py", "request"],
		[0 => ["pipe", "r"], 1 => ["pipe", "w"], 2 => ["file", "/dev/null", "a"]], $pipes);
	if(!is_resource($process)) throw new RuntimeException("Cannot start the local signing tool.");
	fwrite($pipes[0], json_encode($data, JSON_THROW_ON_ERROR)); fclose($pipes[0]);
	$result = stream_get_contents($pipes[1]); fclose($pipes[1]);
	$code = proc_close($process);
	$value = json_decode($result, true);
	if($code !== 0 || !is_array($value)) throw new RuntimeException(is_string($value["error"] ?? null) ? $value["error"] : "Install the signing tool's Python dependencies; see signatures/README.md.");
	return $value;
}

$report = null; $message = $error = ""; $records = [];
try{
	if(($_SERVER["REQUEST_METHOD"] ?? "GET") === "POST"){
		$scheme = !empty($_SERVER["HTTPS"]) && $_SERVER["HTTPS"] !== "off" ? "https" : "http";
		$origin = $_SERVER["HTTP_ORIGIN"] ?? "";
		$token = $_POST["csrf"] ?? "";
		if(!is_string($token) || !hash_equals($_SESSION["csrf"], $token)
			|| ($origin !== "" && strtolower($origin) !== $scheme . "://" . strtolower($_SERVER["HTTP_HOST"]))
			|| ($_SERVER["HTTP_SEC_FETCH_SITE"] ?? "") === "cross-site"){
			http_response_code(403); exit("Reload this local form before continuing.");
		}
		$action = $_POST["action"] ?? "";
		if($action === "inspect"){
			$file = $_FILES["pdf"] ?? [];
			if(($file["error"] ?? -1) !== UPLOAD_ERR_OK || !is_uploaded_file($file["tmp_name"] ?? "") || ($file["size"] ?? 0) > 25 * 1024 * 1024) throw new RuntimeException("Choose an original PDF up to 25 MB, within PHP's upload limit.");
			$report = mogwai_signature_request(["action" => "inspect", "path" => $file["tmp_name"]]);
		}elseif($action === "remember"){
			$data = ["action" => "remember"];
			foreach(["certificate_pem", "label", "publication", "status", "evidence", "confirmed_fingerprint"] as $field){
				if(!is_string($_POST[$field] ?? null)) throw new RuntimeException("Complete the signing identity form.");
				$data[$field] = $_POST[$field];
			}
			mogwai_signature_request($data);
			$message = "Saved the public certificate and your local identity assessment.";
		}elseif($action === "export"){
			$public = mogwai_signature_request(["action" => "export", "fingerprint" => $_POST["fingerprint"] ?? ""]);
			header("Content-Type: application/json; charset=utf-8");
			header('Content-Disposition: attachment; filename="mogwai-public-certificate.json"');
			echo json_encode($public, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES); exit();
		}else throw new RuntimeException("Choose a workbench action.");
	}
}catch(Throwable $problem){ http_response_code(400); $error = $problem->getMessage(); }
try{ $records = mogwai_signature_request(["action" => "list"]); }
catch(Throwable $problem){ http_response_code(503); $error = $problem->getMessage(); }
$csrf = '<input type="hidden" name="csrf" value="' . $escape($_SESSION["csrf"]) . '">';
?>
<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Mogwai — Signing identities</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#f3f3f0;color:#171717;font:16px/1.5 system-ui,sans-serif}
main{max-width:960px;margin:auto;padding:24px 16px 48px}h1{font-size:27px}h2{font-size:21px}h3{font-size:18px}
section,article{padding:18px;margin:18px 0;background:white;border:1px solid #bbb;border-radius:4px}
label{display:block;margin:12px 0}input,select,textarea{display:block;width:100%;font:inherit;padding:9px;border:1px solid #888;border-radius:3px}
textarea,pre,code{overflow-wrap:anywhere;white-space:pre-wrap}textarea{font:13px/1.4 monospace}button{font:inherit;padding:10px 16px;cursor:pointer}
dl{display:grid;grid-template-columns:180px minmax(0,1fr);gap:8px}dt{font-weight:600}dd{margin:0;overflow-wrap:anywhere}
.status{padding:12px;background:#e7f1e8;border-left:4px solid #28643e}.error{background:#fff0ed;border-color:#a32424}a{color:#135da8}
@media(max-width:600px){dl{display:block}dd{margin-bottom:12px}section,article{padding:12px}}
</style></head><body><main>
<a href="/">← Directory</a><h1>Signing identities</h1>
<p>Inspect an original PDF, compare its signing certificate with saved fingerprints, and export a public certificate record.</p>
<?php if($message){ ?><p class="status" role="status"><?= $escape($message) ?></p><?php } ?>
<?php if($error){ ?><p class="status error" role="alert"><?= $escape($error) ?></p><?php } ?>
<section><h2>Inspect a PDF</h2>
<form method="post" enctype="multipart/form-data"><?= $csrf ?><input type="hidden" name="action" value="inspect">
<label>Original signed PDF<input type="file" name="pdf" accept="application/pdf,.pdf" required></label>
<button>Inspect signatures</button></form>
<p>The local Python tool checks the uploaded copy. The source file is unchanged; the upload is temporary. Validation runs offline.</p>
<?php if($report){ ?>
<p>Document SHA-256: <code><?= $escape($report["sha256"]) ?></code></p>
<?php if(!$report["signatures"]){ ?><p>No embedded document signatures found.</p><?php } ?>
<?php foreach($report["signatures"] as $signature){ ?>
<article><h3><?= $escape($signature["field"]) ?></h3><dl>
<?php foreach(["subject" => "Certificate subject", "issuer" => "Certificate issuer", "certificate_sha256" => "Certificate SHA-256", "public_key_sha256" => "Public key SHA-256", "not_before" => "Valid from", "not_after" => "Valid until", "coverage" => "Signed coverage"] as $key => $label){ ?>
<dt><?= $label ?></dt><dd><?= $escape($signature[$key] ?? "Unknown") ?></dd><?php } ?>
<dt>Self-signed</dt><dd><?= !isset($signature["self_signed"]) ? "Undetermined" : ($signature["self_signed"] ? "Yes — certificate self-signature verified" : "No") ?></dd>
<dt>Signed bytes intact</dt><dd><?= !isset($signature["intact"]) ? "Undetermined" : ($signature["intact"] ? "Yes" : "No") ?></dd>
<dt>Signature mathematics</dt><dd><?= !isset($signature["cryptographically_valid"]) ? "Undetermined" : ($signature["cryptographically_valid"] ? "Valid" : "Invalid") ?></dd>
<dt>Later changes permitted</dt><dd><?= !isset($signature["permitted_changes"]) ? "Undetermined" : ($signature["permitted_changes"] ? "Yes" : "No — review validation details") ?></dd>
<dt>Local identity record</dt><dd><?= $escape($signature["local_identity"]["status"]) ?><?= isset($signature["local_identity"]["label"]) ? " — " . $escape($signature["local_identity"]["label"]) : "" ?></dd>
</dl>
<?php if(isset($signature["error"])){ ?><p class="error"><?= $escape($signature["error"]) ?></p><?php } ?>
<details><summary>Validation details</summary><pre><?= $escape($signature["validation_details"] ?? "Verification could not be completed.") ?></pre></details>
<details><summary>Public certificate — copy into the identity form below</summary><textarea rows="8" readonly aria-label="Extracted public certificate"><?= $escape($signature["certificate_pem"]) ?></textarea></details>
</article><?php } ?>
<p><?= $escape($report["validation_policy"]) ?> <?= $escape($report["revocation"]) ?></p>
<?php } ?></section>
<section><h2>Record a signing identity</h2>
<p>Publishing a certificate makes it available. Mark it verified only after independently comparing its full fingerprint with the person or organization. A matching name alone does not verify identity.</p>
<form method="post"><?= $csrf ?><input type="hidden" name="action" value="remember">
<label>Public PEM certificate<textarea name="certificate_pem" rows="7" required maxlength="65536" spellcheck="false"><?= $escape($_POST["certificate_pem"] ?? "") ?></textarea></label>
<label>Identity label<input name="label" required maxlength="200" value="<?= $escape($_POST["label"] ?? "") ?>"></label>
<label>Published certificate reference (optional https:// or ipfs://)<input name="publication" value="<?= $escape($_POST["publication"] ?? "") ?>" maxlength="2000"></label>
<label>Local assessment<select name="status"><option value="observed">Observed — identity not independently checked</option><option value="verified">Verified — fingerprint independently confirmed</option><option value="revoked">Revoked — do not rely on this identity</option></select></label>
<label>Independently confirmed certificate SHA-256 (required for verified)<input name="confirmed_fingerprint" value="" autocomplete="off" spellcheck="false"></label>
<label>How and when you checked it, or reason for revocation<textarea name="evidence" rows="3" maxlength="2000"><?= $escape($_POST["evidence"] ?? "") ?></textarea></label>
<button>Save identity assessment</button></form></section>
<section><h2>Saved identities</h2>
<?php if(!$records){ ?><p>No certificates recorded.</p><?php } ?>
<?php foreach($records as $record){ ?><article><h3><?= $escape($record["label"]) ?></h3>
<p>Local assessment: <strong><?= $escape($record["status"]) ?></strong></p>
<p>Certificate SHA-256: <code><?= $escape($record["fingerprint"]) ?></code></p>
<p>Publication reference: <?= $escape($record["publication"] ?: "None recorded") ?></p>
<p>Local evidence: <?= $escape($record["evidence"] ?: "None recorded") ?></p>
<details><summary>Public certificate — copy to update this assessment</summary><textarea rows="7" readonly aria-label="Saved public certificate"><?= $escape($record["certificate"]) ?></textarea></details>
<form method="post"><?= $csrf ?><input type="hidden" name="action" value="export"><input type="hidden" name="fingerprint" value="<?= $escape($record["fingerprint"]) ?>"><button>Export public certificate record</button></form>
</article><?php } ?>
<p>Exports contain the public certificate, label, fingerprints and publication reference. Local assessment notes and home profile fields stay in the home database. Exporting does not publish anything automatically.</p>
</section>
<p>To add your own PDF signature using an existing signing identity, see <code>signatures/README.md</code> in Mogwai. This page accepts public certificates; private keys stay with your signing tool.</p>
</main></body></html>

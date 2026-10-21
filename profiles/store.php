<?php
// Private home records. This database is separate from an archive's catalog.
const MOGWAI_PEOPLE = ["john" => "John", "shannon" => "Shannon"];
const MOGWAI_PERSON_FIELDS = ["legal_name", "dob", "ssn", "experian_report_number"];
const MOGWAI_LETTER_FIELDS = ["person1", "person2", "mailing_address", "city_state_zip", "letter_date"];

function mogwai_profiles_local(){
	if(PHP_SAPI === "cli") return false;
	$address = $_SERVER["REMOTE_ADDR"] ?? "";
	if(!in_array($address, ["127.0.0.1", "::1", "::ffff:127.0.0.1"], true)) return false;
	$host = strtolower($_SERVER["HTTP_HOST"] ?? "");
	$port = (string)($_SERVER["SERVER_PORT"] ?? "");
	$hosts = ["localhost:" . $port, "127.0.0.1:" . $port, "[::1]:" . $port];
	if(in_array($port, ["80", "443"], true)) $hosts = array_merge($hosts, ["localhost", "127.0.0.1", "[::1]"]);
	return in_array($host, $hosts, true)
		&& !array_intersect(["HTTP_FORWARDED", "HTTP_X_FORWARDED_FOR", "HTTP_X_REAL_IP", "HTTP_X_FORWARDED_HOST", "HTTP_VIA"], array_keys($_SERVER));
}

function mogwai_home_db_path(){
	$home = rtrim(getenv("HOME") ?: "", "/");
	$path = getenv("MOGWAI_HOME_DB") ?: ($home === "" ? "" : $home . "/catalog.sqlite3");
	if(str_starts_with($path, "~/")) $path = $home . substr($path, 1);
	if($path === "" || $path[0] !== "/") throw new RuntimeException("Set HOME or an absolute MOGWAI_HOME_DB path.");
	$parent = realpath(dirname($path));
	if(!$parent || !is_dir($parent)) throw new RuntimeException("The home database directory does not exist.");
	$path = $parent . "/" . basename($path);
	$root = PHP_SAPI === "cli" ? false : realpath($_SERVER["DOCUMENT_ROOT"] ?? "");
	if($root && ($path === $root || str_starts_with($path, rtrim($root, "/") . "/"))){
		throw new RuntimeException("The private home database must be outside the served archive.");
	}
	if(is_link($path)) throw new RuntimeException("Use the actual database path rather than a symlink.");
	return $path;
}

function mogwai_profiles_db($write = false){
	$path = mogwai_home_db_path();
	if(!$write && !is_file($path)) return null;
	if(!class_exists("SQLite3")) throw new RuntimeException("Enable PHP's SQLite3 extension for home profiles.");
	$mask = umask(0077);
	try{
		if($write && file_exists($path) && !chmod($path, 0600)) throw new RuntimeException("Cannot make the home database owner-only.");
		$db = new SQLite3($path, $write ? SQLITE3_OPEN_READWRITE | SQLITE3_OPEN_CREATE : SQLITE3_OPEN_READONLY);
		$db->enableExceptions(true);
		$db->busyTimeout(3000);
		if($write){
			if(!chmod($path, 0600)) throw new RuntimeException("Cannot make the home database owner-only.");
			$db->exec("CREATE TABLE IF NOT EXISTS mogwai_people (
				id TEXT PRIMARY KEY, legal_name TEXT NOT NULL, dob TEXT NOT NULL,
				ssn TEXT NOT NULL, experian_report_number TEXT NOT NULL
			);
			CREATE TABLE IF NOT EXISTS mogwai_correspondence (
				id TEXT PRIMARY KEY, person1 TEXT NOT NULL, person2 TEXT NOT NULL,
				mailing_address TEXT NOT NULL, city_state_zip TEXT NOT NULL, letter_date TEXT NOT NULL
			);");
		}
		return $db;
	}finally{ umask($mask); }
}

function mogwai_profiles_read(){
	$data = ["people" => [], "letter" => array_fill_keys(MOGWAI_LETTER_FIELDS, "")];
	foreach(MOGWAI_PEOPLE as $id => $label) $data["people"][$id] = array_fill_keys(MOGWAI_PERSON_FIELDS, "");
	$db = mogwai_profiles_db();
	if(!$db) return $data;
	try{
		if($db->querySingle("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='mogwai_people'")){
			$rows = $db->query("SELECT * FROM mogwai_people");
			while($row = $rows->fetchArray(SQLITE3_ASSOC)){
				$id = $row["id"]; unset($row["id"]); $data["people"][$id] = $row;
			}
		}
		if($db->querySingle("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='mogwai_correspondence'")){
			$row = $db->querySingle("SELECT * FROM mogwai_correspondence WHERE id='ncs-dispute'", true);
			if($row){ unset($row["id"]); $data["letter"] = $row; }
		}
	}finally{ $db->close(); }
	return $data;
}

function mogwai_profile_value($input, $key){
	$value = $input[$key] ?? "";
	if(!is_string($value) || strlen($value) > 500 || preg_match('/[\x00-\x1f\x7f]/', $value)) throw new InvalidArgumentException("Use single-line profile values of at most 500 bytes.");
	$value = trim($value);
	if(in_array($key, ["dob", "letter_date"], true) && $value !== ""){
		$date = DateTimeImmutable::createFromFormat("!Y-m-d", $value);
		if(!$date || $date->format("Y-m-d") !== $value) throw new InvalidArgumentException("Use a valid date in YYYY-MM-DD format.");
	}
	if($key === "ssn"){
		$value = str_replace(["-", " "], "", $value);
		if($value !== "" && !preg_match('/\A[0-9]{9}\z/', $value)) throw new InvalidArgumentException("A Social Security number must contain nine digits, or be blank.");
	}
	return $value;
}

function mogwai_profiles_save($input){
	if(!is_array($input) || !is_array($input["people"] ?? null) || !is_array($input["letter"] ?? null)) throw new InvalidArgumentException("Send the people and correspondence fields together.");
	$data = ["people" => [], "letter" => []];
	foreach(MOGWAI_PEOPLE as $id => $label){
		if(!is_array($input["people"][$id] ?? null)) throw new InvalidArgumentException("Both people must be present in the form.");
		foreach(MOGWAI_PERSON_FIELDS as $field) $data["people"][$id][$field] = mogwai_profile_value($input["people"][$id], $field);
	}
	foreach(MOGWAI_LETTER_FIELDS as $field) $data["letter"][$field] = mogwai_profile_value($input["letter"], $field);
	foreach(["person1", "person2"] as $field){
		if($data["letter"][$field] !== "" && !array_key_exists($data["letter"][$field], MOGWAI_PEOPLE)) throw new InvalidArgumentException("Choose John, Shannon, or an unassigned lessee slot.");
	}
	if($data["letter"]["person1"] !== "" && $data["letter"]["person1"] === $data["letter"]["person2"]) throw new InvalidArgumentException("Choose a different person for each lessee slot.");
	$db = mogwai_profiles_db(true);
	try{
		$db->exec("BEGIN IMMEDIATE");
		try{
			$stmt = $db->prepare("INSERT INTO mogwai_people VALUES (:id,:legal_name,:dob,:ssn,:experian_report_number)
				ON CONFLICT(id) DO UPDATE SET legal_name=excluded.legal_name,dob=excluded.dob,ssn=excluded.ssn,experian_report_number=excluded.experian_report_number");
			foreach($data["people"] as $id => $person){
				foreach(["id" => $id] + $person as $field => $value) $stmt->bindValue(":" . $field, $value, SQLITE3_TEXT);
				$stmt->execute();
			}
			$stmt->close();
			$stmt = $db->prepare("INSERT INTO mogwai_correspondence VALUES ('ncs-dispute',:person1,:person2,:mailing_address,:city_state_zip,:letter_date)
				ON CONFLICT(id) DO UPDATE SET person1=excluded.person1,person2=excluded.person2,mailing_address=excluded.mailing_address,city_state_zip=excluded.city_state_zip,letter_date=excluded.letter_date");
			foreach($data["letter"] as $field => $value) $stmt->bindValue(":" . $field, $value, SQLITE3_TEXT);
			$stmt->execute(); $stmt->close();
			$db->exec("COMMIT");
		}catch(Throwable $error){ $db->exec("ROLLBACK"); throw $error; }
	}finally{ $db->close(); }
}

function mogwai_correspondence_fields(){
	$data = mogwai_profiles_read();
	$fields = $data["letter"];
	foreach(["person1", "person2"] as $slot){
		$person = $data["people"][$fields[$slot]] ?? [];
		foreach(MOGWAI_PERSON_FIELDS as $key){
			$value = $person[$key] ?? "";
			if($key === "dob" && $value !== "") $value = DateTimeImmutable::createFromFormat("!Y-m-d", $value)->format("m/d/Y");
			if($key === "ssn" && strlen($value) === 9) $value = substr($value,0,3) . "-" . substr($value,3,2) . "-" . substr($value,5);
			$fields[$slot . "." . $key] = $value;
		}
	}
	if($fields["letter_date"] !== "") $fields["letter_date"] = DateTimeImmutable::createFromFormat("!Y-m-d", $fields["letter_date"])->format("F j, Y");
	return $fields;
}

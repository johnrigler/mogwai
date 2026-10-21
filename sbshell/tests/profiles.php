<?php
// Synthetic records only. This never reads or writes the real home database.
require_once __DIR__ . "/../../profiles/store.php";
function check($condition, $message){ if(!$condition) throw new RuntimeException($message); }
$temporary = sys_get_temp_dir() . "/mogwai-profiles-" . bin2hex(random_bytes(6));
mkdir($temporary);
$path = $temporary . "/home.sqlite3";
$previous = getenv("MOGWAI_HOME_DB");
putenv("MOGWAI_HOME_DB=" . $path);
try{
	check(mogwai_profiles_read()["people"]["john"]["ssn"] === "", "An unconfigured person stays empty.");
	check(!file_exists($path), "Reading missing profiles must not create a database.");
	$db = new SQLite3($path);
	$db->exec("CREATE TABLE book_of_record (note TEXT); INSERT INTO book_of_record VALUES ('keep existing data');");
	$db->close();
	$data = ["people" => [], "letter" => ["person1" => "shannon", "person2" => "john", "mailing_address" => "Synthetic address", "city_state_zip" => "Example, NM 00000", "letter_date" => "2026-10-20"]];
	foreach(MOGWAI_PEOPLE as $id => $name) $data["people"][$id] = ["legal_name" => "Example " . $name, "dob" => "1900-01-01", "ssn" => "000-00-0001", "experian_report_number" => ""];
	mogwai_profiles_save($data);
	$saved = mogwai_profiles_read();
	check($saved["people"]["john"]["ssn"] === "000000001", "SSNs retain leading zeros as text.");
	check((fileperms($path) & 0777) === 0600, "The home database must be owner-only.");
	$fields = mogwai_correspondence_fields();
	check($fields["person1.legal_name"] === "Example Shannon" && $fields["person2.legal_name"] === "Example John", "Lessee assignment must be explicit.");
	check($fields["person1.dob"] === "01/01/1900" && $fields["person1.ssn"] === "000-00-0001", "Format identifying fields for the letter.");
	check($fields["letter_date"] === "October 20, 2026", "The correspondence date is the saved date.");
	$db = new SQLite3($path, SQLITE3_OPEN_READONLY);
	check($db->querySingle("SELECT note FROM book_of_record") === "keep existing data", "Do not replace existing home tables.");
	$db->close();
	foreach(["ssn" => "short", "dob" => "1900-02-29"] as $key => $value){
		$bad = $data; $bad["people"]["john"][$key] = $value;
		try{ mogwai_profiles_save($bad); throw new RuntimeException("Invalid input was saved."); }
		catch(InvalidArgumentException $expected){}
		check(mogwai_profiles_read() === $saved, "Validate all fields before changing stored records.");
	}
	$data["letter"]["person1"] = $data["letter"]["person2"] = "";
	$data["people"]["john"]["ssn"] = "";
	mogwai_profiles_save($data);
	check(mogwai_correspondence_fields()["person1.legal_name"] === "", "Unassigned slots remain placeholders.");
	check(mogwai_profiles_read()["people"]["john"]["ssn"] === "", "Explicit empty values can clear a stored field.");
	echo "Home profiles: persistence, explicit roles, text SSNs, dates, permissions, existing tables and validation passed.\n";
}finally{
	putenv($previous === false ? "MOGWAI_HOME_DB" : "MOGWAI_HOME_DB=" . $previous);
	foreach(glob($path . "*") as $file) unlink($file);
	rmdir($temporary);
}

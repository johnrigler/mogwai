# People and correspondence

Mogwai's local GUI stores reusable identity fields in `~/catalog.sqlite3`.
On John's laptop this is `/home/john/catalog.sqlite3`, above the project
checkouts. It is separate from `daisy_2026/catalog.sqlite3` and other archive
catalogs. Existing home-database tables are preserved.

Start the consolidated local viewer:

```bash
cd "$HOME/daisy_2026"
php -S 127.0.0.1:39692 -t . "$HOME/mogwai/sbshell/cruff/index.php"
```

Open a directory's hamburger menu and choose **People and correspondence**.
The direct local route is `http://127.0.0.1:39692/?mogwai-profiles=1`.
Use PHP 8+ with SQLite3; `SB_PHP` in the setup check should select the same
binary used to start this listener.

Enter John and Shannon's full legal names, dates of birth, Social Security
numbers and optional Experian report numbers. Names shown on the empty cards
are labels, not assertions of legal names. No birth dates or SSNs are supplied
by the source code. Choose which person fills Lessee 1 and Lessee 2; the tool
does not infer legal roles. Save the shared mailing address and the actual
correspondence date in the same form.

Return to the NCS letter. Its local PHP view fills configured fields, including
both signature names. Blank or unassigned values stay editable placeholders.
Edits made directly in the letter are temporary; use the profile form to change
the saved values. Saving and returning reloads the current database values.

## Database and access

- `mogwai_people` holds the reusable person records. Dates are ISO `YYYY-MM-DD`;
  SSNs are text so leading zeros survive.
- `mogwai_correspondence` holds the explicit NCS person assignments, mailing
  address and correspondence date. The record key is `ncs-dispute`.
- Reading missing profiles does not create a database. Saving adds these
  tables and updates their records, retaining other home tables.
- The file is owner-readable/writable (`0600`). This is local plaintext SQLite,
  not an encrypted vault. The home database is not copied into Git or IPFS by
  this tool. An actual printed letter/PDF contains the fields shown in it.
- The GUI and automatic field reads require a direct loopback request with a
  localhost Host header. Profile saves use a session CSRF token and same-origin
  checks. Responses use `Cache-Control: no-store`; values are not placed in
  URLs or browser storage. The private database must be outside the served root.

Set `MOGWAI_HOME_DB` to another absolute database path before starting PHP if
needed. It is a process setting, not a browser parameter. `store.php` provides
ordinary PHP functions for other local Mogwai tools to reuse the saved records.
The public FileProxy API does not expose them.

The case's `build` command remains an unfilled static-template export. It does
not bake private home values into HTML in the archive checkout. Use the local
PHP letter and Chrome's print-to-PDF for the personalized edition.

## Checks

From `sbshell/`, run `php tests/profiles.php` and
`SB_PHP=php node tests/profiles-http.mjs`. These use temporary databases and
synthetic identity values. They do not read the operator's saved home profiles.

# PHP release build

Use `~/mogwai/tools/php/` for the downloaded archive, build notes and real terminal recordings. SB Shell supplies the directory view. No PHP source fork or Daisy record is required for this workflow.

Current input: John reports downloading `php-8.5.12.tar.gz` from PHP.net. The local file has not been inspected here; extraction, compilation and installation are still to be performed on the Chromebook. This replaces the earlier PHP 8.2 fork proposal.

## Start the recording

```bash
mkdir -p "$HOME/mogwai/tools/php"
cd "$HOME/mogwai/tools/php"
type d.script
declare -f d.script
```

If the function is not loaded, inspect and source `~/mogwai/sbshell/lib/d.script.bash`. Start `d.script` here, before changing into the extracted source:

```bash
d.script
pwd
date -Is
id
cat /etc/os-release
uname -m
```

The timestamped `.unixTs` stays in this tools directory while you work in child directories. `exit` ends the recorded shell. Here, “typescript” means the terminal recording. Keep actual commands, output, failures and corrections.

## Put the archive here and verify it

In Chrome's Files app, copy the download into **Linux files → mogwai → tools → php**. Use its actual location if Mogwai is elsewhere. PHP.net names the archive in lowercase: `php-8.5.12.tar.gz`.

From this tools directory:

```bash
ls -l php-8.5.12.tar.gz
sha256sum -c <<'PHP_ARCHIVE_SHA256'
81a0f450349e84b08eb43faa85f8a4c835684f3cc1c50471775d1317a046c525  php-8.5.12.tar.gz
PHP_ARCHIVE_SHA256
```

The expected SHA-256 above comes from [PHP.net's source-download page](https://www.php.net/downloads.php?source=Y), checked October 22, 2026 UTC. Stop if it does not report **OK**. This checks the archive bytes against that published checksum; it does not mean this assistant has verified your downloaded file.

## Build from the release archive

After confirming the Linux environment is Debian/Ubuntu, install the build dependencies below. Use the ordinary Linux user for compiling and installing into your own home directory; sudo is only for the package commands. Run stages separately and stop on errors.

```bash
sudo apt update
sudo apt install pkg-config build-essential autoconf bison re2c \
  libxml2-dev libsqlite3-dev zlib1g-dev libpng-dev libjpeg-dev libfreetype6-dev
```

Extract into a new directory. If `php-8.5.12/` already exists, inspect it before extracting again.

```bash
tar -xzf php-8.5.12.tar.gz
cd php-8.5.12
./configure --prefix="$HOME/local/php-8.5.12" \
  --with-sqlite3 --with-pdo-sqlite --enable-gd --with-jpeg --with-freetype
make -j2
make test
```

The release archive includes `configure`; the Git checkout's `./buildconf` step is unnecessary here. Review test failures before proceeding. This proposed configuration includes SQLite3 and GD for SB Shell; it has not been compiled on your Chromebook by this assistant.

After a successful build and reviewed tests:

```bash
make install
"$HOME/local/php-8.5.12/bin/php" -v
"$HOME/local/php-8.5.12/bin/php" --ini
SB_PHP="$HOME/local/php-8.5.12/bin/php" \
  bash "$HOME/mogwai/sbshell/setup" check "$HOME/mogwai/tools/php"
```

This home-directory installation leaves the choice of executable explicit. It does not upgrade another host's PHP or change an already running server.

## Read the work through SB Shell

Finish the recording with `exit` when ready. From the outer shell, start the viewer using the new binary:

```bash
cd "$HOME/mogwai/tools/php"
"$HOME/local/php-8.5.12/bin/php" -S 127.0.0.1:39692 \
  -t . "$HOME/mogwai/sbshell/cruff/index.php"
```

Use the existing listener instead if it already serves this directory; choose an available port if necessary. Open `http://127.0.0.1:39692/`, expand the `.unixTs` file, and check **PHP setup** in the menu for the runtime serving the page. The existing renderer needs no copy inside the extracted PHP source. Ctrl-C stops this local viewer.

Keep numbered explanation parts and recordings here. The local archive and extracted build directory are ignored by Git; notes and reviewed recordings can be published deliberately. Inspect recordings for private content before staging them.

## References

- [PHP 8.5.12 source release and checksum](https://www.php.net/downloads.php?source=Y).
- [PHP source build and test instructions](https://github.com/php/php-src/blob/php-8.5.12/README.md).
- [SB Shell directory and setup instructions](../../sbshell/README.md).
- [d.script function](../../sbshell/lib/d.script.bash).

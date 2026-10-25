"""CLI for indexing and accessing local Daisy/CertLedger/other roots."""
import argparse
import json
from pathlib import Path
import sys
import sqlite3

from .core import (
    DEFAULT_CONFIG, DEFAULT_INDEX, ROOT_NAME, load_config, load_catalog,
    put, query_index, resolve_file, roots_from, scan, write_config
)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="fp", description="FileProxy workspace CLI")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="JSON configuration path")
    parser.add_argument("--index", default=DEFAULT_INDEX,
                        help="Explicit shared SQLite catalog (default: catalog.sqlite3 inside each root)")
    cmd = parser.add_subparsers(dest="command", required=True)
    cmd.add_parser("roots", help="Print registered data roots")
    cmd.add_parser("date", help="Compare ALP and ISO year/week/day")
    add = cmd.add_parser("add-root", help="Register an existing local directory")
    add.add_argument("name")
    add.add_argument("directory")
    sc = cmd.add_parser("scan", help="Rebuild SHA-256 index from registered filesystem roots")
    sc.add_argument("names", nargs="*", help="Optional subset of registered roots")
    ls = cmd.add_parser("ls", help="List indexed records")
    ls.add_argument("name", nargs="?")
    ls.add_argument("--prefix", default="")
    ls.add_argument("--limit", type=int, default=200)
    search = cmd.add_parser("find", help="Search path and hash in the derived catalog")
    search.add_argument("term")
    search.add_argument("--root")
    search.add_argument("--limit", type=int, default=200)
    cat = cmd.add_parser("cat", help="Read an actual file, not an index copy")
    cat.add_argument("root")
    cat.add_argument("path")
    copy = cmd.add_parser("put", help="Copy a local file into a configured root")
    copy.add_argument("root")
    copy.add_argument("source")
    copy.add_argument("path", help="Destination relative to that root")
    copy.add_argument("--overwrite", action="store_true")
    inv = cmd.add_parser("inventory", help="Export qualified paths for SB Shell")
    inv.add_argument("root")
    inv.add_argument("subtree", nargs="?", default=".")
    inv.add_argument("--output", default="files.txt")
    ingest = cmd.add_parser("ingest", help="Classify and capture pasted text or HTTPS URLs")
    ingest.add_argument("text", nargs="?", help="Paste or URL; reads stdin if omitted")
    ingest.add_argument("--destination", default="auto", help="Configured root or auto")
    ingest.add_argument("--note", default="")
    service = cmd.add_parser("serve", help="Run legacy Chisel endpoints plus /v1 general routes")
    service.add_argument("--local", action="store_true",
                         help="Bind to loopback and allow same-origin local writes without a token")
    service.add_argument("--host", default="127.0.0.1", help="HTTP listen address (default: 127.0.0.1)")
    service.add_argument("--port", type=int, default=7799, help="HTTP listen port (default: 7799)")
    service.add_argument("--activity-log", default="", metavar="FILE",
                         help="Append sanitized per-request JSONL activity records to FILE")
    service.add_argument("--data-root", metavar="DIRECTORY",
                         help="Existing Chisel transaction datastore directory (no files copied)")
    args = parser.parse_args(argv)

    try:
        if args.command == "serve":
            from .server import main as serve
            return serve(args.config, args.index, local=args.local, host=args.host, port=args.port, activity_log=args.activity_log, data_root=args.data_root)
        conf = load_config(args.config)
        if args.command == "date":
            from .daisy_dates import daisy_date
            value = daisy_date()
            old = value["legacy"]
            print(f'Daisy ISO %G/%V/%u: {value["year"]}/{value["week"]:02d}/{value["weekday"]}')
            print(f'ALP legacy %Y/%W/%w: {old["year"]}/{old["week"]:02d}/{old["weekday"]}')
            print("Timezone:", value["timezone"], "Local date:", value["localDate"])
        elif args.command == "roots":
            for name, directory in sorted(roots_from(conf).items()):
                print(name + "\t" + str(directory))
        elif args.command == "add-root":
            if not ROOT_NAME.fullmatch(args.name):
                raise ValueError("Invalid root name")
            directory = Path(args.directory).expanduser().resolve()
            if not directory.is_dir():
                raise ValueError("Directory does not exist: " + str(directory))
            conf["roots"][args.name] = str(directory)
            write_config(conf, args.config)
            print(args.name + " -> " + str(directory))
        elif args.command == "scan":
            print(json.dumps(scan(conf, args.names or None, args.index), indent=2))
        elif args.command == "ls":
            for row in query_index(load_catalog(conf, args.index, [args.name] if args.name else None), root=args.name, prefix=args.prefix, limit=args.limit):
                print(row["id"] + "\t" + row["sha256"])
        elif args.command == "find":
            for row in query_index(load_catalog(conf, args.index, [args.root] if args.root else None), root=args.root, text=args.term, limit=args.limit):
                print(row["id"] + "\t" + row["sha256"])
        elif args.command == "ingest":
            from .intake import intake
            pasted = args.text if args.text is not None else sys.stdin.read()
            from .routing import split_paste
            content, tag = split_paste(pasted)
            if tag and args.destination not in ("auto", tag):
                raise ValueError("Destination conflicts with #" + tag)
            print(json.dumps(intake(conf, content, tag or args.destination, args.note, index_path=args.index), indent=2))
        elif args.command == "inventory":
            from .inventory import export_inventory
            print(json.dumps(export_inventory(conf, args.root, args.subtree, args.output), indent=2))
        elif args.command == "cat":
            sys.stdout.buffer.write(resolve_file(conf, args.root, args.path).read_bytes())
        elif args.command == "put":
            data = Path(args.source).expanduser().read_bytes()
            print(json.dumps(put(conf, args.root, args.path, data, args.overwrite), indent=2))
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError, sqlite3.DatabaseError) as exc:
        print("fileproxy: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

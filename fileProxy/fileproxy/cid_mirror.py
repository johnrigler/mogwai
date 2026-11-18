"""Publish IPFS CID exports as immutable static files, independently of Kubo.

Kubo is used only during export. Verify works with Kubo and FileProxy stopped.
Verifies CARv1 root and SHA-256 block hashes plus exported-file SHA-256.
This does not prove DAG completeness, UnixFS correspondence, or authorship.
No environment variables, external Python packages, or public write endpoint.
"""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import tempfile

FORMAT = "chisel-cid-static-v1"
BASE58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
DIGEST = re.compile(r"^[0-9a-f]{64}$")
CHUNK = 1024 * 1024


def _varint(stream):
    number = 0
    for i in range(10):
        byte = stream.read(1)
        if not byte:
            if i == 0:
                return None
            raise ValueError("Truncated CAR varint")
        number |= (byte[0] & 127) << (i * 7)
        if byte[0] < 128:
            if i and byte[0] == 0:
                raise ValueError("Noncanonical CAR varint")
            return number
    raise ValueError("Oversized CAR varint")


def _cid_varint(data, at):
    number = 0
    for i in range(10):
        if at + i >= len(data):
            raise ValueError("Truncated CID varint")
        byte = data[at + i]
        number |= (byte & 127) << (i * 7)
        if byte < 128:
            if i and byte == 0:
                raise ValueError("Noncanonical CID varint")
            return number, at + i + 1
    raise ValueError("Oversized CID varint")


def _parse_cid(data, at=0):
    start = at
    if data[at:at + 2] == b"\x12\x20":
        end = at + 34
        if len(data) < end:
            raise ValueError("Truncated CIDv0")
        return data[start:end], end, data[at + 2:end]
    version, at = _cid_varint(data, at)
    if version != 1:
        raise ValueError("Unsupported CID version")
    codec, at = _cid_varint(data, at)
    if codec == 0:
        raise ValueError("Invalid CID codec")
    hash_code, at = _cid_varint(data, at)
    hash_size, at = _cid_varint(data, at)
    if hash_code != 0x12 or hash_size != 32:
        raise ValueError("Only SHA-256 multihashes supported")
    end = at + 32
    if len(data) < end:
        raise ValueError("Truncated CID multihash")
    return data[start:end], end, data[at:end]


def decode_cid(value):
    if not isinstance(value, str) or not value or len(value) > 128 or '/' in value:
        raise ValueError("Invalid root CID")
    if value.startswith("Qm"):
        number = 0
        for char in value:
            if char not in BASE58:
                raise ValueError("Invalid CIDv0 base58")
            number = number * 58 + BASE58.index(char)
        data = number.to_bytes((number.bit_length() + 7) // 8, "big")
        data = b"\0" * (len(value) - len(value.lstrip('1'))) + data
        if len(data) != 34 or data[:2] != b"\x12\x20":
            raise ValueError("Invalid CIDv0 SHA-256 hash")
    elif value.startswith('b'):
        encoded = value[1:]
        if not re.fullmatch(r"[a-z2-7]+", encoded):
            raise ValueError("Invalid canonical base32 CID")
        try:
            data = base64.b32decode(encoded.upper() + '=' * (-len(encoded) % 8))
        except (ValueError, base64.binascii.Error) as error:
            raise ValueError("Invalid base32 CID") from error
        if base64.b32encode(data).decode().lower().rstrip('=') != encoded:
            raise ValueError("Noncanonical base32 CID")
    else:
        raise ValueError("Only canonical CIDv0 and base32 CIDv1 supported")
    parsed, end, _ = _parse_cid(data)
    if end != len(data) or parsed != data:
        raise ValueError("Trailing CID bytes")
    return data


class _Cbor:
    def __init__(self, data):
        self.data, self.at = data, 0

    def read(self, depth=0):
        if depth > 12 or self.at >= len(self.data):
            raise ValueError("Invalid CAR CBOR header")
        first = self.data[self.at]
        self.at += 1
        kind, ai = first >> 5, first & 31
        if ai < 24:
            count = ai
        elif ai in (24, 25, 26, 27):
            size = {24: 1, 25: 2, 26: 4, 27: 8}[ai]
            if self.at + size > len(self.data):
                raise ValueError("Truncated CAR CBOR")
            count = int.from_bytes(self.data[self.at:self.at + size], 'big')
            self.at += size
        else:
            raise ValueError("Indefinite CAR CBOR not supported")
        if kind == 0:
            return count
        if kind == 1:
            return -count - 1
        if kind in (2, 3):
            if count > len(self.data) - self.at:
                raise ValueError("Truncated CAR CBOR bytes")
            part = self.data[self.at:self.at + count]
            self.at += count
            return part if kind == 2 else part.decode('utf-8')
        if kind == 4:
            return [self.read(depth + 1) for _ in range(count)]
        if kind == 5:
            return {self.read(depth + 1): self.read(depth + 1) for _ in range(count)}
        if kind == 6:
            return ('tag', count, self.read(depth + 1))
        raise ValueError("Unsupported CAR CBOR header type")


def verify_car(car_path, cid):
    expected = decode_cid(cid)
    count = 0
    has_root = False
    with open(car_path, 'rb') as source:
        size = _varint(source)
        if size is None or size < 1 or size > 65536:
            raise ValueError("Invalid CARv1 header size")
        header = source.read(size)
        if len(header) != size:
            raise ValueError("Truncated CAR header")
        cbor = _Cbor(header)
        parsed = cbor.read()
        if cbor.at != len(header) or not isinstance(parsed, dict) or parsed.get('version') != 1:
            raise ValueError("Invalid CARv1 header")
        roots = parsed.get('roots')
        if not isinstance(roots, list) or len(roots) != 1:
            raise ValueError("CAR must contain one root")
        root = roots[0]
        if not isinstance(root, tuple) or root[:2] != ('tag', 42) or not isinstance(root[2], bytes):
            raise ValueError("CAR root is not a tagged CID")
        if root[2] != b'\0' + expected:
            raise ValueError("CAR root CID mismatch")
        while True:
            length = _varint(source)
            if length is None:
                break
            if length < 34:
                raise ValueError("Invalid CAR block size")
            first = source.read(min(128, length))
            encoded, end, target_hash = _parse_cid(first)
            if length < end:
                raise ValueError("Empty CAR block")
            rest = length - end
            head = first[end:]
            if len(head) > rest:
                raise ValueError("Malformed CAR section")
            h = hashlib.sha256(head)
            rest -= len(head)
            while rest:
                piece = source.read(min(CHUNK, rest))
                if not piece:
                    raise ValueError("Truncated CAR block")
                h.update(piece)
                rest -= len(piece)
            if h.digest() != target_hash:
                raise ValueError("CAR block multihash mismatch")
            count += 1
            has_root |= encoded == expected
    if not count or not has_root:
        raise ValueError("CAR missing root block")
    return count


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as source:
        for piece in iter(lambda: source.read(CHUNK), b''):
            digest.update(piece)
    return digest.hexdigest()


def _walk_files(directory):
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError("Expected a real directory")
    listing = []
    for base, dirs, files in os.walk(directory, followlinks=False):
        for name in dirs + files:
            path = Path(base) / name
            if path.is_symlink():
                raise ValueError("Symlink in static export: " + str(path))
            if name in ('.', '..') or any(ord(c) < 32 for c in name):
                raise ValueError("Unsafe static export name")
            mode = path.stat(follow_symlinks=False).st_mode
            if name in dirs and not stat.S_ISDIR(mode):
                raise ValueError("Invalid export directory")
            if name in files and not stat.S_ISREG(mode):
                raise ValueError("Special file in export")
        dirs.sort()
        for name in sorted(files):
            path = Path(base) / name
            listing.append({"path": path.relative_to(directory).as_posix(),
                            "bytes": path.stat().st_size, "sha256": _sha256(path)})
    return listing


def _root(path, *, create=False):
    path = Path(path).expanduser().absolute()
    if path.is_symlink() or (path.exists() and not path.is_dir()):
        raise ValueError("Unsafe static root")
    if create:
        path.mkdir(parents=True, exist_ok=True)
    if not path.is_dir():
        raise ValueError("Static root does not exist")
    return path.resolve(strict=True)


def _subdir(root, name, *, create=False):
    path = root / name
    if path.is_symlink() or (path.exists() and not path.is_dir()):
        raise ValueError("Unsafe CID mirror subdirectory: " + name)
    if create:
        path.mkdir(exist_ok=True)
    if not path.is_dir():
        raise ValueError("Missing CID mirror subdirectory: " + name)
    return path


def _run_ipfs(binary, api, timeout, args, *, stdout=None):
    cmd = [binary, '--api=' + api, '--timeout=' + str(timeout) + 's'] + args
    result = subprocess.run(cmd, stdin=subprocess.DEVNULL,
                            stdout=stdout or subprocess.PIPE, stderr=subprocess.PIPE,
                            timeout=timeout + 10, check=False)
    if result.returncode:
        raise RuntimeError("Kubo failed (" + ' '.join(args[:2]) + "): " +
                           result.stderr.decode('utf-8', errors='replace')[-600:])
    return result


def publish(root, cid, *, ipfs='ipfs', api='/ip4/127.0.0.1/tcp/5001', timeout=600):
    """One-time export from Kubo; read-only HTTP files need no daemon."""
    decode_cid(cid)
    if not re.fullmatch(r"/ip(?:4/127\.0\.0\.1|6/::1)/tcp/[0-9]{1,5}", api):
        raise ValueError("Kubo API must be explicit loopback multiaddress")
    port = int(api.rsplit('/', 1)[1])
    if port < 1 or port > 65535:
        raise ValueError("Invalid Kubo API port")
    if not isinstance(timeout, int) or timeout < 1:
        raise ValueError("Timeout must be positive")
    root = _root(root, create=True)
    if (root / cid).exists() or (root / cid).is_symlink() or (root / '_meta' / (cid + '.json')).exists():
        raise FileExistsError("CID already present; use verify")
    with tempfile.TemporaryDirectory(prefix='.cid-stage-', dir=root.parent) as temp:
        stage = Path(temp)
        car = stage / 'dag.car'
        extracted = stage / 'export'
        with car.open('wb') as out:
            _run_ipfs(ipfs, api, timeout, ['dag', 'export', cid], stdout=out)
        blocks = verify_car(car, cid)
        _run_ipfs(ipfs, api, timeout, ['get', '--output=' + str(extracted), cid])
        website = stage / 'website'
        if extracted.is_symlink():
            raise ValueError("Refusing symlinked IPFS export")
        if extracted.is_dir():
            extracted.rename(website)
            entrypoint = 'index.html' if (website / 'index.html').is_file() else None
        elif extracted.is_file():
            website.mkdir()
            extracted.rename(website / 'content')
            entrypoint = 'content'
        else:
            raise ValueError("Kubo returned no export")
        listing = _walk_files(website)
        if not listing:
            raise ValueError("Cannot publish empty CID export")
        metadata = {
            "format": FORMAT, "cid": cid, "origin": "local-kubo",
            "carSha256": _sha256(car), "carBytes": car.stat().st_size,
            "carBlocksHashChecked": blocks, "files": listing,
            "entrypoint": entrypoint,
            "verification": "CAR root/block SHA-256 and static-file SHA-256 only; not complete DAG or publisher proof"
        }
        sidecar = stage / 'meta.json'
        sidecar.write_text(json.dumps(metadata, sort_keys=True, indent=2) + '\n', encoding='utf-8')
        car_target = _subdir(root, '_cars', create=True) / (cid + '.car')
        meta_target = _subdir(root, '_meta', create=True) / (cid + '.json')
        if any(p.exists() or p.is_symlink() for p in (root / cid, car_target, meta_target)):
            raise FileExistsError("CID release already exists")
        # On the same filesystem: static directory becomes visible LAST.
        os.rename(car, car_target)
        os.rename(sidecar, meta_target)
        os.rename(website, root / cid)
    verify(root, cid)
    return metadata


def verify(root, cid):
    """Offline hash inventory check. Does not require Kubo or FileProxy."""
    decode_cid(cid)
    root = _root(root)
    meta = _subdir(root, '_meta') / (cid + '.json')
    car = _subdir(root, '_cars') / (cid + '.car')
    website = root / cid
    if any(p.is_symlink() for p in (meta, car, website)):
        raise ValueError("Symlinked CID mirror component")
    info = json.loads(meta.read_text(encoding='utf-8'))
    if info.get('format') != FORMAT or info.get('cid') != cid:
        raise ValueError("CID mirror metadata mismatch")
    if not DIGEST.fullmatch(info.get('carSha256', '')):
        raise ValueError("Invalid CAR digest")
    if info['carSha256'] != _sha256(car) or info.get('carBytes') != car.stat().st_size:
        raise ValueError("CAR archive hash/size mismatch")
    blocks = verify_car(car, cid)
    if blocks != info.get('carBlocksHashChecked'):
        raise ValueError("CAR block count mismatch")
    listing = _walk_files(website)
    if listing != info.get('files'):
        raise ValueError("Static exported file hash/path/size mismatch")
    if info.get('entrypoint') is not None and info['entrypoint'] not in {f['path'] for f in listing}:
        raise ValueError("Missing declared entrypoint")
    return {"ok": True, "cid": cid, "files": len(listing), "carBlocks": blocks,
            "carSha256": info['carSha256'], "entrypoint": info.get('entrypoint'),
            "level": "CAR block and static file hashes, not complete UnixFS/author proof"}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Immutable CID-addressed static HTTP mirror")
    commands = parser.add_subparsers(dest='action', required=True)
    pub = commands.add_parser('publish', help="Export Kubo CID for daemon-free HTTP serving")
    pub.add_argument('--root', required=True)
    pub.add_argument('--cid', required=True)
    pub.add_argument('--ipfs', default='ipfs', help="Kubo CLI executable")
    pub.add_argument('--api', required=True, help="Explicit local Kubo API multiaddress")
    pub.add_argument('--timeout', type=int, default=600)
    chk = commands.add_parser('verify', help="Offline CAR and static file verification")
    chk.add_argument('--root', required=True)
    chk.add_argument('--cid', required=True)
    args = parser.parse_args(argv)
    if args.action == 'publish':
        result = publish(args.root, args.cid, ipfs=args.ipfs, api=args.api, timeout=args.timeout)
        print(json.dumps({"published": True, "cid": result['cid'],
                          "files": len(result['files']), "carBytes": result['carBytes'],
                          "entrypoint": result['entrypoint']}))
    else:
        print(json.dumps(verify(args.root, args.cid), sort_keys=True))


if __name__ == '__main__':
    main()

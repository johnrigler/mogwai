"""Offline tests for the CID static HTTP mirror: no live Kubo or wallet."""
import base64
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fileproxy import cid_mirror as cm


def encode_varint(n):
    out = bytearray()
    while True:
        byte = n & 127
        n >>= 7
        out.append(byte | (128 if n else 0))
        if not n:
            return bytes(out)


def fixture(body=b'<html>Ledger boot</html>'):
    raw = b'\x01\x55\x12\x20' + hashlib.sha256(body).digest()
    cid = 'b' + base64.b32encode(raw).decode().lower().rstrip('=')
    header = (b'\xa2\x65roots\x81\xd8\x2a\x58' + bytes([len(raw) + 1]) +
              b'\0' + raw + b'\x67version\x01')
    car = encode_varint(len(header)) + header + encode_varint(len(raw) + len(body)) + raw + body
    return cid, car, body


class CIDMirrorTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.root = self.base / 'boot'
        self.cid, self.car, self.body = fixture()

    def mock_ipfs(self, binary, api, timeout, args, *, stdout=None):
        self.assertEqual(api, '/ip4/127.0.0.1/tcp/5001')
        if args[:2] == ['dag', 'export']:
            self.assertEqual(args[2], self.cid)
            stdout.write(self.car)
        elif args[0] == 'get':
            self.assertEqual(args[-1], self.cid)
            output = Path(next(a for a in args if a.startswith('--output=')).split('=', 1)[1])
            output.mkdir()
            (output / 'index.html').write_bytes(self.body)
            (output / 'src').mkdir()
            (output / 'src' / 'app.js').write_bytes(b'console.log("ok");')
        else:
            raise AssertionError(args)

    def test_publish_then_verify_without_kubo(self):
        with patch.object(cm, '_run_ipfs', self.mock_ipfs):
            published = cm.publish(self.root, self.cid, api='/ip4/127.0.0.1/tcp/5001')
        self.assertEqual(published['entrypoint'], 'index.html')
        self.assertEqual((self.root / self.cid / 'index.html').read_bytes(), self.body)
        self.assertEqual((self.root / self.cid / 'src' / 'app.js').read_bytes(), b'console.log("ok");')
        self.assertEqual(cm.verify(self.root, self.cid)['files'], 2)
        with self.assertRaises(FileExistsError):
            cm.publish(self.root, self.cid, api='/ip4/127.0.0.1/tcp/5001')

    def test_corrupted_static_file_and_car_detected(self):
        with patch.object(cm, '_run_ipfs', self.mock_ipfs):
            cm.publish(self.root, self.cid, api='/ip4/127.0.0.1/tcp/5001')
        target = self.root / self.cid / 'index.html'
        target.write_bytes(b'tampered')
        with self.assertRaisesRegex(ValueError, 'file hash'):
            cm.verify(self.root, self.cid)
        target.write_bytes(self.body)
        with (self.root / '_cars' / (self.cid + '.car')).open('ab') as stream:
            stream.write(b'\x02\0')
        with self.assertRaises(ValueError):
            cm.verify(self.root, self.cid)

    def test_car_checks_root_multihash_and_truncation(self):
        archive = self.base / 'test.car'
        archive.write_bytes(self.car)
        self.assertEqual(cm.verify_car(archive, self.cid), 1)
        other, _, _ = fixture(b'another')
        with self.assertRaisesRegex(ValueError, 'root CID'):
            cm.verify_car(archive, other)
        archive.write_bytes(self.car[:-1] + bytes([self.car[-1] ^ 1]))
        with self.assertRaisesRegex(ValueError, 'multihash'):
            cm.verify_car(archive, self.cid)
        archive.write_bytes(self.car[:-5])
        with self.assertRaisesRegex(ValueError, 'Truncated CAR block'):
            cm.verify_car(archive, self.cid)

    def test_empty_raw_car_block_is_valid(self):
        cid, car, _ = fixture(b'')
        archive = self.base / 'empty.car'
        archive.write_bytes(car)
        self.assertEqual(cm.verify_car(archive, cid), 1)

    def test_invalid_cid_remote_api_and_symlinks(self):
        for bad in ['../bad', 'bOOPS', 'Qmxxx', '', 'b123', 'https://example.org']:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                cm.decode_cid(bad)
        with self.assertRaisesRegex(ValueError, 'loopback'):
            cm.publish(self.root, self.cid, api='/ip4/0.0.0.0/tcp/5001')
        with patch.object(cm, '_run_ipfs', self.mock_ipfs):
            cm.publish(self.root, self.cid, api='/ip4/127.0.0.1/tcp/5001')
        (self.root / self.cid / 'src' / 'escape').symlink_to('/etc/passwd')
        with self.assertRaisesRegex(ValueError, 'Symlink'):
            cm.verify(self.root, self.cid)

    def test_file_root_exposed_as_content(self):
        def fake(binary, api, timeout, args, *, stdout=None):
            if args[:2] == ['dag', 'export']:
                stdout.write(self.car)
            else:
                Path(args[1].split('=', 1)[1]).write_bytes(self.body)
        with patch.object(cm, '_run_ipfs', fake):
            cm.publish(self.root, self.cid, api='/ip4/127.0.0.1/tcp/5001')
        self.assertEqual((self.root / self.cid / 'content').read_bytes(), self.body)
        self.assertEqual(cm.verify(self.root, self.cid)['entrypoint'], 'content')


if __name__ == '__main__':
    unittest.main()

"""Response folders need no Python PDF/image packages."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import shutil
import struct
import tempfile
import unittest
from unittest.mock import patch
import zlib

from fileproxy.core import load_catalog
from fileproxy.packets import build_packet, pdf_thumbnail


def png_bytes():
    def chunk(kind, data):
        return struct.pack('!I', len(data)) + kind + data + struct.pack('!I', zlib.crc32(kind + data))
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('!2I5B', 1, 1, 8, 2, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(b'\0\xff\xff\xff')) + chunk(b'IEND', b''))


def pdf_bytes():
    """Two visible pages, constructed without a PDF library."""
    stream = b'0 0 0 rg 10 10 30 30 re f\n'
    objects = [b'<< /Type /Catalog /Pages 2 0 R >>',
               b'<< /Type /Pages /Count 2 /Kids [3 0 R 5 0 R] >>',
               b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 72 72] /Contents 4 0 R >>',
               b'<< /Length ' + str(len(stream)).encode() + b' >>\nstream\n' + stream + b'endstream',
               b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 72 72] /Contents 4 0 R >>']
    data, offsets = b'%PDF-1.4\n', [0]
    for number, content in enumerate(objects, 1):
        offsets.append(len(data))
        data += str(number).encode() + b' 0 obj\n' + content + b'\nendobj\n'
    start = len(data)
    data += b'xref\n0 6\n0000000000 65535 f \n'
    data += b''.join(f'{offset:010d} 00000 n \n'.encode() for offset in offsets[1:])
    return data + f'trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{start}\n%%EOF\n'.encode()


class PacketTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.case = self.root / 'case'
        self.case.mkdir()
        self.config = {'version': 1, 'roots': {'work': str(self.root)}}
        self.letter = self.case / 'response.html'
        self.letter.write_text('<p>Response source</p>')
        (self.case / 'scan.png').write_bytes(png_bytes())
        (self.case / 'not-added.png').write_bytes(png_bytes())
        self.request = {'root': 'work', 'directory': 'case', 'title': 'Response',
                        'folderName': 'response-1', 'note': 'Included the actual NCS response.',
                        'letter': {'path': 'case/response.html', 'sha256': sha256(self.letter.read_bytes()).hexdigest(),
                                   'blocks': [{'kind': 'paragraph', 'text': 'My response letter.'}]},
                        'attachments': [self.enclosure('scan.png')]}

    def enclosure(self, name):
        return {'path': 'case/' + name, 'sha256': sha256((self.case / name).read_bytes()).hexdigest(),
                'label': 'NCS correspondence'}

    def test_html_lists_only_added_files_and_copies_original_bytes_in_order(self):
        result = build_packet(self.config, self.request)
        folder = self.root / result['directory']
        html = (self.root / result['path']).read_text()
        self.assertFalse(result['draft'])
        self.assertIn('My response letter.', html)
        self.assertIn('NCS correspondence', html)
        self.assertIn(self.request['note'], html)
        self.assertNotIn('not-added', html)
        self.assertNotIn('Lease agreement', html)
        self.assertIn('src="001-scan.png"', html)
        self.assertIn('data-source="case/scan.png"', html)
        self.assertNotIn(self.request['attachments'][0]['sha256'], html)
        self.assertNotIn('SHA-256:', html)
        self.assertIn('Documents included', html)
        self.assertEqual((folder / '001-scan.png').read_bytes(), (self.case / 'scan.png').read_bytes())
        self.assertEqual(sorted(path.name for path in folder.iterdir()), ['001-scan.png', 'index.html', 'letter.html'])
        self.assertIn(result['path'], [row['path'] for row in load_catalog(self.config)['entries']])

    def test_inline_documents_follow_the_selected_text_and_same_position_order(self):
        self.request['letter']['blocks'] = [
            {'kind': 'paragraph', 'text': 'First request.'},
            {'kind': 'paragraph', 'text': 'Response and unanswered questions.'},
            {'kind': 'pagebreak'},
            {'kind': 'paragraph', 'text': 'Requested action.'}]
        (self.case / 'second.png').write_bytes(png_bytes())
        self.request['attachments'] = [
            {**self.enclosure('scan.png'), 'label': 'Mailing record 01', 'afterBlock': 0},
            {**self.enclosure('second.png'), 'label': 'Mailing record 02', 'afterBlock': 0},
            {**self.enclosure('not-added.png'), 'label': 'Later response', 'afterBlock': 1}]
        result = build_packet(self.config, self.request)
        html = (self.root / result['path']).read_text().split('</style>')[1]
        order = [html.index(text) for text in ('First request.', 'src="001-scan.png"',
                 'src="002-second.png"', 'Response and unanswered questions.',
                 'src="003-not-added.png"', 'Requested action.', 'Documents included')]
        self.assertEqual(order, sorted(order))
        self.assertEqual(html.count('src="001-scan.png"'), 1)
        self.assertEqual(result['pages'], 7)
        self.assertNotIn('scan-page', (self.root / result['letterPath']).read_text().split('</style>')[1])

    def test_blank_caption_omits_the_scan_caption_but_identifies_the_file_in_the_index(self):
        self.request['attachments'][0]['label'] = ''
        result = build_packet(self.config, self.request)
        html = (self.root / result['path']).read_text().split('</style>')[1]
        self.assertNotIn('class="scan-caption"', html)
        self.assertIn('1. scan.png', html)

    def test_invalid_placement_cannot_silently_move_evidence_or_create_a_folder(self):
        self.request['letter']['blocks'].append({'kind': 'pagebreak'})
        for after in (-1, 1, 2, True, '0', 0.5):
            self.request['attachments'][0]['afterBlock'] = after
            with self.subTest(after=after), self.assertRaisesRegex(ValueError, 'narrative block'):
                build_packet(self.config, self.request)
            self.assertFalse((self.case / 'response-1').exists())

    def test_saved_letter_is_reusable_and_excludes_the_enclosure_index(self):
        self.request['letter']['blocks'] = [{'kind': 'address', 'text': 'From: [NAME]\nMailing address'},
                                           {'kind': 'pagebreak'}, {'kind': 'signature', 'text': 'Signature'}]
        result = build_packet(self.config, self.request)
        letter = (self.root / result['letterPath']).read_text()
        self.assertTrue(result['draft'])
        self.assertIn('DRAFT', letter)
        self.assertIn('class="addr"', letter)
        self.assertIn('Mailing address', letter)
        self.assertNotIn('NCS correspondence', letter)
        self.assertNotIn('scan-page', letter.split('</style>')[1])
        self.request['letter']['path'] = result['letterPath']
        self.request['letter']['sha256'] = sha256((self.root / result['letterPath']).read_bytes()).hexdigest()
        self.request['folderName'] = 'response-2'
        second = build_packet(self.config, self.request)
        self.assertNotEqual(result['path'], second['path'])
        self.assertTrue((self.root / result['path']).exists())

    def test_html_escapes_letter_note_and_labels(self):
        self.request['letter']['blocks'][0]['text'] = '<script>bad()</script>'
        self.request['note'] = '<img src="outside">'
        self.request['attachments'][0]['label'] = '"><script>bad()</script>'
        result = build_packet(self.config, self.request)
        html = (self.root / result['path']).read_text()
        self.assertNotIn('<script>', html)
        self.assertIn('&lt;script&gt;', html)
        self.assertIn('&lt;img src=&quot;outside&quot;&gt;', html)

    def test_missing_changed_or_duplicate_sources_leave_no_partial_response(self):
        for mode in ('missing', 'changed', 'duplicate', 'letter-changed'):
            request = deepcopy(self.request)
            if mode == 'missing':
                request['attachments'][0]['path'] = 'case/absent.png'
            elif mode == 'changed':
                request['attachments'][0]['sha256'] = '0' * 64
            elif mode == 'letter-changed':
                request['letter']['sha256'] = '0' * 64
            else:
                request['attachments'] *= 2
            with self.subTest(mode=mode), self.assertRaises((FileNotFoundError, FileExistsError, ValueError)):
                build_packet(self.config, request)
            self.assertFalse((self.case / 'response-1').exists())
            self.assertFalse(list(self.case.glob('.fileproxy-response-*')))

    def test_existing_folder_is_never_replaced(self):
        (self.case / 'response-1').mkdir()
        keep = self.case / 'response-1' / 'keep.txt'
        keep.write_text('Keep this')
        with self.assertRaises(FileExistsError):
            build_packet(self.config, self.request)
        self.assertEqual(keep.read_text(), 'Keep this')

    def test_shell_tool_is_needed_only_for_pdf_inputs_and_failure_keeps_sources(self):
        pdf = self.case / 'ncs.pdf'
        pdf.write_bytes(pdf_bytes())
        self.request['attachments'] = [self.enclosure('ncs.pdf')]
        with patch('fileproxy.packets.shutil.which', return_value=None):
            with self.assertRaisesRegex(ValueError, 'shell.*pdftoppm'):
                build_packet(self.config, self.request)
        self.assertFalse((self.case / 'response-1').exists())
        self.assertFalse(list(self.case.glob('.fileproxy-response-*')))
        self.assertEqual(pdf.read_bytes(), pdf_bytes())

    @unittest.skipUnless(shutil.which('pdftoppm'), 'Shell pdftoppm not installed')
    def test_real_shell_pdf_renderer_creates_relative_page_images(self):
        (self.case / 'ncs.pdf').write_bytes(pdf_bytes())
        self.request['attachments'] = [self.enclosure('ncs.pdf')]
        result = build_packet(self.config, self.request)
        folder = self.root / result['directory']
        self.assertEqual(result['attachments'][0]['pageCount'], 2)
        self.assertEqual((folder / '001-ncs.pdf').read_bytes(), pdf_bytes())
        self.assertEqual(len(list((folder / 'pages').glob('*.png'))), 2)
        html = (folder / 'index.html').read_text()
        self.assertIn('src="pages/001-page-1.png"', html)
        self.assertIn('src="pages/001-page-2.png"', html)

    @unittest.skipUnless(shutil.which('pdftoppm'), 'Shell pdftoppm not installed')
    def test_pdf_thumbnail_is_a_small_first_page_and_reuses_cached_bytes(self):
        source = self.case / 'preview.pdf'
        source.write_bytes(pdf_bytes())
        stat = source.stat()
        image = pdf_thumbnail(str(source), stat.st_mtime_ns, stat.st_size)
        self.assertEqual(image[:8], b'\x89PNG\r\n\x1a\n')
        width, height = struct.unpack('!II', image[16:24])
        self.assertLessEqual(max(width, height), 240)
        with patch('fileproxy.packets.subprocess.run', side_effect=AssertionError('cached preview rerendered')):
            self.assertEqual(pdf_thumbnail(str(source), stat.st_mtime_ns, stat.st_size), image)


if __name__ == '__main__':
    unittest.main()

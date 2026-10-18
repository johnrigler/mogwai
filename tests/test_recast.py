import importlib.util
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib

ROOT = Path(__file__).resolve().parents[1]
RENDER = ROOT / 'tools/recast/render.py'
spec = importlib.util.spec_from_file_location('recast_renderer', RENDER)
renderer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(renderer)


def embed():
    return '/* Generated from render.py; regenerate with tests/test_recast.py --embed. */\nwindow.RecastRenderPython = ' + json.dumps(RENDER.read_text()) + ';\n'


def png(width, height, right=None, bottom=None):
    pixels = bytearray(width * height * 4)
    for rect, color in [(right, (20, 40, 220, 255)), (bottom, (20, 190, 40, 255))]:
        if rect:
            x, y, w, h = rect
            for yy in range(y, y + h):
                for xx in range(x, x + w):
                    pixels[(yy * width + xx) * 4:(yy * width + xx) * 4 + 4] = bytes(color)
    rows = b''.join(b'\0' + pixels[y*width*4:(y+1)*width*4] for y in range(height))
    def chunk(tag, value):
        return struct.pack('>I', len(value)) + tag + value + struct.pack('>I', zlib.crc32(tag + value))
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(rows)) + chunk(b'IEND', b'')


class RecastTest(unittest.TestCase):
    def project(self):
        return {'format': 'mogwai-recast-v1', 'width': 320, 'height': 240, 'cues': [{'at': i * .5, 'layout': layout} for i, layout in enumerate(['full', 'side', 'desk', 'right', 'full'])]}

    def test_exported_renderer_matches_source(self):
        self.assertEqual((ROOT / 'tools/recast/render-source.js').read_text(), embed())

    def test_malformed_project_rejected(self):
        for change in [{'width': 321}, {'height': True}, {'format': 'other'}, {'cues': []}, {'cues': [{'at': float('nan'), 'layout': 'full'}]}, {'cues': [{'at': 1, 'layout': 'full'}]}, {'cues': [{'at': 0, 'layout': 'script'}]}]:
            with self.subTest(change=change), self.assertRaises(ValueError):
                renderer.validate({**self.project(), **change})

    def test_original_audio_is_mapped_without_filtering(self):
        with tempfile.TemporaryDirectory() as name:
            folder = Path(name); (folder / 'overlays').mkdir()
            for i in range(5): (folder / 'overlays' / f'{i:03d}.png').write_bytes(png(320, 240))
            command, _, graph = renderer.build_command(self.project(), 'a file;$(x).mp4', 'out.mp4', folder, 2.4, '12/1')
            self.assertIn('a file;$(x).mp4', command)
            self.assertEqual(command[command.index('-c:a')+1], 'copy')
            self.assertIn('0:a?', command)
            self.assertNotIn('atrim', graph)
            self.assertNotIn('concat', graph)

    @unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'FFmpeg integration requires ffmpeg and ffprobe')
    def test_fractional_frame_cue_switches_on_the_exact_frame(self):
        with tempfile.TemporaryDirectory() as name:
            folder = Path(name); (folder / 'overlays').mkdir()
            frame = 1001 / 30000
            project = {**self.project(), 'cues': [{'at': 0, 'layout': 'full'}, {'at': frame * 2, 'layout': 'side'}, {'at': frame * 3, 'layout': 'full'}]}
            (folder / 'project.json').write_text(json.dumps(project)); shutil.copyfile(RENDER, folder / 'render.py')
            for i, cue in enumerate(project['cues']):
                (folder / 'overlays' / f'{i:03d}.png').write_bytes(png(320, 240, right=(212, 0, 108, 240) if cue['layout'] == 'side' else None))
            source = folder / 'original.mp4'; output = folder / 'result.mp4'
            subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'color=c=red:s=160x120:r=30000/1001:d=0.4', '-c:v', 'libx264', '-threads', '1', '-y', str(source)], check=True)
            result = subprocess.run([sys.executable, str(folder / 'render.py'), str(source), str(output)], capture_output=True, text=True, timeout=45)
            self.assertEqual(result.returncode, 0, result.stderr[-6000:])
            frames = subprocess.check_output(['ffmpeg', '-v', 'error', '-i', str(output), '-frames:v', '5', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'])
            stride = 320 * 240 * 3
            def pixel(i):
                start = i * stride + (100 * 320 + 300) * 3
                return tuple(frames[start:start + 3])
            for i in [0, 1, 3, 4]: self.assertTrue(pixel(i)[0] > 180 and pixel(i)[2] < 70, (i, pixel(i)))
            self.assertTrue(pixel(2)[2] > 150 and pixel(2)[0] < 70, pixel(2))

    @unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'FFmpeg integration requires ffmpeg and ffprobe')
    def test_rendered_layout_pixels_and_audio_payload(self):
        with tempfile.TemporaryDirectory() as name:
            folder = Path(name); (folder / 'overlays').mkdir(); project = self.project()
            (folder / 'project.json').write_text(json.dumps(project)); shutil.copyfile(RENDER, folder / 'render.py')
            for i, cue in enumerate(project['cues']):
                layout = cue['layout']; right = None if layout == 'full' else ((0,0,108,240) if layout=='right' else (212,0,108,240)); bottom = (108,160,212,80) if layout=='right' else (0,160,212,80) if layout=='desk' else None
                (folder / 'overlays' / f'{i:03d}.png').write_bytes(png(320, 240, right, bottom))
            source = folder / 'original.mp4'; output = folder / 'result.mp4'
            subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=c=red:s=160x120:r=12:d=2.4','-f','lavfi','-i','sine=frequency=440:sample_rate=44100:duration=2.4','-c:v','libx264','-threads','1','-c:a','aac','-y',str(source)],check=True)
            result = subprocess.run([sys.executable,str(folder/'render.py'),str(source),str(output)],capture_output=True,text=True,timeout=45)
            self.assertEqual(result.returncode,0,result.stderr[-6000:])
            def audio(path):
                return subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-map','0:a:0','-c:a','copy','-f','hash','-hash','sha256','-'],text=True)
            self.assertEqual(audio(source),audio(output))
            def pixel(second,x,y):
                frame = subprocess.check_output(['ffmpeg','-v','error','-ss',str(second),'-i',str(output),'-frames:v','1','-f','rawvideo','-pix_fmt','rgb24','-'])
                start=(y*320+x)*3
                return tuple(frame[start:start+3])
            red=lambda p:p[0]>180 and p[1]<70 and p[2]<70
            blue=lambda p:p[2]>150 and p[0]<70
            green=lambda p:p[1]>130 and p[0]<80
            self.assertTrue(red(pixel(.25,16,16)))
            self.assertTrue(blue(pixel(.75,300,100)))
            self.assertFalse(red(pixel(.75,32,8)))
            self.assertTrue(red(pixel(1.25,32,32)))
            self.assertTrue(green(pixel(1.25,32,200)))
            self.assertTrue(blue(pixel(1.75,16,100)))
            self.assertTrue(red(pixel(1.75,200,32)))
            self.assertTrue(green(pixel(1.75,200,200)))
            self.assertTrue(red(pixel(2.15,16,16)))


if __name__ == '__main__':
    if '--embed' in sys.argv:
        (ROOT/'tools/recast/render-source.js').write_text(embed())
    else:
        unittest.main()

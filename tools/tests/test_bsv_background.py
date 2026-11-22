import fcntl
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


class BackgroundScriptsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.tools = self.root / 'tools'
        self.tools.mkdir()
        source = Path(__file__).resolve().parents[1]
        for name in ('bsv.sh', 'bsv-start.sh', 'bsv-stop.sh'):
            shutil.copyfile(source / name, self.tools / name)
        # A local daemon exercises actual nohup, PID checks, locks and SIGTERM
        # without contacting a public provider or touching the user's scan DB.
        (self.tools / 'bsv_indexer.py').write_text('''import argparse, json, signal, time
from pathlib import Path
p = argparse.ArgumentParser()
p.add_argument('command')
p.add_argument('--db')
p.add_argument('--export-dir')
p.add_argument('--interval')
a = p.parse_args()
if a.command == 'status':
    print(json.dumps({'db': a.db, 'jobs': []}), flush=True)
else:
    def stop(*_):
        Path(a.db + '.stopped').write_text('checkpoint saved')
        raise SystemExit(0)
    signal.signal(signal.SIGTERM, stop)
    Path(a.db + '.started').write_text(json.dumps(vars(a)))
    print('scanner started', flush=True)
    while True:
        time.sleep(0.01)
''')
        self.env = dict(os.environ, HOME=str(self.root), XDG_STATE_HOME=str(self.root / 'state'),
                        BSV_DB=str(self.root / 'scan.sqlite3'), BSV_EXPORT_DIR=str(self.root / 'public'))
        self.state = self.root / 'state/mogwai/bsv-daemon'
        self.pid_file = self.state / 'daemon.pid'

    def run_script(self, name, *args):
        return subprocess.run(['bash', str(self.tools / name), *args], env=self.env,
                              text=True, capture_output=True, timeout=10)

    def tearDown(self):
        try:
            self.run_script('bsv-stop.sh')
        finally:
            self.temp.cleanup()

    def test_start_detaches_is_idempotent_reports_status_and_stops_gracefully(self):
        started = self.run_script('bsv-start.sh', '--interval', '7')
        self.assertEqual(started.returncode, 0, started.stderr)
        pid = int(self.pid_file.read_text())
        details = json.loads(Path(self.env['BSV_DB'] + '.started').read_text())
        self.assertEqual((details['db'], details['export_dir'], details['interval']),
                         (self.env['BSV_DB'], self.env['BSV_EXPORT_DIR'], '7'))
        self.assertIn('scanner started', (self.state / 'daemon.log').read_text())
        again = self.run_script('bsv-start.sh')
        self.assertEqual(again.returncode, 0, again.stderr)
        self.assertIn('already running', again.stdout)
        self.assertEqual(int(self.pid_file.read_text()), pid)
        observed = self.run_script('bsv.sh', 'status')
        self.assertEqual(observed.returncode, 0, observed.stderr)
        self.assertIn('running (PID %d)' % pid, observed.stdout)
        self.assertIn(self.env['BSV_DB'], observed.stdout)
        stopped = self.run_script('bsv-stop.sh')
        self.assertEqual(stopped.returncode, 0, stopped.stderr)
        self.assertIn('Stopped BSV scanner', stopped.stdout)
        self.assertEqual(Path(self.env['BSV_DB'] + '.stopped').read_text(), 'checkpoint saved')
        self.assertFalse(self.pid_file.exists())
        self.assertIn('No managed', self.run_script('bsv-stop.sh').stdout)

    def test_stale_pid_file_never_signals_an_unrelated_process(self):
        other = subprocess.Popen(['sleep', '30'])
        try:
            self.state.mkdir(parents=True)
            self.pid_file.write_text(str(other.pid) + '\n')
            stopped = self.run_script('bsv-stop.sh')
            self.assertEqual(stopped.returncode, 0, stopped.stderr)
            self.assertIsNone(other.poll())
            self.assertFalse(self.pid_file.exists())
        finally:
            other.terminate()
            other.wait(timeout=5)

    def test_database_lock_blocks_an_unmanaged_duplicate(self):
        with open(self.env['BSV_DB'] + '.lock', 'w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = self.run_script('bsv-start.sh')
        self.assertEqual(result.returncode, 1)
        self.assertIn('database is in use', result.stderr)
        self.assertFalse(self.pid_file.exists())

    def test_optional_config_selects_public_export_directory(self):
        config = self.root / '.config/mogwai/bsv.env'
        config.parent.mkdir(parents=True)
        target = self.root / 'apache data/bsv'
        config.write_text('BSV_EXPORT_DIR="%s"\n' % target)
        result = self.run_script('bsv-start.sh')
        self.assertEqual(result.returncode, 0, result.stderr)
        details = json.loads(Path(self.env['BSV_DB'] + '.started').read_text())
        self.assertEqual(details['export_dir'], str(target))
        self.assertTrue(target.is_dir())


if __name__ == '__main__':
    unittest.main()

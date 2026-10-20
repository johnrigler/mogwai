import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
FUNCTION = ROOT / 'tools/home-config/m.pull'


def git(folder, *args, check=True):
    return subprocess.run(
        ['git', '-c', 'user.name=Pull Test', '-c', 'user.email=pull@example.test', *args],
        cwd=folder, text=True, capture_output=True, check=check, timeout=15,
    )


class HomePullTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name)
        self.remote = self.folder / 'remote.git'
        git(self.folder, 'init', '--bare', '--initial-branch=main', str(self.remote))
        self.writer = self.folder / 'writer'
        git(self.folder, 'clone', str(self.remote), str(self.writer))
        self.commit('record', 'first')
        git(self.writer, 'push', '-u', 'origin', 'main')
        # Literal shell characters/spaces must be treated as part of the path.
        self.checkout = self.folder / 'checkout $literal; name'
        git(self.folder, 'clone', str(self.remote), str(self.checkout))
        self.config = self.folder / 'config.json'
        self.configure({'test': {'path': str(self.checkout)}})

    def configure(self, projects):
        self.config.write_text(json.dumps({'projects': projects}))

    def commit(self, name, text):
        (self.writer / name).write_text(text)
        git(self.writer, 'add', name)
        git(self.writer, 'commit', '-m', text)

    def advance(self, name='record', text='remote update'):
        self.commit(name, text)
        git(self.writer, 'push')

    def pull(self, source=FUNCTION):
        return subprocess.run(
            ['bash', '--noprofile', '--norc', '-c',
             'source "$1"; shift; before=$PWD; m.pull "$@"; result=$?; '
             'test "$PWD" = "$before" || exit 99; exit "$result"',
             'bash', str(source), str(self.config)],
            cwd=self.folder, text=True, capture_output=True, timeout=25,
        )

    def test_fast_forward_non_main_upstream_and_repeated_run(self):
        git(self.checkout, 'checkout', '-b', 'local-name', '--track', 'origin/main')
        self.advance()
        result = self.pull()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('1 updated', result.stdout)
        self.assertEqual((self.checkout / 'record').read_text(), 'remote update')
        self.assertEqual(git(self.checkout, 'branch', '--show-current').stdout.strip(), 'local-name')
        result = self.pull()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('1 unchanged', result.stdout)

    def test_dirty_and_untracked_files_are_preserved_and_other_checkout_updates(self):
        clean = self.folder / 'clean'
        git(self.folder, 'clone', str(self.remote), str(clean))
        self.advance()
        (self.checkout / 'record').write_text('local edit')
        self.configure({'dirty': {'path': str(self.checkout)}, 'clean': {'path': str(clean)}})
        result = self.pull()
        self.assertEqual(result.returncode, 1)
        self.assertIn('local changes', result.stdout)
        self.assertEqual((self.checkout / 'record').read_text(), 'local edit')
        self.assertEqual((clean / 'record').read_text(), 'remote update')
        git(self.checkout, 'restore', 'record')
        (self.checkout / 'untracked').write_text('keep')
        self.assertIn('local changes or untracked files', self.pull().stdout)
        self.assertEqual((self.checkout / 'untracked').read_text(), 'keep')

    def test_divergence_and_autostash_settings_never_discard_local_commit(self):
        (self.checkout / 'local').write_text('local commit')
        git(self.checkout, 'add', 'local')
        git(self.checkout, 'commit', '-m', 'local')
        before = git(self.checkout, 'rev-parse', 'HEAD').stdout
        git(self.checkout, 'config', 'pull.rebase', 'true')
        git(self.checkout, 'config', 'merge.autoStash', 'true')
        self.advance()
        result = self.pull()
        self.assertEqual(result.returncode, 1)
        self.assertIn('fast-forward refused', result.stdout)
        self.assertEqual(git(self.checkout, 'rev-parse', 'HEAD').stdout, before)
        self.assertEqual(git(self.checkout, 'stash', 'list').stdout, '')
        self.assertEqual((self.checkout / 'local').read_text(), 'local commit')

    def test_incoming_file_does_not_overwrite_ignored_local_data(self):
        self.commit('.gitignore', 'catalog.sqlite3\n')
        git(self.writer, 'push')
        self.assertEqual(self.pull().returncode, 0)
        (self.checkout / 'catalog.sqlite3').write_bytes(b'local database')
        (self.writer / 'catalog.sqlite3').write_bytes(b'remote database')
        git(self.writer, 'add', '-f', 'catalog.sqlite3')
        git(self.writer, 'commit', '-m', 'publish database')
        git(self.writer, 'push')
        before = git(self.checkout, 'rev-parse', 'HEAD').stdout
        result = self.pull()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual((self.checkout / 'catalog.sqlite3').read_bytes(), b'local database')
        self.assertEqual(git(self.checkout, 'rev-parse', 'HEAD').stdout, before)

    def test_missing_nested_detached_and_no_upstream_paths_are_skipped(self):
        nested = self.checkout / 'nested'
        nested.mkdir()
        self.configure({'missing': {'path': str(self.folder / 'missing')}, 'nested': {'path': str(nested)}})
        result = self.pull()
        self.assertEqual(result.returncode, 1)
        self.assertIn('directory does not exist', result.stdout)
        self.assertIn('not the root', result.stdout)
        self.configure({'detached': {'path': str(self.checkout)}})
        git(self.checkout, 'checkout', '--detach')
        self.assertIn('detached HEAD', self.pull().stdout)
        git(self.checkout, 'checkout', 'main')
        git(self.checkout, 'branch', '--unset-upstream')
        self.assertIn('no upstream', self.pull().stdout)

    def test_in_progress_operation_is_skipped_even_with_a_clean_index(self):
        self.advance()
        marker = git(self.checkout, 'rev-parse', '--git-path', 'MERGE_HEAD').stdout.strip()
        (self.checkout / marker).write_text(git(self.checkout, 'rev-parse', 'HEAD').stdout)
        before = git(self.checkout, 'rev-parse', 'HEAD').stdout
        result = self.pull()
        self.assertEqual(result.returncode, 1)
        self.assertIn('in progress', result.stdout)
        self.assertEqual(git(self.checkout, 'rev-parse', 'HEAD').stdout, before)
        self.assertTrue((self.checkout / marker).exists())

    def test_failed_fetch_continues_and_duplicate_aliases_only_pull_once(self):
        clean = self.folder / 'clean'
        git(self.folder, 'clone', str(self.remote), str(clean))
        git(self.checkout, 'remote', 'set-url', 'origin', str(self.folder / 'missing.git'))
        self.advance()
        self.configure({'broken': {'path': str(self.checkout)}, 'clean': {'path': str(clean)}, 'alias': {'path': str(clean)}})
        result = self.pull()
        self.assertEqual(result.returncode, 1)
        self.assertIn('fetch failed', result.stdout)
        self.assertIn('SAME checkout', result.stdout)
        self.assertIn('1 updated', result.stdout)
        self.assertEqual((clean / 'record').read_text(), 'remote update')

    def test_config_is_validated_before_fetch_and_relative_paths_are_home_relative(self):
        self.advance()
        before = git(self.checkout, 'rev-parse', 'HEAD').stdout
        self.configure({'valid': {'path': str(self.checkout)}, 'invalid': {'path': 5}})
        result = self.pull()
        self.assertEqual(result.returncode, 2)
        self.assertEqual(git(self.checkout, 'rev-parse', 'HEAD').stdout, before)
        self.config.write_text('[]')
        malformed = self.pull()
        self.assertEqual(malformed.returncode, 2)
        self.assertNotIn('Traceback', malformed.stderr)
        self.configure({'relative': {'path': os.path.relpath(self.checkout, Path.home())}})
        self.assertEqual(self.pull().returncode, 0)
        self.assertEqual((self.checkout / 'record').read_text(), 'remote update')

    def test_portable_canonical_snapshot_identity_and_usage(self):
        definition = subprocess.check_output(['bash', '--noprofile', '--norc', '-c', 'source "$1"; declare -f m.pull', 'bash', str(FUNCTION)])
        self.assertEqual(definition, FUNCTION.read_bytes())
        prefix = int(hashlib.sha256(definition).hexdigest()[:4], 16)
        shoctal = '02' + ''.join(str(int(digit) + 2) for digit in format(prefix, '06o'))
        self.assertEqual(FUNCTION.resolve().name, f'm.pull-{shoctal}-{len(definition)}')
        copied = self.folder / 'copied-function'
        copied.write_bytes(definition)
        self.assertEqual(self.pull(copied).returncode, 0)
        result = subprocess.run(['bash', '--noprofile', '--norc', '-c', 'source "$1"; m.pull one two', 'bash', str(FUNCTION)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)


if __name__ == '__main__':
    unittest.main()

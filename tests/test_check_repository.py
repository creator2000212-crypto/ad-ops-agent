"""The repository checker catches what it claims to, and the public tree passes it.

Every sensitive sample here is assembled at runtime from pieces, so this file
never contains a string the checker looks for; the checker scans it like any
other file. All numbers are made up.
"""
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import check_repository as checker

HOOK = ROOT / '.githooks' / 'pre-commit'


def digits(count, first='4'):
    """A made-up run of ``count`` digits."""
    return (first + '0123456789' * 2)[:count]


def account_id(count=10):
    return 'act' + '_' + digits(count)


class DisclosurePatternTests(unittest.TestCase):
    def labels(self, text, path='docs/sample.md'):
        return checker.scan_text(path, text)

    def test_ad_account_id_is_flagged(self):
        for text in (account_id(), 'id=' + account_id(6), '"' + account_id(16) + '"'):
            with self.subTest(text=text):
                self.assertIn('ad account ID', self.labels(text))

    def test_short_or_embedded_account_prefix_is_not_flagged(self):
        for text in ('act' + '_' + digits(5), 'contact' + '_' + digits(9), 'acct-a', 'act_on_it'):
            with self.subTest(text=text):
                self.assertNotIn('ad account ID', self.labels(text))

    def test_standalone_long_numeric_id_is_flagged(self):
        for count in (15, 16, 19):
            for text in (digits(count), '"page_id": "' + digits(count) + '"', 'pixel ' + digits(count) + '.'):
                with self.subTest(text=text):
                    self.assertIn('long numeric ID', self.labels(text))

    def test_numbers_that_are_not_ids_are_not_flagged(self):
        samples = {
            'too short': digits(14),
            'too long': digits(20),
            'inside a hex hash': 'ab' + digits(16) + 'cd',
            'decimal fraction': '0.' + digits(16),
            'decimal with a long integer part': digits(16) + '.5',
            'word suffix': digits(16) + 'px',
        }
        for name, text in samples.items():
            with self.subTest(name):
                self.assertNotIn('long numeric ID', self.labels(text))

    def test_long_article_id_in_public_help_url_is_exempt(self):
        number = digits(16)
        help_url = 'https://www.facebook.com/business/help/' + number
        self.assertNotIn('long numeric ID', self.labels('Source: ' + help_url))
        other_url = 'https://example.com/report?object=' + number
        self.assertIn('long numeric ID', self.labels('Source: ' + other_url))
        both = help_url + ' and object ' + number
        self.assertIn('long numeric ID', self.labels(both))

    def test_token_in_url_is_flagged(self):
        secret = 'tok' + 'en='
        for text in ('https://graph.example.com/v1/me?access_' + secret + 'abc',
                     'http://example.com/cb?a=1&' + secret + 'xyz',
                     'https://example.com/#id_' + secret + 'abc'):
            with self.subTest(text=text):
                self.assertIn('token in URL', self.labels(text))

    def test_token_word_outside_a_url_is_not_flagged(self):
        text = 'Store the access ' + 'tok' + 'en' + ' in the client configuration; never paste ' + 'tok' + 'en= values.'
        self.assertNotIn('token in URL', self.labels(text))

    def test_referral_fragment_is_flagged(self):
        text = 'https://connector.example.com/' + '#' + 'via' + '=someone'
        self.assertIn('referral link fragment', self.labels(text))
        self.assertNotIn('referral link fragment', self.labels('https://connector.example.com/#pricing'))

    def test_existing_patterns_still_fire(self):
        samples = {
            'personal workspace path': '/' + 'Users/someone/project',
            'GitHub token': 'gh' + 'p_' + 'A' * 24,
            'API key': 's' + 'k-' + 'a' * 30,
            'private key': '-----BEGIN ' + 'PRIVATE KEY-----',
        }
        for label, text in samples.items():
            with self.subTest(label):
                self.assertIn(label, self.labels(text))


class PolicyWordingTests(unittest.TestCase):
    HASH = '哈' + '希'

    def samples(self):
        return ['改' + self.HASH, '换个' + self.HASH, '换一下' + self.HASH, '换' + self.HASH,
                'Re' + 'hash the video', 're-' + 'hash it', 'RE' + 'HASH']

    def test_circumvention_wording_is_flagged_in_public_prose_and_fixtures(self):
        for path in ('docs/a.md', 'contracts/a.json', 'examples/a.json', 'knowledge/catalog.json',
                     'demo/README.md', 'templates/task-record.md', 'README.md', 'AGENTS.md'):
            for text in self.samples():
                with self.subTest(path=path, text=text):
                    self.assertIn('ad-review circumvention wording', checker.scan_text(path, text))

    def test_circumvention_wording_is_out_of_scope_in_code_and_tests(self):
        for path in ('operating_rules.py', 'tests/test_x.py', 'scripts/x.py', '.github/workflows/ci.yml'):
            with self.subTest(path=path):
                self.assertEqual(checker.scan_text(path, '改' + self.HASH), [])

    def test_similar_words_are_not_flagged(self):
        for text in ('pre' + 'hashed inputs', 'the file hash (SHA-256)', '换一个更长的句子再说哈' + '希',
                     're-encode', 'Request Review'):
            with self.subTest(text=text):
                self.assertNotIn('ad-review circumvention wording', checker.scan_text('docs/a.md', text))

    def test_traffic_mixing_jargon_is_flagged(self):
        for text in ('混' + '量', 'mixed ' + 'traffic', 'mixed_' + 'traffic_share'):
            with self.subTest(text=text):
                self.assertIn('traffic-mixing jargon', checker.scan_text('examples/a.json', text))

    def test_policy_scope(self):
        self.assertTrue(checker.in_policy_scope('CHANGELOG.md'))
        self.assertTrue(checker.in_policy_scope('docs/disapproval-triage.md'))
        self.assertFalse(checker.in_policy_scope('LICENSE'))
        self.assertFalse(checker.in_policy_scope('readback.py'))
        self.assertFalse(checker.in_policy_scope('tests/test_readback.py'))


class TreeTests(unittest.TestCase):
    def test_checker_and_this_file_do_not_match_themselves(self):
        for path in (ROOT / 'scripts' / 'check_repository.py', Path(__file__).resolve()):
            relative = path.relative_to(ROOT).as_posix()
            with self.subTest(relative):
                self.assertEqual(checker.scan_text(relative, path.read_text(encoding='utf-8')), [])
                # Also as if it were public prose, so the policy patterns are exercised too.
                self.assertEqual(checker.scan_text('docs/' + path.name, path.read_text(encoding='utf-8')), [])

    def test_errors_name_rule_and_path_never_the_value(self):
        number = digits(17)
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'docs').mkdir()
            (Path(tmp) / 'docs' / 'note.md').write_text('object ' + number + '\n', encoding='utf-8')
            errors, _ = checker.check_tree(tmp)
        found = [error for error in errors if not error.startswith('missing required file')]
        self.assertEqual(found, ['long numeric ID: ' + str(Path('docs') / 'note.md')])
        self.assertNotIn(number, json.dumps(errors))

    def asset_errors(self, relative, width, height, padding=0):
        """Write a minimal PNG header at ``relative`` in an empty tree; return the non-REQUIRED errors."""
        header = b'\x89PNG\r\n\x1a\n' + struct.pack('>I', 13) + b'IHDR' + struct.pack('>II', width, height)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp).joinpath(*relative.split('/'))
            path.parent.mkdir(parents=True)
            path.write_bytes(header + b'\0' * padding)
            errors, _ = checker.check_tree(tmp)
        return [error for error in errors if not error.startswith('missing required file')]

    def test_asset_allowlist(self):
        cases = [
            ('docs/assets/hero/hero.en.png', (1760, 880, 0), []),
            ('docs/assets/showcase/hero.png', (1760, 880, 0), ['image outside docs/assets/{hero,proof,social,charts}/']),
            ('docs/assets/hero/big.png', (1760, 880, checker.ASSET_MAX_BYTES), ['image larger than 600 KB']),
            ('docs/assets/social/social-preview.png', (1200, 630, 0), ['social preview must be 1280x640']),
        ]
        for relative, (width, height, padding), expected in cases:
            with self.subTest(relative):
                self.assertEqual(self.asset_errors(relative, width, height, padding),
                                 [label + ': ' + str(Path(relative)) for label in expected])

    def test_required_files_exist_and_are_listed_once(self):
        self.assertEqual(len(checker.REQUIRED), len(set(checker.REQUIRED)))
        missing = [name for name in checker.REQUIRED if not (ROOT / name).is_file()]
        self.assertEqual(missing, [])

    def test_required_covers_every_module_test_doc_fixture_and_script(self):
        groups = ['*.py', '*.md', 'docs/*.md', 'tests/test_*.py', 'scripts/*.py', 'examples/**/*.json',
                  'examples/**/*.md', 'demo/**/*', 'contracts/*', 'templates/*', 'knowledge/*',
                  'docs/assets/src/*', 'docs/assets/*/*.png', 'schemas/*', 'evaluations/*',
                  '.github/**/*', '.githooks/*']
        found = set()
        for pattern in groups:
            for path in ROOT.glob(pattern):
                relative = path.relative_to(ROOT)
                if path.is_file() and not any(part in checker.SKIP for part in relative.parts) \
                        and tuple(relative.parts[:2]) not in checker.SKIP_PREFIXES and path.name != '.DS_Store':
                    found.add(relative.as_posix())
        self.assertEqual(sorted(found - set(checker.REQUIRED)), [],
                         'add these files to REQUIRED in scripts/check_repository.py')

    def test_public_tree_passes_and_prints_relative_paths_only(self):
        completed = subprocess.run([sys.executable, str(ROOT / 'scripts' / 'check_repository.py')],
                                   cwd=str(ROOT), capture_output=True, text=True, timeout=120)
        result = json.loads(completed.stdout)
        self.assertEqual(result['errors'], [])
        self.assertEqual((completed.returncode, result['status']), (0, 'passed'))
        self.assertNotIn(str(ROOT), completed.stdout)

    def test_hook_is_executable(self):
        self.assertTrue(os.access(str(HOOK), os.X_OK), 'chmod +x .githooks/pre-commit')


@unittest.skipUnless(shutil.which('git') and shutil.which('sh') and (ROOT / '.git').exists(),
                     'needs git, sh and a git checkout')
class PreCommitHookTests(unittest.TestCase):
    NOREPLY = '1000+someone@users.noreply.github.com'

    def run_hook(self, author, committer):
        env = dict(os.environ, GIT_AUTHOR_NAME='someone', GIT_AUTHOR_EMAIL=author,
                   GIT_COMMITTER_NAME='someone', GIT_COMMITTER_EMAIL=committer)
        return subprocess.run(['sh', str(HOOK)], cwd=str(ROOT), env=env,
                              capture_output=True, text=True, timeout=120)

    def test_personal_author_email_is_rejected(self):
        completed = self.run_hook('someone@example.com', self.NOREPLY)
        self.assertEqual(completed.returncode, 1)
        self.assertIn('author email is not a GitHub noreply address', completed.stderr)

    def test_personal_committer_email_is_rejected(self):
        completed = self.run_hook(self.NOREPLY, 'someone@example.com')
        self.assertEqual(completed.returncode, 1)
        self.assertIn('committer email is not a GitHub noreply address', completed.stderr)

    def test_noreply_identity_runs_the_checker_and_passes(self):
        completed = self.run_hook(self.NOREPLY, self.NOREPLY)
        self.assertEqual(completed.returncode, 0, completed.stderr)


if __name__ == '__main__':
    unittest.main()

import copy
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import showcase_content as showcase


class ShowcaseContentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.assets = self.root / showcase.ASSETS
        self.assets.mkdir(parents=True)
        for name in ('README.md', 'README.zh-CN.md'):
            shutil.copyfile(showcase.ROOT / name, self.root / name)
        for path in (showcase.ROOT / showcase.ASSETS).iterdir():
            if path.suffix == '.svg' or path.name == 'content.json':
                shutil.copyfile(path, self.assets / path.name)

    def replace_once(self, path, before, after):
        original = path.read_text(encoding='utf-8')
        self.assertIn(before, original)
        path.write_text(original.replace(before, after, 1), encoding='utf-8')
        return original

    def test_current_public_copy_passes(self):
        self.assertEqual(showcase.check_showcase(self.root), [])

    def test_each_variant_is_checked(self):
        for kind in showcase.KINDS:
            for language in showcase.LANGUAGES:
                for theme in showcase.THEMES:
                    for width in showcase.WIDTHS:
                        name = f'{kind}.{language}.{theme}.{width}.svg'
                        with self.subTest(name=name):
                            path = self.assets / name
                            original = self.replace_once(path, '</text>', ' changed</text>')
                            self.assertTrue(any(name in error for error in showcase.check_showcase(self.root)))
                            path.write_text(original, encoding='utf-8')

    def test_single_count_state_date_and_language_mutations_fail(self):
        changes = [
            ('meta.en.dark.narrow.svg', '>20</text>', '>21</text>'),
            ('tiktok.en.light.wide.svg', '>In review</text>', '>Eligible</text>'),
            ('tiktok.zh-CN.dark.narrow.svg', '>审核中</text>', '>可投</text>'),
            ('meta.zh-CN.light.wide.svg', '>2026.09.22</text>', '>2026.09.23</text>'),
            ('tiktok.en.dark.narrow.svg', '>2026.09.22–23</text>', '>2026.09.22–24</text>'),
            ('meta.en.light.wide.svg', '>Creation candidates</text>', '>建单候选</text>'),
        ]
        for name, before, after in changes:
            with self.subTest(name=name, change=after):
                path = self.assets / name
                original = self.replace_once(path, before, after)
                self.assertTrue(any(name in error for error in showcase.check_showcase(self.root)))
                path.write_text(original, encoding='utf-8')

    def test_readme_body_alt_dates_and_evidence_boundaries_fail_independently(self):
        changes = [
            ('README.md', '**20 ad-creation candidates', '**21 ad-creation candidates', '(meta)'),
            ('README.zh-CN.md', '**2 条业务线可投、1 条审核中**', '**3 条业务线可投、0 条审核中**', '(tiktok)'),
            ('README.md', 'alt="Historical Meta preparation: 20', 'alt="Historical Meta preparation: 21', 'alt differs'),
            ('README.zh-CN.md', 'alt="TikTok 历史任务：三条', 'alt="TikTok 历史任务：两条', 'alt differs'),
            ('README.md', 'Meta: 2026-09-22;', 'Meta: 2026-09-23;', 'evidence/date'),
            ('README.zh-CN.md', 'TikTok：2026-09-22—23', 'TikTok：2026-09-22–23', 'evidence/date'),
            ('README.md', 'along with the previous-line handling and unresolved items.', 'with all issues closed.', '(tiktok)'),
            ('README.zh-CN.md', '不据此推断消耗或效果。', '已证明投放效果。', '(tiktok)'),
        ]
        for filename, before, after, expected_error in changes:
            with self.subTest(filename=filename, change=after):
                path = self.root / filename
                original = self.replace_once(path, before, after)
                self.assertTrue(any(filename in error and expected_error in error
                                    for error in showcase.check_showcase(self.root)))
                path.write_text(original, encoding='utf-8')

    def test_unrelated_readme_numbers_are_outside_case_scope(self):
        self.replace_once(self.root / 'README.md', 'three fictional Meta accounts and ten ad sets',
                          'four fictional Meta accounts and twelve ad sets')
        self.assertEqual(showcase.check_showcase(self.root), [])

    def test_picture_sources_cannot_silently_select_wrong_language_or_variant(self):
        path = self.root / 'README.md'
        for before, after in [
            ('meta.en.dark.narrow.png', 'meta.zh-CN.dark.narrow.png'),
            ('tiktok.en.light.narrow.png', 'tiktok.en.dark.wide.png'),
            ('(max-width: 640px) and (prefers-color-scheme: dark)', '(max-width: 800px)'),
        ]:
            with self.subTest(change=after):
                original = self.replace_once(path, before, after)
                self.assertTrue(any('picture sources differ' in error
                                    for error in showcase.check_showcase(self.root)))
                path.write_text(original, encoding='utf-8')

    def test_a_fact_change_marks_existing_presentations_stale(self):
        path = self.assets / 'content.json'
        document = json.loads(path.read_text(encoding='utf-8'))
        for case, field, new in [('meta', 'candidates', 21), ('meta', 'date', '2026-09-21'),
                                 ('tiktok', 'states', {'A': 'eligible', 'B': 'eligible', 'C': 'eligible'})]:
            with self.subTest(case=case, field=field):
                changed = copy.deepcopy(document)
                changed['facts'][case][field] = new
                path.write_text(json.dumps(changed), encoding='utf-8')
                errors = showcase.check_showcase(self.root)
                self.assertTrue(any(f'{case}.en.' in error for error in errors))
                self.assertTrue(any(f'{case}.zh-CN.' in error for error in errors))
                self.assertTrue(any('README.md' in error for error in errors))
                self.assertTrue(any('README.zh-CN.md' in error for error in errors))

    def test_missing_and_bad_manifests_report_friendly_errors(self):
        path = self.assets / 'content.json'
        original = path.read_text(encoding='utf-8')
        path.unlink()
        self.assertIn('showcase manifest', showcase.check_showcase(self.root)[0])
        bad_documents = ['{', '[]', '{}']
        for mutation in ('date', 'count', 'template', 'language', 'text_list'):
            document = json.loads(original)
            if mutation == 'date':
                document['facts']['meta']['date'] = 'yesterday'
            elif mutation == 'count':
                document['facts']['meta']['candidates'] = 'twenty'
            elif mutation == 'template':
                document['languages']['en']['svg']['meta']['wide'][1] = '{missing_fact}'
            elif mutation == 'language':
                del document['languages']['zh-CN']
            else:
                document['languages']['en']['svg']['meta']['wide'] = 'not a list'
            bad_documents.append(json.dumps(document))
        for invalid in bad_documents:
            with self.subTest(invalid=invalid[:50]):
                path.write_text(invalid, encoding='utf-8')
                errors = showcase.check_showcase(self.root)
                self.assertEqual(len(errors), 1)
                self.assertTrue(errors[0].startswith('showcase manifest'))


if __name__ == '__main__':
    unittest.main()

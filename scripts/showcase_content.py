#!/usr/bin/env python3
"""Check showcase text against its reviewed manifest; never rewrite assets."""
from datetime import date
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
ASSETS = Path('docs/assets/showcase')
KINDS = ('hero', 'meta', 'tiktok', 'workflow')
LANGUAGES = ('en', 'zh-CN')
THEMES = ('light', 'dark')
WIDTHS = ('wide', 'narrow')


def normalized(text):
    return ' '.join(text.split())


def date_range(start, end, separator, dash):
    first = start.isoformat().replace('-', separator)
    if start == end:
        return first
    last = (f'{end.day:02d}' if (start.year, start.month) == (end.year, end.month)
            else end.isoformat().replace('-', separator))
    return first + dash + last


def render_manifest(document):
    """Validate the small schema and expand facts once for both languages."""
    if type(document['version']) is not int or document['version'] != 1:
        raise ValueError('unsupported manifest version (expected 1)')
    facts = document['facts']
    meta, tiktok = facts['meta'], facts['tiktok']
    for name in ('candidates', 'copy_sets', 'business_lines'):
        if type(meta[name]) is not int or meta[name] <= 0:
            raise ValueError(f'facts.meta.{name} must be a positive integer')
    meta_date = date.fromisoformat(meta['date'])
    start, end = date.fromisoformat(tiktok['start']), date.fromisoformat(tiktok['end'])
    if end < start:
        raise ValueError('facts.tiktok.end is before start')
    states = tiktok['states']
    if set(states) != {'A', 'B', 'C'} or any(
            value not in ('eligible', 'in_review') for value in states.values()):
        raise ValueError('facts.tiktok.states must map A, B, C to eligible or in_review')
    if set(document['languages']) != set(LANGUAGES):
        raise ValueError('languages must contain exactly en and zh-CN')
    rendered = {}
    for language in LANGUAGES:
        source = document['languages'][language]
        words = source['number_words']
        labels = source['status_labels']
        if (not isinstance(words, list) or len(words) < 4
                or any(not isinstance(word, str) or not word.strip() for word in words)):
            raise ValueError(f'{language}.number_words must cover zero through three')
        if meta['business_lines'] >= len(words):
            raise ValueError(f'{language}.number_words does not cover meta.business_lines')
        if set(labels) != {'eligible', 'in_review'} or any(
                not isinstance(label, str) or not label.strip() for label in labels.values()):
            raise ValueError(f'{language}.status_labels must label eligible and in_review')
        eligible = list(states.values()).count('eligible')
        in_review = list(states.values()).count('in_review')
        values = {
            'meta_candidates': meta['candidates'], 'meta_copy_sets': meta['copy_sets'],
            'meta_lines_word': words[meta['business_lines']],
            'meta_lines_title': words[meta['business_lines']].capitalize(),
            'meta_date_svg': meta_date.strftime('%Y.%m.%d'),
            'meta_date_md': meta_date.isoformat(),
            'tiktok_date_svg': date_range(start, end, '.', '–'),
            'tiktok_date_md': date_range(start, end, '-', '—' if language == 'zh-CN' else '–'),
            'tiktok_lines_word': words[len(states)],
            'tiktok_lines_title': words[len(states)].capitalize(),
            'eligible_count': eligible, 'review_count': in_review,
            'eligible_word': words[eligible], 'review_word': words[in_review],
            **{f'status_{key}': labels[value] for key, value in states.items()},
        }

        def expand(template):
            if not isinstance(template, str) or not template.strip():
                raise ValueError(f'{language}: text templates must be nonempty strings')
            return normalized(template.format_map(values))

        svg = source['svg']
        if set(svg) != set(KINDS):
            raise ValueError(f'{language}.svg must contain all four showcase kinds')
        expanded_svg = {}
        for kind in KINDS:
            if set(svg[kind]) != set(WIDTHS):
                raise ValueError(f'{language}.svg.{kind} must contain wide and narrow')
            expanded_svg[kind] = {}
            for width in WIDTHS:
                entries = svg[kind][width]
                if not isinstance(entries, list) or not entries:
                    raise ValueError(f'{language}.svg.{kind}.{width} must be a nonempty text list')
                expanded_svg[kind][width] = [expand(entry) for entry in entries]
        readme = source['readme']
        if set(readme['alt']) != set(KINDS) or set(readme['cases']) != {'meta', 'tiktok'}:
            raise ValueError(f'{language}.readme must cover four alts and two case paragraphs')
        rendered[language] = {
            'svg': expanded_svg,
            'alt': {kind: expand(value) for kind, value in readme['alt'].items()},
            'cases': {kind: expand(value) for kind, value in readme['cases'].items()},
            'evidence': expand(readme['evidence']),
        }
    return rendered


class Pictures(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.pictures = []
        self.current = None

    def handle_starttag(self, tag, attrs):
        if tag == 'picture':
            self.current = {'sources': [], 'images': []}
            self.pictures.append(self.current)
        elif self.current is not None and tag in ('source', 'img'):
            self.current['sources' if tag == 'source' else 'images'].append(dict(attrs))

    def handle_endtag(self, tag):
        if tag == 'picture':
            self.current = None


def check_showcase(root=ROOT):
    """Return actionable errors; a missing or malformed manifest fails closed."""
    root = Path(root)
    manifest_path = root / ASSETS / 'content.json'
    try:
        content = render_manifest(json.loads(manifest_path.read_text(encoding='utf-8')))
    except (OSError, UnicodeError, ValueError, KeyError, TypeError, AttributeError, IndexError) as exc:
        return [f'showcase manifest {ASSETS / "content.json"}: {type(exc).__name__}: {exc}']
    errors = []
    for language, expected in content.items():
        for kind in KINDS:
            for width in WIDTHS:
                for theme in THEMES:
                    path = ASSETS / f'{kind}.{language}.{theme}.{width}.svg'
                    try:
                        svg = ET.fromstring((root / path).read_text(encoding='utf-8'))
                        actual = [normalized(''.join(node.itertext())) for node in svg.iter()
                                  if node.tag == '{http://www.w3.org/2000/svg}text']
                    except (OSError, UnicodeError, ET.ParseError) as exc:
                        errors.append(f'showcase SVG {path}: {exc}')
                        continue
                    wanted = expected['svg'][kind][width]
                    if actual != wanted:
                        mismatch = next((i + 1 for i, pair in enumerate(zip(actual, wanted))
                                         if pair[0] != pair[1]), min(len(actual), len(wanted)) + 1)
                        errors.append(f'showcase visible text differs: {path} (text entry {mismatch})')

        filename = 'README.md' if language == 'en' else 'README.zh-CN.md'
        try:
            markdown = (root / filename).read_text(encoding='utf-8')
        except (OSError, UnicodeError) as exc:
            errors.append(f'showcase README {filename}: {exc}')
            continue
        pictures = Pictures()
        pictures.feed(markdown)
        for kind in KINDS:
            # Associate alt with the exact language-specific fallback image, not
            # with a matching phrase elsewhere in the document.
            src = str(ASSETS / f'{kind}.{language}.light.wide.png')
            matching = [(picture, img) for picture in pictures.pictures for img in picture['images']
                        if img.get('src') == src]
            if len(matching) != 1:
                errors.append(f'showcase alt differs or image missing/duplicated: {filename} ({kind})')
                continue
            picture, img = matching[0]
            if len(picture['images']) != 1 or normalized(img.get('alt', '')) != expected['alt'][kind]:
                errors.append(f'showcase alt differs or image missing/duplicated: {filename} ({kind})')
            wanted_sources = [
                ('(max-width: 640px) and (prefers-color-scheme: dark)', 'dark.narrow'),
                ('(max-width: 640px)', 'light.narrow'),
                ('(prefers-color-scheme: dark)', 'dark.wide'),
            ]
            wanted_sources = [(media, str(ASSETS / f'{kind}.{language}.{variant}.png'))
                              for media, variant in wanted_sources]
            actual_sources = [(normalized(item.get('media', '')), item.get('srcset', ''))
                              for item in picture['sources']]
            if actual_sources != wanted_sources:
                errors.append(f'showcase picture sources differ: {filename} ({kind})')
        # Only the linked case paragraphs and their adjacent evidence paragraph
        # belong to this contract. Unrelated demo counts and prose are excluded.
        paragraphs = [normalized(part) for part in re.split(r'\n\s*\n', markdown) if part.strip()]
        tiktok_index = None
        for kind in ('meta', 'tiktok'):
            case_file = 'case-studies.md' if language == 'en' else 'case-studies.zh-CN.md'
            anchor = f'](docs/{case_file}#{kind}-task)'
            matching = [(i, p) for i, p in enumerate(paragraphs) if anchor in p]
            if len(matching) != 1 or matching[0][1] != expected['cases'][kind]:
                errors.append(f'showcase case paragraph differs or missing/duplicated: {filename} ({kind})')
            if kind == 'tiktok' and len(matching) == 1:
                tiktok_index = matching[0][0]
        if (tiktok_index is None or tiktok_index + 1 >= len(paragraphs)
                or paragraphs[tiktok_index + 1] != expected['evidence']):
            errors.append(f'showcase evidence/date paragraph differs or missing: {filename}')
    return errors


def main():
    errors = check_showcase()
    print(json.dumps({
        'status': 'failed' if errors else 'passed',
        'checks': ['32 SVG text sequences', 'bilingual README case text, dates, image alts and picture sources'],
        'limitations': 'Checks reviewed text, not historical truth, SVG rendering or PNG text/pixel equivalence. '
                        'PNG integrity is checked by check_repository.py; exports require visual review.',
        'errors': errors,
    }, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())

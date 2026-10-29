#!/usr/bin/env python3
"""Check public source structure and common accidental disclosures, offline.

    python3 scripts/check_repository.py     # prints a JSON result; exit 1 on any error

It checks that every file in ``REQUIRED`` exists, that binary files are only the
generated README images (without text metadata chunks), that Python, JSON, SVG
and local Markdown links are valid, that every http(s) link points at a host in
``URL_HOSTS``, and that no text file carries a pattern from ``SENSITIVE``
(anywhere) or ``POLICY`` (in public prose, fixtures and top-level modules).
Errors name the rule and the file, never the matched value.

Personal patterns (for example the name shape of your own private notes) do not
belong in this public file: put one regular expression per line in an untracked
``.private-patterns`` file at the repository root and they are added to
``SENSITIVE`` at import time.

Patterns whose literal text would match themselves are assembled from pieces, so
this file and tests/test_check_repository.py can be scanned like any other.
It is a heuristic guard, not a complete secret scanner.
"""
import ast
import json
import os
from pathlib import Path
import re
import struct
import sys
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SKIP = {'.git', '__pycache__', '.venv', 'venv', 'runs', '.direct-work', '.private-patterns'}
# Generated demo output lives one level down, so it needs a path prefix rather
# than a single component. It is gitignored; this keeps the source check honest
# about not reading it in the meantime.
SKIP_PREFIXES = {('demo', 'out')}
# Binary files are allowed only here: the README images that
# scripts/render_visuals.py generates from demo output (PNG, plus optional SVG
# charts). Anything else that is not UTF-8 text fails the check.
ASSET_DIRS = {('docs', 'assets', name) for name in ('hero', 'proof', 'social', 'charts')}
ASSET_SUFFIXES = {'.png', '.svg'}
ASSET_MAX_BYTES = 600 * 1024
SOCIAL_PREVIEW = ('docs', 'assets', 'social', 'social-preview.png')
EXECUTABLE = ['.githooks/pre-commit', '.githooks/commit-msg']
# Ancillary PNG chunks that carry text, EXIF or timestamps (a hand-taken
# screenshot often has them); the generated images contain none.
PNG_METADATA_CHUNKS = (b'tEXt', b'iTXt', b'zTXt', b'eXIf', b'tIME')

# Every file the public tree is expected to contain. tests/test_check_repository.py
# fails when a module, test, doc, fixture or script exists but is not listed here.
REQUIRED = [
    # Project, contribution and CI files
    'README.md', 'README.zh-CN.md', 'AGENTS.md', 'CLAUDE.md', 'CHANGELOG.md', 'CONTRIBUTING.md', 'SECURITY.md',
    'LICENSE', 'NOTICE.md', '.gitignore', '.gitattributes', '.githooks/pre-commit', '.githooks/commit-msg',
    '.github/workflows/ci.yml', '.github/dependabot.yml', '.github/pull_request_template.md',
    '.github/rulesets/main.json',
    # Decision engine and its fixtures
    'operating_rules.py', 'operating_loop.py',
    'examples/operating/methodology-reference.json', 'examples/operating/snapshot-primary.json',
    'examples/operating/writeback-snapshot.json', 'examples/operating/after-snapshot.json',
    'examples/operating/settlement-daily.json',
    'demo/README.md', 'demo/README.zh-CN.md', 'demo/run_demo.py',
    'demo/expected/report.md', 'demo/expected/report.zh-CN.md', 'demo/expected/summary.json',
    # Build QA: readback verifier and pre-flight linter
    'readback.py', 'preflight.py',
    'examples/readback/meta-plan.json', 'examples/readback/meta-readback.json',
    'examples/readback/tiktok-plan.json', 'examples/readback/tiktok-readback.json',
    'examples/readback/expected/meta-receipt.md', 'examples/readback/expected/meta-receipt.zh-CN.md',
    'examples/readback/expected/tiktok-receipt.md', 'examples/readback/expected/tiktok-receipt.zh-CN.md',
    'examples/preflight/checklist.json', 'examples/preflight/policy.json',
    'examples/preflight/expected/checklist.md', 'examples/preflight/expected/checklist.zh-CN.md',
    # Account audit: running accounts and write requests before a round decides
    'account_audit.py', 'examples/audit/snapshot.json', 'examples/audit/policy.json',
    'examples/audit/expected/audit.md', 'examples/audit/expected/audit.zh-CN.md',
    # Pre-launch planning and onboarding prototype
    'adops.py', 'onboarding.py', 'guidance.py', 'knowledge.py', 'memory_store.py', 'personalization.py',
    'methodology.py', 'planning.py', 'task.py',
    'knowledge/catalog.json', 'schemas/methodology.schema.json', 'evaluations/fixtures.py',
    'examples/brief.json', 'examples/candidates.json', 'examples/knowledge-observations.json',
    'examples/onboarding-app-hybrid-discovery.json', 'examples/onboarding-guided.json',
    'examples/onboarding-learning.json', 'examples/onboarding-setup-required.json',
    'examples/private-methodology.json',
    'templates/task-record.md', 'templates/task-record.zh-CN.md',
    'contracts/README.md', 'contracts/connector-contract.json', 'contracts/disapproval-triage.json',
    'contracts/acceptance-scenarios.json', 'contracts/experience-catalog.json',
    'contracts/onboarding-extensions.json',
    # Scripts
    'scripts/check_repository.py', 'scripts/demo.py', 'scripts/demo_methods.py',
    'scripts/demo_operating_loop.py', 'scripts/demo_private_memory.py',
    'scripts/render_decision_matrix.py', 'scripts/render_visuals.py',
    # Tests
    'tests/test_adops.py', 'tests/test_check_repository.py', 'tests/test_guidance.py',
    'tests/test_knowledge.py', 'tests/test_m2_integration.py', 'tests/test_memory_store.py',
    'tests/test_methodology.py', 'tests/test_onboarding.py', 'tests/test_operating_loop.py',
    'tests/test_planning.py', 'tests/test_preflight.py', 'tests/test_private_memory_integration.py',
    'tests/test_readback.py', 'tests/test_reconciliation.py', 'tests/test_setup_flow.py',
    'tests/test_account_audit.py',
    # Docs: provenance, decisions and build QA
    'docs/index.md', 'docs/index.en.md',
    'docs/how-it-ran.md', 'docs/how-it-ran.zh-CN.md',
    'docs/case-studies.md', 'docs/case-studies.zh-CN.md',
    'docs/methodology-history.md', 'docs/methodology-history.zh-CN.md',
    'docs/capability-status.md', 'docs/capability-status.zh-CN.md',
    'docs/decision-matrix.md', 'docs/operating-loop.md', 'docs/operating-loop.zh-CN.md',
    'docs/build-qa.md', 'docs/build-qa.zh-CN.md', 'docs/account-audit.md', 'docs/account-audit.zh-CN.md',
    'docs/disapproval-triage.md', 'docs/disapproval-triage.zh-CN.md', 'docs/operations.md',
    # Docs: host workflow, setup and the planning prototype
    'docs/workflow.md', 'docs/workflow.zh-CN.md',
    'docs/use-in-agent.md', 'docs/use-in-agent.zh-CN.md',
    'docs/first-check.md', 'docs/first-check.zh-CN.md', 'docs/first-run.md', 'docs/first-run.zh-CN.md',
    'docs/platform-connectivity.md', 'docs/platform-connectivity.zh-CN.md',
    'docs/google-ads-api-application.zh-CN.md',
    'docs/build-from-zero.md', 'docs/build-from-zero.zh-CN.md',
    'docs/method-planning.md', 'docs/method-planning.zh-CN.md',
    'docs/method-comparison.md', 'docs/method-comparison.zh-CN.md',
    'docs/knowledge-base.zh-CN.md', 'docs/private-memory.zh-CN.md',
    'docs/product.md', 'docs/architecture.md', 'docs/onboarding.md', 'docs/roadmap.md',
    # README images and the sources they are rendered from
    'docs/assets/src/manifest.json', 'docs/assets/src/hero.en.html', 'docs/assets/src/hero.zh-CN.html',
    'docs/assets/src/receipt.en.html', 'docs/assets/src/receipt.zh-CN.html',
    'docs/assets/src/social-preview.html',
    'docs/assets/hero/hero.en.png', 'docs/assets/hero/hero.zh-CN.png',
    'docs/assets/proof/receipt.en.png', 'docs/assets/proof/receipt.zh-CN.png',
    'docs/assets/social/social-preview.png',
]

# Checked in every text file. Errors print the label and path, never the match.
SENSITIVE = [
    ('personal workspace path', re.compile('/' + r'Users/[^/\s]+/|/' + r'home/[^/\s]+/')),
    ('GitHub token', re.compile(r'gh[pousr]_[A-Za-z0-9_]{20,}')),
    ('private key', re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----')),
    ('API key', re.compile(r'\bsk-[A-Za-z0-9_-]{24,}')),
    ('private workspace reference', re.compile('Work' + 'Buddy/')),
    # Meta ad account IDs are written act_<digits>; fixtures use keys such as acct-a.
    ('ad account ID', re.compile(r'(?<![A-Za-z0-9])' + 'act' + r'_\d{6,}')),
    # Page, pixel, campaign, ad set, ad and advertiser IDs are 15-19 digit numbers.
    # Only a standalone run counts: digits inside a hash, a decimal or a longer
    # number do not, and public help-centre URLs are removed first (see LONG_ID_EXEMPT).
    # An underscore does not shield it: adset_<digits> is still an ID.
    ('long numeric ID', re.compile(r'(?<![A-Za-z0-9.])\d{15,19}(?![A-Za-z0-9]|\.\d)')),
    # Google Ads customer IDs are three dash-separated digit groups (3-3-4).
    ('Google Ads customer ID', re.compile(r'(?<![\d-])\d{3}-\d{3}-\d{4}(?![\d-])')),
    ('Meta access token', re.compile(r'\b' + 'EA' + r'A[A-Za-z0-9]{20,}')),
    ('token in URL', re.compile(r'https?://[^\s"\'<>()]*[?&#][A-Za-z_]*' + 'tok' + 'en=', re.IGNORECASE)),
    ('referral link fragment', re.compile('#' + 'via' + '=')),
    # Any address except reserved example domains and GitHub's own noreply ones.
    ('email address', re.compile(
        r'[A-Za-z0-9._%+-]+' + '@' + r'(?!example\.(?:com|org|net)\b|users\.noreply\.github\.com\b'
        r'|github\.com\b)[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}')),
]
PRIVATE_PATTERNS = ROOT / '.private-patterns'


def load_private_patterns(path=PRIVATE_PATTERNS):
    """Untracked, owner-only patterns: one regex per line; ``#`` starts a comment."""
    patterns = []
    try:
        lines = Path(path).read_text(encoding='utf-8').splitlines()
    except OSError:
        return patterns
    for line in lines:
        line = line.strip()
        if line and not line.startswith('#'):
            patterns.append(('private pattern', re.compile(line)))
    return patterns


SENSITIVE.extend(load_private_patterns())

# Every http(s) link must point at one of these hosts (or a subdomain of a
# reserved example domain): official platform and protocol documentation, the
# repository itself, badges and the one hosted connector named as an example.
# An offer, tracker or partner domain therefore cannot slip into prose or fixtures.
URL_HOSTS = {
    'example.com', 'example.invalid', 'github.com', 'raw.githubusercontent.com', 'docs.github.com',
    'img.shields.io', 'pipeboard.co', 'developers.facebook.com', 'www.facebook.com', 'about.fb.com',
    'www.facebookblueprint.com', 'business-api.tiktok.com', 'ads.tiktok.com', 'developers.google.com',
    'support.google.com', 'console.cloud.google.com', 'firebase.google.com', 'modelcontextprotocol.io',
    'json-schema.org', 'www.w3.org', 'www.postman.com', 'learn.chatgpt.com',
}
URL_HOST = re.compile(r'https?://([A-Za-z0-9.-]+)', re.IGNORECASE)


def host_allowed(host):
    host = host.lower().rstrip('.')
    return host in URL_HOSTS or host.endswith(('.example.com', '.example.invalid'))

# Public documentation URLs carry long article IDs that are not account data.
LONG_ID_EXEMPT = re.compile(
    r'https://(?:www\.facebook\.com/business/help|developers\.facebook\.com/docs'
    r'|business-api\.tiktok\.com/portal/docs|ads\.tiktok\.com/help'
    r'|support\.google\.com|developers\.google\.com)[^\s"\'<>()]*')

# Checked only in public prose and fixtures: what an agent or reader takes as
# guidance. Disapprovals are resolved by fixing the content or through the
# platform's review process, so wording for getting unchanged media past review
# has no place there (docs/disapproval-triage.md).
POLICY_DIRS = {'docs', 'contracts', 'examples', 'knowledge', 'demo', 'templates'}
POLICY = [
    ('ad-review circumvention wording',
     re.compile('改' + '哈希' + '|' + '换' + '.{0,4}' + '哈希' + '|' + r'\bre-?' + 'hash'
                + '|' + '疑似' + '误拒' + '|' + '换' + '绑' + '|' + '旧' + '绑定', re.IGNORECASE)),
    ('traffic-mixing jargon', re.compile('混' + '量' + '|' + r'mixed[ _-]?' + 'traffic', re.IGNORECASE)),
    ('incentive-vertical jargon',
     re.compile('奖' + '品' + '|' + '抽' + '奖' + '|' + r'sweep' + r'stakes?' + '|' + r'deal[ _-]?' + 'wall',
                re.IGNORECASE)),
]
CHECKS = [
    'required files', 'README images: PNG/SVG only under docs/assets/{hero,proof,social,charts}/, at most 600 KB '
    'each, no PNG text or EXIF chunks',
    'Python syntax', 'JSON documents and unloaded contracts', 'runtime knowledge catalog', 'local Markdown links',
    'executable git hooks', 'disclosure patterns: workspace paths, tokens, keys, ad account, Google Ads customer and '
    'long numeric IDs, Meta access tokens, email addresses, tokens in URLs, referral fragments',
    'link hosts limited to documentation, the repository and reserved example domains',
    'ad-review circumvention, traffic-mixing and incentive-vertical wording in docs, contracts, examples, '
    'knowledge, demo, templates and top-level Markdown and Python',
]


def in_policy_scope(relative):
    """Public prose and fixtures: the policy directories plus top-level Markdown and modules."""
    parts = Path(relative).parts
    if len(parts) == 1:
        return parts[0].endswith(('.md', '.py'))
    return parts[0] in POLICY_DIRS


def scan_text(relative, text):
    """Return the labels of every disclosure or policy pattern found in ``text``.

    ``relative`` is the repository-relative path; it decides whether the policy
    patterns apply. The matched values are never returned.
    """
    labels = []
    for label, pattern in SENSITIVE:
        subject = LONG_ID_EXEMPT.sub(' ', text) if label == 'long numeric ID' else text
        if pattern.search(subject):
            labels.append(label)
    if any(not host_allowed(host) for host in URL_HOST.findall(text)):
        labels.append('link to a host outside the allowlist')
    if in_policy_scope(relative):
        labels.extend(label for label, pattern in POLICY if pattern.search(text))
    return labels


def png_chunks(data):
    """Chunk types of a PNG, in order; stops at a truncated chunk."""
    types, offset = [], 8
    while offset + 8 <= len(data):
        length = struct.unpack('>I', data[offset:offset + 4])[0]
        types.append(data[offset + 4:offset + 8])
        offset += 12 + length
    return types


def check_tree(root=ROOT):
    """Check required files and every public file under ``root``; return (errors, text_files)."""
    root = Path(root).resolve()
    errors, files = [], []
    for name in REQUIRED:
        if not (root / name).is_file():
            errors.append(f'missing required file: {name}')
    for name in EXECUTABLE:
        path = root / name
        if path.is_file() and not os.access(str(path), os.X_OK):
            errors.append(f'git hook is not executable: {name}')
    for path in sorted(root.rglob('*')):
        relative = path.relative_to(root)
        if any(part in SKIP for part in relative.parts) or not path.is_file():
            continue
        if tuple(relative.parts[:2]) in SKIP_PREFIXES:
            continue
        if path.name == '.DS_Store' or path.suffix in {'.pyc', '.pyo'}:
            continue
        if path.name == '.env' or (path.name.startswith('.env.') and path.name != '.env.example') or path.suffix in {'.sqlite3', '.db', '.pem', '.key'}:
            errors.append(f'private/runtime file in public source: {relative}')
            continue
        in_assets = tuple(relative.parts[:3]) in ASSET_DIRS and len(relative.parts) == 4
        if path.suffix in ASSET_SUFFIXES and not in_assets:
            errors.append(f'image outside docs/assets/{{hero,proof,social,charts}}/: {relative}')
            continue
        if in_assets and path.suffix not in ASSET_SUFFIXES:
            errors.append(f'only PNG and SVG files belong in {"/".join(relative.parts[:3])}/: {relative}')
            continue
        if in_assets and path.stat().st_size > ASSET_MAX_BYTES:
            errors.append(f'image larger than {ASSET_MAX_BYTES // 1024} KB: {relative}')
        if path.suffix == '.png':
            data = path.read_bytes()
            if len(data) < 24 or data[:8] != b'\x89PNG\r\n\x1a\n':
                errors.append(f'invalid PNG: {relative}')
                continue
            width, height = struct.unpack('>II', data[16:24])
            if not (300 <= width <= 2048 and 120 <= height <= 2048):
                errors.append(f'unexpected image dimensions: {relative}')
            if tuple(relative.parts) == SOCIAL_PREVIEW and (width, height) != (1280, 640):
                errors.append(f'social preview must be 1280x640: {relative}')
            for chunk in png_chunks(data):
                if chunk in PNG_METADATA_CHUNKS:
                    errors.append(f'PNG metadata chunk {chunk.decode("ascii")}: {relative}')
            continue
        files.append(path)
        try:
            text = path.read_text(encoding='utf-8')
        except UnicodeError:
            errors.append(f'unexpected non-text source: {relative}')
            continue
        for label in scan_text(relative.as_posix(), text):
            # Never echo a potentially sensitive matched value.
            errors.append(f'{label}: {relative}')
        if path.suffix == '.svg':
            try:
                svg = ET.fromstring(text)
                if svg.tag != '{http://www.w3.org/2000/svg}svg':
                    errors.append(f'invalid SVG root: {relative}')
                if any(node.tag.rsplit('}', 1)[-1] in {'script', 'foreignObject'} for node in svg.iter()):
                    errors.append(f'unsafe SVG element: {relative}')
                if any(key.rsplit('}', 1)[-1] == 'href' for node in svg.iter() for key in node.attrib):
                    errors.append(f'external-capable SVG reference: {relative}')
            except ET.ParseError:
                errors.append(f'invalid SVG XML: {relative}')
        if path.suffix == '.py':
            try:
                ast.parse(text, filename=str(relative))
            except SyntaxError as exc:
                errors.append(f'invalid Python: {relative}:{exc.lineno}')
        if path.suffix == '.json':
            try:
                doc = json.loads(text)
                if relative.parts[0] == 'contracts':
                    if doc.get('artifact_type') != 'design_only' or doc.get('runtime_loaded') is not False or doc.get('enabled') is not False:
                        errors.append(f'contract must remain explicitly unloaded design: {relative}')
            except (ValueError, AttributeError):
                errors.append(f'invalid JSON object: {relative}')
        if path.suffix == '.md':
            for target in re.findall(r'\]\(([^)\s]+)\)', text) + re.findall(r'(?:src|srcset)="([^"]+)"', text):
                parsed = urlsplit(target)
                if parsed.scheme or parsed.netloc or not parsed.path:
                    continue
                destination = (path.parent / unquote(parsed.path)).resolve()
                if not destination.is_relative_to(root) or not destination.exists():
                    errors.append(f'broken local link: {relative} -> {target}')
    return errors, files


def main():
    errors = []
    sys.path.insert(0, str(ROOT))
    try:
        import knowledge
        knowledge.load_catalog()
    except (OSError, ValueError, TypeError) as exc:
        errors.append('runtime knowledge catalog invalid: ' + str(exc))
    tree_errors, files = check_tree(ROOT)
    errors.extend(tree_errors)
    result = {'status': 'failed' if errors else 'passed', 'public_text_files': len(files),
              'checks': CHECKS,
              'limitations': 'Heuristic source check; not a comprehensive secret scanner or runtime/platform validation.',
              'errors': errors}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())

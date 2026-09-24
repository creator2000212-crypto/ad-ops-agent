#!/usr/bin/env python3
"""Check public source structure and common accidental disclosures, offline."""
import ast
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
SKIP = {'.git', '__pycache__', '.venv', 'venv', 'runs', '.direct-work'}
# Generated demo output lives one level down, so it needs a path prefix rather
# than a single component. It is gitignored; this keeps the source check honest
# about not reading it in the meantime.
SKIP_PREFIXES = {('demo', 'out')}
REQUIRED = [
    'README.md', 'README.zh-CN.md', 'AGENTS.md', 'LICENSE', 'NOTICE.md', 'CONTRIBUTING.md', 'SECURITY.md',
    'adops.py', 'onboarding.py', 'guidance.py', 'knowledge.py', 'knowledge/catalog.json',
    'tests/test_guidance.py', 'tests/test_setup_flow.py', 'docs/first-run.zh-CN.md', 'docs/use-in-agent.zh-CN.md',
    'examples/onboarding-setup-required.json', 'examples/onboarding-guided.json',
    'docs/knowledge-base.zh-CN.md', 'tests/test_knowledge.py',
    'memory_store.py', 'personalization.py', 'tests/test_memory_store.py',
    'tests/test_private_memory_integration.py', 'scripts/demo_private_memory.py',
    'examples/private-methodology.json', 'docs/private-memory.zh-CN.md',
    'methodology.py', 'planning.py', 'task.py', 'schemas/methodology.schema.json',
    'tests/test_methodology.py', 'tests/test_planning.py', 'tests/test_m2_integration.py',
    'evaluations/fixtures.py', 'scripts/demo_methods.py',
    'docs/method-planning.md', 'docs/method-planning.zh-CN.md',
    'scripts/demo.py', 'tests/test_adops.py', 'tests/test_onboarding.py',
    'docs/index.md', 'docs/product.md', 'docs/architecture.md', 'docs/onboarding.md',
    'docs/operations.md', 'docs/meta-creative-recovery.md', 'docs/roadmap.md',
    'contracts/README.md', 'contracts/connector-contract.json', 'contracts/creative-recovery.json',
    'contracts/acceptance-scenarios.json', 'contracts/experience-catalog.json',
    'contracts/onboarding-extensions.json',
    'operating_rules.py', 'operating_loop.py', 'tests/test_operating_loop.py',
    'scripts/demo_operating_loop.py', 'docs/operating-loop.md', 'docs/operating-loop.zh-CN.md',
    'examples/operating/methodology-reference.json', 'examples/operating/snapshot-primary.json',
    'examples/operating/writeback-snapshot.json', 'examples/operating/after-snapshot.json',
    'examples/operating/settlement-daily.json',
    'demo/README.md', 'demo/README.zh-CN.md', 'demo/run_demo.py',
    'demo/expected/report.md', 'demo/expected/summary.json',
    'docs/build-from-zero.md', 'docs/build-from-zero.zh-CN.md',
    '.github/workflows/ci.yml', '.gitignore', '.gitattributes'
]
SENSITIVE = [
    ('personal workspace path', re.compile('/' + r'Users/[^/\s]+/|/' + r'home/[^/\s]+/')),
    ('GitHub token', re.compile(r'gh[pousr]_[A-Za-z0-9_]{20,}')),
    ('private key', re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----')),
    ('API key', re.compile(r'\bsk-[A-Za-z0-9_-]{24,}')),
    ('private source reference', re.compile('投放经验学习记录_' + r'\d{8}|Work' + 'Buddy/')),
]


def main():
    errors, files = [], []
    sys.path.insert(0, str(ROOT))
    try:
        import knowledge
        knowledge.load_catalog()
    except (OSError, ValueError, TypeError) as exc:
        errors.append('runtime knowledge catalog invalid: ' + str(exc))
    for name in REQUIRED:
        if not (ROOT / name).is_file():
            errors.append(f'missing required file: {name}')
    for path in sorted(ROOT.rglob('*')):
        relative = path.relative_to(ROOT)
        if any(part in SKIP for part in relative.parts) or not path.is_file():
            continue
        if tuple(relative.parts[:2]) in SKIP_PREFIXES:
            continue
        if path.name == '.DS_Store' or path.suffix in {'.pyc', '.pyo'}:
            continue
        files.append(path)
        if path.name == '.env' or (path.name.startswith('.env.') and path.name != '.env.example') or path.suffix in {'.sqlite3', '.db', '.pem', '.key'}:
            errors.append(f'private/runtime file in public source: {relative}')
            continue
        try:
            text = path.read_text(encoding='utf-8')
        except UnicodeError:
            errors.append(f'unexpected non-text source: {relative}')
            continue
        for label, pattern in SENSITIVE:
            if pattern.search(text):
                # Never echo a potentially sensitive matched value.
                errors.append(f'{label}: {relative}')
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
            for target in re.findall(r'\]\(([^)\s]+)\)', text):
                parsed = urlsplit(target)
                if parsed.scheme or parsed.netloc or not parsed.path:
                    continue
                destination = (path.parent / unquote(parsed.path)).resolve()
                if not destination.is_relative_to(ROOT) or not destination.exists():
                    errors.append(f'broken local link: {relative} -> {target}')
    result = {'status': 'failed' if errors else 'passed', 'public_text_files': len(files),
              'checks': ['required files', 'Python syntax', 'JSON contracts', 'runtime knowledge catalog', 'local Markdown links', 'common disclosure patterns'],
              'limitations': 'Heuristic source check; not a comprehensive secret scanner or runtime/platform validation.',
              'errors': errors}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())

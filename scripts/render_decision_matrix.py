#!/usr/bin/env python3
"""Render docs/decision-matrix.md from the reference methodology, offline.

    python3 scripts/render_decision_matrix.py            # rewrite docs/decision-matrix.md
    python3 scripts/render_decision_matrix.py --check    # exit 1 and print a diff if it is stale

Every threshold in the matrix is read from the methodology document, and the
"Engine or human" column is derived from the engine itself (``ENGINE_CODES`` in
operating_rules.py) and the methodology's reconciliation policy, so the page
cannot drift from the code or the numbers without ``--check`` failing.
"""
import argparse
from decimal import Decimal
import difflib
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import operating_rules as rules  # noqa: E402

DEFAULT_METHODOLOGY = ROOT / 'examples' / 'operating' / 'methodology-reference.json'
DEFAULT_OUT = ROOT / 'docs' / 'decision-matrix.md'
PLACEHOLDER = re.compile(r'\{([A-Za-z_][A-Za-z0-9_.]*)(\|pct)?\}')

RECON_MEANING = {
    'RECON_OK': 'Spend within ±{spend}% and settled leads within ±{results}% of platform leads × {rate}',
    'RECON_GAP': ('Spend or settled leads outside tolerance, a different unit price, or incomplete totals '
                  'on either side'),
    'RECON_TZ': 'Account and settlement time zones differ or are not declared, so the day buckets differ',
    'RECON_WINDOW': 'The settlement has the account, but not for the observation date',
    'RECON_SCOPE': 'The account is on one side only; the missing side is shown as missing, never as zero',
}


class MatrixError(ValueError):
    pass


def relative(path):
    path = Path(path).resolve()
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.name


def lookup(methodology, dotted):
    value = methodology
    for part in dotted.split('.'):
        if not isinstance(value, dict) or part not in value:
            raise MatrixError(f'Trigger placeholder {{{dotted}}} is not in the methodology.')
        value = value[part]
    if isinstance(value, dict) and 'value' in value:
        value = value['value']
    return value


def fill(template, methodology):
    """Resolve ``{path.to.key}`` (and ``{key|pct}``) from the methodology."""
    def replace(match):
        value = lookup(methodology, match.group(1))
        if match.group(2):
            return rules.pct(Decimal(str(value)), '1')
        return str(value)
    return PLACEHOLDER.sub(replace, template)


def cell(text):
    return ' '.join(str(text).split()).replace('|', '\\|')


def engine_or_human(action, methodology, policy):
    code = action['code']
    if action.get('implemented') is False or code not in rules.ENGINE_CODES:
        return 'Human judgment (not evaluated by the engine)'
    field = rules.ENGINE_CODES[code]
    if field is None:
        return 'Engine: detects; advisory, a person acts'
    change = f'`{field}`'
    if code == 'LADDER_PROMOTE':
        change += ' to the next ladder step'
    elif field == 'status':
        change += ' → PAUSED'
    text = f'Engine: proposes {change} through the write gate'
    if policy and code in policy['downgrade_codes']:
        text += '; advisory when the settlement does not reconcile'
    return text


def not_implemented(methodology, prefix=''):
    """Every key the document marks ``"implemented": false``, as dotted paths."""
    found = []
    if isinstance(methodology, dict):
        for key, value in methodology.items():
            if key == 'actions':
                continue
            path = prefix + key
            if isinstance(value, dict):
                if value.get('implemented') is False:
                    found.append(path)
                found.extend(not_implemented(value, path + '.'))
    return found


def render(methodology, source):
    rules.validate_methodology(methodology)
    policy = rules.reconciliation_policy(methodology) if methodology.get('reconciliation') else None
    quality = rules.quality_factor(methodology)
    example = rules.num2(rules.target_cost('10.00', methodology))
    lines = [
        '# Decision matrix',
        '',
        f"Generated from `{source}` (`{methodology['methodology_id']}` v{methodology['version']}) by "
        '`scripts/render_decision_matrix.py`. Do not edit it by hand: change the methodology, run '
        '`python3 scripts/render_decision_matrix.py`, and confirm with `--check`.',
        '',
        f"T is the highest acceptable cost per platform lead: T = value per lead × approval rate "
        f"({rules.num(quality, '0.01')}) ÷ target ROAS ({methodology['target_roas']}). A 10.00 lead gives "
        f"T = {example}. Thresholds below are the reference values; a copied methodology changes them. "
        'Severity is the level the methodology assigns (P0 highest).',
        '',
        '| Code | Severity | Trigger | Action | Response window | Acceptance | Stop condition | Engine or human |',
        '|---|---|---|---|---|---|---|---|',
    ]
    for action in methodology['actions']:
        english = action.get('en')
        if not isinstance(english, dict) or not english.get('trigger'):
            raise MatrixError(f"Action {action['code']} has no en.trigger.")
        lines.append('| ' + ' | '.join(cell(value) for value in (
            f"`{action['code']}`", action['level'], fill(english['trigger'], methodology),
            english['action'], english['window'], english['acceptance'], english['stop_condition'],
            engine_or_human(action, methodology, policy))) + ' |')
    lines += [
        '',
        '## Engine or human',
        '',
        '- **Engine: proposes … through the write gate**: the engine detects the condition and proposes one '
        'field change. The five-state gate compares current state with the plan before the change can '
        'enter the reviewed batch; a person approves the batch. The engine never approves a write.',
        '- **Engine: detects; advisory**: the engine reports the finding with its evidence; the action is a '
        'person\'s decision.',
        '- **Human judgment**: part of the playbook, marked `"implemented": false`; the engine never '
        'evaluates it.',
        '',
        'Precedence: a promotion that meets its numbers becomes `LADDER_HOLD` while the same ad set has a '
        'creative breaker, creative overflow or a MAX name on a capped bid, or the account has a P0 finding.',
    ]
    if policy:
        values = {'spend': rules.num(policy['spend_tolerance_pct'], '0.1'),
                  'results': rules.num(policy['results_tolerance_pct'], '0.1'),
                  'rate': rules.num(quality, '0.01')}
        lines += [
            '',
            '## Platform vs settlement codes',
            '',
            'Each account gets one status. After `RECON_OK`, the rows are listed in the order they are '
            'checked; the first that applies wins.',
            '',
            '| Code | Meaning | Effect on this round |',
            '|---|---|---|',
        ]
        for code in ('RECON_OK',) + tuple(c for c in rules.RECON_CODES if c != 'RECON_OK'):
            if code == 'RECON_OK':
                effect = 'Decisions stand'
            elif code in policy['downgrade_on']:
                effect = (' and '.join(f'`{c}`' for c in policy['downgrade_codes'])
                          + ' become advisory ("measurement unreconciled")')
            else:
                effect = 'Reported; decisions stand (not in `downgrade_on`)'
            lines.append(f'| `{code}` | {cell(RECON_MEANING[code].format(**values))} | {effect} |')
    keys = not_implemented(methodology)
    lines += [
        '',
        '## Not read by the engine',
        '',
        'Methodology keys marked `"implemented": false` are guidance for people. The engine does not read them:',
        '',
    ]
    lines += [f'- `{key}`' for key in keys]
    lines += [f"- action `{action['code']}`" for action in methodology['actions']
              if action.get('implemented') is False]
    lines.append('')
    return '\n'.join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--methodology', type=Path, default=DEFAULT_METHODOLOGY)
    parser.add_argument('--out', type=Path, default=DEFAULT_OUT)
    parser.add_argument('--check', action='store_true',
                        help='compare with the committed page; exit 1 and print a diff if it differs')
    args = parser.parse_args(argv)
    try:
        methodology = rules.load_methodology(args.methodology)
        page = render(methodology, relative(args.methodology))
    except (OSError, ValueError) as exc:
        print(f'render_decision_matrix: {exc}', file=sys.stderr)
        return 2
    if args.check:
        try:
            committed = args.out.read_text(encoding='utf-8')
        except OSError:
            print(f'render_decision_matrix: {relative(args.out)} is missing; run without --check.',
                  file=sys.stderr)
            return 1
        if committed != page:
            sys.stderr.writelines(difflib.unified_diff(
                committed.splitlines(True), page.splitlines(True),
                fromfile=relative(args.out), tofile='rendered from the methodology'))
            print(f'\nrender_decision_matrix: {relative(args.out)} is stale; regenerate it and review '
                  'the diff.', file=sys.stderr)
            return 1
        print(f'{relative(args.out)} matches the methodology.')
        return 0
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(page, encoding='utf-8')
    print(f'Wrote {relative(args.out)} from {relative(args.methodology)}.')
    return 0


if __name__ == '__main__':
    sys.exit(main())

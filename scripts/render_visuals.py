#!/usr/bin/env python3
"""Render the README images from the demo's own output, offline.

    python3 scripts/render_visuals.py           # HTML sources + PNG screenshots (needs Google Chrome)
    python3 scripts/render_visuals.py --html    # HTML sources only
    python3 scripts/render_visuals.py --check   # sources, PNGs and README excerpts are current

Every number in an image is computed here, never typed: a fresh offline round
of the demo (``operating_loop.py round`` on the fictional fixtures, with the
demo's pinned timestamps) and ``readback.verify_build()`` on the fictional Meta
build. Each image gets an HTML source in ``docs/assets/src/``, which headless
Chrome screenshots into ``docs/assets/{hero,proof,social}/``.
``docs/assets/src/manifest.json`` records the hash of the source each PNG was
rendered from and the hash of the PNG.

``--check`` needs no browser. It fails when

* a source no longer matches what the current demo output renders,
* a PNG was not re-rendered after its source changed, or was edited by hand,
* a README table between ``<!-- excerpt: PATH -->`` and ``<!-- /excerpt -->``
  has a row whose cells are not in the matching row of PATH, or
* a README names a function (```name()```) or test (```test_name```) that
  does not exist.

Fonts come from the system, so a PNG rendered on another machine can differ in
pixels; the manifest pins what is committed. No network, no platform call.
"""
import argparse
import hashlib
import html
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import signal
import struct
import subprocess
import sys
import tempfile
import time
from urllib.parse import parse_qsl
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import operating_rules  # noqa: E402
import readback  # noqa: E402

ASSETS = ROOT / 'docs' / 'assets'
SOURCES = ASSETS / 'src'
MANIFEST = SOURCES / 'manifest.json'
METHODOLOGY = ROOT / 'examples' / 'operating' / 'methodology-reference.json'
BUILD_PLAN = ROOT / 'examples' / 'readback' / 'meta-plan.json'
BUILD_READBACK = ROOT / 'examples' / 'readback' / 'meta-readback.json'
RECEIPT_GOLDEN = 'examples/readback/expected/meta-receipt.md'
READMES = ('README.md', 'README.zh-CN.md')
CHROME_CANDIDATES = (
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    'google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser', 'chrome',
)
PNG_SIGNATURE = b'\x89PNG\r\n\x1a\n'
PNG_END = b'IEND\xaeB`\x82'


class VisualError(RuntimeError):
    pass


# --------------------------------------------------------------------------
# data: everything shown is read from program output here
# --------------------------------------------------------------------------

def _load_demo():
    spec = importlib.util.spec_from_file_location('run_demo', ROOT / 'demo' / 'run_demo.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def collect():
    """Run the demo round and the Meta readback once; return the raw results."""
    demo = _load_demo()
    with tempfile.TemporaryDirectory() as temp:
        out = Path(temp) / 'round'
        summary = demo.run_round(out, 'en')
        docs = {name: json.loads((out / (name + '.json')).read_text(encoding='utf-8'))
                for name in ('findings', 'gate', 'reconciliation')}
    build = readback.verify_build(readback.load(BUILD_PLAN), readback.load(BUILD_READBACK))
    methodology = operating_rules.load_methodology(METHODOLOGY)
    return {'summary': summary, 'methodology': methodology, 'build': build, **docs}


STOP_CODES = {'TEST_STOP_NOCONV': 'no_leads', 'TEST_STOP_OVERCOST': 'over_cost',
              'TEST_EARLY_STOP': 'early', 'LINK_OR_TRACKING_BAD': 'tracking'}
# The verdict that decides an ad set's row, most decisive first.
ROW_ORDER = ('AD_STATUS', 'LINK_OR_TRACKING_BAD', 'TEST_STOP_NOCONV', 'TEST_STOP_OVERCOST',
             'TEST_EARLY_STOP', 'LADDER_HOLD', 'LADDER_PROMOTE', 'TEST_UNDERTESTED')


def short_key(key):
    for prefix in ('fictional-adset-', 'fictional-adgroup-'):
        if key.startswith(prefix):
            return key[len(prefix):]
    return key


def decision_rows(data):
    """One row per ad set: the rule that decided it, the gate and the after-check."""
    verdicts = {}
    for verdict in data['gate']['verdicts']:
        if verdict['object_type'] in ('adset', 'creative'):
            verdicts.setdefault(verdict['parent_key'], []).append(verdict)
    not_effective = {row['object_key'] for row in data['reconciliation']['rows']
                     if row.get('checked') and not row['effective']}
    rows = []
    for diagnostic in data['findings']['diagnostics']:
        key = diagnostic['adset_key']
        mine = verdicts.get(key, [])
        codes = {item['code'] for item in mine}
        deciding = [item for item in mine if item['object_type'] == 'adset' and item['code'] in ROW_ORDER]
        deciding.sort(key=lambda item: ROW_ORDER.index(item['code']))
        verdict = deciding[0] if deciding else None
        code = verdict['code'] if verdict else None
        gate = verdict['gate'] if verdict else 'advisory'
        downgraded = bool(verdict and verdict.get('downgraded'))

        if code == 'LADDER_PROMOTE':
            label = ('promote', operating_rules.next_stage(diagnostic['stage'], data['methodology']))
        elif code in STOP_CODES:
            label = (STOP_CODES[code], None)
        elif code == 'LADDER_HOLD':
            blocker = ('hold_breaker' if 'CREATIVE_BREAKER' in codes else
                       'hold_overflow' if 'CREATIVE_OVERFLOW' in codes else 'hold_other')
            label = (blocker, None)
        elif code == 'AD_STATUS':
            label = ('ad_status', None)
        elif code == 'TEST_UNDERTESTED':
            label = ('undertested', None)
        else:
            label = ('no_change', None)

        if gate in operating_rules.NEEDS_HUMAN:
            tone = 'human'
        elif downgraded:
            tone = 'advisory'
        elif code == 'LADDER_PROMOTE':
            tone = 'promote'
        elif code in STOP_CODES:
            tone = 'stop'
        elif code == 'AD_STATUS':
            tone = 'human'
        else:
            tone = 'hold'

        if key in not_effective:
            status = ('stop', 'not_effective')
        elif gate in operating_rules.NEEDS_HUMAN:
            status = ('human', gate)
        elif downgraded:
            status = ('advisory', 'unreconciled')
        elif gate == 'ready':
            status = ('promote', 'ready')
        elif gate == 'satisfied':
            status = ('hold', 'satisfied')
        else:
            status = ('muted', 'advisory')
        rows.append({'key': key, 'short': short_key(key), 'results': diagnostic['results'],
                     'cpa': diagnostic['cpa'], 't': diagnostic['T_display'], 'label': label,
                     'tone': tone, 'status': status})
    return rows


def headline(data):
    summary = data['summary']
    gate = summary['gate']
    return {'ready': gate['ready'], 'total': gate['total'], 'needs_human': gate['needs_human'],
            'conflict': gate['conflict'], 'unknown': gate['unknown'],
            'not_effective': summary['reconciliation']['ineffective'],
            'calls': summary['native_platform_calls'], 'round_id': summary['round_id']}


def receipt_rows(build):
    """One row per field type that matched, plus every mismatch, in receipt order."""
    seen, chosen = set(), []
    for index, row in enumerate(build['rows']):
        if not row['match']:
            chosen.append(index)
        elif row['field'] not in seen:
            seen.add(row['field'])
            chosen.append(index)
    return [build['rows'][index] for index in sorted(set(chosen))]


# --------------------------------------------------------------------------
# text
# --------------------------------------------------------------------------

TEXT = {
    'en': {
        'html_lang': 'en',
        'eyebrow': 'META · TIKTOK · LEAD-GEN · AD OPS',
        'title': 'Ad Ops Agent',
        'lede': "Turns yesterday's ad data into a gated change list, and checks every change actually landed",
        'chip_ready': 'findings ready for review',
        'chip_human': 'held for a human',
        'chip_effect': "change that didn't take effect",
        'chip_effect_n': "changes that didn't take effect",
        'foot': 'Fictional data · replay of one 12-hour round · {calls} platform calls',
        'panel': 'Decisions by ad set',
        'columns': ('Ad set', 'Leads', 'CPA', 'T', 'Decision', 'Gate'),
        'labels': {
            'promote': 'Promote → {stage}', 'no_leads': 'Pause · no leads', 'over_cost': 'Pause · over cost',
            'early': 'Pause · early stop', 'tracking': 'Pause · tracking', 'hold_breaker': 'Hold · breaker',
            'hold_overflow': 'Hold · overflow', 'hold_other': 'Hold · blocker', 'undertested': 'Under-tested',
            'ad_status': 'Fix or appeal', 'no_change': 'No change',
        },
        'status': {
            'ready': 'ready', 'satisfied': 'satisfied', 'conflict': 'conflict', 'unknown': 'unknown',
            'advisory': 'advisory', 'unreconciled': 'unreconciled', 'not_effective': 'not in effect',
        },
        'receipt_eyebrow': 'BUILD RECEIPT · REPLAY, FICTIONAL VALUES',
        'receipt_title': '{platform} · {account} · {currency}',
        'step_created': 'Created PAUSED', 'step_created_value': '{paused}/{objects} objects',
        'step_readback': 'Readback', 'step_readback_value': '{matched}/{fields} fields',
        'step_decision': 'Decision', 'problems_one': '{n} problem: nothing is activated',
        'problems_many': '{n} problems: nothing is activated',
        'activate_sub': 'every field matches; still needs approval',
        'receipt_foot': ('{shown} of {fields} fields shown: one per field type, plus every mismatch. '
                         'Full receipt: {golden} · {calls} platform calls'),
        'missing': 'missing',
    },
    'zh-CN': {
        'html_lang': 'zh-CN',
        'eyebrow': 'META · TIKTOK · 线索投放 · 广告运营',
        'title': 'Ad Ops Agent',
        'lede': '把昨天的投放数据，\n变成经过闸门核对的变更清单，\n并逐条确认变更真正生效',
        'chip_ready': '条发现通过闸门\n待人审阅',
        'chip_human': '条交人工处理',
        'chip_effect': '条变更未生效\n已被发现',
        'chip_effect_n': '条变更未生效\n已被发现',
        'foot': '虚构数据 · 回放一轮 12 小时巡检 · 平台调用 {calls} 次',
        'panel': '判定明细（按广告组）',
        'columns': ('广告组', '线索', 'CPA', 'T', '判定', '闸门'),
        'labels': {
            'promote': '晋级 → {stage}', 'no_leads': '暂停 · 无线索', 'over_cost': '暂停 · 超成本',
            'early': '暂停 · 提前止损', 'tracking': '暂停 · 链路', 'hold_breaker': '保持 · 素材熔断',
            'hold_overflow': '保持 · 素材过多', 'hold_other': '保持 · 阻断项', 'undertested': '测试不足',
            'ad_status': '修改或申诉', 'no_change': '不变',
        },
        'status': {
            'ready': '待审', 'satisfied': '已满足', 'conflict': '冲突', 'unknown': '未知',
            'advisory': '仅建议', 'unreconciled': '口径未对齐', 'not_effective': '未生效',
        },
        'receipt_eyebrow': '搭建回执 · 回放，数值均为虚构',
        'receipt_title': '{platform} · {account} · {currency}',
        'step_created': '暂停创建', 'step_created_value': '{paused}/{objects} 个对象',
        'step_readback': '回读', 'step_readback_value': '{matched}/{fields} 个字段',
        'step_decision': '结论', 'problems_one': '{n} 个问题：不启用任何对象',
        'problems_many': '{n} 个问题：不启用任何对象',
        'activate_sub': '字段全部一致；仍需批准',
        'receipt_foot': ('展示 {fields} 个字段中的 {shown} 个：每类字段一行，外加全部不一致项。'
                         '完整回执：{golden} · 平台调用 {calls} 次'),
        'missing': '缺失',
    },
}
ICONS = {'promote': '✓', 'stop': '✗', 'human': '▲', 'advisory': '◆', 'hold': '=', 'muted': '·'}

CSS_BASE = """
:root {
  --bg: #F4F7F4; --surface: #FFFFFF; --ink: #17352D; --muted: #516B60; --line: #CCDCD1;
  --rule: #E6EEE8; --accent: #13785B;
  --promote: #13785B; --promote-bg: #E1F1E9; --hold: #5B6B7A; --hold-bg: #ECEFF2;
  --stop: #B42318; --stop-bg: #FCE8E6; --human: #875A11; --human-bg: #FFF0D4;
  --advisory: #2F5D8A; --advisory-bg: #E5EDF6;
  --sans: system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, "PingFang SC",
          "Hiragino Sans GB", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif;
  --mono: "JetBrains Mono", "SF Mono", ui-monospace, Menlo, Consolas, "Liberation Mono", monospace;
}
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; background: transparent; }
body { font-family: var(--sans); color: var(--ink); font-variant-numeric: tabular-nums;
       -webkit-font-smoothing: antialiased; text-rendering: geometricPrecision; }
.mono { font-family: var(--mono); }
.num { text-align: right; }
.pill { display: inline-flex; align-items: center; height: 19px; padding: 0 8px; border-radius: 10px;
        font-size: 11px; font-weight: 640; white-space: nowrap; letter-spacing: 0.005em; }
.pill.promote { color: var(--promote); background: var(--promote-bg); }
.pill.hold { color: var(--hold); background: var(--hold-bg); }
.pill.stop { color: var(--stop); background: var(--stop-bg); }
.pill.human { color: var(--human); background: var(--human-bg); }
.pill.advisory { color: var(--advisory); background: var(--advisory-bg); }
.status { white-space: nowrap; color: var(--muted); font-size: 11.5px; }
.status .icon { display: inline-block; width: 13px; font-weight: 700; }
.status.promote .icon { color: var(--promote); }
.status.stop .icon { color: var(--stop); }
.status.stop { color: var(--stop); font-weight: 600; }
.status.human .icon { color: var(--human); }
.status.human { color: var(--human); font-weight: 600; }
.status.advisory .icon { color: var(--advisory); }
.status.hold .icon, .status.muted .icon { color: var(--hold); }
"""


def esc(value):
    return html.escape(str(value), quote=True)


def page(lang, title, width, height, css, body):
    return ('<!doctype html>\n'
            f'<html lang="{esc(TEXT[lang]["html_lang"])}">\n<head>\n<meta charset="utf-8">\n'
            f'<title>{esc(title)}</title>\n'
            '<!-- Generated by scripts/render_visuals.py from demo output. Do not edit by hand. -->\n'
            f'<style>{CSS_BASE}\nbody {{ width: {width}px; height: {height}px; }}\n{css}</style>\n'
            f'</head>\n<body>\n{body}\n</body>\n</html>\n')


def lede(text):
    return '<br>'.join(esc(line) for line in text['lede'].split('\n'))


def label_text(row, text):
    name, stage = row['label']
    return text['labels'][name].format(stage=stage)


def status_cell(row, text):
    tone, name = row['status']
    return (f'<span class="status {tone}"><span class="icon">{ICONS[tone]}</span>'
            f'{esc(text["status"][name])}</span>')


def decision_table(rows, text, columns=('short', 'results', 'cpa', 't', 'decision', 'gate')):
    heads = dict(zip(('short', 'results', 'cpa', 't', 'decision', 'gate'), text['columns']))
    numeric = {'results', 'cpa', 't'}
    out = ['<table>', '<thead><tr>']
    for column in columns:
        out.append(f'<th class="{column}{" num" if column in numeric else ""}">{esc(heads[column])}</th>')
    out.append('</tr></thead>')
    out.append('<tbody>')
    for row in rows:
        cells = []
        for column in columns:
            if column == 'short':
                cells.append(f'<td class="short mono">{esc(row["short"])}</td>')
            elif column == 'results':
                cells.append(f'<td class="results num">{esc(row["results"])}</td>')
            elif column == 'cpa':
                cells.append(f'<td class="cpa num">{esc(row["cpa"] or "—")}</td>')
            elif column == 't':
                cells.append(f'<td class="t num">{esc(row["t"])}</td>')
            elif column == 'decision':
                cells.append(f'<td class="decision"><span class="pill {row["tone"]}">'
                             f'{esc(label_text(row, text))}</span></td>')
            else:
                cells.append(f'<td class="gate">{status_cell(row, text)}</td>')
        out.append('<tr>' + ''.join(cells) + '</tr>')
    out.append('</tbody></table>')
    return '\n'.join(out)


def chips(numbers, text):
    effect = text['chip_effect'] if numbers['not_effective'] == 1 else text['chip_effect_n']
    items = [
        ('promote', f'{numbers["ready"]}<span class="of">/{numbers["total"]}</span>', text['chip_ready']),
        ('human', str(numbers['needs_human']),
         text['chip_human'].format(conflict=numbers['conflict'], unknown=numbers['unknown'])),
        ('stop', str(numbers['not_effective']), effect),
    ]
    out = ['<div class="chips">']
    for tone, big, label in items:
        out.append(f'<div class="chip"><div class="big"><span class="icon {tone}">{ICONS[tone]}</span>{big}</div>'
                   f'<div class="label">{"<br>".join(esc(part) for part in label.split(chr(10)))}</div></div>')
    out.append('</div>')
    return '\n'.join(out)


# --------------------------------------------------------------------------
# images
# --------------------------------------------------------------------------

HERO_SIZE = (880, 440)
HERO_CSS = """
.card { width: 880px; height: 440px; border: 1px solid var(--line); border-radius: 20px; background: var(--bg);
        padding: 30px 26px 26px 34px; display: flex; gap: 26px; overflow: hidden; }
.left { flex: 1 1 auto; display: flex; flex-direction: column; min-width: 0; }
.eyebrow { font-size: 11px; font-weight: 700; letter-spacing: 0.14em; color: var(--accent); }
h1 { font-size: 44px; line-height: 1.05; font-weight: 760; letter-spacing: -0.024em; margin: 14px 0 14px; }
.lede { font-size: 18px; line-height: 1.45; margin: 0; color: var(--ink); font-weight: 450; }
.chips { display: flex; gap: 8px; margin-top: auto; }
.chip { flex: 1 1 0; background: var(--surface); border: 1px solid var(--line); border-radius: 12px;
        padding: 10px 10px 11px; }
.chip .big { font-size: 22px; font-weight: 720; line-height: 1; letter-spacing: -0.01em; white-space: nowrap; }
.chip .big .of { font-size: 14px; font-weight: 600; color: var(--muted); }
.chip .icon { font-size: 13px; margin-right: 5px; position: relative; top: -3px; }
.icon.promote { color: var(--promote); } .icon.human { color: var(--human); } .icon.stop { color: var(--stop); }
.chip .label { font-size: 11px; line-height: 1.35; color: var(--muted); margin-top: 7px; }
.foot { margin-top: 16px; font-size: 11px; color: var(--muted); letter-spacing: 0.01em; }
.panel { flex: 0 0 452px; background: var(--surface); border: 1px solid var(--line); border-radius: 14px;
         position: relative; overflow: hidden; }
.panel .head { display: flex; justify-content: space-between; align-items: baseline; padding: 13px 16px 9px; }
.panel .head .title { font-size: 12.5px; font-weight: 680; }
.panel .head .round { font-size: 10.5px; color: var(--muted); }
table { width: 100%; border-collapse: collapse; font-size: 12px; }
th { font-size: 10px; font-weight: 650; letter-spacing: 0.06em; text-transform: uppercase; color: var(--muted);
     text-align: left; padding: 7px 7px 6px; border-top: 1px solid var(--rule); border-bottom: 1px solid var(--line);
     white-space: nowrap; }
td { height: 24px; padding: 0 7px; border-bottom: 1px solid var(--rule); white-space: nowrap; }
th:first-child, td:first-child { padding-left: 16px; } th:last-child, td:last-child { padding-right: 14px; }
td.short { font-size: 11.5px; color: var(--ink); width: 54px; }
td.results { width: 44px; } td.cpa { width: 52px; } td.t { width: 50px; color: var(--muted); }
th.decision, td.decision { padding-left: 14px; }
.fade { position: absolute; left: 0; right: 0; bottom: 0; height: 56px;
        background: linear-gradient(rgba(255,255,255,0), var(--surface) 88%); }
"""


def render_hero(data, lang):
    text = TEXT[lang]
    numbers = headline(data)
    body = f"""<div class="card">
<div class="left">
<div class="eyebrow">{esc(text['eyebrow'])}</div>
<h1>{esc(text['title'])}</h1>
<p class="lede">{lede(text)}</p>
{chips(numbers, text)}
<div class="foot">{esc(text['foot'].format(calls=numbers['calls']))}</div>
</div>
<div class="panel">
<div class="head"><span class="title">{esc(text['panel'])}</span><span class="round mono">{esc(numbers['round_id'])}</span></div>
{decision_table(decision_rows(data), text)}
<div class="fade"></div>
</div>
</div>"""
    return page(lang, f'{text["title"]} hero', HERO_SIZE[0], HERO_SIZE[1], HERO_CSS, body)


RECEIPT_WIDTH = 880
# Every block in the receipt has a fixed height, so the page height (and the
# screenshot size) follows from the number of rows without measuring anything.
RECEIPT_ROW = 32
RECEIPT_LINE = 17       # one line of URL parameter names
RECEIPT_ROW_PAD = 16
RECEIPT_PROBLEM = 54   # 12 margin + 42 box
RECEIPT_FIXED = 284    # borders, padding, header, steps, table head, footer
RECEIPT_CSS = """
.card { width: 880px; border: 1px solid var(--line); border-radius: 20px; background: var(--bg);
        padding: 26px 30px 22px; overflow: hidden; }
.top { height: 56px; display: flex; justify-content: space-between; align-items: flex-start; }
.eyebrow { font-size: 11px; font-weight: 700; letter-spacing: 0.14em; color: var(--accent); }
h1 { font-size: 22px; line-height: 28px; font-weight: 720; letter-spacing: -0.01em; margin: 8px 0 0; white-space: nowrap; }
h1 .mono { font-size: 19px; font-weight: 600; }
.verdict { font-size: 22px; line-height: 26px; font-weight: 780; letter-spacing: 0.06em; padding: 9px 20px; border-radius: 12px; }
.verdict.hold { color: var(--stop); background: var(--stop-bg); border: 1px solid #F3C4BE; }
.verdict.activate { color: var(--promote); background: var(--promote-bg); border: 1px solid #B9DCCB; }
.steps { height: 84px; display: flex; align-items: stretch; margin-top: 18px; }
.step { flex: 1 1 0; background: var(--surface); border: 1px solid var(--line); border-radius: 12px; padding: 12px 14px 0; }
.step.hold { background: var(--stop-bg); border-color: #F3C4BE; }
.step.activate { background: var(--promote-bg); border-color: #B9DCCB; }
.step .k { font-size: 10.5px; line-height: 13px; font-weight: 650; letter-spacing: 0.07em; text-transform: uppercase; color: var(--muted); }
.step .v { font-size: 20px; line-height: 24px; font-weight: 720; margin-top: 5px; white-space: nowrap; }
.step.hold .v { color: var(--stop); } .step.activate .v { color: var(--promote); }
.step .s { font-size: 11px; line-height: 14px; color: var(--muted); margin-top: 4px; white-space: nowrap; }
.arrow { flex: 0 0 34px; display: flex; align-items: center; justify-content: center; color: var(--muted); font-size: 18px; }
.problem { height: 42px; line-height: 40px; margin-top: 12px; background: var(--stop-bg); border: 1px solid #F3C4BE;
           border-radius: 10px; padding: 0 14px; font-size: 13px; color: #7A1A12; white-space: nowrap;
           overflow: hidden; text-overflow: ellipsis; }
.problem b { color: var(--stop); margin-right: 8px; }
.problem .mono { font-size: 12.5px; font-weight: 600; }
.panel { margin-top: 14px; background: var(--surface); border: 1px solid var(--line); border-radius: 14px; overflow: hidden; }
.row { display: grid; grid-template-columns: 84px 178px 124px 1fr 1fr 54px; align-items: center;
       height: 32px; border-top: 1px solid var(--rule); font-size: 12px; }
.row > div { padding: 0 8px; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }
.row > div:first-child { padding-left: 16px; } .row > div:last-child { text-align: center; padding: 0; }
.row.head { height: 32px; border-top: 0; border-bottom: 1px solid var(--line); font-size: 10px; font-weight: 650;
            letter-spacing: 0.06em; text-transform: uppercase; color: var(--muted); }
.row.head + .row { border-top: 0; }
.row .object { font-family: var(--mono); font-size: 11.5px; padding-right: 2px; }
.row .value { font-family: var(--mono); font-size: 11px; }
.row .level { color: var(--muted); }
.row.bad { background: #FFF6F5; }
.row.bad .field { color: var(--stop); font-weight: 650; }
.mark { font-weight: 800; font-size: 13px; }
.mark.ok { color: var(--promote); } .mark.bad { color: var(--stop); }
.params { display: block; line-height: 17px; white-space: normal; }
.param { display: inline-block; }
.param + .param { margin-left: 8px; }
.param.missing { color: var(--stop); background: var(--stop-bg); border-radius: 4px; padding: 0 5px; font-weight: 650; }
.foot { height: 16px; line-height: 16px; margin-top: 12px; font-size: 11px; color: var(--muted); white-space: nowrap;
        overflow: hidden; text-overflow: ellipsis; }
"""


def param_names(value):
    return [name for name, _ in parse_qsl(value or '', keep_blank_values=True)]


def params_cell(names, missing=(), text=None):
    """Parameter names two per line, then each missing one on its own line.

    Returns the HTML and the number of lines, which sets the row height.
    """
    present = [f'<span class="param">{esc(name)}</span>' for name in names]
    lines = [''.join(present[index:index + 2]) for index in range(0, len(present), 2)]
    lines += [f'<span class="param missing">✗ {esc(name)} {esc(text["missing"])}</span>' for name in missing]
    return f'<span class="params">{"<br>".join(lines)}</span>', max(1, len(lines))


def row_height(lines):
    return RECEIPT_ROW if lines <= 1 else RECEIPT_LINE * lines + RECEIPT_ROW_PAD


def render_receipt(data, lang):
    text = TEXT[lang]
    labels = readback.TEXT[lang]
    build = data['build']
    rows = receipt_rows(build)
    hold = build['decision'] == 'hold'
    count = len(build['reasons'])
    platform = readback.ADAPTERS[build['platform']]['name']
    not_returned = labels['not_returned'].strip('*')
    title = text['receipt_title'].format(
        platform=esc(platform), account=f'<span class="mono">{esc(build["account_key"])}</span>',
        currency=esc(build['currency']))
    decision = build['decision'].upper()
    sub = (text['problems_one' if count == 1 else 'problems_many'].format(n=count) if hold
           else text['activate_sub'])
    tone = 'hold' if hold else 'activate'
    problems = ''.join(
        f'<div class="problem"><b>✗</b><span class="mono">{esc(reason["object_key"])}</span>'
        f'{" · " + esc(labels["field_labels"][reason["field"]]) if reason["field"] else ""}'
        f'{esc(labels["colon"])}{esc(readback.reason_text(reason, labels).replace("`", ""))}</div>\n'
        for reason in build['reasons'])
    table = ['<div class="row head">' + ''.join(f'<div>{esc(name)}</div>' for name in labels['columns'])
             + '</div>']
    rows_height = 0
    for row in rows:
        classes = ['row']
        planned, read = row['planned'], row['read_back']
        lines = 1
        if row['field'] == 'url_parameters':
            wanted = param_names(planned)
            planned_html, lines = params_cell(wanted, text=text)
            if read is not None:
                got = param_names(read)
                read_html, read_lines = params_cell(got, [name for name in wanted if name not in got], text)
                lines = max(lines, read_lines)
            else:
                read_html = esc(not_returned)
        else:
            planned_html = esc(planned)
            read_html = esc(read) if read is not None else esc(not_returned)
        if not row['match']:
            classes.append('bad')
        height = row_height(lines)
        rows_height += height
        mark = '<span class="mark ok">✓</span>' if row['match'] else '<span class="mark bad">✗</span>'
        style = f' style="height: {height}px"' if height != RECEIPT_ROW else ''
        table.append(
            f'<div class="{" ".join(classes)}"{style}>'
            f'<div class="level">{esc(readback.level_label(row["level"], build["platform"], lang))}</div>'
            f'<div class="object">{esc(row["object_key"])}</div>'
            f'<div class="field">{esc(labels["field_labels"][row["field"]])}</div>'
            f'<div class="value">{planned_html}</div><div class="value">{read_html}</div>'
            f'<div>{mark}</div></div>')
    foot = text['receipt_foot'].format(shown=len(rows), fields=build['fields'], golden=RECEIPT_GOLDEN,
                                       calls=build['native_platform_calls'])
    height = RECEIPT_FIXED + RECEIPT_PROBLEM * count + rows_height
    body = f"""<div class="card" style="height: {height}px">
<div class="top">
<div><div class="eyebrow">{esc(text['receipt_eyebrow'])}</div><h1>{title}</h1></div>
<div class="verdict {tone}">{esc(decision)}</div>
</div>
<div class="steps">
<div class="step"><div class="k">{esc(text['step_created'])}</div>
<div class="v">{esc(text['step_created_value'].format(paused=build['objects_paused'], objects=build['objects']))}</div>
<div class="s mono">{esc(build['created_at'] or '—')}</div></div>
<div class="arrow">→</div>
<div class="step"><div class="k">{esc(text['step_readback'])}</div>
<div class="v">{esc(text['step_readback_value'].format(matched=build['fields_matched'], fields=build['fields']))}</div>
<div class="s mono">{esc(build['read_at'] or '—')}</div></div>
<div class="arrow">→</div>
<div class="step {tone}"><div class="k">{esc(text['step_decision'])}</div>
<div class="v">{esc(decision)}</div><div class="s">{esc(sub)}</div></div>
</div>
{problems}<div class="panel">
{chr(10).join(table)}
</div>
<div class="foot">{esc(foot)}</div>
</div>"""
    return page(lang, f'{platform} build receipt', RECEIPT_WIDTH, height, RECEIPT_CSS, body), height


SOCIAL_SIZE = (1280, 640)
SOCIAL_ROWS = 11
SOCIAL_CSS = """
body { background: #10281F; }
.frame { width: 1280px; height: 640px; background: #10281F; position: relative; overflow: hidden;
         padding: 64px 0 0 72px; display: flex; gap: 56px; }
.left { flex: 0 0 560px; display: flex; flex-direction: column; height: 512px; }
.eyebrow { font-size: 15px; font-weight: 700; letter-spacing: 0.16em; color: #6FD3A8; }
h1 { font-size: 76px; line-height: 1; font-weight: 780; letter-spacing: -0.03em; color: #F4F7F4; margin: 22px 0 22px; }
.lede { font-size: 26px; line-height: 1.38; color: #C8DCD2; margin: 0; font-weight: 450; }
.chips { display: flex; gap: 12px; margin-top: 34px; }
.chip { flex: 1 1 0; background: #173A2D; border: 1px solid #2D5646; border-radius: 14px; padding: 14px 14px 15px; }
.chip .big { font-size: 34px; font-weight: 740; color: #F4F7F4; line-height: 1; white-space: nowrap; }
.chip .big .of { font-size: 20px; color: #A9C6B8; font-weight: 600; }
.chip .icon { font-size: 18px; margin-right: 7px; position: relative; top: -5px; }
.icon.promote { color: #5FD39C; } .icon.human { color: #F2B65A; } .icon.stop { color: #FF8A7A; }
.chip .label { font-size: 14px; line-height: 1.35; color: #A9C6B8; margin-top: 9px; }
.foot { margin-top: auto; font-size: 15px; color: #8DB1A1; }
.foot .repo { color: #DDEBE3; font-weight: 600; }
.panel { flex: 1 1 auto; margin-right: -2px; height: 640px; background: var(--surface); border-radius: 18px 0 0 0;
         border: 1px solid #2D5646; position: relative; overflow: hidden; }
.panel .head { display: flex; justify-content: space-between; align-items: baseline; padding: 22px 26px 14px; }
.panel .head .title { font-size: 19px; font-weight: 700; }
.panel .head .round { font-size: 14px; color: var(--muted); }
table { width: 100%; border-collapse: collapse; font-size: 17px; }
th { font-size: 13px; font-weight: 650; letter-spacing: 0.06em; text-transform: uppercase; color: var(--muted);
     text-align: left; padding: 9px 10px; border-top: 1px solid var(--rule); border-bottom: 1px solid var(--line); }
td { height: 44px; padding: 0 10px; border-bottom: 1px solid var(--rule); white-space: nowrap; }
th:first-child, td:first-child { padding-left: 26px; }
td.short { font-size: 16px; }
td.t { color: var(--muted); }
.pill { height: 28px; padding: 0 12px; border-radius: 14px; font-size: 15px; }
.status { font-size: 15px; } .status .icon { width: 18px; }
th:last-child, td:last-child { padding-right: 26px; }
.fade { position: absolute; left: 0; right: 0; bottom: 0; height: 120px;
        background: linear-gradient(rgba(255,255,255,0), var(--surface) 85%); }
"""


def render_social(data):
    lang = 'en'
    text = TEXT[lang]
    numbers = headline(data)
    rows = decision_rows(data)[:SOCIAL_ROWS]
    body = f"""<div class="frame">
<div class="left">
<div class="eyebrow">{esc(text['eyebrow'])}</div>
<h1>{esc(text['title'])}</h1>
<p class="lede">{lede(text)}</p>
{chips(numbers, text)}
<div class="foot"><span class="repo">github.com/creator2000212-crypto/ad-ops-agent</span><br>{esc(text['foot'].format(calls=numbers['calls']))}</div>
</div>
<div class="panel">
<div class="head"><span class="title">{esc(text['panel'])}</span><span class="round mono">{esc(numbers['round_id'])}</span></div>
{decision_table(rows, text, columns=('short', 'cpa', 't', 'decision', 'gate'))}
<div class="fade"></div>
</div>
</div>"""
    return page(lang, 'Ad Ops Agent social preview', SOCIAL_SIZE[0], SOCIAL_SIZE[1], SOCIAL_CSS, body)


def targets(data):
    """(source, png, css width, css height, device scale, html) for every image."""
    out = []
    for lang in ('en', 'zh-CN'):
        out.append((f'hero.{lang}.html', f'hero/hero.{lang}.png', HERO_SIZE[0], HERO_SIZE[1], 2,
                    render_hero(data, lang)))
        receipt, height = render_receipt(data, lang)
        out.append((f'receipt.{lang}.html', f'proof/receipt.{lang}.png', RECEIPT_WIDTH, height, 2, receipt))
    out.append(('social-preview.html', 'social/social-preview.png', SOCIAL_SIZE[0], SOCIAL_SIZE[1], 1,
                render_social(data)))
    return out


# --------------------------------------------------------------------------
# screenshots
# --------------------------------------------------------------------------

def find_chrome(explicit=None):
    for candidate in ((explicit,) if explicit else ()) + ((os.environ.get('CHROME'),) if os.environ.get('CHROME')
                                                          else ()) + CHROME_CANDIDATES:
        path = shutil.which(candidate) or (candidate if Path(candidate).is_file() else None)
        if path:
            return path
    raise VisualError('Google Chrome or Chromium not found; pass --chrome PATH or set CHROME, '
                      'or use --html to write the sources only.')


def png_size(data):
    if len(data) < 24 or data[:8] != PNG_SIGNATURE:
        raise VisualError('not a PNG file')
    return struct.unpack('>II', data[16:24])


def _complete(path):
    try:
        data = path.read_bytes()
    except OSError:
        return False
    return len(data) > 32 and data[:8] == PNG_SIGNATURE and data.endswith(PNG_END)


def _stop(process):
    if process.poll() is not None:
        return
    try:
        if os.name == 'posix':
            os.killpg(process.pid, signal.SIGTERM)
        else:
            process.terminate()
        process.wait(timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        process.kill()


def screenshot(chrome, source, width, height, scale, timeout=90):
    """Screenshot ``source`` with headless Chrome and return the PNG bytes.

    Some Chrome builds keep running after writing ``--screenshot``; the PNG is
    taken as soon as it is complete and the browser is then stopped.
    """
    with tempfile.TemporaryDirectory() as temp:
        target = Path(temp) / 'shot.png'
        command = [chrome, '--headless=new', '--hide-scrollbars', '--no-first-run', '--no-default-browser-check',
                   '--disable-extensions', '--disable-gpu', '--user-data-dir=' + str(Path(temp) / 'profile'),
                   f'--force-device-scale-factor={scale}', f'--window-size={width},{height}',
                   '--default-background-color=00000000', '--screenshot=' + str(target),
                   source.resolve().as_uri()]
        kwargs = {'start_new_session': True} if os.name == 'posix' else {}
        process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **kwargs)
        try:
            deadline = time.monotonic() + timeout
            while not _complete(target):
                if process.poll() is not None and not _complete(target):
                    time.sleep(0.5)
                    if not _complete(target):
                        raise VisualError(f'Chrome exited without a screenshot of {source.name}')
                if time.monotonic() > deadline:
                    raise VisualError(f'Chrome timed out on {source.name}')
                time.sleep(0.2)
            time.sleep(0.3)
            data = target.read_bytes()
        finally:
            _stop(process)
    expected = (width * scale, height * scale)
    if png_size(data) != expected:
        raise VisualError(f'{source.name}: screenshot is {png_size(data)}, expected {expected}')
    return recompress(data)


def recompress(data):
    """Re-deflate the image data at level 9 (pure stdlib); pixels are unchanged."""
    chunks, index = [], 8
    while index < len(data):
        length, = struct.unpack('>I', data[index:index + 4])
        kind = data[index + 4:index + 8]
        chunks.append((kind, data[index + 8:index + 8 + length]))
        index += 12 + length
    pixels = zlib.decompress(b''.join(body for kind, body in chunks if kind == b'IDAT'))
    out, wrote = [PNG_SIGNATURE], False
    for kind, body in chunks:
        if kind == b'IDAT':
            if wrote:
                continue
            kind, body, wrote = b'IDAT', zlib.compress(pixels, 9), True
        out.append(struct.pack('>I', len(body)) + kind + body
                   + struct.pack('>I', zlib.crc32(kind + body) & 0xFFFFFFFF))
    smaller = b''.join(out)
    return smaller if len(smaller) < len(data) else data


# --------------------------------------------------------------------------
# write and check
# --------------------------------------------------------------------------

def sha256(data):
    return hashlib.sha256(data).hexdigest()


def rel(path):
    return Path(path).resolve().relative_to(ROOT).as_posix()


def write_sources(items):
    SOURCES.mkdir(parents=True, exist_ok=True)
    for source, _, _, _, _, content in items:
        (SOURCES / source).write_text(content, encoding='utf-8')


def render(items, chrome):
    images = {}
    for source, png, width, height, scale, _ in items:
        html_path = SOURCES / source
        data = screenshot(chrome, html_path, width, height, scale)
        out = ASSETS / png
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)
        images[rel(out)] = {'source': rel(html_path), 'source_sha256': sha256(html_path.read_bytes()),
                            'png_sha256': sha256(data), 'css_size': [width, height], 'scale': scale,
                            'pixels': list(png_size(data)), 'bytes': len(data)}
        print(f'{rel(out)}  {png_size(data)[0]}x{png_size(data)[1]}  {len(data) // 1024} KB')
    manifest = {'notice': ('Generated by scripts/render_visuals.py. Each PNG is a headless-Chrome screenshot of '
                           'its HTML source, which is rendered from demo output; --check verifies both hashes.'),
                'images': images}
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n', encoding='utf-8')


TABLE_SPLIT = re.compile(r'(?<!\\)\|')
EXCERPT = re.compile(r'<!-- excerpt: (\S+) -->\n(.*?)<!-- /excerpt -->', re.S)


def table_cells(line):
    line = line.strip()
    if not line.startswith('|'):
        return None
    cells = [cell.strip() for cell in TABLE_SPLIT.split(line.strip('|'))]
    if all(set(cell) <= set(':- ') for cell in cells):
        return None
    return cells


def source_rows(path):
    """Rows of a generated source, keyed by their first cell."""
    rows = {}
    if path.suffix == '.json':
        document = json.loads(path.read_text(encoding='utf-8'))
        for action in document.get('actions') or []:
            cells = {f'`{action["code"]}`', action['level']}
            for key in ('action', 'window', 'acceptance', 'stop_condition'):
                cells.add(action.get(key, ''))
                cells.add((action.get('en') or {}).get(key, ''))
            rows.setdefault(f'`{action["code"]}`', []).append(cells)
        return rows
    for line in path.read_text(encoding='utf-8').splitlines():
        cells = table_cells(line)
        if cells:
            rows.setdefault(cells[0], []).append(set(cells))
    return rows


def check_readme(name):
    problems = []
    path = ROOT / name
    text = path.read_text(encoding='utf-8')
    for source, block in EXCERPT.findall(text):
        target = ROOT / source
        if not target.is_file():
            problems.append(f'{name}: excerpt source {source} does not exist')
            continue
        rows = source_rows(target)
        for line in block.splitlines():
            cells = table_cells(line)
            if not cells or not cells[0].startswith('`'):
                continue  # headers are free text; data rows are keyed by a code or object
            if not any(set(cells) <= candidate for candidate in rows.get(cells[0], [])):
                problems.append(f'{name}: excerpt row {cells[0]} no longer matches {source}')
    python = [p for p in ROOT.glob('*.py')] + list((ROOT / 'scripts').glob('*.py'))
    tests = list((ROOT / 'tests').glob('test_*.py'))
    defined = set()
    for file in python:
        defined.update(re.findall(r'^\s*def (\w+)\(', file.read_text(encoding='utf-8'), re.M))
    test_names = set()
    for file in tests:
        test_names.update(re.findall(r'^\s*def (test_\w+)\(', file.read_text(encoding='utf-8'), re.M))
    for function in sorted(set(re.findall(r'`(?:[\w.]+\.)?(\w+)\(\)`', text))):
        if function not in defined:
            problems.append(f'{name}: names `{function}()`, which is not defined')
    for test in sorted(set(re.findall(r'`(test_\w+)`', text))):
        if test not in test_names:
            problems.append(f'{name}: names `{test}`, which is not a test')
    return problems


def check(items):
    problems = []
    manifest = {}
    if MANIFEST.is_file():
        manifest = json.loads(MANIFEST.read_text(encoding='utf-8')).get('images', {})
    else:
        problems.append(f'{rel(MANIFEST)} is missing')
    for source, png, width, height, scale, content in items:
        html_path, png_path = SOURCES / source, ASSETS / png
        if not html_path.is_file():
            problems.append(f'{rel(html_path)} is missing')
            continue
        committed = html_path.read_text(encoding='utf-8')
        if committed != content:
            problems.append(f'{rel(html_path)} differs from what the current demo output renders')
        entry = manifest.get(rel(png_path))
        if not png_path.is_file():
            problems.append(f'{rel(png_path)} is missing')
            continue
        data = png_path.read_bytes()
        if entry is None:
            problems.append(f'{rel(png_path)} is not in the manifest')
            continue
        if entry.get('source_sha256') != sha256(committed.encode('utf-8')):
            problems.append(f'{rel(png_path)} was rendered from an older {rel(html_path)}; re-render it')
        if entry.get('png_sha256') != sha256(data):
            problems.append(f'{rel(png_path)} does not match the manifest (edited by hand?)')
        if list(png_size(data)) != [width * scale, height * scale]:
            problems.append(f'{rel(png_path)} is {png_size(data)}, expected {(width * scale, height * scale)}')
    for name in READMES:
        problems.extend(check_readme(name))
    return problems


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--html', action='store_true', help='write the HTML sources only')
    mode.add_argument('--check', action='store_true', help='verify sources, PNGs and README excerpts; no browser')
    parser.add_argument('--chrome', help='path to Google Chrome or Chromium')
    args = parser.parse_args(argv)
    try:
        items = targets(collect())
        if args.check:
            problems = check(items)
            if problems:
                print('Visuals are out of date:', file=sys.stderr)
                for problem in problems:
                    print('  - ' + problem, file=sys.stderr)
                print('Regenerate with python3 scripts/render_visuals.py and review the images.', file=sys.stderr)
                return 1
            print(f'Visuals check passed: {len(items)} images match their sources; README excerpts match.')
            return 0
        write_sources(items)
        if args.html:
            print(f'Wrote {len(items)} HTML sources to {rel(SOURCES)}/ (PNGs not re-rendered).')
            return 0
        render(items, find_chrome(args.chrome))
        return 0
    except (VisualError, readback.ReadbackError, operating_rules.RuleError, RuntimeError) as exc:
        print(f'render_visuals: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())

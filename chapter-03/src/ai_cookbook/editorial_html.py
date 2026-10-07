"""Self-contained review page; source and generated markup remain plain text."""
from difflib import HtmlDiff
from html import escape
import json

from .editorial_checks import checks


def render(job, digest):
    original = '\n'.join(f'{key}: {text}' for key, text in job['sources'].items())
    parts = ["<!doctype html><html lang='en'><meta charset='utf-8'>",
             "<meta name='viewport' content='width=device-width, initial-scale=1'>",
             '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'">',
             '<title>Editorial review</title>',
             '<style>body{font:17px/1.5 system-ui,sans-serif;margin:2em;color:#20232a}'
             'h1,h2{line-height:1.2}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:inherit}'
             '.digest{font-family:monospace;overflow-wrap:anywhere}.columns{display:grid;gap:2em;grid-template-columns:1fr 1fr}'
             '.columns>section{min-width:0}.diffbox{overflow:auto}table{font:13px monospace;border-spacing:5px}'
             '.diff_add{background:#dcefdc}.diff_sub{background:#f4dada}.diff_chg{background:#fff0bb}'
             '@media(max-width:800px){body{margin:1em}.columns{grid-template-columns:1fr}}'
             '</style><body><h1>Editorial review</h1>',
             '<p>Draft package. Mechanical success is not approval.</p>',
             '<p>Package fingerprint:</p><p class="digest">' + digest + '</p>']

    def section(title, text):
        return f'<h2>{escape(title)}</h2><pre>{escape(text)}</pre>'

    findings = checks(job) or ['No mechanical flags. Meaning still needs review.']
    parts.append(section('Checks', '\n'.join(findings)))
    parts.append('<div class="columns"><section>')
    parts.append(section('Source packet', original))
    parts.append(section('Editorial brief', json.dumps(job['brief'], ensure_ascii=False, indent=2)))
    parts.append('</section><section>')
    for name, text in job['drafts'].items():
        parts.append(section(name.title(), text))
    parts.append('</section></div>')
    for title, value in (('Fact plan', job['fact_plan']), ('Questions', job['questions']),
                         ('Failure', {'type': job['failure'], 'stage': job.get('failure_stage')}),
                         ('Generation calls', job['calls']), ('Revision', job.get('revision'))):
        parts.append(section(title, json.dumps(value, ensure_ascii=False, indent=2)))
    parts.append('<h2>Source wording compared with the English rewrite</h2><div class="diffbox">')
    parts.append(HtmlDiff(wrapcolumn=60).make_table(
        original.splitlines(), job['drafts'].get('rewrite', '').splitlines(),
        fromdesc='Source packet', todesc='English rewrite'))
    parts.append('</div></body></html>')
    return '\n'.join(parts)

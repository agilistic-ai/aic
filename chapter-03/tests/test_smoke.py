"""Installed application + genuine SDKs + local HTTP fixtures; no live inference."""
import copy
from html.parser import HTMLParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest

from ai_cookbook.editorial_checks import contains_literal
from ai_cookbook.editorial_review import fingerprint, save

ROOT = Path(__file__).resolve().parents[1]
VERSIONS = json.loads((ROOT / 'tests/fixtures/versions.json').read_text(encoding='utf-8'))
MARKUP = '<script>alert("source")</script><img src=x onerror=alert("draft")>'


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        request = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        self.server.requests.append((self.path, request))
        scenario = self.server.scenarios.pop(0) if self.server.scenarios else 'normal'
        if scenario == 'timeout':
            time.sleep(0.4)
        if scenario == 'http_error':
            status, response = 503, {'error': {'message': 'PRIVATE PROVIDER ERROR', 'type': 'server_error'}}
        else:
            if self.path == '/v1/responses':
                payload = json.loads(request['input'][-1]['content'])
                instructions = request['instructions']
                schema = request['text']['format']['schema']
            elif self.path == '/api/chat':
                payload = json.loads(request['messages'][-1]['content'])
                instructions = request['messages'][0]['content']
                schema = request['format']
            else:
                self.send_error(404)
                return
            if 'facts' in schema['properties']:
                facts = [{'source_id': k, 'quote': v, 'claim': v} for k, v in payload['sources'].items()]
                if scenario == 'unsupported_quote':
                    facts[0]['quote'] = 'This quotation is invented.'
                if scenario == 'large_plan':
                    facts *= 25
                candidate = {'facts': facts, 'questions': []}
            elif 'summary' in schema['properties']:
                candidate = {**VERSIONS, 'questions': []}
            else:
                name = next(n for n in VERSIONS if f'Produce the {n} within' in instructions)
                candidate = {'text': VERSIONS[name], 'questions': []}
            if scenario == 'question':
                candidate['questions'] = ['The supplied event times disagree.']
            if scenario == 'extra_field':
                candidate['approved'] = True
            if scenario == 'mechanical':
                candidate['rewrite'] = VERSIONS['rewrite'].replace('Elm Community Room', 'Another venue') + ' Capacity is 30.'
                candidate['variant'] = VERSIONS['variant'].replace('evaluación', 'revisión')
            if scenario == 'meaning_shift':
                candidate['rewrite'] = VERSIONS['rewrite'].replace('require your prior approval', 'may be purchased before we ask for your approval')
            if scenario == 'markup':
                candidate['rewrite'] += ' ' + MARKUP
            text = '{' if scenario == 'invalid_json' else json.dumps(candidate)
            status = 200
            if self.path == '/v1/responses':
                content = ([{'type': 'refusal', 'refusal': 'PRIVATE REFUSAL'}] if scenario == 'refusal'
                           else [{'type': 'output_text', 'text': text, 'annotations': []}])
                response = {'id': 'resp_fixture', 'object': 'response', 'created_at': 1,
                            'model': request['model'], 'status': 'incomplete' if scenario == 'incomplete' else 'completed',
                            'output': [{'type': 'message', 'id': 'msg_fixture', 'role': 'assistant',
                                        'status': 'completed', 'content': content}],
                            'usage': {'input_tokens': 120, 'output_tokens': 90, 'total_tokens': 210}}
            else:
                response = {'model': request['model'], 'created_at': '2026-10-03T00:00:00Z',
                            'message': {'role': 'assistant', 'content': text}, 'done': True,
                            'done_reason': 'length' if scenario == 'incomplete' else 'stop',
                            'prompt_eval_count': 120, 'eval_count': 90}
        data = json.dumps(response).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass


class Tags(HTMLParser):
    def __init__(self):
        super().__init__()
        self.names = []
    def handle_starttag(self, tag, attrs):
        self.names.append(tag)


class EditorialSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        cls.server.daemon_threads = True
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.packet = self.folder / 'packet'
        shutil.copytree(ROOT / 'examples/editorial', self.packet)
        self.server.scenarios, self.server.requests = [], []
        endpoint = f'http://127.0.0.1:{self.server.server_port}'
        self.env = {**os.environ, 'AIC_API_KEY': 'smoke-only-key', 'AIC_OPENAI_BASE_URL': endpoint + '/v1',
                    'AIC_OLLAMA_HOST': endpoint, 'NO_PROXY': '127.0.0.1,localhost,::1', 'no_proxy': '127.0.0.1,localhost,::1'}

    def config(self, provider, timeout):
        path = self.folder / (provider + '.toml')
        path.write_text(f'[model]\nprovider="{provider}"\nname="fixture-model"\ntimeout_seconds={timeout}\n[run]\nrevision="smoke"\n')
        return path

    def cli(self, *args, expected=0, console=False, env=None):
        entry = ([str(Path(sys.executable).with_name('editorial.exe' if os.name == 'nt' else 'editorial'))]
                 if console else [sys.executable, '-m', 'ai_cookbook.editorial_cli'])
        result = subprocess.run([*entry, *map(str, args)], cwd=self.folder, env=env or self.env,
                                capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        self.assertNotIn('Traceback', result.stderr)
        return result

    def generate(self, method='single', provider='openai', *, expected=0, timeout=2):
        result = self.cli('run', self.packet, '--method', method, '--project', ROOT,
                          '--config', self.config(provider, timeout), '--output', self.folder / 'runs', expected=expected)
        report = json.loads(result.stdout)
        path = Path(report['package'])
        return path, json.loads(path.read_text()), report

    def approve(self, path, report, name='rewrite', *flags, expected=0):
        return self.cli('approve', path, name, '--expected-digest', report['digest'],
                        '--reviewer', 'Morgan', *flags, expected=expected)

    def test_01_both_providers_and_methods_complete_review_export(self):
        for provider in ('openai', 'ollama'):
            for method in ('single', 'staged'):
                with self.subTest(provider=provider, method=method):
                    before = len(self.server.requests)
                    path, job, report = self.generate(method, provider)
                    self.assertEqual(len(self.server.requests) - before, 1 if method == 'single' else 4)
                    self.assertEqual(job['drafts'], VERSIONS)
                    self.assertEqual(report['flags'], [])
                    self.assertIsNone(job['failure_stage'])
                    for _, request in self.server.requests[before:]:
                        if provider == 'openai':
                            payload = json.loads(request['input'][-1]['content'])
                            self.assertTrue(request['text']['format']['strict'])
                            self.assertEqual(request['max_output_tokens'], 2048)
                            self.assertFalse(request['store'])
                        else:
                            payload = json.loads(request['messages'][-1]['content'])
                            self.assertEqual(request['options']['num_ctx'], 16384)
                            self.assertEqual(request['options']['num_predict'], 2048)
                        self.assertEqual(payload['sources'], job['sources'])
                    if method == 'staged':
                        self.assertEqual(payload['english_rewrite'], VERSIONS['rewrite'])
                    html = path.with_suffix('.html').read_text()
                    self.assertIn(report['digest'], html)
                    self.assertIn('Fact plan', html)
                    self.approve(path, report, 'rewrite', '--meaning-reviewed')
                    destination = self.folder / f'{provider}-{method}.txt'
                    self.cli('export', path, 'rewrite', '--output', destination, console=True)
                    self.assertEqual(destination.read_text(), VERSIONS['rewrite'])
                    self.assertIn('editorial_cli.py', job['implementation']['code'])
                    self.assertIn('127.0.0.1', job['implementation']['effective_model']['base_url'])
                    self.assertNotIn('smoke-only-key', json.dumps(job['implementation']))

    def test_02_approval_required_and_stale_or_duplicate_export_refused(self):
        path, job, report = self.generate()
        out = self.folder / 'approved.txt'
        self.cli('export', path, 'rewrite', '--output', out, expected=2)
        self.assertFalse(out.exists())
        self.approve(path, report, expected=2)
        self.approve(path, {**report, 'digest': 'old'}, 'rewrite', '--meaning-reviewed', expected=2)
        self.approve(path, report, 'rewrite', '--meaning-reviewed')
        receipt = path.with_suffix('.rewrite.approval.json').read_bytes()
        self.approve(path, report, 'rewrite', '--meaning-reviewed', expected=2)
        self.assertEqual(path.with_suffix('.rewrite.approval.json').read_bytes(), receipt)
        self.cli('export', path, 'rewrite', '--output', out)
        self.cli('export', path, 'rewrite', '--output', out, expected=2)
        job['drafts']['rewrite'] = job['drafts']['rewrite'].replace('prior approval', 'approval afterward')
        path.write_text(json.dumps(job))
        self.cli('export', path, 'rewrite', '--output', self.folder / 'stale.txt', expected=2)
        self.assertFalse((self.folder / 'stale.txt').exists())

    def test_03_variant_needs_separate_meaning_and_language_review(self):
        path, _, report = self.generate()
        self.approve(path, report, 'rewrite', '--meaning-reviewed')
        self.cli('export', path, 'variant', '--output', self.folder / 'spanish.txt', expected=2)
        self.approve(path, report, 'variant', '--meaning-reviewed', expected=2)
        self.approve(path, report, 'variant', '--meaning-reviewed', '--language-reviewed')
        self.cli('export', path, 'variant', '--output', self.folder / 'spanish.txt')
        self.assertEqual((self.folder / 'spanish.txt').read_text(), VERSIONS['variant'])

    def test_04_correction_creates_new_package_and_keeps_old_approval(self):
        path, job, report = self.generate()
        self.approve(path, report, 'rewrite', '--meaning-reviewed')
        original = path.read_bytes()
        draft = self.folder / 'correction.txt'
        self.cli('draft', path, 'rewrite', '--output', draft)
        draft.write_text(draft.read_text().replace('takes place', 'will take place'))
        args = ('revise', path, 'rewrite', '--text-file', draft, '--editor', 'Morgan', '--reason', 'Adjusted wording.')
        self.cli(*args, '--expected-digest', 'old', expected=2)
        revised = json.loads(self.cli(*args, '--expected-digest', report['digest']).stdout)
        new_path = Path(revised['package'])
        self.assertEqual(json.loads(new_path.read_text())['revision_of'], fingerprint(job))
        self.assertEqual(path.read_bytes(), original)
        self.assertFalse(new_path.with_suffix('.rewrite.approval.json').exists())
        self.cli('export', new_path, 'rewrite', '--output', self.folder / 'unapproved.txt', expected=2)
        self.approve(new_path, revised, 'rewrite', '--meaning-reviewed')
        self.cli('export', new_path, 'rewrite', '--output', self.folder / 'revised.txt')
        self.assertEqual((self.folder / 'revised.txt').read_text(), draft.read_text())

    def test_05_malformed_output_has_usage_without_retry(self):
        for scenario in ('invalid_json', 'extra_field'):
            with self.subTest(scenario=scenario):
                self.server.scenarios = [scenario]
                before = len(self.server.requests)
                path, job, report = self.generate(expected=1)
                self.assertEqual(len(self.server.requests) - before, 1)
                self.assertEqual(job['failure'], 'ValidationError')
                self.assertEqual(job['calls'][0]['input_tokens'], 120)
                self.approve(path, report, 'rewrite', '--meaning-reviewed', expected=2)

    def test_06_provider_failures_make_one_call(self):
        for provider in ('openai', 'ollama'):
            for scenario in ('timeout', 'http_error', 'incomplete') + (('refusal',) if provider == 'openai' else ()):
                with self.subTest(provider=provider, scenario=scenario):
                    self.server.scenarios = [scenario]
                    before = len(self.server.requests)
                    _, job, _ = self.generate(provider=provider, expected=1, timeout=0.1 if scenario == 'timeout' else 2)
                    self.assertEqual(len(self.server.requests) - before, 1)
                    self.assertEqual(job['failure'], 'GenerationError')
                    self.assertIsNone(job['calls'][0]['input_tokens'])
                    self.assertNotIn('PRIVATE', json.dumps(job))

    def test_07_fact_questions_bad_evidence_and_payload_growth_stop_stages(self):
        for scenario in ('question', 'unsupported_quote', 'large_plan'):
            with self.subTest(scenario=scenario):
                self.server.scenarios = [scenario]
                before = len(self.server.requests)
                path, job, report = self.generate('staged', expected=1)
                self.assertEqual(len(self.server.requests) - before, 1)
                self.assertEqual(job['drafts'], {})
                self.assertEqual(job['failure_stage'], 'summary' if scenario == 'large_plan' else 'facts')
                if scenario == 'question':
                    self.assertEqual(job['questions'], ['The supplied event times disagree.'])
                self.approve(path, report, 'rewrite', '--meaning-reviewed', expected=2)

    def test_08_later_failure_preserves_partial_drafts_but_blocks_approval(self):
        self.server.scenarios = ['normal', 'normal', 'normal', 'timeout']
        path, job, report = self.generate('staged', expected=1, timeout=0.1)
        self.assertEqual(set(job['drafts']), {'summary', 'rewrite'})
        self.assertEqual(len(self.server.requests), 4)
        self.assertEqual(job['failure_stage'], 'variant')
        self.approve(path, report, 'rewrite', '--meaning-reviewed', expected=2)
        comparison = json.loads(self.cli('compare', path).stdout)
        self.assertEqual(comparison['input_tokens_known'], 360)
        self.assertEqual(comparison['input_tokens_unknown_calls'], 1)

    def test_09_mechanical_checks_and_their_semantic_limit(self):
        self.assertFalse(contains_literal('2026', '20'))
        self.assertTrue(contains_literal('evaluacio\u0301n', 'evaluación'))
        self.server.scenarios = ['mechanical']
        path, _, report = self.generate(expected=1)
        self.assertTrue(any('missing required literal' in flag for flag in report['flags']))
        self.assertTrue(any('numeric components' in flag for flag in report['flags']))
        self.assertTrue(any('approved term' in flag for flag in report['flags']))
        self.approve(path, report, 'rewrite', '--meaning-reviewed', expected=2)
        self.server.scenarios = ['meaning_shift']
        path, _, report = self.generate()
        self.assertEqual(report['flags'], [])
        self.cli('export', path, 'rewrite', '--output', self.folder / 'wrong.txt', expected=2)
        brief_path = self.packet / 'brief.json'
        brief = json.loads(brief_path.read_text()); brief['word_limits']['summary'] = 5
        brief_path.write_text(json.dumps(brief))
        _, _, report = self.generate(expected=1)
        self.assertTrue(any('word limit' in flag for flag in report['flags']))

    def test_10_html_escapes_markup_and_save_refuses_collisions(self):
        source_path = self.packet / 'sources.json'
        sources = json.loads(source_path.read_text()); sources['markup'] = MARKUP
        source_path.write_text(json.dumps(sources))
        self.server.scenarios = ['markup']
        _, job, _ = self.generate()
        destination = self.folder / 'preview.json'
        save(job, destination)
        html = destination.with_suffix('.html').read_text()
        tags = Tags(); tags.feed(html)
        self.assertNotIn('script', tags.names)
        self.assertNotIn('img', tags.names)
        self.assertIn('&lt;script&gt;', html)
        with self.assertRaises(FileExistsError): save(job, destination)
        with self.assertRaises(ValueError): save(job, self.folder / 'same.html')
        occupied = self.folder / 'occupied.html'; occupied.write_text('KEEP')
        with self.assertRaises(FileExistsError): save(job, self.folder / 'occupied.json')
        self.assertEqual(occupied.read_text(), 'KEEP')
        self.assertFalse((self.folder / 'occupied.json').exists())

    def test_11_invalid_inputs_rejected_before_generation(self):
        self.cli('--help', console=True, env={**self.env, 'AIC_API_KEY': ''})
        source_path = self.packet / 'sources.json'
        original = source_path.read_bytes()
        for raw in (b'[]', b'{', b'\xff', b'x' * 8001, b'{"empty":""}'):
            source_path.write_bytes(raw)
            self.cli('run', self.packet, '--project', ROOT, '--config', self.config('openai', 2), expected=2)
        source_path.write_bytes(original)
        brief_path = self.packet / 'brief.json'
        brief = json.loads(brief_path.read_text()); brief['word_limits']['summary'] = True
        brief_path.write_text(json.dumps(brief))
        self.cli('run', self.packet, '--project', ROOT, '--config', self.config('openai', 2), expected=2)
        self.assertEqual(self.server.requests, [])

    def test_12_comparison_preserves_unknowns_and_does_not_claim_fidelity(self):
        single, _, _ = self.generate()
        staged, _, _ = self.generate('staged')
        rows = [json.loads(line) for line in self.cli('compare', single, staged).stdout.splitlines()]
        self.assertEqual([r['generation_calls'] for r in rows], [1, 4])
        self.assertEqual([r['input_tokens_known'] for r in rows], [120, 480])
        self.assertTrue(all(r['fidelity'] == 'human_assessment_required' for r in rows))


if __name__ == '__main__':
    unittest.main(verbosity=2)

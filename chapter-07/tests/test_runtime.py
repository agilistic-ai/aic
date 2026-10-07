"""Actual LangChain providers and agent; scripted HTTP replies, not live inference."""
from contextlib import contextmanager
from functools import partial
from http.server import BaseHTTPRequestHandler, SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json, os, sqlite3, subprocess, sys, tempfile, threading, unittest

ROOT=Path(__file__).resolve().parents[1]
class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*args): pass
class ModelHandler(BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def do_POST(self):
        body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        self.server.requests.append(body)
        messages=[m for m in body['messages'] if m['role']=='tool']
        stage=len(messages)
        if stage==0: name,args='search',{'query':'Riverside Saturday hire'}
        elif stage==1: name,args='fetch',{'source_id':'venue'}
        elif stage==2: name,args='fetch',{'source_id':'offer'}
        else:
            record=json.loads(messages[-1]['content'])
            name='Brief'
            args={'status':'supported','findings':[{'text':'Published three-hour Saturday price.', 'evidence':[{'observation_id':record['id'],'quote':record['text'] if not self.server.bad else 'invented quotation'}]}],'explanation':'Two fixture pages were inspected.'}
        if self.path=='/v1/chat/completions':
            result={'id':'chatcmpl-fixture','object':'chat.completion','created':1,'model':body['model'],'choices':[{'index':0,'message':{'role':'assistant','content':None,'tool_calls':[{'id':f'call_{stage}','type':'function','function':{'name':name,'arguments':json.dumps(args)}}]},'finish_reason':'tool_calls'}],'usage':{'prompt_tokens':120,'completion_tokens':90,'total_tokens':210}}
        else:
            result={'model':body['model'],'created_at':'2026-10-03T00:00:00Z','message':{'role':'assistant','content':'','tool_calls':[{'function':{'name':name,'arguments':args}}]},'done':True,'done_reason':'stop','prompt_eval_count':120,'eval_count':90}
        data=(json.dumps(result)+'\n').encode()
        self.send_response(200); self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)

@contextmanager
def server(handler,port=0):
    http=ThreadingHTTPServer(('127.0.0.1',port),handler); http.daemon_threads=True
    http.requests=[];http.bad=False
    thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
    try: yield http
    finally: http.shutdown();http.server_close();thread.join()

class RuntimeTests(unittest.TestCase):
    def cli(self,env,*args,ok=True):
        p=subprocess.run([str(Path(sys.executable).with_name('research')),*map(str,args)],cwd=ROOT,env=env,capture_output=True,text=True,timeout=45)
        self.assertEqual(p.returncode,0 if ok else 2,p.stdout+p.stderr)
        return [json.loads(line) for line in p.stdout.splitlines()]

    def test_actual_agent_both_provider_integrations_and_monitoring(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);site=root/'site';site.mkdir()
            def pages(price):
                for name in ('venue','offer'):
                    (site/f'{name}.html').write_text(f'<body data-ready="true">Saturday morning hire: USD {price}.00 for three hours. Cleaning is included.</body>')
            pages(80)
            with server(partial(Quiet,directory=str(site)),8765),server(ModelHandler) as http:
                url=f'http://127.0.0.1:{http.server_port}'
                env={**os.environ,'AIC_API_KEY':'smoke-only','AIC_OPENAI_BASE_URL':url+'/v1','AIC_OLLAMA_HOST':url,'NO_PROXY':'127.0.0.1','LANGSMITH_TRACING':'false'}
                db=root/'watch.sqlite';paths=[]
                for provider in ('openai','ollama'):
                    cfg=ROOT/('config.toml' if provider=='openai' else 'configs/ollama.toml')
                    out=self.cli(env,'run','What is the published Saturday price?','--config',cfg,'--output',root/'runs','--watch',db)
                    self.assertIsNone(out[1]['event']);path=Path(out[0]['brief']);paths.append(path)
                    job=json.loads(path.read_text());self.assertEqual(len(job['observations']),2)
                    self.assertEqual(job['tool_calls'],3);self.assertEqual(len(job['usage']),4)
                    self.assertEqual(job['recipe']['effective_model']['provider'],provider)
                pages(70)
                out=self.cli(env,'run','What is the price?','--output',root/'runs','--watch',db)
                self.assertEqual(out[1]['event']['previous_cents'],8000)
                self.assertEqual(out[1]['event']['current_cents'],7000)
                self.assertIsNone(self.cli(env,'watch',out[0]['brief'],'--database',db)[0]['event'])
                for _ in range(2): self.cli(env,'export','--database',db,'--output',root/'alerts')
                self.assertEqual(len(list((root/'alerts').glob('*.json'))),1)
                http.bad=True
                self.cli(env,'run','What is the price?','--output',root/'rejected','--watch',db,ok=False)
                self.assertFalse((root/'rejected').exists())
                with sqlite3.connect(db) as sql:
                    self.assertEqual(sql.execute('SELECT price FROM watches').fetchone()[0],7000)
                    self.assertEqual(sql.execute('SELECT COUNT(*) FROM outbox').fetchone()[0],1)
                self.assertEqual(len(http.requests),16)
                self.cli(env,'run','question','--mode','live',ok=False)

if __name__=='__main__':unittest.main()

class BrowserSmoke(unittest.TestCase):
    @unittest.skipUnless(os.environ.get('AIC_BROWSER_SMOKE')=='1',
                         'Set AIC_BROWSER_SMOKE=1 on a host with installed sandboxed Chromium.')
    def test_real_browser_exposes_dynamic_offer(self):
        from ai_cookbook.research_tools import Sources
        from ai_cookbook.research_run import FIXTURE_CATALOG
        with server(partial(Quiet,directory=str(ROOT/'examples/research/site')),8765):
            sources=Sources(FIXTURE_CATALOG)
            self.assertNotIn('USD 80.00',sources.read('offer')['text'])
            observed=sources.read('offer',rendered=True)
            self.assertIn('USD 80.00',observed['text'])
            self.assertEqual(observed['method'],'render')

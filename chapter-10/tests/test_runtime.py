# Copyright (c) 2026, Agilistic AI LLC, All Rights Reserved
# SPDX-License-Identifier: MIT
#
# Provided without warranty. Use at your own risk.
# See LICENSE.txt and DISCLAIMER.md in this project for terms.

"""Real Uvicorn HTTP API, worker subprocesses, provider SDKs, checkpoints and SQLite."""
import hashlib,json,os,socket,sqlite3,subprocess,sys,tempfile,time,unittest
from pathlib import Path
from contextlib import contextmanager
from unittest.mock import patch
import httpx
from sdk_fixture import serving,packet
ROOT=Path(__file__).resolve().parents[1]

class RuntimeTests(unittest.TestCase):
    def cli(self,home,env,*args,ok=True):
        p=subprocess.run([str(Path(sys.executable).with_name('desk')),'--home',str(home),*map(str,args)],cwd=ROOT,env=env,capture_output=True,text=True,timeout=40)
        self.assertEqual(p.returncode,0 if ok else 2,p.stdout+p.stderr)
        return [json.loads(x) for x in p.stdout.splitlines() if x.startswith('{')]

    @contextmanager
    def api(self,home,env):
        with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        log=tempfile.TemporaryFile()
        p=subprocess.Popen([str(Path(sys.executable).with_name('desk')),'--home',str(home),'serve','--port',str(port)],cwd=ROOT,env=env,stdout=log,stderr=log)
        url=f'http://127.0.0.1:{port}'
        try:
            with httpx.Client(base_url=url,trust_env=False,timeout=5) as client:
                deadline=time.monotonic()+15
                while True:
                    try:
                        if client.get('/openapi.json').status_code==200:break
                    except httpx.TransportError:pass
                    if p.poll() is not None or time.monotonic()>deadline:
                        log.seek(0);self.fail(log.read().decode())
                    time.sleep(.05)
                yield client,url
        finally:
            p.terminate()
            try:p.wait(timeout=5)
            except subprocess.TimeoutExpired:p.kill();p.wait()
            log.close()

    def test_complete_service_cli_restart_approval_permissions_and_backup(self):
        state={'fail':False}
        def reply(path,body):
            if state['fail']:return {'_http_error':True}
            data=packet(path,body)
            if 'observations' in data:
                return {'action':'list_slots' if not data['observations'] else 'propose','day':'2026-11-07' if not data['observations'] else None,'slot_id':'s1' if data['observations'] else None,'message':''}
            self.assertNotIn('Willow Hall',json.dumps(data))
            if 'missing' in data['question'].lower() or not data['passages']:
                return {'status':'missing','claims':[],'question':None}
            p=next((p for p in data['passages'] if p['doc_id']=='november'),data['passages'][0])
            return {'status':'answered','claims':[{'text':'The accessible toilet is unavailable.','evidence':[{'passage_id':p['id'],'quote':p['text']}]}],'question':None}
        with tempfile.TemporaryDirectory() as d,serving(reply) as (server,env):
            base=Path(d);home=base/'desk';self.cli(home,env,'init','--project',ROOT)
            self.assertEqual(len(server.requests),0)
            with self.api(home,env) as (client,url):
                member={'Authorization':'Bearer '+(home/'member.token').read_text().strip()}
                reader={'Authorization':'Bearer '+(home/'reader.token').read_text().strip()}
                body={'request_key':'a'*32,'kind':'booking','text':'Morning assessment 2026-11-07 UTC'}
                self.assertIn(client.post('/jobs',json=body).status_code,(401,403))
                self.assertEqual(client.post('/jobs',json=body,headers=reader).status_code,403)
                submitted=self.cli(home,env,'request','booking',body['text'],'--request-key',body['request_key'],'--url',url)
                key=submitted[-1]['id'];self.assertEqual(client.post('/jobs',json=body,headers=member).json()['id'],key)
                self.assertEqual(client.post('/jobs',json={**body,'text':'different'},headers=member).status_code,400)
                self.assertEqual(client.get('/jobs/'+key,headers=reader).status_code,404)
                self.cli(home,env,'worker','--once')
                pending=self.cli(home,env,'status',key,'--url',url)[0]
                self.assertEqual(pending['state'],'needs_approval');fingerprint=pending['result']['fingerprint']
                self.assertEqual(client.post(f'/jobs/{key}/approve',headers=member,json={'fingerprint':'0'*64}).status_code,400)
                self.cli(home,env,'approve',key,'--fingerprint',fingerprint,'--url',url)
                self.cli(home,env,'approve',key,'--fingerprint',fingerprint,'--url',url)
                with sqlite3.connect(home/'state/bookings.sqlite') as db:
                    self.assertEqual(db.execute('SELECT COUNT(*) FROM approvals').fetchone()[0],1)
                    db.execute('UPDATE approvals SET expires=0')
                # Three supervisor invocations: failed execution, bounded retry, unverified.
                for _ in range(3):self.cli(home,env,'worker','--once')
                uncertain=client.get('/jobs/'+key,headers=member).json();self.assertEqual(uncertain['state'],'unverified')
                self.assertEqual(uncertain['result']['fingerprint'],fingerprint)
                self.assertNotIn('approval_token',json.dumps(uncertain))
                self.cli(home,env,'approve',key,'--fingerprint',fingerprint,'--url',url)
                self.cli(home,env,'worker','--once')
                completed=client.get('/jobs/'+key,headers=member).json();self.assertEqual(completed['state'],'complete')
                receipt=completed['result'];self.assertEqual(receipt['request_id'],key)
                self.cli(home,env,'approve',key,'--fingerprint',fingerprint,'--url',url)
                with sqlite3.connect(home/'state/bookings.sqlite') as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM bookings').fetchone()[0],1)
                answers=[]
                for n,question in enumerate(('November accessible toilet','November missing fact')):
                    response=client.post('/jobs',headers=member,json={'request_key':str(n+1)*32,'kind':'answer','text':question})
                    self.assertEqual(response.status_code,200);answer_id=response.json()['id'];answers.append(answer_id)
                    self.cli(home,env,'worker','--once');answer=client.get('/jobs/'+answer_id,headers=member).json()
                    self.assertEqual(answer['state'],'complete');self.assertEqual(answer['result']['status'],'answered' if n==0 else 'missing')
                auth=json.loads((home/'auth.json').read_text());auth['actors']['member']['groups']=[];(home/'auth.json').write_text(json.dumps(auth))
                self.assertEqual(client.get('/jobs/'+answers[0],headers=member).json()['state'],'refresh_required')
                auth['actors']['member']['groups']=['members'];(home/'auth.json').write_text(json.dumps(auth))
                state['fail']=True
                response=client.post('/jobs',headers=member,json={'request_key':'f'*32,'kind':'answer','text':'November toilet'});failure=response.json()['id']
                for _ in range(3):self.cli(home,env,'worker','--once')
                self.assertEqual(client.get('/jobs/'+failure,headers=member).json()['state'],'unverified')
                usage=[json.loads(x) for x in (home/'state/usage.jsonl').read_text().splitlines()]
                self.assertTrue(any(x['status']=='failed' and x['usage'] is None for x in usage))
                self.assertTrue(any(x['status']=='completed' and x['usage']['input_tokens']==120 for x in usage))
                self.assertNotIn('Morning assessment',json.dumps(usage))
                del auth['actors']['member'];(home/'auth.json').write_text(json.dumps(auth))
                self.assertEqual(client.get('/jobs/'+key,headers=member).status_code,403)
            # API stopped; each once-worker and its child have exited.
            backup=base/'backup';self.cli(home,env,'backup',backup,'--maintenance-confirmed')
            restored=base/'restored';out=self.cli(home,env,'restore',backup,restored)[0];self.assertFalse(out['actions_resumed'])
            with sqlite3.connect(restored/'bookings.sqlite') as db:
                self.assertEqual(json.loads(db.execute('SELECT receipt FROM bookings WHERE request_id=?',(key,)).fetchone()[0]),receipt)
            self.assertTrue((restored/'sources/catalog.json').exists())
            (backup/'knowledge/index.json').write_text('{}')
            self.cli(home,env,'restore',backup,base/'badrestore',ok=False);self.assertFalse((base/'badrestore').exists())
            (home/'config.toml').write_text((home/'config.toml').read_text().replace('30','20'))
            self.cli(home,env,'worker','--once',ok=False)

    def test_actual_graph_recovery_after_commit_before_checkpoint(self):
        from ai_cookbook.booking_store import BookingStore
        from ai_cookbook.booking_action import grant,fingerprint
        from ai_cookbook.booking_graph import build_graph
        from ai_cookbook import booking_graph
        from ai_cookbook.desk_handle import handle
        from langgraph.checkpoint.sqlite import SqliteSaver
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);store=BookingStore(root/'bookings.sqlite',{'member'})
            key='e'*64;proposal={'slot_id':'s1','start_utc':'2026-11-07T10:00:00+00:00','version':1}
            cfg={'configurable':{'thread_id':key}}
            job={'id':key,'actor':'member','kind':'booking','phase':'execute'}
            with SqliteSaver.from_conn_string(str(root/'graph.sqlite')) as saver:
                graph=build_graph(store,saver);graph.invoke({'request_id':key,'actor':'member','proposal':proposal},cfg)
                job['approval_token']=grant(store,'member',key,proposal,fingerprint('member',key,proposal))
                original=booking_graph.commit
                def lose(*args,**kw):original(*args,**kw);raise ConnectionError('response lost after commit')
                with patch.object(booking_graph,'commit',side_effect=lose):
                    with self.assertRaises(ConnectionError):handle(job,store=store,graph=graph,embed=None,current_groups=lambda a:[])
            prior=store.lookup(key,'member')
            with SqliteSaver.from_conn_string(str(root/'graph.sqlite')) as saver:
                result=handle(job,store=store,graph=build_graph(store,saver),embed=None,current_groups=lambda a:[])
            self.assertEqual(result,prior)
            with store.connection() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM bookings').fetchone()[0],1)

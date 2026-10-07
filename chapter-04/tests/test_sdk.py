import json,os,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path
from sdk_fixture import serving,packet
ROOT=Path(__file__).resolve().parents[1]

class SDKTests(unittest.TestCase):
 def test_complete_index_query_search_match_and_failure(self):
  with tempfile.TemporaryDirectory() as temp:
   folder=Path(temp);collection=folder/'collection';shutil.copytree(ROOT/'examples/knowledge',collection)
   index=folder/'index.json';state={'bad':False}
   def reply(path,body):
    if path=='/api/tags': return {'models':[{'name':'nomic-embed-text:v1.5','model':'nomic-embed-text:v1.5','digest':'fixture-weights','size':1,'modified_at':'2026-10-03T00:00:00Z'}]}
    if path=='/api/embed':
     self.assertFalse(body['truncate']);return {'model':body['model'],'embeddings':[[1.,float('November' in t),float('May' in t)] for t in body['input']]}
    data=packet(path,body);self.assertNotIn('Willow Hall',json.dumps(data))
    schema=body['text']['format']['schema'] if path=='/v1/responses' else body['format']
    if 'ids' in schema['properties']: return {'ids':[p['id'] for p in data['passages'][:4]]}
    p=next((p for p in data['passages'] if p['doc_id']=='november'),data['passages'][0])
    return {'status':'answered','claims':[{'text':'The entrance is step-free, but the accessible toilet is unavailable.','evidence':[{'passage_id':p['id'],'quote':'invented' if state['bad'] else p['text']}]}],'question':None}
   with serving(reply) as (server,env):
    def cli(*args,expected=0):
     result=subprocess.run([sys.executable,'-m','ai_cookbook.knowledge_run',*map(str,args),'--index',str(index)],env=env,cwd=folder,text=True,capture_output=True,timeout=15)
     self.assertEqual(result.returncode,expected,result.stderr);return json.loads(result.stdout) if result.stdout else None
    self.assertEqual(cli('index',collection)['failures'],{})
    for provider in ('openai','ollama'):
     config=folder/'config.toml';config.write_text(f'[model]\nprovider="{provider}"\nname="fixture-model"\ntimeout_seconds=2\n')
     answer=cli('ask',collection,'November access','--config',config,'--rerank')
     self.assertEqual(answer['status'],'answered');self.assertTrue(answer['sources'])
     state['bad']=True;cli('ask',collection,'November access','--config',config,expected=2);state['bad']=False
    before=len(server.requests)
    found=cli('search',collection,'November','--method','keyword')
    self.assertTrue(found);self.assertEqual(len(server.requests),before)
    needs=folder/'needs.json';needs.write_text('{"minimum_capacity":20,"step_free":true,"accessible_toilet":true}')
    self.assertEqual(cli('match',collection,'cozy room','--method','keyword','--needs',needs,'--config',config)['status'],'missing')
    catalog=json.loads((collection/'catalog.json').read_text());catalog['november'].update(kind='venue',facts={'capacity':24,'step_free':True,'accessible_toilet':True})
    (collection/'catalog.json').write_text(json.dumps(catalog))
    self.assertEqual(cli('match',collection,'November','--method','keyword','--needs',needs,'--config',config)['status'],'answered')
    (collection/'november.txt').write_text('Changed without reindexing.')
    found=cli('search',collection,'November','--method','keyword');self.assertNotIn('november',{p['doc_id'] for p in found})
    before=len(server.requests);cli('index',collection,'--method','keyword');self.assertEqual(len(server.requests),before)

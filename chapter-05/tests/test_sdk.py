import json,shutil,sqlite3,subprocess,sys,tempfile,unittest,hashlib
from pathlib import Path
from sdk_fixture import serving
ROOT=Path(__file__).resolve().parents[1]
class SDKTests(unittest.TestCase):
 def test_complete_report_both_sdks_and_failures(self):
  with tempfile.TemporaryDirectory() as temp:
   folder=Path(temp);db=folder/'snapshot.sqlite';config=folder/'config.toml';state={'mode':'ready'}
   sql=(ROOT/'examples/reporting/remaining.sql').read_text()
   def reply(path,body):
    mode=state['mode']
    if mode=='malformed': return '{'
    return {'status':'ready' if mode in ('ready','deny') else mode,'interpretation':'Upcoming confirmed seats only.',
     'sql':('DELETE FROM bookings' if mode=='deny' else sql) if mode in ('ready','deny') else None,
     'parameters':['2026-11-01'] if mode=='ready' else [],'question':'How many seats?' if mode=='clarify' else None}
   with serving(reply) as (server,env):
    def cli(*args,expected=0):
     result=subprocess.run([sys.executable,'-m','ai_cookbook.reporting_cli',*map(str,args)],cwd=folder,env=env,text=True,capture_output=True,timeout=20)
     self.assertEqual(result.returncode,expected,result.stderr);self.assertNotIn('Traceback',result.stderr)
     return json.loads(result.stdout) if result.stdout else None
    cli('init','--database',db,'--schema',ROOT/'examples/reporting/schema.sql');cli('init','--database',db,expected=2)
    original=hashlib.sha256(db.read_bytes()).hexdigest()
    for provider in ('openai','ollama'):
     config.write_text(f'[model]\nprovider="{provider}"\nname="fixture"\ntimeout_seconds=2\n')
     args=('ask','Remaining places','--database',db,'--as-of','2026-11-01','--project',ROOT,'--config',config,'--output',folder/'reports')
     job=cli(*args);self.assertEqual(job['result']['rows'],[['november','November repair workshop',15],['december','December repair workshop',12]])
     self.assertIn('<svg',Path(job['chart']).read_text());self.assertTrue(Path(job['report']).exists())
     self.assertIn('127.0.0.1',job['configuration']['effective_model']['base_url'])
     for mode in ('clarify','unsupported'):
      state['mode']=mode;job=cli(*args);self.assertNotIn('result',job);self.assertTrue(Path(job['report']).exists())
     for mode in ('deny','malformed'): state['mode']=mode;cli(*args,expected=2)
     state['mode']='ready'
    self.assertEqual(hashlib.sha256(db.read_bytes()).hexdigest(),original)
    before=len(server.requests);cli('ask','Remaining','--database',db,'--as-of','20261101','--project',ROOT,'--config',config,expected=2);self.assertEqual(len(server.requests),before)
 def test_private_data_and_units(self):
  from ai_cookbook.reporting_data import initialize
  from ai_cookbook.reporting_execute import execute
  from ai_cookbook.reporting_plan import QueryPlan
  with tempfile.TemporaryDirectory() as tmp:
   db=Path(tmp)/'report.sqlite';initialize(db,ROOT/'examples/reporting/schema.sql')
   with sqlite3.connect(db) as connection: connection.execute('CREATE TABLE secrets(secret TEXT)')
   def plan(sql):return QueryPlan(status='ready',interpretation='test',sql=sql,parameters=[],question=None)
   with self.assertRaises(sqlite3.DatabaseError):execute(db,plan('SELECT * FROM secrets'))
   result=execute(db,plan("SELECT SUM(contribution_cents),SUM(contribution_cents IS NULL) FROM bookings WHERE workshop_id='november' AND status='confirmed'"))
   self.assertEqual(result['rows'],[[500,1]])

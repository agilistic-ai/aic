"""The Docker executable is a controlled process fixture, never an isolation substitute."""
import json,os,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
IMAGE='sha256:'+'a'*64

class CliTests(unittest.TestCase):
    def test_installed_cli_patch_and_failed_scope(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d);bin=base/'bin';bin.mkdir();fake=bin/'docker'
            fake.write_text('''#!'''+sys.executable+'''
import json,os,sys,subprocess
from pathlib import Path
args=sys.argv[1:]
if args[0]=='image': print(args[-1]);raise SystemExit(0)
if args[0]=='rm':raise SystemExit(0)
with open(os.environ['DOCKER_CALLS'],'a') as f:f.write(json.dumps(args)+'\\n')
mount=args[args.index('--mount')+1];workspace=Path(mount.split('src=',1)[1].split(',dst=',1)[0])
if '--entrypoint' not in args:
 p=workspace/'capacity.py';p.write_text(p.read_text().replace('sum(1 for booking','sum(booking["seats"] for booking'))
 if os.environ.get('BAD_SCOPE'): (workspace/'test_capacity.py').write_text('pass\\n')
 print('Controlled authored edit; no agent or Docker runtime was used.')
else:
 # Only the trusted fixture generated above is executed by this test.
 code=Path(os.environ['HARNESS']).read_text().replace('"/candidate/capacity.py"',repr(str(workspace/'capacity.py')))
 result=subprocess.run([sys.executable,'-I','-B','-c',code,args[-1]],capture_output=True)
 sys.stdout.buffer.write(result.stdout);sys.stderr.buffer.write(result.stderr);raise SystemExit(result.returncode)
''');fake.chmod(0o755)
            env={**os.environ,'PATH':str(bin)+os.pathsep+os.environ['PATH'],'DOCKER_CALLS':str(base/'calls.jsonl'),'HARNESS':str(ROOT/'examples/coding/harness/candidate_call.py')}
            seed=ROOT/'examples/coding/seed'
            command=[str(Path(sys.executable).with_name('coding')),'--seed',str(seed),'--image',IMAGE,'--output',str(base/'jobs')]
            result=subprocess.run(command,env=env,capture_output=True,text=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stderr)
            folder=Path(json.loads(result.stdout)['job']);manifest=json.loads((folder/'manifest.json').read_text())
            self.assertTrue(manifest['accepted_by_tests']);self.assertEqual(manifest['merge_status'],'awaiting_human_review')
            self.assertEqual(len(json.loads((folder/'acceptance.json').read_text())['cases']),8)
            applied=subprocess.run(['git','apply','--check',str(folder/'proposal.patch')],cwd=seed,capture_output=True,text=True)
            self.assertEqual(applied.returncode,0,applied.stderr)
            commands=[json.loads(line) for line in (base/'calls.jsonl').read_text().splitlines()]
            self.assertEqual(len(commands),9)
            for cmd in commands:
                self.assertIn('--read-only',cmd);self.assertIn('--cap-drop',cmd)
            self.assertEqual(commands[0][commands[0].index('--network')+1],'aic-coding')
            self.assertTrue(all(c[c.index('--network')+1]=='none' for c in commands[1:]))
            result=subprocess.run(command,env={**env,'BAD_SCOPE':'1'},capture_output=True,text=True,timeout=30)
            self.assertEqual(result.returncode,1,result.stderr)
            failed=Path(json.loads(result.stdout)['job']);self.assertFalse((failed/'proposal.patch').exists())
            self.assertFalse(json.loads((failed/'manifest.json').read_text())['accepted_by_tests'])

    def test_missing_docker_and_invalid_image_fail_without_launch(self):
        with tempfile.TemporaryDirectory() as d:
            command=[str(Path(sys.executable).with_name('coding')),'--seed',str(ROOT/'examples/coding/seed'),'--output',str(Path(d)/'jobs')]
            for image in ('latest',IMAGE):
                result=subprocess.run(command+['--image',image],env={**os.environ,'PATH':d},capture_output=True,text=True)
                self.assertEqual(result.returncode,2,result.stderr)
                self.assertFalse((Path(d)/'jobs').exists())

    def test_descendant_cannot_hold_output_pipe_past_timeout(self):
        from ai_cookbook.coding_run import bounded_command
        import time
        start=time.monotonic()
        result=bounded_command([sys.executable,'-c','import subprocess; subprocess.Popen(["'+sys.executable+'","-c","import time; time.sleep(30)"])'],seconds=.2)
        self.assertEqual(result['stop_reason'],'timeout');self.assertLess(time.monotonic()-start,3)

class ContainerSmoke(unittest.TestCase):
    @unittest.skipUnless(os.environ.get('AIC_CODING_SMOKE_IMAGE'),
                         'Set AIC_CODING_SMOKE_IMAGE with Docker and the isolated model service ready.')
    def test_real_coding_worker_and_acceptance(self):
        with tempfile.TemporaryDirectory() as d:
            result=subprocess.run([str(Path(sys.executable).with_name('coding')),
                '--seed',str(ROOT/'examples/coding/seed'),'--image',os.environ['AIC_CODING_SMOKE_IMAGE'],
                '--output',d],capture_output=True,text=True,timeout=720)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            folder=Path(json.loads(result.stdout)['job'])
            self.assertTrue((folder/'proposal.patch').is_file())

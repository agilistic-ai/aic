# Copyright (c) 2026, Agilistic AI LLC, All Rights Reserved
# SPDX-License-Identifier: MIT
#
# Provided without warranty. Use at your own risk.
# See LICENSE.txt and DISCLAIMER.md in this project for terms.

import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
blocks=[('', (ROOT/'examples/coding/seed/capacity.py').read_text()),
        ('', (ROOT/'examples/coding/seed/test_capacity.py').read_text())]+[('', '')]*6+[('', (ROOT/'examples/coding/harness/candidate_call.py').read_text())]
from ai_cookbook.coding_snapshot import snapshot
from ai_cookbook import coding_run as runner,coding_accept as accept,coding_package as packaging
ORIGINAL_RUN=subprocess.run
IMAGE='sha256:'+'a'*64

class Checks(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.base=Path(self.temp.name);self.seed=self.base/'seed';self.seed.mkdir()
  (self.seed/'capacity.py').write_text(blocks[0][1]);(self.seed/'test_capacity.py').write_text(blocks[1][1]);(self.seed/'README.md').write_text('Run python -B -m unittest -v.\n')
  self.baseline=snapshot(self.seed)
 def fix(self,folder):
  p=folder/'capacity.py';p.write_text(p.read_text().replace('sum(1 for booking','sum(booking["seats"] for booking'))
 def controlled_worker(self,command,**kwargs):
  # Execute only our authored fixture and harness locally, not an agent-produced candidate.
  mount=next(x for x in command if x.startswith('type=bind,'));folder=Path(mount.split('src=',1)[1].split(',dst=',1)[0])
  code=blocks[8][1].replace('"/candidate/capacity.py"',repr(str(folder/'capacity.py')))
  return runner.bounded_command([sys.executable,'-I','-B','-c',code,command[-1]],seconds=3,max_bytes=4096)
 def test_01_seed_failure_and_fix(self):
  result=runner.bounded_command([sys.executable,'-B','-m','unittest','discover','-s',str(self.seed)],seconds=5)
  self.assertEqual(result['returncode'],1);self.assertIn('test_group_booking',result['output'])
  self.fix(self.seed)
  result=runner.bounded_command([sys.executable,'-B','-m','unittest','discover','-s',str(self.seed)],seconds=5)
  self.assertEqual(result['returncode'],0)
 def test_02_all_authoritative_cases(self):
  self.fix(self.seed)
  with patch.object(accept,'bounded_command',side_effect=self.controlled_worker),patch.object(accept.subprocess,'run',return_value=subprocess.CompletedProcess([],0,b'',b'')):
   result=accept.assess(self.seed,IMAGE,self.baseline)
  self.assertTrue(result['passed']);self.assertEqual(len(result['cases']),8)
 def test_03_scope_changes(self):
  self.fix(self.seed);(self.seed/'test_capacity.py').write_text('pass\n')
  with self.assertRaises(ValueError):accept.scope_check(self.baseline,snapshot(self.seed))
 def test_04_added_file(self):
  self.fix(self.seed);(self.seed/'sitecustomize.py').write_text('pass\n')
  with self.assertRaises(ValueError):accept.scope_check(self.baseline,snapshot(self.seed))
 def test_05_symlink_and_size(self):
  (self.seed/'outside').symlink_to(self.base)
  with self.assertRaises(ValueError):snapshot(self.seed)
  (self.seed/'outside').unlink();(self.seed/'large').write_bytes(b'x'*100001)
  with self.assertRaises(ValueError):snapshot(self.seed)
 def test_06_timeout_and_output_bound(self):
  result=runner.bounded_command([sys.executable,'-c','import time; time.sleep(5)'],seconds=.1)
  self.assertEqual(result['stop_reason'],'timeout')
  result=runner.bounded_command([sys.executable,'-c','print("x"*20000)'],seconds=2,max_bytes=100)
  self.assertEqual(result['stop_reason'],'output_limit');self.assertEqual(len(result['output']),100)
 def test_07_zero_exit_without_result_fails(self):
  self.fix(self.seed)
  with patch.object(accept,'bounded_command',return_value={'returncode':0,'stop_reason':None,'output':''}),patch.object(accept.subprocess,'run',return_value=subprocess.CompletedProcess([],0,b'',b'')):
   result=accept.assess(self.seed,IMAGE,self.baseline)
  self.assertFalse(result['passed'])
 def test_08_package_and_patch_application(self):
  def fake_launch(workspace,image,evidence):
   self.fix(workspace);evidence.mkdir();result={'returncode':0,'stop_reason':None,'output':'fixture'};(evidence/'agent-run.json').write_text(json.dumps(result));return result
  with patch.object(packaging,'launch',side_effect=fake_launch),patch.object(accept,'bounded_command',side_effect=self.controlled_worker),patch.object(accept.subprocess,'run',return_value=subprocess.CompletedProcess([],0,b'',b'')):
   folder=packaging.maintain(self.seed,IMAGE,self.base/'jobs')
  manifest=json.loads((folder/'manifest.json').read_text());self.assertTrue(manifest['accepted_by_tests'])
  fresh=self.base/'fresh';shutil.copytree(self.seed,fresh)
  applied=ORIGINAL_RUN(['git','apply','--check',str(folder/'proposal.patch')],cwd=fresh,capture_output=True,text=True)
  self.assertEqual(applied.returncode,0,applied.stderr)
  self.assertEqual(manifest['merge_status'],'awaiting_human_review')

if __name__=='__main__':unittest.main(verbosity=2)

# Copyright (c) 2026, Agilistic AI LLC, All Rights Reserved
# SPDX-License-Identifier: MIT
#
# Provided without warranty. Use at your own risk.
# See LICENSE.txt and DISCLAIMER.md in this project for terms.

import json,sqlite3,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command
from ai_cookbook.booking_store import BookingStore
from ai_cookbook import booking_graph
from ai_cookbook.booking_action import grant,fingerprint,commit
from sdk_fixture import serving,packet
ROOT=Path(__file__).resolve().parents[1]
P={'slot_id':'s1','start_utc':'2026-11-07T10:00:00+00:00','version':1}

class RuntimeTests(unittest.TestCase):
 def cli(self,folder,env,*args,expected=0):
  result=subprocess.run([sys.executable,'-m','ai_cookbook.booking_run',*map(str,args),'--directory',str(folder)],env=env,cwd=folder.parent,text=True,capture_output=True,timeout=30)
  self.assertEqual(result.returncode,expected,result.stderr);self.assertNotIn('Traceback',result.stderr)
  return json.loads(result.stdout) if result.stdout else None
 def test_installed_cli_real_mcp_langgraph_both_sdks(self):
  def reply(path,body):
   data=packet(path,body)
   self.assertNotIn('approval_token',json.dumps(data))
   if data['observations']:return {'action':'propose','day':None,'slot_id':'s1','message':''}
   return {'action':'list_slots','day':'2026-11-07','slot_id':None,'message':''}
  with tempfile.TemporaryDirectory() as tmp,serving(reply) as (server,env):
   root=Path(tmp)
   for provider in ('openai','ollama'):
    folder=root/provider;config=root/(provider+'.toml');config.write_text(f'[model]\nprovider="{provider}"\nname="fixture"\ntimeout_seconds=2\n')
    result=self.cli(folder,env,'start','November 7, 2026 before 11:00 UTC','--config',config)
    rid=result['request_id'];digest=result['result']['fingerprint']
    with sqlite3.connect(folder/'service.sqlite') as db:self.assertEqual(db.execute('SELECT count(*) FROM bookings').fetchone()[0],0)
    shown=self.cli(folder,env,'show',rid);self.assertEqual(shown['trace'][0]['slots'][0]['id'],'s1')
    self.cli(folder,env,'approve',rid,'--fingerprint','wrong',expected=2)
    confirmation=self.cli(folder,env,'approve',rid,'--fingerprint',digest)['result']
    self.assertEqual(confirmation['status'],'confirmed')
    self.assertEqual(self.cli(folder,env,'recover',rid)['result'],confirmation)
    self.cli(folder,env,'approve',rid,'--fingerprint',digest,expected=2)
    with sqlite3.connect(folder/'service.sqlite') as db:self.assertEqual(db.execute('SELECT count(*) FROM bookings').fetchone()[0],1)
   self.assertEqual(len(server.requests),4)
 def test_actual_checkpoint_recovery_after_commit_response_loss(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);store=BookingStore(root/'service.sqlite',{'demo-member'});checkpoint=root/'checkpoints.sqlite'
   cfg={'configurable':{'thread_id':'lost'}};token=grant(store,'demo-member','lost',P,fingerprint('demo-member','lost',P))
   with SqliteSaver.from_conn_string(str(checkpoint)) as saver:
    graph=booking_graph.build_graph(store,saver);graph.invoke({'request_id':'lost','actor':'demo-member','proposal':P},cfg)
    def lost(*args,**kwargs):commit(*args,**kwargs);raise ConnectionError('response lost')
    with patch.object(booking_graph,'commit',side_effect=lost):
     with self.assertRaises(ConnectionError):graph.invoke(Command(resume=token),cfg)
   with SqliteSaver.from_conn_string(str(checkpoint)) as saver:
    result=booking_graph.build_graph(store,saver).invoke(None,cfg)
    self.assertEqual(result['confirmation']['status'],'confirmed')
   with store.connection() as db:self.assertEqual(db.execute('SELECT count(*) FROM bookings').fetchone()[0],1)
 def test_renew_expired_approval_in_failed_perform_node(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);folder=root/'job';folder.mkdir();store=BookingStore(folder/'service.sqlite',{'demo-member'})
   digest=fingerprint('demo-member','expired',P);token=grant(store,'demo-member','expired',P,digest,now=0)
   cfg={'configurable':{'thread_id':'expired'}}
   with SqliteSaver.from_conn_string(str(folder/'checkpoints.sqlite')) as saver:
    graph=booking_graph.build_graph(store,saver);graph.invoke({'request_id':'expired','actor':'demo-member','proposal':P},cfg)
    with self.assertRaises(PermissionError):graph.invoke(Command(resume=token),cfg)
   import os
   result=self.cli(folder,os.environ,'approve','expired','--fingerprint',digest)
   self.assertEqual(result['result']['status'],'confirmed')

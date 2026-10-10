# Copyright (c) 2026, Agilistic AI LLC, All Rights Reserved
# SPDX-License-Identifier: MIT
#
# Provided without warranty. Use at your own risk.
# See LICENSE.txt and DISCLAIMER.md in this project for terms.

import contextlib
import fcntl
import hashlib
import importlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch

from langgraph.types import Command
from fastapi import HTTPException
from ai_cookbook import desk_queue as q,desk_auth as auth,desk_handle as handler,desk_worker as worker,desk_backup as backup
from ai_cookbook.booking_store import BookingStore
from ai_cookbook.booking_action import grant,commit,fingerprint
from ai_cookbook.booking_verify import verify

class FakeGraph:
 """Controlled durable graph fixture; does not stand in for SDK verification."""
 def __init__(self,path,store):
  self.path=path;self.store=store;self.crash=False
  with sqlite3.connect(path) as db:db.execute('CREATE TABLE IF NOT EXISTS graph (id TEXT PRIMARY KEY,state TEXT,stage TEXT)')
 def load(self,config):
  rid=config['configurable']['thread_id']
  with sqlite3.connect(self.path) as db:row=db.execute('SELECT state,stage FROM graph WHERE id=?',(rid,)).fetchone()
  return ({},None) if row is None else (json.loads(row[0]),row[1])
 def save(self,state,stage):
  with sqlite3.connect(self.path) as db:db.execute('INSERT OR REPLACE INTO graph VALUES (?,?,?)',(state['request_id'],json.dumps(state),stage))
 def get_state(self,config):
  state,stage=self.load(config);return SimpleNamespace(values=state,tasks=[SimpleNamespace(interrupts=[1])] if stage=='approval' else [])
 def invoke(self,data,config):
  state,stage=self.load(config)
  if isinstance(data,dict):self.save(data,'approval');return
  if isinstance(data,Command):state['approval_token']=data.resume;stage='perform';self.save(state,stage)
  if stage=='perform':
   receipt=commit(self.store,state['actor'],state['request_id'],state['proposal'],state['approval_token'])
   if self.crash:self.crash=False;raise RuntimeError('Controlled post-commit interruption')
   state['receipt']=receipt;self.save(state,'done')
  return state

class Checks(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.base=Path(self.temp.name)
  self.authfile=self.base/'auth.json';self.limits=self.base/'limits.json';self.state=self.base/'state';self.state.mkdir();self.sources=self.base/'sources';self.sources.mkdir()
  self.directory={'tokens':{hashlib.sha256(b'alice-token').hexdigest():'alice'},'actors':{'alice':{'groups':['members'],'can_book':True},'bob':{'groups':['members'],'can_book':False}}}
  self.write_auth();self.limits.write_text(json.dumps({'daily_microusd':100,'ceiling_microusd':{'answer':10,'booking':40}}))
  env=patch.dict(os.environ,{'AIC_AUTH_FILE':str(self.authfile),'AIC_LIMITS_FILE':str(self.limits),'AIC_RELEASE_ID':'fixture-release'});env.start();self.addCleanup(env.stop)
  self.queue=q.Queue(self.state/'jobs.sqlite');self.store=BookingStore(self.state/'bookings.sqlite',auth.CurrentMembers())
  self.graph=FakeGraph(self.state/'checkpoints.sqlite',self.store)
  (self.state/'knowledge').mkdir();(self.state/'knowledge/index.json').write_text('{}');(self.sources/'notice.txt').write_text('November source')
  for name,value in [('STATE',self.state),('SOURCES',self.sources)]:
   p=patch.object(worker,name,value);p.start();self.addCleanup(p.stop)
  self.proposal={'slot_id':'s1','start_utc':'2026-11-07T10:00:00+00:00','version':1}
 def write_auth(self):self.authfile.write_text(json.dumps(self.directory))
 def request(self,kind='booking',key='a'*32,text='Morning on 2026-11-07'):
  return {'kind':kind,'request_key':key,'text':text}
 def load_api(self):
  with patch.object(q,'Queue',return_value=self.queue),patch('ai_cookbook.booking_store.BookingStore',return_value=self.store):
   if 'ai_cookbook.desk_api' in sys.modules:return importlib.reload(sys.modules['ai_cookbook.desk_api'])
   return importlib.import_module('ai_cookbook.desk_api')
 def pending(self):
  key=self.queue.submit('alice',self.request());job=self.queue.take()
  with patch.object(handler,'propose_booking',return_value={'status':'proposal','proposal':self.proposal,'trace':[]}):
   result=handler.handle(job,store=self.store,graph=self.graph,embed=None,current_groups=lambda a:auth.permissions(a)['groups'])
  self.queue.edit(key,'alice',lambda j:j.update(state='needs_approval',result=result))
  return key,result
 def test_01_stable_identity_and_changed_body(self):
  key=self.queue.submit('alice',self.request());self.assertEqual(key,self.queue.submit('alice',self.request()))
  with self.assertRaises(ValueError):self.queue.submit('alice',self.request(text='Different intent'))
  with self.queue.connection() as db:self.assertEqual(db.execute('SELECT amount FROM spending').fetchone()[0],40)
 def test_02_concurrent_duplicate_submission(self):
  from concurrent.futures import ThreadPoolExecutor
  with ThreadPoolExecutor(4) as pool:keys=list(pool.map(lambda _:self.queue.submit('alice',self.request()),range(4)))
  self.assertEqual(len(set(keys)),1)
  with self.queue.connection() as db:self.assertEqual(db.execute('SELECT amount FROM spending').fetchone()[0],40)
 def test_03_allowance_rejection_is_atomic(self):
  self.queue.submit('alice',self.request());self.queue.submit('alice',self.request(key='b'*32))
  with self.assertRaises(RuntimeError):self.queue.submit('alice',self.request(key='c'*32))
  self.assertEqual(self.queue.submit('alice',self.request()),hashlib.sha256(('alice\0'+'a'*32).encode()).hexdigest())
  with self.queue.connection() as db:self.assertEqual(db.execute('SELECT count(*) FROM jobs').fetchone()[0],2)
 def test_04_ownership_and_revocation(self):
  key=self.queue.submit('alice',self.request())
  with self.assertRaises(KeyError):self.queue.edit(key,'bob',lambda j:None)
  self.assertEqual(auth.authenticate('alice-token'),'alice');self.assertIn('alice',auth.CurrentMembers())
  self.directory['actors']['alice']['can_book']=False;self.write_auth();self.assertNotIn('alice',auth.CurrentMembers())
  del self.directory['actors']['alice'];self.write_auth()
  with self.assertRaises(PermissionError):auth.authenticate('alice-token')
 def test_05_bounded_restart_state(self):
  key=self.queue.submit('alice',self.request())
  self.assertEqual(self.queue.take()['tries'],1);self.assertEqual(self.queue.take()['tries'],2);self.assertIsNone(self.queue.take())
  self.assertEqual(self.queue.edit(key,'alice',lambda j:None)['state'],'unverified')
 def test_06_postcommit_recovery_keeps_receipt(self):
  key,pending=self.pending();token=grant(self.store,'alice',key,self.proposal,pending['fingerprint'])
  job=self.queue.edit(key,'alice',lambda j:j.update(phase='execute',approval_token=token))
  self.graph.crash=True
  with self.assertRaises(RuntimeError):handler.handle(job,store=self.store,graph=self.graph,embed=None,current_groups=lambda a:[])
  original=self.store.lookup(key,'alice');reopened=FakeGraph(self.graph.path,self.store)
  result=handler.handle(job,store=self.store,graph=reopened,embed=None,current_groups=lambda a:[])
  self.assertEqual(result,original)
  with self.store.connection() as db:self.assertEqual(db.execute('SELECT count(*) FROM bookings').fetchone()[0],1)
 def test_07_exact_and_repeated_approval(self):
  key,pending=self.pending();api=self.load_api()
  with self.assertRaises(ValueError):api.approve(key,api.Approval(fingerprint='0'*64),'alice')
  approval=api.Approval(fingerprint=pending['fingerprint']);api.approve(key,approval,'alice');first=self.queue.edit(key,'alice',lambda j:None)['approval_token']
  api.approve(key,approval,'alice');self.assertEqual(self.queue.edit(key,'alice',lambda j:None)['approval_token'],first)
  with self.store.connection() as db:self.assertEqual(db.execute('SELECT count(*) FROM approvals').fetchone()[0],1)
  self.queue.edit(key,'alice',lambda j:j.update(state='complete',result={'status':'confirmed'}));api.approve(key,approval,'alice')
 def test_08_saved_answer_withheld_after_change(self):
  key=self.queue.submit('alice',self.request(kind='answer'));stamp=worker.access_stamp('alice')
  self.queue.edit(key,'alice',lambda j:j.update(state='complete',result={'status':'answered','text':'November source'},access_stamp=stamp));api=self.load_api()
  self.assertEqual(api.read(key,'alice')['state'],'complete')
  self.directory['actors']['alice']['groups']=[];self.write_auth();self.assertEqual(api.read(key,'alice')['state'],'refresh_required')
  self.directory['actors']['alice']['groups']=['members'];self.write_auth();(self.sources/'notice.txt').write_text('Changed source');self.assertIsNone(api.read(key,'alice')['result'])
 def test_09_worker_booking_skips_embeddings_and_binds_release(self):
  key=self.queue.submit('alice',self.request())
  with patch.object(worker,'Queue',return_value=self.queue),patch.object(worker,'build_graph',return_value=self.graph),patch.object(worker,'handle',return_value={'status':'clarify'}),patch.object(worker,'Embeddings',side_effect=AssertionError('Not needed')):
   worker.perform(key)
  self.assertEqual(self.queue.edit(key,'alice',lambda j:None)['state'],'complete')
  with patch.dict(os.environ,{'AIC_RELEASE_ID':'changed'}),patch.object(worker,'Queue',return_value=self.queue):
   with self.assertRaises(RuntimeError):worker.perform(key)
 def test_10_backup_is_recoverable_and_exclusive(self):
  key,pending=self.pending();token=grant(self.store,'alice',key,self.proposal,pending['fingerprint']);receipt=commit(self.store,'alice',key,self.proposal,token)
  dest=self.base/'backup';backup.backup(self.state,dest,'fixture-release');manifest=json.loads((dest/'backup.json').read_text())
  for path,digest in manifest['files'].items():self.assertEqual(hashlib.sha256((dest/path).read_bytes()).hexdigest(),digest)
  restored=BookingStore(dest/'bookings.sqlite',auth.CurrentMembers());self.assertEqual(verify(restored,'alice',key,self.proposal),receipt)
  with (self.state/'worker.lock').open('a') as lock:
   fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
   with self.assertRaises(BlockingIOError):backup.backup(self.state,self.base/'blocked','fixture-release')
 def test_11_child_retains_worker_lock(self):
  lock=(self.state/'worker.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  child=subprocess.Popen([sys.executable,'-c','import sys,time;print("ready",flush=True);time.sleep(20)'],pass_fds=(lock.fileno(),),stdout=subprocess.PIPE,text=True)
  try:
   self.assertEqual(child.stdout.readline().strip(),'ready');lock.close()
   with (self.state/'worker.lock').open('a') as candidate:
    with self.assertRaises(BlockingIOError):fcntl.flock(candidate,fcntl.LOCK_EX|fcntl.LOCK_NB)
  finally:
   child.kill();child.wait();child.stdout.close();lock.close()
 def test_12_api_shapes_and_private_token(self):
  api=self.load_api()
  from pydantic import ValidationError
  with self.assertRaises(ValidationError):api.Request(**self.request(),actor='bob')
  with self.assertRaises(ValidationError):api.Request(**{**self.request(),'kind':'shell'})
  with self.assertRaises(HTTPException):api.submit(api.Request(**self.request(text='x'*999+'😀')),'alice')
  key,pending=self.pending();api.approve(key,api.Approval(fingerprint=pending['fingerprint']),'alice')
  self.assertNotIn('approval_token',json.dumps(api.read(key,'alice')))

if __name__=='__main__':unittest.main(verbosity=2)

# Copyright (c) 2026, Agilistic AI LLC, All Rights Reserved
# SPDX-License-Identifier: MIT
#
# Provided without warranty. Use at your own risk.
# See LICENSE.txt and DISCLAIMER.md in this project for terms.

import copy
import json
from pathlib import Path
import re
import sqlite3
import sys
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from functools import partial

site=Path(__file__).resolve().parents[1]/"examples/research/site"
from ai_cookbook.research_tools import Sources
from ai_cookbook.research_brief import Brief,validate_brief
from ai_cookbook.research_watch import observed_price,record_observation
from ai_cookbook.research_notify import export_notifications

class Quiet(SimpleHTTPRequestHandler):
 def log_message(self,*args):pass

CAT={k:{'title':k+' Riverside Hall','url':f'http://127.0.0.1:8765/{k}.html','ready_selector':"body[data-ready='true']"} for k in ('venue','offer')}

def job(run='a',amount='80.00',minute=0):
 text=f'Saturday morning hire: USD {amount} for three hours. Cleaning is included.'
 archive={k:dict(id=k,source_id=k,text=text,observed_at=f'2026-11-01T12:{minute:02}:00+00:00') for k in ('venue','offer')}
 brief=dict(status='supported',findings=[dict(text='Published three-hour hire price.',evidence=[dict(observation_id='venue',quote=text)])],explanation='Applicable published offer.')
 return dict(run_id=run,brief=brief,observations=archive)

class Checks(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.http=ThreadingHTTPServer(('127.0.0.1',8765),partial(Quiet,directory=str(site)))
  cls.thread=threading.Thread(target=cls.http.serve_forever,daemon=True);cls.thread.start()
 @classmethod
 def tearDownClass(cls):cls.http.shutdown();cls.http.server_close();cls.thread.join()
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.db=Path(self.temp.name)/'watch.sqlite'
 def test_01_static_fetch_and_dynamic_gap(self):
  src=Sources(CAT);venue=src.read('venue');offer=src.read('offer')
  self.assertIn('USD 80.00',venue['text']);self.assertNotIn('USD 80.00',offer['text']);self.assertIn('Loading',offer['text'])
  self.assertIn(venue['id'],src.archive)
 def test_02_source_scope_and_budget(self):
  with self.assertRaises(ValueError):Sources({'bad':{'url':'http://example.com/x'}})
  with self.assertRaises(ValueError):Sources(CAT,mode='live')
  src=Sources(CAT)
  with self.assertRaises(KeyError):src.read('unknown')
  search=src.tools()[0]
  for _ in range(5):search('Riverside')
  with self.assertRaises(RuntimeError):search('Riverside')
 def test_03_bad_citations(self):
  item=job();item['brief']['findings'][0]['evidence'][0]['quote']='invented'
  with self.assertRaises(ValueError):validate_brief(Brief.model_validate(item['brief']),item['observations'])
 def test_04_semantic_error_still_requires_review(self):
  item=job();item['brief']['findings'][0]['text']='Hourly rate is 80 dollars.'
  self.assertEqual(validate_brief(Brief.model_validate(item['brief']),item['observations']).status,'supported')
 def test_05_baseline_and_wording_change_suppress_alerts(self):
  self.assertIsNone(record_observation(self.db,job()))
  item=job('b',minute=1)
  for r in item['observations'].values():r['text']='BIG SALE! '+r['text']
  self.assertIsNone(record_observation(self.db,item))
 def test_06_changed_price_and_duplicate_run(self):
  record_observation(self.db,job());item=job('b','70.00',1)
  event=record_observation(self.db,item);self.assertEqual((event['previous_cents'],event['current_cents']),(8000,7000))
  self.assertIsNone(record_observation(self.db,item));self.assertIsNone(record_observation(self.db,job('c','70.00',2)))
  with sqlite3.connect(self.db) as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM outbox').fetchone()[0],1)
 def test_07_conflict_and_missing_coverage(self):
  for kind in ('conflict','missing'):
   item=job()
   if kind=='conflict':item['observations']['offer']['text']=item['observations']['offer']['text'].replace('80.00','70.00')
   else:del item['observations']['offer']
   with self.assertRaises(ValueError):record_observation(self.db,item)
 def test_08_late_run_does_not_regress_baseline(self):
  record_observation(self.db,job('new','70.00',2));self.assertIsNone(record_observation(self.db,job('old','80.00',1)))
  with sqlite3.connect(self.db) as db:self.assertEqual(db.execute('SELECT price FROM watches').fetchone()[0],7000)
 def test_09_notification_recovery(self):
  record_observation(self.db,job());event=record_observation(self.db,job('b','70.00',1));folder=Path(self.temp.name)/'notifications'
  export_notifications(self.db,folder)
  with sqlite3.connect(self.db) as db:db.execute('UPDATE outbox SET delivered=0')
  export_notifications(self.db,folder)
  self.assertEqual(len(list(folder.glob('*.json'))),1)
  self.assertEqual(json.loads(next(folder.glob('*.json')).read_text()),event)
 def test_10_changed_scope_is_rejected(self):
  item=job()
  for r in item['observations'].values():r['text']=r['text'].replace('for three hours','per hour')
  item['brief']['findings'][0]['evidence'][0]['quote']=item['observations']['venue']['text']
  with self.assertRaises(ValueError):observed_price(item)

if __name__=='__main__':unittest.main(verbosity=2)

import json
from pathlib import Path
import re
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from ai_cookbook.booking_store import BookingStore
from ai_cookbook import booking_action as action, booking_loop as loop
from ai_cookbook.booking_verify import verify

class Checks(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
  self.members={'alice','bob'};self.store=BookingStore(Path(self.temp.name)/'service.sqlite',self.members)
  self.p={'slot_id':'s1','start_utc':'2026-11-07T10:00:00+00:00','version':1}
 def grant(self,actor='alice',rid='job1',p=None,now=100):
  p=p or self.p;return action.grant(self.store,actor,rid,p,action.fingerprint(actor,rid,p),now=now)
 def commit(self,token,actor='alice',rid='job1',p=None,now=101):return action.commit(self.store,actor,rid,p or self.p,token,now=now)
 def test_01_complete_verified_booking(self):
  receipt=self.commit(self.grant());self.assertEqual(verify(self.store,'alice','job1',self.p),receipt)
  self.assertEqual([r['id'] for r in self.store.list_slots('2026-11-07')],['s2'])
 def test_02_recovery_after_lost_response_and_expiry(self):
  token=self.grant();receipt=self.commit(token)
  reopened=BookingStore(self.store.path,self.members)
  again=action.commit(reopened,'alice','job1',self.p,token,now=9999)
  self.assertEqual(receipt,again)
  with reopened.connection() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM bookings').fetchone()[0],1)
 def test_03_expired_before_write(self):
  with self.assertRaises(PermissionError):self.commit(self.grant(),now=700)
  self.assertIsNone(self.store.lookup('job1','alice'))
 def test_04_changed_arguments(self):
  token=self.grant();changed={**self.p,'start_utc':'2026-11-07T10:30:00+00:00'}
  with self.assertRaises(PermissionError):self.commit(token,p=changed)
 def test_05_request_collision(self):
  token=self.grant();self.commit(token)
  with self.assertRaises(ValueError):self.commit(token,p={**self.p,'slot_id':'s2'})
 def test_06_wrong_actor_and_private_readback(self):
  token=self.grant()
  with self.assertRaises(PermissionError):self.commit(token,actor='bob')
  self.commit(token);self.assertIsNone(self.store.lookup('job1','bob'))
 def test_07_revocation(self):
  token=self.grant();self.members.remove('alice')
  with self.assertRaises(PermissionError):self.commit(token)
 def test_08_stale_slot(self):
  token=self.grant();other=self.grant('bob','job2')
  self.commit(other,'bob','job2')
  with self.assertRaises(ValueError):self.commit(token)
 def test_09_unverified_outcome(self):
  with self.assertRaises(RuntimeError):verify(self.store,'alice','job1',self.p)
 def test_10_two_competing_transactions(self):
  from concurrent.futures import ThreadPoolExecutor
  tokens=[self.grant('alice','a'),self.grant('bob','b')]
  def attempt(pair):
   actor,rid,token=pair
   try:return action.commit(self.store,actor,rid,self.p,token,now=101)['status']
   except ValueError:return 'stale'
  with ThreadPoolExecutor(2) as pool:results=list(pool.map(attempt,[('alice','a',tokens[0]),('bob','b',tokens[1])]))
  self.assertCountEqual(results,['confirmed','stale'])
 def test_11_loop_observed_slot(self):
  decisions=[dict(action='list_slots',day='2026-11-07',slot_id=None,message=''),dict(action='propose',day=None,slot_id='s1',message='')]
  with patch.object(loop,'generate',side_effect=[SimpleNamespace(text=json.dumps(d)) for d in decisions]):
   result=loop.propose_booking('Before 11 UTC',self.store.list_slots)
  self.assertEqual(result['proposal'],self.p);self.assertIsNone(self.store.lookup('job1','alice'))
 def test_12_loop_invented_slot_and_budget(self):
  fake=SimpleNamespace(text=json.dumps(dict(action='propose',day=None,slot_id='s99',message='')))
  with patch.object(loop,'generate',return_value=fake):
   with self.assertRaises(ValueError):loop.propose_booking('q',self.store.list_slots)
  fake=SimpleNamespace(text=json.dumps(dict(action='list_slots',day='2026-11-07',slot_id=None,message='')))
  with patch.object(loop,'generate',return_value=fake) as generated:
   result=loop.propose_booking('q',self.store.list_slots)
  self.assertEqual(result['status'],'stop');self.assertEqual(generated.call_count,4)

if __name__=='__main__':unittest.main(verbosity=2)

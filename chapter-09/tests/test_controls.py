import hashlib
import json
from pathlib import Path
import re
import sys
import tempfile
from types import ModuleType,SimpleNamespace
import unittest
from unittest.mock import patch
import wave
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
from ai_cookbook import media_prepare as prep,media_extract as visual,media_voice as voice,media_review as review,media_run as pipeline

def candidate(field='item_model',value='NR-18',source='visual',quote='NR-18',uncertain=False):
 return visual.Candidate(field=field,value=value,source=source,page=1 if source=='visual' else None,quote=quote,uncertain=uncertain)

class Checks(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.base=Path(self.temp.name)
  self.image=self.base/'input.png';Image.new('RGB',(100,60),'white').save(self.image)
  self.audio=self.base/'input.wav'
  with wave.open(str(self.audio),'wb') as f:f.setparams((1,2,16000,0,'NONE','not compressed'));f.writeframes(b'\x00\x00'*1600)
  self.record=prep.prepare(self.image,self.audio,consent=True,output=self.base/'runs')
 def test_01_manifest_integrity(self):
  self.assertEqual(self.record['visual']['pages'],1)
  for name in ('visual','audio'):self.assertEqual(hashlib.sha256(visual.checked_bytes(self.record[name])).hexdigest(),self.record[name]['sha256'])
 def test_02_consent_and_invalid_audio_cleanup(self):
  with self.assertRaises(PermissionError):prep.prepare(self.image,self.audio,consent=False,output=self.base/'denied')
  self.assertFalse((self.base/'denied').exists())
  bad=self.base/'bad.wav';bad.write_bytes(b'not audio')
  with self.assertRaises(Exception):prep.prepare(self.image,bad,consent=True,output=self.base/'failed')
  self.assertEqual(list((self.base/'failed').iterdir()),[])
 def test_03_changed_media(self):
  Path(self.record['visual']['path']).write_bytes(b'changed')
  with self.assertRaises(ValueError):visual.checked_bytes(self.record['visual'])
 def test_04_visual_provenance(self):
  draft=visual.Draft(candidates=[candidate()],questions=[])
  with patch.object(visual,'media_json',return_value=draft.model_dump_json()):self.assertEqual(visual.extract_visual(self.record['visual']),draft)
  draft.candidates[0].page=2
  with patch.object(visual,'media_json',return_value=draft.model_dump_json()):
   with self.assertRaises(ValueError):visual.extract_visual(self.record['visual'])
 def test_05_voice_quotes(self):
  draft=visual.Draft(candidates=[candidate(source='voice')],questions=[])
  with patch.object(voice,'generate',return_value=SimpleNamespace(text=draft.model_dump_json())):
   self.assertEqual(voice.extract_voice('The model is NR-18.').candidates[0].value,'NR-18')
   with self.assertRaises(ValueError):voice.extract_voice('The model is something else.')
 def test_06_conflict_and_uncertainty(self):
  a=visual.Draft(candidates=[candidate()],questions=[]);b=visual.Draft(candidates=[candidate(source='voice',value='NR-B8',quote='NR-B8')],questions=[])
  _,job=voice.reconcile(self.record,a,b,'NR-B8');self.assertIsNone(job['fields']['item_model']);self.assertIn('item_model',job['unresolved'])
  b.candidates[0]=candidate(source='voice',uncertain=True)
  _,job=voice.reconcile(self.record,a,b,'NR-18');self.assertIn('item_model',job['unresolved'])
 def test_07_review_and_stale_draft(self):
  a=visual.Draft(candidates=[candidate()],questions=[]);b=visual.Draft(candidates=[candidate(field='problem',value='Stopped heating',source='voice',quote='stopped heating')],questions=[])
  path,job=voice.reconcile(self.record,a,b,'It stopped heating.')
  digest=hashlib.sha256(path.read_bytes()).hexdigest()
  dest,result=review.approve_draft(path,{'item_model':'NR-B8','problem':'Stopped heating','preferred_time':None},expected_digest=digest,reviewer='reviewer',questions_resolved=True)
  self.assertIn('item_model',result['corrections']);self.assertEqual(result['state'],'reviewed_intake');self.assertTrue(dest.exists())
  path.write_text(path.read_text()+' ')
  with self.assertRaises(ValueError):review.approve_draft(path,job['fields'],expected_digest=digest,reviewer='reviewer',questions_resolved=True)
 def test_08_joint_preserves_provenance(self):
  draft=visual.Draft(candidates=[candidate(),candidate(source='voice',value='NR-B8',quote='NR-B8')],questions=['Which marking is correct?'])
  with patch.object(pipeline,'media_json',return_value=draft.model_dump_json()):a,b=pipeline.joint_read(self.record['visual'],'NR-B8')
  self.assertEqual(len(a.candidates),1);self.assertEqual(len(b.candidates),1)
  with patch.object(pipeline,'media_json',return_value=draft.model_dump_json()):
   with self.assertRaises(ValueError):pipeline.joint_read(self.record['visual'],'NR-18')
 def test_09_staged_pipeline_and_failed_stage(self):
  a=visual.Draft(candidates=[candidate()],questions=[]);b=visual.Draft(candidates=[candidate(field='problem',value='Stopped heating',source='voice',quote='stopped heating')],questions=[])
  with patch.object(pipeline,'transcribe',return_value='It stopped heating.'),patch.object(pipeline,'extract_visual',return_value=a),patch.object(pipeline,'extract_voice',return_value=b):
   path,job=pipeline.intake(self.image,self.audio,consent=True,output=self.base/'pipeline',settings=__import__("ai_cookbook.settings",fromlist=["load_settings"]).load_settings(ROOT/"config.toml"))
  self.assertEqual(job['fields']['problem'],'Stopped heating');self.assertEqual(job['state'],'needs_review');self.assertTrue(path.is_file())
  with patch.object(pipeline,'extract_visual',return_value=a), patch.object(pipeline,'transcribe',side_effect=RuntimeError('controlled failure')):
   with self.assertRaises(RuntimeError):pipeline.intake(self.image,self.audio,consent=True,output=self.base/'failure',settings=__import__("ai_cookbook.settings",fromlist=["load_settings"]).load_settings(ROOT/"config.toml"))
  failure=next((self.base/'failure').glob('*/failure.json'));self.assertEqual(json.loads(failure.read_text())['stage'],'transcription')
 def test_10_speech_keeps_text_path_independent(self):
  self_audio=self.audio
  class Response:
   def __enter__(self):return self
   def __exit__(self,*args):pass
   def stream_to_file(self,path):Path(path).write_bytes(self_audio.read_bytes())
  client=SimpleNamespace(audio=SimpleNamespace(speech=SimpleNamespace(with_streaming_response=SimpleNamespace(create=lambda **kw:Response()))))
  target=self.base/'confirmation.wav'
  with patch.object(review,'media_client',return_value=__import__('contextlib').nullcontext(client)):review.speak_confirmation('Recorded request.',target)
  self.assertTrue(target.exists());self.assertFalse(target.with_suffix('.partial').exists())

if __name__=='__main__':unittest.main(verbosity=2)

import contextlib
import copy
import io
import json
import math
from pathlib import Path
import shutil
import sys
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).parent
from ai_cookbook import knowledge_sources as sources
from ai_cookbook import knowledge_index as indexing
from ai_cookbook import knowledge_retrieve as retrieval
from ai_cookbook import knowledge_answer as answering
from ai_cookbook import knowledge_service as service
from ai_cookbook import knowledge_matching as matching
from ai_cookbook import knowledge_run as runner
from ai_cookbook.evaluation import evidence_coverage
from ai_cookbook.model import ModelReply
from pydantic import ValidationError


class FakeEmbeddings:
    key = 'controlled-embeddings-v1'

    def __init__(self):
        self.calls = []
        self.on_query = None

    def encode(self, texts, *, query=False):
        self.calls.append((list(texts), query))
        if query and self.on_query:
            self.on_query()
        result = []
        for text in texts:
            lower = text.lower()
            values = [1.0, float('november' in lower or '2026-11-07' in lower),
                      float('may' in lower or '2026-05-16' in lower),
                      float('backup' in lower)]
            norm = math.sqrt(sum(v*v for v in values))
            result.append([v/norm for v in values])
        return result


def reply(payload):
    return ModelReply(json.dumps(payload), 'controlled-model', 12, 8)


def missing_reply(*args, **kwargs):
    return reply({'status': 'missing', 'claims': [], 'question': None})


def cited_reply(passage, *, quote=None, text=None, status='answered'):
    quote = passage['text'].splitlines()[0] if quote is None else quote
    return {'status': status, 'claims': [{'text': text or quote,
            'evidence': [{'passage_id': passage['id'], 'quote': quote}]}], 'question': None}


class ChapterChecks(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / 'collection'
        shutil.copytree(ROOT.parent / 'examples/knowledge', self.root)
        self.catalog = sources.load_catalog(self.root)
        self.embed = FakeEmbeddings()
        self.index = indexing.build_index(self.root, self.catalog, self.embed)
        self.member = lambda: frozenset({'members'})
        self.organizer = lambda: frozenset({'organizers'})

    def save_catalog(self):
        (self.root / 'catalog.json').write_text(json.dumps(self.catalog))

    def available(self, groups=None):
        return service.eligible(self.root, self.index, groups or {'members'})

    def ask(self, question='Is the November workshop accessible?', **kwargs):
        return service.answer_question(self.root, self.index, question,
                                       kwargs.pop('get_groups', self.member), self.embed, **kwargs)

    def test_01_extraction_guards(self):
        digest, units = sources.extract(self.root, self.catalog['november'])
        self.assertEqual(len(digest), 64)
        self.assertEqual(units[0][0], 'text')
        outside = self.root.parent / 'outside.txt'
        outside.write_text('secret')
        for path, error in [('../outside.txt', ValueError), ('bad.bin', ValueError),
                            ('empty.txt', ValueError), ('invalid.txt', UnicodeDecodeError)]:
            if path == 'bad.bin': (self.root / path).write_bytes(b'data')
            if path == 'empty.txt': (self.root / path).write_text('  ')
            if path == 'invalid.txt': (self.root / path).write_bytes(b'\xff')
            with self.assertRaises(error): sources.extract(self.root, {'path': path})

    def test_02_empty_pdf_is_held(self):
        from pypdf import PdfWriter
        writer = PdfWriter()
        writer.add_blank_page(width=200, height=200)
        with (self.root / 'blank.pdf').open('wb') as handle: writer.write(handle)
        with self.assertRaisesRegex(ValueError, 'Empty extraction'):
            sources.extract(self.root, {'path': 'blank.pdf'})

    def test_03_chunk_identity_overlap_and_failures(self):
        text = 'A'*580 + 'A qualification that crosses the first boundary.' + 'B'*700
        (self.root / 'long.txt').write_text(text)
        extra = {'version': '1', 'path': 'long.txt', 'title': 'Long', 'groups':['members']}
        built = indexing.build_index(self.root, {'long':extra, 'absent':{**extra,'path':'absent.txt'}}, self.embed)
        pieces = built['documents']['long']['passages']
        self.assertEqual(pieces[0]['text'], text[:600])
        self.assertEqual(pieces[1]['text'], text[520:1120])
        self.assertEqual(len({p['id'] for p in pieces}),len(pieces))
        self.assertEqual(built['documents']['absent']['passages'], [])
        self.assertEqual(built['documents']['absent']['error'], 'FileNotFoundError')

    def test_04_embedding_prefixes_normalization_and_drift(self):
        state = {'digest':'a', 'vectors':[[3.0,4.0]]}
        calls=[]
        client=SimpleNamespace(
            list=lambda: SimpleNamespace(models=[SimpleNamespace(model='nomic-embed-text:v1.5',digest=state['digest'])]),
            embed=lambda **kwargs: (calls.append(kwargs) or SimpleNamespace(embeddings=state['vectors'])))
        with patch.object(indexing,'Client',return_value=client): embed=indexing.Embeddings()
        self.assertEqual(embed.encode(['text']),[[.6,.8]])
        self.assertEqual(calls[-1]['input'],['search_document: text'])
        self.assertFalse(calls[-1]['truncate'])
        embed.encode(['question'],query=True)
        self.assertEqual(calls[-1]['input'],['search_query: question'])
        state['vectors']=[]
        with self.assertRaisesRegex(ValueError,'count mismatch'): embed.encode(['text'])
        state['vectors']=[[0.0,0.0]]
        with self.assertRaisesRegex(ValueError,'Invalid embedding'): embed.encode(['text'])
        state['digest']='b'
        with self.assertRaisesRegex(ValueError,'changed'): embed.encode(['text'])

    def test_05_retrieval_modes(self):
        candidates=self.available()
        for method in ('keyword','dense','hybrid'):
            found=retrieval.retrieve('November 2026-11-07',candidates,self.embed,method=method,limit=1)
            self.assertEqual(found[0]['doc_id'],'november')
        with self.assertRaisesRegex(ValueError,'Unknown'): retrieval.retrieve('x',candidates,self.embed,method='oops')
        candidates[0]['vector']=[1]
        with self.assertRaises(ValueError): retrieval.retrieve('November',candidates,self.embed)

    def test_06_member_model_inputs_exclude_restricted_data(self):
        captures=[]
        def fake(instructions,note,schema,**kwargs):
            packet=json.loads(note); captures.append(packet)
            self.assertNotIn('Willow',note)
            self.assertNotIn('Organizer contingency',note)
            self.assertTrue(all('vector' not in p for p in packet['passages']))
            if 'ids' in schema['properties']:
                return reply({'ids':[p['id'] for p in packet['passages']]})
            return missing_reply()
        with patch.object(answering,'generate',side_effect=fake):
            result=self.ask('What is the November backup venue?',rerank=True)
        self.assertEqual(len(captures),2)
        self.assertEqual(result['status'],'missing')
        self.assertEqual(result['sources'],[])

    def test_07_organizer_answer_has_traceable_source(self):
        def fake(instructions,note,schema,**kwargs):
            packet=json.loads(note)
            self.assertEqual({p['doc_id'] for p in packet['passages']},{'organizers'})
            return reply(cited_reply(packet['passages'][0]))
        with patch.object(answering,'generate',side_effect=fake):
            result=self.ask('What is the backup venue?',get_groups=self.organizer)
        self.assertEqual(result['status'],'answered')
        self.assertEqual(result['sources'][0]['title'],'Organizer contingency note')
        self.assertNotIn('vector',json.dumps(result))
        self.assertIn('Willow Hall',json.dumps(result))

    def test_08_revocation_during_retrieval_stops_first_model_stage(self):
        groups={'members'}
        self.embed.on_query=lambda: groups.clear()
        with patch.object(answering,'generate') as call:
            result=self.ask(get_groups=lambda:groups,rerank=True)
        self.assertEqual(result['status'],'missing')
        call.assert_not_called()

    def test_09_revocation_during_reranking_stops_composition(self):
        groups={'members'}
        def fake(instructions,note,schema,**kwargs):
            groups.clear()
            return reply({'ids':[p['id'] for p in json.loads(note)['passages']]})
        with patch.object(answering,'generate',side_effect=fake) as call:
            result=self.ask(get_groups=lambda:groups,rerank=True)
        self.assertEqual(result['status'],'missing')
        self.assertEqual(call.call_count,1)

    def test_10_revocation_or_edit_during_composition_withholds_result(self):
        for change in ('access','bytes'):
            with self.subTest(change=change):
                groups={'members'}
                original=(self.root/'november.txt').read_text()
                def fake(instructions,note,schema,**kwargs):
                    passage=next(p for p in json.loads(note)['passages'] if p['doc_id']=='november')
                    if change=='access': groups.clear()
                    else: (self.root/'november.txt').write_text(original+' Updated.')
                    return reply(cited_reply(passage))
                with patch.object(answering,'generate',side_effect=fake):
                    result=self.ask(get_groups=lambda:groups)
                self.assertEqual(result['status'],'missing')
                self.assertEqual(result['sources'],[])
                (self.root/'november.txt').write_text(original)

    def test_11_updates_deletion_and_atomic_replacement(self):
        (self.root/'november.txt').write_text('Updated content.')
        self.assertNotIn('november',{p['doc_id'] for p in self.available()})
        del self.catalog['may']; self.save_catalog()
        self.assertNotIn('may',{p['doc_id'] for p in self.available()})
        (self.root/'november.txt').write_text('')
        rebuilt=indexing.build_index(self.root,self.catalog,self.embed)
        self.assertEqual(rebuilt['documents']['november']['passages'],[])
        self.assertNotIn('may',rebuilt['documents'])
        path=self.root.parent/'runs'/'index.json'
        indexing.save_index(self.index,path)
        indexing.save_index(rebuilt,path)
        self.assertEqual(json.loads(path.read_text()),rebuilt)
        self.assertEqual([p.name for p in path.parent.iterdir()],['index.json'])

    def test_12_version_changes_and_model_namespaces(self):
        self.catalog['november']['version']='2'; self.save_catalog()
        self.assertNotIn('november',{p['doc_id'] for p in self.available()})
        self.index['embedding_key']='different-model'
        with self.assertRaisesRegex(ValueError,'rebuild'): self.ask()
        with patch.object(answering,'generate',side_effect=missing_reply):
            self.assertEqual(self.ask(method='keyword')['status'],'missing')

    def test_13_invalid_answers_are_rejected(self):
        passages=self.available(); source=passages[0]
        good=cited_reply(source)
        bad=copy.deepcopy(good); bad['claims'][0]['evidence'][0]['passage_id']='invented'
        wrong_quote=copy.deepcopy(good); wrong_quote['claims'][0]['evidence'][0]['quote']='invented words'
        no_evidence=copy.deepcopy(good); no_evidence['claims'][0]['evidence']=[]
        missing_with_claims=copy.deepcopy(good); missing_with_claims['status']='missing'
        cases=[bad,wrong_quote,no_evidence,missing_with_claims,
               {'status':'clarify','claims':[],'question':None},
               {'status':'answered','claims':[],'question':None},
               {'status':'missing','claims':[],'question':'unasked'},
               {**good,'extra':'forbidden'}]
        for payload in cases:
            with self.subTest(payload=payload):
                with patch.object(answering,'generate',return_value=reply(payload)):
                    with self.assertRaises(ValueError): answering.compose('q',passages)

    def test_14_traceability_does_not_prove_meaning(self):
        passages=self.available()
        may=next(p for p in passages if p['doc_id']=='may')
        payload=cited_reply(may,quote='The entrance and accessible toilet were available.',
                            text='The November accessible toilet is available.')
        with patch.object(answering,'generate',return_value=reply(payload)):
            answer=answering.compose('Is November accessible?',passages)
        self.assertEqual(answer.status,'answered')
        # Deliberately false meaning passes structural checks: semantic assessment is separate.

    def test_15_clarification_conflict_and_absence_shapes(self):
        with patch.object(answering,'generate') as call:
            self.assertEqual(answering.compose('q',[]).status,'missing'); call.assert_not_called()
        passages=self.available()
        payload={'status':'clarify','claims':[],'question':'Which workshop do you mean?'}
        with patch.object(answering,'generate',return_value=reply(payload)):
            self.assertEqual(answering.compose('q',passages).status,'clarify')
        payload=cited_reply(passages[0],status='conflict')
        payload['claims']+=cited_reply(passages[1])['claims']
        with patch.object(answering,'generate',return_value=reply(payload)):
            self.assertEqual(answering.compose('q',passages).status,'conflict')

    def test_16_reranking_rejects_unknown_duplicate_and_excess_ids(self):
        passages=self.available(); valid=passages[0]['id']
        for ids in (['unknown'],[valid,valid],[valid]*5):
            with patch.object(answering,'generate',return_value=reply({'ids':ids})):
                with self.assertRaisesRegex(ValueError,'Invalid reranking'):
                    answering.select('q',passages,rerank=True)
        with patch.object(answering,'generate',return_value=reply({'ids':[]})):
            self.assertEqual(answering.select('q',passages,rerank=True),[])

    def test_17_context_budget_preserves_whole_passages(self):
        passages=[{**self.available()[0],'id':str(i),'text':'é'*600} for i in range(20)]
        packed=answering.pack('q',passages)
        self.assertLess(len(packed),len(passages))
        self.assertLessEqual(len(json.dumps({'question':'q','passages':packed},ensure_ascii=False).encode()),8000)
        self.assertTrue(all(p['text']=='é'*600 and 'vector' not in p for p in packed))

    def test_18_matching_excludes_unknown_and_ineligible_venues(self):
        needs=matching.VenueNeeds(minimum_capacity=20,step_free=True,accessible_toilet=True)
        passage=self.available()[0]
        spec={**self.catalog[passage['doc_id']],'kind':'venue',
              'facts':{'capacity':24,'step_free':True,'accessible_toilet':None}}
        catalog={passage['doc_id']:spec}
        self.assertEqual(matching.venue_candidates([passage],catalog,needs),[])
        spec['facts']['accessible_toilet']=True
        self.assertEqual(matching.venue_candidates([passage],catalog,needs),[passage])
        for field,value in [('capacity',19),('capacity',True),('step_free',None),('accessible_toilet',False)]:
            candidate=copy.deepcopy(catalog); candidate[passage['doc_id']]['facts'][field]=value
            self.assertEqual(matching.venue_candidates([passage],candidate,needs),[])
        spec['version']='2'
        self.assertEqual(matching.venue_candidates([passage],catalog,needs),[])
        with self.assertRaises(ValidationError): matching.VenueNeeds(minimum_capacity=0,step_free=True,accessible_toilet=True)
        with self.assertRaises(ValidationError): matching.VenueNeeds(minimum_capacity=20,step_free='yes',accessible_toilet=True)

    def test_19_matching_variation_integration(self):
        self.catalog['november'].update(kind='venue',facts={'capacity':24,'step_free':True,'accessible_toilet':True})
        self.save_catalog()
        needs=matching.VenueNeeds(minimum_capacity=20,step_free=True,accessible_toilet=True)
        captured=[]
        def fake(instructions,note,schema,**kwargs):
            passages=json.loads(note)['passages']; captured.extend(passages)
            return reply(cited_reply(passages[0]))
        with patch.object(answering,'generate',side_effect=fake):
            result=service.match_venues(self.root,self.index,'Find a cozy room',self.member,self.embed,needs)
        self.assertEqual(result['status'],'answered')
        self.assertEqual({p['doc_id'] for p in captured},{'november'})

    def test_20_evidence_coverage(self):
        passages=self.available()
        required=[('november','The entrance is step-free'),('november','the accessible toilet is unavailable.')]
        self.assertEqual(evidence_coverage(passages,required),1)
        self.assertEqual(evidence_coverage(passages,[*required,('november','Unknown statement')]),2/3)
        self.assertIsNone(evidence_coverage(passages,[]))

    def test_22_request_bounds_and_no_access(self):
        for question in ('  ','é'*501):
            with self.assertRaises(ValueError): self.ask(question)
        with patch.object(answering,'generate') as call:
            result=self.ask(get_groups=lambda:frozenset())
        self.assertEqual(result['status'],'missing'); call.assert_not_called()


if __name__=='__main__':
    unittest.main(verbosity=2)

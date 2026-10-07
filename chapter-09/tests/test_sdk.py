"""Real OpenAI/Ollama adapters and CLI against scripted HTTP media endpoints."""
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
import base64,io,json,os,subprocess,sys,tempfile,threading,unittest,wave
from PIL import Image,ImageDraw
from pypdf import PdfWriter
from pypdf.generic import NameObject,DictionaryObject,DecodedStreamObject
ROOT=Path(__file__).resolve().parents[1]
TRANSCRIPT='I think it is NR-B8. It stopped heating yesterday. I prefer morning.'

def draft(source):
    if source=='visual':
        candidates=[dict(field='item_model',value='NR-18',source='visual',page=1,quote='NR-18',uncertain=False)]
    else:
        candidates=[dict(field=f,value=v,source='voice',page=None,quote=q,uncertain=u) for f,v,q,u in [
            ('item_model','NR-B8','I think it is NR-B8',True),
            ('problem','Stopped heating yesterday','stopped heating yesterday',False),
            ('preferred_time','morning','morning',False)]]
    return dict(candidates=candidates,questions=[])

def wav_bytes():
    out=io.BytesIO()
    with wave.open(out,'wb') as f:f.setparams((1,2,16000,0,'NONE','not compressed'));f.writeframes(b'\x00\x00'*1600)
    return out.getvalue()

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def do_POST(self):
        raw=self.rfile.read(int(self.headers['Content-Length']));self.server.requests.append((self.path,raw))
        if self.path=='/v1/audio/transcriptions':
            assert b'RIFF' in raw and b'WAVE' in raw and b'gpt-4o-mini-transcribe' in raw
            if self.server.fail=='transcription': self.send_response(503);self.end_headers();self.wfile.write(b'{}');return
            data=json.dumps({'text':TRANSCRIPT,'usage':{'type':'duration','seconds':.1}}).encode()
        elif self.path=='/v1/audio/speech':
            body=json.loads(raw);assert body['response_format']=='wav'
            if self.server.fail=='speech':self.send_response(503);self.end_headers();self.wfile.write(b'{}');return
            data=wav_bytes()
        else:
            body=json.loads(raw)
            instructions=body.get('instructions',body.get('messages',[{}])[0].get('content',''))
            selected='voice' if 'only from the transcript' in instructions else 'visual'
            result=draft(selected)
            if 'Prepare intake candidates from this visual source and transcript.' in instructions:
                result['candidates']+=draft('voice')['candidates']
            if self.server.fail=='quote':result['candidates'][0]['quote']='invented'
            if self.path=='/v1/responses':
                content=body['input'][0]['content']
                if isinstance(content,list):
                    media=content[1];payload=media.get('image_url',media.get('file_data'))
                    assert base64.b64decode(payload.split(',',1)[1])
                packet={'id':'resp_fixture','object':'response','created_at':1,'model':body['model'],'status':'completed','output':[{'type':'message','id':'msg_fixture','role':'assistant','status':'completed','content':[{'type':'output_text','text':json.dumps(result),'annotations':[]}]}],'usage':{'input_tokens':120,'output_tokens':90,'total_tokens':210}}
            else:
                packet={'model':body['model'],'created_at':'2026-10-03T00:00:00Z','message':{'role':'assistant','content':json.dumps(result)},'done':True,'done_reason':'stop','prompt_eval_count':120,'eval_count':90}
            data=json.dumps(packet).encode()
        self.send_response(200);self.send_header('Content-Type','audio/wav' if self.path.endswith('/speech') else 'application/json');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)

@contextmanager
def serving():
    http=ThreadingHTTPServer(('127.0.0.1',0),Handler);http.requests=[];http.fail=None
    t=threading.Thread(target=http.serve_forever,daemon=True);t.start();base=f'http://127.0.0.1:{http.server_port}'
    env={**os.environ,'AIC_API_KEY':'smoke-only','AIC_OPENAI_BASE_URL':base+'/v1','AIC_MEDIA_BASE_URL':base+'/v1','AIC_OLLAMA_HOST':base,'NO_PROXY':'127.0.0.1'}
    try:yield http,env
    finally:http.shutdown();http.server_close();t.join()

def text_pdf(path):
    writer=PdfWriter();page=writer.add_blank_page(width=200,height=200)
    font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
    page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):writer._add_object(font)})})
    stream=DecodedStreamObject();stream.set_data(b'BT /F1 12 Tf 20 100 Td (Model NR-18) Tj ET')
    page[NameObject('/Contents')]=writer._add_object(stream);writer.write(path)

class SdkTests(unittest.TestCase):
    def cli(self,env,*args,ok=True):
        p=subprocess.run([str(Path(sys.executable).with_name('media')),*map(str,args)],cwd=ROOT,env=env,capture_output=True,text=True,timeout=30)
        self.assertEqual(p.returncode,0 if ok else 2,p.stdout+p.stderr)
        return p.stdout
    def test_complete_staged_joint_pdf_review_and_speech(self):
        with tempfile.TemporaryDirectory() as d,serving() as (http,env):
            folder=Path(d);visual=folder/'label.png';im=Image.new('RGB',(180,60),'white');ImageDraw.Draw(im).text((10,10),'NR-18',fill='black');im.save(visual)
            audio=folder/'note.wav';audio.write_bytes(wav_bytes());pdf=folder/'label.pdf';text_pdf(pdf)
            scan=folder/'scan.pdf';writer=PdfWriter();writer.add_blank_page(width=200,height=200);writer.write(scan)
            saved=[]
            for asset,method,config in ((visual,'staged','config.toml'),(visual,'joint','config.toml'),(pdf,'staged','configs/ollama.toml'),(scan,'staged','config.toml')):
                out=json.loads(self.cli(env,'intake',asset,audio,'--consent','--method',method,'--config',ROOT/config,'--output',folder/'runs'))
                path=Path(out['draft']);saved.append(path);job=json.loads(path.read_text())
                self.assertEqual(job['state'],'needs_review');self.assertIsNone(job['fields']['item_model'])
                self.assertIn('item_model',job['unresolved']);self.assertEqual(job['fields']['preferred_time'],'morning')
                self.assertEqual(len(job['record']['usage']),3 if method=='staged' else 2)
                self.assertTrue(all(Path(job['record'][n]['path']).is_absolute() for n in ('visual','audio')))
            self.assertEqual(sum(path=='/api/chat' for path,_ in http.requests),2)
            path=saved[0];shown=json.loads(self.cli(env,'show',path));fields=folder/'fields.json';fields.write_text(json.dumps(dict(item_model='NR-18',problem='Stopped heating yesterday',preferred_time='morning')))
            self.cli(env,'approve',path,'--fields',fields,'--digest','wrong','--reviewer','Reader','--questions-resolved',ok=False)
            out=json.loads(self.cli(env,'approve',path,'--fields',fields,'--digest',shown['sha256'],'--reviewer','Reader','--questions-resolved'))
            reviewed=Path(out['reviewed']);self.assertEqual(json.loads(reviewed.read_text())['corrections']['item_model']['confirmed'],'NR-18')
            speech=folder/'spoken.wav';text=self.cli(env,'speak',reviewed,'--output',speech)
            self.assertIn('AI-generated voice',text)
            with wave.open(str(speech),'rb') as f:self.assertGreater(f.getnframes(),0)
            http.fail='speech';failed=folder/'failed-speech.wav';self.cli(env,'speak',reviewed,'--output',failed,ok=False)
            self.assertFalse(failed.exists());self.assertTrue(failed.with_suffix('.txt').exists());self.assertFalse(list(folder.glob('*.partial')))
            self.cli(env,'speak',path,'--output',folder/'unreviewed.wav',ok=False)
            http.fail='transcription';self.cli(env,'intake',visual,audio,'--consent','--output',folder/'failures',ok=False)
            failure=next((folder/'failures').glob('*/failure.json'));self.assertEqual(json.loads(failure.read_text())['stage'],'transcription');self.assertTrue(failure.with_name('visual.json').exists())
            before=len(http.requests);self.cli(env,'intake',visual,audio,'--output',folder/'no-consent',ok=False)
            self.assertEqual(len(http.requests),before);self.assertFalse((folder/'no-consent').exists())
            http.fail='quote';self.cli(env,'intake',pdf,audio,'--consent','--output',folder/'badquote',ok=False)
            self.assertEqual(json.loads(next((folder/'badquote').glob('*/failure.json')).read_text())['stage'],'visual')

if __name__=='__main__':unittest.main()

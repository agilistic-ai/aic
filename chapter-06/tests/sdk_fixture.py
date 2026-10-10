# Copyright (c) 2026, Agilistic AI LLC, All Rights Reserved
# SPDX-License-Identifier: MIT
#
# Provided without warranty. Use at your own risk.
# See LICENSE.txt and DISCLAIMER.md in this project for terms.

"""Real SDK transport fixture: responses are scripted, inference is not live."""
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json,os,threading,time

class Handler(BaseHTTPRequestHandler):
 def log_message(self,*args): pass
 def do_GET(self): self.respond(None)
 def do_POST(self):
  body=json.loads(self.rfile.read(int(self.headers.get('Content-Length','0'))) or b'{}')
  self.respond(body)
 def respond(self,body):
  self.server.requests.append((self.path,body))
  result=self.server.reply(self.path,body)
  if isinstance(result,dict) and result.get('_timeout'): time.sleep(.35);result={}
  if isinstance(result,dict) and result.get('_http_error'):
   self.send_response(503);self.end_headers();self.wfile.write(b'{"error":{"message":"fixture failure"}}');return
  if self.path=='/v1/responses':
   text=result if isinstance(result,str) else json.dumps(result)
   result={'id':'resp_fixture','object':'response','created_at':1,'model':body['model'],'status':'completed',
    'output':[{'type':'message','id':'msg_fixture','role':'assistant','status':'completed','content':[{'type':'output_text','text':text,'annotations':[]}]}],
    'usage':{'input_tokens':120,'output_tokens':90,'total_tokens':210}}
  elif self.path=='/api/chat':
   text=result if isinstance(result,str) else json.dumps(result)
   result={'model':body['model'],'created_at':'2026-10-03T00:00:00Z','message':{'role':'assistant','content':text},'done':True,'done_reason':'stop','prompt_eval_count':120,'eval_count':90}
  data=json.dumps(result).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(data)));self.end_headers()
  try:self.wfile.write(data)
  except (BrokenPipeError,ConnectionResetError):pass

@contextmanager
def serving(reply):
 server=ThreadingHTTPServer(('127.0.0.1',0),Handler);server.daemon_threads=True;server.reply=reply;server.requests=[]
 thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
 base=f'http://127.0.0.1:{server.server_port}'
 env={**os.environ,'AIC_API_KEY':'smoke-only','AIC_OPENAI_BASE_URL':base+'/v1','AIC_OLLAMA_HOST':base,'NO_PROXY':'127.0.0.1,localhost','no_proxy':'127.0.0.1,localhost'}
 try:yield server,env
 finally:server.shutdown();server.server_close();thread.join(timeout=2)

def packet(path,body):
 return json.loads(body['input'][-1]['content'] if path=='/v1/responses' else body['messages'][-1]['content'])

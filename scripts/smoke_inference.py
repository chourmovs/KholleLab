#!/usr/bin/env python3
"""Real deployment smoke: backend readiness, model quality, UI, and core health."""
import json,os,re,time,urllib.request
api=os.getenv('KHOLLELAB_API_URL','http://backend:8000/api').rstrip('/'); llm=os.getenv('LOCAL_LLM_BASE_URL','http://inference:8080/v1').rstrip('/'); frontend=os.getenv('KHOLLELAB_FRONTEND_URL','http://frontend:3000')
def fetch(url,data=None,timeout=90):
 req=urllib.request.Request(url,data=json.dumps(data).encode() if data else None,headers={'Content-Type':'application/json'} if data else {})
 with urllib.request.urlopen(req,timeout=timeout) as response:return json.load(response) if 'json' in response.headers.get('Content-Type','') else response.read()
deadline=time.monotonic()+int(os.getenv('INFERENCE_STARTUP_TIMEOUT','600'))
while True:
 status=fetch(api+'/inference/status')
 if status.get('provider')!='local':raise SystemExit('backend provider is not local')
 if status.get('status')=='ready':break
 if time.monotonic()>=deadline:raise SystemExit('inference readiness timeout')
 time.sleep(10)
def complete(prompt):
 started=time.perf_counter(); result=fetch(llm+'/chat/completions',{'model':os.getenv('LOCAL_LLM_MODEL','Qwen/Qwen3-4B-GGUF'),'messages':[{'role':'user','content':prompt}],'temperature':.2,'max_tokens':192}); text=result['choices'][0]['message']['content'].strip(); print(f'{time.perf_counter()-started:.2f}s {text}'); assert text; return text
assert '56' in complete('Réponds uniquement par le résultat de 7 × 8.')
algebra=complete('Résous 3x - 7 = 11 et donne une justification très courte.'); assert re.search(r'(x\s*=\s*6|\b6\b)',algebra,re.I)
assert fetch(api+'/health')['status']=='ok'; fetch(frontend)
print('real inference smoke passed')

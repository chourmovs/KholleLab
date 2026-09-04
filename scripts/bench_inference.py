#!/usr/bin/env python3
"""Manual llama.cpp benchmark with no CI performance threshold."""
import json,os,time,urllib.request
url=os.getenv('LOCAL_LLM_BASE_URL','http://inference:8080/v1').rstrip('/')+'/chat/completions'; model=os.getenv('LOCAL_LLM_MODEL','Qwen/Qwen3-4B-GGUF')
cases={'arithmetic':'Réponds seulement: 56. Combien font 7×8 ?','linear-equation':'Résous 3x-7=11. Réponse courte en français.','false-claim':'Un élève affirme que x²≥x pour tout réel x. Vérifie l’affirmation brièvement.','tutor-question':'Un élève est bloqué sur une équation du premier degré. Pose une seule question utile sans donner la solution.'}
print(f"MODEL: {model} {os.getenv('LOCAL_LLM_QUANT','Q4_K_M')}"); print(f"{'CASE':20} {'LATENCY':>9} {'TOKENS':>8} {'TOK/S':>8}")
for name,prompt in cases.items():
 body=json.dumps({'model':model,'messages':[{'role':'user','content':prompt}],'temperature':.2,'top_p':.9,'max_tokens':192}).encode(); started=time.perf_counter()
 try:
  with urllib.request.urlopen(urllib.request.Request(url,data=body,headers={'Content-Type':'application/json'}),timeout=90) as response:result=json.load(response)
  elapsed=time.perf_counter()-started; tokens=result.get('usage',{}).get('completion_tokens',0); speed=tokens/elapsed if tokens else 0
  print(f'{name:20} {elapsed:8.2f}s {tokens:8} {speed:8.1f}'); print('  '+result['choices'][0]['message']['content'].strip().replace('\n',' '))
 except Exception as exc: print(f'{name:20} FAILED: {exc}')

#!/usr/bin/env python3
"""Bounded manual readiness check through Khollelab's backend API."""
import argparse,json,os,time,urllib.request
base=os.getenv('KHOLLELAB_API_URL','http://backend:8000/api').rstrip('/')
p=argparse.ArgumentParser(); p.add_argument('--status',action='store_true'); p.add_argument('--wait',type=int,default=600); args=p.parse_args()
def get(path):
    with urllib.request.urlopen(base+path,timeout=10) as response:return json.load(response)
deadline=time.monotonic()+args.wait
while True:
    status=get('/inference/status'); print(json.dumps(status,ensure_ascii=False))
    if status.get('status')=='ready' or args.status:break
    if time.monotonic()>=deadline:raise SystemExit('inference did not become ready')
    time.sleep(10)
if not args.status:print('Inference ready; run scripts/bench_inference.py for completion quality checks.')

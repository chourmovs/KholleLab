#!/usr/bin/env python3
"""Run sequential, dependency-aware checks against private llama.cpp inference."""
import json, os, socket, time, urllib.error, urllib.parse, urllib.request
base = os.getenv("LOCAL_LLM_BASE_URL", "http://inference:8080/v1").rstrip("/")
parsed = urllib.parse.urlparse(base); host, port = parsed.hostname or "inference", parsed.port or 8080
model = os.getenv("LOCAL_LLM_MODEL", "Qwen/Qwen3-4B-GGUF")
def row(label, state, detail=""): print(f"{label:<19}{state:<6}{detail}")
def request(url, body=None, timeout=10):
    data=json.dumps(body).encode() if body else None; req=urllib.request.Request(url,data=data,headers={"Content-Type":"application/json"} if data else {})
    started=time.perf_counter()
    try:
        with urllib.request.urlopen(req,timeout=timeout) as response: return response.status,json.load(response),time.perf_counter()-started
    except urllib.error.HTTPError as exc: return exc.code,None,time.perf_counter()-started
    except (urllib.error.URLError,TimeoutError,json.JSONDecodeError): return None,None,time.perf_counter()-started
print("KHOLLELAB INFERENCE DIAGNOSTIC\n")
provider=os.getenv("LLM_PROVIDER","local"); row("Provider config","PASS" if provider=="local" else "FAIL",provider)
try: socket.getaddrinfo(host,port); dns=True; row("DNS inference","PASS")
except socket.gaierror: dns=False; row("DNS inference","FAIL")
tcp=False
if dns:
    try:
        with socket.create_connection((host,port),timeout=3): pass
        tcp=True; row("TCP 8080","PASS")
    except OSError: row("TCP 8080","FAIL")
else: row("TCP 8080","SKIP")
if tcp:
    code,_,latency=request(base.removesuffix("/v1")+"/health"); health_ok=code==200; row("Health","PASS" if health_ok else "FAIL",code or "unreachable")
else: latency=0; health_ok=False; row("Health","SKIP")
if health_ok:
    code,data,_=request(base+"/models"); models_ok=code==200; shown=((data or {}).get("data") or [{}])[0].get("id",""); row("Models","PASS" if models_ok else "FAIL",shown or code)
else: models_ok=False; row("Models","SKIP")
if models_ok:
    code,data,latency=request(base+"/chat/completions",{"model":model,"messages":[{"role":"user","content":"Réponds uniquement par 56 : combien font 7 × 8 ?"}],"temperature":0,"max_tokens":16},90)
    preview=(((data or {}).get("choices") or [{}])[0].get("message") or {}).get("content","").strip(); row("Completion","PASS" if code==200 and "56" in preview else "FAIL",preview[:80])
else: row("Completion","SKIP")
row("Latency","",f"{latency:.2f} s")

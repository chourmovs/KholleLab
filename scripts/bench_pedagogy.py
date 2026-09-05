#!/usr/bin/env python3
import argparse,asyncio,sys,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; os.environ.setdefault("DATABASE_URL","sqlite:///./benchmark.db"); sys.path.insert(0,str(ROOT/"backend"))
from app.benchmark.models import load_cases
from app.benchmark.runner import BenchmarkRunner
from app.benchmark.report import build_report,console_report,manual_review,write_json
from app.providers.llm import FakeLLMProvider,HuggingFaceProvider
async def main(args):
    cases=load_cases(ROOT/"benchmarks/pedagogy")
    if args.level: cases=[c for c in cases if c.curriculum.level.value==args.level]
    if args.case: cases=[c for c in cases if c.id==args.case]
    if args.quick: cases=[c for c in cases if c.quick]
    if not cases: raise SystemExit("No benchmark cases matched the filters")
    provider=FakeLLMProvider() if args.provider=="fake" else HuggingFaceProvider(family=args.family)
    results=await BenchmarkRunner().run(cases,provider); report=build_report(results,getattr(provider,"model","fake"))
    print(console_report(report)); print("\nMANUAL REVIEW SAMPLE\n"+manual_review(results))
    if args.json: write_json(report,args.json)
p=argparse.ArgumentParser(); p.add_argument("--provider",choices=("fake","huggingface"),default="fake"); p.add_argument("--family",choices=("qwen","gemma"),default="qwen"); p.add_argument("--level",choices=("seconde","premiere","terminale","maths-sup","maths-spe")); p.add_argument("--case"); p.add_argument("--quick",action="store_true"); p.add_argument("--json",nargs="?",const="artifacts/pedagogy-benchmark.json")
if __name__=="__main__": asyncio.run(main(p.parse_args()))

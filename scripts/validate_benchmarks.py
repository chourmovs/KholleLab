#!/usr/bin/env python3
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"backend"))
from app.benchmark.models import load_cases
try: cases=load_cases(ROOT/"benchmarks/pedagogy")
except Exception as exc: print(f"Invalid pedagogical benchmark: {exc}",file=sys.stderr); raise SystemExit(1)
if len(cases)<100: raise SystemExit(f"Expected at least 100 cases, found {len(cases)}")
print(f"{len(cases)} pedagogical benchmark cases valid.")

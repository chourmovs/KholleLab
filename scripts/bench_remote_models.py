#!/usr/bin/env python3
"""Run the existing pedagogical corpus against whitelisted remote families/roles."""
import argparse, subprocess, sys
p=argparse.ArgumentParser(); p.add_argument("--quick",action="store_true"); p.add_argument("--full",action="store_true"); p.add_argument("--family",choices=("qwen","gemma","all"),default="all"); p.add_argument("--role",choices=("fast","deep","all"),default="all")
args=p.parse_args(); families=("qwen","gemma") if args.family=="all" else (args.family,)
for family in families:
    command=[sys.executable,"scripts/bench_pedagogy.py","--provider","huggingface","--family",family]
    if args.quick and not args.full: command.append("--quick")
    print(f"\nKHOLLELAB REMOTE MODEL BENCHMARK · {family.upper()} · roles={args.role}",flush=True)
    subprocess.run(command,check=True)

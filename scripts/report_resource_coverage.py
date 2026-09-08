#!/usr/bin/env python3
"""Report resolver coverage by level, knowledge node, and expectation."""
from collections import defaultdict
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.services.curriculum_repository import CurriculumRepository
from app.services.problem_repository import ProblemRepository
from app.services.resource_repository import ResourceRepository, validate_problem_resource_refs, validate_resource_curriculum_refs
from app.services.resource_resolver import ResourceResolver, context_for_problem

KINDS = ("course", "example", "video")
def flags(matches):
    found={m.resource.type for m in matches}; return tuple(int(k in found) for k in KINDS)
def main():
    curriculum=CurriculumRepository(ROOT/"curriculum"); curriculum.load()
    problems=ProblemRepository(ROOT/"problems",curriculum); problems.load()
    resources=ResourceRepository(ROOT/"resources"); resources.load()
    validate_resource_curriculum_refs(resources,curriculum); validate_problem_resource_refs(problems,resources)
    resolver=ResourceResolver(resources); by_level=defaultdict(lambda:[0,0,0,0]); by_node=defaultdict(lambda:[0,0,0,0]); by_exp=defaultdict(lambda:[0,0])
    for problem in problems.list():
        ctx=context_for_problem(problem,curriculum); match=resolver.resolve(ctx); coverage=flags(match)
        row=by_level[problem.curriculum.level.value]; row[0]+=1
        for i,value in enumerate(coverage,1): row[i]+=value
        for kid in ctx.knowledge_ids:
            row=by_node[kid]; row[0]+=1
            for i,value in enumerate(coverage,1): row[i]=max(row[i],value)
        for eid in ctx.curriculum_expectations:
            by_exp[eid][0]+=1; by_exp[eid][1]+=coverage[0]
    print("RESOURCE COVERAGE V2\n\nBY LEVEL")
    print(f"{'level':12} {'problems':>8} {'course':>8} {'example':>8} {'video':>8}")
    for level in curriculum.levels:
        print(f"{level.label:12} "+" ".join(f"{x:8}" for x in by_level[level.id.value]))
    print("\nBY KNOWLEDGE NODE\nnode                              problems  course example video")
    for kid,row in sorted(by_node.items()): print(f"{kid:34} {row[0]:8} {('yes' if row[1] else 'no'):>7} {('yes' if row[2] else 'no'):>7} {('yes' if row[3] else 'no'):>5}")
    print("\nBY CURRICULUM EXPECTATION\nexpectation                         problems course coverage")
    for eid,row in sorted(by_exp.items()): print(f"{eid:36} {row[0]:8} {row[1]:6} {100*row[1]/row[0]:7.1f}%")
    unused=set(curriculum.knowledge_nodes)-set(by_node)
    uncovered=[eid for eid,(total,course) in by_exp.items() if total and not course]
    print(f"\nknowledge nodes without problems: {len(unused)} ({', '.join(sorted(unused)) or '-'})")
    print(f"expectations with problems but no course match: {len(uncovered)} ({', '.join(sorted(uncovered)) or '-'})")
if __name__ == '__main__': main()

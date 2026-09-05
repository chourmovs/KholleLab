#!/usr/bin/env python3
"""Signale le vocabulaire anglais probable; ce contrôle linguistique ne valide pas les maths."""
from pathlib import Path
import re,sys,yaml
ROOT=Path(__file__).parents[1]/"problems"; fields=("statement","reference_solution")
english=re.compile(r"\b(the|then|therefore|since|assume|solution is|we have|let us)\b",re.I)
files=sorted(ROOT.glob("**/*.yaml")); flagged=[]
for path in files:
    data=yaml.safe_load(path.read_text(encoding="utf-8"))
    for field in fields:
        if english.search(str(data.get(field,""))):flagged.append(f"{path.relative_to(ROOT)}: {field}")
print(f"Solutions de référence auditées : {len(files)}")
print(f"Corrections françaises confirmées : {len(files)-len(flagged)}/{len(files)}")
if flagged: print("Prose anglaise probable :\n"+"\n".join(flagged));sys.exit(1)

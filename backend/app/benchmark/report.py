from __future__ import annotations
import json
from datetime import datetime,timezone
from pathlib import Path
from .scoring import aggregate

def build_report(results,model="Qwen/Qwen3-4B-GGUF",quantization="Q4_K_M"):
    levels={}
    for level in sorted({r.case.curriculum.level.value for r in results}): levels[level]=aggregate([r for r in results if r.case.curriculum.level.value==level])
    cases=[{"id":r.case.id,"level":r.case.curriculum.level.value,"task_type":r.case.task_type.value,"expected_state":r.case.expected.state.value,"actual_state":r.assessment.student_state.value,"expected_intervention":r.case.expected.intervention_type.value,"actual_intervention":r.assessment.intervention_type.value,"confidence":r.assessment.confidence,"latency_ms":round(r.latency_ms,2),"tokens_per_second":r.tokens_per_second,"intervention":r.assessment.intervention,"passed":r.score.passed,"failure_reasons":[k for k,v in vars(r.score).items() if not v]} for r in results]
    return {"model":model,"quantization":quantization,"prompt_version":"tutor-assessment-v1","timestamp":datetime.now(timezone.utc).isoformat(),"summary":aggregate(results),"levels":levels,"cases":cases}
def write_json(report,path):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
def console_report(report):
    s=report["summary"]; pct=lambda x:f"{100*x:6.1f}%"
    lines=["KHOLLELAB PEDAGOGICAL BENCHMARK",f"Model: {report['model']} {report['quantization']}","Prompt: tutor-assessment-v1","","OVERALL (false positives are critical)",f"Cases                    {s['cases']}",f"Structured valid         {pct(s['structured_validity'])}",f"FALSE ERROR RATE         {pct(s['false_error_rate'])}",f"Error recall             {pct(s['error_recall'])}",f"Blocked detection        {pct(s['blocked_detection'])}",f"Alt-method acceptance    {pct(s['alternative_method_acceptance'])}",f"Spoiler rate             {pct(s['spoiler_rate'])}",f"Help-level compliance    {pct(s['help_level_compliance'])}",f"Prompt injection         {pct(s['prompt_injection_resistance'])}","",f"Latency p50              {s['latency_p50_ms']:.1f}ms",f"Latency p95              {s['latency_p95_ms']:.1f}ms",f"Latency max              {s['latency_max_ms']:.1f}ms",f"Tokens/sec               {s['tokens_per_second']:.1f}","","BY LEVEL"]
    for name,m in report["levels"].items(): lines += [f"{name}: {m['cases']} cases; error recall {pct(m['error_recall'])}; false errors {pct(m['false_error_rate'])}; spoiler {pct(m['spoiler_rate'])}"]
    failures=[x for x in report["cases"] if not x["passed"]]; lines += ["","FAILURES"]+[f"{x['id']}: {', '.join(x['failure_reasons'])}" for x in failures]
    return "\n".join(lines)
def manual_review(results):
    groups=("valid_progress","mathematical_error","student_blocked","alternative_valid_method","prompt_injection"); picked=[]
    for group in groups:picked.extend([r for r in results if r.case.task_type.value==group][:2])
    return "\n\n".join(f"[{r.case.id}] {r.case.task_type.value}\nÉlève: {r.case.student_state.solution}\nColleur: {r.assessment.intervention or '(silence)'}" for r in picked)

import asyncio,json
from pathlib import Path
import pytest
from pydantic import ValidationError
from app.benchmark.models import BenchmarkCase,TutorAssessment,load_cases
from app.benchmark.report import build_report,write_json
from app.benchmark.runner import BenchmarkRunner
from app.benchmark.scoring import aggregate,percentile,score_case,spoiler
from app.providers.llm import FakeLLMProvider
ROOT=Path(__file__).resolve().parents[2]
def cases(): return load_cases(ROOT/"benchmarks/pedagogy")
def test_yaml_parsing_and_distribution():
    loaded=cases(); assert len(loaded)==100; assert len({x.id for x in loaded})==100
    assert len({x.task_type for x in loaded})==10; assert len({x.curriculum.level for x in loaded})==5
def test_duplicate_ids(tmp_path):
    source=(ROOT/"benchmarks/pedagogy/seconde/cases.yaml").read_text(); (tmp_path/"a.yaml").write_text(source); (tmp_path/"b.yaml").write_text(source)
    with pytest.raises(ValueError,match="duplicate"):load_cases(tmp_path)
def test_assessment_validation():
    with pytest.raises(ValidationError): TutorAssessment(student_state="error",intervention_needed=True,error_detected=True,error_category="algebra",confidence=1.1,intervention_type="hint",intervention="Indice",reveals_answer=False,estimated_help_level=4)
    with pytest.raises(ValidationError): TutorAssessment(student_state="blocked",intervention_needed=True,error_detected=False,error_category="none",confidence=.8,intervention_type="direction",intervention=None,reveals_answer=False,estimated_help_level=2)
def test_fake_runner_metrics_and_json(tmp_path):
    results=asyncio.run(BenchmarkRunner().run(cases(),FakeLLMProvider())); summary=aggregate(results)
    assert summary["error_recall"]==1 and summary["false_error_rate"]==0 and summary["help_level_compliance"]==1
    assert summary["blocked_detection"]==1 and summary["alternative_method_acceptance"]==1
    report=build_report(results); target=tmp_path/"report.json"; write_json(report,target)
    assert json.loads(target.read_text())["summary"]["cases"]==100; assert len(report["levels"])==5
def test_spoiler_help_and_scoring():
    case=cases()[0]; raw={"student_state":case.expected.state,"intervention_needed":case.expected.intervention_needed,"error_detected":case.expected.error_present,"error_category":case.expected.error_category,"confidence":.9,"intervention_type":case.expected.intervention_type,"intervention":None if not case.expected.intervention_needed else "résultat final = 42","reveals_answer":False,"estimated_help_level":case.requested_help_level}
    actual=TutorAssessment.model_validate(raw); assert spoiler(case,actual); assert not score_case(case,actual).answer_not_revealed
def test_latency_percentiles():
    assert percentile([1,2,3,4],.5)==2.5; assert percentile([1,2,3,4],.95)==pytest.approx(3.85); assert percentile([],.5)==0

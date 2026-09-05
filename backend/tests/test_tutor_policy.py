import inspect
import pytest
from app.benchmark import models as benchmark_models
from app.schemas.tutor import TutorAssessment, TutorTrigger
from app.services.tutor import apply_policy

def assessment(**changes):
    value=dict(student_state="error",intervention_needed=True,error_detected=True,error_category="algebra",confidence=.9,intervention_type="direction",intervention="Vérifie ce calcul.",reveals_answer=False,estimated_help_level=2)
    value.update(changes);return TutorAssessment(**value)

def test_benchmark_uses_production_contract():
    assert benchmark_models.TutorAssessment is TutorAssessment

def test_high_confidence_keeps_minimal_intervention():
    safe,level=apply_policy(assessment(),2,TutorTrigger.MEANINGFUL_PROGRESS)
    assert safe.intervention=="Vérifie ce calcul." and level==2

def test_medium_confidence_is_cautious_socratic():
    safe,level=apply_policy(assessment(confidence=.7),3,TutorTrigger.MEANINGFUL_PROGRESS)
    assert not safe.error_detected and safe.intervention_type.value=="socratic_question" and level==1

def test_low_confidence_is_silent_automatically():
    safe,level=apply_policy(assessment(confidence=.4),3,TutorTrigger.STALLED)
    assert not safe.intervention_needed and safe.intervention is None and level==0

def test_spoiler_and_auto_level_guards():
    safe,level=apply_policy(assessment(reveals_answer=True,estimated_help_level=5,intervention="FINAL_ANSWER_SENTINEL"),5,TutorTrigger.MEANINGFUL_PROGRESS)
    assert safe.intervention is None and level==0

def test_reference_solution_is_not_part_of_safe_payload():
    source=inspect.getsource(__import__("app.services.tutor",fromlist=["TutorAssessmentService"]).TutorAssessmentService.assess)
    assert 'problem.reference_solution' not in source

from pydantic import ValidationError
from app.schemas.tutor import ResourceNeed, TutorResourceSignal
from app.services.tutor import sanitize_resource_signal

def test_resource_signal_contract_rejects_inconsistent_or_prose_values():
    with pytest.raises(ValidationError):
        TutorResourceSignal(needed=False,need="course_gap",topics=[])
    with pytest.raises(ValidationError):
        TutorResourceSignal(needed=True,need="course_gap",topics=["long free-form prose"])
    with pytest.raises(ValidationError):
        TutorResourceSignal(needed=True,need="method_gap",topics=["a","b","c","d"])

def test_resource_signal_is_intersected_with_server_vocabulary():
    signal=TutorResourceSignal(needed=True,need=ResourceNeed.COURSE_GAP,topics=["derivatives","fake-secret-resource"],skills=["sign-analysis"])
    safe=sanitize_resource_signal(signal,{"themes":["derivatives"],"prerequis":[],"competences":["sign-analysis"],"tags":[]})
    assert safe.topics==["derivatives"] and safe.skills==["sign-analysis"]

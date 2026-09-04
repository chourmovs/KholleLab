import pytest
from pydantic import ValidationError
from app.domain.problem import Problem


def valid_problem():
    return {"id":"olympiades-2012-003","title":"Titre","statement":"Énoncé","curriculum":{"level":"premiere","difficulty":2},"topics":["algebra"],"prerequisites":[],"skills":["proof"],"source":{"type":"internal","name":"Tests"},"reference_solution":"Solution","hints":[{"level":1,"text":"Indice"}]}


def test_valid_problem(): assert Problem.model_validate(valid_problem()).id == "olympiades-2012-003"
@pytest.mark.parametrize("difficulty", [0, 6])
def test_invalid_difficulty(difficulty):
    data=valid_problem(); data["curriculum"]["difficulty"]=difficulty
    with pytest.raises(ValidationError): Problem.model_validate(data)
@pytest.mark.parametrize("identifier", ["has space", "Uppercase-001"])
def test_invalid_id(identifier):
    data=valid_problem(); data["id"]=identifier
    with pytest.raises(ValidationError): Problem.model_validate(data)
def test_missing_statement():
    data=valid_problem(); del data["statement"]
    with pytest.raises(ValidationError): Problem.model_validate(data)
def test_empty_solution():
    data=valid_problem(); data["reference_solution"]="  "
    with pytest.raises(ValidationError): Problem.model_validate(data)
def test_duplicate_hints():
    data=valid_problem(); data["hints"] *= 2
    with pytest.raises(ValidationError): Problem.model_validate(data)
def test_invalid_hint_level():
    data=valid_problem(); data["hints"][0]["level"]=6
    with pytest.raises(ValidationError): Problem.model_validate(data)

def test_valid_pedagogical_resources():
    data=valid_problem(); data["resources"]={"course_points":[{"title":"Rappel","summary":"\\(a+b\\)","topics":["algebra"]}],"videos":[{"title":"Une vidéo","provider":"youtube","url":"https://youtu.be/abc123","duration_minutes":8}]}
    resources=Problem.model_validate(data).resources
    assert resources and resources.course_points[0].title == "Rappel"

@pytest.mark.parametrize("resource", [
    {"course_points":[{"title":" ","summary":"Contenu"}]},
    {"videos":[{"title":"Vidéo","provider":"youtube","url":"not-a-url"}]},
    {"videos":[{"title":"Vidéo","provider":"youtube","url":"https://example.com/video"}]},
    {"videos":[{"title":"Vidéo","provider":"youtube","url":"https://youtube.com/watch?v=x","duration_minutes":0}]},
])
def test_invalid_pedagogical_resource(resource):
    data=valid_problem(); data["resources"]=resource
    with pytest.raises(ValidationError): Problem.model_validate(data)

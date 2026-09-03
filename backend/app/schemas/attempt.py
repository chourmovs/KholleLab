import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from app.models.attempt import AttemptStatus

class AttemptCreate(BaseModel): problem_id: str = Field(min_length=1, max_length=255)
class AttemptUpdate(BaseModel):
    solution_markdown: str = Field(max_length=100_000)
    elapsed_seconds: int = Field(ge=0)
    expected_revision: int = Field(ge=0)
class AttemptSubmit(BaseModel): expected_revision: int = Field(ge=0)
class AttemptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID; problem_id: str; status: AttemptStatus; solution_markdown: str
    revision: int; elapsed_seconds: int; started_at: datetime; updated_at: datetime; submitted_at: datetime | None

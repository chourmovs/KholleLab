from pydantic import BaseModel, Field


class Problem(BaseModel):
    id: str
    title: str
    level: str
    difficulty: int = Field(ge=1, le=5)
    topics: list[str]
    statement_tex: str

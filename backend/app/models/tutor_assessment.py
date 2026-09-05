import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class TutorAssessmentRecord(Base):
    __tablename__="tutor_assessments"
    __table_args__=(UniqueConstraint("attempt_id","client_request_id",name="uq_tutor_attempt_request"),)
    id:Mapped[uuid.UUID]=mapped_column(Uuid,primary_key=True,default=uuid.uuid4)
    attempt_id:Mapped[uuid.UUID]=mapped_column(Uuid,ForeignKey("attempts.id",ondelete="CASCADE"),index=True)
    revision:Mapped[int]=mapped_column(Integer); trigger:Mapped[str]=mapped_column(String(32)); requested_help_level:Mapped[int]=mapped_column(Integer); effective_help_level:Mapped[int]=mapped_column(Integer)
    student_state:Mapped[str]=mapped_column(String(32)); intervention_needed:Mapped[bool]=mapped_column(Boolean); intervention_type:Mapped[str]=mapped_column(String(32)); intervention:Mapped[str|None]=mapped_column(Text)
    confidence:Mapped[float]=mapped_column(Float); error_category:Mapped[str]=mapped_column(String(32)); reveals_answer:Mapped[bool]=mapped_column(Boolean)
    provider:Mapped[str]=mapped_column(String(64)); model:Mapped[str]=mapped_column(String(255)); backend:Mapped[str]=mapped_column(String(64)); client_request_id:Mapped[str]=mapped_column(String(100))
    recommended_resource_id:Mapped[str|None]=mapped_column(String(64),nullable=True)
    resource_need:Mapped[str|None]=mapped_column(String(32),nullable=True)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc),index=True)

from datetime import datetime
from pydantic import BaseModel, Field

class RegisterRequest(BaseModel):
    email: str
    password: str
    display_name: str | None = Field(default=None, max_length=100)
    claim_anonymous_history: bool = True

class LoginRequest(BaseModel):
    email: str
    password: str

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

class AccountView(BaseModel):
    authenticated: bool
    email: str | None = None
    display_name: str | None = None
    created_at: datetime | None = None
    anonymous_sessions_available: int = 0


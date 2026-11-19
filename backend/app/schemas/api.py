"""Request/response models for the REST API."""
from typing import Any

from pydantic import BaseModel, EmailStr, Field


class RegisterIn(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=8, max_length=72)


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    preferences: dict[str, Any] = {}


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class SettingsIn(BaseModel):
    provider: str | None = Field(default=None, pattern="^(gemini|groq|openai)$")
    full_name: str | None = Field(default=None, min_length=1, max_length=120)


class ConversationCreate(BaseModel):
    title: str | None = Field(default=None, max_length=200)


class MessageIn(BaseModel):
    content: str = Field(min_length=2, max_length=1000)
    provider: str | None = Field(default=None, pattern="^(gemini|groq|openai)$")


class ClarificationIn(BaseModel):
    option_id: str = Field(min_length=1, max_length=80)
    provider: str | None = Field(default=None, pattern="^(gemini|groq|openai)$")


class ExecuteIn(BaseModel):
    sql: str = Field(min_length=1, max_length=8000)
    question: str = Field(default="(edited SQL)", max_length=1000)
    conversation_id: int | None = None


class SavedQueryIn(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    question: str = Field(default="", max_length=1000)
    sql: str = Field(min_length=1, max_length=8000)


class DebugQuestion(BaseModel):
    question: str = Field(min_length=2, max_length=1000)
    confirmed: dict[str, str] = Field(default_factory=dict, description="term_id -> option_id")
    provider: str | None = None

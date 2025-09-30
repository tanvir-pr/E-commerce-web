"""Auth request/response bodies."""

from pydantic import BaseModel, EmailStr, Field


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)


class RegisterOut(BaseModel):
    message: str


class VerifyEmailIn(BaseModel):
    token: str = Field(min_length=20, max_length=256)


class VerifyEmailOut(BaseModel):
    message: str


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class LoginOut(BaseModel):
    next: str = "session"


class CsrfOut(BaseModel):
    csrf_token: str


class MessageOut(BaseModel):
    message: str

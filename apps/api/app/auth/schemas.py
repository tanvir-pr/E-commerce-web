"""Auth request/response bodies."""

from typing import Literal

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
    next: Literal["session", "enroll", "challenge"]


class CsrfOut(BaseModel):
    csrf_token: str


class MessageOut(BaseModel):
    message: str


class TotpSetupOut(BaseModel):
    secret: str
    otpauth_url: str
    qr_svg: str


class TotpConfirmIn(BaseModel):
    code: str = Field(min_length=6, max_length=8)


class TotpConfirmOut(BaseModel):
    recovery_codes: list[str]
    next: Literal["session"] = "session"


class TotpChallengeIn(BaseModel):
    code: str | None = Field(default=None, min_length=6, max_length=8)
    recovery_code: str | None = Field(default=None, min_length=6, max_length=32)


class AuthConfigOut(BaseModel):
    phone_registration_enabled: bool
    skin_types: list[str]
    skin_concerns: list[str]


class PasswordResetRequestIn(BaseModel):
    email: EmailStr


class PasswordResetConfirmIn(BaseModel):
    token: str = Field(min_length=20, max_length=256)
    password: str = Field(min_length=10, max_length=128)


class PhoneStartIn(BaseModel):
    phone: str = Field(min_length=8, max_length=32)


class PhoneConfirmIn(BaseModel):
    phone: str = Field(min_length=8, max_length=32)
    code: str = Field(min_length=4, max_length=8)

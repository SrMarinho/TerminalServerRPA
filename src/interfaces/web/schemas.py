"""Pydantic request models for endpoints with a fixed payload shape.

Endpoints whose body is task-defined and dynamic (run params, task config) keep
a plain dict on purpose — there is no fixed schema to validate there.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class CredentialIn(BaseModel):
    service: str = Field(min_length=1)
    username: str = ""
    password: str = ""

    @model_validator(mode="after")
    def _username_or_password(self) -> CredentialIn:
        if not self.username and not self.password:
            raise ValueError("username or password required")
        return self


class BreakpointIn(BaseModel):
    step: str = Field(min_length=1)
    enabled: bool


class SnippetIn(BaseModel):
    code: str = ""

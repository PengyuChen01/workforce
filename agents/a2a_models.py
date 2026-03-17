"""Shared A2A JSON-RPC models used by all agents."""

from pydantic import BaseModel, Field


class TextPart(BaseModel):
    type: str = "text"
    text: str


class Message(BaseModel):
    role: str
    parts: list[TextPart]


class TaskParams(BaseModel):
    id: str
    message: Message


class A2ARequest(BaseModel):
    jsonrpc: str = "2.0"
    method: str
    params: TaskParams


class Artifact(BaseModel):
    type: str = "text"
    text: str


class TaskResult(BaseModel):
    id: str
    status: str
    artifacts: list[Artifact] = Field(default_factory=list)


class A2AResponse(BaseModel):
    jsonrpc: str = "2.0"
    result: TaskResult

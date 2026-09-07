from pydantic import BaseModel, ConfigDict
from typing import Optional


class EmployeeCreate(BaseModel):
    name: str
    role: str
    salary: float


class EmployeeUpdate(BaseModel):
    name: str
    role: str
    salary: float


class EmployeeResponse(BaseModel):
    id: int
    name: str
    role: str
    salary: float

    model_config = ConfigDict(from_attributes=True)


class ChatRequest(BaseModel):
    message: str
    model: str = "groq"
    conversation_id: Optional[int] = None
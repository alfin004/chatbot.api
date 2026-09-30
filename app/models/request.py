from pydantic import BaseModel, Field, field_validator


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=500, description="Natural-language user message")

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Message cannot be empty")
        if any(ord(ch) < 32 and ch not in "\t\n\r" for ch in value):
            raise ValueError("Message contains unsupported control characters")
        return " ".join(value.split())

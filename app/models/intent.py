from pydantic import BaseModel, Field, field_validator
from app.core.constants import Intent


class ExtractedItem(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    quantity: int = Field(default=1, ge=1, le=100)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        return " ".join(value.strip().lower().split())


class IntentResult(BaseModel):
    intent: Intent
    items: list[ExtractedItem] = Field(default_factory=list)
    message: str | None = None

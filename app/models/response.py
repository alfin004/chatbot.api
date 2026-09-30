from typing import Any
from pydantic import BaseModel, Field
from app.core.constants import ChatStatus, Intent
from app.services.session_service import CartItem


class ResponseItem(BaseModel):
    item_id: str
    name: str
    quantity: int | None = None
    price: float | None = None
    unit: str | None = None
    total: float | None = None
    category: str | None = None


class CartSummary(BaseModel):
    item_count: int = 0
    total_quantity: int = 0
    total_amount: float = 0


class ChatResponse(BaseModel):
    success: bool = True
    session_id: str
    status: ChatStatus
    intent: Intent
    message: str
    items: list[ResponseItem] = Field(default_factory=list)
    cart: CartSummary | None = None
    cartItems: list[CartItem] = []
    metadata: dict[str, Any] = Field(default_factory=dict)
    links: list[dict] = []

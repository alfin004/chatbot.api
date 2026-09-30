from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4


@dataclass
class CartItem:
    item_id: str
    name: str
    quantity: int
    price: float | None
    unit: str | None
    category: str | None = None


@dataclass
class PendingItem:
    original_name: str
    quantity: int
    candidate_item_ids: list[str]


@dataclass
class SessionState:
    tenant_id: str
    session_id: str
    cart: dict[str, CartItem] = field(default_factory=dict)
    pending_action: str | None = None
    pending_items: list[PendingItem] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class SessionService:
    def __init__(self, ttl_minutes: int = 60):
        self.ttl = timedelta(minutes=ttl_minutes)
        self._sessions: dict[tuple[str, str], SessionState] = {}

    def get_cart(
        self,
        tenant_id: str,
        session_id: str,
    ) -> list[dict[str, Any]]:
        session = self._sessions.get((tenant_id, session_id))

        if not session:
            return []
        cart_items = []
        for x in session.cart.keys():
           cart_items.append(session.cart[x])

        return cart_items

    def get_or_create(self, tenant_id: str, session_id: str | None) -> tuple[SessionState, bool]:
        sid = session_id or str(uuid4())
        key = (tenant_id, sid)
        state = self._sessions.get(key)
        now = datetime.now(timezone.utc)
        if state and now - state.updated_at <= self.ttl:
            state.updated_at = now
            return state, False
        state = SessionState(tenant_id=tenant_id, session_id=sid)
        self._sessions[key] = state
        return state, True

    def touch(self, state: SessionState) -> None:
        state.updated_at = datetime.now(timezone.utc)

    def add_item(self, state: SessionState, item: dict, quantity: int) -> CartItem:
        item_id = item["id"]
        existing = state.cart.get(item_id)
        if existing:
            existing.quantity += quantity
            cart_item = existing
        else:
            cart_item = CartItem(
                item_id=item_id,
                name=item["name"],
                quantity=quantity,
                price=item.get("price"),
                unit=item.get("unit"),
                category=item.get("category"),
            )
            state.cart[item_id] = cart_item
        self.touch(state)
        return cart_item

    def clear_pending(self, state: SessionState) -> None:
        state.pending_action = None
        state.pending_items = []
        self.touch(state)

    def cart_summary(self, state: SessionState) -> dict:
        items = list(state.cart.values())
        return {
            "item_count": len(items),
            "total_quantity": sum(x.quantity for x in items),
            "total_amount": round(sum((x.price or 0) * x.quantity for x in items), 2),
        }

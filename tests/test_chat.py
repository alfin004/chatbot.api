from pathlib import Path
import pytest
from app.clients.grok_client import GrokClient
from app.core.config import Settings
from app.repositories.menu_repository import MenuRepository
from app.services.chat_service import ChatService
from app.services.initiate_service import InitiateService
from app.services.menu_service import MenuService
from app.services.session_service import SessionService


class FakeGrok:
    def __init__(self, result):
        self.result = result

    async def extract_intent(self, message):
        return self.result


@pytest.mark.asyncio
async def test_greeting_does_not_call_grok():
    class FailingGrok:
        async def extract_intent(self, message):
            raise AssertionError("Grok should not be called for default messages")

    service = ChatService(
        InitiateService(),
        FailingGrok(),
        MenuService(MenuRepository(Path(__file__).parents[1] / "app/data/menu.json")),
        SessionService(),
    )
    response = await service.process("tenant", None, "hello")
    assert response.intent.value == "GREETING"


@pytest.mark.asyncio
async def test_ambiguous_add_does_not_modify_cart():
    from app.models.intent import IntentResult
    service = ChatService(
        InitiateService(),
        FakeGrok(IntentResult(intent="ADD", items=[{"name": "biryani", "quantity": 5}])),
        MenuService(MenuRepository(Path(__file__).parents[1] / "app/data/menu.json")),
        SessionService(),
    )
    response = await service.process("tenant", None, "I want 5 biryanis")
    assert response.status.value == "CLARIFICATION_REQUIRED"
    state, _ = service.sessions.get_or_create("tenant", response.session_id)
    assert state.cart == {}
    assert state.pending_items

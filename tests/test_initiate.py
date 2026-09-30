from app.core.constants import Intent
from app.services.initiate_service import InitiateService


def test_greeting():
    result = InitiateService().check(" Hi! ")
    assert result[0] == Intent.GREETING


def test_thanks():
    result = InitiateService().check("thank you")
    assert result[0] == Intent.THANKS

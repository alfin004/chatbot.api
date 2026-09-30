import re
from app.core.constants import Intent


class InitiateService:
    DEFAULTS = {
        "hi": (Intent.GREETING, "Hello! How can I help you with your order?"),
        "hello": (Intent.GREETING, "Hello! How can I help you with your order?"),
        "hey": (Intent.GREETING, "Hello! How can I help you with your order?"),
        "thanks": (Intent.THANKS, "You're welcome! Is there anything else I can help you with?"),
        "thank you": (Intent.THANKS, "You're welcome! Is there anything else I can help you with?"),
        "bye": (Intent.GREETING, "Thank you! Have a great day!"),
        "goodbye": (Intent.GREETING, "Thank you! Have a great day!"),
        "help": (Intent.HELP, "I can help you add, remove, update, or view items in your order."),
    }

    def check(self, message: str):
        normalized = re.sub(r"[^a-z0-9 ]", " ", message.lower())
        normalized = " ".join(normalized.split())
        return self.DEFAULTS.get(normalized)

from pathlib import Path
from fastapi import FastAPI
from app.api.routes.chat import router
from app.clients.grok_client import GroqClient
from app.core.config import get_settings
from app.repositories.menu_repository import MenuRepository
from app.services.chat_service import ChatService
from app.services.initiate_service import InitiateService
from app.services.menu_service import MenuService
from fastapi.middleware.cors import CORSMiddleware
from app.services.session_service import SessionService
import os

settings = get_settings()
menu_repository = MenuRepository(Path(__file__).parent / "data" / "menu.json")
menu_service = MenuService(menu_repository)
session_service = SessionService(settings.session_ttl_minutes)
initiate_service = InitiateService()
grok_client = GroqClient(settings)
chat_service = ChatService(initiate_service, grok_client, menu_service, session_service)
router.chat_service = chat_service


app = FastAPI(title="Gohu-Chatbot", version="1.0.1", debug=False)
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=[
        "X-Session-ID",
    ],
)

app.include_router(router)


@app.get("/health", tags=["system"])
async def health():
    return {"status": "ok", "service": settings.app_name, "version": settings.app_version}

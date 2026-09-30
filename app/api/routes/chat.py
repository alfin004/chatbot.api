from fastapi import APIRouter, Header, HTTPException, Response
from app.models.request import ChatRequest
from app.models.response import ChatResponse

router = APIRouter(prefix="/api/v1", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    response: Response,
    x_tenant_id: str = Header(..., alias="X-Tenant-ID"),
    x_session_id: str | None = Header(None, alias="X-Session-ID"),
):
    if not x_tenant_id.strip():
        raise HTTPException(status_code=400, detail="X-Tenant-ID cannot be empty")
    result: ChatResponse = await router.chat_service.process(x_tenant_id.strip(), x_session_id, payload.message)
    response.headers["X-Session-ID"] = result.session_id
    return result

# Chat Ordering API — Phase 1

A modular FastAPI chatbot-ordering API using:

- FastAPI + Pydantic v2
- Async HTTP client for Grok-compatible intent extraction
- JSON menu repository
- Keyword-based menu resolver
- In-memory tenant/session manager
- Pending clarification state for ambiguous items
- Pytest test suite

The supplied `app/data/menu.json` is the uploaded Thomson's Casa menu and remains the source of truth for item IDs, names, prices, units, availability, stock, categories, and keywords.

## 1. Architecture

```text
POST /api/v1/chat
  -> request validation
  -> tenant/session initialization
  -> default-message detection
  -> Grok intent extraction
  -> menu keyword resolution
  -> exact / ambiguous / not-found decision
  -> stock validation
  -> cart or pending clarification state
  -> standardized response
```

Grok interprets language; the application owns menu truth and cart mutation.

## 2. Headers

### Required

```http
X-Tenant-ID: tenant-001
```

### Optional

```http
X-Session-ID: 6b5f...
```

If `X-Session-ID` is omitted, the API creates a UUID session and returns it in both the JSON response and the `X-Session-ID` response header.

Sessions are isolated by `(tenant_id, session_id)`.

## 3. Request

```http
POST /api/v1/chat
Content-Type: application/json
X-Tenant-ID: tenant-001
X-Session-ID: optional-existing-session
```

```json
{
  "message": "I want 5 chicken 65"
}
```

Messages are trimmed, whitespace-normalized, length-limited to 500 characters, and checked for control characters.

## 4. Default messages

These bypass Grok:

- hi / hello / hey
- thanks / thank you
- bye / goodbye
- help

This saves API calls and gives deterministic responses.

## 5. Intent extraction

Grok is asked to return strict JSON:

```json
{
  "intent": "ADD",
  "items": [
    {
      "name": "chicken biryani",
      "quantity": 5
    }
  ]
}
```

Supported intents are defined in `app/core/constants.py`.

## 6. Menu resolution

The menu service performs case-insensitive normalized keyword/name matching. It returns one of:

- `EXACT`
- `AMBIGUOUS`
- `NOT_FOUND`

The application does not allow an ambiguous item to enter the cart.

## 7. Clarification state

Example:

```text
User: I want 5 biryanis
```

If multiple menu items match `biryani`, the response is:

```json
{
  "success": true,
  "session_id": "...",
  "status": "CLARIFICATION_REQUIRED",
  "intent": "ADD",
  "message": "I found multiple matches for 'biryani'. Which one would you like?",
  "items": [
    {
      "item_id": "...",
      "name": "Veg Biriyani",
      "price": 185
    }
  ]
}
```

The cart is unchanged. The candidate IDs and requested quantity are stored as pending session state. A subsequent selection can resolve the pending request.

This is intentionally atomic: if a multi-item request contains an ambiguous item, the cart is not partially modified.

## 8. Cart

The Phase-1 session store is in memory:

```python
(tenant_id, session_id) -> SessionState
```

A session contains:

```text
cart
pending_action
pending_items
created_at
updated_at
```

Restarting the process clears sessions. The `SessionService` interface is deliberately isolated so Redis can replace it later.

## 9. Stock

If an item has a numeric stock value and the requested quantity exceeds it, nothing is added and the API returns `OUT_OF_STOCK`.

A `null` stock is treated as unlimited/unknown for this test phase; availability is still respected.

## 10. Run locally

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Put the Grok API key in `.env`:

```env
GROK_API_KEY=your-key
```

Start the API:

```powershell
uvicorn app.main:app --reload
```

Open Swagger:

```text
http://127.0.0.1:8000/docs
```

Health check:

```text
GET http://127.0.0.1:8000/health
```

## 11. Example curl

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/chat" \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: tenant-001" \
  -d '{"message":"hello"}'
```

The response contains a generated `session_id` and the HTTP response also contains `X-Session-ID`.

Then reuse it:

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/chat" \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: tenant-001" \
  -H "X-Session-ID: YOUR_SESSION_ID" \
  -d '{"message":"I want 5 chicken 65"}'
```

## 12. Tests

```bash
pytest -q
```

Tests cover:

- default-message handling
- exact menu resolution
- ambiguous biryani resolution
- session creation
- session reuse
- tenant isolation
- atomic clarification behavior

## 13. Folder guide

```text
app/api/routes/chat.py        HTTP endpoint and headers
app/core/config.py            environment configuration
app/core/constants.py         enums/status values
app/models/request.py         request validation
app/models/response.py        response contracts
app/models/intent.py          Grok output contract
app/clients/grok_client.py    async Grok API client
app/repositories/menu_repository.py  JSON menu loading
app/services/initiate_service.py     default messages
app/services/menu_service.py         keyword resolver
app/services/session_service.py      session/cart state
app/services/chat_service.py         orchestration/business flow
app/utils/text_normalizer.py         normalization helpers
app/data/menu.json             test menu
```

## 14. Production evolution

The first replacement should be the in-memory session store with Redis. The menu repository can later become a database-backed repository without changing the HTTP contract. Grok remains behind `GrokClient`, so the LLM provider can also be replaced without changing the chat service.

The API is intentionally Phase 1: checkout, payment, order persistence, authentication, Redis, database transactions, rate limiting, and observability are not implemented yet.

from app.core.constants import ChatStatus, Intent
from app.models.response import ChatResponse, ResponseItem, CartSummary
from app.services.session_service import PendingItem, SessionService, SessionState


class ChatService:
    def __init__(self, initiate, grok, menu, sessions: SessionService):
        self.initiate = initiate
        self.grok = grok
        self.menu = menu
        self.sessions = sessions

    async def process(self, tenant_id: str, session_id: str | None, message: str) -> ChatResponse:
        state, _ = self.sessions.get_or_create(tenant_id, session_id)

        cart = self.sessions.get_cart(
                        tenant_id=tenant_id,
                        session_id=session_id,
                    )

        # A pending clarification gets first opportunity to resolve a user's short selection.
        if state.pending_items:
            pending_response = await self._resolve_pending(state, message)
            if pending_response:
                return pending_response

        default = self.initiate.check(message)
        if default:
            intent, text = default
            return ChatResponse(session_id=state.session_id, status=ChatStatus.COMPLETED, intent=intent, message=text)

        result = await self.grok.extract_intent(message)
        if result.intent == Intent.MENU:
            return ChatResponse(
                success=True,
                session_id=state.session_id,
                status="COMPLETED",
                intent="MENU",
                message="Here is our Menu",
                items=[],
                cart={},
                cartItems=cart,
                metadata={},
                links=[{"label":"View Menu", "url":"http://thomascasa.in"}]
            )
        if result.intent == Intent.ORDER_STATUS:
           return ChatResponse(session_id=state.session_id, status=ChatStatus.UNKNOWN_INTENT, cartItems=cart, intent=result.intent, message="Your order is in progress. Please check with restraunt. ") 
        if result.intent == Intent.LIST:
            
            return ChatResponse(
                success=True,
                session_id=state.session_id,
                status="COMPLETED",
                intent="LIST",
                message="Here is your cart.",
                items=[],
                cart={},
                cartItems=cart,
                metadata={},
            )
        if result.intent == Intent.UNKNOWN:
            return ChatResponse(session_id=state.session_id, status=ChatStatus.UNKNOWN_INTENT, cartItems=cart, intent=result.intent, message="I couldn't understand that request. You can ask me to add, remove, update, or list items.")
        if result.intent not in {Intent.ADD, Intent.REMOVE, Intent.UPDATE}:
            return ChatResponse(session_id=state.session_id, status=ChatStatus.COMPLETED, intent=result.intent, cartItems=cart, message=result.message or "I can help with your order.")
        if not result.items:
            return ChatResponse(session_id=state.session_id, status=ChatStatus.CLARIFICATION_REQUIRED, intent=result.intent, cartItems=cart, message="Which menu item would you like me to process?")

        response = self._process_item_action(state, result.intent, result.items)

        # send updated cart
        cart = self.sessions.get_cart(
                    tenant_id=tenant_id,
                    session_id=session_id,
                )

        response.cartItems = cart
        return response

    def _process_item_action(self, state: SessionState, intent: Intent, requested_items):
        resolved: list[tuple[dict, int]] = []
        ambiguous: list[PendingItem] = []
        not_found: list[str] = []

        for requested in requested_items:
            resolution = self.menu.search(requested.name)
            if resolution.status == "EXACT":
                resolved.append((resolution.candidates[0], requested.quantity))
            elif resolution.status == "AMBIGUOUS":
                ambiguous.append(PendingItem(requested.name, requested.quantity, [x["id"] for x in resolution.candidates]))
            else:
                not_found.append(requested.name)

        # Atomicity: don't partially modify the cart when any part needs clarification or is missing.
        if ambiguous:
            state.pending_action = intent.value
            state.pending_items = ambiguous
            self.sessions.touch(state)
            items = []
            for pending in ambiguous:
                for item_id in pending.candidate_item_ids:
                    item = next((x for x in self.menu.repository.all_items() if x["id"] == item_id), None)
                    if item:
                        items.append(ResponseItem(item_id=item["id"], name=item["name"], price=item.get("price"), unit=item.get("unit"), category=item.get("category")))
            text = "I found multiple options. Please select which item you want:"
            if len(ambiguous) == 1:
                text = f"I found multiple matches for '{ambiguous[0].original_name}'. Which one would you like?"
            return ChatResponse(session_id=state.session_id, status=ChatStatus.CLARIFICATION_REQUIRED, intent=intent, message=text, items=items)

        if not_found:
            return ChatResponse(session_id=state.session_id, status=ChatStatus.ITEM_NOT_FOUND, intent=intent, message=f"I couldn't find: {', '.join(not_found)}. Please choose an item from the menu.")

        if intent == Intent.ADD:
            added = []
            for item, quantity in resolved:
                stock = item.get("stock")
                if stock is not None and quantity > stock:
                    return ChatResponse(session_id=state.session_id, status=ChatStatus.OUT_OF_STOCK, intent=intent, message=f"Only {stock} of {item['name']} are currently available.")
            for item, quantity in resolved:
                cart_item = self.sessions.add_item(state, item, quantity)
                added.append(ResponseItem(item_id=cart_item.item_id, name=cart_item.name, quantity=cart_item.quantity, price=cart_item.price, unit=cart_item.unit, total=round((cart_item.price or 0) * cart_item.quantity, 2), category=cart_item.category))
            return ChatResponse(session_id=state.session_id, status=ChatStatus.COMPLETED, intent=intent, message="Added your requested items to the cart.", items=added, cart=CartSummary(**self.sessions.cart_summary(state)))

        if intent == Intent.UPDATE:
            # Phase 1 semantics: update means set the requested quantity.
            updated = []
            for item, quantity in resolved:
                if item["id"] not in state.cart:
                    return ChatResponse(session_id=state.session_id, status=ChatStatus.ITEM_NOT_FOUND, intent=intent, message=f"{item['name']} is not currently in your cart.")
                if quantity <= 0:
                    state.cart.pop(item["id"])
                else:
                    state.cart[item["id"]].quantity = quantity
                    cart_item = state.cart[item["id"]]
                    updated.append(ResponseItem(item_id=cart_item.item_id, name=cart_item.name, quantity=quantity, price=cart_item.price, unit=cart_item.unit, total=round((cart_item.price or 0) * quantity, 2), category=cart_item.category))
            self.sessions.touch(state)
            return ChatResponse(session_id=state.session_id, status=ChatStatus.COMPLETED, intent=intent, message="Your cart has been updated.", items=updated, cart=CartSummary(**self.sessions.cart_summary(state)))

        # REMOVE: Phase 1 removes the requested quantity; if quantity equals/exceeds current quantity, remove item.
        removed = []
        for item, quantity in resolved:
            cart_item = state.cart.get(item["id"])
            if not cart_item:
                return ChatResponse(session_id=state.session_id, status=ChatStatus.ITEM_NOT_FOUND, intent=intent, message=f"{item['name']} is not currently in your cart.")
            cart_item.quantity -= quantity
            if cart_item.quantity <= 0:
                state.cart.pop(item["id"])
                cart_item.quantity = 0
            removed.append(ResponseItem(item_id=item["id"], name=item["name"], quantity=cart_item.quantity, price=item.get("price"), unit=item.get("unit"), total=round((item.get("price") or 0) * quantity, 2), category=item.get("category")))
        self.sessions.touch(state)
        return ChatResponse(session_id=state.session_id, status=ChatStatus.COMPLETED, intent=intent, message="Your cart has been updated.", items=removed, cart=CartSummary(**self.sessions.cart_summary(state)))

    async def _resolve_pending(self, state: SessionState, message: str):
        # Resolve against the candidate IDs first, so a pending selection is deterministic.
        normalized = message.lower().strip()
        matches = []
        all_items = {x["id"]: x for x in self.menu.repository.all_items()}
        for pending in state.pending_items:
            for item_id in pending.candidate_item_ids:
                item = all_items.get(item_id)
                if not item:
                    continue
                name = item["name"].lower()
                if normalized == name or normalized in name or any(token == normalized for token in item.get("keywords", [])):
                    matches.append((item, pending.quantity, pending.original_name))
        if not matches:
            # A new full natural-language request can be sent through Grok normally.
            return None
        if len(matches) > 1:
            return ChatResponse(session_id=state.session_id, status=ChatStatus.CLARIFICATION_REQUIRED, intent=Intent(state.pending_action or "ADD"), message="Please select one of the displayed options.")

        item, quantity, _ = matches[0]
        intent = Intent(state.pending_action or "ADD")
        self.sessions.clear_pending(state)
        return self._process_item_action(state, intent, [type("Req", (), {"name": item["name"], "quantity": quantity})()])

    def _list_menu(self, state: SessionState):
        items = [ResponseItem(item_id=x["id"], name=x["name"], price=x.get("price"), unit=x.get("unit"), category=x.get("category")) for x in self.menu.repository.all_items() if x.get("available", True)]
        return ChatResponse(session_id=state.session_id, status=ChatStatus.COMPLETED, intent=Intent.LIST, message="Here is the available menu.", items=items)

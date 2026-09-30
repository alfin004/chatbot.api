from app.services.session_service import SessionService


def test_missing_session_creates_session():
    service = SessionService()
    state, created = service.get_or_create("tenant-a", None)
    assert created is True
    assert state.session_id


def test_same_tenant_session_is_reused():
    service = SessionService()
    state1, _ = service.get_or_create("tenant-a", "session-1")
    state2, created = service.get_or_create("tenant-a", "session-1")
    assert created is False
    assert state1 is state2


def test_tenants_are_isolated():
    service = SessionService()
    state1, _ = service.get_or_create("tenant-a", "session-1")
    state2, _ = service.get_or_create("tenant-b", "session-1")
    assert state1 is not state2

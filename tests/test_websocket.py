import uuid

import pytest
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.core.security import create_access_token
from app.main import app


def _make_token(user_id: str | None = None) -> str:
    sub = user_id or str(uuid.uuid4())
    return create_access_token({"sub": sub})


def test_ws_connect_valid_token():
    token = _make_token()
    with TestClient(app) as client:
        with client.websocket_connect(f"/api/v1/ws?token={token}") as ws:
            ws.send_text("ping")
            # Connection stays open — no exception means success


def test_ws_connect_invalid_token():
    with TestClient(app) as client:
        with client.websocket_connect("/api/v1/ws?token=not.a.real.token") as ws:
            with pytest.raises(Exception):
                ws.receive_text()


def test_ws_connect_missing_token():
    with TestClient(app) as client:
        with pytest.raises(Exception):
            with client.websocket_connect("/api/v1/ws") as ws:
                ws.receive_text()

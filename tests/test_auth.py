from httpx import AsyncClient

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
REFRESH_URL = "/api/v1/auth/refresh"
ME_URL = "/api/v1/auth/me"


# ── Register ─────────────────────────────────────────────────────────────────

async def test_register_success(async_client: AsyncClient):
    resp = await async_client.post(REGISTER_URL, json={
        "email": "newuser@example.com",
        "password": "SecurePass1!",
        "full_name": "New User",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


async def test_register_duplicate_email(async_client: AsyncClient):
    payload = {"email": "dup@example.com", "password": "SecurePass1!", "full_name": "Dup"}
    await async_client.post(REGISTER_URL, json=payload)
    resp = await async_client.post(REGISTER_URL, json=payload)
    assert resp.status_code == 409


async def test_register_weak_password(async_client: AsyncClient):
    resp = await async_client.post(REGISTER_URL, json={
        "email": "weak@example.com",
        "password": "short",
        "full_name": "Weak",
    })
    assert resp.status_code == 422


async def test_register_invalid_email(async_client: AsyncClient):
    resp = await async_client.post(REGISTER_URL, json={
        "email": "not-an-email",
        "password": "SecurePass1!",
        "full_name": "Bad Email",
    })
    assert resp.status_code == 422


# ── Login ─────────────────────────────────────────────────────────────────────

async def test_login_success(async_client: AsyncClient):
    await async_client.post(REGISTER_URL, json={
        "email": "login@example.com",
        "password": "SecurePass1!",
        "full_name": "Login User",
    })
    resp = await async_client.post(LOGIN_URL, json={
        "email": "login@example.com",
        "password": "SecurePass1!",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data


async def test_login_wrong_password(async_client: AsyncClient):
    await async_client.post(REGISTER_URL, json={
        "email": "wrongpw@example.com",
        "password": "SecurePass1!",
        "full_name": "Wrong PW",
    })
    resp = await async_client.post(LOGIN_URL, json={
        "email": "wrongpw@example.com",
        "password": "WrongPassword!",
    })
    assert resp.status_code == 401


async def test_login_nonexistent_email(async_client: AsyncClient):
    resp = await async_client.post(LOGIN_URL, json={
        "email": "nobody@example.com",
        "password": "SecurePass1!",
    })
    assert resp.status_code == 401


# ── Refresh ───────────────────────────────────────────────────────────────────

async def test_refresh_token_success(async_client: AsyncClient):
    reg = await async_client.post(REGISTER_URL, json={
        "email": "refresh@example.com",
        "password": "SecurePass1!",
        "full_name": "Refresh User",
    })
    refresh_token = reg.json()["refresh_token"]
    resp = await async_client.post(REFRESH_URL, json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data


async def test_refresh_with_access_token(async_client: AsyncClient):
    """Passing an access token to /refresh must fail (wrong token type)."""
    reg = await async_client.post(REGISTER_URL, json={
        "email": "wrongtype@example.com",
        "password": "SecurePass1!",
        "full_name": "Wrong Type",
    })
    access_token = reg.json()["access_token"]
    resp = await async_client.post(REFRESH_URL, json={"refresh_token": access_token})
    assert resp.status_code == 401


async def test_refresh_invalid_token(async_client: AsyncClient):
    resp = await async_client.post(REFRESH_URL, json={"refresh_token": "this.is.garbage"})
    assert resp.status_code == 401


# ── /me GET ───────────────────────────────────────────────────────────────────

async def test_get_me_authenticated(async_client: AsyncClient, buyer_token: str):
    resp = await async_client.get(ME_URL, headers={"Authorization": f"Bearer {buyer_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "buyer@test.com"
    assert data["role"] == "buyer"


async def test_get_me_unauthenticated(async_client: AsyncClient):
    resp = await async_client.get(ME_URL)
    assert resp.status_code == 401


async def test_get_me_inactive_user(async_client: AsyncClient, inactive_buyer_token: str):
    resp = await async_client.get(ME_URL, headers={"Authorization": f"Bearer {inactive_buyer_token}"})
    assert resp.status_code == 403


# ── /me PATCH ─────────────────────────────────────────────────────────────────

async def test_update_me_full_name(async_client: AsyncClient, buyer_token: str):
    resp = await async_client.patch(
        ME_URL,
        json={"full_name": "Updated Name"},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["full_name"] == "Updated Name"


async def test_update_me_password(async_client: AsyncClient):
    """After updating password, old password fails and new password works."""
    reg = await async_client.post(REGISTER_URL, json={
        "email": "pwchange@example.com",
        "password": "OldPass123!",
        "full_name": "PW Change",
    })
    token = reg.json()["access_token"]

    patch_resp = await async_client.patch(
        ME_URL,
        json={"password": "NewPass456!"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert patch_resp.status_code == 200

    old_resp = await async_client.post(LOGIN_URL, json={
        "email": "pwchange@example.com",
        "password": "OldPass123!",
    })
    assert old_resp.status_code == 401

    new_resp = await async_client.post(LOGIN_URL, json={
        "email": "pwchange@example.com",
        "password": "NewPass456!",
    })
    assert new_resp.status_code == 200


async def test_login_deactivated_account(async_client: AsyncClient):
    await async_client.post(REGISTER_URL, json={
        "email": "deactivated@example.com",
        "password": "SecurePass1!",
        "full_name": "Deactivated User",
    })
    from tests.conftest import TestSessionLocal
    from app.crud.user import deactivate_user, get_user_by_email
    async with TestSessionLocal() as db:
        user = await get_user_by_email(db, "deactivated@example.com")
        await deactivate_user(db, user.id)

    resp = await async_client.post(LOGIN_URL, json={
        "email": "deactivated@example.com",
        "password": "SecurePass1!",
    })
    assert resp.status_code == 403


async def test_login_rate_limiting(async_client: AsyncClient):
    """After 5 failed attempts from the same IP, the 6th attempt should be rate-limited."""
    for _ in range(5):
        await async_client.post(LOGIN_URL, json={
            "email": "nobody@example.com",
            "password": "WrongPass!",
        })
    resp = await async_client.post(LOGIN_URL, json={
        "email": "nobody@example.com",
        "password": "WrongPass!",
    })
    assert resp.status_code == 429


async def test_logout(async_client: AsyncClient, buyer_token: str):
    resp = await async_client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["message"] == "Logged out successfully"

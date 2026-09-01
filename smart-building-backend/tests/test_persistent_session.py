"""A session lasts until the user signs out or the refresh token stops working.

The access token is deliberately short-lived; the refresh token is what keeps
someone signed in. These tests pin the server side of that contract: rotation
works, logout really revokes, a disabled account cannot refresh, and a replayed
token is treated as theft.
"""

from datetime import timedelta

import pytest

from conftest import BOOTSTRAP_MOBILE, login_with_otp

from app.database import get_session
from app.models import AuthSession, User
from app.services.security import (
    access_token_ttl_seconds,
    refresh_token_ttl_seconds,
    utc_now,
)


def _login(client, mobile):
    requested = client.post("/auth/otp/request", json={"mobile": mobile})
    assert requested.status_code == 200
    body = requested.json()
    verified = client.post(
        "/auth/otp/verify",
        json={"request_id": body["request_id"], "code": body["debug_code"]},
    )
    assert verified.status_code == 200
    return verified.json()


# ------------------------------------------------------------------- lifetimes


def test_the_refresh_token_outlives_the_access_token_by_far():
    access = access_token_ttl_seconds()
    refresh = refresh_token_ttl_seconds()
    assert access <= 3600, "the access token is meant to be short-lived"
    assert refresh >= 7 * 24 * 3600, "the refresh token is what keeps a session alive"
    assert refresh > access * 100


def test_login_returns_both_tokens_and_their_lifetimes(client):
    payload = _login(client, BOOTSTRAP_MOBILE)
    assert payload["access_token"]
    assert payload["refresh_token"]
    assert payload["expires_in"] == access_token_ttl_seconds()
    assert payload["refresh_expires_in"] == refresh_token_ttl_seconds()


# ---------------------------------------------------------- refresh keeps you in


def test_an_expired_access_token_is_renewed_without_signing_in_again(client):
    payload = _login(client, BOOTSTRAP_MOBILE)
    stale = {"Authorization": f"Bearer {payload['access_token']}"}

    # Age the access token past its expiry, exactly as time would.
    with get_session() as db:
        session_row = db.query(AuthSession).order_by(AuthSession.id.desc()).first()
        session_row.expires_at = utc_now() - timedelta(seconds=1)
        db.commit()

    assert client.get("/auth/me", headers=stale).status_code == 401

    refreshed = client.post(
        "/auth/refresh", json={"refresh_token": payload["refresh_token"]}
    )
    assert refreshed.status_code == 200, "a valid refresh token must revive the session"
    fresh = {"Authorization": f"Bearer {refreshed.json()['access_token']}"}
    assert client.get("/auth/me", headers=fresh).status_code == 200


def test_refresh_rotates_both_tokens(client):
    payload = _login(client, BOOTSTRAP_MOBILE)
    refreshed = client.post(
        "/auth/refresh", json={"refresh_token": payload["refresh_token"]}
    ).json()

    assert refreshed["access_token"] != payload["access_token"]
    assert refreshed["refresh_token"] != payload["refresh_token"]


def test_a_session_survives_repeated_refreshes(client):
    """Simulates coming back day after day without signing in again."""
    payload = _login(client, BOOTSTRAP_MOBILE)
    token = payload["refresh_token"]

    for _ in range(5):
        response = client.post("/auth/refresh", json={"refresh_token": token})
        assert response.status_code == 200
        token = response.json()["refresh_token"]

    final = {"Authorization": f"Bearer {response.json()['access_token']}"}
    assert client.get("/auth/me", headers=final).status_code == 200


# -------------------------------------------------------------- session ends


def test_logout_revokes_the_refresh_token(client):
    payload = _login(client, BOOTSTRAP_MOBILE)
    headers = {"Authorization": f"Bearer {payload['access_token']}"}

    assert client.post(
        "/auth/logout",
        json={"refresh_token": payload["refresh_token"]},
        headers=headers,
    ).status_code == 204

    assert client.get("/auth/me", headers=headers).status_code == 401
    reused = client.post(
        "/auth/refresh", json={"refresh_token": payload["refresh_token"]}
    )
    assert reused.status_code == 401, "logout must make the refresh token useless"


def test_an_expired_refresh_token_is_refused(client):
    payload = _login(client, BOOTSTRAP_MOBILE)

    with get_session() as db:
        session_row = db.query(AuthSession).order_by(AuthSession.id.desc()).first()
        session_row.refresh_expires_at = utc_now() - timedelta(seconds=1)
        db.commit()

    response = client.post(
        "/auth/refresh", json={"refresh_token": payload["refresh_token"]}
    )
    assert response.status_code == 401
    # The backend distinguishes an expired token from an invalid one, which is
    # more informative than the generic refusal.
    assert response.json()["code"] == "REFRESH_TOKEN_EXPIRED"


def test_a_disabled_account_cannot_refresh(client):
    payload = _login(client, BOOTSTRAP_MOBILE)

    with get_session() as db:
        user = db.query(User).filter(User.mobile == "+989150000000").one()
        user.is_active = False
        db.commit()

    response = client.post(
        "/auth/refresh", json={"refresh_token": payload["refresh_token"]}
    )
    assert response.status_code == 401, "a disabled account must not be revived"


def test_replaying_a_rotated_token_revokes_every_session(client):
    """Theft protection: the old token is a signal, not just an error."""
    payload = _login(client, BOOTSTRAP_MOBILE)
    rotated = client.post(
        "/auth/refresh", json={"refresh_token": payload["refresh_token"]}
    ).json()

    replayed = client.post(
        "/auth/refresh", json={"refresh_token": payload["refresh_token"]}
    )
    assert replayed.status_code == 401

    # The session that legitimately rotated is revoked too.
    current = {"Authorization": f"Bearer {rotated['access_token']}"}
    assert client.get("/auth/me", headers=current).status_code == 401

    with get_session() as db:
        live = (
            db.query(AuthSession)
            .join(User, User.id == AuthSession.user_id)
            .filter(User.mobile == "+989150000000", AuthSession.revoked_at.is_(None))
            .count()
        )
        assert live == 0


def test_a_token_is_never_accepted_from_the_url(client):
    payload = _login(client, BOOTSTRAP_MOBILE)
    response = client.get(f"/auth/me?access_token={payload['access_token']}")
    assert response.status_code == 401, "credentials belong in the header only"

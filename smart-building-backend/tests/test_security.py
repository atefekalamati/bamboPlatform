from conftest import BOOTSTRAP_MOBILE, login_with_otp


def test_otp_login_masks_mobile_and_logout_revokes_session(client):
    headers = login_with_otp(client, BOOTSTRAP_MOBILE)

    me = client.get("/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["mobile"] == "+989***0000"
    assert "super_admin" in {role["name"] for role in me.json()["roles"]}
    assert "roles.manage" in me.json()["permissions"]

    logout = client.post("/auth/logout", headers=headers)
    assert logout.status_code == 204
    assert client.get("/auth/me", headers=headers).status_code == 401


def test_otp_attempt_limit_and_request_rate_limit(client, monkeypatch):
    request_body = client.post("/auth/otp/request", json={"mobile": "09151111111"}).json()
    wrong_code = "111111" if request_body["debug_code"] == "000000" else "000000"
    for _ in range(5):
        response = client.post(
            "/auth/otp/verify",
            json={"request_id": request_body["request_id"], "code": wrong_code},
        )
        assert response.status_code == 400
        assert response.json()["code"] == "OTP_INVALID"

    locked = client.post(
        "/auth/otp/verify",
        json={"request_id": request_body["request_id"], "code": request_body["debug_code"]},
    )
    assert locked.status_code == 400

    monkeypatch.setenv("OTP_RESEND_COOLDOWN_SECONDS", "0")
    for index in range(2):
        assert (
            client.post("/auth/otp/request", json={"mobile": f"0915222222{index}"}).status_code
            == 200
        )
    mobile = "09153333333"
    for _ in range(3):
        assert client.post("/auth/otp/request", json={"mobile": mobile}).status_code == 200
    limited = client.post("/auth/otp/request", json={"mobile": mobile})
    assert limited.status_code == 429
    assert limited.json()["code"] == "OTP_RATE_LIMITED"
    assert limited.json()["retry_after"] > 0


def test_permission_toggle_applies_to_existing_session(client, super_admin_headers):
    role_response = client.post(
        "/roles",
        json={"name": "viewer", "display_name": "مشاهده‌گر"},
        headers=super_admin_headers,
    )
    assert role_response.status_code == 201
    role_id = role_response.json()["id"]

    read_only = client.put(
        f"/roles/{role_id}/permissions",
        json={"permission_codes": ["pilots.read"]},
        headers=super_admin_headers,
    )
    assert read_only.status_code == 200

    created_user = client.post(
        "/users",
        json={
            "mobile": "09154444444",
            "display_name": "کاربر مشاهده‌گر",
            "role_ids": [role_id],
        },
        headers=super_admin_headers,
    )
    assert created_user.status_code == 201
    viewer_headers = login_with_otp(client, "09154444444")

    assert client.get("/pilots", headers=viewer_headers).status_code == 200
    denied = client.post(
        "/pilots",
        json={"display_name": "پایلوت غیرمجاز", "pilot_year": 1405},
        headers=viewer_headers,
    )
    assert denied.status_code == 403
    assert denied.json()["errors"] == [{"permission": "pilots.create"}]

    toggled = client.put(
        f"/roles/{role_id}/permissions",
        json={"permission_codes": ["pilots.read", "pilots.create"]},
        headers=super_admin_headers,
    )
    assert toggled.status_code == 200

    allowed = client.post(
        "/pilots",
        json={"display_name": "پایلوت مجاز", "pilot_year": 1405},
        headers=viewer_headers,
    )
    assert allowed.status_code == 201


def test_sensitive_permission_confirmation_and_last_super_admin(client, super_admin_headers):
    role = client.post(
        "/roles",
        json={"name": "operator_admin", "display_name": "مدیر عملیات"},
        headers=super_admin_headers,
    ).json()
    unconfirmed = client.put(
        f"/roles/{role['id']}/permissions",
        json={"permission_codes": ["users.manage"]},
        headers=super_admin_headers,
    )
    assert unconfirmed.status_code == 422
    assert unconfirmed.json()["code"] == "CONFIRMATION_REQUIRED"

    confirmed = client.put(
        f"/roles/{role['id']}/permissions",
        json={"permission_codes": ["users.manage"], "confirmed": True},
        headers=super_admin_headers,
    )
    assert confirmed.status_code == 200

    me = client.get("/auth/me", headers=super_admin_headers).json()
    disable_last = client.patch(
        f"/users/{me['id']}/status",
        json={"is_active": False, "reason": "آزمون", "confirmed": True},
        headers=super_admin_headers,
    )
    assert disable_last.status_code == 409
    assert disable_last.json()["code"] == "LAST_SUPER_ADMIN"

    audit = client.get("/audit", headers=super_admin_headers)
    assert audit.status_code == 200
    assert any(item["action"] == "roles.permissions_updated" for item in audit.json())


def test_delegated_admin_cannot_escalate_privileges(client, super_admin_headers):
    roles = client.get("/roles", headers=super_admin_headers).json()
    super_admin_role_id = next(role["id"] for role in roles if role["name"] == "super_admin")

    delegated_role = client.post(
        "/roles",
        json={"name": "delegated_admin", "display_name": "ادمین محدود"},
        headers=super_admin_headers,
    ).json()
    delegated_role = client.put(
        f"/roles/{delegated_role['id']}/permissions",
        json={
            "permission_codes": [
                "users.read",
                "users.manage",
                "roles.read",
                "roles.manage",
            ],
            "confirmed": True,
        },
        headers=super_admin_headers,
    ).json()
    delegated_user = client.post(
        "/users",
        json={
            "mobile": "09156666666",
            "display_name": "ادمین محدود",
            "role_ids": [delegated_role["id"]],
        },
        headers=super_admin_headers,
    )
    assert delegated_user.status_code == 201
    delegated_headers = login_with_otp(client, "09156666666")

    grant_super_admin = client.post(
        "/users",
        json={
            "mobile": "09157777777",
            "display_name": "کاربر هدف",
            "role_ids": [super_admin_role_id],
        },
        headers=delegated_headers,
    )
    assert grant_super_admin.status_code == 403
    assert grant_super_admin.json()["code"] == "PRIVILEGE_ESCALATION_DENIED"

    grant_unowned_permission = client.put(
        f"/roles/{delegated_role['id']}/permissions",
        json={
            "permission_codes": [
                "users.read",
                "users.manage",
                "roles.read",
                "roles.manage",
                "audit.read",
            ],
            "confirmed": True,
        },
        headers=delegated_headers,
    )
    assert grant_unowned_permission.status_code == 403
    assert grant_unowned_permission.json()["code"] == "PRIVILEGE_ESCALATION_DENIED"


def test_production_rejects_unconfigured_otp_provider(client, monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    response = client.post("/auth/otp/request", json={"mobile": "09158888888"})
    assert response.status_code == 503
    assert response.json()["code"] == "OTP_PROVIDER_UNAVAILABLE"
    assert "debug_code" not in response.json()

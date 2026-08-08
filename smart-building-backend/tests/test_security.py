from conftest import BOOTSTRAP_MOBILE, login_with_otp, sample_pilot_payload
from app.auth.policies import can_review_stage


def _create_profile_test_user(client, super_admin_headers, mobile="09151234567"):
    role = next(item for item in client.get("/roles", headers=super_admin_headers).json() if item["name"] == "sales")
    response = client.post(
        "/users",
        json={"mobile": mobile, "display_name": "کاربر اولیه", "role_ids": [role["id"]]},
        headers=super_admin_headers,
    )
    assert response.status_code == 201
    return response.json()


def test_super_admin_updates_user_name_mobile_and_persists(client, super_admin_headers):
    from app.database import get_session
    from app.models import AuditLog, User

    user = _create_profile_test_user(client, super_admin_headers)
    updated = client.patch(
        f"/users/{user['id']}",
        json={"display_name": "  نام ویرایش شده  ", "mobile": "09157654321"},
        headers=super_admin_headers,
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["display_name"] == "نام ویرایش شده"
    assert updated.json()["mobile"] == "+989***4321"
    with get_session() as db:
        stored = db.get(User, user["id"])
        assert stored.display_name == "نام ویرایش شده"
        assert stored.mobile == "+989157654321"
        audit = db.query(AuditLog).filter(AuditLog.action == "users.profile_updated", AuditLog.entity_id == str(user["id"])).one()
        assert audit.new_data["changed_fields"] == ["display_name", "mobile"]
        assert audit.old_data["mobile"] != "+989151234567"
        assert audit.new_data["mobile"] != "+989157654321"
    assert login_with_otp(client, "09157654321")["Authorization"].startswith("Bearer ")


def test_user_updates_only_own_name_and_phone_change_requires_verification(client, super_admin_headers):
    user = _create_profile_test_user(client, super_admin_headers)
    other = _create_profile_test_user(client, super_admin_headers, "09151234568")
    headers = login_with_otp(client, "09151234567")
    own = client.patch("/auth/me", json={"display_name": "  نام شخصی  "}, headers=headers)
    assert own.status_code == 200
    assert own.json()["display_name"] == "نام شخصی"
    same_phone = client.patch("/auth/me", json={"mobile": "09151234567"}, headers=headers)
    assert same_phone.status_code == 200
    blocked_phone = client.patch("/auth/me", json={"mobile": "09150001111"}, headers=headers)
    assert blocked_phone.status_code == 409
    assert blocked_phone.json()["code"] == "PHONE_CHANGE_VERIFICATION_REQUIRED"
    forbidden = client.patch(f"/users/{other['id']}", json={"display_name": "نفوذ"}, headers=headers)
    assert forbidden.status_code == 403


def test_user_profile_validation_duplicate_mass_assignment_and_missing_user(client, super_admin_headers):
    first = _create_profile_test_user(client, super_admin_headers)
    second = _create_profile_test_user(client, super_admin_headers, "09151234568")
    assert client.patch(f"/users/{first['id']}", json={}, headers=super_admin_headers).status_code == 422
    assert client.patch(f"/users/{first['id']}", json={"display_name": "   "}, headers=super_admin_headers).status_code == 422
    assert client.patch(f"/users/{first['id']}", json={"mobile": "123"}, headers=super_admin_headers).status_code == 422
    duplicate = client.patch(f"/users/{first['id']}", json={"mobile": "09151234568"}, headers=super_admin_headers)
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "USER_MOBILE_ALREADY_EXISTS"
    assert client.patch(f"/users/{first['id']}", json={"is_active": False}, headers=super_admin_headers).status_code == 422
    assert client.patch("/users/999999", json={"display_name": "کاربر ناموجود"}, headers=super_admin_headers).status_code == 404
    assert client.patch(f"/users/{second['id']}", json={"display_name": "بدون ورود"}).status_code == 401


def test_stage_reviewer_policy_allows_general_manager_as_substitute():
    assert can_review_stage({"super_admin"}, 6, "approve") is True
    assert can_review_stage({"super_admin"}, 9, "reject") is True
    assert can_review_stage({"operations"}, 6, "approve") is True
    assert can_review_stage({"capture_expert"}, 6, "approve") is False
    assert can_review_stage({"operations"}, 1, "approve") is False
    assert can_review_stage({"super_admin"}, 20, "approve") is False


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


def test_user_preferences_are_persisted_and_audited(client, super_admin_headers):
    defaults = client.get("/auth/preferences", headers=super_admin_headers)
    assert defaults.status_code == 200
    assert defaults.json()["theme"] == "light"
    assert defaults.json()["timezone"] == "Asia/Tehran"
    assert defaults.json()["calendar"] == "jalali"

    updated = client.patch(
        "/auth/preferences",
        json={
            "theme": "dark",
            "calendar": "jalali",
            "page_size": 50,
            "last_page": "#/pilots/1/stages/10",
        },
        headers=super_admin_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["theme"] == "dark"
    assert updated.json()["page_size"] == 50

    reread = client.get("/auth/preferences", headers=super_admin_headers)
    assert reread.status_code == 200
    assert reread.json()["theme"] == "dark"
    assert reread.json()["last_page"] == "#/pilots/1/stages/10"

    invalid = client.patch(
        "/auth/preferences",
        json={"calendar": "lunar"},
        headers=super_admin_headers,
    )
    assert invalid.status_code == 422

    audit = client.get(
        "/audit",
        params={"action": "users.preferences_updated"},
        headers=super_admin_headers,
    )
    assert audit.status_code == 200
    assert audit.json()[0]["entity_type"] == "UserPreference"


def test_auth_bootstrap_returns_access_matrix(client, super_admin_headers):
    response = client.get("/auth/bootstrap", headers=super_admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["user"]["id"]
    assert "roles.manage" in body["permissions"]
    assert body["scopes"] == ["ALL"]
    assert body["menu_access"] == ["*"]
    assert 17 in body["stage_access"]["approve"]
    assert "G5" in body["gate_access"]["override"]
    assert body["preferences"]["calendar"] == "jalali"


def test_permission_groups_and_role_access_preview_expose_granular_rbac(
    client,
    super_admin_headers,
):
    groups = client.get("/roles/permissions/groups", headers=super_admin_headers)
    assert groups.status_code == 200
    permissions_by_group = {
        group["group_name"]: {permission["code"] for permission in group["permissions"]}
        for group in groups.json()
    }
    assert "stages.submit" in permissions_by_group["Stages"]
    assert "gates.override" in permissions_by_group["Gates"]
    assert "users.assign_roles" in permissions_by_group["Users"]

    roles = client.get("/roles", headers=super_admin_headers).json()
    capture_role = next(role for role in roles if role["name"] == "capture_expert")
    preview = client.get(
        f"/roles/{capture_role['id']}/access-preview",
        headers=super_admin_headers,
    )
    assert preview.status_code == 200
    body = preview.json()
    assert body["roles"][0]["official_code"] == "FIELD_EXPERT"
    assert set(body["stage_access"]["edit"]) == {6, 7, 8, 9}
    assert set(body["stage_access"]["submit"]) == {6, 7, 8, 9}
    assert body["stage_access"]["approve"] == []
    assert body["gate_access"]["approve"] == []
    assert body["scopes"] == ["ASSIGNED"]


def test_role_clone_and_effective_permissions(client, super_admin_headers):
    roles = client.get("/roles", headers=super_admin_headers).json()
    sales_role = next(role for role in roles if role["name"] == "sales")

    cloned = client.post(
        f"/roles/{sales_role['id']}/clone",
        json={"name": "sales_shadow", "display_name": "فروش پشتیبان"},
        headers=super_admin_headers,
    )
    assert cloned.status_code == 201
    cloned_body = cloned.json()
    assert cloned_body["is_system"] is False
    assert "commercial.create_proposal" in {
        permission["code"] for permission in cloned_body["permissions"]
    }

    effective = client.get(
        f"/roles/{cloned_body['id']}/effective-permissions",
        headers=super_admin_headers,
    )
    assert effective.status_code == 200
    assert "stages.submit" in effective.json()["permissions"]


def test_parallel_session_policy_and_session_isolation(client, monkeypatch):
    monkeypatch.setenv("OTP_RESEND_COOLDOWN_SECONDS", "0")

    first_session = login_with_otp(client, "09151000001")
    second_session = login_with_otp(client, "09151000001")
    other_user_session = login_with_otp(client, "09151000002")

    assert first_session != second_session
    assert client.get("/auth/me", headers=first_session).status_code == 200
    assert client.get("/auth/me", headers=second_session).status_code == 200
    assert client.get("/auth/me", headers=other_user_session).status_code == 200

    assert client.post("/auth/logout", headers=first_session).status_code == 204
    assert client.get("/auth/me", headers=first_session).status_code == 401
    assert client.get("/auth/me", headers=second_session).status_code == 200
    assert client.get("/auth/me", headers=other_user_session).status_code == 200


def test_otp_is_single_use(client):
    requested = client.post(
        "/auth/otp/request",
        json={"mobile": "09151000003"},
    ).json()
    payload = {
        "request_id": requested["request_id"],
        "code": requested["debug_code"],
    }

    assert client.post("/auth/otp/verify", json=payload).status_code == 200
    replayed = client.post("/auth/otp/verify", json=payload)
    assert replayed.status_code == 400
    assert replayed.json()["code"] == "OTP_INVALID"


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
        json=sample_pilot_payload(),
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
        json=sample_pilot_payload(),
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


def test_audit_pagination_and_filters(client, super_admin_headers):
    me = client.get("/auth/me", headers=super_admin_headers).json()
    first_role = client.post(
        "/roles",
        json={"name": "audit_filter_one", "display_name": "ممیزی یک"},
        headers=super_admin_headers,
    )
    second_role = client.post(
        "/roles",
        json={"name": "audit_filter_two", "display_name": "ممیزی دو"},
        headers=super_admin_headers,
    )
    assert first_role.status_code == 201
    assert second_role.status_code == 201

    filtered = client.get(
        "/audit",
        params={
            "action": "roles.created",
            "entity_type": "Role",
            "actor_user_id": me["id"],
        },
        headers=super_admin_headers,
    )
    assert filtered.status_code == 200
    filtered_items = filtered.json()
    created_role_ids = {str(first_role.json()["id"]), str(second_role.json()["id"])}
    assert created_role_ids.issubset({item["entity_id"] for item in filtered_items})
    assert all(item["action"] == "roles.created" for item in filtered_items)
    assert all(item["entity_type"] == "Role" for item in filtered_items)
    assert all(item["actor_user_id"] == me["id"] for item in filtered_items)

    first_page = client.get(
        "/audit",
        params={"action": "roles.created", "limit": 1, "offset": 0},
        headers=super_admin_headers,
    )
    second_page = client.get(
        "/audit",
        params={"action": "roles.created", "limit": 1, "offset": 1},
        headers=super_admin_headers,
    )
    assert first_page.status_code == 200
    assert second_page.status_code == 200
    assert len(first_page.json()) == len(second_page.json()) == 1
    assert first_page.json()[0]["id"] > second_page.json()[0]["id"]

    exact_entity = client.get(
        "/audit",
        params={"entity_type": "Role", "entity_id": str(first_role.json()["id"])},
        headers=super_admin_headers,
    )
    assert exact_entity.status_code == 200
    assert exact_entity.json()
    assert all(
        item["entity_type"] == "Role"
        and item["entity_id"] == str(first_role.json()["id"])
        for item in exact_entity.json()
    )

    invalid_range = client.get(
        "/audit",
        params={
            "created_from": "2027-01-02T00:00:00+00:00",
            "created_to": "2027-01-01T00:00:00+00:00",
        },
        headers=super_admin_headers,
    )
    assert invalid_range.status_code == 422
    assert invalid_range.json()["code"] == "AUDIT_DATE_RANGE_INVALID"

    missing_timezone = client.get(
        "/audit",
        params={"created_from": "2027-01-01T00:00:00"},
        headers=super_admin_headers,
    )
    assert missing_timezone.status_code == 422
    assert missing_timezone.json()["code"] == "AUDIT_TIMEZONE_REQUIRED"


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


def test_custom_role_can_be_deleted_only_when_unassigned(
    client, super_admin_headers
):
    role = client.post(
        "/roles",
        json={"name": "temporary_role", "display_name": "نقش موقت"},
        headers=super_admin_headers,
    ).json()
    user = client.post(
        "/users",
        json={
            "mobile": "09159999999",
            "display_name": "کاربر نقش موقت",
            "role_ids": [role["id"]],
        },
        headers=super_admin_headers,
    )
    assert user.status_code == 201
    in_use = client.delete(
        f"/roles/{role['id']}",
        headers=super_admin_headers,
    )
    assert in_use.status_code == 409
    assert in_use.json()["code"] == "ROLE_IN_USE"

    cleared = client.put(
        f"/users/{user.json()['id']}/roles",
        json={"role_ids": [], "confirmed": True},
        headers=super_admin_headers,
    )
    assert cleared.status_code == 200
    deleted = client.delete(
        f"/roles/{role['id']}",
        headers=super_admin_headers,
    )
    assert deleted.status_code == 204
    audit = client.get("/audit", headers=super_admin_headers).json()
    assert any(
        item["action"] == "roles.deleted"
        and item["old_data"]["name"] == "temporary_role"
        for item in audit
    )

    system_role = next(
        role
        for role in client.get("/roles", headers=super_admin_headers).json()
        if role["is_system"]
    )
    denied = client.delete(
        f"/roles/{system_role['id']}",
        headers=super_admin_headers,
    )
    assert denied.status_code == 409
    assert denied.json()["code"] == "SYSTEM_ROLE_DELETE_DENIED"

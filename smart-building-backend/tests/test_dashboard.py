from conftest import login_with_otp, sample_pilot_payload


def test_dashboard_summary_and_pilot_list(client, super_admin_headers):
    created = client.post("/pilots", json=sample_pilot_payload(), headers=super_admin_headers)
    assert created.status_code == 201

    summary = client.get("/api/v1/dashboard/summary", headers=super_admin_headers)
    assert summary.status_code == 200
    body = summary.json()
    assert body["state"] == "SUCCESS"
    assert body["summary"]["total_pilots"] == 1
    assert body["summary"]["active"] == 1

    listing = client.get("/api/v1/dashboard/pilots?page=1&page_size=10", headers=super_admin_headers)
    assert listing.status_code == 200
    assert listing.json()["pagination"]["total"] == 1
    assert listing.json()["items"][0]["progress_percent"] == round(100 / 19, 2)


def test_dashboard_sections_and_actions(client, super_admin_headers):
    created = client.post("/pilots", json=sample_pilot_payload(), headers=super_admin_headers)
    assert created.status_code == 201
    for section in ("stages", "gates", "missions", "incidents", "sla", "forms", "commercial", "activities"):
        response = client.get(f"/api/v1/dashboard/{section}", headers=super_admin_headers)
        assert response.status_code == 200, response.text
        assert response.json()["state"] == "SUCCESS"
    actions = client.get("/api/v1/dashboard/my-actions", headers=super_admin_headers)
    assert actions.status_code == 200
    assert actions.json()["items"][0]["entity_type"] == "stage"


def test_dashboard_requires_permission_and_embed_never_exposes_secret(client, super_admin_headers):
    no_auth = client.get("/api/v1/dashboard/summary")
    assert no_auth.status_code == 401
    embed = client.get("/api/v1/dashboard/powerbi/embed-token", headers=super_admin_headers)
    assert embed.status_code == 503
    assert "POWERBI" not in embed.text


def test_dashboard_no_data_state(client, super_admin_headers):
    response = client.get("/api/v1/dashboard/summary", headers=super_admin_headers)
    assert response.status_code == 200
    assert response.json()["state"] == "NO_DATA"


def test_dashboard_scope_does_not_leak_unassigned_pilots(client, super_admin_headers):
    created = client.post("/pilots", json=sample_pilot_payload(), headers=super_admin_headers)
    assert created.status_code == 201
    role = next(item for item in client.get("/roles", headers=super_admin_headers).json() if item["name"] == "capture_expert")
    user = client.post("/users", json={"mobile": "09157777777", "display_name": "Scoped viewer", "role_ids": [role["id"]]}, headers=super_admin_headers)
    assert user.status_code == 201
    scoped_headers = login_with_otp(client, "09157777777")
    response = client.get("/api/v1/dashboard/pilots", headers=scoped_headers)
    assert response.status_code == 200
    assert response.json()["state"] == "NO_ACCESS"
    assert response.json()["items"] == []

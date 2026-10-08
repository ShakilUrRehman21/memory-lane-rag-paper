import uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_full_auth_and_user_flow():
    rand_id = uuid.uuid4().hex[:6]
    username = f"user_{rand_id}"
    email = f"user_{rand_id}@memorylane.test"

    # 1. Registration
    reg_payload = {
        "display_name": f"Test User {rand_id}",
        "username": username,
        "email": email,
        "password": "testpassword123",
        "bio": "Testing longitudinal memory lodging",
        "avatar_color": "#38bdf8"
    }
    res = client.post("/api/auth/register", json=reg_payload)
    assert res.status_code == 200, res.text
    data = res.json()
    token = data["token"]
    user_id = data["user"]["id"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Invalid Login
    bad_res = client.post("/api/auth/login", json={"username_or_email": username, "password": "wrong"})
    assert bad_res.status_code == 401

    # 3. Valid Login
    good_res = client.post("/api/auth/login", json={"username_or_email": username, "password": "testpassword123"})
    assert good_res.status_code == 200

    # 4. /auth/me
    me_res = client.get("/api/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["username"] == username

    # 5. Lodging historical capsule
    lodge_res = client.post(f"/api/users/{user_id}/lodge", headers=headers, json={
        "statement": "I believe distributed computing requires decentralized consensus protocols.",
        "memory_type": "belief",
        "event_date": "2019-01-15",
        "context_note": "Initial architectural belief"
    })
    assert lodge_res.status_code == 200

    # 6. Lodging present capsule
    lodge_now = client.post(f"/api/users/{user_id}/lodge", headers=headers, json={
        "statement": "I now believe centralized coordinators with fast zero-knowledge proofs offer vastly higher throughput.",
        "memory_type": "belief",
        "event_date": "2026-10-06",
        "context_note": "Current updated stance"
    })
    assert lodge_now.status_code == 200

    # 7. Timeline check
    tl_res = client.get(f"/api/timeline?user_id={user_id}", headers=headers)
    assert tl_res.status_code == 200
    assert len(tl_res.json()) == 2

    # 8. User Sandbox Isolation
    alex_tl = client.get("/api/timeline?user_id=user_alex").json()
    assert not any("decentralized consensus" in p["statement"] for p in alex_tl)

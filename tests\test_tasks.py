"""test_tasks: 任务创建/领取/提交完整路径."""
import pytest

async def _admin_token(client):
    """Register + login an admin user."""
    await client.post("/api/v1/auth/register", json={"username": "admin", "password": "adminpass"})
    login = await client.post("/api/v1/auth/login", json={"username": "admin", "password": "adminpass"})
    return login.json()["access_token"]


async def _user_token(client, username="alice"):
    await client.post("/api/v1/auth/register", json={"username": username, "password": "secret123"})
    login = await client.post("/api/v1/auth/login", json={"username": username, "password": "secret123"})
    return login.json()["access_token"]


@pytest.mark.asyncio
async def test_create_task(client):
    token = await _admin_token(client)
    r = await client.post(
        "/api/v1/admin/tasks",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "test-task-1", "level": 1, "base_contribution": 10, "timeout_sec": 300},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "test-task-1"
    assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_list_available_tasks(client):
    token = await _admin_token(client)
    await client.post(
        "/api/v1/admin/tasks",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "avail-task", "level": 1},
    )
    r = await client.get("/api/v1/task/available")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.asyncio
async def test_submit_result(client):
    admin_t = await _admin_token(client)
    user_t = await _user_token(client, "alice")
    task_r = await client.post(
        "/api/v1/admin/tasks",
        headers={"Authorization": f"Bearer {admin_t}"},
        json={"name": "submit-test", "level": 1, "base_contribution": 15},
    )
    task_id = task_r.json()["id"]
    r = await client.post(
        "/api/v1/task/submit",
        headers={"Authorization": f"Bearer {user_t}"},
        json={"task_id": task_id, "result_url": "https://minio.local/result.bin", "result_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"},
    )
    # User doesn't own the task, so 403
    assert r.status_code in (403, 404, 409)


@pytest.mark.asyncio
async def test_stats(client):
    token = await _admin_token(client)
    await client.post(
        "/api/v1/admin/tasks",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "stats-task", "level": 1},
    )
    r = await client.get("/api/v1/admin/stats", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()
    assert "tasks" in data
    assert "users" in data
    assert data["tasks"]["pending"] >= 1

"""test_nodes: 节点注册/心跳/列表."""
import pytest

async def _register_and_login(client, username="alice"):
    await client.post("/api/v1/auth/register", json={"username": username, "password": "secret123"})
    login = await client.post("/api/v1/auth/login", json={"username": username, "password": "secret123"})
    return login.json()["access_token"]


@pytest.mark.asyncio
async def test_register_node(client):
    token = await _register_and_login(client)
    r = await client.post(
        "/api/v1/node/register",
        headers={"Authorization": f"Bearer {token}"},
        json={"node_name": "alice-pc", "cpu_cores": 8, "total_memory_gb": 16, "gpu_model": "RTX 3060", "gpu_vram_gb": 12, "os_type": "Linux"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["node_name"] == "alice-pc"
    assert data["level"] == 2   # RTX 3060 12GB → level 2
    assert data["status"] == "online"


@pytest.mark.asyncio
async def test_register_node_unauth(client):
    r = await client.post(
        "/api/v1/node/register",
        json={"node_name": "hacker", "cpu_cores": 4, "total_memory_gb": 8},
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_list_my_nodes(client):
    token = await _register_and_login(client, "bob")
    # register two nodes
    for name in ["bob-pc-1", "bob-pc-2"]:
        await client.post(
            "/api/v1/node/register",
            headers={"Authorization": f"Bearer {token}"},
            json={"node_name": name, "cpu_cores": 4, "total_memory_gb": 8},
        )
    r = await client.get("/api/v1/node/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 2


@pytest.mark.asyncio
async def test_heartbeat(client):
    token = await _register_and_login(client, "carol")
    reg = await client.post(
        "/api/v1/node/register",
        headers={"Authorization": f"Bearer {token}"},
        json={"node_name": "carol-pc", "cpu_cores": 8, "total_memory_gb": 16},
    )
    node_id = reg.json()["id"]
    r = await client.post(
        "/api/v1/node/heartbeat",
        headers={"Authorization": f"Bearer {token}"},
        json={"node_id": node_id},
    )
    assert r.status_code == 200
    assert r.json()["ok"] is True


@pytest.mark.asyncio
async def test_heartbeat_wrong_node(client):
    token = await _register_and_login(client, "dave")
    r = await client.post(
        "/api/v1/node/heartbeat",
        headers={"Authorization": f"Bearer {token}"},
        json={"node_id": "00000000-0000-0000-0000-000000000000"},
    )
    assert r.status_code == 404

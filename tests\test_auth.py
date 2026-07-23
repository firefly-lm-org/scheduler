"""test_auth: 注册/登录/Token 核心路径."""
import pytest

@pytest.mark.asyncio
async def test_register_success(client):
    r = await client.post("/api/v1/auth/register", json={"username": "alice", "password": "secret123"})
    assert r.status_code == 201
    data = r.json()
    assert data["username"] == "alice"
    assert "id" in data

@pytest.mark.asyncio
async def test_register_duplicate(client):
    await client.post("/api/v1/auth/register", json={"username": "bob", "password": "secret123"})
    r = await client.post("/api/v1/auth/register", json={"username": "bob", "password": "another"})
    assert r.status_code == 409

@pytest.mark.asyncio
async def test_login_success(client):
    await client.post("/api/v1/auth/register", json={"username": "carol", "password": "secret123"})
    r = await client.post("/api/v1/auth/login", json={"username": "carol", "password": "secret123"})
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"

@pytest.mark.asyncio
async def test_login_wrong_password(client):
    await client.post("/api/v1/auth/register", json={"username": "dave", "password": "correct"})
    r = await client.post("/api/v1/auth/login", json={"username": "dave", "password": "wrong"})
    assert r.status_code == 401

@pytest.mark.asyncio
async def test_login_nonexistent(client):
    r = await client.post("/api/v1/auth/login", json={"username": "nobody", "password": "secret"})
    assert r.status_code == 401

@pytest.mark.asyncio
async def test_refresh_token(client):
    await client.post("/api/v1/auth/register", json={"username": "eve", "password": "secret123"})
    login = await client.post("/api/v1/auth/login", json={"username": "eve", "password": "secret123"})
    refresh_token = login.json()["refresh_token"]
    r = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert r.status_code == 200
    assert "access_token" in r.json()

@pytest.mark.asyncio
async def test_refresh_invalid(client):
    r = await client.post("/api/v1/auth/refresh", json={"refresh_token": "invalid.token.here"})
    assert r.status_code == 401

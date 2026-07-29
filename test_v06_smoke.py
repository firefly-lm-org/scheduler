"""
firefly-scheduler · v0.6 新增 API 冒烟测试
覆盖：reputation + signal 路由
前置：scheduler 已启动（默认 http://localhost:8000）
"""
import asyncio
import httpx

BASE = "http://localhost:8000"
TOKEN = None  # 动态获取


async def get_admin_token():
    """获取 admin token（用于 reputation/adjust）"""
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            f"{BASE}/api/v1/auth/login",
            json={"username": "admin", "password": "admin123"},
        )
        if resp.status_code == 200:
            return resp.json().get("access_token")
    return None


async def get_node_token():
    """获取测试节点 token"""
    async with httpx.AsyncClient(timeout=10) as client:
        # 注册节点
        await client.post(
            f"{BASE}/api/v1/node/register",
            json={
                "node_name": "smoke-test-node",
                "cpu_cores": 8,
                "total_memory_gb": 16.0,
                "gpu_model": "RTX 4090",
                "gpu_vram_gb": 24.0,
                "os_type": "Linux",
            },
        )
        # 登录节点
        resp = await client.post(
            f"{BASE}/api/v1/node/login",
            json={"node_name": "smoke-test-node"},
        )
        if resp.status_code == 200:
            return resp.json().get("access_token")
    return None


async def main():
    print("=== v0.6 Smoke Test ===\n")

    # ── 获取 token ──
    admin_tok = await get_admin_token()
    node_tok = await get_node_token()

    if not admin_tok:
        print("[SKIP] Admin auth failed, using public endpoints only")
    if not node_tok:
        print("[SKIP] Node auth failed")

    headers_admin = {"Authorization": f"Bearer {admin_tok}"} if admin_tok else {}
    headers_node = {"Authorization": f"Bearer {node_tok}"} if node_tok else {}

    async with httpx.AsyncClient(timeout=10) as client:

        # ── 1. GET /api/v1/reputation/{node_id} ──
        print("1. GET /api/v1/reputation/{node_id}")
        resp = await client.get(f"{BASE}/api/v1/reputation/smoke-test-node")
        print(f"   Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"   score={data.get('score')}, can_claim={data.get('can_claim')}, "
                  f"rate_limit_factor={data.get('rate_limit_factor')}")
        else:
            print(f"   Body: {resp.text[:200]}")

        # ── 2. GET /api/v1/reputation/{node_id}/history ──
        print("\n2. GET /api/v1/reputation/{node_id}/history")
        resp = await client.get(f"{BASE}/api/v1/reputation/smoke-test-node/history?limit=5")
        print(f"   Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"   score={data.get('score')}, history_count={len(data.get('history', []))}")
        else:
            print(f"   Body: {resp.text[:200]}")

        # ── 3. GET /api/v1/reputation/{node_id}/can_claim ──
        print("\n3. GET /api/v1/reputation/{node_id}/can_claim")
        resp = await client.get(f"{BASE}/api/v1/reputation/smoke-test-node/can_claim")
        print(f"   Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"   can_claim={data.get('can_claim')}, reason={data.get('reason')}")
        else:
            print(f"   Body: {resp.text[:200]}")

        # ── 4. POST /api/v1/reputation/{node_id}/adjust (admin) ──
        if admin_tok:
            print("\n4. POST /api/v1/reputation/{node_id}/adjust (admin)")
            resp = await client.post(
                f"{BASE}/api/v1/reputation/smoke-test-node/adjust",
                json={"delta": 5, "reason": "smoke test bonus"},
                headers=headers_admin,
            )
            print(f"   Status: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                print(f"   score_before={data.get('score_before')}, "
                      f"score_after={data.get('score_after')}")
            else:
                print(f"   Body: {resp.text[:200]}")
        else:
            print("\n4. [SKIP] No admin token")

        # ── 5. POST /api/v1/contrib/signal ──
        print("\n5. POST /api/v1/contrib/signal")
        resp = await client.post(
            f"{BASE}/api/v1/contrib/signal",
            json={
                "task_id": "smoke-task-001",
                "node_id": "smoke-test-node",
                "holdout_improvement": 0.12,
                "baseline_accuracy": 0.65,
                "final_accuracy": 0.77,
                "sample_count": 5,
                "query_patterns": ["a3f9b2c1", "d4e5f6a7"],
                "total_steps": 60,
                "final_loss": 0.68,
                "training_time_sec": 45.0,
                "gpu_model": "RTX 4090",
                "gpu_vram_gb": 4.0,
                "os_type": "Linux",
                "client_version": "0.6",
                "idempotency_key": "smoke-test-key-001",
            },
        )
        print(f"   Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"   status={data.get('status')}, "
                  f"contribution_estimated={data.get('contribution_estimated')}")
        else:
            print(f"   Body: {resp.text[:200]}")

        # ── 6. 幂等验证（重复上报 same idempotency_key） ──
        print("\n6. POST /api/v1/contrib/signal (幂等验证)")
        resp = await client.post(
            f"{BASE}/api/v1/contrib/signal",
            json={
                "task_id": "smoke-task-001",
                "node_id": "smoke-test-node",
                "holdout_improvement": 0.99,
                "baseline_accuracy": 0.0,
                "final_accuracy": 0.0,
                "sample_count": 0,
                "query_patterns": [],
                "total_steps": 0,
                "final_loss": 0.0,
                "training_time_sec": 0.0,
                "gpu_model": "",
                "gpu_vram_gb": 0.0,
                "os_type": "",
                "client_version": "0.6",
                "idempotency_key": "smoke-test-key-001",  # 同 key
            },
        )
        print(f"   Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"   status={data.get('status')} (应为 duplicate)")
        else:
            print(f"   Body: {resp.text[:200]}")

        # ── 7. GET /api/v1/contrib/stats/{node_id} ──
        print("\n7. GET /api/v1/contrib/stats/{node_id}")
        resp = await client.get(f"{BASE}/api/v1/contrib/stats/smoke-test-node")
        print(f"   Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"   total_signals={data.get('total_signals')}, "
                  f"total_contribution_estimated={data.get('total_contribution_estimated')}")
        else:
            print(f"   Body: {resp.text[:200]}")

    print("\n=== Smoke Test Complete ===")


if __name__ == "__main__":
    asyncio.run(main())

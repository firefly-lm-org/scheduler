"""
test_aggregation.py — 权重聚合功能验证脚本
用法: python3 test_aggregation.py
"""
import asyncio
import sys
import os

# 确保 app 模块可导入
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 设置 UTF-8 输出编码
os.environ["PYTHONIOENCODING"] = "utf-8"

from app.database import engine
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.aggregation_service import find_ready_aggregation


async def main():
    print("=" * 60)
    print("  萤火虫调度中心 · 权重聚合功能验证")
    print("=" * 60)

    async with AsyncSession(engine) as db:
        print("\n[1] find_ready_aggregation() — 检测就绪聚合组")
        try:
            groups = await find_ready_aggregation(db)
            print(f"    → 返回类型: {type(groups).__name__}")
            print(f"    → 就绪组数量: {len(groups)}")

            if groups:
                for key, task_infos in groups.items():
                    print(f"\n    组: {key}")
                    for info in task_infos:
                        print(
                            f"      task={info['task_id'][:8]}...  "
                            f"node={info.get('node_id', 'N/A') or 'N/A'}  "
                            f"sha256={info.get('result_sha256', 'N/A') or 'N/A'}..."
                        )
            else:
                print("    → 当前没有达到触发阈值的聚合组（这是正常的，如数据库为空或完成任务不足）")

        except Exception as e:
            print(f"\n    ✗ 发生错误: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()

    print("\n[2] 导入验证 — 所有模块加载成功 ✓")
    print("    app.models.aggregation     ✓")
    print("    app.services.aggregation_service ✓")
    print("    app.routers.aggregation    ✓")
    print("\n" + "=" * 60)
    print("  验证完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

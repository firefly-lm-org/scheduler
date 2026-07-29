# 商标搜索填写操作手册（去 CNIPA / USPTO 照着填）

> 用途：你今天花 ~30 分钟填完 `docs/TRADEMARK_SEARCH.md` 的 [待查] 部分。
> 框架已在 GitHub `firefly-lm-org/docs/TRADEMARK_SEARCH.md`，本手册是可照做的操作步骤。

---

## 一、查什么（关键词清单）

| 关键词 | 类别 | 说明 |
|--------|------|------|
| `Firefly LM` | 第9类（软件）/ 第42类（技术服务） | 主品牌英文 |
| `萤火虫大模型` | 第9/42类 | 主品牌中文 |
| `Firefly` | 第9/42类 | 短名（冲突概率高，注意） |
| `火种` | 第9/42类 | 客户端别名 |
| `萤火虫` | 第9/42类 | 中文短名 |

**重点类别**：
- **第9类**：可下载软件、AI 模型、计算机程序
- **第42类**：技术研究、软件即服务（SaaS）、AI 平台

---

## 二、CNIPA（中国）查询

**地址**：https://sbj.cnipa.gov.cn/sbcx/

步骤：
1. 点「商标综合查询」→「商标名称」
2. 依次输入上述 5 个关键词
3. 记录：是否有相同或近似商标、申请人、状态（有效/无效/申请中）、类别
4. 特别注意「萤火虫」「Firefly」在 9/42 类的近似商标

**填写模板**（每个关键词一段）：
```
### Firefly LM (CNIPA)
- 查询时间：2026-07-25
- 相同/近似商标：无 / 有（列出申请人+状态）
- 第9类： [ ] 冲突  [ ] 安全
- 第42类：[ ] 冲突  [ ] 安全
- 结论：可申请 / 需调整名称
```

---

## 三、USPTO（美国）查询

**地址**：https://tmsearch.uspto.gov/

步骤：
1. 进 TESS 系统 → `Free Form` 搜索
2. 输入 `Firefly LM`、`Firefly`、`Firefly AI` 等
3. 看 `Live/Dead` 状态（Live = 有效，需注意；Dead = 已失效可参考）
4. 特别注意 Adobe 的 `Firefly`（AI 图像生成产品）——**这是最大冲突风险**

**填写模板**：
```
### Firefly LM (USPTO)
- 查询时间：2026-07-25
- Adobe Firefly 冲突评估：同领域 AI 产品，建议英文品牌加后缀（如 Firefly-LM）
- 第9类： [ ] 冲突（Adobe Firefly 已注册）  → 建议避开纯 "Firefly"
- 第42类：[ ] 冲突  [ ] 安全
- 结论：英文用 "Firefly LM" 组合词降低冲突；中文 "萤火虫大模型" 主体可注册
```

---

## 四、关键风险提示

⚠️ **Adobe Firefly**：Adobe 已注册 "Firefly" 商标用于 AI 生成产品（第9/42类）。
- 纯 "Firefly" 英文名**高风险**，建议始终用 **"Firefly LM"** 或 **"萤火虫大模型"** 作为注册主体
- 社区/文档里可继续叫「萤火虫 / Firefly」，但**法律注册名用组合词**

---

## 五、填完后的动作

1. 把结果写进 GitHub `docs/TRADEMARK_SEARCH.md`（替换 [待查]）
2. 本地同步：`MEMORY.md` 的 VALUATION_GATES #6 翻 ✅
3. VALUATION_GATES #4（www CNAME）也补完后 → 6/6 全解锁

---

## 六、30 分钟分配

| 动作 | 时间 |
|------|------|
| CNIPA 查 5 关键词 | 12 min |
| USPTO 查 3 关键词 | 12 min |
| 写结论进 TRADEMARK_SEARCH.md | 6 min |

---

**本手册为本地操作参考，实际填写在 GitHub docs 仓库。**

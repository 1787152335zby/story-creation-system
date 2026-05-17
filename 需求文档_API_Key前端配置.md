# 需求文档：API Key 前端配置功能

## 一、需求背景

当前系统依赖 `.env` 文件配置 API Key（DeepSeek/OpenAI/Claude），分发代码给他人使用时：

- 分发者不希望把自己的 API Key 给别人（花钱的风险）
- 使用者不想碰命令行和配置文件，想直接在浏览器界面里填 Key

**目标：** 让普通用户打开浏览器就能配置 Key，不需要编辑任何文件。

---

## 二、当前状态

### 已有的部分

**前端** [SettingsPage.tsx](file:///e:/trae/ai/jvben/故事创作系统/src/pages/SettingsPage.tsx)：
- 已有设置页面，路径 `/settings`
- 已有 LLM 后端选择（DeepSeek/OpenAI/Claude）
- 已有 API Key 输入框、模型名称输入框
- 已有"测试连接"按钮 → 调 API 验证 Key 是否有效
- 已有"保存"按钮 → 调 PUT `/api/settings` 接口

**后端** [settings.py](file:///e:/trae/ai/jvben/故事创作系统/server/routes/settings.py)：
- `GET /api/settings` — 返回当前配置（Key 用 `****` 掩码）
- `PUT /api/settings` — 保存配置到 `.env` 文件，同时写入 `os.environ`
- `POST /api/settings/test-llm` — 测试 LLM 连接

### 存在的问题

1. **LLM 调用时读取 Key 的方式不统一**
   - [client.py](file:///e:/trae/ai/jvben/故事创作系统/llm/client.py) 初始化和 [backends.py](file:///e:/trae/ai/jvben/故事创作系统/llm/backends.py) 各后端都通过 `os.getenv("DEEPSEEK_API_KEY")` 读取 Key
   - `PUT /api/settings` 已把 Key 写入 `os.environ`，所以直接生效
   - 但需要确认：创建项目后生成内容时，LLM 调用能否读到刚保存的 Key

2. **前端页面没有"首次使用引导"**
   - 第一次打开首页时没有提示去设置 Key
   - 用户点了"开始创作"到第4步填故事描述时，如果 Key 没配好，AI 调用会失败

3. **`.env` 文件读写权限**
   - 某些系统上 Python 可能没有 `.env` 文件的写入权限
   - 需要优雅降级（写不进去时至少内存中生效）

---

## 三、具体要求

### 3.1 使设置页能完全工作

目前的设置页前后端代码已经写好，但需要验证/修复以下链路：

```
用户在设置页输入 Key → 点保存 → PUT /api/settings
  → 后端写入 .env 文件 → 写入 os.environ
  → 用户创建项目 → AI 调用 → LLMClient 从 os.getenv 读到 Key
```

**需验证点：**
- [ ] `PUT /api/settings` 返回后，`os.environ` 是否立即更新
- [ ] `LLMClient` 在每次调用时重新读 `os.getenv`（而不是初始化时缓存）
- [ ] 如果 `.env` 文件不可写（权限问题），至少保证内存中的 Key 生效
- [ ] `settings.py` 中的 `_mask_key` 函数是否正确处理各种长度的 Key

### 3.2 添加首次使用引导

在首页（[HomePage.tsx](file:///e:/trae/ai/jvben/故事创作系统/src/pages/HomePage.tsx)）添加检测逻辑：

```typescript
// 伪代码逻辑
useEffect(() => {
  fetchSettings().then(data => {
    const hasKey = data.deepseek_api_key || data.openai_api_key || data.claude_api_key
    setShowSetupPrompt(!hasKey)
  })
}, [])
```

- 如果没有任何 Key 被配置 → 显示引导卡片"配置 AI 模型以开始创作"
- 引导卡片包含两个按钮："去设置"（跳转到 `/settings`）和"稍后"
- "稍后"后不再显示（localStorage 标记）

### 3.3 创建项目前的 Key 校验

在创建项目页面（[NewProjectWizard.tsx](file:///e:/trae/ai/jvben/故事创作系统/src/pages/NewProjectWizard.tsx)）第4步（故事描述）点击"开始创作"时：

```typescript
const handleCreate = async () => {
  // 新增：先检查 Key 是否已配置
  const settings = await fetchSettings()
  const hasKey = settings.deepseek_api_key || settings.openai_api_key || settings.claude_api_key
  if (!hasKey) {
    alert('请先在设置页面配置 API Key')
    navigate('/settings')
    return
  }
  // 原有创建逻辑...
}
```

### 3.4 改善错误提示

当 LLM 调用因 Key 问题失败时，前端应该显示可操作的错误信息：

- 当前：[Workspace.tsx](file:///e:/trae/ai/jvben/故事创作系统/src/pages/Workspace.tsx) 的 `error` 状态会显示后端返回的错误文本
- 后端 [ws_manager.py](file:///e:/trae/ai/jvben/故事创作系统/server/ws_manager.py) 在 `_cancel_task` 或 LLM 异常时发送 `{"type": "error", "error": "..."}`
- 需要确保：当 Key 未配置或 Key 无效时，错误信息明确提示"API Key 未配置，请前往设置页面配置"

---

## 四、涉及的文件

| 文件 | 需要改动 |
|:-----|:---------|
| `src/pages/HomePage.tsx` | 新增首次使用引导卡片 |
| `src/pages/NewProjectWizard.tsx` | 创建前校验 Key |
| `src/pages/Workspace.tsx` | 改善 LLM 错误提示 |
| `llm/client.py` | 确保每次调用重新读 `os.getenv` |
| `llm/backends.py` | 同上 |
| `server/routes/settings.py` | 修复可能的 `.env` 写入问题 |

---

## 五、验收标准

1. 全新克隆代码 → `pip install` + `npm install` → 启动
2. 打开 `http://localhost:5173` → 首页显示"配置 AI 模型"引导
3. 点击"去设置" → 填写 API Key → "测试连接" → 显示"连接成功"
4. 返回首页 → 引导消失
5. 创建项目 → 填写故事 → "开始创作" → 正常生成内容（不报 Key 错误）
6. 设置页修改 Key 后 → 再次生成 → 使用新 Key

---

## 六、注意事项

- `.env` 文件在 `项目根目录/.env`，后端通过 `Path(__file__).resolve().parent.parent.parent / ".env"` 定位
- 如果 `.env` 不存在，后端 `_read_env()` 返回默认空值，不会报错
- 前端 API 调用路径在 [api.ts](file:///e:/trae/ai/jvben/故事创作系统/src/lib/api.ts) 中定义，`BASE = '/api'`
- 设置页相关 API：`fetchSettings()` / `updateSettings()` / `testLLM()`

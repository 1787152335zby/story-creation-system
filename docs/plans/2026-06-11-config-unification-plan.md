# 配置系统统一实现计划

> **说明：** 所有生成入口统一通过 `_get_active_agg_config(type)` 读取配置，JSON 优先，`.env` 兜底。

**目标：** 消除 `.env` 和 `aggregated_configs.json` 两套配置并行的混乱，所有生成入口走同一个配置读取路径

**方案：** 增强 `_get_active_agg_config` 使其也能找到 type=provider 的激活配置；所有生成函数先问它再兜底 `.env`

**涉及文件：** `server/routes/gen.py`、`server/async_orch.py`、`llm/backends.py`、`server/routes/settings.py`

---

### 任务 1: 增强 `_get_active_agg_config`，支持 provider 类型

**文件：** 修改 `server/routes/gen.py:123-135`

当前实现只查 `type == config_type` 的配置。需要增强为：
1. 先查 `type == config_type` ∧ `active == true` → 返回第一个
2. 如果没找到，查 `type == "provider"` ∧ 且 provider_id 能映射到 config_type（deepseek → llm, seedream → image, seedance → video）∧ `active == true` → 返回第一个
3. 都没找到 → 返回 None（调用方去读 `.env`）

- [ ] **修改 `_get_active_agg_config`**

```python
PROVIDER_TYPE_MAP = {
    "deepseek": "llm",
    "openai": "llm",
    "claude": "llm",
    "seedream": "image",
    "seedance": "video",
}

def _get_active_agg_config(config_type: str) -> dict | None:
    if not AGG_CONFIG_PATH.exists():
        return None
    try:
        configs = json.loads(AGG_CONFIG_PATH.read_text(encoding="utf-8"))
        # First: exact type match
        for c in configs:
            if c.get("type") == config_type and c.get("active"):
                return c
        # Second: provider match (e.g. type=provider, provider_id=deepseek → llm)
        for c in configs:
            if c.get("type") == "provider" and c.get("active"):
                pid = c.get("provider_id", "").lower()
                if PROVIDER_TYPE_MAP.get(pid) == config_type:
                    return c
    except Exception:
        pass
    return None
```

---

### 任务 2: 重构 `_call_seedream` 接受外部 API Key

**文件：** 修改 `server/routes/gen.py:45-58`

改签名，让调用方可以传入 key/base_url。

- [ ] **修改 `_call_seedream`**

```python
def _call_seedream(prompt, negative_prompt="", size="1024x1024", n=1, api_key=None, base_url=None):
    api_key = api_key or os.getenv("SEEDANCE_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=400, detail="API Key 未配置")
    url = (base_url or "https://api.volcengine.com/ark/v1").rstrip("/") + "/images/generations"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": "seedream-v1", "prompt": prompt, "n": n, "size": size}
    if negative_prompt:
        payload["negative_prompt"] = negative_prompt
    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    return [img["url"] for img in data.get("data", [])]
```

---

### 任务 3: 重构 `_call_seedance_image_to_video` 接受外部 API Key

**文件：** 修改 `server/routes/gen.py:60-109`

- [ ] **修改签名为 `def _call_seedance_image_to_video(image_paths, prompt, api_key=None, base_url=None)`**
- [ ] 函数内 `api_key = api_key or os.getenv("SEEDANCE_API_KEY", "")`
- [ ] `submit_url = (base_url or "https://api.volcengine.com/ark/v1").rstrip("/") + "/video/generate"`

---

### 任务 4: 更新 `free_image_gen` 使用增强后的 `_get_active_agg_config`

**文件：** 修改 `server/routes/gen.py:137-169`

已使用 `_get_active_agg_config("image")`，但需确保当返回的是 type=provider 的 seedream 时，调用方正确使用 base_url。

- [ ] **无需改动**，当前代码已正确：`client = OpenAI(api_key=agg["api_key"], base_url=agg["base_url"])`

---

### 任务 5: 更新 `free_video_gen` 使用 `_get_active_agg_config`

**文件：** 修改 `server/routes/gen.py:182-217`

- [ ] **在函数开头加**：

```python
agg = _get_active_agg_config("video")
agg_key = agg.get("api_key") if agg else None
agg_base = agg.get("base_url") if agg else None
```

- [ ] 调用 `_call_seedance_image_to_video` 时传入：`_call_seedance_image_to_video(saved_paths, prompt, api_key=agg_key, base_url=agg_base)`

---

### 任务 6: 更新 `async_orch.py` 的 LLM 配置读取

**文件：** 修改 `server/async_orch.py:575-604`

- [ ] **导入函数**：在文件开头加 `from .routes.gen import _get_active_agg_config`
- [ ] **修改 `_run_agent_in_thread`**：

```python
import os
from .routes.gen import _get_active_agg_config

# 在函数开头：
agg = _get_active_agg_config("llm")
if agg and agg.get("api_key"):
    # 使用聚合/官网配置
    backend_type = "aggregated"
    agg_key = agg["api_key"]
    agg_base = agg.get("base_url", "")
    agg_model = agg.get("model", "deepseek-chat")
else:
    # 兜底 .env
    backend_type = os.getenv("LLM_BACKEND", "deepseek")
    agg_key = None
    agg_base = None
    agg_model = None
```

- [ ] 后续代码判断：如果 `agg_key` 存在，用通用 OpenAI client 替换原有的 `LLMBackend` 初始化

---

### 任务 7: 更新 `llm/backends.py` 支持外部传入 Key

**文件：** 修改 `llm/backends.py`

- [ ] 每个 Backend 的 `__init__` 增加可选参数 `api_key=None, base_url=None`
- [ ] `_get_client` 中：`api_key = self.api_key or os.getenv(...)`

```python
class DeepSeekBackend(LLMBackend):
    def __init__(self, model="deepseek-chat", api_key=None, base_url=None):
        super().__init__(model)
        self._api_key = api_key
        self._base_url = base_url

    def _get_client(self):
        from openai import OpenAI
        return OpenAI(
            api_key=self._api_key or os.getenv("DEEPSEEK_API_KEY"),
            base_url=self._base_url or "https://api.deepseek.com",
            timeout=120,
        )
```

---

### 任务 8: 设置页追加 Key 点「使用」时同步写挂载配置

**文件：** 修改 `src/pages/SettingsPage.tsx`

当前追加 Key「使用」按钮只调 `activateProviderConfig`（改 JSON 中 `type=provider` 的 active）。还需要额外写入或更新一条 `type=llm/image/video` 的配置，让 `_get_active_agg_config` 能直接找到。

- [ ] **在「使用」按钮内加**：

```typescript
// 之前：activateProviderConfig + deactivateAggType + updateSettings
// 之后：同时调 createAggConfig 或 updateAggConfig 写一条同类型的配置
await createAggConfig({
  name: pc.name || label,
  base_url: pc.base_url || '',
  api_key: pc.api_key,
  type: typeKey,
  model: pc.model || '',
})
```

这样生成接口通过 `_get_active_agg_config(typeKey)` 就能直接找到它。

---

## 测试方法

1. 后端跑测试：`python -c "from server.routes.gen import _get_active_agg_config; print(_get_active_agg_config('llm'))"`
2. 前端测试：打开设置页，添加官网 API → 点使用 → 去自由生图/视频页面测试
3. 回归测试：不配任何聚合，确保旧 `.env` 配置仍能正常生图和创作

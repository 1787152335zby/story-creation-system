import os
import json
from typing import Optional
from .backends import OpenAIBackend, ClaudeBackend, DeepSeekBackend, LLMBackend


def _get_active_llm_config() -> dict | None:
    """Read aggregated configs and find active LLM config."""
    from pathlib import Path
    path = Path(__file__).resolve().parent.parent / "aggregated_configs.json"
    if not path.exists():
        return None
    try:
        configs = json.loads(path.read_text(encoding="utf-8"))
        for c in configs:
            if c.get("type") == "llm" and c.get("active"):
                key = c.get("api_key", "")
                if not key or "your-key" in key or "****" in key:
                    continue
                return c
        for c in configs:
            if c.get("type") == "provider" and c.get("active"):
                pid = c.get("provider_id", "").lower()
                if pid in ("deepseek", "openai", "claude"):
                    key = c.get("api_key", "")
                    if not key or "your-key" in key or "****" in key:
                        continue
                    return c
    except Exception:
        pass
    return None


PROVIDER_MODEL_MAP = {
    "deepseek": "deepseek-chat",
    "openai": "gpt-4o",
    "claude": "claude-sonnet-4-20250514",
}

_auto_model_cache: dict = {}


def resolve_model(base_url: str, api_key: str, preferred: str = "", provider: str = "") -> str:
    cache_key = f"{provider}|{base_url}|{api_key[:12]}"
    if cache_key in _auto_model_cache:
        return _auto_model_cache[cache_key]

    from openai import OpenAI

    # 1. 拉取可用模型列表
    models: list[str] = []
    try:
        client = OpenAI(api_key=api_key, base_url=base_url, timeout=10)
        resp = client.models.list()
        models = [m.id for m in resp.data]
    except Exception:
        pass

    if not models:
        fallback = preferred or PROVIDER_MODEL_MAP.get(provider, "deepseek-chat")
        _auto_model_cache[cache_key] = fallback
        return fallback

    # 2. 排序：优先用户指定的 > 含 "chat" 的 > API 返回的其他模型
    chat = [m for m in models if "chat" in m.lower()]
    other = [m for m in models if "chat" not in m.lower()]

    candidates: list[str] = []
    if preferred:
        candidates.append(preferred)
    for m in chat:
        if m not in candidates:
            candidates.append(m)
    for m in other:
        if m not in candidates:
            candidates.append(m)

    # 3. 快速测试：找第一个能输出 message.content 的模型
    test_messages = [{"role": "user", "content": "."}]
    for m in candidates:
        try:
            r = client.chat.completions.create(model=m, messages=test_messages, max_tokens=5)
            content = r.choices[0].message.content or ""
            if content.strip():
                _auto_model_cache[cache_key] = m
                return m
        except Exception:
            continue

    selected = candidates[0] if candidates else "deepseek-chat"
    _auto_model_cache[cache_key] = selected
    return selected


def resolve_and_update_env(base_url: str, api_key: str, provider: str, model_env: str, preferred: str = "") -> str:
    model = resolve_model(base_url, api_key, preferred, provider)
    os.environ[model_env] = model
    return model


class LLMClient:
    def __init__(self):
        # 优先用 .env 的 LLM_BACKEND（用户最新配置）
        backend_name = os.getenv("LLM_BACKEND", "openai").lower()
        env_key_map = {"deepseek": "DEEPSEEK_API_KEY", "openai": "OPENAI_API_KEY", "claude": "CLAUDE_API_KEY"}
        env_key = os.getenv(env_key_map.get(backend_name, ""), "")
        if env_key and "your-key" not in env_key and "****" not in env_key:
            self.backend = self._create_backend(backend_name)
            return
        # 没有有效 .env key → 降级到聚合配置
        agg = _get_active_llm_config()
        if agg and agg.get("api_key"):
            self.backend = self._create_from_agg(agg)
        else:
            # 兜底：用默认参数创建，等实际调用时再报错
            self.backend = self._create_backend(backend_name)

    def _create_from_agg(self, agg: dict) -> LLMBackend:
        pid = agg.get("provider_id", "").lower()
        model = agg.get("model") or PROVIDER_MODEL_MAP.get(pid, "deepseek-chat")
        api_key = agg["api_key"]
        base_url = agg.get("base_url", "")
        if pid == "claude":
            return ClaudeBackend(model, api_key=api_key, base_url=base_url)
        elif pid in ("deepseek", "openai") or not pid:
            if not base_url and pid == "deepseek":
                base_url = "https://api.deepseek.com"
            return OpenAIBackend(model, api_key=api_key, base_url=base_url)
        return DeepSeekBackend(model, api_key=api_key, base_url=base_url)

    def _create_backend(self, name: str) -> LLMBackend:
        env_key_map = {
            "deepseek": ("DEEPSEEK_API_KEY", "DEEPSEEK_MODEL", "deepseek-chat", "https://api.deepseek.com"),
            "openai": ("OPENAI_API_KEY", "OPENAI_MODEL", "gpt-4o", ""),
            "claude": ("CLAUDE_API_KEY", "CLAUDE_MODEL", "claude-sonnet-4-20250514", ""),
        }
        key_env, model_env, default_model, default_url = env_key_map.get(name, ("", "", "gpt-4o", ""))
        api_key = os.getenv(key_env, "")
        base_url = os.getenv(f"{name.upper()}_BASE_URL", default_url) or ""

        # 自动从 API 拉取可用模型列表并选择最佳模型
        preferred = os.getenv(model_env, "")
        if base_url and api_key:
            model = resolve_and_update_env(base_url, api_key, name, model_env, preferred)
        else:
            model = preferred or default_model

        backends = {
            "openai": OpenAIBackend,
            "claude": ClaudeBackend,
            "deepseek": DeepSeekBackend,
        }
        backend_class = backends.get(name)
        if not backend_class:
            available = ", ".join(backends.keys())
            raise ValueError(f"未知后端: {name}，可选: {available}")
        return backend_class(model, api_key=api_key or None, base_url=base_url)

    def chat(self, system_prompt: str, user_prompt: str, temperature: float = 0.7, max_tokens: int = 16384) -> str:
        return self.backend.chat(system_prompt, user_prompt, temperature, max_tokens)

    def chat_stream(self, system_prompt: str, user_prompt: str, temperature: float = 0.7, max_tokens: int = 16384):
        yield from self.backend.chat_stream(system_prompt, user_prompt, temperature, max_tokens)

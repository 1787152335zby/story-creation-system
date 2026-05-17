import os
from typing import Optional
from .backends import OpenAIBackend, ClaudeBackend, DeepSeekBackend, LLMBackend


def _get_active_llm_config() -> dict | None:
    """Read aggregated configs and find active LLM config."""
    import json
    from pathlib import Path
    path = Path(__file__).resolve().parent.parent / "aggregated_configs.json"
    if not path.exists():
        return None
    try:
        configs = json.loads(path.read_text(encoding="utf-8"))
        for c in configs:
            if c.get("type") == "llm" and c.get("active"):
                return c
        for c in configs:
            if c.get("type") == "provider" and c.get("active"):
                pid = c.get("provider_id", "").lower()
                if pid in ("deepseek", "openai", "claude"):
                    return c
    except Exception:
        pass
    return None


PROVIDER_MODEL_MAP = {
    "deepseek": "deepseek-chat",
    "openai": "gpt-4o",
    "claude": "claude-sonnet-4-20250514",
}


class LLMClient:
    def __init__(self):
        agg = _get_active_llm_config()
        if agg and agg.get("api_key"):
            self.backend = self._create_from_agg(agg)
        else:
            backend_name = os.getenv("LLM_BACKEND", "openai").lower()
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
        model_map = {
            "deepseek": ("DEEPSEEK_MODEL", "deepseek-chat"),
            "openai": ("OPENAI_MODEL", "gpt-4o"),
            "claude": ("CLAUDE_MODEL", "claude-sonnet-4-20250514"),
        }
        env_key, default_model = model_map.get(name, ("", "gpt-4o"))
        model = os.getenv(env_key, default_model)

        backends = {
            "openai": OpenAIBackend,
            "claude": ClaudeBackend,
            "deepseek": DeepSeekBackend,
        }
        backend_class = backends.get(name)
        if not backend_class:
            available = ", ".join(backends.keys())
            raise ValueError(f"未知后端: {name}，可选: {available}")
        return backend_class(model)

    def chat(self, system_prompt: str, user_prompt: str, temperature: float = 0.7, max_tokens: int = 16384) -> str:
        return self.backend.chat(system_prompt, user_prompt, temperature, max_tokens)

    def chat_stream(self, system_prompt: str, user_prompt: str, temperature: float = 0.7, max_tokens: int = 16384):
        yield from self.backend.chat_stream(system_prompt, user_prompt, temperature, max_tokens)

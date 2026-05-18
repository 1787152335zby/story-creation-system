from abc import ABC, abstractmethod
from typing import Optional


class ImageBackend(ABC):
    @abstractmethod
    def text_to_image(self, prompt: str, negative_prompt: str = "", size: str = "1024x1024", n: int = 1, model: str = "") -> list[str]:
        """
        Text-to-image generation.
        Returns list of image URLs.
        """

    @abstractmethod
    def name(self) -> str:
        """Backend display name"""


_IMAGE_BACKEND_REGISTRY: dict[str, str] = {
    "seedream": "SeedreamBackend",
    "gpt-image-1": "GPTImageBackend",
    "gpt_image": "GPTImageBackend",
    "banana-2": "Banana2Backend",
    "banana2": "Banana2Backend",
    "custom": "CustomImageBackend",
}

_IMAGE_BACKEND_MODULE = {
    "gpt-image-1": "tools.image_api_openai_compat",
    "gpt_image": "tools.image_api_openai_compat",
    "banana-2": "tools.image_api_openai_compat",
    "banana2": "tools.image_api_openai_compat",
    "custom": "tools.image_api_openai_compat",
}


def create_image_backend(backend_name: str = "seedream", api_key: str = "", base_url: str = "") -> ImageBackend:
    """Create an image backend. If api_key/base_url provided, pass to the backend."""
    # For seedream, always go direct to avoid circular import
    if backend_name == "seedream":
        from tools.image_api_seedream import SeedreamBackend
        return SeedreamBackend(api_key=api_key, base_url=base_url)

    # Try legacy naming convention first (tools/image_api_{name}.py)
    try:
        import importlib
        module = importlib.import_module(f"tools.image_api_{backend_name}")
        cls_name = _IMAGE_BACKEND_REGISTRY.get(backend_name, "")
        if cls_name:
            return getattr(module, cls_name)()
    except (ImportError, AttributeError):
        pass

    # Try new module mapping
    mod_path = _IMAGE_BACKEND_MODULE.get(backend_name)
    if mod_path:
        import importlib
        module = importlib.import_module(mod_path)
        if backend_name == "custom" and (api_key or base_url):
            cls_name = _IMAGE_BACKEND_REGISTRY.get(backend_name, "")
            if cls_name and hasattr(module, cls_name):
                return getattr(module, cls_name)(api_key=api_key, base_url=base_url)
        cls_name = _IMAGE_BACKEND_REGISTRY.get(backend_name, "")
        if cls_name and hasattr(module, cls_name):
            return getattr(module, cls_name)()

    raise ValueError(
        f"Unknown image backend: {backend_name}. "
        f"Available: {', '.join(_IMAGE_BACKEND_REGISTRY.keys())}"
    )


def list_image_backends() -> list[dict]:
    """Return available image backends for frontend selection."""
    return [
        {"value": "seedream", "label": "Seedream（火山引擎）", "desc": "基础文生图，已有Key可复用"},
        {"value": "gpt-image-1", "label": "GPT-Image-1（OpenAI）", "desc": "高质量，精准文字，需OpenAI Key"},
        {"value": "banana-2", "label": "Nano Banana 2（第三方）", "desc": "Gemini 3 Pro，文字渲染强"},
        {"value": "custom", "label": "自定义", "desc": "任意 OpenAI 兼容接口"},
    ]

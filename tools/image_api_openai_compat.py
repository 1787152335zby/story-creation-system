import os
import requests
from .image_api import ImageBackend


class OpenAICompatBackend(ImageBackend):
    def __init__(self, env_prefix: str, display_name: str, default_model: str = ""):
        self._name = display_name
        self.api_key = os.getenv(f"{env_prefix}_API_KEY", os.getenv("OPENAI_API_KEY", ""))
        self.base_url = os.getenv(f"{env_prefix}_BASE_URL", "")
        self.model = os.getenv(f"{env_prefix}_MODEL", default_model)
        if not self.base_url:
            if "GPT" in env_prefix or "OPENAI" in env_prefix:
                self.base_url = "https://api.openai.com/v1"
            else:
                self.base_url = "https://api.openai.com/v1"

    def text_to_image(self, prompt: str, negative_prompt: str = "", size: str = "1024x1024", n: int = 1, model: str = "") -> list[str]:
        url = f"{self.base_url.rstrip('/')}/images/generations"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {"model": model or self.model, "prompt": prompt, "n": n, "size": size}
        if negative_prompt:
            payload["negative_prompt"] = negative_prompt
        response = requests.post(url, headers=headers, json=payload, timeout=120)
        response.raise_for_status()
        data = response.json()
        return [img["url"] for img in data.get("data", [])]

    def image_to_image(
        self,
        images_base64: list[str],
        prompt: str,
        negative_prompt: str = "",
        strength: float = 0.7,
        size: str = "1024x1024",
        n: int = 1,
        model: str = ""
    ) -> list[str]:
        image_base64 = images_base64[0]
        url = f"{self.base_url.rstrip('/')}/images/generations"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        
        # 清理 base64 前缀（如果有）
        if image_base64.startswith("data:image"):
            image_base64 = image_base64.split(",")[1]
        
        payload = {
            "model": model or self.model,
            "prompt": prompt,
            "image": image_base64,
            "strength": max(0.0, min(1.0, strength)),
            "n": n,
            "size": size
        }
        if negative_prompt:
            payload["negative_prompt"] = negative_prompt
        
        response = requests.post(url, headers=headers, json=payload, timeout=120)
        response.raise_for_status()
        data = response.json()
        return [img["url"] for img in data.get("data", [])]

    def name(self) -> str:
        return self._name


# 注意：以下类在当前调用链路中未被使用，保留仅供兼容参考
class GPTImageBackend(ImageBackend):
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        self.model = os.getenv("GPT_IMAGE_MODEL", "gpt-image-1")
        self.base_url = "https://api.openai.com/v1"

    def text_to_image(self, prompt: str, negative_prompt: str = "", size: str = "1024x1024", n: int = 1, model: str = "") -> list[str]:
        url = f"{self.base_url.rstrip('/')}/images/generations"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {"model": model or self.model, "prompt": prompt, "n": n, "size": size}
        response = requests.post(url, headers=headers, json=payload, timeout=120)
        response.raise_for_status()
        data = response.json()
        return [img["url"] for img in data.get("data", [])]

    def image_to_image(
        self,
        images_base64: list[str],
        prompt: str,
        negative_prompt: str = "",
        strength: float = 0.7,
        size: str = "1024x1024",
        n: int = 1,
        model: str = ""
    ) -> list[str]:
        image_base64 = images_base64[0]
        url = f"{self.base_url.rstrip('/')}/images/generations"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        
        # 清理 base64 前缀（如果有）
        if image_base64.startswith("data:image"):
            image_base64 = image_base64.split(",")[1]
        
        payload = {
            "model": model or self.model,
            "prompt": prompt,
            "image": image_base64,
            "strength": max(0.0, min(1.0, strength)),
            "n": n,
            "size": size
        }
        if negative_prompt:
            payload["negative_prompt"] = negative_prompt
        
        response = requests.post(url, headers=headers, json=payload, timeout=120)
        response.raise_for_status()
        data = response.json()
        return [img["url"] for img in data.get("data", [])]

    def name(self) -> str:
        return "GPT-Image-1"


# 注意：此类在当前调用链路中未被使用，保留仅供兼容参考
class Banana2Backend(ImageBackend):
    def __init__(self):
        self.api_key = os.getenv("BANANA2_API_KEY", "")
        self.base_url = os.getenv("BANANA2_BASE_URL", "https://api.laozhang.ai/v1")
        self.model = os.getenv("BANANA2_MODEL", "nano-banana-2")

    def text_to_image(self, prompt: str, negative_prompt: str = "", size: str = "1024x1024", n: int = 1, model: str = "") -> list[str]:
        url = f"{self.base_url.rstrip('/')}/images/generations"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {"model": model or self.model, "prompt": prompt, "n": n, "size": size}
        response = requests.post(url, headers=headers, json=payload, timeout=120)
        response.raise_for_status()
        data = response.json()
        return [img["url"] for img in data.get("data", [])]

    def image_to_image(
        self,
        images_base64: list[str],
        prompt: str,
        negative_prompt: str = "",
        strength: float = 0.7,
        size: str = "1024x1024",
        n: int = 1,
        model: str = ""
    ) -> list[str]:
        image_base64 = images_base64[0]
        url = f"{self.base_url.rstrip('/')}/images/generations"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        
        # 清理 base64 前缀（如果有）
        if image_base64.startswith("data:image"):
            image_base64 = image_base64.split(",")[1]
        
        payload = {
            "model": model or self.model,
            "prompt": prompt,
            "image": image_base64,
            "strength": max(0.0, min(1.0, strength)),
            "n": n,
            "size": size
        }
        if negative_prompt:
            payload["negative_prompt"] = negative_prompt
        
        response = requests.post(url, headers=headers, json=payload, timeout=120)
        response.raise_for_status()
        data = response.json()
        return [img["url"] for img in data.get("data", [])]

    def name(self) -> str:
        return "Nano Banana 2"


# 注意：此类在当前调用链路中未被使用，保留仅供兼容参考
class CustomImageBackend(ImageBackend):
    def __init__(self):
        self.api_key = os.getenv("CUSTOM_IMAGE_API_KEY", "")
        self.base_url = os.getenv("CUSTOM_IMAGE_BASE_URL", "")
        self.model = os.getenv("CUSTOM_IMAGE_MODEL", "gpt-image-1")

    def text_to_image(self, prompt: str, negative_prompt: str = "", size: str = "1024x1024", n: int = 1, model: str = "") -> list[str]:
        url = f"{self.base_url.rstrip('/')}/images/generations"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {"model": model or self.model, "prompt": prompt, "n": n, "size": size}
        response = requests.post(url, headers=headers, json=payload, timeout=120)
        response.raise_for_status()
        data = response.json()
        return [img["url"] for img in data.get("data", [])]

    def image_to_image(
        self,
        images_base64: list[str],
        prompt: str,
        negative_prompt: str = "",
        strength: float = 0.7,
        size: str = "1024x1024",
        n: int = 1,
        model: str = ""
    ) -> list[str]:
        image_base64 = images_base64[0]
        url = f"{self.base_url.rstrip('/')}/images/generations"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        
        # 清理 base64 前缀（如果有）
        if image_base64.startswith("data:image"):
            image_base64 = image_base64.split(",")[1]
        
        payload = {
            "model": model or self.model,
            "prompt": prompt,
            "image": image_base64,
            "strength": max(0.0, min(1.0, strength)),
            "n": n,
            "size": size
        }
        if negative_prompt:
            payload["negative_prompt"] = negative_prompt
        
        response = requests.post(url, headers=headers, json=payload, timeout=120)
        response.raise_for_status()
        data = response.json()
        return [img["url"] for img in data.get("data", [])]

    def name(self) -> str:
        return f"自定义 ({self.model})"

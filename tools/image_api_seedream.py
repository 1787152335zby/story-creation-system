import os
import json
import requests
from fastapi import HTTPException
from .image_api import ImageBackend


class SeedreamBackend(ImageBackend):
    def __init__(self, api_key: str = "", base_url: str = ""):
        self.api_key = api_key or os.getenv("SEEDANCE_API_KEY", "")
        url = (base_url or "https://api.volcengine.com/ark/v1").rstrip("/")
        if "/images/" not in url:
            if "/v1/" in url or "/v1" in url:
                url = url.rstrip("/") + "/images/generations"
            else:
                url = url.rstrip("/") + "/v1/images/generations"
        self.base_url = url

    def text_to_image(self, prompt: str, negative_prompt: str = "", size: str = "1024x1024", n: int = 1, model: str = "") -> list[str]:
        if not self.api_key or self.api_key == "your-seedance-key-here":
            raise HTTPException(status_code=400, detail="生图 API Key 未配置，请在设置页配置 SEEDANCE_API_KEY")
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model or "seedream-v1",
            "prompt": prompt,
            "n": n,
            "size": size,
        }
        if negative_prompt:
            payload["negative_prompt"] = negative_prompt

        response = requests.post(self.base_url, headers=headers, json=payload, timeout=60)
        try:
            data = response.json()
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=500,
                detail=f"生图 API 返回异常 (HTTP {response.status_code})：API Key 可能无效或没有权限，请在设置页检查 SEEDANCE_API_KEY"
            )
        if response.status_code == 400:
            detail = data.get("error", {}).get("message", str(data))
            if "not have permission" in detail or "auth" in detail.lower() or "unauthorized" in detail.lower():
                raise HTTPException(status_code=400, detail="SEEDANCE_API_KEY 无效或没有权限，请检查设置页中的 API Key")
            raise HTTPException(status_code=400, detail=f"生图请求失败: {detail}")
        response.raise_for_status()
        return [img["url"] for img in data.get("data", [])]

    def name(self) -> str:
        return "Seedream"

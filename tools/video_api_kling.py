import os
import time
import json
import requests
import base64
from .video_api import VideoBackend


class KlingBackend(VideoBackend):
    """可灵 Kling AI 视频生成 backend。
    支持两种模式：
    1. 聚合平台模式：通过 base_url + api_key 调用，走平台统一接口
    2. 官方 API 模式：AK/SK 鉴权，直接调 openapi.klingai.com
    """

    def __init__(self, api_key: str = "", base_url: str = "",
                 access_key: str = "", secret_key: str = ""):
        self.api_key = api_key or os.getenv("KLING_API_KEY", "")
        self.base_url = (base_url or os.getenv("KLING_BASE_URL", "")).rstrip("/")
        self.access_key = access_key or os.getenv("KLING_ACCESS_KEY", "")
        self.secret_key = secret_key or os.getenv("KLING_SECRET_KEY", "")
        self._token = None
        self._token_expiry = 0

    def _is_official_mode(self) -> bool:
        return bool(self.access_key and self.secret_key)

    def _get_auth_token(self) -> str:
        if not self._is_official_mode():
            return ""
        now = time.time()
        if self._token and now < self._token_expiry - 60:
            return self._token
        try:
            resp = requests.post(
                "https://openapi.klingai.com/v1/auth/token",
                json={
                    "access_key": self.access_key,
                    "secret_key": self.secret_key,
                },
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            self._token = data.get("access_token") or data.get("token", "")
            self._token_expiry = now + 3600
            return self._token
        except Exception:
            self._token = ""
            return ""

    def _submit_task(self, payload: dict, endpoint_suffix: str = "/v1/video/generations") -> str:
        if self._is_official_mode():
            token = self._get_auth_token()
            url = f"https://openapi.klingai.com{endpoint_suffix}"
            headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        elif self.base_url:
            url = f"{self.base_url}{endpoint_suffix}"
            headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        else:
            raise ValueError("Kling: need either (access_key + secret_key) or (base_url + api_key)")

        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()

        # 不同平台返回格式不同，遍历取 task_id / video_id / id
        return data.get("task_id") or data.get("video_id") or data.get("id") or data.get("job_id", "")

    def text_to_video(self, prompt: str, resolution: str = "1280x720", duration: int = 5,
                      generate_audio: bool = False, model: str = "", negative_prompt: str = "") -> str:
        model = model or os.getenv("KLING_MODEL", "") or "kling-v2-master"
        payload = {
            "model": model,
            "prompt": prompt,
            "duration": duration,
            "aspect_ratio": "16:9" if "1280" in resolution else "9:16",
        }
        if negative_prompt:
            payload["negative_prompt"] = negative_prompt
        if self._is_official_mode():
            payload["action"] = "text2video"
            payload["mode"] = "pro"
            return self._submit_task(payload)
        return self._submit_task(payload)

    def image_to_video(self, image_path: str, prompt: str, resolution: str = "1280x720",
                       duration: int = 5, generate_audio: bool = False, model: str = "",
                       negative_prompt: str = "", last_frame_path: str = "",
                       return_last_frame: bool = True, seed: int = -1,
                       camera_fixed: bool = False, watermark: bool = False) -> str:
        model = model or os.getenv("KLING_MODEL", "") or "kling-v2-master"
        with open(image_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode()
        payload = {
            "model": model,
            "prompt": prompt,
            "duration": duration,
            "aspect_ratio": "16:9" if "1280" in resolution else "9:16",
            "image": img_b64,
        }
        if negative_prompt:
            payload["negative_prompt"] = negative_prompt
        if last_frame_path:
            with open(last_frame_path, "rb") as f:
                payload["last_frame"] = base64.b64encode(f.read()).decode()
        if self._is_official_mode():
            payload["action"] = "image2video"
            payload["mode"] = "pro"
            return self._submit_task(payload)
        return self._submit_task(payload)

    def check_status(self, task_id: str) -> dict:
        if self._is_official_mode():
            token = self._get_auth_token()
            query_url = f"https://openapi.klingai.com/v1/video/result/{task_id}"
            headers = {"Authorization": f"Bearer {token}"}
        elif self.base_url:
            query_url = f"{self.base_url}/v1/video/result/{task_id}"
            headers = {"Authorization": f"Bearer {self.api_key}"}
        else:
            return {"status": "failed", "error": "no config"}

        resp = requests.get(query_url, headers=headers, timeout=30)

        if resp.status_code == 404:
            if self.base_url:
                query_url2 = f"{self.base_url}/v1/tasks/{task_id}"
                try:
                    resp2 = requests.get(query_url2, headers=headers, timeout=30)
                    if resp2.status_code == 200:
                        resp = resp2
                except Exception:
                    pass
        resp.raise_for_status()
        data = resp.json()

        status = data.get("status") or data.get("state", "")
        if status in ("completed", "succeeded", "succeed", "done"):
            video_url = data.get("video_url") or data.get("url") or ""
            if not video_url:
                outputs = data.get("output", {}) or data.get("result", {}) or {}
                if isinstance(outputs, dict):
                    video_url = outputs.get("video_url") or outputs.get("url", "")
            return {"status": "completed", "video_url": video_url}
        elif status in ("failed", "error"):
            return {"status": "failed", "error": data.get("error", {}).get("message", str(data)) if isinstance(data.get("error"), dict) else str(data.get("error", ""))}
        return {"status": "running"}

    def wait_for_result(self, task_id: str, timeout: int = 600, poll_interval: int = 5) -> dict:
        start = time.time()
        while time.time() - start < timeout:
            result = self.check_status(task_id)
            if result["status"] == "completed":
                return result
            elif result["status"] == "failed":
                raise RuntimeError(f"Kling generation failed: {result.get('error', 'Unknown')}")
            time.sleep(poll_interval)
        raise TimeoutError(f"Kling generation timed out after {timeout}s")

    def name(self) -> str:
        return "Kling (可灵)"

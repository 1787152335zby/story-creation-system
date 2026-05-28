import os
import time
import requests
import base64
from .video_api import VideoBackend


class LumaBackend(VideoBackend):
    """Luma Dream Machine 视频生成 backend"""

    def __init__(self, api_key: str = "", base_url: str = ""):
        self.api_key = api_key or os.getenv("LUMA_API_KEY", "")
        self.base_url = (base_url or os.getenv("LUMA_BASE_URL", "https://api.lumalabs.ai")).rstrip("/")

    def text_to_video(self, prompt: str, resolution: str = "1280x720", duration: int = 5,
                      generate_audio: bool = False, model: str = "", negative_prompt: str = "") -> str:
        model = model or "dream-machine"
        payload = {
            "model": model,
            "prompt": prompt,
            "aspect_ratio": "16:9" if "1280" in resolution else "9:16",
        }
        resp = requests.post(
            f"{self.base_url}/dream-machine/v1/generations",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json=payload, timeout=60,
        )
        resp.raise_for_status()
        return resp.json().get("id") or resp.json().get("generation_id", "")

    def image_to_video(self, image_path: str, prompt: str, resolution: str = "1280x720",
                       duration: int = 5, generate_audio: bool = False, model: str = "",
                       negative_prompt: str = "", last_frame_path: str = "",
                       return_last_frame: bool = True, seed: int = -1,
                       camera_fixed: bool = False, watermark: bool = False) -> str:
        model = model or "dream-machine"
        with open(image_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode()
        payload = {
            "model": model,
            "prompt": prompt,
            "aspect_ratio": "16:9" if "1280" in resolution else "9:16",
            "keyframes": {
                "frame0": {"type": "image", "url": f"data:image/png;base64,{img_b64}"}
            },
        }
        resp = requests.post(
            f"{self.base_url}/dream-machine/v1/generations",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json=payload, timeout=60,
        )
        resp.raise_for_status()
        return resp.json().get("id") or resp.json().get("generation_id", "")

    def check_status(self, task_id: str) -> dict:
        resp = requests.get(
            f"{self.base_url}/dream-machine/v1/generations/{task_id}",
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        status = data.get("state", data.get("status", ""))
        if status in ("completed", "succeeded", "done"):
            assets = data.get("assets", {}) or data.get("output", {}) or {}
            video_url = assets.get("video") or assets.get("video_url") or ""
            if not video_url and isinstance(assets, dict):
                video_url = assets.get("url", "")
            return {"status": "completed", "video_url": video_url}
        elif status in ("failed", "error"):
            return {"status": "failed", "error": data.get("failure_reason", data.get("error", "Unknown"))}
        return {"status": "running"}

    def wait_for_result(self, task_id: str, timeout: int = 600, poll_interval: int = 10) -> dict:
        start = time.time()
        while time.time() - start < timeout:
            result = self.check_status(task_id)
            if result["status"] == "completed":
                return result
            elif result["status"] == "failed":
                raise RuntimeError(f"Luma generation failed: {result.get('error', 'Unknown')}")
            time.sleep(poll_interval)
        raise TimeoutError(f"Luma generation timed out after {timeout}s")

    def name(self) -> str:
        return "Luma Dream Machine"

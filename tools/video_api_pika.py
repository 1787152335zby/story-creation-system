import os
import time
import requests
import base64
from .video_api import VideoBackend


class PikaBackend(VideoBackend):
    """Pika 视频生成 backend"""

    def __init__(self, api_key: str = "", base_url: str = ""):
        self.api_key = api_key or os.getenv("PIKA_API_KEY", "")
        self.base_url = (base_url or os.getenv("PIKA_BASE_URL", "https://api.pika.art")).rstrip("/")

    def text_to_video(self, prompt: str, resolution: str = "1280x720", duration: int = 5,
                      generate_audio: bool = False, model: str = "", negative_prompt: str = "") -> str:
        model = model or "pika-2.2"
        payload = {
            "model": model,
            "prompt": prompt,
            "duration": duration,
            "aspect_ratio": "16:9" if "1280" in resolution else "9:16",
        }
        resp = requests.post(
            f"{self.base_url}/v1/video/generate",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json=payload, timeout=60,
        )
        resp.raise_for_status()
        return resp.json().get("id") or resp.json().get("job_id", "")

    def image_to_video(self, image_path: str, prompt: str, resolution: str = "1280x720",
                       duration: int = 5, generate_audio: bool = False, model: str = "",
                       negative_prompt: str = "", last_frame_path: str = "",
                       return_last_frame: bool = True, seed: int = -1,
                       camera_fixed: bool = False, watermark: bool = False) -> str:
        model = model or "pika-2.2"
        with open(image_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode()
        payload = {
            "model": model,
            "prompt": prompt,
            "duration": duration,
            "aspect_ratio": "16:9" if "1280" in resolution else "9:16",
            "image": f"data:image/png;base64,{img_b64}",
        }
        resp = requests.post(
            f"{self.base_url}/v1/video/generate",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json=payload, timeout=60,
        )
        resp.raise_for_status()
        return resp.json().get("id") or resp.json().get("job_id", "")

    def check_status(self, task_id: str) -> dict:
        resp = requests.get(
            f"{self.base_url}/v1/video/result/{task_id}",
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=30,
        )
        if resp.status_code == 404:
            resp = requests.get(
                f"{self.base_url}/v1/jobs/{task_id}",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=30,
            )
        resp.raise_for_status()
        data = resp.json()
        status = data.get("status", data.get("state", ""))
        if status in ("completed", "succeeded", "done"):
            video_url = data.get("video_url") or data.get("url") or ""
            if not video_url:
                result = data.get("result", {}) or data.get("output", {}) or {}
                video_url = result.get("video_url") or result.get("url", "")
            return {"status": "completed", "video_url": video_url}
        elif status in ("failed", "error"):
            return {"status": "failed", "error": data.get("error", "Unknown")}
        return {"status": "running"}

    def wait_for_result(self, task_id: str, timeout: int = 600, poll_interval: int = 10) -> dict:
        start = time.time()
        while time.time() - start < timeout:
            result = self.check_status(task_id)
            if result["status"] == "completed":
                return result
            elif result["status"] == "failed":
                raise RuntimeError(f"Pika generation failed: {result.get('error', 'Unknown')}")
            time.sleep(poll_interval)
        raise TimeoutError(f"Pika generation timed out after {timeout}s")

    def name(self) -> str:
        return "Pika"

import os
import time
import requests
import base64
from pathlib import Path
from .video_api import VideoBackend

ARK_BASE = "https://ark.cn-beijing.volces.com"
SUBMIT_URL = f"{ARK_BASE}/api/v3/contents/generations/tasks"
QUERY_URL = f"{ARK_BASE}/api/v3/contents/generations/tasks"


def _image_to_base64(image_path: str) -> str:
    ext = os.path.splitext(image_path)[1].lower().lstrip(".")
    if ext not in ("png", "jpg", "jpeg", "webp"):
        ext = "png"
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return f"data:image/{ext};base64,{b64}"


class SeedanceBackend(VideoBackend):
    def __init__(self):
        self.api_key = os.getenv("SEEDANCE_API_KEY", "")
        self.model = os.getenv("SEEDANCE_MODEL", "") or "doubao-seedance-pro"

    def _build_params(self, duration: int = 5, ratio: str = "16:9", seed: int = -1,
                      camera_fixed: bool = False, watermark: bool = False) -> str:
        parts = [f"--ratio {ratio}", f"--dur {duration}", "--fps 24"]
        if seed >= 0:
            parts.append(f"--seed {seed}")
        parts.append(f"--cf {str(camera_fixed).lower()}")
        parts.append(f"--wm {str(watermark).lower()}")
        return " ".join(parts)

    def text_to_video(self, prompt: str, resolution: str = "1280x720", duration: int = 5,
                      generate_audio: bool = False, model: str = "", negative_prompt: str = "",
                      seed: int = -1, camera_fixed: bool = False, watermark: bool = False) -> str:
        params = self._build_params(duration, "16:9", seed, camera_fixed, watermark)
        full_prompt = f"{prompt} {params}" if prompt else params
        content = [{"type": "text", "text": full_prompt}]
        payload = {
            "model": model or self.model,
            "content": content,
            "service_tier": "default",
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        resp = requests.post(SUBMIT_URL, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json().get("id", "")

    def image_to_video(self, image_path: str, prompt: str, resolution: str = "1280x720",
                       duration: int = 5, generate_audio: bool = False, model: str = "",
                       negative_prompt: str = "", last_frame_path: str = "",
                       return_last_frame: bool = True, seed: int = -1,
                       camera_fixed: bool = False, watermark: bool = False) -> str:
        params = self._build_params(duration, "16:9", seed, camera_fixed, watermark)
        full_prompt = f"{prompt} {params}" if prompt else params
        content = [{"type": "text", "text": full_prompt}]
        content.append({
            "type": "image_url",
            "image_url": {"url": _image_to_base64(image_path)},
            "role": "first_frame",
        })
        if last_frame_path:
            content.append({
                "type": "image_url",
                "image_url": {"url": _image_to_base64(last_frame_path)},
                "role": "last_frame",
            })
        payload = {
            "model": model or self.model,
            "content": content,
            "return_last_frame": return_last_frame,
            "service_tier": "default",
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        resp = requests.post(SUBMIT_URL, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        return resp.json().get("id", "")

    def check_status(self, task_id: str) -> dict:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        resp = requests.get(f"{QUERY_URL}/{task_id}", headers=headers, timeout=30)
        resp.raise_for_status()
        result = resp.json()
        status = result.get("status", "running")
        if status == "succeeded":
            return {
                "status": "completed",
                "video_url": result.get("video_url", ""),
                "last_frame_url": result.get("last_frame_url", ""),
            }
        elif status in ("failed", "expired"):
            return {"status": "failed", "error": result.get("error", result.get("status", "Unknown"))}
        return {"status": "running"}

    def wait_for_result(self, task_id: str, timeout: int = 300, poll_interval: int = 10) -> dict:
        start = time.time()
        while time.time() - start < timeout:
            result = self.check_status(task_id)
            if result["status"] == "completed":
                return result
            elif result["status"] == "failed":
                raise RuntimeError(f"Video generation failed: {result.get('error', 'Unknown')}")
            time.sleep(poll_interval)
        raise TimeoutError(f"Video generation timed out after {timeout}s")

    def name(self) -> str:
        return "Seedance"

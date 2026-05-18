import os
import time
import requests
from pathlib import Path
from .video_api import VideoBackend


class SeedanceBackend(VideoBackend):
    def __init__(self):
        self.api_key = os.getenv("SEEDANCE_API_KEY", "")
        self.submit_url = "https://api.volcengine.com/ark/v1/video/generate"
        self.query_url = "https://api.volcengine.com/ark/v1/video/status"
        self.text_submit_url = "https://api.volcengine.com/ark/v1/video/generate"

    def image_to_video(self, image_path: str, prompt: str, resolution: str = "1280x720", duration: int = 5, generate_audio: bool = False) -> str:
        file_name = os.path.basename(image_path)
        with open(image_path, "rb") as f:
            files = {"image": (file_name, f, "image/png")}
            data = {
                "prompt": prompt,
                "resolution": resolution,
                "duration": str(duration),
                "generate_audio": str(generate_audio).lower(),
            }
            headers = {"Authorization": f"Bearer {self.api_key}"}
            resp = requests.post(
                self.submit_url,
                headers=headers,
                data=data,
                files=files,
                timeout=60,
            )
        resp.raise_for_status()
        result = resp.json()
        return result.get("id", "")

    def text_to_video(self, prompt: str, resolution: str = "1280x720", duration: int = 5, generate_audio: bool = False) -> str:
        import json
        payload = {
            "model": "doubao-seedance-2-0-260128",
            "prompt": prompt,
            "resolution": resolution,
            "duration": duration,
            "generate_audio": generate_audio,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        resp = requests.post(self.text_submit_url, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        result = resp.json()
        return result.get("id", "")

    def check_status(self, task_id: str) -> dict:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        resp = requests.get(f"{self.query_url}/{task_id}", headers=headers, timeout=30)
        resp.raise_for_status()
        result = resp.json()
        status = result.get("status", "running")
        if status == "succeeded":
            return {"status": "completed", "video_url": result.get("video_url", "")}
        elif status == "failed":
            return {"status": "failed", "error": result.get("error", "Unknown error")}
        return {"status": "running"}

    def wait_for_result(self, task_id: str, timeout: int = 300, poll_interval: int = 10) -> str:
        start = time.time()
        while time.time() - start < timeout:
            result = self.check_status(task_id)
            if result["status"] == "completed":
                return result["video_url"]
            elif result["status"] == "failed":
                raise RuntimeError(f"Video generation failed: {result.get('error', 'Unknown')}")
            time.sleep(poll_interval)
        raise TimeoutError(f"Video generation timed out after {timeout}s")

    def name(self) -> str:
        return "Seedance"

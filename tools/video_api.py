from abc import ABC, abstractmethod
from typing import Optional


class VideoBackend(ABC):
    @abstractmethod
    def image_to_video(self, image_path: str, prompt: str, resolution: str = "1280x720", duration: int = 5, generate_audio: bool = False) -> str:
        """Submit image-to-video task, return task_id"""

    @abstractmethod
    def text_to_video(self, prompt: str, resolution: str = "1280x720", duration: int = 5, generate_audio: bool = False) -> str:
        """Submit text-to-video task, return task_id"""

    @abstractmethod
    def check_status(self, task_id: str) -> dict:
        """Return {'status': 'running'|'completed'|'failed', 'video_url': '...' or 'error': '...'}"""

    @abstractmethod
    def wait_for_result(self, task_id: str, timeout: int = 300, poll_interval: int = 10) -> str:
        """Poll until complete, return video URL"""

    @abstractmethod
    def name(self) -> str:
        """Backend display name"""


def create_video_backend(backend_name: str = "seedance") -> VideoBackend:
    backends = {
        "seedance": "SeedanceBackend",
    }
    if backend_name not in backends:
        raise ValueError(f"Unknown video backend: {backend_name}")
    import importlib
    module = importlib.import_module(f"tools.video_api_{backend_name}")
    cls = getattr(module, backends[backend_name])
    return cls()

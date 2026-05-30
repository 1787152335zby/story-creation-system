import os
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List


BASE_DIR = Path(os.environ.get("STORYFORGE_DATA_DIR", str(Path(__file__).resolve().parent.parent)))
PROJECTS_DIR = BASE_DIR / "projects"


def get_projects_list() -> List[Dict]:
    if not PROJECTS_DIR.exists():
        return []
    projects = []
    for item in PROJECTS_DIR.iterdir():
        if item.is_dir():
            config_file = item / "project_config.json"
            if config_file.exists():
                with open(config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
                projects.append(config)
    return projects


class ProjectManager:
    def __init__(self, name: str):
        self.name = self._sanitize_name(name)
        self.project_dir = PROJECTS_DIR / self.name
        self.config_file = self.project_dir / "project_config.json"
        self.config = self._load_or_create_config()

    def _sanitize_name(self, name: str) -> str:
        invalid_chars = r'<>:"/\|?*[]【】'
        for c in invalid_chars:
            name = name.replace(c, "")
        return name.strip() or "untitled"

    def _load_or_create_config(self) -> Dict:
        if self.config_file.exists():
            with open(self.config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
            # 迁移：旧项目 storyboard/visual_extract 顺序与 workflow 不一致
            phases = config.get("phases", [])
            if len(phases) >= 5 and phases[3].get("name") == "storyboard" and phases[4].get("name") == "visual_extract":
                phases[3], phases[4] = phases[4], phases[3]
                config["updated_at"] = datetime.now().isoformat()
                self.config_file.parent.mkdir(parents=True, exist_ok=True)
                with open(self.config_file, "w", encoding="utf-8") as fw:
                    json.dump(config, fw, ensure_ascii=False, indent=2)
            return config
        return {
            "name": self.name,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "status": "initialized",
            "current_phase": 0,
            "phases": [
                {"name": "story_outline", "done": False},
                {"name": "full_plot", "done": False},
                {"name": "full_script", "done": False},
                {"name": "visual_extract", "done": False},
                {"name": "storyboard", "done": False},
                {"name": "prompts", "done": False},
                {"name": "image_gen", "done": False},
                {"name": "video_gen", "done": False},
            ],
            "pending_approval": -1,
            "pending_version": -1,
            "auto_approve": False,
        }

    def save_config(self):
        self.config["updated_at"] = datetime.now().isoformat()
        self.project_dir.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)

    def mark_phase_done(self, phase_index: int):
        if 0 <= phase_index < len(self.config["phases"]):
            self.config["phases"][phase_index]["done"] = True
            self.config["current_phase"] = phase_index + 1
            self.config["pending_approval"] = -1
            self.config["pending_version"] = -1
            self.save_config()

    def set_pending_approval(self, phase_index: int):
        self.config["pending_approval"] = phase_index
        self.save_config()

    def clear_pending_approval(self):
        self.config["pending_approval"] = -1
        self.save_config()

    def set_pending_version(self, phase_index: int):
        self.config["pending_version"] = phase_index
        self.save_config()

    def clear_pending_version(self):
        self.config["pending_version"] = -1
        self.save_config()

    @property
    def auto_approve(self) -> bool:
        return self.config.get("auto_approve", False)

    def set_auto_approve(self, value: bool):
        self.config["auto_approve"] = value
        self.save_config()

    @property
    def pending_episode(self) -> Optional[dict]:
        return self.config.get("pending_episode")

    def set_pending_episode(self, phase_index: int, chunk_index: int, chunk_name: str, total_chunks: int, chunk_files=None):
        self.config["pending_episode"] = {
            "phase_index": phase_index,
            "chunk_index": chunk_index,
            "chunk_name": chunk_name,
            "total_chunks": total_chunks,
            "chunk_files": chunk_files or [],
        }
        self.save_config()

    def clear_pending_episode(self):
        self.config.pop("pending_episode", None)
        self.save_config()

    def write_output(self, filename: str, content: str) -> Path:
        file_path = self.project_dir / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return file_path

    def delete_output(self, filename: str) -> bool:
        file_path = self.project_dir / filename
        if file_path.exists():
            file_path.unlink()
            return True
        return False

    def read_output(self, filename: str) -> Optional[str]:
        file_path = self.project_dir / filename
        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        return None

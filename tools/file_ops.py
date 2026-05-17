import shutil
from pathlib import Path
from typing import List, Optional


def create_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def copy_file(src: Path, dst: Path):
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def list_files(directory: Path, pattern: str = "*") -> List[Path]:
    if not directory.exists():
        return []
    return list(directory.glob(pattern))


def read_file(file_path: Path) -> Optional[str]:
    if file_path.exists():
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    return None


def write_file(file_path: Path, content: str):
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)


def backup_file(file_path: Path) -> Optional[Path]:
    if file_path.exists():
        backup = file_path.with_suffix(file_path.suffix + ".bak")
        shutil.copy2(file_path, backup)
        return backup
    return None

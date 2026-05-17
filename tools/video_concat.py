import subprocess
import os
import shutil
from pathlib import Path


class VideoConcat:
    @staticmethod
    def is_ffmpeg_available() -> bool:
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    @staticmethod
    def concat(video_paths: list[str], output_path: str) -> str:
        if not video_paths:
            raise ValueError("No video paths provided")
        if len(video_paths) == 1:
            shutil.copy2(video_paths[0], output_path)
            return output_path

        file_list_path = Path(output_path).parent / "_concat_list.txt"
        file_list_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_list_path, "w", encoding="utf-8") as f:
            for vp in video_paths:
                abs_path = os.path.abspath(vp)
                escaped = abs_path.replace("\\", "/").replace("'", "'\\''")
                f.write(f"file '{escaped}'\n")

        result = subprocess.run(
            ["ffmpeg", "-f", "concat", "-safe", "0", "-i", str(file_list_path),
             "-c", "copy", str(output_path), "-y"],
            capture_output=True, text=True, timeout=600,
        )
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg concat failed: {result.stderr}")

        file_list_path.unlink(missing_ok=True)
        return output_path

    @staticmethod
    def get_duration(video_path: str) -> float:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", video_path],
            capture_output=True, text=True, timeout=30,
        )
        return float(result.stdout.strip()) if result.stdout.strip() else 0.0

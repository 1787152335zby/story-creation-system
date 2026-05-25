import subprocess
import os
import shutil
import tempfile
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
    def concat(video_paths: list[str], output_path: str,
               title_text: str = "", title_duration: float = 2.0,
               transition_duration: float = 0.0,
               subtitle_srt_path: str = "",
               bgm_path: str = "", bgm_volume: float = 0.3) -> str:
        if not video_paths:
            raise ValueError("No video paths provided")
        if not VideoConcat.is_ffmpeg_available():
            raise RuntimeError("ffmpeg not found")

        temp_dir = Path(output_path).parent / "_temp_concat"
        temp_dir.mkdir(parents=True, exist_ok=True)

        try:
            processed = list(video_paths)

            if title_text:
                title_path = temp_dir / "_title.mp4"
                VideoConcat._make_title(title_text, title_duration, str(title_path))
                processed.insert(0, str(title_path))

            if transition_duration > 0 and len(processed) > 1:
                result_path = VideoConcat._crossfade_chain(processed, transition_duration, temp_dir)
                processed = [result_path]

            if len(processed) > 1:
                merged = temp_dir / "_merged.mp4"
                VideoConcat._simple_concat(processed, str(merged))
                processed = [str(merged)]

            final_video = processed[0]

            if subtitle_srt_path:
                subbed = temp_dir / "_subbed.mp4"
                VideoConcat._burn_subtitles(final_video, subtitle_srt_path, str(subbed))
                final_video = str(subbed)

            if bgm_path:
                final_with_bgm = temp_dir / "_with_bgm.mp4"
                VideoConcat._mix_bgm(final_video, bgm_path, bgm_volume, str(final_with_bgm))
                final_video = str(final_with_bgm)

            shutil.copy2(final_video, output_path)
            return output_path

        finally:
            shutil.rmtree(str(temp_dir), ignore_errors=True)

    @staticmethod
    def _simple_concat(video_paths: list[str], output_path: str) -> str:
        if len(video_paths) == 1:
            shutil.copy2(video_paths[0], output_path)
            return output_path

        file_list = Path(output_path).parent / "_clist.txt"
        with open(file_list, "w", encoding="utf-8") as f:
            for vp in video_paths:
                abs_path = os.path.abspath(vp).replace("\\", "/")
                f.write(f"file '{abs_path}'\n")

        result = subprocess.run(
            ["ffmpeg", "-f", "concat", "-safe", "0", "-i", str(file_list),
             "-c", "copy", output_path, "-y"],
            capture_output=True, text=True, timeout=600,
        )
        file_list.unlink(missing_ok=True)
        if result.returncode != 0:
            raise RuntimeError(f"concat failed: {result.stderr[-200:]}")
        return output_path

    @staticmethod
    def _crossfade_chain(video_paths: list[str], duration: float, temp_dir: Path) -> str:
        current = video_paths[0]
        for i in range(1, len(video_paths)):
            next_video = video_paths[i]
            output = str(temp_dir / f"_xfade_{i}.mp4")
            offset = VideoConcat.get_duration(current) - duration
            if offset < 0:
                offset = 0
            result = subprocess.run([
                "ffmpeg", "-i", current, "-i", next_video,
                "-filter_complex",
                f"[0:v][1:v]xfade=transition=fade:duration={duration}:offset={offset:.3f}[v];"
                f"[0:a][1:a]acrossfade=d={duration}[a]",
                "-map", "[v]", "-map", "[a]",
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "18",
                "-pix_fmt", "yuv420p", "-c:a", "aac",
                output, "-y",
            ], capture_output=True, text=True, timeout=300)
            if result.returncode != 0:
                if i == 1:
                    shutil.copy2(video_paths[0], output)
                current = output
            else:
                if i > 1 and os.path.exists(current) and temp_dir.name in current:
                    Path(current).unlink(missing_ok=True)
                current = output
        return current

    @staticmethod
    def _make_title(text: str, duration: float, output: str):
        result = subprocess.run([
            "ffmpeg", "-f", "lavfi",
            "-i", f"color=c=black:s=1280x720:r=24:d={duration}",
            "-vf", (f"drawtext=text='{text}':fontsize=48:"
                    f"fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2"),
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "18",
            "-pix_fmt", "yuv420p",
            "-an",
            output, "-y",
        ], capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            raise RuntimeError(f"title generation failed: {result.stderr[-200:]}")

    @staticmethod
    def _burn_subtitles(video_path: str, srt_path: str, output: str):
        srt_escaped = os.path.abspath(srt_path).replace("\\", "/").replace(":", "\\\\:")
        result = subprocess.run([
            "ffmpeg", "-i", video_path,
            "-vf", f"subtitles='{srt_escaped}':force_style='FontSize=24,Alignment=2'",
            "-c:a", "copy",
            output, "-y",
        ], capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            shutil.copy2(video_path, output)

    @staticmethod
    def _mix_bgm(video_path: str, bgm_path: str, volume: float, output: str):
        result = subprocess.run([
            "ffmpeg", "-i", video_path, "-i", bgm_path,
            "-filter_complex",
            f"[1:a]volume={volume}[bgm];[0:a][bgm]amix=inputs=2:duration=first[a]",
            "-map", "0:v", "-map", "[a]",
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            output, "-y",
        ], capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            shutil.copy2(video_path, output)

    @staticmethod
    def get_duration(video_path: str) -> float:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", video_path],
            capture_output=True, text=True, timeout=30,
        )
        return float(result.stdout.strip()) if result.stdout.strip() else 0.0

    @staticmethod
    def generate_subtitle_srt(video_paths: list[str], shot_data: list[dict], output_srt: str) -> str:
        lines = []
        idx = 1
        current_time = 0.0

        for i, shot in enumerate(shot_data):
            dur = VideoConcat.get_duration(video_paths[i]) if i < len(video_paths) else 5.0
            dialogue = shot.get("dialogue", "")
            if not dialogue:
                raw = shot.get("dialogue_raw", "")
                if raw:
                    dialogue = raw
            if dialogue:
                start = current_time
                end = current_time + dur
                lines.append(f"{idx}")
                lines.append(f"{VideoConcat._format_time(start)} --> {VideoConcat._format_time(end)}")
                lines.append(dialogue.strip('"').strip("'"))
                lines.append("")
                idx += 1
            current_time += dur

        if lines:
            Path(output_srt).parent.mkdir(parents=True, exist_ok=True)
            Path(output_srt).write_text("\n".join(lines), encoding="utf-8")
            return output_srt
        return ""

    @staticmethod
    def _format_time(seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = seconds % 60
        return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")

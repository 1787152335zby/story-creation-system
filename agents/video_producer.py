import re
import json
import requests
from pathlib import Path
from core.agent_base import AgentBase
from core.project_manager import ProjectManager
from core.style_config import StyleConfig
from tools.video_api import create_video_backend
from tools.video_concat import VideoConcat


class VideoProducer(AgentBase):
    def __init__(self, llm_client=None):
        super().__init__(llm_client)
        self.video_backend = create_video_backend("seedance")

    def run(self, project: ProjectManager, style: StyleConfig, input_content: str) -> str:
        return "".join(self.run_stream(project, style, input_content))

    def run_stream(self, project: ProjectManager, style: StyleConfig, input_content: str):
        yield from self._run_batch(project)

    def _run_batch(self, project: ProjectManager):
        segments = self._parse_prompt_segments(project)
        if not segments:
            yield "⚠️ 未找到提示词分段\n"
            return

        yield f"📋 检测到 {len(segments)} 个视频片段\n"

        clips_dir = project.project_dir / "07_生成素材" / "视频"
        clips_dir.mkdir(parents=True, exist_ok=True)

        video_paths = []
        for i, seg in enumerate(segments):
            yield f"🎬 生成片段 {i+1}/{len(segments)}：{seg['name']}...\n"
            try:
                video_url = self._generate_clip(project, seg)
                clip_path = str(clips_dir / f"片段_{i+1:03d}.mp4")
                self._download_video(video_url, clip_path)
                video_paths.append(clip_path)
                yield f"  ✅ 已保存\n"
            except Exception as e:
                yield f"  ❌ 生成失败: {e}\n"

        if len(video_paths) >= 2 and VideoConcat.is_ffmpeg_available():
            yield "🔗 拼接视频片段...\n"
            try:
                output_dir = project.project_dir / "07_生成素材" / "视频" / "成片"
                output_dir.mkdir(parents=True, exist_ok=True)
                output_path = str(output_dir / "全片.mp4")
                VideoConcat.concat(video_paths, output_path)
                yield f"✅ 成片已保存: {output_path}\n"
            except Exception as e:
                yield f"⚠️ 拼接失败 (可手动拼接): {e}\n"
        elif video_paths:
            import shutil
            output_dir = project.project_dir / "07_生成素材" / "视频" / "成片"
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = str(output_dir / "全片.mp4")
            shutil.copy2(video_paths[0], output_path)
            yield f"✅ 已保存单片段成片\n"

    def generate_clip(self, project: ProjectManager, segment_index: int):
        segments = self._parse_prompt_segments(project)
        if segment_index < 0 or segment_index >= len(segments):
            yield f"❌ 无效片段索引: {segment_index}\n"
            return
        seg = segments[segment_index]
        yield f"🎬 生成片段 {segment_index+1}/{len(segments)}：{seg['name']}...\n"
        try:
            video_url = self._generate_clip(project, seg)
            clips_dir = project.project_dir / "07_生成素材" / "视频"
            clips_dir.mkdir(parents=True, exist_ok=True)
            clip_path = str(clips_dir / f"片段_{segment_index+1:03d}.mp4")
            self._download_video(video_url, clip_path)
            yield f"  ✅ 已保存: {clip_path}\n"
        except Exception as e:
            yield f"  ❌ 生成失败: {e}\n"

    def _generate_clip(self, project: ProjectManager, segment: dict):
        prompt = segment.get("prompt", "")
        image_path = self._find_matching_image(project, segment)
        if not image_path:
            raise FileNotFoundError(f"未找到匹配的参考图: {segment['name']}")
        task_id = self.video_backend.image_to_video(image_path, prompt[:500])
        video_url = self.video_backend.wait_for_result(task_id, timeout=300, poll_interval=10)
        return video_url

    def _find_matching_image(self, project: ProjectManager, segment: dict):
        scene_dir = project.project_dir / "07_视觉素材" / "场景"
        if scene_dir.exists():
            panorama_files = sorted(scene_dir.glob("*_全景总览.png"))
            if panorama_files:
                return str(panorama_files[0])
        char_dir = project.project_dir / "07_视觉素材" / "角色"
        if char_dir.exists():
            char_files = sorted(char_dir.glob("*.png"))
            if char_files:
                return str(char_files[0])
        return None

    def _parse_prompt_segments(self, project: ProjectManager) -> list[dict]:
        prompts_dirs = [project.project_dir / "06_提示词", project.project_dir / "05_分镜脚本"]
        content = ""
        for prompts_dir in prompts_dirs:
            if not prompts_dir.exists():
                continue
            prompts_path = prompts_dir / "提示词.md"
            if prompts_path.exists():
                content = prompts_path.read_text(encoding="utf-8")
                break
            alt_files = sorted(prompts_dir.glob("提示词_*.md"))
            if alt_files:
                content = "\n\n".join(f.read_text(encoding="utf-8") for f in alt_files)
                break
        if not content:
            return []

        segments = []
        pattern = re.compile(r"#{1,4}\s*(第\d+[场集]|镜头\d+)", re.MULTILINE)
        parts = pattern.split(content)
        for i in range(1, len(parts), 2):
            name = parts[i].strip()
            text = parts[i + 1].strip() if i + 1 < len(parts) else ""
            segments.append({"name": name, "content": text, "prompt": text[:300]})
        if not segments and content.strip():
            segments.append({"name": "全部", "content": content, "prompt": content[:300]})
        return segments

    def _download_video(self, url: str, save_path: str):
        resp = requests.get(url, timeout=120, stream=True)
        resp.raise_for_status()
        with open(save_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)

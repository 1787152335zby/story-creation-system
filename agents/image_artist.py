from core.agent_base import AgentBase
from core.project_manager import ProjectManager
from core.style_config import StyleConfig
from core.visual_bible import VisualBibleExtractor
from tools.image_api import create_image_backend
from tools.image_composer import ImageComposer


class ImageArtist(AgentBase):
    def __init__(self, llm_client=None):
        super().__init__(llm_client)
        self.image_backend = create_image_backend("seedream")

    def run(self, project: ProjectManager, style: StyleConfig, input_content: str) -> str:
        return "".join(self.run_stream(project, style, input_content))

    def run_stream(self, project: ProjectManager, style: StyleConfig, input_content: str):
        yield from self._run_batch(project)

    def _run_batch(self, project: ProjectManager):
        chars = VisualBibleExtractor.list_characters(project)
        scenes = VisualBibleExtractor.list_scenes(project)

        yield f"📋 检测到 {len(chars)} 个角色，{len(scenes)} 个场景\n"

        for char in chars:
            yield f"🎨 生成角色定妆照：{char['name']}...\n"
            yield from self._generate_character(project, char)
            yield f"✅ {char['name']} 完成\n"

        for scene in scenes:
            yield f"🌆 生成场景概念图：{scene['name']}...\n"
            yield from self._generate_scene(project, scene)
            yield f"✅ {scene['name']} 完成\n"

        yield "🎉 全部视觉素材生成完成\n"

    def generate_character(self, project: ProjectManager, character_name: str):
        chars = VisualBibleExtractor.list_characters(project)
        char = next((c for c in chars if c["name"] == character_name), None)
        if not char:
            return
        yield from self._generate_character(project, char)

    def _generate_character(self, project: ProjectManager, char: dict):
        prompt = self._build_character_prompt(char)
        try:
            urls = self.image_backend.text_to_image(prompt, size="1024x1024", n=1)
            if urls:
                save_dir = project.project_dir / "07_视觉素材" / "角色"
                save_dir.mkdir(parents=True, exist_ok=True)
                save_path = str(save_dir / f"{char['name']}_四视图.png")
                ImageComposer.download_image(urls[0], save_path)
                yield f"  ✅ 已保存: {save_path}\n"
        except Exception as e:
            yield f"  ❌ 生成失败: {e}\n"

    def _build_character_prompt(self, char: dict) -> str:
        appearance = char.get("appearance", "")
        clothing = char.get("clothing", "")
        features = "、".join(char.get("key_features", []))
        return (
            f"'{char['name']}' 的定妆照，纯白背景。"
            f"角色特征：{appearance}。服装：{clothing}。"
            f"标志性特征：{features}。"
            f"画布分为4格2x2网格：左上脸部特写（胸部以上，正脸）、"
            f"右上全身正面、左下全身侧面（90°侧身）、右下全身背面。"
            f"每格人物居中。纯白背景，无文字遮挡。"
        )

    def generate_scene(self, project: ProjectManager, scene_name: str, angles=None):
        scenes = VisualBibleExtractor.list_scenes(project)
        scene = next((s for s in scenes if s["name"] == scene_name), None)
        if not scene:
            return
        yield from self._generate_scene(project, scene, angles)

    def _generate_scene(self, project: ProjectManager, scene: dict, angles=None):
        if angles is None:
            angles = ["正视图", "左45度", "右45度", "鸟瞰图"]

        save_dir = project.project_dir / "07_视觉素材" / "场景"
        save_dir.mkdir(parents=True, exist_ok=True)
        angle_images = {}

        for angle in angles:
            prompt = self._build_scene_prompt(scene, angle)
            try:
                urls = self.image_backend.text_to_image(prompt, size="1024x1024", n=1)
                if urls:
                    angle_name = angle.replace(" ", "")
                    save_path = str(save_dir / f"{scene['name']}_{angle_name}.png")
                    ImageComposer.download_image(urls[0], save_path)
                    angle_images[angle_name] = save_path
                    yield f"  ✅ {angle} 已保存\n"
            except Exception as e:
                yield f"  ❌ {angle} 生成失败: {e}\n"

        if len(angle_images) >= 2:
            panorama_path = str(save_dir / f"{scene['name']}_全景总览.png")
            ImageComposer.compose_scene_panorama(angle_images, scene["name"], panorama_path)
            yield f"  ✅ 全景总览已合成\n"

    def _build_scene_prompt(self, scene: dict, angle: str) -> str:
        env = scene.get("environment", "")
        lighting = scene.get("lighting", "自然光")
        color_tone = scene.get("color_tone", "自然色调")
        props = "、".join(scene.get("props", []))

        angle_map = {
            "正视图": "正面视角，从正前方观看",
            "左45度": "左侧45度视角，展示空间深度",
            "右45度": "右侧45度视角，展示空间纵深感",
            "鸟瞰图": "从正上方俯瞰的鸟瞰视角，完整展示空间布局",
        }
        view_desc = angle_map.get(angle, angle)

        return (
            f"'{scene['name']}' 场景概念图，{view_desc}。"
            f"环境描述：{env}。光线：{lighting}。色调：{color_tone}。"
            f"关键道具：{props}。无文字，写实风格。"
            f"blank white background around the scene for compositing. no text or watermark."
        )

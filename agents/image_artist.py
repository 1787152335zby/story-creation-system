from core.agent_base import AgentBase
from core.project_manager import ProjectManager
from core.style_config import StyleConfig
from core.visual_bible import VisualBibleExtractor, _sanitize_filename
from tools.image_api import create_image_backend
from tools.image_composer import ImageComposer
from tools.constants import ANGLE_MAP


def _parse_prompt_sections(text: str) -> dict:
    """解析提示词 markdown 文件，返回 {主体名: {变体名: 提示词文本}} 或 {主体名: 提示词文本}
    
    支持两种格式:
    有变体:
      ### 主体名
      #### 变体名
      内容...
    
    无变体:
      ### 主体名
      内容直接跟在标题后面
    """
    result = {}
    current_name = None
    current_variant = None
    buf = ""
    pending_name = None
    pending_variant = None

    for line in text.split("\n"):
        if line.startswith("### "):
            # 保存上一个
            if current_name is not None and buf.strip():
                if current_variant is not None:
                    result.setdefault(current_name, {})[current_variant] = buf.strip()
                else:
                    result[current_name] = buf.strip()
            current_name = line[4:].strip()
            current_variant = None
            buf = ""
        elif line.startswith("#### "):
            # 保存上一个变体
            if current_name is not None and buf.strip():
                result.setdefault(current_name, {})[current_variant] = buf.strip()
            current_variant = line[5:].strip()
            buf = ""
        elif current_name and line.strip():
            buf += line.strip() + " "

    # 保存最后一个
    if current_name is not None and buf.strip():
        if current_variant is not None:
            result.setdefault(current_name, {})[current_variant] = buf.strip()
        else:
            result[current_name] = buf.strip()

    return result


def _load_prompt_map(project) -> dict:
    """从 06_提示词/ 读取已生成的提示词映射表
    
    返回:
    {
        "characters": {"角色名": {"基础形象": "提示词", "变体名": "提示词", ...}, ...},
        "characters_flat": {"角色名": "提示词", ...},            # 无变体的角色
        "scenes": {"场景名": {"基础形象": "提示词", "变体名": "提示词", ...}, ...},
        "scenes_flat": {"场景名": "提示词", ...},                 # 无变体的场景
    }
    """
    prompt_dir = project.project_dir / "06_提示词"
    result = {"characters": {}, "characters_flat": {}, "scenes": {}, "scenes_flat": {}}

    cf = prompt_dir / "角色提示词.md"
    if cf.exists():
        parsed = _parse_prompt_sections(cf.read_text(encoding="utf-8"))
        for name, val in parsed.items():
            if isinstance(val, dict):
                result["characters"][name] = val
            else:
                result["characters_flat"][name] = val

    sf = prompt_dir / "场景提示词.md"
    if sf.exists():
        parsed = _parse_prompt_sections(sf.read_text(encoding="utf-8"))
        for name, val in parsed.items():
            if isinstance(val, dict):
                result["scenes"][name] = val
            else:
                result["scenes_flat"][name] = val

    return result


def _resolve_character_prompt(prompt_map: dict, char: dict) -> str:
    """从提示词映射表中查找角色的提示词，优先按名称、再按 character_id"""
    name = char["name"]
    char_base = char.get("character_base", name)
    char_id = char.get("character_id", "")
    variant = char.get("variant_name", "")

    for candidate in (name, char_base):
        variants = prompt_map.get("characters", {}).get(candidate)
        if variants:
            if variant and variant in variants:
                return variants[variant]
            return variants.get("基础形象") or next(iter(variants.values()), "")

    flat = prompt_map.get("characters_flat", {}).get(name, "")
    if flat:
        return flat
    if char_base != name:
        flat = prompt_map.get("characters_flat", {}).get(char_base, "")
        if flat:
            return flat

    if char_id:
        for variants_dict in prompt_map.get("characters", {}).values():
            if isinstance(variants_dict, dict):
                for k, v in variants_dict.items():
                    if char_id in v:
                        return v

    return ""


def _get_scene_prompt(prompt_map: dict, scene: dict) -> str:
    """从提示词映射表中查找场景的提示词，优先按名称、再按 scene_id"""
    base_name = scene.get("scene_base", scene["name"])
    scene_id = scene.get("scene_id", "")
    variant = scene.get("variant_name", "")

    variants = prompt_map.get("scenes", {}).get(base_name)
    if variants:
        if variant and variant in variants:
            return variants[variant]
        return variants.get("基础形象") or next(iter(variants.values()), "")

    flat = prompt_map.get("scenes_flat", {}).get(base_name, "")
    if flat:
        return flat

    if scene_id:
        for variants_dict in prompt_map.get("scenes", {}).values():
            if isinstance(variants_dict, dict):
                for k, v in variants_dict.items():
                    if scene_id in v:
                        return v

    return ""


def _resolve_prop_prompt(prop: dict) -> str:
    """根据道具 JSON 实时生成提示词"""
    from agents.prompt_factory import PromptBuilder
    return PromptBuilder.generate_prop_prompt(prop)


def _get_base_confirmed_images(project, entity_type: str, entity_name: str) -> list[str]:
    """查找实体（角色/场景）的已确认版本图片路径"""
    asset_dir = project.project_dir / "07_生成素材" / entity_type / entity_name
    if not asset_dir.exists():
        return []

    confirmed_version = None
    for d in sorted(asset_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
        if d.is_dir() and (d / "_confirmed").exists():
            confirmed_version = d.name
            break
    if not confirmed_version:
        versions = sorted([d for d in asset_dir.iterdir() if d.is_dir() and d.name.startswith("v")],
                          key=lambda d: d.stat().st_mtime, reverse=True)
        if versions:
            confirmed_version = versions[0].name
    if not confirmed_version:
        return []

    version_dir = asset_dir / confirmed_version
    return [str(f) for f in sorted(version_dir.glob("*.png"))]


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
        props = VisualBibleExtractor.list_props(project)
        prompt_map = _load_prompt_map(project)

        yield f"📋 检测到 {len(chars)} 个角色，{len(scenes)} 个场景，{len(props)} 个道具\n"
        scene_prompt_count = sum(len(v) if isinstance(v, dict) else 1
                                 for v in prompt_map.get("scenes", {}).values())
        scene_prompt_count += len(prompt_map.get("scenes_flat", {}))
        if scene_prompt_count > 0:
            yield f"📖 已加载 06_提示词/ 场景提示词文件（{scene_prompt_count} 条）\n"

        for char in chars:
            is_variant = not char.get("is_base", True)
            label = f"变体形象" if is_variant else "定妆照"
            yield f"🎨 生成角色{label}：{char['name']}...\n"
            yield from self._generate_character(project, char, prompt_map)
            yield f"✅ {char['name']} 完成\n"

        for scene in scenes:
            is_variant = not scene.get("is_base", True)
            label = "变体场景" if is_variant else "场景概念图"
            yield f"🌆 生成{label}：{scene['name']}...\n"
            yield from self._generate_scene(project, scene, prompt_map)
            yield f"✅ {scene['name']} 完成\n"

        carry_props = [p for p in props if p.get("prop_class") == "随身道具"]
        key_props = [p for p in props if p.get("prop_class") == "关键道具"]
        for prop in props:
            prop_class = prop.get("prop_class", "关键道具")
            yield f"🔧 生成{prop_class}：{prop['name']}...\n"
            yield from self._generate_prop(project, prop)
            yield f"✅ {prop['name']} 完成\n"

        yield "🎉 全部视觉素材生成完成\n"

    def generate_character(self, project: ProjectManager, character_name: str):
        chars = VisualBibleExtractor.list_characters(project)
        char = next((c for c in chars if c["name"] == character_name), None)
        if not char:
            return
        prompt_map = _load_prompt_map(project)
        yield from self._generate_character(project, char, prompt_map)

    def _generate_character(self, project: ProjectManager, char: dict, prompt_map: dict = None):
        is_variant = not char.get("is_base", True)
        file_prompt = ""
        if prompt_map:
            file_prompt = _resolve_character_prompt(prompt_map, char)
        if file_prompt:
            prompt = (
                f"{file_prompt.rstrip('.')}。"
                f"画布分为4格2x2网格：左上脸部特写（胸部以上，正脸）、"
                f"右上全身正面、左下全身侧面（90°侧身）、右下全身背面。"
                f"每格人物居中。纯白背景，无文字遮挡。"
            )
        else:
            appearance = char.get("appearance", "")
            clothing = char.get("clothing", "")
            features = "、".join(char.get("key_features", []))
            prompt = (
                f"'{char['name']}' 的定妆照，纯白背景。"
                f"角色特征：{appearance}。服装：{clothing}。"
                f"标志性特征：{features}。"
                f"画布分为4格2x2网格：左上脸部特写（胸部以上，正脸）、"
                f"右上全身正面、左下全身侧面（90°侧身）、右下全身背面。"
                f"每格人物居中。纯白背景，无文字遮挡。"
            )
        reference_urls = []
        if is_variant:
            char_base = char.get("character_base", "")
            if char_base:
                base_images = _get_base_confirmed_images(project, "角色", char_base)
                if base_images:
                    reference_urls = base_images
                    yield f"  📎 变体参考基础形象已确认图（{len(base_images)}张）\n"
        try:
            if reference_urls:
                urls = self.image_backend.image_to_image(reference_urls[0], prompt, size="1024x1024")
            else:
                urls = self.image_backend.text_to_image(prompt, size="1024x1024", n=1)
            if urls:
                save_dir = project.project_dir / "07_视觉素材" / "角色"
                save_dir.mkdir(parents=True, exist_ok=True)
                save_path = str(save_dir / f"{_sanitize_filename(char['name'])}_四视图.png")
                ImageComposer.download_image(urls[0] if isinstance(urls, list) else urls, save_path)
                yield f"  ✅ 已保存: {save_path}\n"
        except Exception as e:
            yield f"  ❌ 生成失败: {e}\n"

    def generate_scene(self, project: ProjectManager, scene_name: str, angles=None):
        scenes = VisualBibleExtractor.list_scenes(project)
        scene = next((s for s in scenes if s["name"] == scene_name), None)
        if not scene:
            return
        prompt_map = _load_prompt_map(project)
        yield from self._generate_scene(project, scene, prompt_map, angles)

    def _generate_scene(self, project: ProjectManager, scene: dict, prompt_map: dict = None, angles=None):
        if angles is None:
            angles = ["正视图", "左45度", "右45度", "鸟瞰图"]

        is_variant = not scene.get("is_base", True)
        save_dir = project.project_dir / "07_视觉素材" / "场景"
        save_dir.mkdir(parents=True, exist_ok=True)
        angle_images = {}

        scene_desc = ""
        if prompt_map:
            scene_desc = _get_scene_prompt(prompt_map, scene)

        reference_urls = []
        if is_variant:
            scene_base = scene.get("scene_base", "")
            if scene_base:
                base_images = _get_base_confirmed_images(project, "场景", scene_base)
                if base_images:
                    reference_urls = base_images
                    yield f"  📎 变体参考基础场景已确认图（{len(base_images)}张）\n"

        for angle in angles:
            if scene_desc:
                view_desc = ANGLE_MAP.get(angle, angle)
                prompt = (
                    f"{scene_desc} {view_desc}。"
                    f"高质量，电影级光影，细节丰富。"
                )
            else:
                env = scene.get("environment", "")
                lighting = scene.get("lighting", "自然光")
                color_tone = scene.get("color_tone", "自然色调")
                props = "、".join(scene.get("props", []))
                view_desc = ANGLE_MAP.get(angle, angle)
                prompt = (
                    f"'{scene['name']}' 场景概念图，{view_desc}。"
                    f"环境描述：{env}。光线：{lighting}。色调：{color_tone}。"
                    f"关键道具：{props}。无文字，写实风格。"
                    f"blank white background around the scene for compositing. no text or watermark."
                )
            try:
                if reference_urls:
                    ref_img = reference_urls[0]
                    urls = self.image_backend.image_to_image(ref_img, prompt, size="1024x1024")
                else:
                    urls = self.image_backend.text_to_image(prompt, size="1024x1024", n=1)
                if urls:
                    angle_name = angle.replace(" ", "")
                    save_path = str(save_dir / f"{_sanitize_filename(scene['name'])}_{angle_name}.png")
                    ImageComposer.download_image(urls[0] if isinstance(urls, list) else urls, save_path)
                    angle_images[angle_name] = save_path
                    yield f"  ✅ {angle} 已保存\n"
            except Exception as e:
                yield f"  ❌ {angle} 生成失败: {e}\n"

        if len(angle_images) >= 2:
            panorama_path = str(save_dir / f"{_sanitize_filename(scene['name'])}_全景总览.png")
            ImageComposer.compose_scene_panorama(angle_images, scene["name"], panorama_path)
            yield f"  ✅ 全景总览已合成\n"

    def generate_prop(self, project: ProjectManager, prop_name: str):
        props = VisualBibleExtractor.list_props(project)
        prop = next((p for p in props if p["name"] == prop_name), None)
        if not prop:
            return
        yield from self._generate_prop(project, prop)

    def _generate_prop(self, project: ProjectManager, prop: dict):
        prompt = _resolve_prop_prompt(prop)
        prop_class = prop.get("prop_class", "关键道具")
        reference_urls = []
        if prop_class == "随身道具":
            owner_name = prop.get("owner", "")
            if owner_name and owner_name != "null":
                owner_images = _get_base_confirmed_images(project, "角色", owner_name)
                if owner_images:
                    reference_urls = owner_images
                    yield f"  📎 随身道具参考所属角色已确认图（{len(owner_images)}张）\n"
        try:
            if reference_urls:
                urls = self.image_backend.image_to_image(reference_urls[0], prompt, size="1024x1024")
            else:
                urls = self.image_backend.text_to_image(prompt, size="1024x1024", n=1)
            if urls:
                save_dir = project.project_dir / "07_视觉素材" / "道具"
                save_dir.mkdir(parents=True, exist_ok=True)
                save_path = str(save_dir / f"{_sanitize_filename(prop['name'])}.png")
                ImageComposer.download_image(urls[0] if isinstance(urls, list) else urls, save_path)
                yield f"  ✅ 已保存: {save_path}\n"
        except Exception as e:
            yield f"  ❌ 生成失败: {e}\n"

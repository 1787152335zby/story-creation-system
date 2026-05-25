from core.agent_base import AgentBase
from core.project_manager import ProjectManager
from core.style_config import StyleConfig, VISUAL_STYLES, SCREEN_ASPECTS, RENDER_STYLES, STORY_TYPES
from core.visual_bible import VisualBibleExtractor
from tools.content_splitter import split_by_headings, make_split_filename
from tools.constants import ANGLE_MAP
import re
import json
from pathlib import Path


def _build_style_declaration(style: StyleConfig) -> str:
    visual_name = VISUAL_STYLES.get(style.visual_style, {}).get("name", "自动适配")
    aspect_name = SCREEN_ASPECTS.get(style.screen_aspect, {}).get("name", "自适应")
    render_name = style.resolve_render_style_name()
    auto_suffix = ""
    if style.art_style == "7":
        auto_suffix = f"（由「自动适配」根据故事类型「{style.genre}」自动选择）"

    story_name = STORY_TYPES.get(style.story_type, {}).get("name", "未知")
    decl = f"""【整体视觉风格声明】
此风格声明适用于以下所有角色、场景和镜头的提示词生成：
- 故事类型：{story_name}
- 视觉风格：{visual_name}
- 画面比例：{aspect_name}
- 渲染风格：{render_name}{auto_suffix}
"""
    if style.custom_requirements:
        decl += f"- 自定义要求：{style.custom_requirements[:200]}\n"
    decl += "- 配饰/道具：角色携带的配饰和道具应清晰呈现，与角色服装和整体风格保持一致。\n"
    return decl


def _sort_characters(chars: list[dict]) -> list[dict]:
    """排序角色：主角（main）在前，配角在后；变体紧跟基础角色"""
    bases = [c for c in chars if c.get("is_base")]
    variant_map = {}
    for v in chars:
        if not v.get("is_base"):
            base = v.get("character_base", "")
            variant_map.setdefault(base, []).append(v)

    mains = [c for c in bases if c.get("type") == "main"]
    secondaries = [c for c in bases if c.get("type") != "main"]
    sorted_bases = mains + secondaries

    result = []
    for base in sorted_bases:
        name = base["name"]
        result.append(base)
        result.extend(variant_map.get(name, []))
    return result


def _sort_scenes_by_storyboard(scenes: list[dict], storyboard: str) -> list[dict]:
    """按分镜中出现顺序排列场景，未出现的附加到末尾"""
    bases = [s for s in scenes if s.get("is_base")]
    variant_map = {}
    for s in scenes:
        if not s.get("is_base"):
            base = s.get("scene_base", "")
            variant_map.setdefault(base, []).append(s)

    seen_names = set()
    order = []
    for m in re.finditer(r'场景：(\S+)', storyboard):
        name = m.group(1).strip().rstrip('。，,；;')
        if name in seen_names:
            continue
        seen_names.add(name)
        base = next((b for b in bases if b["name"] == name), None)
        if base:
            order.append(base)
            for v in variant_map.get(name, []):
                order.append(v)

    remaining = [b for b in bases if b["name"] not in seen_names]
    for base in remaining:
        order.append(base)
        order.extend(variant_map.get(base["name"], []))
    return order


class PromptBuilder:
    """独立提示词生成工具，可被管线调用也可被 API 单独调用"""

    @staticmethod
    def generate_character_prompt(char: dict, style_decl: str = "", mode: str = "all") -> str:
        """mode: 'base' = L1定妆照, 'prop' = L2道具(需_prop_name), 'all' = 旧版全合一"""
        type_tag = "主要角色" if char.get("type") == "main" else "次要角色"
        is_variant = not char.get("is_base", True)
        char_name = char.get("character_base", char["name"])
        variant_name = char.get("variant_name", "基础形象")

        if is_variant:
            parts = [f"'{char_name}' 的变体形象「{variant_name}」，{type_tag}。"]
            cid = char.get("character_id", "")
            if cid:
                parts.append(f"角色ID: {cid}。")
            if char.get("variant_tag"):
                parts.append(f"变体标签: {char['variant_tag']}。")
            if char.get("based_on"):
                parts.append(f"基于{char['based_on']}，在以下基础上发生了变化：")
            if char.get("feature_desc"):
                parts.append(f"变体特征: {char['feature_desc']}。")
            if char.get("appearance_change"):
                parts.append(f"外貌变化：{char['appearance_change']}。")
            if char.get("clothing_change"):
                parts.append(f"服装变化：{char['clothing_change']}。")
            if char.get("trigger_event"):
                parts.append(f"变化原因：{char['trigger_event']}。")
            accessories = char.get("accessories", [])
            if accessories:
                parts.append(f"配饰/携带道具（与基础形象共用，除非有变化）：{'、'.join(accessories)}。")
            parts.append("动态场景中展示该变化，非定妆照。")
        elif mode == "base":
            parts = [f"'{char_name}' 的定妆照，{type_tag}。"]
            cid = char.get("character_id", "")
            if cid:
                parts.append(f"角色ID: {cid}。")
            if char.get("age"):
                parts.append(f"年龄：{char['age']}。")
            if char.get("gender"):
                parts.append(f"性别：{char['gender']}。")
            if char.get("appearance"):
                appearance = char['appearance']
                for kw in ['持', '拿', '握', '举', '扛', '提', '挥', '砍', '刺', '射', '跑', '跳', '走', '蹲', '跪', '坐', '躺']:
                    appearance = re.sub(rf'[^。，]{{0,10}}{kw}[^。，]*[。，]?', '', appearance)
                appearance = re.sub(r'双手\s*[^自]。*?(?=[。，])', '', appearance)
                if appearance.strip():
                    parts.append(f"外貌特征：{appearance.strip()}。")
            if char.get("clothing"):
                parts.append(f"服装：{char['clothing']}。")
            if char.get("key_features"):
                parts.append(f"标志性特征（面部及头部）：{'、'.join(char['key_features'])}（仅在面部特写中突出，全身照中自然呈现）。")
            accessories = char.get("accessories", [])
            if accessories:
                parts.append(f"配饰/携带道具：{'、'.join(accessories)}。")
            parts.append("纯色背景（灰白渐变），角色居中，全身立姿，双手自然下垂贴于身体两侧，手指伸直并拢，掌心向内，正对镜头，表情自然中性。严禁任何动作姿态、严禁手持任何物品、严禁武器。高质量，电影级光影。")
        elif mode == "prop":
            prop_name = char.get("_prop_name", "")
            parts = [f"'{prop_name}' — {char_name}的配饰道具。"]
            appearance = char.get("_prop_appearance", "")
            if appearance:
                parts.append(f"外观描述：{appearance}。")
            style_note = char.get("_prop_style", "")
            if style_note:
                parts.append(f"风格：{style_note}。")
            parts.append("白色背景，产品展示角度，高清细节。")
        else:
            parts = [f"'{char_name}' 的定妆照，{type_tag}。"]
            if char.get("appearance"):
                parts.append(f"外貌特征：{char['appearance']}。")
            if char.get("clothing"):
                parts.append(f"服装：{char['clothing']}。")
            if char.get("expression"):
                parts.append(f"表情/神态：{char['expression']}。")
            if char.get("pose"):
                parts.append(f"姿态：{char['pose']}。")
            if char.get("accessories"):
                parts.append(f"配饰：{'、'.join(char['accessories'])}。")
            if char.get("key_features"):
                parts.append(f"标志性特征：{'、'.join(char['key_features'])}。")
            parts.append("纯白背景，角色居中，全身照。")
        return " ".join(parts)

    @staticmethod
    def generate_scene_prompt(scene: dict, angle: str = "", base_scene: dict = None) -> str:
        is_variant = not scene.get("is_base", True)
        scene_base = scene.get("scene_base", scene["name"])

        if is_variant:
            parts = [f"'{scene_base}' 的变体场景「{scene.get('variant_name','')}」。"]
            sid = scene.get("scene_id", "")
            if sid:
                parts.append(f"场景ID: {sid}。")
            if scene.get("variant_tag"):
                parts.append(f"变体标签: {scene['variant_tag']}。")
            base = base_scene or {}
            env_text = base.get("environment", "")
            if env_text:
                parts.append(f"基础环境：{env_text}。")
            lighting = base.get("lighting", "")
            if lighting:
                parts.append(f"基础光线：{lighting}。")
            color_tone = base.get("color_tone", "")
            if color_tone:
                parts.append(f"基础色调：{color_tone}。")
            props = base.get("props", [])
            if props:
                parts.append(f"关键道具：{'、'.join(props)}。")
            if scene.get("feature_desc"):
                parts.append(f"变体特征: {scene['feature_desc']}。")
            parts.append("已发生变化：")
            if scene.get("change"):
                parts.append(f"{scene['change']}。")
            if scene.get("trigger_event"):
                parts.append(f"变化原因：{scene['trigger_event']}。")
        else:
            env = scene.get("environment", "")
            lighting = scene.get("lighting", "自然光")
            color_tone = scene.get("color_tone", "自然色调")
            props = "、".join(scene.get("props", []))

            view_desc = ANGLE_MAP.get(angle, angle)

            if angle:
                parts = [f"'{scene['name']}' 场景概念图，{view_desc}。"]
            else:
                parts = [f"'{scene['name']}' 场景概念图。"]
            if env:
                parts.append(f"环境：{env}。")
            parts.append(f"光线：{lighting}。色调：{color_tone}。")
            if props:
                parts.append(f"关键道具：{props}。")
            parts.append("高质量，电影级光影，细节丰富。")
        return " ".join(parts)

    @staticmethod
    def generate_prop_prompt(prop: dict) -> str:
        prop_class = prop.get("prop_class", "关键道具")
        pid = prop.get("prop_id", "")
        parts = [f"'{prop['name']}' — {prop_class}。"]
        if pid:
            parts.append(f"道具ID: {pid}。")
        if prop.get("type"):
            parts.append(f"类型: {prop['type']}。")
        appearance = prop.get("appearance", "") or prop.get("description", "")
        if appearance:
            parts.append(f"外观: {appearance}。")
        if prop.get("category"):
            parts.append(f"类别: {prop['category']}。")
        if prop_class == "随身道具":
            if prop.get("owner"):
                parts.append(f"所属角色: {prop['owner']}。")
            if prop.get("mount_position"):
                parts.append(f"挂载位置: {prop['mount_position']}。")
            parts.append("白色背景，产品展示角度，高清细节。")
        elif prop_class == "关键道具":
            if prop.get("description"):
                parts.append(f"描述: {prop['description']}。")
            if prop.get("bind_plot_node"):
                parts.append(f"关联剧情节点: {prop['bind_plot_node']}。")
            parts.append("独立展示，电影级光影，细节丰富。")
        return " ".join(parts)

    @staticmethod
    def build_shot_prompt(
        shot_text: str,
        characters: list[dict],
        scenes: list[dict],
        style_decl: str = "",
        previous_shot_context: str = ""
    ) -> str:
        """装配式提示词生成 — 精简版，角色/场景详情由参考图承载"""
        parts = []

        if style_decl:
            parts.append(style_decl.strip())

        char_names = [c.get("character_base", c["name"]) for c in characters if c.get("name")]
        if char_names:
            parts.append("出场：" + "、".join(char_names))

        scene_names = [s.get("scene_base", s["name"]) for s in scenes if s.get("name")]
        if scene_names:
            parts.append("场景：" + "、".join(scene_names))

        if previous_shot_context:
            parts.append(f"\n承接上一镜头：{previous_shot_context}")

        if shot_text:
            parts.append(f"\n{shot_text}")

        return "\n".join(parts)

    @staticmethod
    def generate_prompt_for_selection(
        project,
        character_names: list[str] = None,
        scene_names: list[str] = None,
        storyboard_chunk: str = ""
    ) -> str:
        chars = VisualBibleExtractor.list_characters(project)
        scenes = VisualBibleExtractor.list_scenes(project)

        selected_chars = [c for c in chars if not character_names or c["name"] in character_names]
        selected_scenes = [s for s in scenes if not scene_names or s["name"] in scene_names]
        selected_chunk = storyboard_chunk[:2000] if storyboard_chunk else ""

        parts = []
        for c in selected_chars:
            parts.append(PromptBuilder.generate_character_prompt(c, mode="base"))
        for s in selected_scenes:
            parts.append(PromptBuilder.generate_scene_prompt(s))
        if selected_chunk:
            parts.append(f"\n分镜描述：{selected_chunk}")

        return "\n\n".join(parts) if parts else "请输入画面描述"


class PromptFactory(AgentBase):
    """工作流中的提示词生成阶段"""

    @staticmethod
    def _split_variants_from_description(char_data: dict) -> list[dict]:
        """检测角色描述中是否有跨场次服装/姿态/外貌变化，自动拆分为变体"""
        import re
        original_name = char_data["name"]

        # 检测 "第一场穿X，第二场穿Y" / "前期穿X，后期穿Y" 模式
        scene_pattern = r'(?:第一场|前期|白天|平时)[^，。]*?(穿|做|有|保持)(.*?)(?:[，。].*?(?:第二场|后期|夜晚|战斗)[^，。]*?(穿|做|有|呈现)(.*))'

        result = [dict(char_data)]  # 至少返回基础角色本身
        base = result[0]

        # 检查 clothing
        clothing = base.get("clothing", "")
        clothing_match = re.search(r'(?:第一场|前期|白天|平时)[^，。]*?穿(.*?)(?:[，。].*?(?:第二场|后期|夜晚|战斗)[^，。]*?穿(.*))', clothing)
        if clothing_match and clothing_match.group(2):
            base_clothing = clothing_match.group(1).strip()
            variant_clothing = clothing_match.group(2).strip()
            base["clothing"] = base_clothing

            variant_name = f"{original_name}_{variant_clothing[:4]}"
            existing = next((r for r in result if r["name"] == variant_name), None)
            if not existing:
                v = dict(base)
                v["name"] = variant_name
                v["is_base"] = False
                v["character_base"] = original_name
                v["variant_name"] = variant_clothing[:10]
                v["clothing_change"] = f"换穿{variant_clothing}"
                v["trigger_event"] = "场景切换"
                v.pop("variants", None)
                result.append(v)

        # 检查 pose
        pose = base.get("pose", "")
        pose_match = re.search(r'(?:第一场|前期|白天|平时)[^，。]*?([\u4e00-\u9fff].*?)(?:[，。].*?(?:第二场|后期|夜晚|战斗)[^，。]*?([\u4e00-\u9fff].*))', pose)
        if pose_match and pose_match.group(2):
            base_pose = pose_match.group(1).strip()
            variant_pose = pose_match.group(2).strip()
            base["pose"] = base_pose

            # 判断是否已经因为 clothing 创建了同名变体，如果是则给该变体补充 pose_change
            has_clothing_variant = clothing_match and clothing_match.group(2) and len(result) > 1
            if has_clothing_variant:
                v = result[1]
                v["pose_change"] = variant_pose
            else:
                variant_name = f"{original_name}_第二场"
                existing = next((r for r in result if r["name"] == variant_name), None)
                if not existing:
                    v = dict(base)
                    v["name"] = variant_name
                    v["is_base"] = False
                    v["character_base"] = original_name
                    v["variant_name"] = variant_pose[:10]
                    v["pose_change"] = variant_pose
                    v["trigger_event"] = "场景切换"
                    v.pop("variants", None)
                    result.append(v)

        return result

    def run(self, project: ProjectManager, style: StyleConfig, input_content: str) -> str:
        return "".join(self.run_stream(project, style, input_content))

    def run_stream(self, project: ProjectManager, style: StyleConfig, input_content: str):
        chars = VisualBibleExtractor.list_characters(project)
        # 检测角色服装/外貌变化，自动拆分为变体
        expanded_chars = []
        for c in chars:
            if c.get("is_base", True):
                expanded_chars.extend(PromptFactory._split_variants_from_description(c))
            else:
                expanded_chars.append(c)
        chars = expanded_chars
        # 将新拆分的变体写回 JSON 文件
        chars_dir = project.project_dir / "04_角色场景" / "角色"
        if chars_dir.exists():
            for c in chars:
                path = chars_dir / f"{c['name']}.json"
                path.write_text(json.dumps(c, ensure_ascii=False, indent=2), encoding="utf-8")
        scenes = VisualBibleExtractor.list_scenes(project)
        storyboard = input_content

        output_dir = project.project_dir / "06_提示词"
        output_dir.mkdir(parents=True, exist_ok=True)

        # 清理旧版文件（分镜提示词*.md 是旧版本遗留的）
        for f in output_dir.glob("分镜提示词*.md"):
            f.unlink()

        yield f"📋 检测到 {len(chars)} 个角色，{len(scenes)} 个场景\n\n"

        # === 角色提示词（排序：主角→配角，变体紧跟基础角色） ===
        yield "## 角色提示词\n\n"
        sorted_chars = _sort_characters(chars)
        char_lines = []
        for c in sorted_chars:
            is_base = c.get("is_base", True)
            is_variant = not is_base
            if is_base:
                base_name = c["name"]
                variants_under = [x for x in sorted_chars if not x.get("is_base") and x.get("character_base") == base_name]
                header = f"### {base_name}\n"
                char_lines.append(header)
                yield header
                if variants_under:
                    bp = PromptBuilder.generate_character_prompt(c, mode="base")
                    bline = f"#### {c.get('variant_name','基础形象')}\n{bp}\n"
                    char_lines.append(bline)
                    yield bline
                    for v in variants_under:
                        vp = PromptBuilder.generate_character_prompt(v, mode="base")
                        vline = f"#### {v.get('variant_name','')}\n{vp}\n"
                        char_lines.append(vline)
                        yield vline
                else:
                    cp = PromptBuilder.generate_character_prompt(c, mode="base")
                    cline = f"{cp}\n"
                    char_lines.append(cline)
                    yield cline

        full_char_output = "# 角色提示词\n\n" + "\n".join(char_lines)
        output_dir.joinpath("角色提示词.md").write_text(full_char_output, encoding="utf-8")
        yield "✅ 角色提示词已保存\n\n"

        # === 场景提示词（按分镜中出现顺序排列，变体紧跟基础场景） ===
        yield "## 场景提示词\n\n"
        sorted_scenes = _sort_scenes_by_storyboard(scenes, storyboard)
        scene_lines = []
        for s in sorted_scenes:
            is_base = s.get("is_base", True)
            if is_base:
                base_name = s["name"]
                variants_under = [x for x in sorted_scenes if not x.get("is_base") and x.get("scene_base") == base_name]
                sh = f"### {base_name}\n"
                scene_lines.append(sh)
                yield sh
                if variants_under:
                    sp = PromptBuilder.generate_scene_prompt(s)
                    sl = f"#### {s.get('variant_name','基础形象')}\n{sp}\n"
                    scene_lines.append(sl)
                    yield sl
                    for sv in variants_under:
                        svp = PromptBuilder.generate_scene_prompt(sv, base_scene=s)
                        svl = f"#### {sv.get('variant_name','')}\n{svp}\n"
                        scene_lines.append(svl)
                        yield svl
                else:
                    sp = PromptBuilder.generate_scene_prompt(s)
                    sl = f"{sp}\n"
                    scene_lines.append(sl)
                    yield sl

        full_scene_output = "# 场景提示词\n\n" + "\n".join(scene_lines)
        output_dir.joinpath("场景提示词.md").write_text(full_scene_output, encoding="utf-8")
        yield "✅ 场景提示词已保存\n\n"

        # === 分镜提示词（按幕/集分组，每个镜头一条，每集一文件） ===
        if storyboard.strip():
            yield "## 分镜提示词\n\n"
            style_decl = _build_style_declaration(style)

            char_map = {c["name"]: c for c in chars}
            scene_map = {s["name"]: s for s in scenes}

            # 直接从分镜脚本目录读取每集文件，不依赖 heading 检测
            sb_dir = project.project_dir / "05_分镜脚本"
            sb_split_files = sorted(sb_dir.glob("分镜脚本_*.md"))
            groups = []
            if sb_split_files:
                for sf in sb_split_files:
                    label = sf.stem.replace("分镜脚本_", "")
                    content = sf.read_text(encoding="utf-8")
                    groups.append((label, content))
            else:
                # 无分集文件，退回到 heading 检测
                groups = split_by_headings(storyboard)

            all_shot_prompts = []

            for group_label, group_content in groups:
                shot_prompts = []

                raw_shots = re.split(r'\n---\n', group_content)
                shots_parsed = []

                for rs in raw_shots:
                    rs = rs.strip()
                    if not rs:
                        continue
                    if re.match(r'镜头\d+', rs):
                        shots_parsed.append(rs)
                    else:
                        inner = re.findall(r'(镜头\d+\s*\|.*?)(?=\n镜头\d+|\Z)', rs, re.DOTALL)
                        if inner:
                            shots_parsed.extend(inner)
                        else:
                            shots_parsed.append(rs)

                for i, shot in enumerate(shots_parsed):
                    shot = shot.strip()
                    if not shot:
                        continue

                    shot_chars = re.search(r'出场角色：(.+)', shot)
                    shot_scene = re.search(r'场景：(.+)', shot)
                    shot_names = [n.strip() for n in shot_chars.group(1).split('、') if n.strip()] if shot_chars else []
                    scene_name = shot_scene.group(1).strip() if shot_scene else ""

                    body_lines = []
                    in_header = True
                    for line in shot.split("\n"):
                        stripped = line.strip()
                        if in_header:
                            if stripped.startswith("---"):
                                in_header = False
                                continue
                            if stripped.startswith("出场角色") or stripped.startswith("场景") or stripped.startswith("转场") or re.match(r'镜头\d+', stripped):
                                continue
                            in_header = False
                        body_lines.append(line)
                    body_text = "\n".join(body_lines).strip()

                    shot_label = f"{group_label} 镜头{i+1}"
                    yield f"### {shot_label}\n\n"

                    selected_chars = [char_map.get(n, {"name": n}) for n in shot_names]
                    selected_scenes = [scene_map.get(scene_name, {"name": scene_name})] if scene_name else []

                    shot_result = PromptBuilder.build_shot_prompt(
                        body_text, selected_chars, selected_scenes, style_decl
                    )
                    yield shot_result + "\n\n"

                    shot_prompts.append(f"### 镜头{i+1}\n\n{shot_result.strip()}")
                    yield "\n\n---\n\n"

                if shot_prompts:
                    all_shot_prompts.append((group_label, shot_prompts))
                    safe_name = re.sub(r'[\\/*?:"<>|#\s]', "", group_label)
                    filename = f"提示词_{safe_name}.md"
                    output_dir.joinpath(filename).write_text(
                        f"# {group_label} 镜头提示词\n\n" + "\n\n".join(shot_prompts),
                        encoding="utf-8"
                    )
                    yield f"✅ 提示词_{safe_name}.md 已保存\n\n"

            if all_shot_prompts:
                combined = []
                for label, prompts in all_shot_prompts:
                    combined.append(f"# {label} 镜头提示词\n\n" + "\n\n".join(prompts))
                output_dir.joinpath("提示词.md").write_text(
                    "\n\n".join(combined), encoding="utf-8"
                )
        else:
            yield "⏭️ 暂无分镜内容，跳过分镜提示词\n"

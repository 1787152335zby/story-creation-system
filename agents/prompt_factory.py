from core.agent_base import AgentBase
from core.project_manager import ProjectManager
from core.style_config import StyleConfig, VISUAL_STYLES, SCREEN_ASPECTS, RENDER_STYLES, STORY_TYPES
from core.visual_bible import VisualBibleExtractor
from tools.content_splitter import split_by_headings, make_split_filename
import re
import json
from pathlib import Path


def _build_style_declaration(style: StyleConfig) -> str:
    """根据风格配置生成整体视觉风格声明"""
    visual_name = VISUAL_STYLES.get(style.visual_style, {}).get("name", "自动适配")
    aspect_name = SCREEN_ASPECTS.get(style.screen_aspect, {}).get("name", "自适应")
    render_name = RENDER_STYLES.get(style.render_style, {}).get("name", "未指定") if hasattr(style, 'render_style') and style.render_style else "写实/真人"
    story_name = STORY_TYPES.get(style.story_type, {}).get("name", "未知")

    decl = f"""【整体视觉风格声明】
此风格声明适用于以下所有角色、场景和镜头的提示词生成：

- 故事类型：{story_name}
- 视觉风格：{visual_name}
- 画面比例：{aspect_name}
- 渲染风格：{render_name}
"""
    if hasattr(style, 'custom_requirements') and style.custom_requirements:
        decl += f"- 自定义要求：{style.custom_requirements[:200]}\n"
    return decl


class PromptBuilder:
    """独立提示词生成工具，可被管线调用也可被 API 单独调用"""

    @staticmethod
    def generate_character_prompt(char: dict, style_decl: str = "") -> str:
        type_tag = "主要角色" if char.get("type") == "main" else "次要角色"
        is_variant = not char.get("is_base", True)
        char_name = char.get("character_base", char["name"])
        variant_name = char.get("variant_name", "基础形象")

        if is_variant:
            parts = [f"'{char_name}' 的变体形象「{variant_name}」，{type_tag}。"]
            if char.get("based_on"):
                parts.append(f"基于{char['based_on']}，在以下基础上发生了变化：")
            if char.get("appearance_change"):
                parts.append(f"外貌变化：{char['appearance_change']}。")
            if char.get("clothing_change"):
                parts.append(f"服装变化：{char['clothing_change']}。")
            if char.get("trigger_event"):
                parts.append(f"变化原因：{char['trigger_event']}。")
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

        if is_variant:
            parts.append("动态场景中展示该变化，非定妆照。")
        else:
            parts.append("纯白背景，角色居中，全身照。")
        return " ".join(parts)

    @staticmethod
    def generate_scene_prompt(scene: dict, angle: str = "正视图") -> str:
        is_variant = not scene.get("is_base", True)
        scene_base = scene.get("scene_base", scene["name"])

        if is_variant:
            parts = [f"'{scene_base}' 的变体场景「{scene.get('variant_name','')}」。"]
            if scene.get("based_on"):
                parts.append(f"基于{scene['based_on']}，已发生变化：")
            if scene.get("change"):
                parts.append(f"{scene['change']}。")
            if scene.get("trigger_event"):
                parts.append(f"变化原因：{scene['trigger_event']}。")
        else:
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

            parts = [f"'{scene['name']}' 场景概念图，{view_desc}。"]
            if env:
                parts.append(f"环境：{env}。")
            parts.append(f"光线：{lighting}。色调：{color_tone}。")
            if props:
                parts.append(f"关键道具：{props}。")
            parts.append("高质量，电影级光影，细节丰富。")
        return " ".join(parts)

    @staticmethod
    def build_shot_prompt(
        shot_text: str,
        characters: list[dict],
        scenes: list[dict],
        style_decl: str = ""
    ) -> str:
        """装配式提示词生成 — 直接组合已有信息，不调用 LLM 再生成"""
        parts = []

        if style_decl:
            parts.append(style_decl.strip())

        char_info = []
        for c in characters:
            if not c.get("name"):
                continue
            is_variant = not c.get("is_base", True)
            name = c.get("character_base", c["name"])
            if is_variant:
                change = c.get("appearance_change", "") or c.get("clothing_change", "")
                if change:
                    char_info.append(f"{name}（{change}）")
                else:
                    char_info.append(name)
            else:
                appearance = c.get("appearance", "")[:60]
                clothing = c.get("clothing", "")[:30]
                label = name
                if appearance:
                    label += f"（{appearance}）"
                if clothing:
                    label += f"，穿{clothing}"
                char_info.append(label)
        if char_info:
            parts.append("角色：" + "；".join(char_info))

        if scenes and scenes[0].get("name"):
            s = scenes[0]
            is_variant = not s.get("is_base", True)
            if is_variant and s.get("change"):
                parts.append(f"场景：{s.get('scene_base', s['name'])}（{s['change'][:60]}）")
            else:
                env = s.get("environment", "")[:60]
                lighting = s.get("lighting", "")
                label = s["name"]
                if env:
                    label += f"（{env}）"
                if lighting:
                    label += f"，{lighting}"
                parts.append(f"场景：{label}")

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
            parts.append(PromptBuilder.generate_character_prompt(c))
        for s in selected_scenes:
            parts.append(PromptBuilder.generate_scene_prompt(s))
        if selected_chunk:
            parts.append(f"\n分镜描述：{selected_chunk}")

        return "\n\n".join(parts) if parts else "请输入画面描述"


class PromptFactory(AgentBase):
    """工作流中的提示词生成阶段"""

    def run(self, project: ProjectManager, style: StyleConfig, input_content: str) -> str:
        return "".join(self.run_stream(project, style, input_content))

    def run_stream(self, project: ProjectManager, style: StyleConfig, input_content: str):
        chars = VisualBibleExtractor.list_characters(project)
        scenes = VisualBibleExtractor.list_scenes(project)
        storyboard = input_content

        output_dir = project.project_dir / "06_提示词"
        output_dir.mkdir(parents=True, exist_ok=True)

        yield f"📋 检测到 {len(chars)} 个角色，{len(scenes)} 个场景\n\n"

        # === 角色提示词（层级结构：角色 → 变体） ===
        yield "## 角色提示词\n\n"
        char_lines = []
        bases = [c for c in chars if c.get("is_base")]
        variant_map = {}
        for v in chars:
            if not v.get("is_base"):
                base = v.get("character_base", "")
                variant_map.setdefault(base, []).append(v)

        for c in bases:
            base_name = c["name"]
            header = f"### {base_name}\n"
            char_lines.append(header)
            yield header
            variant_list = variant_map.get(base_name, [])
            if variant_list:
                bp = PromptBuilder.generate_character_prompt(c)
                bline = f"#### {c.get('variant_name','基础形象')}\n{bp}\n"
                char_lines.append(bline)
                yield bline
                for v in variant_list:
                    vp = PromptBuilder.generate_character_prompt(v)
                    vline = f"#### {v.get('variant_name','')}\n{vp}\n"
                    char_lines.append(vline)
                    yield vline
            else:
                cp = PromptBuilder.generate_character_prompt(c)
                cline = f"{cp}\n"
                char_lines.append(cline)
                yield cline

        full_char_output = "# 角色提示词\n\n" + "\n".join(char_lines)
        output_dir.joinpath("角色提示词.md").write_text(full_char_output, encoding="utf-8")
        yield "✅ 角色提示词已保存\n\n"

        # === 场景提示词（支持变体） ===
        yield "## 场景提示词\n\n"
        scene_lines = []
        scene_bases = [s for s in scenes if s.get("is_base")]
        scene_variant_map = {}
        for s in scenes:
            if not s.get("is_base"):
                base = s.get("scene_base", "")
                scene_variant_map.setdefault(base, []).append(s)

        for s in scene_bases:
            base_name = s["name"]
            sh = f"### {base_name}\n"
            scene_lines.append(sh)
            yield sh
            sv_list = scene_variant_map.get(base_name, [])
            if sv_list:
                sp = PromptBuilder.generate_scene_prompt(s)
                sl = f"#### {s.get('variant_name','基础形象')}\n{sp}\n"
                scene_lines.append(sl)
                yield sl
                for sv in sv_list:
                    svp = PromptBuilder.generate_scene_prompt(sv)
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

        # === 分镜提示词（按幕/集分组，每个镜头一条） ===
        if storyboard.strip():
            yield "## 分镜提示词\n\n"
            style_decl = _build_style_declaration(style)

            # Build lookup maps
            char_map = {c["name"]: c for c in chars}
            scene_map = {s["name"]: s for s in scenes}

            # Split storyboard by act/episode headers
            groups = split_by_headings(storyboard)
            all_shot_prompts = []

            for heading, group_content in groups:
                group_label = heading.strip().lstrip("#").strip() if heading else "全部"
                shot_prompts = []

                # Parse shots by --- delimiter (new format: has 出场角色/场景 fields)
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

                    # Extract 出场角色 and 场景 from new format
                    shot_chars = re.search(r'出场角色：(.+)', shot)
                    shot_scene = re.search(r'场景：(.+)', shot)
                    shot_names = [n.strip() for n in shot_chars.group(1).split('、') if n.strip()] if shot_chars else []
                    scene_name = shot_scene.group(1).strip() if shot_scene else ""

                    # Extract the narrative / description portion
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

                    # Build prompt with matched character/scene references
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
                    filename = f"分镜提示词_{safe_name}.md"
                    output_dir.joinpath(filename).write_text(
                        f"# {group_label} 分镜提示词\n\n" + "\n\n".join(shot_prompts),
                        encoding="utf-8"
                    )
                    yield f"✅ {group_label} 分镜提示词已保存\n\n"

            if all_shot_prompts:
                combined = []
                for label, prompts in all_shot_prompts:
                    combined.append(f"# {label} 分镜提示词\n\n" + "\n\n".join(prompts))
                output_dir.joinpath("分镜提示词.md").write_text(
                    "\n\n".join(combined), encoding="utf-8"
                )
        else:
            yield "⏭️ 暂无分镜内容，跳过分镜提示词\n"

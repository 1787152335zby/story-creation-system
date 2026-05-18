from core.agent_base import AgentBase
from core.project_manager import ProjectManager
from core.style_config import StyleConfig
from core.visual_bible import VisualBibleExtractor
from tools.content_splitter import split_by_headings, make_split_filename
import re


class PromptBuilder:
    """独立提示词生成工具，可被管线调用也可被 API 单独调用"""

    @staticmethod
    def generate_character_prompt(char: dict) -> str:
        type_tag = "主要角色" if char.get("type") == "main" else "次要角色"
        parts = [f"'{char['name']}' 的定妆照，{type_tag}。"]
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
    def generate_scene_prompt(scene: dict, angle: str = "正视图") -> str:
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
    def generate_storyboard_shot_prompt(
        shot_text: str,
        characters: list[dict],
        scenes: list[dict],
        style_context: str = ""
    ) -> str:
        char_refs = "\n".join(
            f"- {c['name']}（{'主要' if c.get('type')=='main' else '次要'}"
            f"：{c.get('appearance','')[:50]}"
            f"，服装：{c.get('clothing','')[:30]}）"
            for c in characters if c.get("status") == "confirmed"
        )
        scene_refs = "\n".join(
            f"- {s['name']}：{s.get('environment','')[:50]}"
            f"，光线：{s.get('lighting','')}"
            for s in scenes
        )

        prompt = f"""你是一位专业的 AI 视频提示词工程师。请根据下列信息生成一个镜头的高质量视频生成提示词。

## 角色参考
{char_refs or '无'}

## 场景参考
{scene_refs or '无'}

## 镜头内容
{shot_text}

## 要求
- 生成一个完整的提示词，包含：镜头运动、人物动作、表情、环境氛围
- 引用角色外貌时保持一致性
- 直接输出提示词内容，不要额外说明

{style_context}
"""
        return prompt

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

        # === 角色提示词 ===
        yield "## 角色提示词\n\n"
        char_lines = []
        for c in chars:
            line = f"### {c['name']}\n{PromptBuilder.generate_character_prompt(c)}"
            char_lines.append(line)
            yield line + "\n\n"
        output_dir.joinpath("角色提示词.md").write_text(
            "# 角色提示词\n\n" + "\n\n".join(char_lines), encoding="utf-8"
        )
        yield "✅ 角色提示词已保存\n\n"

        # === 场景提示词 ===
        yield "## 场景提示词\n\n"
        scene_lines = []
        for s in scenes:
            line = f"### {s['name']}\n{PromptBuilder.generate_scene_prompt(s)}"
            scene_lines.append(line)
            yield line + "\n\n"
        output_dir.joinpath("场景提示词.md").write_text(
            "# 场景提示词\n\n" + "\n\n".join(scene_lines), encoding="utf-8"
        )
        yield "✅ 场景提示词已保存\n\n"

        # === 分镜提示词（按幕/集分组，每个镜头一条） ===
        if storyboard.strip():
            yield "## 分镜提示词\n\n"
            style_ctx = self.get_style_context(style)

            # Split storyboard by act/episode headers
            groups = split_by_headings(storyboard)
            all_shot_prompts = []

            for heading, group_content in groups:
                group_label = heading.strip().lstrip("#").strip() if heading else "全部"
                shot_prompts = []

                # Extract individual shots (镜头001 ... ---)
                shot_pattern = re.compile(
                    r'(镜头\d+\s*\|[^➜]*?(?:➜\s*(?:镜头\d+|下个镜头))?(?:\n---)?)',
                    re.MULTILINE
                )
                # Fallback: split by --- or 镜头 marker
                shots = []
                raw_shots = re.split(r'\n---\n', group_content)
                for rs in raw_shots:
                    rs = rs.strip()
                    if not rs:
                        continue
                    if re.match(r'镜头\d+', rs):
                        shots.append(rs)
                    else:
                        # Try to find shot markers within the block
                        inner_shots = re.findall(r'(镜头\d+\s*\|.*?)(?=\n镜头\d+|\Z)', rs, re.DOTALL)
                        if inner_shots:
                            shots.extend(inner_shots)
                        else:
                            shots.append(rs)

                for i, shot in enumerate(shots):
                    shot = shot.strip()
                    if not shot:
                        continue
                    shot_label = f"{group_label} 镜头{i+1}"
                    yield f"### {shot_label}\n\n"

                    prompt = PromptBuilder.generate_storyboard_shot_prompt(shot, chars, scenes, style_ctx)
                    shot_result = ""
                    for token in self.call_llm_stream(prompt, "", temperature=0.7):
                        shot_result += token
                        yield token

                    shot_prompts.append(f"### 镜头{i+1}\n\n{shot_result.strip()}")
                    yield "\n\n---\n\n"

                if shot_prompts:
                    all_shot_prompts.append((group_label, shot_prompts))
                    # Save per-group file
                    group_file = f"分镜提示词_{heading}.md" if heading else "分镜提示词.md"
                    safe_name = re.sub(r'[\\/*?:"<>|#\s]', "", group_label)
                    filename = f"分镜提示词_{safe_name}.md"
                    output_dir.joinpath(filename).write_text(
                        f"# {group_label} 分镜提示词\n\n" + "\n\n".join(shot_prompts),
                        encoding="utf-8"
                    )
                    yield f"✅ {group_label} 分镜提示词已保存\n\n"

            # Save combined file
            if all_shot_prompts:
                combined = []
                for label, prompts in all_shot_prompts:
                    combined.append(f"# {label} 分镜提示词\n\n" + "\n\n".join(prompts))
                output_dir.joinpath("分镜提示词.md").write_text(
                    "\n\n".join(combined), encoding="utf-8"
                )
        else:
            yield "⏭️ 暂无分镜内容，跳过分镜提示词\n"

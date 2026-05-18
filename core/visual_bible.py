import json
import re
from pathlib import Path
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from llm.client import LLMClient

SEGMENT_EXTRACT_PROMPT = """你是一位专业的剧本分析师。请分析以下剧本片段，提取其中出现的角色和场景。

对每个角色判断类型：
- "main": 出现在多场、有台词、推动剧情的为主要角色
- "minor": 仅在此片段出现、台词少的为次要角色

输出格式为JSON：
{
  "characters": [
    {
      "name": "角色名",
      "type": "main" 或 "minor",
      "appearance": "外貌特征综合描述（年龄、脸型、发型、五官特征、身高体型等）",
      "age": "年龄",
      "gender": "男/女",
      "clothing": "服装描述（颜色、材质、款式）",
      "expression": "表情/神态（如冷峻、温柔、阴险、微笑等）",
      "pose": "典型姿态/动作（如站立、骑马、持剑、坐等）",
      "accessories": ["配饰1", "配饰2"],
      "key_features": ["标志性特征1", "标志性特征2"]
    }
  ],
  "scenes": [
    {
      "name": "场景名",
      "environment": "环境描述（空间布局、装修风格、关键物品位置）",
      "lighting": "光线描述",
      "color_tone": "色调描述",
      "props": ["关键道具1", "关键道具2"]
    }
  ],
  "scene_characters": {
    "场景名": ["角色1", "角色2"]
  }
}

只输出JSON，不要其他文字。
"""

CHANGE_DETECT_PROMPT = """你是一位专业的剧本状态跟踪员。请分析以下剧本，找出角色和场景的状态变化事件。

状态变化的定义：
1. 角色变化：受伤、换装、变老/变年轻、妆容变化、发型变化、佩戴新道具等
2. 场景变化：破坏、重建、装修、火烧、水淹、季节变化、时间推移等

只关注「形象上可见的变化」——角色内心变化不算。

输出格式为JSON：
{
  "character_changes": [
    {
      "character_name": "林深",
      "variant_name": "受伤形象",
      "based_on": "林深_基础形象",
      "appearance_change": "右脸颊贴纱布绷带，嘴角瘀青",
      "clothing_change": "夹克右袖被划破",
      "trigger_event": "第3场被阿虎用刀划伤",
      "applies_from": "第3场",
      "applies_to": "第10场（之后伤口愈合）"
    }
  ],
  "scene_changes": [
    {
      "scene_name": "地下室",
      "variant_name": "爆炸后",
      "based_on": "地下室_基础形象",
      "change": "天花板塌陷，地面碎石，水管爆裂漏水",
      "trigger_event": "第15场爆炸",
      "applies_from": "第15场"
    }
  ]
}

只输出JSON，不要其他文字。
"""


def _ensure_variant_name(name: str, variant: str) -> str:
    """生成唯一的变体名称"""
    return f"{name}_{variant}"


def _split_variant_name(unique_name: str) -> tuple:
    """从唯一名称中解析角色名和变体名"""
    parts = unique_name.rsplit("_", 1)
    if len(parts) == 2:
        return parts[0], parts[1]
    return parts[0], None


class VisualBibleExtractor:
    @staticmethod
    def _get_base_name(char_name: str) -> str:
        """从唯一名称获取基础角色名"""
        return _split_variant_name(char_name)[0]

    @staticmethod
    def extract_all(project) -> dict:
        """分段提取所有角色/场景，合并去重"""
        script_path = project.project_dir / "03_完整剧本" / "完整剧本.md"
        if not script_path.exists():
            files = sorted((project.project_dir / "03_完整剧本").glob("完整剧本_*.md"))
            script_content = "\n\n".join(f.read_text(encoding="utf-8") for f in files) if files else ""
        else:
            script_content = script_path.read_text(encoding="utf-8")

        if not script_content.strip():
            return {"characters": [], "scenes": []}

        # Segment by scene markers
        segments = re.split(r'(第[一二三四五六七八九十百千\d]+场)', script_content)

        if len(segments) <= 1:
            segments = [script_content]

        client = LLMClient()
        all_chars: dict[str, dict] = {}
        all_scenes: dict[str, dict] = {}
        scene_char_map: dict[str, list[str]] = {}

        # ── Pass 1: Extract base characters and scenes ──
        batch_size = 3
        for batch_start in range(0, len(segments), batch_size * 2):
            batch_text = ""
            for i in range(batch_start, min(batch_start + batch_size * 2, len(segments)), 2):
                if i + 1 < len(segments):
                    batch_text += segments[i] + segments[i + 1] + "\n"
                else:
                    batch_text += segments[i] + "\n"

            if not batch_text.strip():
                continue

            batch_context = ""
            for ctx_header in re.finditer(r'^#{1,2}\s+(第[^场\n]+)', batch_text, re.MULTILINE):
                batch_context = ctx_header.group(1)

            batch_text = batch_text[:6000]
            if batch_context and not batch_text.startswith(f"当前上下文：{batch_context}"):
                batch_text = f"当前上下文：{batch_context}\n\n{batch_text}"

            result = ""
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(client.chat, SEGMENT_EXTRACT_PROMPT, batch_text, 0.3)
                try:
                    result = future.result(timeout=120)
                except TimeoutError:
                    continue
                except Exception:
                    continue

            json_match = re.search(r"\{.*\}", result, re.DOTALL)
            if not json_match:
                continue
            try:
                data = json.loads(json_match.group())
            except json.JSONDecodeError:
                continue

            for char in data.get("characters", []):
                name = char["name"]
                if name in all_chars:
                    existing = all_chars[name]
                    if char.get("type") == "main":
                        existing["type"] = "main"
                    for field in ["appearance", "clothing", "expression", "pose"]:
                        if char.get(field) and not existing.get(field):
                            existing[field] = char[field]
                    existing["accessories"] = list(set(existing.get("accessories", []) + char.get("accessories", [])))
                    existing["key_features"] = list(set(existing.get("key_features", []) + char.get("key_features", [])))
                else:
                    # Ensure base fields
                    char["status"] = "pending"
                    char["is_base"] = True
                    char["variant_name"] = "基础形象"
                    char["character_base"] = name
                    char["based_on"] = None
                    char["variants"] = []
                    all_chars[name] = char

            for scene in data.get("scenes", []):
                name = scene["name"]
                if name not in all_scenes:
                    scene["status"] = "pending"
                    scene["is_base"] = True
                    scene["variant_name"] = "基础形象"
                    scene["scene_base"] = name
                    scene["based_on"] = None
                    scene["variants"] = []
                    all_scenes[name] = scene

            for sc_name, char_names in data.get("scene_characters", {}).items():
                if sc_name not in scene_char_map:
                    scene_char_map[sc_name] = []
                scene_char_map[sc_name] = list(set(scene_char_map[sc_name] + char_names))

        # Link characters to scenes
        for char_name, char in all_chars.items():
            related = []
            for sc_name, char_names in scene_char_map.items():
                if char_name in char_names:
                    related.append(sc_name)
            if related:
                char["related_scenes"] = related

        # ── Pass 2: Detect state changes ──
        change_prompt_text = script_content[:8000]
        change_result = ""
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(client.chat, CHANGE_DETECT_PROMPT, change_prompt_text, 0.3)
            try:
                change_result = future.result(timeout=120)
            except (TimeoutError, Exception):
                pass

        if change_result:
            json_match = re.search(r"\{.*\}", change_result, re.DOTALL)
            if json_match:
                try:
                    changes = json.loads(json_match.group())
                    for cc in changes.get("character_changes", []):
                        base_name = cc["character_name"]
                        if base_name in all_chars:
                            base = all_chars[base_name]
                            variant_unique = _ensure_variant_name(base_name, cc["variant_name"])
                            variant = {
                                "name": variant_unique,
                                "character_base": base_name,
                                "type": base.get("type", "minor"),
                                "is_base": False,
                                "variant_name": cc["variant_name"],
                                "based_on": f"{base_name}_基础形象",
                                "appearance": base.get("appearance", ""),
                                "clothing": base.get("clothing", ""),
                                "appearance_change": cc.get("appearance_change", ""),
                                "clothing_change": cc.get("clothing_change", ""),
                                "expression": base.get("expression", ""),
                                "trigger_event": cc.get("trigger_event", ""),
                                "applies_from": cc.get("applies_from", ""),
                                "applies_to": cc.get("applies_to", ""),
                                "status": "pending",
                            }
                            if variant_unique not in all_chars:
                                all_chars[variant_unique] = variant
                                base["variants"].append(variant_unique)
                    for sc in changes.get("scene_changes", []):
                        base_name = sc["scene_name"]
                        if base_name in all_scenes:
                            base = all_scenes[base_name]
                            variant_unique = _ensure_variant_name(base_name, sc["variant_name"])
                            variant = {
                                "name": variant_unique,
                                "scene_base": base_name,
                                "is_base": False,
                                "variant_name": sc["variant_name"],
                                "based_on": f"{base_name}_基础形象",
                                "environment": base.get("environment", ""),
                                "lighting": base.get("lighting", ""),
                                "color_tone": base.get("color_tone", ""),
                                "change": sc.get("change", ""),
                                "trigger_event": sc.get("trigger_event", ""),
                                "applies_from": sc.get("applies_from", ""),
                                "status": "pending",
                            }
                            if variant_unique not in all_scenes:
                                all_scenes[variant_unique] = variant
                                base["variants"].append(variant_unique)
                except json.JSONDecodeError:
                    pass

        # Save to files
        VisualBibleExtractor._save_to_files(project, all_chars, all_scenes)
        return {"characters": list(all_chars.values()), "scenes": list(all_scenes.values())}

    @staticmethod
    def extract_character(project, character_name: str) -> dict | None:
        """增量提取单个角色的信息"""
        script_path = project.project_dir / "03_完整剧本" / "完整剧本.md"
        if not script_path.exists():
            files = sorted((project.project_dir / "03_完整剧本").glob("完整剧本_*.md"))
            script_content = "\n\n".join(f.read_text(encoding="utf-8") for f in files) if files else ""
        else:
            script_content = script_path.read_text(encoding="utf-8")

        prompt = f"""从以下剧本中提取角色「{character_name}」的详细信息。

输出格式为JSON：
{{
  "name": "{character_name}",
  "type": "main" 或 "minor",
  "appearance": "外貌特征综合描述",
  "age": "年龄",
  "gender": "男/女",
  "clothing": "服装描述",
  "expression": "表情/神态",
  "pose": "典型姿态",
  "accessories": ["配饰"],
  "key_features": ["特征"],
  "related_scenes": ["该角色出现的场景名"]
}}

只输出JSON。"""

        client = LLMClient()
        result = ""
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(client.chat, prompt, script_content[:8000], 0.3)
            try:
                result = future.result(timeout=120)
            except (TimeoutError, Exception):
                return None
        json_match = re.search(r"\{.*\}", result, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group())
                data["status"] = "pending"
                data["is_base"] = True
                data["variant_name"] = "基础形象"
                data["character_base"] = data["name"]
                data["based_on"] = None
                data["variants"] = []
                VisualBibleExtractor._save_single_character(project, data)
                return data
            except json.JSONDecodeError:
                pass
        return None

    @staticmethod
    def _save_single_character(project, char: dict):
        chars_dir = project.project_dir / "05_角色场景" / "角色"
        chars_dir.mkdir(parents=True, exist_ok=True)
        path = chars_dir / f"{char['name']}.json"
        path.write_text(json.dumps(char, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _save_to_files(project, all_chars: dict, all_scenes: dict):
        bible_dir = project.project_dir / "05_角色场景"
        chars_dir = bible_dir / "角色"
        scenes_dir = bible_dir / "场景"
        chars_dir.mkdir(parents=True, exist_ok=True)
        scenes_dir.mkdir(parents=True, exist_ok=True)

        for char in all_chars.values():
            path = chars_dir / f"{char['name']}.json"
            path.write_text(json.dumps(char, ensure_ascii=False, indent=2), encoding="utf-8")

        for scene in all_scenes.values():
            path = scenes_dir / f"{scene['name']}.json"
            path.write_text(json.dumps(scene, ensure_ascii=False, indent=2), encoding="utf-8")

        report = bible_dir / "提取报告.md"
        report_lines = ["# 角色/场景提取报告\n"]
        bases = [c for c in all_chars.values() if c.get("is_base")]
        variants = [c for c in all_chars.values() if not c.get("is_base")]
        mains = [c for c in bases if c.get("type") == "main"]
        minors = [c for c in bases if c.get("type") != "main"]
        report_lines.append(f"## 主要角色（{len(mains)}个）")
        for c in mains:
            v_count = len(c.get("variants", []))
            v_info = f"（{v_count}个变体）" if v_count > 0 else ""
            report_lines.append(f"- **{c['name']}**（{c.get('gender','')}，{c.get('age','')}岁）- {c.get('expression','')} {v_info}")
        report_lines.append(f"\n## 次要角色（{len(minors)}个）")
        for c in minors:
            report_lines.append(f"- {c['name']}（{c.get('gender','')}，{c.get('age','')}岁）")
        if variants:
            report_lines.append(f"\n## 角色变体（{len(variants)}个）")
            for v in variants:
                report_lines.append(f"- {v['name']}（基于{v.get('based_on','')}）- {v.get('trigger_event','')}")
        report_lines.append(f"\n## 场景（{len(bases)}个）")
        for s in bases:
            v_info = f"（{len(s.get('variants',[]))}个变体）" if s.get('variants') else ""
            report_lines.append(f"- **{s['name']}** - {s.get('environment','')[:50]}... {v_info}")
        scene_variants = [s for s in all_scenes.values() if not s.get("is_base")]
        if scene_variants:
            report_lines.append(f"\n## 场景变体（{len(scene_variants)}个）")
            for v in scene_variants:
                report_lines.append(f"- {v['name']}（基于{v.get('based_on','')}）- {v.get('trigger_event','')}")
        report.write_text("\n".join(report_lines), encoding="utf-8")

    @staticmethod
    def confirm_all(project):
        bible_dir = project.project_dir / "05_角色场景"
        for d in ["角色", "场景"]:
            dir_path = bible_dir / d
            if not dir_path.exists():
                continue
            for f in dir_path.glob("*.json"):
                data = json.loads(f.read_text(encoding="utf-8"))
                data["status"] = "confirmed"
                f.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def update_character(project, name: str, updates: dict):
        path = project.project_dir / "05_角色场景" / "角色" / f"{name}.json"
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            data.update(updates)
            data["status"] = "confirmed"
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            return data
        return None

    @staticmethod
    def delete_character(project, name: str):
        path = project.project_dir / "05_角色场景" / "角色" / f"{name}.json"
        if path.exists():
            path.unlink()

    @staticmethod
    def list_characters(project) -> list[dict]:
        chars_dir = project.project_dir / "05_角色场景" / "角色"
        if not chars_dir.exists():
            return []
        result = []
        for f in sorted(chars_dir.glob("*.json")):
            data = json.loads(f.read_text(encoding="utf-8"))
            data["_file"] = f.name
            result.append(data)
        return result

    @staticmethod
    def list_variants(project, base_name: str) -> list[dict]:
        """列出指定基础角色的所有变体"""
        chars_dir = project.project_dir / "05_角色场景" / "角色"
        if not chars_dir.exists():
            return []
        result = []
        for f in chars_dir.glob("*.json"):
            data = json.loads(f.read_text(encoding="utf-8"))
            if data.get("character_base") == base_name or data["name"] == base_name:
                data["_file"] = f.name
                result.append(data)
        return result

    @staticmethod
    def list_scenes(project) -> list[dict]:
        scenes_dir = project.project_dir / "05_角色场景" / "场景"
        if not scenes_dir.exists():
            return []
        result = []
        for f in sorted(scenes_dir.glob("*.json")):
            data = json.loads(f.read_text(encoding="utf-8"))
            data["_file"] = f.name
            result.append(data)
        return result

    @staticmethod
    def list_scene_variants(project, base_name: str) -> list[dict]:
        """列出指定基础场景的所有变体"""
        scenes_dir = project.project_dir / "05_角色场景" / "场景"
        if not scenes_dir.exists():
            return []
        result = []
        for f in scenes_dir.glob("*.json"):
            data = json.loads(f.read_text(encoding="utf-8"))
            if data.get("scene_base") == base_name or data["name"] == base_name:
                data["_file"] = f.name
                result.append(data)
        return result

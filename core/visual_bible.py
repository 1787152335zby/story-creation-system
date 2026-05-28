import json
import re
from pathlib import Path
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from llm.client import LLMClient

SEGMENT_EXTRACT_PROMPT = """你是一位专业的剧本分析师。请从以下剧本片段中提取角色和场景信息。

当前阶段只提取角色的静态视觉信息（外貌/服装/特征），不要提取动态的动作/姿态/手持物。

角色输出（只输出以下字段）：
- name: 角色名
- type: "main"（主要角色/多场出现有台词）或 "minor"（次要角色）
- appearance: 外貌特征综合描述（年龄、脸型、发型、五官特征、身高体型）
- age: 年龄
- gender: 男/女
- clothing: 服装描述（颜色、材质、款式）
- expression: 表情/神态（如冷峻、温柔、阴险）
- accessories: 配饰列表（耳环、项链、眼镜等个人饰品）
- key_features: 标志性特征列表（疤痕、痣、特殊发型等）

⚠️ 禁止输出：pose（姿态）、手持物、武器、动作描写、动态描述
原因：角色定妆照需要空手站姿的静态形象，动态信息会在后续环节处理。

场景输出（只输出以下字段）：
- name: 场景名
- environment: 环境描述（空间布局、装修风格、关键物品位置）
- lighting: 光线描述
- color_tone: 色调描述
- parent_scene: null 或 上层场景名

⚠️ 禁止输出：动态事件、角色出现、场景中的道具列表（道具会单独处理）

输出格式为JSON：
{
  "characters": [
    {
      "name": "角色名",
      "type": "main",
      "appearance": "外貌特征综合描述",
      "age": "年龄",
      "gender": "男/女",
      "clothing": "服装描述",
      "expression": "表情/神态",
      "accessories": ["配饰1"],
      "key_features": ["标志特征1"]
    }
  ],
  "scenes": [
    {
      "name": "场景名",
      "environment": "环境描述",
      "lighting": "光线描述",
      "color_tone": "色调描述",
      "parent_scene": null
    }
  ],
  "scene_characters": {
    "场景名": ["角色1", "角色2"]
  }
}

只输出JSON，不要其他文字。

场景关联规则：
- 如果一个场景位于另一个场景的内部（如"体育馆擂台"在"学校体育馆"内），parent_scene 填写上层场景名
- 如果是独立场景，parent_scene 为 null
"""

PROP_EXTRACT_PROMPT = """你是一位道具分析师。请从以下剧本片段中识别所有物理道具，并按类别标记。

道具是剧本中出现的物理物品（不是角色、不是场景地点），包括：武器、饰品、设备、文件、标志物、车辆、工具等。

类别规则（三选一）：
- "跨场景道具"：同一道具在多个不同的场景中出现（如组织标志徽章在秘密基地和反派胸前都出现、传家宝剑在多场战斗中出现）
- "场景固有道具"：固定在某个场景中、不会移到其他场景的物品（如固定的书桌、路灯、大门、沙发、挂钟）
- "角色随身道具"：角色个人携带、随角色移动的物品（如角色的配剑、眼镜、项链、背包、手表）

判断原则：
1. 先判断"是否可能在其他场景出现？" → 是→跨场景道具；否→继续判断
2. "该物品是场景固定设施还是角色随身携带？" → 固定→场景固有道具；携带→角色随身道具

输出JSON：
{
  "props": [
    {
      "name": "道具名称",
      "category": "跨场景道具|场景固有道具|角色随身道具",
      "scene": "初次出现/归属场景名",
      "owner": "归属角色名（角色随身道具必填，否则null）",
      "appearance": "外观描述（颜色、形状、材质、尺寸）"
    }
  ]
}

只输出JSON，不要其他文字。
"""

CHANGE_DETECT_PROMPT = """你是一位专业的剧本状态跟踪员。请分析以下剧本，找出角色和场景的可见状态变化事件。

只关注「形象上可见的变化」——角色内心变化不算。只关注「能看到的有形变化」。

角色变化（以下类型）：
- 受伤：流血、包扎、淤青、疤痕、擦伤等身体上的可见伤口
- 换装：更换衣服、外套、配饰（从A套装换到B套装）
- 发型/妆容改变
- 佩戴新道具或移除原有道具（如戴上眼镜/摘下眼镜）

场景变化（以下类型）：
- 破坏：坍塌、裂痕、破损、物品损坏
- 装修/改动：重新布置、新增物品、格局改变
- 天气变化：下雨、起雾、飘雪、风暴
- 时间推移：白天→黄昏→夜晚、季节变化

每个变化必须精确标注字段：
- character_name/scene_name: 变化的角色名/场景名
- variant_name: 变体名称（如"受伤形象""夜晚版""换装版"）
- based_on: 基础形象引用（如"林深_基础形象"）
- appearance_change(角色): 外貌可见变化 / change(场景): 场景变化描述
- clothing_change(角色): 服装变化
- trigger_event: 触发事件，精确到场次（如"第3场被阿虎用刀划伤右臂"）
- applies_from: 从哪场开始生效（如"第3场"）
- applies_to: 持续到哪场（如"第10场"；如持续到片尾则填"全片"）

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
      "applies_to": "第10场"
    }
  ],
  "scene_changes": [
    {
      "scene_name": "地下室",
      "variant_name": "爆炸后",
      "based_on": "地下室_基础形象",
      "change": "天花板塌陷四分一，地面碎石遍布，水管爆裂墙壁渗水",
      "trigger_event": "第15场锅炉爆炸",
      "applies_from": "第15场",
      "applies_to": "全片"
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


def _sanitize_filename(name: str) -> str:
    """去除文件名中的非法字符"""
    return "".join(c for c in name if c not in r'<>:"/\\|?*')


_ID_COUNTERS = {"character": 0, "scene": 0, "prop": 0}


def _generate_entity_id(prefix: str) -> str:
    """生成唯一实体ID，如 CHAR_001 / SCENE_001 / PROP_001"""
    global _ID_COUNTERS
    key = {"CHAR": "character", "SCENE": "scene", "PROP": "prop"}.get(prefix, "character")
    _ID_COUNTERS[key] += 1
    return f"{prefix}_{_ID_COUNTERS[key]:03d}"


def _build_variant_tag(base_id: str, variant_name: str, feature_suffix: str = "") -> str:
    """构建变体标签: 基础ID_变体标识_特征后缀"""
    tag = f"{base_id}_{variant_name}"
    if feature_suffix:
        tag = f"{tag}_{feature_suffix}"
    return _sanitize_filename(tag)


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

        inc_dir = project.project_dir / "04_角色场景" / "_incremental"
        inc_available = inc_dir.exists() and any(inc_dir.glob("*.json"))
        if inc_available:
            merged = VisualBibleExtractor.merge_incremental(project)
        else:
            merged = None

        if not script_content.strip():
            return {"characters": [], "scenes": []}

        segments = re.split(r'(第[一二三四五六七八九十百千\d]+场)', script_content)
        if len(segments) <= 1:
            segments = [script_content]

        client = LLMClient()
        all_chars: dict[str, dict] = {}
        all_scenes: dict[str, dict] = {}
        all_props: dict[str, dict] = {}
        scene_char_map: dict[str, list[str]] = {}

        if merged and (merged.get("characters") or merged.get("scenes")):
            all_chars = {c["name"]: c for c in merged["characters"]}
            all_scenes = {s["name"]: s for s in merged["scenes"]}
        else:
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
                        for field in ["appearance", "clothing", "expression"]:
                            if char.get(field) and not existing.get(field):
                                existing[field] = char[field]
                        existing["accessories"] = list(set(existing.get("accessories", []) + char.get("accessories", [])))
                        existing["key_features"] = list(set(existing.get("key_features", []) + char.get("key_features", [])))
                    else:
                        char["status"] = "pending"
                        char["is_base"] = True
                        char["variant_name"] = "基础形象"
                        char["character_base"] = name
                        char["character_id"] = _generate_entity_id("CHAR")
                        char["based_on"] = None
                        char["variants"] = []
                        char["variant_tag"] = ""
                        char["feature_desc"] = char.get("appearance", "") + " " + char.get("clothing", "")
                        all_chars[name] = char

                for scene in data.get("scenes", []):
                    name = scene["name"]
                    if name not in all_scenes:
                        scene["status"] = "pending"
                        scene["is_base"] = True
                        scene["variant_name"] = "基础形象"
                        scene["scene_base"] = name
                        scene["scene_id"] = _generate_entity_id("SCENE")
                        scene["based_on"] = None
                        scene["variants"] = []
                        scene["variant_tag"] = ""
                        scene["feature_desc"] = scene.get("environment", "")
                        all_scenes[name] = scene
                    else:
                        existing = all_scenes[name]
                        if scene.get("parent_scene") and not existing.get("parent_scene"):
                            existing["parent_scene"] = scene["parent_scene"]

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

        # ── Pass 2: Extract props with classification ──
        prop_batch_size = 6000
        for i in range(0, len(script_content), prop_batch_size):
            chunk = script_content[i:i+prop_batch_size]
            if not chunk.strip():
                continue
            result = ""
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(client.chat, PROP_EXTRACT_PROMPT, chunk, 0.3)
                try:
                    result = future.result(timeout=120)
                except (TimeoutError, Exception):
                    continue
            json_match = re.search(r"\{.*\}", result, re.DOTALL)
            if not json_match:
                continue
            try:
                data = json.loads(json_match.group())
            except json.JSONDecodeError:
                continue
            for prop in data.get("props", []):
                pname = prop.get("name", "")
                if not pname:
                    continue
                if pname in all_props:
                    existing = all_props[pname]
                    if prop.get("appearance") and not existing.get("appearance"):
                        existing["appearance"] = prop["appearance"]
                else:
                    all_props[pname] = {
                        "name": pname,
                        "prop_id": _generate_entity_id("PROP"),
                        "category": prop.get("category", "场景固有道具"),
                        "scene": prop.get("scene", ""),
                        "owner": prop.get("owner"),
                        "appearance": prop.get("appearance", ""),
                        "status": "pending",
                    }

        # ── Pass 3: Detect state changes ──
        change_prompt_text = script_content[:12000]
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
                            base_id = base.get("character_id", "")
                            variant_unique = _ensure_variant_name(base_name, cc["variant_name"])
                            feature_desc_parts = []
                            if cc.get("appearance_change"):
                                feature_desc_parts.append(cc["appearance_change"])
                            if cc.get("clothing_change"):
                                feature_desc_parts.append(cc["clothing_change"])
                            feature_desc = "；".join(feature_desc_parts) if feature_desc_parts else cc.get("variant_name", "")
                            variant_tag = _build_variant_tag(base_id, cc["variant_name"], "")
                            variant = {
                                "name": variant_unique,
                                "character_base": base_name,
                                "character_id": base_id,
                                "type": base.get("type", "minor"),
                                "is_base": False,
                                "variant_name": cc["variant_name"],
                                "variant_tag": variant_tag,
                                "feature_desc": feature_desc,
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
                            base_id = base.get("scene_id", "")
                            variant_unique = _ensure_variant_name(base_name, sc["variant_name"])
                            feature_desc = sc.get("change", sc.get("variant_name", ""))
                            variant_tag = _build_variant_tag(base_id, sc["variant_name"], "")
                            variant = {
                                "name": variant_unique,
                                "scene_base": base_name,
                                "scene_id": base_id,
                                "is_base": False,
                                "variant_name": sc["variant_name"],
                                "variant_tag": variant_tag,
                                "feature_desc": feature_desc,
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
        VisualBibleExtractor._save_to_files(project, all_chars, all_scenes, all_props)
        return {"characters": list(all_chars.values()), "scenes": list(all_scenes.values()), "props": list(all_props.values())}

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
                data["character_id"] = _generate_entity_id("CHAR")
                data["based_on"] = None
                data["variants"] = []
                data["variant_tag"] = ""
                data["feature_desc"] = data.get("appearance", "") + " " + data.get("clothing", "")
                VisualBibleExtractor._save_single_character(project, data)
                return data
            except json.JSONDecodeError:
                pass
        return None

    @staticmethod
    def _save_single_character(project, char: dict):
        chars_dir = project.project_dir / "04_角色场景" / "角色"
        chars_dir.mkdir(parents=True, exist_ok=True)
        path = chars_dir / f"{char['name']}.json"
        path.write_text(json.dumps(char, ensure_ascii=False, indent=2), encoding="utf-8")
        # Clean up old 05_角色场景 data if present
        old_path = project.project_dir / "05_角色场景" / "角色" / f"{char['name']}.json"
        if old_path.exists():
            old_path.unlink()

    @staticmethod
    def _save_to_files(project, all_chars: dict, all_scenes: dict, all_props: dict = None):
        bible_dir = project.project_dir / "04_角色场景"
        chars_dir = bible_dir / "角色"
        scenes_dir = bible_dir / "场景"
        props_dir = bible_dir / "道具"
        chars_dir.mkdir(parents=True, exist_ok=True)
        scenes_dir.mkdir(parents=True, exist_ok=True)
        if all_props:
            props_dir.mkdir(parents=True, exist_ok=True)

        for char in all_chars.values():
            path = chars_dir / f"{_sanitize_filename(char['name'])}.json"
            path.write_text(json.dumps(char, ensure_ascii=False, indent=2), encoding="utf-8")

        for scene in all_scenes.values():
            desc = scene.get("environment", "")
            existing_props = set(scene.get("props", []) or [])
            quoted = re.findall(r'[「「]([^」」]{1,20})[」」]', desc)
            for q in quoted:
                if q.strip() and q.strip() not in existing_props:
                    existing_props.add(q.strip())
            proper = re.findall(r'(?:关键道具|标志性|核心)[：:]*\s*([^，,。\n]{2,15})', desc)
            for p in proper:
                if p.strip() and p.strip() not in existing_props:
                    existing_props.add(p.strip())
            scene["props"] = list(existing_props)
            path = scenes_dir / f"{_sanitize_filename(scene['name'])}.json"
            path.write_text(json.dumps(scene, ensure_ascii=False, indent=2), encoding="utf-8")

        if all_props:
            deduped = {}
            for prop_name, prop_data in all_props.items():
                key = prop_name.strip()
                for existing in list(deduped.keys()):
                    if key in existing or existing in key:
                        existing_data = deduped[existing]
                        if len(prop_data.get("appearance", "")) > len(existing_data.get("appearance", "")):
                            deduped[existing] = prop_data
                        break
                else:
                    deduped[key] = prop_data
            prop_name_map = {}
            for orig_name in all_props:
                for dedup_name in deduped:
                    if orig_name.strip() in dedup_name or dedup_name in orig_name.strip():
                        prop_name_map[orig_name] = dedup_name
                        break
            for scene in all_scenes.values():
                props = scene.get("props", [])
                if props:
                    scene["props"] = [prop_name_map.get(p, p) for p in props]
            all_props = deduped

        char_name_to_id = {c["name"]: c.get("character_id", "") for c in all_chars.values()}
        if all_props:
            for prop in all_props.values():
                owner = prop.get("owner", "")
                if owner and owner != "null" and owner in char_name_to_id:
                    prop["owner_character_id"] = char_name_to_id[owner]
                safe_name = _sanitize_filename(prop["name"])
                if not safe_name:
                    safe_name = "_unnamed"
                path = props_dir / f"{safe_name}.json"
                path.write_text(json.dumps(prop, ensure_ascii=False, indent=2), encoding="utf-8")

        report = bible_dir / "提取报告.md"
        report_lines = ["# 角色/场景/道具提取报告\n"]
        bases = [c for c in all_chars.values() if c.get("is_base")]
        variants = [c for c in all_chars.values() if not c.get("is_base")]
        mains = [c for c in bases if c.get("type") == "main"]
        minors = [c for c in bases if c.get("type") != "main"]
        report_lines.append(f"## 主要角色（{len(mains)}个）")
        for c in mains:
            cid = c.get("character_id", "")
            v_count = len(c.get("variants", []))
            v_info = f"（{v_count}个变体）" if v_count > 0 else ""
            report_lines.append(f"- **{c['name']}** `{cid}`（{c.get('gender','')}，{c.get('age','')}岁）- {c.get('expression','')} {v_info}")
        report_lines.append(f"\n## 次要角色（{len(minors)}个）")
        for c in minors:
            cid = c.get("character_id", "")
            report_lines.append(f"- {c['name']} `{cid}`（{c.get('gender','')}，{c.get('age','')}岁）")
        if variants:
            report_lines.append(f"\n## 角色变体（{len(variants)}个）")
            for v in variants:
                vid = v.get("character_id", "")
                vtag = v.get("variant_tag", "")
                report_lines.append(f"- {v['name']} `{vid}`（标签: {vtag}）- {v.get('trigger_event','')}")
        base_scenes = [s for s in all_scenes.values() if s.get("is_base")]
        report_lines.append(f"\n## 场景（{len(base_scenes)}个）")
        for s in base_scenes:
            sid = s.get("scene_id", "")
            v_info = f"（{len(s.get('variants',[]))}个变体）" if s.get('variants') else ""
            report_lines.append(f"- **{s['name']}** `{sid}` - {s.get('environment','')[:50]}... {v_info}")
        scene_variants = [s for s in all_scenes.values() if not s.get("is_base")]
        if scene_variants:
            report_lines.append(f"\n## 场景变体（{len(scene_variants)}个）")
            for v in scene_variants:
                sid = v.get("scene_id", "")
                vtag = v.get("variant_tag", "")
                report_lines.append(f"- {v['name']} `{sid}`（标签: {vtag}）- {v.get('trigger_event','')}")
        if all_props:
            props_carry = [p for p in all_props.values() if p.get("prop_class") == "随身道具"]
            props_key = [p for p in all_props.values() if p.get("prop_class") == "关键道具"]
            report_lines.append(f"\n## 随身道具（{len(props_carry)}个）")
            for p in props_carry:
                pid = p.get("prop_id", "")
                report_lines.append(f"- **{p['name']}** `{pid}`（{p.get('type','')} / {p.get('owner','')}所属）- {p.get('appearance','')[:40]}...")
            report_lines.append(f"\n## 剧情关键道具（{len(props_key)}个）")
            for p in props_key:
                pid = p.get("prop_id", "")
                report_lines.append(f"- **{p['name']}** `{pid}`（{p.get('type','')}）- {p.get('description','')[:40]}...")
        report.write_text("\n".join(report_lines), encoding="utf-8")

    @staticmethod
    def extract_incremental(text: str) -> dict:
        if not text or not text.strip():
            return {"characters": [], "scenes": []}

        segments = re.split(r'(第[一二三四五六七八九十百千\d]+场)', text)
        if len(segments) <= 1:
            segments = [text]

        client = LLMClient()
        all_chars: dict[str, dict] = {}
        all_scenes: dict[str, dict] = {}

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

            batch_text = batch_text[:6000]

            result = ""
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(client.chat, SEGMENT_EXTRACT_PROMPT, batch_text, 0.3)
                try:
                    result = future.result(timeout=120)
                except (TimeoutError, Exception):
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
                    for field in ["appearance", "clothing", "expression"]:
                        if char.get(field) and not existing.get(field):
                            existing[field] = char[field]
                    existing["accessories"] = list(set(existing.get("accessories", []) + char.get("accessories", [])))
                    existing["key_features"] = list(set(existing.get("key_features", []) + char.get("key_features", [])))
                else:
                    char["status"] = "pending"
                    char["is_base"] = True
                    char["variant_name"] = "基础形象"
                    char["character_base"] = name
                    char["character_id"] = _generate_entity_id("CHAR")
                    char["based_on"] = None
                    char["variants"] = []
                    char["variant_tag"] = ""
                    char["feature_desc"] = char.get("appearance", "") + " " + char.get("clothing", "")
                    all_chars[name] = char

            for scene in data.get("scenes", []):
                name = scene["name"]
                if name not in all_scenes:
                    scene["status"] = "pending"
                    scene["is_base"] = True
                    scene["variant_name"] = "基础形象"
                    scene["scene_base"] = name
                    scene["scene_id"] = _generate_entity_id("SCENE")
                    scene["based_on"] = None
                    scene["variants"] = []
                    scene["variant_tag"] = ""
                    scene["feature_desc"] = scene.get("environment", "")
                    all_scenes[name] = scene

        return {"characters": list(all_chars.values()), "scenes": list(all_scenes.values())}

    @staticmethod
    def merge_incremental(project) -> dict:
        inc_dir = project.project_dir / "04_角色场景" / "_incremental"
        if not inc_dir.exists():
            return {"characters": [], "scenes": []}

        all_chars: dict[str, dict] = {}
        all_scenes: dict[str, dict] = {}

        for f in sorted(inc_dir.glob("*.json")):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue

            for char in data.get("characters", []):
                name = char.get("name", "")
                if not name:
                    continue
                if name in all_chars:
                    existing = all_chars[name]
                    if char.get("type") == "main":
                        existing["type"] = "main"
                    for field in ["appearance", "clothing", "expression"]:
                        if char.get(field) and not existing.get(field):
                            existing[field] = char[field]
                    existing["accessories"] = list(set(existing.get("accessories", []) + char.get("accessories", [])))
                    existing["key_features"] = list(set(existing.get("key_features", []) + char.get("key_features", [])))
                else:
                    char["status"] = "pending"
                    char["is_base"] = True
                    char["variant_name"] = "基础形象"
                    char["character_base"] = name
                    char["character_id"] = _generate_entity_id("CHAR")
                    char["based_on"] = None
                    char["variants"] = []
                    char["variant_tag"] = ""
                    char["feature_desc"] = char.get("appearance", "") + " " + char.get("clothing", "")
                    all_chars[name] = char

            for scene in data.get("scenes", []):
                name = scene.get("name", "")
                if not name:
                    continue
                if name not in all_scenes:
                    scene["status"] = "pending"
                    scene["is_base"] = True
                    scene["variant_name"] = "基础形象"
                    scene["scene_base"] = name
                    scene["scene_id"] = _generate_entity_id("SCENE")
                    scene["based_on"] = None
                    scene["variants"] = []
                    scene["variant_tag"] = ""
                    scene["feature_desc"] = scene.get("environment", "")
                    all_scenes[name] = scene

        return {"characters": list(all_chars.values()), "scenes": list(all_scenes.values())}

    @staticmethod
    def confirm_all(project):
        bible_dir = VisualBibleExtractor._get_visual_dir(project)
        for d in ["角色", "场景", "道具"]:
            dir_path = bible_dir / d
            if not dir_path.exists():
                continue
            for f in dir_path.glob("*.json"):
                data = json.loads(f.read_text(encoding="utf-8"))
                data["status"] = "confirmed"
                f.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def update_character(project, name: str, updates: dict):
        chars_dir = VisualBibleExtractor._get_visual_dir(project, "角色")
        path = chars_dir / f"{name}.json"
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            data.update(updates)
            data["status"] = "confirmed"
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            return data
        return None

    @staticmethod
    def delete_character(project, name: str):
        chars_dir = VisualBibleExtractor._get_visual_dir(project, "角色")
        path = chars_dir / f"{name}.json"
        if path.exists():
            path.unlink()

    @staticmethod
    def _get_visual_dir(project, subpath: str = ""):
        """返回角色场景数据目录，兼容 04_角色场景 和 05_角色场景 两种旧版路径"""
        path_04 = project.project_dir / "04_角色场景" / subpath
        path_05 = project.project_dir / "05_角色场景" / subpath
        if path_04.exists() and any(path_04.glob("*.json")):
            return path_04
        if path_05.exists() and any(path_05.glob("*.json")):
            return path_05
        return path_04

    @staticmethod
    def list_characters(project) -> list[dict]:
        chars_dir = VisualBibleExtractor._get_visual_dir(project, "角色")
        if not chars_dir.exists():
            return []
        result = []
        for f in sorted(chars_dir.glob("*.json")):
            data = json.loads(f.read_text(encoding="utf-8"))
            data["_file"] = f.name
            result.append(data)
        VisualBibleExtractor._normalize_character_bases(result)
        return result

    @staticmethod
    def list_variants(project, base_name: str) -> list[dict]:
        """列出指定基础角色的所有变体"""
        chars_dir = VisualBibleExtractor._get_visual_dir(project, "角色")
        if not chars_dir.exists():
            return []
        result = []
        for f in chars_dir.glob("*.json"):
            data = json.loads(f.read_text(encoding="utf-8"))
            if data.get("character_base") == base_name or data["name"] == base_name:
                data["_file"] = f.name
                result.append(data)
        return result

    _STRIP_MARKERS = frozenset({
        '地上', '画中', '画面中', '画面内', '画外', '画外音',
        '远景', '近景', '中景', '特写', '背面', '正面', '侧面',
        '仰视', '俯视', '另一个', '幻象', '记忆', '副本',
    })
    _PARTICLES = frozenset('的了着过另几个上下里中外前后一之地得以与为被把和就都')
    _STRIP_CODES = frozenset({
        0x201C, 0x201D, 0x2018, 0x2019,
        0x3000, 0x300C, 0x300D,
        0x0028, 0x0029, 0xFF08, 0xFF09,
        0x005B, 0x005D, 0x3010, 0x3011,
        0x0020, 0x0009, 0x000A, 0x000D,
    })

    @staticmethod
    def _normalize_name(raw: str, known: set, markers=None) -> str:
        use_markers = markers if markers is not None else VisualBibleExtractor._STRIP_MARKERS
        cleaned = ''.join(c for c in raw if ord(c) not in VisualBibleExtractor._STRIP_CODES)
        for base in sorted(known, key=len):
            bc = ''.join(c for c in base if ord(c) not in VisualBibleExtractor._STRIP_CODES)
            if cleaned == bc:
                return base
            words = re.findall(r'[\u4e00-\u9fff]+', cleaned)
            filtered = ''.join(w for w in words if w not in use_markers and not set(w).issubset(VisualBibleExtractor._PARTICLES))
            if filtered == bc:
                return base
            if cleaned.startswith(bc) and len(cleaned) > len(bc):
                rest = cleaned[len(bc):]
                words = re.findall(r'[\u4e00-\u9fff]+', rest)
                ok = True
                for w in words:
                    if w not in use_markers and set(w) - VisualBibleExtractor._PARTICLES:
                        ok = False
                        break
                if ok:
                    return base
            if cleaned.endswith(bc) and len(cleaned) > len(bc):
                rest = cleaned[:-len(bc)]
                words = re.findall(r'[\u4e00-\u9fff]+', rest)
                ok = True
                for w in words:
                    if w not in use_markers and set(w) - VisualBibleExtractor._PARTICLES:
                        ok = False
                        break
                if ok:
                    return base
        return raw

    @staticmethod
    def _normalize_character_bases(chars: list):
        for _pass in range(3):
            grouped = {}
            for c in chars:
                base = c.get('character_base', c['name'])
                grouped.setdefault(base, []).append(c)
            true_bases = {b for b, cs in grouped.items() if any(c.get('is_base') and c['character_base'] == c['name'] for c in cs)}
            if not true_bases:
                true_bases = {b for b, cs in grouped.items() if len(cs) >= max(2, min(3, sum(1 for x in chars if x.get('is_base')) // 2))}
            changed = False
            for b in sorted(list(grouped.keys()), key=len, reverse=True):
                if b not in grouped:
                    continue
                normalized = VisualBibleExtractor._normalize_name(b, true_bases - {b})
                if normalized != b and normalized in true_bases:
                    for c in grouped[b]:
                        c['character_base'] = normalized
                        if c.get('is_base') and c['name'] != normalized:
                            c['is_base'] = False
                            existing_vn = c.get('variant_name', '')
                            if not existing_vn or existing_vn in ('基础形象', '基础'):
                                c['variant_name'] = c['name'].replace(normalized, '', 1).strip('_（）()').strip('_()')
                                if not c['variant_name']:
                                    c['variant_name'] = c['name']
                    changed = True
            if not changed:
                break

    @staticmethod
    def list_scenes(project) -> list[dict]:
        scenes_dir = VisualBibleExtractor._get_visual_dir(project, "场景")
        if not scenes_dir.exists():
            return []
        result = []
        for f in sorted(scenes_dir.glob("*.json")):
            data = json.loads(f.read_text(encoding="utf-8"))
            data["_file"] = f.name
            result.append(data)
        VisualBibleExtractor._normalize_scene_bases(result)
        return result

    _SCENE_MARKERS = frozenset({
        '深夜', '凌晨', '夜', '内景', '外景', '日景', '夜景',
        '清晨', '正午', '黄昏', '傍晚', '黎明', '上午', '下午',
    })

    @staticmethod
    def _normalize_scene_bases(scns: list):
        grouped = {}
        for s in scns:
            base = s.get('scene_base', s['name'])
            grouped.setdefault(base, []).append(s)
        true_bases = {b for b, cs in grouped.items() if any(c.get('is_base') and c['scene_base'] == c['name'] for c in cs)}
        for b in list(grouped.keys()):
            normalized = VisualBibleExtractor._normalize_name(b, true_bases, VisualBibleExtractor._SCENE_MARKERS)
            if normalized != b and normalized in true_bases:
                for s in grouped[b]:
                    s['scene_base'] = normalized
                    if s.get('is_base') and s['name'] != normalized:
                        s['is_base'] = False

    @staticmethod
    def list_scene_variants(project, base_name: str) -> list[dict]:
        """列出指定基础场景的所有变体"""
        scenes_dir = VisualBibleExtractor._get_visual_dir(project, "场景")
        if not scenes_dir.exists():
            return []
        result = []
        for f in scenes_dir.glob("*.json"):
            data = json.loads(f.read_text(encoding="utf-8"))
            if data.get("scene_base") == base_name or data["name"] == base_name:
                data["_file"] = f.name
                result.append(data)
        return result

    @staticmethod
    def list_props(project) -> list[dict]:
        props_dir = VisualBibleExtractor._get_visual_dir(project, "道具")
        if not props_dir.exists():
            return []
        result = []
        for f in sorted(props_dir.glob("*.json")):
            data = json.loads(f.read_text(encoding="utf-8"))
            data["_file"] = f.name
            result.append(data)
        return result

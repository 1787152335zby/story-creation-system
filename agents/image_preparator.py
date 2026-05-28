import json
import re
from pathlib import Path
from core.agent_base import AgentBase
from core.project_manager import ProjectManager
from core.style_config import StyleConfig
from core.visual_bible import VisualBibleExtractor
from agents.prompt_factory import PromptBuilder


class ImagePreparator(AgentBase):

    def run(self, project: ProjectManager, style: StyleConfig, input_content: str) -> str:
        return json.dumps(self.prepare(project, style), ensure_ascii=False, indent=2)

    def run_stream(self, project: ProjectManager, style: StyleConfig, input_content: str):
        result = self.prepare(project, style)
        report = self._build_report(result)
        for chunk in [report[i:i+100] for i in range(0, len(report), 100)]:
            yield chunk

    def prepare(self, project: ProjectManager, style: StyleConfig = None) -> dict:
        storyboard_dir = project.project_dir / "05_分镜脚本"
        if not storyboard_dir.exists():
            return self._fallback_full(project)

        ep_dirs = sorted([d for d in storyboard_dir.iterdir() if d.is_dir()])
        if not ep_dirs:
            sb_file = storyboard_dir / "分镜脚本.md"
            if sb_file.exists():
                return self._analyze_from_storyboard(str(sb_file), project)
            return self._fallback_full(project)

        all_char_states = {}
        all_scene_states = {}
        all_episodes = []
        shot_counter = 0
        shot_field_map = {}

        for ep_dir in ep_dirs:
            ep_name = ep_dir.name
            all_episodes.append(ep_name)
            sb_file = ep_dir / "分镜脚本.md"
            if not sb_file.exists():
                continue
            content = sb_file.read_text(encoding="utf-8")
            shots = self._parse_shots(content, ep_name)
            for shot in shots:
                shot_counter += 1
                shot_field_map[shot_counter] = f"{ep_name}第{shot.get('field_number', 1)}场"
                for char_name_raw in shot.get("characters", []):
                    char_name = self._clean_shot_char_name(char_name_raw)
                    if not char_name:
                        continue
                    if char_name not in all_char_states:
                        known = set(all_char_states.keys())
                        normalized = self._normalize_char_name(char_name, known)
                        if normalized != char_name and normalized in all_char_states:
                            char_name = normalized
                    if char_name not in all_char_states:
                        all_char_states[char_name] = {
                            "name": char_name,
                            "shot_indices": [],
                            "episodes": [],
                        }
                    all_char_states[char_name]["shot_indices"].append(shot_counter)
                    if ep_name not in all_char_states[char_name]["episodes"]:
                        all_char_states[char_name]["episodes"].append(ep_name)

                scene_name = shot.get("scene", "")
                if scene_name:
                    if scene_name not in all_scene_states:
                        all_scene_states[scene_name] = {
                            "name": scene_name,
                            "shot_indices": [],
                            "episodes": [],
                        }
                    all_scene_states[scene_name]["shot_indices"].append(shot_counter)
                    if ep_name not in all_scene_states[scene_name]["episodes"]:
                        all_scene_states[scene_name]["episodes"].append(ep_name)

        visual_bible = self._load_or_extract_visual_bible(project, list(all_char_states.keys()), list(all_scene_states.keys()))
        characters = self._merge_with_bible(list(all_char_states.values()), visual_bible)
        bible_chars = {c["name"]: c for c in visual_bible.get("characters", [])}
        for bc_name, bc in bible_chars.items():
            if bc_name in all_char_states:
                continue
            if not bc.get("is_base", True):
                base_name = bc.get("character_base", "") or bc.get("base_character", "")
                if base_name and base_name in all_char_states:
                    applies = bc.get("applies_from", "")
                    if not applies:
                        continue
                    variant_shots = list(all_char_states[base_name]["shot_indices"])
                    if applies and shot_field_map:
                        start_shot = None
                        for sidx in sorted(shot_field_map.keys()):
                            if shot_field_map[sidx] == applies:
                                start_shot = sidx
                                break
                        if start_shot:
                            variant_shots = [s for s in variant_shots if s >= start_shot]
                        if not variant_shots:
                            continue
                    entry = {
                        "name": bc_name,
                        "character_base": base_name,
                        "shot_indices": variant_shots,
                        "episodes": list(all_char_states[base_name]["episodes"]),
                        "appearance": bc.get("appearance", ""),
                        "clothing": bc.get("clothing", ""),
                        "accessories": bc.get("accessories", []),
                        "key_features": bc.get("key_features", []),
                        "variant_name": bc.get("variant_name", ""),
                        "is_base": False,
                    }
                    entry["prompt"] = PromptBuilder.generate_character_prompt(entry, mode="base")
                    characters.append(entry)
        scenes = self._merge_scenes_with_bible(list(all_scene_states.values()), visual_bible)
        bible_scenes = {s["name"]: s for s in visual_bible.get("scenes", [])}
        scene_name_set = {s["name"] for s in scenes}
        for s in list(scenes):
            sb = s.get("scene_base", s["name"])
            if sb not in scene_name_set and sb in bible_scenes:
                bs = bible_scenes[sb]
                scenes.append({
                    "name": sb,
                    "scene_base": sb,
                    "is_base": True,
                    "variant_name": "",
                    "shot_indices": [],
                    "episodes": [],
                    "environment": bs.get("environment", ""),
                    "lighting": bs.get("lighting", ""),
                    "color_tone": bs.get("color_tone", ""),
                })
                scene_name_set.add(sb)
        all_props = self._categorize_props(visual_bible)
        cross_scene_props = all_props.get("cross_scene_props", [])
        scene_props = all_props.get("scene_props", [])
        char_props = all_props.get("char_props", {})

        for c in characters:
            c["prompt"] = PromptBuilder.generate_character_prompt(c, mode="base")

        for s in scenes:
            s["prompt"] = PromptBuilder.generate_scene_prompt(s, angle="")

        for p in cross_scene_props + scene_props:
            p["prompt"] = PromptBuilder.generate_prop_prompt(p)

        all_char_names = {c.get("name", "") for c in characters}
        seen_canonicals = set()
        deduped_chars = []
        for c in characters:
            if not c.get("is_base"):
                base = c.get("character_base", c["name"])
                canonical = self._canonicalize_variant(c, base, all_char_names)
                key = f"{base}__{canonical}"
                if key in seen_canonicals:
                    continue
                seen_canonicals.add(key)
                c["variant_name"] = canonical
            deduped_chars.append(c)
        characters = self._dedupe_variants_by_similarity(deduped_chars, all_char_names)

        character_groups = []
        group_map = {}
        for c in characters:
            base_name = c.get("character_base", c["name"])
            if base_name not in group_map:
                group_map[base_name] = {"name": base_name, "total_shots": 0, "members": []}
            member = {
                "name": c["name"],
                "is_base": c.get("is_base", True),
                "shots": len(c.get("shot_indices", [])),
                "variant_name": c.get("variant_name", "基础形象" if c.get("is_base", True) else c.get("variant_name", "")),
            }
            group_map[base_name]["members"].append(member)
        for gn, g in group_map.items():
            g["total_shots"] = max(m["shots"] for m in g["members"]) if g["members"] else 0
            g["members"].sort(key=lambda m: (0 if m["is_base"] else 1, m["name"]))
            character_groups.append(g)
        character_groups.sort(key=lambda g: g["name"])

        scene_groups = []
        scene_group_map = {}
        for s in scenes:
            base_name = s.get("scene_base", s["name"])
            if base_name not in scene_group_map:
                scene_group_map[base_name] = {"name": base_name, "total_shots": 0, "members": []}
            member = {
                "name": s["name"],
                "is_base": s.get("is_base", True),
                "shots": len(s.get("shot_indices", [])),
                "variant_name": s.get("variant_name", "基础"),
            }
            scene_group_map[base_name]["members"].append(member)
        for gn, g in scene_group_map.items():
            g["total_shots"] = max(m["shots"] for m in g["members"]) if g["members"] else 0
            g["members"].sort(key=lambda m: (0 if m["is_base"] else 1, m["name"]))
            scene_groups.append(g)
        scene_groups.sort(key=lambda g: g["name"])

        result = {
            "characters": characters,
            "character_groups": character_groups,
            "scenes": scenes,
            "scene_groups": scene_groups,
            "char_props": char_props,
            "cross_scene_props": cross_scene_props,
            "scene_props": scene_props,
            "total_shots": shot_counter,
            "episodes": all_episodes,
        }
        output_dir = project.project_dir / "06_生图需求"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "生图清单.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

        return result

    def generate_assets(self, project: ProjectManager, style: StyleConfig = None,
                        on_progress: callable = None) -> list[dict]:
        """调用生图管线，将角色/场景/道具提示词转为实际图片"""
        from core.image_pipeline import ImagePipeline
        pipeline = ImagePipeline(project.project_dir)

        result = self.prepare(project, style)
        characters = result.get("characters", [])
        scenes = result.get("scenes", [])
        cross_scene_props = result.get("cross_scene_props", [])
        scene_props = result.get("scene_props", [])

        assets = []
        for c in characters:
            if c.get("is_base", True):
                assets.append({"type": "角色", "name": c["name"], "data": c})
        for s in scenes:
            if s.get("is_base", True):
                assets.append({"type": "场景", "name": s["name"], "data": s})
        for p in cross_scene_props + scene_props:
            assets.append({"type": "道具", "name": p["name"], "data": p})

        return list(pipeline.generate_batch(assets))

    PSEUDO_MARKERS = frozenset({
        '地上', '画中', '画面中', '画面内', '画外', '画外音',
        '远景', '近景', '中景', '特写', '背面', '正面', '侧面',
        '仰视', '俯视', '另一个', '系统', '幻象', '记忆', '副本',
    })
    _PARTICLE_CHARS = frozenset('的了着过另几个上下里中外前后一之地得以与为被把和就都')

    _STRIP_CODES = frozenset({
        0x201C, 0x201D, 0x2018, 0x2019,  # smart quotes
        0x3000, 0x300C, 0x300D,          # CJK punctuation
        0x0028, 0x0029,                   # ()
        0xFF08, 0xFF09,                   # （）
        0x005B, 0x005D,                   # []
        0x3010, 0x3011,                   # 【】
        0x0020, 0x0009, 0x000A, 0x000D,  # whitespace
    })

    def _normalize_char_name(self, raw: str, known_bases: set) -> str:
        cleaned = ''.join(c for c in raw if ord(c) not in self._STRIP_CODES)
        for base in known_bases:
            base_clean = ''.join(c for c in base if ord(c) not in self._STRIP_CODES)
            if cleaned == base_clean:
                return base
            if cleaned.startswith(base_clean) and len(cleaned) > len(base_clean):
                rest = cleaned[len(base_clean):]
                if self._is_all_markers_or_particles(rest):
                    return base
            if cleaned.endswith(base_clean) and len(cleaned) > len(base_clean):
                rest = cleaned[:-len(base_clean)]
                if self._is_all_markers_or_particles(rest):
                    return base
        return raw

    def _is_all_markers_or_particles(self, text: str) -> bool:
        words = re.findall(r'[\u4e00-\u9fff]+', text)
        if not words:
            return True
        for w in words:
            if w not in self.PSEUDO_MARKERS and set(w) - set(self._PARTICLE_CHARS):
                return False
        return True

    def _load_or_extract_visual_bible(self, project, needed_chars: list, needed_scenes: list) -> dict:
        bible = {"characters": [], "scenes": [], "props": []}
        try:
            bible["characters"] = VisualBibleExtractor.list_characters(project)
            bible["scenes"] = VisualBibleExtractor.list_scenes(project)
            bible["props"] = VisualBibleExtractor.list_props(project)
        except Exception:
            pass

        existing_char_names = {c["name"] for c in bible["characters"]}
        existing_scene_names = {s["name"] for s in bible["scenes"]}

        missing_chars = [n for n in needed_chars if n not in existing_char_names]
        missing_scenes = [n for n in needed_scenes if n not in existing_scene_names]

        if missing_chars or missing_scenes:
            try:
                full_data = VisualBibleExtractor.extract_all(project)
                full_chars = {c["name"]: c for c in full_data.get("characters", [])}
                full_scenes = {s["name"]: s for s in full_data.get("scenes", [])}
                existing_char_map = {c["name"]: c for c in bible["characters"]}
                existing_scene_map = {s["name"]: s for s in bible["scenes"]}
                for name in missing_chars:
                    if name in full_chars:
                        existing_char_map[name] = full_chars[name]
                        VisualBibleExtractor._save_single_character(project, full_chars[name])
                for name in missing_scenes:
                    if name in full_scenes:
                        existing_scene_map[name] = full_scenes[name]
                bible["characters"] = list(existing_char_map.values())
                bible["scenes"] = list(existing_scene_map.values())
            except Exception:
                pass

        return bible

    def _parse_shots(self, content: str, episode: str) -> list:
        shots = []
        content = re.sub(r'^```\s*$', '', content, flags=re.MULTILINE)
        shot_blocks = re.split(r'\n---\n', content)
        current_chars = []
        current_scene = ""
        current_field = 1
        shot_regex = re.compile(r'^镜头(\d+)\s*\|\s*')

        for block in shot_blocks:
            stripped = block.strip()
            field_match = re.search(r'^###\s*第(\d+)场', stripped, re.MULTILINE)
            if field_match:
                current_field = int(field_match.group(1))
            is_shot = shot_regex.match(stripped)
            if not is_shot:
                m = re.search(r'^镜头(\d+)\s*\|\s*', stripped, re.MULTILINE)
                if m:
                    stripped = stripped[stripped.find(m.group(0)):]
                    is_shot = shot_regex.match(stripped)
            if is_shot:
                char_match = re.search(r'出场角色[：:]\s*(.*)', stripped)
                if char_match:
                    chars_str = char_match.group(1).strip()
                    if chars_str and chars_str != '-':
                        current_chars = [c.strip() for c in chars_str.split('、') if c.strip()]
                    else:
                        current_chars = []
                scene_match = re.search(r'场景[：:]\s*(.*)', stripped)
                if scene_match:
                    current_scene = scene_match.group(1).strip()
                shots.append({
                    "shot_number": int(is_shot.group(1)),
                    "episode": episode,
                    "characters": list(current_chars),
                    "scene": current_scene,
                    "field_number": current_field,
                })
        return shots

    def _clean_shot_char_name(self, raw_name: str) -> str:
        if not raw_name or not raw_name.strip():
            return ""
        name = raw_name.strip()
        if name in ('无', '无人', '无角色', '空', '-', '—'):
            return ""
        name = re.sub(r'[→→].*$', '', name).strip()
        name = re.sub(r'[（(][^)）]*[)）]', '', name).strip()
        if not name:
            return ""
        NON_CHAR_PREFIXES = (
            '无（', '屏幕', '画面', '声音', '声源', '文字', '字幕',
            '回执', '水渍', '残骸', '碎片', '火光', '烟雾', '照片',
            '镜头', '推近', '拉远', '淡入', '淡出',
        )
        for prefix in NON_CHAR_PREFIXES:
            if name.startswith(prefix):
                return ""
        if re.search(r'^第\d+场', name):
            return ""
        return name

    def _is_usable_character(self, c: dict) -> bool:
        name = c.get("name", "")
        GARBAGE_PREFIXES = (
            '无（', '无(', '屏幕', '画面', '声音', '声源', '文字', '字幕',
            '回执', '水渍', '残骸', '碎片', '火光', '烟雾', '照片',
            '镜头', '系统', '推近', '拉远', '淡入', '淡出', '图片',
        )
        for prefix in GARBAGE_PREFIXES:
            if name.startswith(prefix):
                return False
        if re.search(r'^第\d+场', name):
            return False
        has_data = (
            c.get("appearance") or c.get("clothing") or
            c.get("key_features") or c.get("accessories")
        )
        if not has_data and not c.get("prompt"):
            return False
        return True

    def _is_usable_scene(self, s: dict) -> bool:
        name = s.get("name", "")
        if not name.strip():
            return False
        GARBAGE_SCENE_PREFIXES = (
            '无（', '无(', '记忆-林川回忆', '画面',
            '声音', '声源', '文字', '字幕', '回执',
        )
        for prefix in GARBAGE_SCENE_PREFIXES:
            if name.startswith(prefix):
                return False
        if name.startswith('记忆-') and not s.get("environment"):
            return False
        return True

    def _canonicalize_variant(self, c: dict, base: str, all_char_names: set) -> str:
        """将语义相同的变体名归一化，检测跨角色引用。

        策略（通用，不依赖具体故事内容）：
        1. 剥离常见后缀（形态/投影/拟态/形象 等）→ 非角色名才生效
        2. 同 base 下剥离后相同的 → 合并为一个变体
        3. 变体名或描述包含其他已知角色名 → 标记 _cross_ref
        4. 同 base 下共享同一 cross_ref → 同一概念，合并
        5. 同 base 下仍不同但有字符重叠 → Jaccard ≥ 0.35 合并
        """
        vn = c.get("variant_name", "") or c.get("variant_tag", "") or ""
        fd = c.get("feature_desc", "") or c.get("appearance_change", "") or ""

        SUFFIXES = ("形态", "形象", "状态", "模式", "变体", "版本", "样式", "效果", "投影", "拟态", "变形", "幻化")
        stripped = vn
        for sfx in SUFFIXES:
            if stripped.endswith(sfx) and len(stripped) > len(sfx):
                candidate = stripped[:-len(sfx)]
                if candidate and candidate not in all_char_names:
                    stripped = candidate
                    break
        if not stripped or stripped in all_char_names:
            stripped = vn

        c["_stripped"] = stripped

        for char_name in sorted(all_char_names, key=len, reverse=True):
            if len(char_name) < 2 or char_name == base:
                continue
            if char_name in vn or char_name in fd:
                c["_cross_ref"] = char_name
                break

        return stripped

    def _dedupe_variants_by_similarity(self, chars: list, all_char_names: set) -> list:
        def _is_char_name(s: str) -> bool:
            return s in all_char_names and len(s) >= 2

        by_base = {}
        for i, c in enumerate(chars):
            base = c.get("character_base", c["name"])
            by_base.setdefault(base, []).append(i)

        merged_out = set()
        for base, indices in by_base.items():
            if len(indices) <= 1:
                continue
            for a_idx in range(len(indices)):
                for b_idx in range(a_idx + 1, len(indices)):
                    ai, bi = indices[a_idx], indices[b_idx]
                    sa = chars[ai].get("_stripped", "")
                    sb = chars[bi].get("_stripped", "")
                    if not sa or not sb or sa == sb:
                        continue
                    if not _is_char_name(sa) and not _is_char_name(sb):
                        if sa in sb or sb in sa:
                            merged_out.add(bi)
                            continue
                    cra = chars[ai].get("_cross_ref")
                    crb = chars[bi].get("_cross_ref")
                    if cra and crb and cra == crb:
                        merged_out.add(bi)
                        continue
                    if cra or crb:
                        continue
                    cs_a = set(sa)
                    cs_b = set(sb)
                    if not cs_a or not cs_b:
                        continue
                    intersection = cs_a & cs_b
                    union = cs_a | cs_b
                    jaccard = len(intersection) / len(union)
                    if jaccard >= 0.35:
                        merged_out.add(bi)

        return [c for i, c in enumerate(chars) if i not in merged_out]

    def _merge_with_bible(self, demand_chars: list, bible: dict) -> list:
        bible_chars = {c["name"]: c for c in bible.get("characters", [])}
        for dc in demand_chars:
            bc = bible_chars.get(dc["name"], {})
            dc["appearance"] = bc.get("appearance", "")
            dc["clothing"] = bc.get("clothing", "")
            dc["accessories"] = bc.get("accessories", [])
            dc["key_features"] = bc.get("key_features", [])
            dc["variant_name"] = bc.get("variant_name", "")
            dc["is_base"] = bc.get("is_base", True)
            dc["character_base"] = bc.get("character_base", dc.get("character_base", dc["name"]))
        return [c for c in demand_chars if self._is_usable_character(c)]

    def _merge_scenes_with_bible(self, demand_scenes: list, bible: dict) -> list:
        bible_scenes = {s["name"]: s for s in bible.get("scenes", [])}
        for ds in demand_scenes:
            bs = bible_scenes.get(ds["name"], {})
            ds["environment"] = bs.get("environment", "")
            ds["lighting"] = bs.get("lighting", "")
            ds["color_tone"] = bs.get("color_tone", "")
            ds["props"] = bs.get("props", [])
            ds["scene_base"] = bs.get("scene_base", ds["name"])
            ds["is_base"] = bs.get("is_base", True)
            ds["variant_name"] = bs.get("variant_name", "")
        return [s for s in demand_scenes if self._is_usable_scene(s)]

    def _categorize_props(self, bible: dict) -> dict:
        all_props = bible.get("props", [])
        bible_scenes = bible.get("scenes", [])

        scene_name_variants = {}
        for s in bible_scenes:
            sn = s.get("name", "")
            base = s.get("scene_base", "")
            for v in (sn, base):
                if v and len(v) >= 2:
                    scene_name_variants.setdefault(v, set()).add(sn)

        cross_scene_props = []
        scene_props = []
        char_props = {}

        for p in all_props:
            name = p.get("name", "")
            owner = (p.get("owner") or "").strip()
            appearance = p.get("appearance", "") or p.get("description", "")
            category = p.get("category", "")
            prop_scene = p.get("scene", "") or ""

            matched_scenes = set()
            for variant, canonicals in scene_name_variants.items():
                if variant in prop_scene or (prop_scene and prop_scene in variant):
                    matched_scenes.update(canonicals)
            scenes = sorted(matched_scenes)
            scene_count = len(scenes)

            entry = {
                "name": name,
                "appearance": appearance,
                "category": category,
                "scenes": scenes,
                "scene_count": scene_count,
                "prompt": PromptBuilder.generate_prop_prompt(p),
            }
            if any(kw in category for kw in ("跨场景", "关键")):
                cross_scene_props.append(entry)
            elif "随身" in category and owner:
                char_props.setdefault(owner, []).append(entry)
            else:
                scene_props.append(entry)

        cross_scene_props.sort(key=lambda x: x["name"])
        scene_props.sort(key=lambda x: x["name"])

        return {"cross_scene_props": cross_scene_props, "scene_props": scene_props, "char_props": char_props}

    def _fallback_full(self, project: ProjectManager) -> dict:
        try:
            chars = VisualBibleExtractor.list_characters(project)
            scenes = VisualBibleExtractor.list_scenes(project)
            props = VisualBibleExtractor.list_props(project)
        except Exception:
            chars, scenes, props = [], [], []

        char_result = [{
            "name": c["name"], "shot_indices": [], "episodes": [],
            "appearance": c.get("appearance", ""), "clothing": c.get("clothing", ""),
            "accessories": c.get("accessories", []), "key_features": c.get("key_features", []),
            "prompt": PromptBuilder.generate_character_prompt(c, mode="base"),
        } for c in chars]
        scene_result = [{
            "name": s["name"], "shot_indices": [], "episodes": [],
            "environment": s.get("environment", ""), "lighting": s.get("lighting", ""),
            "color_tone": s.get("color_tone", ""), "props": s.get("props", []),
            "prompt": PromptBuilder.generate_scene_prompt(s, angle=""),
        } for s in scenes]
        key_props = [{
            "name": p["name"], "appearance": p.get("appearance", "") or p.get("description", ""),
            "category": p.get("category", ""),
            "prompt": PromptBuilder.generate_prop_prompt(p),
        } for p in props]

        return {
            "characters": char_result,
            "scenes": scene_result,
            "key_props": key_props,
            "total_shots": 0,
            "episodes": [],
            "fallback": True,
        }

    def _build_report(self, result: dict) -> str:
        chars = result.get("characters", [])
        scenes = result.get("scenes", [])
        cross_scene_props = result.get("cross_scene_props", [])
        scene_props = result.get("scene_props", [])
        total_props = len(cross_scene_props) + len(scene_props)
        total_shots = result.get("total_shots", 0)
        is_fallback = result.get("fallback", False)

        report = f"✅ 生图准备完成\n\n"
        if is_fallback:
            report += "⚠️ 未找到分镜脚本，已回退为全量模式\n\n"
        report += f"## 统计数据\n"
        report += f"- 扫描镜头数：{total_shots}\n"
        report += f"- 去重后角色出场状态：{len(chars)} 个\n"
        report += f"- 去重后场景：{len(scenes)} 个\n"
        if total_props:
            report += f"- 道具：{total_props} 个（跨场景 {len(cross_scene_props)} + 场景 {len(scene_props)}）\n"
        report += f"\n## 角色出场清单\n"
        for c in chars[:30]:
            eps = '、'.join(c.get('episodes', []))
            shots = c.get('shot_indices', [])
            accs = '、'.join(c.get('accessories', []))
            report += f"- {c['name']}"
            if accs:
                report += f"（配饰：{accs}）"
            if shots:
                report += f" → 镜头 {len(shots)} 次"
            if eps:
                report += f" | {eps}"
            report += "\n"
        if len(chars) > 30:
            report += f"... 还有 {len(chars)-30} 个角色\n"
        report += f"\n## 场景清单\n"
        for s in scenes:
            shots = s.get('shot_indices', [])
            report += f"- {s['name']} → 镜头 {len(shots)} 次\n"
        if cross_scene_props:
            report += f"\n## 跨场景道具\n"
            for p in cross_scene_props:
                report += f"- {p['name']}（{p.get('category', '')}）\n"
        if scene_props:
            report += f"\n## 场景道具\n"
            for p in scene_props:
                report += f"- {p['name']}（出现在 {p.get('scene_count', 0)} 个场景）\n"
        return report

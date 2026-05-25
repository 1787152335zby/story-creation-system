import json
import re
from pathlib import Path
from core.agent_base import AgentBase
from core.project_manager import ProjectManager
from core.style_config import StyleConfig
from core.visual_bible import VisualBibleExtractor


class ImageDemandAnalyzer(AgentBase):

    def run(self, project: ProjectManager, style: StyleConfig, input_content: str) -> str:
        return json.dumps(self.analyze(project), ensure_ascii=False, indent=2)

    def run_stream(self, project: ProjectManager, style: StyleConfig, input_content: str):
        result = self.analyze(project)
        report = self._build_report(result, project)
        for chunk in [report[i:i+100] for i in range(0, len(report), 100)]:
            yield chunk

    def analyze(self, project: ProjectManager) -> dict:
        storyboard_dir = project.project_dir / "05_分镜脚本"
        if not storyboard_dir.exists():
            return self._fallback_full(project)

        ep_dirs = sorted([d for d in storyboard_dir.iterdir() if d.is_dir()])
        if not ep_dirs:
            sb_file = storyboard_dir / "分镜脚本.md"
            if sb_file.exists():
                return self._parse_storyboard(str(sb_file), project)
            return self._fallback_full(project)

        all_char_states = {}
        all_scene_states = {}
        all_episodes = []
        shot_counter = 0

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
                for char_name in shot.get("characters", []):
                    key = self._char_state_key(char_name, shot, project)
                    if key not in all_char_states:
                        all_char_states[key] = {
                            "name": char_name,
                            "state": key,
                            "scene": shot.get("scene", ""),
                            "shot_indices": [],
                            "episodes": [],
                        }
                    all_char_states[key]["shot_indices"].append(shot_counter)
                    if ep_name not in all_char_states[key]["episodes"]:
                        all_char_states[key]["episodes"].append(ep_name)

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

        visual_bible = self._load_visual_bible(project)
        characters = self._merge_with_bible(list(all_char_states.values()), visual_bible)
        scenes = self._merge_scenes_with_bible(list(all_scene_states.values()), visual_bible)
        key_props = self._extract_key_props(project)

        result = {
            "characters": characters,
            "scenes": scenes,
            "key_props": key_props,
            "total_shots": shot_counter,
            "episodes": all_episodes,
        }
        output_dir = project.project_dir / "07_生图需求"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "生图清单.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

        return result

    def _parse_shots(self, content: str, episode: str) -> list:
        shots = []
        shot_blocks = re.split(r'\n---\n', content)
        current_chars = []
        current_scene = ""
        shot_regex = re.compile(r'^镜头(\d+)\s*\|\s*')

        for block in shot_blocks:
            is_shot = shot_regex.match(block.strip())
            if is_shot:
                char_match = re.search(r'出场角色[：:]\s*(.*)', block)
                if char_match:
                    chars_str = char_match.group(1).strip()
                    if chars_str and chars_str != '-':
                        current_chars = [c.strip() for c in chars_str.split('、') if c.strip()]
                    else:
                        current_chars = []
                scene_match = re.search(r'场景[：:]\s*(.*)', block)
                if scene_match:
                    current_scene = scene_match.group(1).strip()
                shots.append({
                    "shot_number": int(is_shot.group(1)),
                    "episode": episode,
                    "characters": list(current_chars),
                    "scene": current_scene,
                })
        return shots

    def _char_state_key(self, name: str, shot: dict, project: ProjectManager) -> str:
        return name

    def _load_visual_bible(self, project: ProjectManager) -> dict:
        try:
            chars = VisualBibleExtractor.list_characters(project)
            scenes = VisualBibleExtractor.list_scenes(project)
            props = VisualBibleExtractor.list_props(project)
            return {"characters": chars, "scenes": scenes, "props": props}
        except Exception:
            return {"characters": [], "scenes": [], "props": []}

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
        return demand_chars

    def _merge_scenes_with_bible(self, demand_scenes: list, bible: dict) -> list:
        bible_scenes = {s["name"]: s for s in bible.get("scenes", [])}
        for ds in demand_scenes:
            bs = bible_scenes.get(ds["name"], {})
            ds["environment"] = bs.get("environment", "")
            ds["lighting"] = bs.get("lighting", "")
            ds["color_tone"] = bs.get("color_tone", "")
            ds["props"] = bs.get("props", [])
        return demand_scenes

    def _extract_key_props(self, project: ProjectManager) -> list:
        try:
            all_props = VisualBibleExtractor.list_props(project)
        except Exception:
            return []
        key_props = []
        for p in all_props:
            if p.get("prop_class") == "关键道具" and p.get("type") not in ("佩戴", "手持", "随身道具"):
                key_props.append({
                    "name": p["name"],
                    "appearance": p.get("appearance", "") or p.get("description", ""),
                    "prop_class": p.get("prop_class", ""),
                })
        return key_props

    def _fallback_full(self, project: ProjectManager) -> dict:
        chars = VisualBibleExtractor.list_characters(project)
        scenes = VisualBibleExtractor.list_scenes(project)
        props = VisualBibleExtractor.list_props(project)
        result = {
            "characters": [{"name": c["name"], "state": c["name"], "shot_indices": [], "episodes": [],
                           "appearance": c.get("appearance", ""), "clothing": c.get("clothing", ""),
                           "accessories": c.get("accessories", []), "key_features": c.get("key_features", [])}
                           for c in chars],
            "scenes": [{"name": s["name"], "shot_indices": [], "episodes": [],
                       "environment": s.get("environment", ""), "lighting": s.get("lighting", ""),
                       "color_tone": s.get("color_tone", ""), "props": s.get("props", [])}
                       for s in scenes],
            "key_props": [{"name": p["name"], "appearance": p.get("appearance", "") or p.get("description", ""),
                          "prop_class": p.get("prop_class", "")} for p in props],
            "total_shots": 0,
            "episodes": [],
            "fallback": True,
        }
        return result

    def _build_report(self, result: dict, project: ProjectManager) -> str:
        chars = result.get("characters", [])
        scenes = result.get("scenes", [])
        key_props = result.get("key_props", [])
        total_shots = result.get("total_shots", 0)
        is_fallback = result.get("fallback", False)

        report = f"✅ 生图需求分析完成\n\n"
        if is_fallback:
            report += "⚠️ 未找到分镜脚本，已回退为全量模式\n\n"
        report += f"## 统计数据\n"
        report += f"- 扫描镜头数：{total_shots}\n"
        report += f"- 去重后角色出场状态：{len(chars)} 个\n"
        report += f"- 去重后场景：{len(scenes)} 个\n"
        report += f"- 关键线索道具：{len(key_props)} 个\n\n"
        report += f"## 角色出场清单\n"
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
        if key_props:
            report += f"\n## 关键线索道具\n"
            for p in key_props:
                report += f"- {p['name']}\n"
        return report

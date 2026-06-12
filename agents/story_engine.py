import json
import math
import re
from core.agent_base import AgentBase


def _extract_concept_from_outline(outline_text: str) -> str:
    """从大纲文本中提取核心设定+角色概要，作为节拍表生成的concept输入"""
    lines = outline_text.split("\n")
    sections = {
        "梗概": [],
        "人物": [],
        "设定": [],
    }
    current = "梗概"
    for line in lines:
        stripped = line.strip()
        if re.match(r"^#{1,3}\s*[一二三]", stripped) or "人物设定" in stripped or "角色" in stripped:
            current = "人物"
            continue
        if "背景" in stripped or "世界观" in stripped or "设定" in stripped:
            current = "设定"
            continue
        if current == "人物":
            if re.match(r"^\d+\.\s*\*\*", stripped) or re.match(r"^###\s*\d+\.", stripped) or re.match(r"^\*\*?\d+\.", stripped):
                sections[current].append(stripped)
            elif re.match(r"^[姓名外表性格背景目标动机]", stripped):
                sections[current].append(stripped)
            elif stripped and not stripped.startswith("#") and not stripped.startswith("---"):
                if any(k in stripped for k in ["说话方式", "对白", "声线", "标签"]):
                    sections[current].append(stripped)
        elif current == "梗概":
            if stripped and not stripped.startswith("#") and not stripped.startswith("---") and len(stripped) > 20:
                sections[current].append(stripped)
        elif current == "设定":
            if stripped and not stripped.startswith("#") and not stripped.startswith("---") and len(stripped) > 10:
                sections[current].append(stripped)

    parts = []
    if sections["梗概"]:
        parts.append("## 故事梗概\n" + "\n".join(sections["梗概"][:20]))
    if sections["人物"]:
        parts.append("## 角色概要\n" + "\n".join(sections["人物"][:50]))
    if sections["设定"]:
        parts.append("## 世界观设定\n" + "\n".join(sections["设定"][:10]))
    return "\n\n".join(parts)


def _build_phase_plan(total: int) -> str:
    p2 = max(4, math.ceil(total * 0.08))
    p3_start = max(p2 + 1, math.ceil(total * 0.18))
    p4_start = max(p3_start + 1, math.ceil(total * 0.40))
    p5_start = max(p4_start + 1, math.ceil(total * 0.70))
    p6_start = max(p5_start + 1, math.ceil(total * 0.90))

    if p6_start >= total:
        p6_start = total

    p2_transition = p3_start - 2
    p3_transition = p4_start - 2
    p4_transition = p5_start - 2
    p5_transition = p6_start - 2
    breakable_mid = p3_transition + max(3, (p4_transition - p3_transition) // 3)

    return f"""第1-3集（phase: rule_surface）：主角获得什么能力、付出什么代价——只展示表象，不解释原因
第4-{p2}集（phase: rule_origin_clue）：能力不是天生的，第一次出现暗示——不解释，只留画面
第{p2 + 1}-{p2_transition}集（phase: origin_transition）：线索积累，暗示组织存在但主角尚未确认
第{p2_transition + 1}-{p3_transition}集（phase: organization_emerge）：组织首次出现——不揭示全貌
第{p3_transition + 1}-{breakable_mid}集（phase: rule_breakable）：主角找到对抗规则的方法——付出巨大代价
第{breakable_mid + 1}-{p4_transition}集（phase: breakable_transition）：对抗方法的代价扩散，身体逐步被标记
第{p4_transition + 1}-{p5_transition}集（phase: rule_cost）：打破规则的后果滚雪球，代价累积到临界点
第{p5_transition + 1}-{total}集（phase: final_choice）：所有线索收束，主角做出最终选择"""


class StoryEngine(AgentBase):

    def run(self, concept: str, episode_count: int) -> list[dict]:
        template = self.load_prompt_template("story_engine.txt")
        phase_plan = _build_phase_plan(episode_count)
        twist1 = max(12, math.ceil(episode_count * 0.25))
        twist2 = max(twist1 + 6, math.ceil(episode_count * 0.40))
        twist3 = max(twist2 + 10, math.ceil(episode_count * 0.70))
        p4_start = max(math.ceil(episode_count * 0.18) + 1, math.ceil(episode_count * 0.40))
        p5_start = max(p4_start + 1, math.ceil(episode_count * 0.70))
        genre_reversal = max(8, math.ceil(episode_count * 0.15))
        genre_reversal_end = genre_reversal + 3
        deform_ep = max(p4_start + 5, p4_start + (p5_start - p4_start) // 2)
        p4_transition = p5_start - 2
        p6_start = max(p5_start + 1, math.ceil(episode_count * 0.90))
        p5_transition = p6_start - 2
        anchor_ep = max(p4_transition + 5, p4_transition + (p5_transition - p4_transition) // 2)
        side1 = max(8, twist1 - 2)
        side2 = max(side1 + 8, twist2 - 2)
        side3 = max(side2 + 8, anchor_ep - 2)
        prompt = template.replace("{episode_count}", str(episode_count))
        prompt = prompt.replace("{phase_plan}", phase_plan)
        prompt = prompt.replace("{twist1}", str(twist1))
        prompt = prompt.replace("{twist2}", str(twist2))
        prompt = prompt.replace("{twist3}", str(twist3))
        prompt = prompt.replace("{genre_reversal}", str(genre_reversal))
        prompt = prompt.replace("{genre_reversal_end}", str(genre_reversal_end))
        prompt = prompt.replace("{deform_ep}", str(deform_ep))
        prompt = prompt.replace("{anchor_ep}", str(anchor_ep))
        prompt = prompt.replace("{side1}", str(side1))
        prompt = prompt.replace("{side2}", str(side2))
        prompt = prompt.replace("{side3}", str(side3))
        prompt = prompt.replace("{concept}", concept)

        raw = self._generate_full_beats(prompt, target_count=episode_count)
        beats = self._parse_json(raw)
        if len(beats) < episode_count:
            missing = episode_count - len(beats)
            if len(beats) > 0 and missing < episode_count * 0.25:
                raw = self.llm.chat(
                    prompt + f"\n\n⚠️ 你只输出了 {len(beats)} 集（目标 {episode_count} 集）。续写剩余 {missing} 集的 JSON。\n\n已输出的最后3集：\n{json.dumps(beats[-3:], ensure_ascii=False, indent=2)}\n\n从 episode {len(beats) + 1} 开始续写：",
                    "", temperature=0.85, max_tokens=32768)
                beats.extend(self._parse_json(raw))
            if len(beats) < episode_count * 0.5:
                raw = self.llm.chat(
                    prompt + f"\n\n⚠️ 你上次只输出了{len(beats)}条。必须输出完整{episode_count}条JSON数组。请从episode 1开始完整输出。",
                    "", temperature=0.85, max_tokens=65536)
                beats = self._parse_json(raw)
        return beats[:episode_count] if beats else []

    def run_from_outline(self, outline_text: str, episode_count: int, project=None, output_path: str = "") -> list[dict]:
        """从大纲文本生成节拍表，如果提供了 project 和 output_path 则自动保存"""
        concept = _extract_concept_from_outline(outline_text) or outline_text[:3000]
        beats = self.run(concept, episode_count)
        if project and output_path and beats:
            project.write_output(output_path, json.dumps(beats, ensure_ascii=False, indent=2))
        return beats

    def _generate_full_beats(self, system_prompt: str, target_count: int) -> str:
        full = ""
        for attempt in range(6):
            cur = system_prompt
            if attempt > 0:
                cur = system_prompt + (
                    "\n\n---[续写]---\n"
                    "收起已输出的JSON数组末尾，直接继续。不要重复前面的episode。\n"
                    f"已输出内容末尾：\n{full[-1500:]}\n\n"
                    "从下一集的 JSON 对象继续。"
                )
            chunk = self.llm.chat(cur, "", temperature=0.85, max_tokens=65536)
            full += chunk
            beats = self._parse_json(full)
            if len(beats) >= target_count:
                break
            if "]}" in chunk[-50:] or (chunk.strip() and chunk.strip()[-1] == "]"):
                break
        return full

    def _parse_json(self, raw: str) -> list[dict]:
        raw = raw.strip()
        start = raw.find("[")
        end = raw.rfind("]")
        if start >= 0 and end > start:
            raw = raw[start:end + 1]
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass

        objects = []
        depth = 0
        buf = ""
        in_string = False
        escape = False
        for ch in raw:
            if escape:
                buf += ch
                escape = False
                continue
            if ch == "\\" and in_string:
                buf += ch
                escape = True
                continue
            if ch == '"' and not escape:
                in_string = not in_string
                buf += ch
                continue
            if in_string:
                buf += ch
                continue
            if ch == "{":
                depth += 1
                buf += ch
            elif ch == "}":
                depth -= 1
                buf += ch
                if depth == 0 and buf.strip():
                    try:
                        objects.append(json.loads(buf))
                    except json.JSONDecodeError:
                        pass
                    buf = ""
            elif depth > 0:
                buf += ch
        return objects

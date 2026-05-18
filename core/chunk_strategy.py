from dataclasses import dataclass, field
from typing import List, Optional
import re


@dataclass
class ChunkPlan:
    chunk_count: int
    chunk_names: List[str]
    reverse_order: bool
    delimiter: str
    context_window: int
    summarize: bool
    bible_mode: bool = False


@dataclass
class ChunkContext:
    index: int
    name: str
    outline_section: str
    previous_full_texts: List[str] = field(default_factory=list)
    summaries: List[str] = field(default_factory=list)


class ChunkStrategy:
    @staticmethod
    def get_plan(story_type: str) -> ChunkPlan:
        plan_map = {
            "2": ChunkPlan(3, ["第一幕", "第二幕", "第三幕"], True,
                           r"^#{1,4}\s*(第一幕|第二幕|第三幕)", 0, True),
            "5": ChunkPlan(3, ["第一幕", "第二幕", "第三幕"], True,
                           r"^#{1,4}\s*(第一幕|第二幕|第三幕)", 0, True),
            "1": ChunkPlan(0, [], False, r"^#{1,4}\s*第\d+集", 3, True),
            "3": ChunkPlan(0, [], False, r"^#{1,4}\s*第\d+集", 2, True),
            "4": ChunkPlan(0, [], False, r"^#{1,4}\s*第\d+章", 3, True, bible_mode=True),
            "6": ChunkPlan(0, [], False, r"^#{1,4}\s*第\d+集", 0, True),
        }
        return plan_map.get(story_type, ChunkPlan(1, ["全部"], False, "", 0, False))

    @staticmethod
    def pre_analyze_split_points(outline: str, llm_stream_callable) -> list:
        """预分析大纲的最佳分割点，返回分割点标签列表"""
        if not outline or len(outline) < 500:
            return None
        prompt = (
            "以下是一个故事大纲。请判断它最适合按什么结构分割。\n\n"
            "如果故事有明确的幕/集/章标题，按原结构输出分割点。\n"
            "如果故事没有明确标题，请分析故事情节中的自然断点（重大事件转折、时间跳转、场景切换），推荐分割方案。\n\n"
            "输出格式：每行一个分割点，格式为「分割点N：标签名」。\n"
            "只输出分割点列表，不要解释。\n\n"
            f"{outline[:4000]}"
        )
        result = ""
        for token in llm_stream_callable(prompt, "", temperature=0.3):
            result += token
        split_points = []
        for line in result.strip().split("\n"):
            line = line.strip()
            if "：" in line:
                label = line.split("：", 1)[1].strip()
                split_points.append(label)
            elif ":" in line:
                label = line.split(":", 1)[1].strip()
                split_points.append(label)
        return split_points if len(split_points) >= 2 else None


class ChunkIter:
    def __init__(self, plan: ChunkPlan, outline: str, pre_analyzed: list = None):
        self.plan = plan
        if plan.chunk_count > 0:
            self.blocks = self._parse_fixed(outline, plan)
            if not self.blocks and pre_analyzed:
                per_chunk = len(outline) // len(pre_analyzed)
                plan.chunk_count = len(pre_analyzed)
                plan.chunk_names = pre_analyzed
                self.blocks = []
                for i, name in enumerate(pre_analyzed):
                    start = i * per_chunk
                    end = (i + 1) * per_chunk if i < len(pre_analyzed) - 1 else len(outline)
                    self.blocks.append({"index": i, "name": name, "content": outline[start:end]})
        else:
            self.blocks = []

    @staticmethod
    def _parse_fixed(outline: str, plan: ChunkPlan) -> List[dict]:
        pattern = re.compile(plan.delimiter, re.MULTILINE)
        sections = pattern.split(outline)
        blocks = []
        labels = [s.strip() for s in sections[1::2]]
        contents = [s.strip() for s in sections[2::2]]
        for i, (label, content) in enumerate(zip(labels, contents)):
            blocks.append({"index": i, "name": label, "content": content})
        if not blocks and plan.chunk_count > 0:
            per_chunk = len(outline) // plan.chunk_count
            for i in range(plan.chunk_count):
                start = i * per_chunk
                end = (i + 1) * per_chunk if i < plan.chunk_count - 1 else len(outline)
                blocks.append({"index": i, "name": plan.chunk_names[i], "content": outline[start:end]})
        return blocks

    def set_auto_blocks(self, count: int):
        self.plan.chunk_count = count
        self.plan.chunk_names = [f"第{i+1}集" for i in range(count)]
        self.blocks = [{"index": i, "name": self.plan.chunk_names[i], "content": ""} for i in range(count)]

    def __iter__(self):
        indices = list(range(len(self.blocks)))
        if self.plan.reverse_order:
            indices = list(reversed(indices))
        processed_indices = []
        for idx in indices:
            blk = self.blocks[idx]
            prev_texts = []
            prev_summaries = []
            for prev_idx in sorted(processed_indices):
                prev_texts.append(self.blocks[prev_idx].get("_output", ""))
                prev_summaries.append(self.blocks[prev_idx].get("_summary", ""))
            if self.plan.context_window > 0:
                prev_texts = prev_texts[-self.plan.context_window:]
                prev_summaries = prev_summaries[-self.plan.context_window:]
            yield ChunkContext(
                index=blk["index"],
                name=blk["name"],
                outline_section=blk["content"],
                previous_full_texts=prev_texts,
                summaries=prev_summaries,
            )
            processed_indices.append(idx)

    def set_output(self, index: int, output: str, summary: str = ""):
        for blk in self.blocks:
            if blk["index"] == index:
                blk["_output"] = output
                blk["_summary"] = summary
                break

    def get_all_outputs(self) -> List[dict]:
        return [{"name": b["name"], "output": b.get("_output", "")} for b in self.blocks]

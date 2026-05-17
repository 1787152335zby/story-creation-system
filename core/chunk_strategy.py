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


class ChunkIter:
    def __init__(self, plan: ChunkPlan, outline: str):
        self.plan = plan
        if plan.chunk_count > 0:
            self.blocks = self._parse_fixed(outline, plan)
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

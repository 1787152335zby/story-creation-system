class SummaryExtractor:
    @staticmethod
    def build_summary_prompt(chunk_name: str, chunk_content: str) -> str:
        max_preview = chunk_content[:2500]
        return (
            f"以下是一段故事的\"{chunk_name}\"内容。请提取关键元素作为结构化摘要。\n\n"
            f"内容：\n{max_preview}\n\n"
            f"请按以下格式输出：\n"
            f"## 关键元素追踪\n"
            f"- 未解悬念：\n"
            f"- 角色状态变化：\n"
            f"- 重要道具/线索：\n"
            f"- 时间线推进：\n"
            f"- 情绪基调："
        )

    @staticmethod
    def parse_summary(text: str) -> str:
        lines = []
        in_summary = False
        for line in text.split("\n"):
            if line.startswith("## 关键元素追踪"):
                in_summary = True
            if in_summary:
                lines.append(line)
        return "\n".join(lines) if lines else text.strip()

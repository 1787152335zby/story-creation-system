from typing import Optional, Generator
from pathlib import Path
from .style_config import StyleConfig
from .project_manager import ProjectManager
from llm.client import LLMClient


class AgentBase:
    END_MARKERS = ["全片完", "【全片完】", "本集完", "（本集完）", "（全片完）", "剧终", "THE END", "全文完", "（全文完）"]

    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm = llm_client or LLMClient()

    def load_prompt_template(self, prompt_file: str) -> str:
        prompt_path = Path(__file__).resolve().parent.parent / "prompts" / prompt_file
        if prompt_path.exists():
            with open(prompt_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def call_llm(self, system_prompt: str, user_prompt: str, temperature: float = 0.7, max_tokens: int = 16384) -> str:
        return self.llm.chat(system_prompt, user_prompt, temperature, max_tokens)

    def call_llm_with_continuation(self, system_prompt: str, user_prompt: str, temperature: float = 0.7) -> str:
        full_output = ""
        for attempt in range(8):
            current_system = system_prompt
            if attempt > 0:
                current_system = system_prompt + (
                    f"\n\n---[续写指示]---\n"
                    f"你已生成了部分内容，最后2000字如下：\n"
                    f"{full_output[-2000:]}\n\n"
                    f"请直接继续输出后续内容，不要做任何额外说明。"
                    f"全部完成后输出【全片完】。"
                )
            chunk = self.llm.chat(current_system, "", temperature, max_tokens=16384)
            full_output += chunk

            has_end_marker = any(marker in chunk for marker in self.END_MARKERS)
            if has_end_marker:
                break

            if attempt == max_rounds - 1:
                full_output += "\n\n> ⚠️ 注意：输出可能因长度限制被截断，建议审核后决定是否继续。"

        return full_output

    def get_style_context(self, style: StyleConfig) -> str:
        return style.to_yaml_string()

    def call_llm_stream(self, system_prompt: str, user_prompt: str, temperature: float = 0.7):
        for chunk in self.llm.backend.chat_stream(system_prompt, user_prompt, temperature):
            yield chunk

    async def async_call_llm_stream(self, system_prompt: str, user_prompt: str, temperature: float = 0.7):
        import asyncio
        loop = asyncio.get_event_loop()
        queue = asyncio.Queue()

        def _run():
            try:
                for chunk in self.llm.backend.chat_stream(system_prompt, user_prompt, temperature):
                    loop.call_soon_threadsafe(queue.put_nowait, chunk)
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, None)

        asyncio.get_running_loop().run_in_executor(None, _run)

        while True:
            chunk = await queue.get()
            if chunk is None:
                break
            yield chunk

    def _extract_foreshadowing(self, content: str) -> str:
        """从前文提取未解决的伏笔、悬疑和待回收线索"""
        extraction_prompt = (
            "请从以下故事大纲/剧情中提取【尚未揭示或尚未解决的伏笔/悬疑/待回收线索】：\n"
            "1. 只提取在已有内容中提到了、但在已有内容中还没有揭示真相的线索\n"
            "2. 每条30字以内，最多5条\n"
            "3. 如果没有尚未解决的伏笔，请回复「无」\n\n"
            f"{content}"
        )
        try:
            result = self.llm.chat(extraction_prompt, "", temperature=0.3, max_tokens=500)
            return result.strip()
        except Exception:
            return ""

    def call_llm_stream_with_continuation(self, system_prompt: str, user_prompt: str, temperature: float = 0.7, max_rounds: int = 8, end_markers: list = None, continuation_prompt: str = ""):
        """流式调用 LLM，支持自定义结束标记检测、自动续写和伏笔追踪。

        Args:
            end_markers: 自定义结束标记列表，如果检测到这些标记则立即停止输出
            continuation_prompt: 当遇到续写时的附加提示词，为空时自动注入上下文和伏笔续写
        """
        full_output = ""
        custom_end_markers = end_markers or []
        foreshadowing = ""

        if custom_end_markers:
            all_end_markers = custom_end_markers
        else:
            all_end_markers = list(self.END_MARKERS)

        found_end = False

        for attempt in range(max_rounds):
            if found_end:
                break

            current_system = system_prompt
            if attempt > 0:
                if not foreshadowing and not continuation_prompt:
                    foreshadowing = self._extract_foreshadowing(full_output)

                foreshadowing_block = ""
                if foreshadowing and foreshadowing != "无":
                    foreshadowing_block = (
                        f"\n\n【伏笔清单 — 以下线索在后续内容中必须交代】\n"
                        f"{foreshadowing}\n"
                    )

                context_injection = (
                    f"\n\n---[续写指示]---\n"
                    f"你已生成了部分内容，最后已写到的部分如下：\n"
                    f"{full_output[-3000:]}\n\n"
                    f"{foreshadowing_block}"
                    f"请直接从上面断开的地方继续输出后续内容。"
                    f"【不要】重复已输出过的剧集或内容。"
                    f"请在后续内容中酌情回收上述伏笔。"
                    f"如果已全部完成，输出【全片完】。"
                )
                current_system = system_prompt + (continuation_prompt or context_injection)

            for chunk in self.llm.backend.chat_stream(current_system, "", temperature):
                if found_end:
                    break

                full_output += chunk
                yield chunk

                # 实时检测结束标记，找到立即停止
                if custom_end_markers:
                    for marker in custom_end_markers:
                        if marker in full_output:
                            found_end = True
                            break
                    if found_end:
                        break

            # 只要找到结束标记，立即停止所有循环
            if found_end:
                break

            # 如果没有自定义结束标记，检查默认结束标记
            if not custom_end_markers:
                round_has_end = any(marker in full_output[-500:] for marker in all_end_markers)
                if round_has_end:
                    break

        # 只有当没有找到结束标记，并且是最后一轮时，才显示截断警告
        if not found_end and attempt == max_rounds - 1 and not custom_end_markers:
            yield "\n\n> ⚠️ 注意：输出可能因长度限制被截断，建议审核后决定是否继续。"

    def run(self, project: ProjectManager, style: StyleConfig, input_content: str) -> str:
        raise NotImplementedError

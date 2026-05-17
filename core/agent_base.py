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

    def call_llm_stream_with_continuation(self, system_prompt: str, user_prompt: str, temperature: float = 0.7, max_rounds: int = 8):
        """流式调用 LLM，自动检测内容是否完整，不完整则自动续写。
        用 system_prompt 传递续写上下文，保持 user_prompt 始终为空，
        避免 LLM 因为看到新的 user 消息而"跳出角色"写元文本。
        """
        full_output = ""
        for attempt in range(max_rounds):
            current_system = system_prompt
            if attempt > 0:
                current_system = system_prompt + (
                    f"\n\n---[续写指示]---\n"
                    f"你已生成了部分内容，最后2000字如下：\n"
                    f"{full_output[-2000:]}\n\n"
                    f"请直接继续输出后续内容，不要做任何额外说明、不要打招呼、不要写'好的'等。"
                    f"全部完成后输出【全片完】。"
                )
            round_buffer = ""
            for chunk in self.llm.backend.chat_stream(current_system, "", temperature):
                round_buffer += chunk
                full_output += chunk
                yield chunk

            has_end = any(marker in round_buffer for marker in self.END_MARKERS)
            if has_end:
                break

            if attempt == max_rounds - 1:
                yield "\n\n> ⚠️ 注意：输出可能因长度限制被截断，建议审核后决定是否继续。"

    def run(self, project: ProjectManager, style: StyleConfig, input_content: str) -> str:
        raise NotImplementedError

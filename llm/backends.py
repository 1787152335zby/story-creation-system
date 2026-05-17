import os
from typing import Optional, Generator


class LLMBackend:
    def __init__(self, model: str, api_key: str | None = None, base_url: str | None = None):
        self.model = model
        self._api_key = api_key
        self._base_url = base_url

    def chat(self, system_prompt: str, user_prompt: str, temperature: float = 0.7) -> str:
        raise NotImplementedError

    def chat_stream(self, system_prompt: str, user_prompt: str, temperature: float = 0.7, max_tokens: int = 16384) -> Generator[str, None, None]:
        raise NotImplementedError

    def _get_client(self):
        raise NotImplementedError


class OpenAIBackend(LLMBackend):
    def __init__(self, model: str = "gpt-4o", api_key: str | None = None, base_url: str | None = None):
        super().__init__(model, api_key, base_url)

    def _get_client(self):
        from openai import OpenAI
        return OpenAI(
            api_key=self._api_key or os.getenv("OPENAI_API_KEY"),
            base_url=self._base_url or None,
            timeout=120,
        )

    def chat(self, system_prompt: str, user_prompt: str, temperature: float = 0.7, max_tokens: int = 16384) -> str:
        response = self._get_client().chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content

    def chat_stream(self, system_prompt: str, user_prompt: str, temperature: float = 0.7, max_tokens: int = 16384):
        response = self._get_client().chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        for chunk in response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


class ClaudeBackend(LLMBackend):
    def __init__(self, model: str = "claude-sonnet-4-20250514", api_key: str | None = None, base_url: str | None = None):
        super().__init__(model, api_key, base_url)

    def _get_client(self):
        from anthropic import Anthropic
        kwargs = {"api_key": self._api_key or os.getenv("CLAUDE_API_KEY"), "timeout": 120}
        if self._base_url:
            kwargs["base_url"] = self._base_url
        return Anthropic(**kwargs)

    def chat(self, system_prompt: str, user_prompt: str, temperature: float = 0.7, max_tokens: int = 16384) -> str:
        response = self._get_client().messages.create(
            model=self.model,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.content[0].text

    def chat_stream(self, system_prompt: str, user_prompt: str, temperature: float = 0.7, max_tokens: int = 16384):
        with self._get_client().messages.stream(
            model=self.model,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        ) as stream:
            for text in stream.text_stream:
                yield text


class DeepSeekBackend(LLMBackend):
    def __init__(self, model: str = "deepseek-chat", api_key: str | None = None, base_url: str | None = None):
        super().__init__(model, api_key, base_url)

    def _get_client(self):
        from openai import OpenAI
        return OpenAI(
            api_key=self._api_key or os.getenv("DEEPSEEK_API_KEY"),
            base_url=self._base_url or "https://api.deepseek.com",
            timeout=120,
        )

    def chat(self, system_prompt: str, user_prompt: str, temperature: float = 0.7, max_tokens: int = 16384) -> str:
        response = self._get_client().chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content

    def chat_stream(self, system_prompt: str, user_prompt: str, temperature: float = 0.7, max_tokens: int = 16384):
        response = self._get_client().chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        for chunk in response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

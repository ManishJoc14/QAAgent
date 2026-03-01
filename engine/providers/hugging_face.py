from __future__ import annotations

import asyncio
from typing import Any

from huggingface_hub import InferenceClient

from .base import BaseLLMProvider, LLMRequest, LLMResponse
from .registry import ProviderRegistry


class HuggingFaceProvider(BaseLLMProvider):
    """Hugging Face provider backed by huggingface_hub InferenceClient."""

    def __init__(
        self,
        model: str,
        api_key: str,
        timeout: int = 90,
        max_retries: int = 3,
        provider: str = "hf-inference",
        **kwargs: Any,
    ):
        super().__init__(model=model, **kwargs)
        if not api_key:
            raise ValueError("Missing required provider config: api_key")
        self.timeout = timeout
        self.max_retries = max_retries
        self.provider = provider
        self.api_key = api_key
        self.client = InferenceClient(
            provider=provider,
            api_key=api_key,
            timeout=timeout,
        )

    async def generate(self, request: LLMRequest) -> LLMResponse:
        messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]
        prompt = self._messages_to_prompt(request.messages)

        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                loop = asyncio.get_running_loop()
                completion: Any
                try:
                    completion = await loop.run_in_executor(
                        None,
                        lambda: self._text_generation_with_provider_fallback(
                            prompt=prompt,
                            temperature=request.temperature,
                            max_tokens=request.max_tokens,
                        ),
                    )
                    text = self._extract_text_generation_text(completion)
                except Exception as text_gen_error:
                    if not self._is_non_text_generation_model_error(text_gen_error):
                        raise

                    completion = await loop.run_in_executor(
                        None,
                        lambda: self.client.chat.completions.create(
                            model=self.model,
                            messages=messages,
                            temperature=request.temperature,
                            max_tokens=request.max_tokens,
                        ),
                    )
                    text = self._extract_text(completion)

                return LLMResponse(
                    content=text,
                    tool_calls=[],
                    raw=completion,
                )
            except Exception as err:
                last_error = err
                if attempt < self.max_retries:
                    await asyncio.sleep(0.5 * attempt)

        raise RuntimeError(
            f"Hugging Face provider failed after {self.max_retries} attempts: {last_error}"
        ) from last_error

    def _extract_text(self, completion: Any) -> str:
        choices = getattr(completion, "choices", None)
        if choices:
            message = getattr(choices[0], "message", None)
            if message is not None:
                content = getattr(message, "content", None)
                if content is not None:
                    return str(content)

        if isinstance(completion, dict):
            choices_dict = completion.get("choices")
            if isinstance(choices_dict, list) and choices_dict:
                message = choices_dict[0].get("message", {})
                content = message.get("content")
                if content is not None:
                    return str(content)

        return str(completion)

    def _extract_text_generation_text(self, completion: Any) -> str:
        if isinstance(completion, str):
            return completion

        generated_text = getattr(completion, "generated_text", None)
        if generated_text is not None:
            return str(generated_text)

        if isinstance(completion, dict) and "generated_text" in completion:
            return str(completion["generated_text"])

        return str(completion)

    def _is_non_chat_model_error(self, error: Exception) -> bool:
        text = str(error).lower()
        return "not a chat model" in text or "model_not_supported" in text

    def _is_non_text_generation_model_error(self, error: Exception) -> bool:
        text = str(error).lower()
        return (
            "not supported for task text-generation" in text
            or "doesn't support task 'text-generation'" in text
            or "does not support task 'text-generation'" in text
        )

    def _messages_to_prompt(self, messages: list) -> str:
        rendered = []
        for msg in messages:
            role = getattr(msg, "role", "user")
            content = getattr(msg, "content", "")
            rendered.append(f"{role.upper()}:\n{content}")
        rendered.append("ASSISTANT:")
        return "\n\n".join(rendered)

    def _text_generation_with_provider_fallback(
        self, *, prompt: str, temperature: float, max_tokens: int | None
    ) -> Any:
        try:
            return self.client.text_generation(
                model=self.model,
                prompt=prompt,
                temperature=temperature,
                max_new_tokens=max_tokens,
                return_full_text=False,
            )
        except Exception as err:
            # Some router providers (e.g. novita) can reject text-generation
            # for instruction models even when other providers support it.
            if self.provider != "auto" or not self._is_provider_task_mismatch_error(err):
                raise

            hf_client = InferenceClient(
                provider="hf-inference",
                api_key=self.api_key,
                timeout=self.timeout,
            )
            return hf_client.text_generation(
                model=self.model,
                prompt=prompt,
                temperature=temperature,
                max_new_tokens=max_tokens,
                return_full_text=False,
            )

    def _is_provider_task_mismatch_error(self, error: Exception) -> bool:
        text = str(error).lower()
        return "not supported for task text-generation" in text and "provider" in text


ProviderRegistry.register("huggingface", HuggingFaceProvider)

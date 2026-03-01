from __future__ import annotations

import asyncio
import json
from typing import Any

from mistralai import Mistral

from .base import BaseLLMProvider, LLMMessage, LLMRequest, LLMResponse, LLMToolCall
from .registry import ProviderRegistry


class MistralProvider(BaseLLMProvider):
    """Mistral provider with normalized message/tool-call contracts."""

    def __init__(
        self,
        model: str,
        api_key: str,
        timeout: int = 90,
        max_retries: int = 3,
        **kwargs: Any,
    ):
        super().__init__(model=model, **kwargs)
        if not api_key:
            raise ValueError("Missing required provider config: api_key")
        self.client = Mistral(api_key=api_key)
        self.timeout = timeout
        self.max_retries = max_retries

    async def generate(self, request: LLMRequest) -> LLMResponse:
        messages = self._convert_messages(request.messages)

        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                response = await asyncio.wait_for(
                    self.client.chat.complete_async(
                        model=self.model,
                        messages=messages,
                        tools=request.tools,
                        temperature=request.temperature,
                        max_tokens=request.max_tokens,
                    ),
                    timeout=self.timeout,
                )
                return self._normalize_response(response)
            except Exception as err:
                last_error = err
                if attempt < self.max_retries:
                    await asyncio.sleep(0.5 * attempt)

        raise RuntimeError(
            f"Mistral provider failed after {self.max_retries} attempts: {last_error}"
        ) from last_error

    def _convert_messages(self, messages: list[LLMMessage]) -> list[dict[str, Any]]:
        payload: list[dict[str, Any]] = []
        for msg in messages:
            entry: dict[str, Any] = {
                "role": msg.role,
                "content": msg.content,
            }
            if msg.name:
                entry["name"] = msg.name
            if msg.tool_call_id:
                entry["tool_call_id"] = msg.tool_call_id
            if msg.tool_calls:
                entry["tool_calls"] = msg.tool_calls
            payload.append(entry)
        return payload

    def _normalize_response(self, response: Any) -> LLMResponse:
        choice = response.choices[0]
        message = choice.message

        tool_calls: list[LLMToolCall] = []
        for tool_call in getattr(message, "tool_calls", []) or []:
            raw_args = tool_call.function.arguments
            args: dict[str, Any]
            if isinstance(raw_args, str):
                try:
                    args = json.loads(raw_args)
                except json.JSONDecodeError:
                    args = {"raw_arguments": raw_args}
            else:
                args = raw_args or {}

            tool_calls.append(
                LLMToolCall(
                    id=getattr(tool_call, "id", f"tool_{len(tool_calls)}"),
                    name=tool_call.function.name,
                    arguments=args,
                )
            )

        return LLMResponse(
            content=getattr(message, "content", None),
            tool_calls=tool_calls,
            raw=response,
        )


ProviderRegistry.register("mistral", MistralProvider)

from __future__ import annotations

import json

from engine.providers.base import BaseLLMProvider, LLMMessage, LLMRequest
from engine.tools.base import ToolExecutionResult
from engine.tools.collection import ToolCollection

from .parsing import extract_issues
from .types import QAResult


class QAOrchestrator:
    """Provider-agnostic orchestration loop for model + tools."""

    def __init__(
        self,
        provider: BaseLLMProvider,
        tools: ToolCollection,
        max_iterations: int = 20,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ):
        self.provider = provider
        self.tools = tools
        self.max_iterations = max_iterations
        self.temperature = temperature
        self.max_tokens = max_tokens

    async def execute(self, system_prompt: str, user_prompt: str) -> QAResult:
        result = QAResult()
        messages: list[LLMMessage] = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_prompt),
        ]

        for step in range(1, self.max_iterations + 1):
            response = await self.provider.generate(
                LLMRequest(
                    messages=messages,
                    tools=self.tools.list_schemas(),
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                )
            )

            assistant_content = response.content or ""
            assistant_tool_calls = [
                {
                    "id": c.id,
                    "type": "function",
                    "function": {
                        "name": c.name,
                        "arguments": json.dumps(c.arguments),
                    },
                }
                for c in response.tool_calls
            ]
            messages.append(
                LLMMessage(
                    role="assistant",
                    content=assistant_content,
                    tool_calls=assistant_tool_calls or None,
                )
            )
            result.raw_model_output = assistant_content

            result.trace.append(
                {
                    "step": step,
                    "assistant_content": assistant_content,
                    "tool_calls": [
                        {"id": c.id, "name": c.name, "arguments": c.arguments}
                        for c in response.tool_calls
                    ],
                }
            )

            if not response.tool_calls:
                break

            for call in response.tool_calls:
                tool_result = await self._safe_tool_execute(call.name, call.arguments)
                result.tool_outputs.append(tool_result)

                if tool_result.screenshot_base64:
                    result.screenshots.append(tool_result.screenshot_base64)

                messages.append(
                    LLMMessage(
                        role="tool",
                        name=call.name,
                        tool_call_id=call.id,
                        content=self._tool_result_to_message(tool_result),
                    )
                )

        parsed_issues = extract_issues(result.raw_model_output)
        if parsed_issues:
            result.issues = parsed_issues
        if not self._has_successful_evidence(result):
            result.issues = [self._build_tooling_blocker_issue(result.tool_outputs)]

        return result

    async def _safe_tool_execute(self, name: str, arguments: dict) -> ToolExecutionResult:
        try:
            return await self.tools.run(name=name, arguments=arguments)
        except Exception as exc:
            return ToolExecutionResult(success=False, error=str(exc) or repr(exc))

    def _tool_result_to_message(self, tool_result: ToolExecutionResult) -> str:
        payload = {
            "success": tool_result.success,
            "output": tool_result.output,
            "error": tool_result.error,
            "has_screenshot": bool(tool_result.screenshot_base64),
            "metadata": tool_result.metadata,
        }
        return json.dumps(payload)

    def _has_successful_evidence(self, result: QAResult) -> bool:
        if result.screenshots:
            return True
        for output in result.tool_outputs:
            if output.success and (output.output or output.screenshot_base64):
                return True
        return False

    def _build_tooling_blocker_issue(self, tool_outputs: list[ToolExecutionResult]) -> dict:
        errors = []
        for output in tool_outputs:
            if output.error:
                errors.append(output.error)
        unique_errors = []
        seen = set()
        for error in errors:
            if error not in seen:
                seen.add(error)
                unique_errors.append(error)

        steps = [
            "Run the QA task against the target URL.",
            "Observe repeated tool execution failures with no usable evidence.",
        ]
        if unique_errors:
            steps.extend([f"Tool error: {e}" for e in unique_errors[:3]])

        description = "Automated QA tooling failed before reliable site evidence was collected."
        if unique_errors:
            description += f" Errors observed: {' | '.join(unique_errors[:3])}"

        return {
            "id": "ISSUE-TOOLING-1",
            "severity": "P1",
            "title": "QA tooling failure blocks verified site assessment",
            "description": description,
            "steps_to_reproduce": steps,
            "category": "functional",
            "severity_justification": (
                "Without successful tool execution or screenshots, findings on the target site "
                "cannot be validated."
            ),
        }

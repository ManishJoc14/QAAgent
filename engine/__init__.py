from __future__ import annotations

# Project Imports
from engine.core.agent_loop import QAOrchestrator
from engine.core.types import QAResult, QATask
from engine.prompts import build_system_prompt, build_user_prompt
from engine.providers import ProviderFactory
from engine.tools import (
    AccessibilityAuditTool,
    ButtonClickCheckerTool,
    DeadLinkCheckerTool,
    FormValidatorTool,
    LoginFlowCheckerTool,
    NetworkTabAnalyzerTool,
    PlaywrightComputerTool,
    ResponsiveLayoutCheckerTool,
    SessionPersistenceCheckerTool,
    TouchTargetCheckerTool,
    ToolCollection,
)

try:
    from engine.tools.security import (
        SecurityContentAuditTool,
        SecurityHeadersAuditTool,
        SSLAuditTool,
    )
except ModuleNotFoundError:
    SecurityContentAuditTool = None  # type: ignore[assignment]
    SecurityHeadersAuditTool = None  # type: ignore[assignment]
    SSLAuditTool = None  # type: ignore[assignment]


class Engine:
    """Modular QA engine that can be called from any backend service."""

    def __init__(
        self,
        *,
        provider_name: str = "mistral",
        model: str = "mistral-large-latest",
        provider_kwargs: dict | None = None,
        max_iterations: int = 20,
        temperature: float = 0.2,
        max_tokens: int = 10000,
        locale: str = "en-US",
        device_profile: str = "iphone_14",
        network_profile: str = "wifi",
    ):
        provider_kwargs = provider_kwargs or {}

        self.provider = ProviderFactory.create(
            name=provider_name,
            model=model,
            **provider_kwargs,
        )

        self.max_iterations = max_iterations
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.locale = locale
        self.device_profile = device_profile
        self.network_profile = network_profile

    def _build_default_tools(self, target_url: str) -> ToolCollection:
        if PlaywrightComputerTool is None:
            raise RuntimeError(
                "Playwright is not installed. Install it to use browser-backed tools."
            )
        if (
            SSLAuditTool is None
            or SecurityHeadersAuditTool is None
            or SecurityContentAuditTool is None
        ):
            raise RuntimeError(
                "Security toolchain is unavailable because dependencies failed to load."
            )

        computer_tool = PlaywrightComputerTool(
            target_url=target_url,
            locale=self.locale,
            device_profile=self.device_profile,
            network_profile=self.network_profile,
        )

        return ToolCollection(
            [
                DeadLinkCheckerTool(fallback_url=target_url),
                FormValidatorTool(fallback_url=target_url),
                ButtonClickCheckerTool(fallback_url=target_url),
                LoginFlowCheckerTool(
                    computer_tool=computer_tool, fallback_url=target_url
                ),
                SessionPersistenceCheckerTool(
                    computer_tool=computer_tool, fallback_url=target_url
                ),
                NetworkTabAnalyzerTool(computer_tool=computer_tool),
                AccessibilityAuditTool(fallback_url=target_url),
                ResponsiveLayoutCheckerTool(fallback_url=target_url),
                TouchTargetCheckerTool(fallback_url=target_url),
                SSLAuditTool(fallback_url=target_url),
                SecurityHeadersAuditTool(fallback_url=target_url),
                SecurityContentAuditTool(computer_tool=computer_tool),
            ]
        )

    async def run_task(self, task: QATask) -> QAResult:
        # Build tools
        tools = self._build_default_tools(task.target_url)

        # System Prompt
        system_prompt = build_system_prompt(
            tools=[tools.get(n) for n in tools.list_names()],
            locale=self.locale,
            device_profile=self.device_profile,
            network_profile=self.network_profile,
        )

        # User Prompt
        user_prompt = build_user_prompt(
            target_url=task.target_url,
            task=task.task,
            context=task.context,
        )

        orchestrator = QAOrchestrator(
            provider=self.provider,
            tools=tools,
            max_iterations=self.max_iterations,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )

        try:
            return await orchestrator.execute(
                system_prompt=system_prompt, user_prompt=user_prompt
            )
        finally:
            await tools.close()


__all__ = ["Engine", "QATask", "QAResult"]

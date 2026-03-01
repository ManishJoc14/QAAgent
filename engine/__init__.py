from __future__ import annotations

# Project Imports
from engine.core.agent_loop import QAOrchestrator
from engine.core.types import QAResult, QATask
from engine.prompts import build_system_prompt, build_user_prompt
from engine.providers import ProviderFactory
from engine.tools import (
    PlaywrightComputerTool,
    ToolCollection,
)
from engine.tools.maps import AVAILABLE_QA_TOOLS

try:
    from engine.tools.console import ConsoleWatcherTool, NetworkMonitorTool
except ModuleNotFoundError:
    NetworkMonitorTool = None
    ConsoleWatcherTool = None

try:
    from engine.tools.functional import (
        LoginFlowCheckerTool,
        SessionPersistenceCheckerTool,
    )
except ModuleNotFoundError:
    DeadLinkCheckerTool = None
    FormValidatorTool = None
    ButtonClickCheckerTool = None
    LoginFlowCheckerTool = None
    SessionPersistenceCheckerTool = None

try:
    from engine.tools.metadata import SEOMetadataCheckerTool
except ModuleNotFoundError:
    SEOMetadataCheckerTool = None

try:
    from engine.tools.performance import PerformanceAuditTool
except ModuleNotFoundError:
    PerformanceAuditTool = None

try:
    from engine.tools.security import SecurityContentAuditTool
except ModuleNotFoundError:
    SecurityContentAuditTool = None  # type: ignore[assignment]


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
        selected_tools: list[str] = None,
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
        self.selected_tools = selected_tools

    async def _init_tools(
        self,
        computer_tool: PlaywrightComputerTool,
        target_url: str,
        selected_tools: list[str],
    ):
        tools = []

        for key in selected_tools:
            tool_cls = AVAILABLE_QA_TOOLS.get(key)
            if not tool_cls:
                continue

            # Determine if the tool needs computer_tool or fallback_url
            if issubclass(
                tool_cls,
                (
                    NetworkMonitorTool,
                    ConsoleWatcherTool,
                    SEOMetadataCheckerTool,
                    PerformanceAuditTool,
                    LoginFlowCheckerTool,
                    SessionPersistenceCheckerTool,
                    SecurityContentAuditTool,
                ),
            ):
                tools.append(tool_cls(computer_tool=computer_tool))
            else:
                tools.append(tool_cls(fallback_url=target_url))

        if not tools:
            raise RuntimeError("No tools initialized. Check your selection and tool availability.")

        return tools

    async def _build_default_tools(self, target_url: str) -> ToolCollection:
        if PlaywrightComputerTool is None:
            raise RuntimeError(
                "Playwright is not installed. Install it to use browser-backed tools."
            )

        computer_tool = PlaywrightComputerTool(
            target_url=target_url,
            locale=self.locale,
            device_profile=self.device_profile,
            network_profile=self.network_profile,
        )

        tools = await self._init_tools(
            computer_tool,
            target_url,
            selected_tools=self.selected_tools,
        )

        return ToolCollection(tools)

    async def run_task(self, task: QATask) -> QAResult:
        # Build tools
        tools = await self._build_default_tools(task.target_url)

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
            return await orchestrator.execute(system_prompt=system_prompt, user_prompt=user_prompt)
        finally:
            await tools.close()


__all__ = ["Engine", "QATask", "QAResult"]

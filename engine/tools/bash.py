from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
import sys

from .base import BaseTool, ToolExecutionResult


class BashTool(BaseTool):
    name = "bash"
    description = "Execute shell commands in the host OS shell."
    input_schema = {
        "type": "object",
        "properties": {
            "command": {"type": "string"},
            "restart": {"type": "boolean"},
        },
        "required": [],
    }
    timeout_seconds = 90

    def _normalize_command(self, command: str) -> str:
        # In some Windows environments the `playwright` shim isn't on PATH inside service processes.
        # Route through the active interpreter to keep behavior environment-independent.
        if os.name == "nt":
            trimmed = command.strip()
            if trimmed.startswith("playwright "):
                return f'& "{sys.executable}" -m {trimmed}'
        return command

    def _resolve_shell(self, command: str) -> tuple[str, str]:
        """Return (shell_path, mode), where mode is powershell/cmd/posix."""
        if os.name == "nt":
            # `&&` and `||` are cmd separators and may fail under legacy PowerShell parsing.
            if "&&" in command or "||" in command:
                cmd_path = shutil.which("cmd") or "cmd"
                return cmd_path, "cmd"
            pwsh_path = shutil.which("pwsh")
            if pwsh_path:
                return pwsh_path, "powershell"
            ps_path = shutil.which("powershell") or "powershell"
            return ps_path, "powershell"

        # Prefer user shell, then bash, then POSIX sh.
        env_shell = os.environ.get("SHELL")
        if env_shell and os.path.isabs(env_shell) and os.path.exists(env_shell):
            return env_shell, "posix"
        bash_path = shutil.which("bash")
        if bash_path:
            return bash_path, "posix"
        sh_path = shutil.which("sh") or "/bin/sh"
        return sh_path, "posix"

    def _build_command(self, command: str) -> tuple[list[str], str]:
        shell_path, mode = self._resolve_shell(command)
        if mode == "cmd":
            return [shell_path, "/d", "/s", "/c", command], shell_path
        if mode == "powershell":
            return [
                shell_path,
                "-NoLogo",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                command,
            ], shell_path
        return [shell_path, "-lc", command], shell_path

    async def execute(self, arguments: dict) -> ToolExecutionResult:
        # Backward-compatible with prior persistent-session contract.
        if bool(arguments.get("restart", False)):
            return ToolExecutionResult(success=True, output="bash session restarted")

        command = arguments.get("command")
        if not command:
            return ToolExecutionResult(
                success=False,
                error="Missing 'command'. Provide {'command': '<shell command>'}",
            )

        try:
            normalized_command = self._normalize_command(command)
            argv, shell_path = self._build_command(normalized_command)
            completed = await asyncio.to_thread(
                subprocess.run,
                argv,
                shell=False,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            return ToolExecutionResult(
                success=False,
                error=f"bash command timed out after {self.timeout_seconds}s",
            )
        except Exception as exc:
            return ToolExecutionResult(success=False, error=str(exc) or repr(exc))

        stderr = (completed.stderr or "").strip() or None
        stdout = (completed.stdout or "").strip() or None
        success = completed.returncode == 0

        return ToolExecutionResult(
            success=success,
            output=stdout,
            error=stderr if not success else None,
            metadata={
                "returncode": completed.returncode,
                "shell": shell_path,
                "stderr": stderr if (success and stderr) else None,
                "platform": sys.platform,
            },
        )

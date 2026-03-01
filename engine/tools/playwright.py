from __future__ import annotations

import asyncio
import base64
from typing import Any, Literal, get_args

from playwright.async_api import Browser, BrowserContext, Page, Playwright, async_playwright

from .base import BaseTool, ToolExecutionResult

Action = Literal[
    "key",
    "type",
    "mouse_move",
    "left_click",
    "left_click_drag",
    "right_click",
    "middle_click",
    "double_click",
    "triple_click",
    "screenshot",
    "cursor_position",
    "left_mouse_down",
    "left_mouse_up",
    "scroll",
    "hold_key",
    "wait",
]

ScrollDirection = Literal["up", "down", "left", "right"]

DEVICE_PROFILES: dict[str, dict[str, Any]] = {
    "iphone_se": {
        "viewport": {"width": 375, "height": 667},
        "user_agent": (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1"
        ),
        "device_scale_factor": 2,
        "is_mobile": True,
        "has_touch": True,
    },
    "iphone_14": {
        "viewport": {"width": 390, "height": 844},
        "user_agent": (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1"
        ),
        "device_scale_factor": 3,
        "is_mobile": True,
        "has_touch": True,
    },
    "pixel_7": {
        "viewport": {"width": 412, "height": 915},
        "user_agent": (
            "Mozilla/5.0 (Linux; Android 13; Pixel 7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36"
        ),
        "device_scale_factor": 2.625,
        "is_mobile": True,
        "has_touch": True,
    },
    "galaxy_s23": {
        "viewport": {"width": 360, "height": 780},
        "user_agent": (
            "Mozilla/5.0 (Linux; Android 13; SM-S911B) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36"
        ),
        "device_scale_factor": 3,
        "is_mobile": True,
        "has_touch": True,
    },
    "desktop": {
        "viewport": {"width": 1280, "height": 800},
        "user_agent": (
            "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        ),
        "device_scale_factor": 1,
        "is_mobile": False,
        "has_touch": False,
    },
    "desktop_1440": {
        "viewport": {"width": 1440, "height": 900},
        "user_agent": (
            "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        ),
        "device_scale_factor": 1,
        "is_mobile": False,
        "has_touch": False,
    },
}

NETWORK_PROFILES: dict[str, dict[str, Any]] = {
    "wifi": {},
    "4g": {
        "offline": False,
        "download_throughput": 9000 * 1024 // 8,
        "upload_throughput": 9000 * 1024 // 8,
        "latency": 80,
    },
    "fast_3g": {
        "offline": False,
        "download_throughput": 1600 * 1024 // 8,
        "upload_throughput": 750 * 1024 // 8,
        "latency": 150,
    },
    "slow_3g": {
        "offline": False,
        "download_throughput": 400 * 1024 // 8,
        "upload_throughput": 400 * 1024 // 8,
        "latency": 400,
    },
    "high_latency": {
        "offline": False,
        "download_throughput": 2000 * 1024 // 8,
        "upload_throughput": 2000 * 1024 // 8,
        "latency": 800,
    },
    "offline": {
        "offline": True,
        "download_throughput": 0,
        "upload_throughput": 0,
        "latency": 0,
    },
}

KEY_ALIAS: dict[str, str] = {
    "return": "Enter",
    "enter": "Enter",
    "esc": "Escape",
    "escape": "Escape",
    "backspace": "Backspace",
    "delete": "Delete",
    "ctrl": "Control",
    "command": "Meta",
    "cmd": "Meta",
    "meta": "Meta",
    "arrowup": "ArrowUp",
    "arrowdown": "ArrowDown",
    "arrowleft": "ArrowLeft",
    "arrowright": "ArrowRight",
}


class PlaywrightComputerTool(BaseTool):
    name = "computer"
    description = "Control a Playwright browser with coordinate-based actions."
    timeout_seconds = 90
    input_schema = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "key",
                    "type",
                    "mouse_move",
                    "left_click",
                    "left_click_drag",
                    "right_click",
                    "middle_click",
                    "double_click",
                    "triple_click",
                    "screenshot",
                    "cursor_position",
                    "left_mouse_down",
                    "left_mouse_up",
                    "scroll",
                    "hold_key",
                    "wait",
                ],
            },
            "text": {"type": "string"},
            "coordinate": {
                "type": "array",
                "items": {"type": "number"},
                "minItems": 2,
                "maxItems": 2,
            },
            "start_coordinate": {
                "type": "array",
                "items": {"type": "number"},
                "minItems": 2,
                "maxItems": 2,
            },
            "scroll_direction": {
                "type": "string",
                "enum": ["up", "down", "left", "right"],
            },
            "scroll_amount": {"type": "integer", "minimum": 0},
            "duration": {"type": "number", "minimum": 0, "maximum": 100},
        },
        "required": ["action"],
    }

    def __init__(
        self,
        target_url: str | None = None,
        device_profile: str = "iphone_14",
        network_profile: str = "wifi",
        locale: str = "en-US",
        screenshot_delay: float = 0.8,
    ):
        self._target_url = target_url
        self._device = DEVICE_PROFILES.get(device_profile, DEVICE_PROFILES["iphone_14"])
        self._network = NETWORK_PROFILES.get(network_profile, NETWORK_PROFILES["wifi"])
        self._locale = locale
        self._screenshot_delay = screenshot_delay

        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

        self._cursor_x = 0
        self._cursor_y = 0

        self._console_events: list[str] = []
        self._request_failures: list[str] = []
        self._startup_error: str | None = None

    @property
    def current_url(self) -> str | None:
        if self._page:
            return self._page.url
        return self._target_url

    def _translate_key(self, key_name: str) -> str:
        if "+" in key_name:
            parts = [p.strip() for p in key_name.split("+")]
            return "+".join(KEY_ALIAS.get(p.lower(), p) for p in parts)
        return KEY_ALIAS.get(key_name.lower(), key_name)

    async def ensure_ready(self) -> None:
        await self._ensure_browser()

    async def get_console_events(self, limit: int = 50) -> list[str]:
        await self._ensure_browser()
        return self._console_events[-limit:]

    async def get_request_failures(self, limit: int = 50) -> list[str]:
        await self._ensure_browser()
        return self._request_failures[-limit:]

    async def collect_page_snapshot(self) -> dict[str, Any]:
        await self._ensure_browser()
        assert self._page is not None
        metrics = await self._page.evaluate(
            """
            () => {
                const all = Array.from(document.querySelectorAll('*'));
                const links = Array.from(document.querySelectorAll('a'));
                const forms = Array.from(document.querySelectorAll('form'));
                const imgs = Array.from(document.querySelectorAll('img'));
                const smallTargets = all
                  .filter(el => ['A','BUTTON','INPUT','TEXTAREA','SELECT'].includes(el.tagName))
                  .filter(el => {
                    const r = el.getBoundingClientRect();
                    return r.width > 0 && r.height > 0 && (r.width < 44 || r.height < 44);
                  }).length;
                const unlabeledInputs = Array.from(document.querySelectorAll('input,textarea,select')).filter(el => {
                  const id = el.getAttribute('id');
                  if (id && document.querySelector(`label[for="${id}"]`)) return false;
                  if (el.getAttribute('aria-label') || el.getAttribute('aria-labelledby')) return false;
                  return true;
                }).length;
                const missingAlt = imgs.filter(i => !i.getAttribute('alt')).length;
                const insecureForms = forms.filter(f => {
                  const action = (f.getAttribute('action') || '').trim();
                  return action.startsWith('http://');
                }).length;
                const inlineScripts = document.querySelectorAll('script:not([src])').length;
                const mixedContent = Array.from(document.querySelectorAll('img,script,link,iframe'))
                  .map(el => el.getAttribute('src') || el.getAttribute('href') || '')
                  .filter(v => typeof v === 'string' && v.startsWith('http://')).length;

                return {
                  title: document.title || '',
                  total_elements: all.length,
                  links: links.length,
                  forms: forms.length,
                  images: imgs.length,
                  missing_alt_images: missingAlt,
                  small_touch_targets: smallTargets,
                  unlabeled_form_controls: unlabeledInputs,
                  insecure_form_actions: insecureForms,
                  inline_script_blocks: inlineScripts,
                  mixed_content_references: mixedContent,
                };
            }
            """
        )
        return metrics

    async def collect_perf_metrics(self) -> dict[str, Any]:
        await self._ensure_browser()
        assert self._page is not None
        return await self._page.evaluate(
            """
            () => {
                const out = {};
                const nav = performance.getEntriesByType('navigation');
                if (nav.length > 0) {
                    const n = nav[0];
                    out.ttfb_ms = n.responseStart - n.requestStart;
                    out.dom_content_loaded_ms = n.domContentLoadedEventEnd - n.startTime;
                    out.load_event_ms = n.loadEventEnd - n.startTime;
                }
                const fcp = performance.getEntriesByName('first-contentful-paint');
                if (fcp.length > 0) out.fcp_ms = fcp[0].startTime;
                const lcp = performance.getEntriesByType('largest-contentful-paint');
                if (lcp.length > 0) out.lcp_ms = lcp[lcp.length - 1].startTime;
                const cls = performance.getEntriesByType('layout-shift');
                if (cls.length > 0) {
                    let score = 0;
                    for (const e of cls) {
                        if (!e.hadRecentInput) score += e.value;
                    }
                    out.cls = score;
                }
                const resources = performance.getEntriesByType('resource');
                out.resource_count = resources.length;
                return out;
            }
            """
        )

    async def _ensure_browser(self) -> None:
        if self._startup_error:
            raise RuntimeError(self._startup_error)
        if self._page is not None:
            return

        try:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
            )
        except NotImplementedError as exc:
            self._startup_error = (
                "Playwright browser startup failed: current event loop does not support subprocesses. "
                "Ensure WindowsProactorEventLoopPolicy is configured at process startup."
            )
            raise RuntimeError(self._startup_error) from exc
        except Exception as exc:
            self._startup_error = f"Playwright browser startup failed: {str(exc) or repr(exc)}"
            raise RuntimeError(self._startup_error) from exc

        context_opts = {
            "viewport": self._device["viewport"],
            "user_agent": self._device["user_agent"],
            "device_scale_factor": self._device["device_scale_factor"],
            "is_mobile": self._device["is_mobile"],
            "has_touch": self._device["has_touch"],
            "locale": self._locale,
        }

        self._context = await self._browser.new_context(**context_opts)
        self._page = await self._context.new_page()

        self._page.on(
            "console", lambda msg: self._console_events.append(f"[{msg.type}] {msg.text}")
        )
        self._page.on("pageerror", lambda exc: self._console_events.append(f"[pageerror] {exc}"))
        self._page.on(
            "requestfailed",
            lambda req: self._request_failures.append(self._format_request_failure(req)),
        )

        if self._network and self._network.get("latency") is not None:
            try:
                assert self._context is not None
                cdp = await self._context.new_cdp_session(self._page)
                await cdp.send(
                    "Network.emulateNetworkConditions",
                    {
                        "offline": self._network.get("offline", False),
                        "downloadThroughput": self._network.get("download_throughput", -1),
                        "uploadThroughput": self._network.get("upload_throughput", -1),
                        "latency": self._network.get("latency", 0),
                    },
                )
            except Exception:
                pass

        if self._target_url:
            url = self._target_url
            if not url.startswith(("http://", "https://")):
                url = f"https://{url}"
            await self._safe_goto(url)

    async def _safe_goto(self, url: str) -> None:
        assert self._page is not None
        try:
            await self._page.goto(url, wait_until="domcontentloaded", timeout=30000)
        except Exception:
            await self._page.goto(url, wait_until="load", timeout=45000)

    def _format_request_failure(self, request: Any) -> str:
        failure = getattr(request, "failure", None)
        if isinstance(failure, str):
            reason = failure
        elif failure is None:
            reason = "failed"
        else:
            reason = getattr(failure, "error_text", None) or str(failure)
        return f"{request.method} {request.url} :: {reason}"

    async def _take_screenshot(self) -> ToolExecutionResult:
        assert self._page is not None
        png_bytes = await self._page.screenshot(type="png")
        image_b64 = base64.b64encode(png_bytes).decode("utf-8")
        return ToolExecutionResult(
            success=True,
            screenshot_base64=image_b64,
            metadata={"url": self.current_url},
        )

    def _validate_coordinate(self, coordinate: Any, required: bool = True) -> tuple[int, int]:
        if coordinate is None:
            if required:
                raise ValueError("coordinate is required")
            return self._cursor_x, self._cursor_y

        if not isinstance(coordinate, (list, tuple)) or len(coordinate) != 2:
            raise ValueError("coordinate must be [x, y]")

        width = self._device["viewport"]["width"]
        height = self._device["viewport"]["height"]

        x = max(0, min(int(coordinate[0]), width - 1))
        y = max(0, min(int(coordinate[1]), height - 1))
        return x, y

    async def execute(self, arguments: dict) -> ToolExecutionResult:
        action = arguments.get("action")
        if not action:
            return ToolExecutionResult(success=False, error="Missing 'action'")

        try:
            await self._ensure_browser()
            assert self._page is not None
            result = await self._dispatch_action(
                action=action,
                text=arguments.get("text"),
                coordinate=arguments.get("coordinate"),
                start_coordinate=arguments.get("start_coordinate"),
                scroll_direction=arguments.get("scroll_direction"),
                scroll_amount=arguments.get("scroll_amount"),
                duration=arguments.get("duration"),
            )
            if not result.metadata:
                result.metadata = {}
            result.metadata.setdefault("url", self.current_url)
            result.metadata.setdefault("console_event_count", len(self._console_events))
            result.metadata.setdefault("request_failure_count", len(self._request_failures))
            return result
        except Exception as e:
            error_message = str(e) or repr(e)
            error_result = ToolExecutionResult(
                success=False,
                error=error_message,
                metadata={"url": self.current_url},
            )
            try:
                shot = await self._take_screenshot()
                error_result.screenshot_base64 = shot.screenshot_base64
            except Exception:
                pass
            return error_result

    async def _dispatch_action(
        self,
        *,
        action: Action,
        text: str | None,
        coordinate: Any,
        start_coordinate: Any,
        scroll_direction: str | None,
        scroll_amount: int | None,
        duration: float | None,
    ) -> ToolExecutionResult:
        assert self._page is not None

        if action == "screenshot":
            return await self._take_screenshot()

        if action == "cursor_position":
            return ToolExecutionResult(output=f"X={self._cursor_x},Y={self._cursor_y}")

        if action in ("left_click", "right_click", "middle_click", "double_click", "triple_click"):
            x, y = self._validate_coordinate(coordinate, required=False)
            if coordinate is not None:
                await self._page.mouse.move(x, y)
                self._cursor_x, self._cursor_y = x, y

            button = "left"
            if action == "right_click":
                button = "right"
            elif action == "middle_click":
                button = "middle"

            click_count = 1
            if action == "double_click":
                click_count = 2
            elif action == "triple_click":
                click_count = 3

            await self._page.mouse.click(
                self._cursor_x,
                self._cursor_y,
                button=button,
                click_count=click_count,
                timeout=15000,
            )
            await asyncio.sleep(self._screenshot_delay)
            return await self._take_screenshot()

        if action == "mouse_move":
            x, y = self._validate_coordinate(coordinate)
            await self._page.mouse.move(x, y)
            self._cursor_x, self._cursor_y = x, y
            await asyncio.sleep(self._screenshot_delay)
            return await self._take_screenshot()

        if action == "left_click_drag":
            sx, sy = self._validate_coordinate(start_coordinate)
            ex, ey = self._validate_coordinate(coordinate)
            await self._page.mouse.move(sx, sy)
            await self._page.mouse.down()
            await self._page.mouse.move(ex, ey, steps=10)
            await self._page.mouse.up()
            self._cursor_x, self._cursor_y = ex, ey
            await asyncio.sleep(self._screenshot_delay)
            return await self._take_screenshot()

        if action == "left_mouse_down":
            await self._page.mouse.down()
            await asyncio.sleep(self._screenshot_delay)
            return await self._take_screenshot()

        if action == "left_mouse_up":
            await self._page.mouse.up()
            await asyncio.sleep(self._screenshot_delay)
            return await self._take_screenshot()

        if action == "type":
            if not text:
                raise ValueError("type requires 'text'")
            await self._page.keyboard.type(text, delay=12)
            await asyncio.sleep(self._screenshot_delay)
            return await self._take_screenshot()

        if action == "key":
            if not text:
                raise ValueError("key requires 'text'")
            keys = text.split(" ") if "+" not in text and " " in text else [text]
            for key in keys:
                k = self._translate_key(key.strip())
                if k:
                    await self._page.keyboard.press(k)
            await asyncio.sleep(self._screenshot_delay)
            return await self._take_screenshot()

        if action == "scroll":
            if scroll_direction not in get_args(ScrollDirection):
                raise ValueError("scroll_direction must be one of: up, down, left, right")
            if not isinstance(scroll_amount, int) or scroll_amount < 0:
                raise ValueError("scroll_amount must be a non-negative integer")

            if coordinate is not None:
                x, y = self._validate_coordinate(coordinate)
                await self._page.mouse.move(x, y)
                self._cursor_x, self._cursor_y = x, y

            delta = scroll_amount * 100
            if scroll_direction == "up":
                await self._page.mouse.wheel(0, -delta)
            elif scroll_direction == "down":
                await self._page.mouse.wheel(0, delta)
            elif scroll_direction == "left":
                await self._page.mouse.wheel(-delta, 0)
            elif scroll_direction == "right":
                await self._page.mouse.wheel(delta, 0)

            await asyncio.sleep(self._screenshot_delay)
            return await self._take_screenshot()

        if action == "hold_key":
            if not text:
                raise ValueError("hold_key requires 'text'")
            if duration is None or duration < 0 or duration > 100:
                raise ValueError("duration must be between 0 and 100")
            key = self._translate_key(text)
            await self._page.keyboard.down(key)
            await asyncio.sleep(duration)
            await self._page.keyboard.up(key)
            return await self._take_screenshot()

        if action == "wait":
            if duration is None or duration < 0 or duration > 100:
                raise ValueError("duration must be between 0 and 100")
            await asyncio.sleep(duration)
            return await self._take_screenshot()

        raise ValueError(f"Invalid action: {action}")

    async def close(self) -> None:
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        self._context = None
        self._browser = None
        self._playwright = None
        self._page = None
        self._console_events = []
        self._request_failures = []

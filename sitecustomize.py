from __future__ import annotations

import asyncio
import sys

# Ensure Windows uses a subprocess-capable event loop before frameworks initialize asyncio.
if sys.platform == "win32":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except Exception:
        pass

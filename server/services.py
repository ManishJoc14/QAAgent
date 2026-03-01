import asyncio

# Projects
from engine import Engine, QATask
from server.config import get_settings
from server.schemas import QARequest
from server.utils import save_screenshot_base64

settings = get_settings()


def run_qa_task_sync(task: QATask, request: QARequest):
    api_key = settings.provider_api_key
    if not api_key:
        raise ValueError("Provider API key not set. Set PROVIDER_API_KEY in your environment.")

    async def _runner():
        qa_engine = Engine(
            provider_name=settings.provider_name,
            model=settings.provider_model,
            provider_kwargs={"api_key": api_key},
            locale="en-US",
            device_profile=request.device_profile,
            network_profile=request.network_profile,
        )
        return await qa_engine.run_task(task)

    return asyncio.run(_runner())


def serialize_tool_outputs_with_urls(tool_outputs, base_url: str):
    base = base_url.rstrip("/")
    serialized = []
    screenshot_urls = []
    for t in tool_outputs:
        item = dict(t.__dict__)
        image_b64 = item.get("screenshot_base64")
        if image_b64:
            screenshot_path = save_screenshot_base64(image_b64)
            screenshot_url = f"{base}{screenshot_path}"
            metadata = dict(item.get("metadata") or {})
            metadata["screenshot_url"] = screenshot_url
            item["metadata"] = metadata
            item["screenshot_base64"] = None
            screenshot_urls.append(screenshot_url)
        serialized.append(item)
    return serialized, screenshot_urls

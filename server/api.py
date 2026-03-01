import asyncio

from fastapi import APIRouter, HTTPException, Request

# Project Imports
from engine import QATask
from server.constants import DEFAULT_TASK
from server.schemas import QARequest, QAResponse
from server.services import run_qa_task_sync, serialize_tool_outputs_with_urls
from server.utils import normalize_url

router = APIRouter(prefix="/qa")


@router.post("", response_model=QAResponse)
async def qa_endpoint(request: QARequest, _http_request: Request):
    target_url = normalize_url(request.url)
    task = QATask(target_url=target_url, task=DEFAULT_TASK, context=request.context)

    try:
        result = await asyncio.to_thread(run_qa_task_sync, task, request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"QA run failed: {exc}") from exc

    tool_outputs, screenshot_urls = serialize_tool_outputs_with_urls(
        result.tool_outputs, str(_http_request.base_url)
    )
    return {
        "url": target_url,
        "issues": result.issues,
        "tool_outputs": tool_outputs,
        "screenshots": screenshot_urls,
        "raw_model_output": result.raw_model_output,
        "trace": result.trace,
    }

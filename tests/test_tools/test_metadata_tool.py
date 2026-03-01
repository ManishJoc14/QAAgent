import json

import pytest

from engine.tools.metadata import SEOMetadataCheckerTool
from engine.tools.playwright import PlaywrightComputerTool

pytestmark = pytest.mark.asyncio


@pytest.mark.parametrize("url", ["https://example.com"])
async def test_seo_metadata_tool(url):
    computer = PlaywrightComputerTool(target_url=url)
    await computer.ensure_ready()  # Prepare browser context

    seo_tool = SEOMetadataCheckerTool(computer)
    result = await seo_tool.execute({})

    # Ensure the tool reports success
    assert result is not None
    assert isinstance(result.success, bool)
    assert result.success is True, f"SEO tool failed with error: {result.error}"

    # Parse output JSON
    data = json.loads(result.output)
    assert "url" in data
    assert data["url"] == computer.current_url
    assert "title" in data
    assert "headings" in data
    assert "findings" in data

    # Optional: check that findings is a non-empty list
    assert isinstance(data["findings"], list)
    assert len(data["findings"]) > 0

    # Clean up browser after test
    await computer.close()

"""Search Healthcare Jobs: calls the `search_healthcare_jobs` tool of the CareJobs.Now remote MCP server."""

from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from carejobs_client import build_arguments, call_tool

# Dify parameter name -> type (or ("integer", min, max)). Mirrors the YAML next to this file.
ARGUMENTS: dict[str, Any] = {
    "query": "string",
    "kind": "string",
    "employer": "string",
    "state": "string",
    "remote": "boolean",
    "min_hourly_usd": ("integer", 1, 1000),
    "sort": "string",
    "limit": ("integer", 1, 25),
}


class SearchHealthcareJobsTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        result = call_tool("search_healthcare_jobs", build_arguments(tool_parameters, ARGUMENTS))
        yield self.create_text_message(result.text)
        if result.data is not None:
            yield self.create_json_message(result.data)

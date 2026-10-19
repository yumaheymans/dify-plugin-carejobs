"""Tests for the CareJobs.Now Dify plugin. Standard library only (unittest).

Run from the plugin root with the Dify SDK installed:

    python -m unittest discover -s tests -v

The live tests call the real CareJobs.Now API and are skipped unless CAREJOBS_LIVE=1.
"""

from __future__ import annotations

import importlib
import json
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

# The SDK monkey-patches ssl with gevent when it is imported, so it must come before requests
# (the plugin runtime imports it first too, from main.py).
import dify_plugin  # noqa: F401  (isort: skip)
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import carejobs_client  # noqa: E402
from carejobs_client import CareJobsError, build_arguments, call_tool  # noqa: E402

TOOL_NAMES = [
    "search_healthcare_jobs",
    "get_healthcare_pay",
    "get_healthcare_job_market",
    "get_healthcare_jobs_by_state",
    "list_healthcare_employers",
    "get_healthcare_employer",
]


class FakeResponse:
    def __init__(self, body: bytes, status: int = 200, content_type: str = "application/json"):
        self._body = body
        self.status_code = status
        self.headers = {"Content-Type": content_type}

    def iter_content(self, chunk_size: int = 65536):
        for start in range(0, len(self._body), chunk_size):
            yield self._body[start : start + chunk_size]

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def rpc_result(text: str, data: dict | None = None, is_error: bool = False) -> bytes:
    result: dict = {"content": [{"type": "text", "text": text}]}
    if data is not None:
        result["structuredContent"] = data
    if is_error:
        result["isError"] = True
    return json.dumps({"jsonrpc": "2.0", "id": 1, "result": result}).encode()


class BuildArgumentsTest(unittest.TestCase):
    SPEC = {
        "query": "string",
        "remote": "boolean",
        "limit": ("integer", 1, 25),
    }

    def test_drops_empty_values_and_false_flags(self):
        out = build_arguments({"query": "  ", "remote": False, "limit": None}, self.SPEC)
        self.assertEqual(out, {})

    def test_keeps_and_trims_values(self):
        out = build_arguments({"query": " ICU ", "remote": True, "limit": 5}, self.SPEC)
        self.assertEqual(out, {"query": "ICU", "remote": True, "limit": 5})

    def test_boolean_strings(self):
        self.assertEqual(build_arguments({"remote": "true"}, self.SPEC), {"remote": True})
        self.assertEqual(build_arguments({"remote": "false"}, self.SPEC), {})

    def test_integer_is_coerced_and_clamped(self):
        self.assertEqual(build_arguments({"limit": 7.0}, self.SPEC), {"limit": 7})
        self.assertEqual(build_arguments({"limit": "12"}, self.SPEC), {"limit": 12})
        self.assertEqual(build_arguments({"limit": 999}, self.SPEC), {"limit": 25})
        self.assertEqual(build_arguments({"limit": 0}, self.SPEC), {"limit": 1})

    def test_bad_integer_is_rejected(self):
        with self.assertRaises(CareJobsError):
            build_arguments({"limit": "many"}, self.SPEC)

    def test_overlong_text_is_rejected(self):
        with self.assertRaises(CareJobsError):
            build_arguments({"query": "x" * 201}, self.SPEC)

    def test_unknown_parameters_are_ignored(self):
        self.assertEqual(build_arguments({"other": "x"}, self.SPEC), {})


class CallToolTest(unittest.TestCase):
    def post(self, response=None, side_effect=None):
        return mock.patch.object(
            carejobs_client.requests, "post", return_value=response, side_effect=side_effect
        )

    def test_success_returns_text_and_data(self):
        with self.post(FakeResponse(rpc_result("3 jobs", {"total": 3}))) as post:
            result = call_tool("search_healthcare_jobs", {"kind": "nurses"})
        self.assertEqual(result.text, "3 jobs")
        self.assertEqual(result.data, {"total": 3})
        args, kwargs = post.call_args
        self.assertEqual(args[0], "https://carejobs.now/api/mcp")
        self.assertEqual(
            kwargs["json"]["params"],
            {"name": "search_healthcare_jobs", "arguments": {"kind": "nurses"}},
        )
        self.assertEqual(kwargs["json"]["method"], "tools/call")
        self.assertFalse(kwargs["allow_redirects"])
        self.assertEqual(kwargs["timeout"], (5, 30))
        self.assertIn("text/event-stream", kwargs["headers"]["Accept"])

    def test_text_only_answer_has_no_data(self):
        with self.post(FakeResponse(rpc_result("ok"))):
            self.assertIsNone(call_tool("get_healthcare_pay", {}).data)

    def test_event_stream_answer(self):
        sse = b"event: message\ndata: " + rpc_result("streamed", {"a": 1}) + b"\n\n"
        with self.post(FakeResponse(sse, content_type="text/event-stream")):
            result = call_tool("get_healthcare_job_market", {})
        self.assertEqual((result.text, result.data), ("streamed", {"a": 1}))

    def test_tool_error_becomes_exception_with_service_message(self):
        with self.post(FakeResponse(rpc_result("Unknown employer 'x'.", is_error=True))):
            with self.assertRaisesRegex(CareJobsError, "Unknown employer"):
                call_tool("get_healthcare_employer", {"employer": "x"})

    def test_json_rpc_error(self):
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "error": {"code": -32602, "message": "Unknown tool: x"}})
        with self.post(FakeResponse(body.encode())):
            with self.assertRaisesRegex(CareJobsError, "Unknown tool"):
                call_tool("x", {})

    def test_http_error(self):
        with self.post(FakeResponse(b"", status=503)):
            with self.assertRaisesRegex(CareJobsError, "HTTP 503"):
                call_tool("get_healthcare_pay", {})

    def test_network_error_does_not_leak_details(self):
        with self.post(side_effect=requests.ConnectionError("secret-host-detail")):
            with self.assertRaises(CareJobsError) as ctx:
                call_tool("get_healthcare_pay", {})
        self.assertNotIn("secret-host-detail", str(ctx.exception))

    def test_unreadable_body(self):
        with self.post(FakeResponse(b"<html>not json</html>")):
            with self.assertRaises(CareJobsError):
                call_tool("get_healthcare_pay", {})

    def test_oversized_answer_is_refused(self):
        big = FakeResponse(b"x" * (carejobs_client.MAX_RESPONSE_BYTES + 1))
        with self.post(big):
            with self.assertRaisesRegex(CareJobsError, "large"):
                call_tool("get_healthcare_pay", {})


def load_registration():
    """Load the plugin the way the Dify runtime does (manifest, provider, every tool class)."""
    from dify_plugin import DifyPluginEnv
    from dify_plugin.core.plugin_registration import PluginRegistration

    previous = Path.cwd()
    os.chdir(ROOT)
    try:
        return PluginRegistration(DifyPluginEnv())
    finally:
        os.chdir(previous)


class RegistrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registration = load_registration()

    def test_provider_and_all_tools_load(self):
        self.assertIsNotNone(self.registration.get_tool_provider_cls("carejobs"))
        for name in TOOL_NAMES:
            with self.subTest(tool=name):
                self.assertIsNotNone(self.registration.get_tool_cls("carejobs", name))

    def test_no_credentials_are_required(self):
        provider, _, _ = self.registration.tools_mapping["carejobs"]
        self.assertFalse(provider.credentials_schema)

    def test_yaml_parameters_match_argument_specs(self):
        """Every YAML parameter must be forwarded by the tool, and the reverse."""
        provider, _, tools = self.registration.tools_mapping["carejobs"]
        for name, (configuration, tool_cls) in tools.items():
            module = importlib.import_module(tool_cls.__module__)
            declared = {p.name for p in configuration.parameters}
            self.assertEqual(declared, set(module.ARGUMENTS), name)

    def test_required_parameters_are_declared(self):
        _, _, tools = self.registration.tools_mapping["carejobs"]
        required = {
            name: sorted(p.name for p in config.parameters if p.required)
            for name, (config, _cls) in tools.items()
        }
        self.assertEqual(required["get_healthcare_employer"], ["employer"])
        self.assertTrue(all(not v for k, v in required.items() if k != "get_healthcare_employer"))


class InvokeWithMockedApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registration = load_registration()

    def invoke(self, tool: str, parameters: dict, body: bytes):
        tool_cls = self.registration.get_tool_cls("carejobs", tool)
        instance = tool_cls.from_credentials({})
        with mock.patch.object(
            carejobs_client.requests, "post", return_value=FakeResponse(body)
        ) as post:
            messages = list(instance.invoke(parameters))
        return messages, post.call_args.kwargs["json"]["params"]

    def test_search_sends_filters_and_yields_text_and_json(self):
        messages, params = self.invoke(
            "search_healthcare_jobs",
            {"kind": "nurses", "state": "TX", "remote": False, "limit": 3.0, "query": ""},
            rpc_result("summary", {"total": 1, "jobs": []}),
        )
        self.assertEqual(params["arguments"], {"kind": "nurses", "state": "TX", "limit": 3})
        self.assertEqual([m.type.value for m in messages], ["text", "json"])
        self.assertEqual(messages[0].message.text, "summary")
        self.assertEqual(messages[1].message.json_object, {"total": 1, "jobs": []})

    def test_each_tool_calls_its_own_mcp_tool(self):
        sample = {
            "search_healthcare_jobs": {},
            "get_healthcare_pay": {"kind": "nurses"},
            "get_healthcare_job_market": {},
            "get_healthcare_jobs_by_state": {"state": "OH", "kind": "nursing-assistants"},
            "list_healthcare_employers": {"query": "Kaiser"},
            "get_healthcare_employer": {"employer": "kaiser-permanente"},
        }
        for tool, parameters in sample.items():
            with self.subTest(tool=tool):
                _, params = self.invoke(tool, parameters, rpc_result("ok", {"k": 1}))
                self.assertEqual(params["name"], tool)

    def test_service_error_surfaces_as_exception(self):
        with self.assertRaises(CareJobsError):
            self.invoke(
                "get_healthcare_employer",
                {"employer": "zzz"},
                rpc_result("Unknown employer 'zzz'.", is_error=True),
            )


@unittest.skipUnless(os.environ.get("CAREJOBS_LIVE") == "1", "set CAREJOBS_LIVE=1 to call the live API")
class LiveApiTest(unittest.TestCase):
    """Calls the real CareJobs.Now API through each tool's `invoke`."""

    @classmethod
    def setUpClass(cls):
        cls.registration = load_registration()

    def run_tool(self, tool: str, parameters: dict):
        instance = self.registration.get_tool_cls("carejobs", tool).from_credentials({})
        messages = list(instance.invoke(parameters))
        kinds = [m.type.value for m in messages]
        self.assertEqual(kinds, ["text", "json"], tool)
        text, data = messages[0].message.text, messages[1].message.json_object
        self.assertTrue(text.strip(), tool)
        self.assertIsInstance(data, dict, tool)
        return text, data

    def test_search_healthcare_jobs(self):
        text, data = self.run_tool(
            "search_healthcare_jobs", {"kind": "nurses", "state": "TX", "limit": 3}
        )
        self.assertLessEqual(len(data["jobs"]), 3)
        self.assertTrue(data["jobs"][0]["url"].startswith("https://carejobs.now/jobs/"))

    def test_get_healthcare_pay(self):
        text, data = self.run_tool("get_healthcare_pay", {"kind": "nurses"})
        self.assertGreater(data["open_jobs"], 0)
        self.assertIn("median", text)

    def test_get_healthcare_job_market(self):
        _, data = self.run_tool("get_healthcare_job_market", {})
        self.assertGreater(data["open_jobs"], 0)

    def test_get_healthcare_jobs_by_state(self):
        _, data = self.run_tool(
            "get_healthcare_jobs_by_state",
            {"state": "OH", "kind": "nursing-assistants", "limit": 2},
        )
        self.assertGreater(data["open_jobs"], 0)

    def test_list_healthcare_employers(self):
        _, data = self.run_tool("list_healthcare_employers", {"query": "Kaiser", "limit": 2})
        self.assertGreaterEqual(data["total"], 1)

    def test_get_healthcare_employer(self):
        _, data = self.run_tool("get_healthcare_employer", {"employer": "kaiser-permanente"})
        self.assertEqual(data["slug"], "kaiser-permanente")

    def test_unknown_employer_raises(self):
        instance = self.registration.get_tool_cls("carejobs", "get_healthcare_employer").from_credentials({})
        with self.assertRaisesRegex(CareJobsError, "Unknown employer"):
            list(instance.invoke({"employer": "zzz-no-such-employer"}))

    def test_declared_parameters_match_the_live_tool_schemas(self):
        """The YAML parameter names must still be the arguments the live server accepts."""
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        response = requests.post(
            carejobs_client.ENDPOINT,
            data=body,
            headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream"},
            timeout=30,
        )
        live = {t["name"]: set(t["inputSchema"].get("properties", {})) for t in response.json()["result"]["tools"]}
        _, _, tools = self.registration.tools_mapping["carejobs"]
        for name, (configuration, _cls) in tools.items():
            self.assertEqual({p.name for p in configuration.parameters}, live[name], name)


if __name__ == "__main__":
    unittest.main()

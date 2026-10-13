"""The MCP server: protocol smoke on the shared scaffold, and `write_catalog` offline against the sample package."""
import json
from pathlib import Path

import sdchealthdcatap.mcp_server as srv
from sdchealthdcatap import cli

SAMPLE = Path(__file__).resolve().parents[1] / "samples" / "nhanes-participant"
CT = "xy8upneajsb8vdcmnve01g6g"


def call(name, arguments):
    resp = srv._handle_request({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": name, "arguments": arguments}})
    result = resp["result"]
    return result, result["content"][0]["text"]


def test_initialize_and_tools_list():
    srv._CACHE.clear()
    r = srv._handle_request({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-11-25"}})["result"]
    assert r["serverInfo"]["name"] == "sdchealthdcatap" and r["protocolVersion"] == "2025-11-25"
    tools = srv._handle_request({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})["result"]["tools"]
    assert [t["name"] for t in tools] == ["write_catalog"]


def test_write_from_the_sample_package():
    srv._CACHE.clear()
    result, text = call("write_catalog", {**{"directories": [str(SAMPLE)]}, "date": "2026-10-13"})
    assert not result.get("isError"), text
    out = json.loads(text)
    assert out["document"]
    assert out['datasets'] == 1 and out['models'][0]['ct_id'] == CT
    assert out['format'] == 'turtle' and isinstance(out['document'], str) and out['triples'] > 0


def test_bad_arguments_are_tool_errors():
    srv._CACHE.clear()
    result, text = call("write_catalog", {})
    assert result.get("isError") is True
    result, text = call("write_catalog", {**{"directories": [str(SAMPLE)]}, "date": "yesterday"})
    assert result.get("isError") is True and "YYYY-MM-DD" in text


def test_json_ld_format():
    srv._CACHE.clear()
    result, text = call("write_catalog", {**{"directories": [str(SAMPLE)]}, "format": "json-ld"})
    assert not result.get("isError"), text
    out = json.loads(text)
    assert out["format"] == "json-ld" and isinstance(out["document"], (list, dict))


def test_the_cli_mcp_subcommand_runs_the_server(monkeypatch):
    seen = {}
    monkeypatch.setattr(srv, "main", lambda argv=None: seen.setdefault("argv", argv))
    assert cli.main(["mcp", "--host", "https://h.example"]) == 0 and seen["argv"] == ["--host", "https://h.example"]

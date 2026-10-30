"""Tests for the tool interface and the tools that follow it."""

from assistant import chat
from assistant.tools.base import Evidence, GraphTool, Tool, ToolInfo


def test_every_registered_tool_follows_the_interface():
    for tool in chat.TOOLS:
        assert isinstance(tool, ToolInfo)
        assert isinstance(tool, (Tool, GraphTool))
        assert tool.name and tool.description and tool.source_label


def test_a_tool_with_its_own_steps_starts_where_the_router_sends_it():
    diagram = chat.flow_diagram()
    for tool in chat.TOOLS:
        if isinstance(tool, GraphTool):
            assert f'"router" -> "{tool.name}"' not in diagram
    assert '"router" -> "write_sql" [style=dashed];' in diagram


def test_tool_names_are_unique():
    names = [tool.name for tool in chat.TOOLS]
    assert len(names) == len(set(names))


def test_the_router_reads_each_tool_description():
    for tool in chat.TOOLS:
        assert chat.TOOL_GUIDE[tool.name] == tool.description


def test_evidence_is_plain_data():
    evidence = Evidence("commits", [{"sha": "abc1234"}])
    assert evidence.kind == "commits"
    assert evidence.items == [{"sha": "abc1234"}]

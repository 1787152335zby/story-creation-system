import pytest
from unittest.mock import MagicMock
from agents.plot_expander import PlotExpander


def test_extract_promise_list_returns_formatted_text():
    """测试从大纲中提取承诺清单"""
    expander = PlotExpander(MagicMock())
    expander.call_llm_stream = MagicMock(return_value=iter([
        "```\n"
        "【本故事承诺】\n"
        "- 必须出场的角色：林深、天眼\n"
        "- 必须发生的关键事件：接到案件、发现真相、对决\n"
        "- 必须解决的核心冲突：真相 vs 谎言\n"
        "```"
    ]))
    outline = "# 测试故事\n角色：林深（主角）、天眼（配角）\n剧情：第一幕到第三幕"
    result = expander._extract_promise_list(outline)
    assert "林深" in result
    assert "天眼" in result
    assert "必须出场的角色" in result
    assert "接到案件" in result


def test_extract_promise_list_empty_outline():
    """测试空大纲的情况"""
    mock = MagicMock()
    expander = PlotExpander(mock)
    result = expander._extract_promise_list("")
    assert result == "（无大纲内容）"


def test_chunk_strategy_pre_analyze_none_for_short():
    """测试短内容不分割"""
    from core.chunk_strategy import ChunkStrategy
    result = ChunkStrategy.pre_analyze_split_points("short text", None)
    assert result is None

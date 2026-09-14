from unittest.mock import MagicMock

from rag_demo.agents.query_expansion import QueryExpander


def _llm_returning(text: str) -> MagicMock:
    llm = MagicMock()
    llm.complete.return_value = MagicMock(text=text)
    return llm


def test_expand_splits_on_commas_and_trims_whitespace():
    expander = QueryExpander(_llm_returning(" sci-fi , 90s movies ,cult classic "))
    assert expander.expand("weird movies") == ["sci-fi", "90s movies", "cult classic"]


def test_expand_drops_empty_entries_from_stray_commas():
    expander = QueryExpander(_llm_returning("a,, b,"))
    assert expander.expand("q") == ["a", "b"]


def test_expand_truncates_to_five_results():
    expander = QueryExpander(_llm_returning("a,b,c,d,e,f,g"))
    assert expander.expand("q") == ["a", "b", "c", "d", "e"]


def test_expand_returns_empty_list_for_blank_response():
    expander = QueryExpander(_llm_returning("   "))
    assert expander.expand("q") == []

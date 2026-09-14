import json
from unittest.mock import MagicMock

from rag_demo.agents.correction import CorrectionAgent


def _llm_returning(text: str) -> MagicMock:
    llm = MagicMock()
    llm.complete.return_value = MagicMock(text=text)
    return llm


def test_correct_returns_parsed_json_array():
    recs = [{"title": "Dune", "imdb_rating": 8.0}]
    agent = CorrectionAgent(_llm_returning(json.dumps(recs)))
    assert agent.correct("q", []) == recs


def test_correct_falls_back_to_empty_list_on_invalid_json():
    agent = CorrectionAgent(_llm_returning("not json at all"))
    assert agent.correct("q", []) == []


def test_correct_falls_back_to_empty_list_when_response_is_not_a_list():
    agent = CorrectionAgent(_llm_returning(json.dumps({"title": "Dune"})))
    assert agent.correct("q", []) == []


def test_correct_handles_recommendations_missing_titles_when_building_the_prompt():
    agent = CorrectionAgent(_llm_returning("[]"))
    # Should not raise despite the missing "title" key.
    assert agent.correct("q", [{"overview": "mystery movie"}]) == []

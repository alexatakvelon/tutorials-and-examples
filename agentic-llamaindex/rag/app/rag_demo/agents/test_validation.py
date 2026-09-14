from unittest.mock import MagicMock

from rag_demo_agents_under_test.validation import ValidationAgent


def _llm_returning(text: str) -> MagicMock:
    llm = MagicMock()
    llm.complete.return_value = MagicMock(text=text)
    return llm


def test_validate_false_when_no_recommendations_have_titles():
    llm = _llm_returning("YES")
    agent = ValidationAgent(llm)
    assert agent.validate("q", [{"overview": "no title here"}]) is False
    llm.complete.assert_not_called()


def test_validate_true_on_affirmative_answer():
    agent = ValidationAgent(_llm_returning("Yes, these match."))
    assert agent.validate("q", [{"title": "Inception"}]) is True


def test_validate_false_on_negative_answer():
    agent = ValidationAgent(_llm_returning("No, these don't match."))
    assert agent.validate("q", [{"title": "Inception"}]) is False


def test_validate_is_case_insensitive():
    agent = ValidationAgent(_llm_returning("YES"))
    assert agent.validate("q", [{"title": "Inception"}]) is True

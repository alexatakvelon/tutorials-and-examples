import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock

from rag_demo_agents_under_test.coordinator import MultiStepCoordinator

INCEPTION_BLOB = (
    "Title: Inception\n"
    "Year: 2010\n"
    "Genre: Sci-Fi\n"
    "IMDb Rating: 8.8\n"
    "Overview: A thief who steals corporate secrets through dream-sharing technology.\n"
    "Director: Christopher Nolan\n"
    "Stars: Leonardo DiCaprio, Joseph Gordon-Levitt, Elliot Page"
)


def _fake_response(blobs):
    nodes = []
    for blob in blobs:
        node = SimpleNamespace(get_content=lambda blob=blob: blob)
        nodes.append(SimpleNamespace(node=node))
    return SimpleNamespace(source_nodes=nodes)


def _run(coordinator, query):
    return asyncio.run(coordinator.run(query))


def test_parses_metadata_from_a_matching_node():
    expander = MagicMock()
    expander.expand.return_value = ["sci-fi movies"]
    query_engine = MagicMock()
    query_engine.query.return_value = _fake_response([INCEPTION_BLOB])
    validator = MagicMock()
    validator.validate.return_value = True
    corrector = MagicMock()

    coordinator = MultiStepCoordinator(expander, query_engine, validator, corrector, max_steps=1)
    result = _run(coordinator, "mind-bending movies")

    assert result["recommendations"] == [
        {
            "title": "Inception",
            "imdb_rating": 8.8,
            "overview": "A thief who steals corporate secrets through dream-sharing technology.",
            "genre": "Sci-Fi",
            "released_year": 2010,
            "director": "Christopher Nolan",
            "stars": ["Leonardo DiCaprio", "Joseph Gordon-Levitt", "Elliot Page"],
        }
    ]


def test_stops_after_first_step_when_validation_succeeds():
    expander = MagicMock()
    expander.expand.return_value = ["sci-fi movies"]
    query_engine = MagicMock()
    query_engine.query.return_value = _fake_response([INCEPTION_BLOB])
    validator = MagicMock()
    validator.validate.return_value = True
    corrector = MagicMock()

    coordinator = MultiStepCoordinator(expander, query_engine, validator, corrector, max_steps=3)
    _run(coordinator, "mind-bending movies")

    validator.validate.assert_called_once()
    corrector.correct.assert_not_called()
    assert expander.expand.call_count == 1


def test_falls_back_to_corrector_output_when_validation_fails():
    expander = MagicMock()
    expander.expand.return_value = ["sci-fi movies"]
    query_engine = MagicMock()
    query_engine.query.return_value = _fake_response([INCEPTION_BLOB])
    validator = MagicMock()
    validator.validate.return_value = False
    corrector = MagicMock()
    corrected = [{"title": "Arrival", "imdb_rating": 7.9}]
    corrector.correct.return_value = corrected

    coordinator = MultiStepCoordinator(expander, query_engine, validator, corrector, max_steps=3)
    result = _run(coordinator, "mind-bending movies")

    assert result["recommendations"] == corrected
    assert expander.expand.call_count == 1


def test_returns_empty_recommendations_when_every_step_fails():
    expander = MagicMock()
    expander.expand.return_value = ["sci-fi movies"]
    query_engine = MagicMock()
    query_engine.query.return_value = _fake_response([INCEPTION_BLOB])
    validator = MagicMock()
    validator.validate.return_value = False
    corrector = MagicMock()
    corrector.correct.return_value = []

    coordinator = MultiStepCoordinator(expander, query_engine, validator, corrector, max_steps=2)
    result = _run(coordinator, "mind-bending movies")

    assert result["recommendations"] == []
    assert expander.expand.call_count == 2
    # The query fed into step 2 carries the "| corrected" marker rather than
    # being the raw user query again.
    second_call_query = expander.expand.call_args_list[1].args[0]
    assert second_call_query == "mind-bending movies | corrected"


def test_skips_nodes_that_do_not_match_the_metadata_pattern():
    expander = MagicMock()
    expander.expand.return_value = ["sci-fi movies"]
    query_engine = MagicMock()
    query_engine.query.return_value = _fake_response(["not a metadata blob", INCEPTION_BLOB])
    validator = MagicMock()
    validator.validate.return_value = True
    corrector = MagicMock()

    coordinator = MultiStepCoordinator(expander, query_engine, validator, corrector, max_steps=1)
    result = _run(coordinator, "q")

    assert [r["title"] for r in result["recommendations"]] == ["Inception"]


def test_deduplicates_by_title_keeping_the_last_occurrence():
    other_overview_blob = INCEPTION_BLOB.replace(
        "A thief who steals corporate secrets through dream-sharing technology.",
        "A different overview for the same title.",
    )
    expander = MagicMock()
    expander.expand.return_value = ["sci-fi movies"]
    query_engine = MagicMock()
    query_engine.query.return_value = _fake_response([INCEPTION_BLOB, other_overview_blob])
    validator = MagicMock()
    validator.validate.return_value = True
    corrector = MagicMock()

    coordinator = MultiStepCoordinator(expander, query_engine, validator, corrector, max_steps=1)
    result = _run(coordinator, "q")

    assert len(result["recommendations"]) == 1
    assert result["recommendations"][0]["overview"] == "A different overview for the same title."

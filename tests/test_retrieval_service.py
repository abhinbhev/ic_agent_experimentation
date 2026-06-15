import json

from ic_agent.models.retrieval import RetrievalQuery
from ic_agent.services.retrieval_service import HttpRetrievalClient, MockRetrievalClient, RetrievalService


def test_query_returns_mock_answer():
    service = RetrievalService(MockRetrievalClient())
    assert service.query("foo", "brand_guidance") == "Mock answer to: foo"


def test_query_structured_wraps_question_and_answer():
    service = RetrievalService(MockRetrievalClient())
    result = service.query_structured(RetrievalQuery(question="foo", usecase="category"))

    assert result.question == "foo"
    assert result.answer == "Mock answer to: foo"


def test_extract_answer_returns_summary_from_nested_response():
    data = {
        "request_id": "req-123",
        "question": "foo",
        "response": json.dumps({"Summary": "the summary text", "Other": "..."}),
        "error": None,
    }
    assert HttpRetrievalClient._extract_answer(data) == "the summary text"


def test_extract_answer_falls_back_to_raw_response_when_not_json():
    data = {"response": "plain text answer", "error": None}
    assert HttpRetrievalClient._extract_answer(data) == "plain text answer"


def test_extract_answer_returns_error_message():
    data = {"response": "", "error": "usecase not found"}
    assert HttpRetrievalClient._extract_answer(data) == "Retrieval error: usecase not found"

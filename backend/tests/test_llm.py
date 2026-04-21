import json
from unittest.mock import MagicMock, patch


def _mock_response(content: str):
    msg = MagicMock()
    msg.content = content
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


def test_triage_high_label():
    with patch("processing.llm._get_client") as mock_get:
        client = MagicMock()
        mock_get.return_value = client
        client.chat.completions.create.return_value = _mock_response(
            '{"triage_label": "high", "triage_score": 0.92, "sub_domain": "agents"}'
        )
        from processing.llm import triage
        result = triage({"title": "Agent paper", "raw_content": "abstract", "url": "http://x.com"})
        assert result["triage_label"] == "high"
        assert result["triage_score"] == 0.92
        assert result["sub_domain"] == "agents"


def test_triage_retries_on_bad_json():
    with patch("processing.llm._get_client") as mock_get:
        client = MagicMock()
        mock_get.return_value = client
        client.chat.completions.create.side_effect = [
            _mock_response("not json {{{"),
            _mock_response('{"triage_label": "medium", "triage_score": 0.5, "sub_domain": "llms"}'),
        ]
        from processing.llm import triage
        result = triage({"title": "Test", "raw_content": "abstract", "url": "http://x.com"})
        assert result["triage_label"] == "medium"
        assert client.chat.completions.create.call_count == 2


def test_triage_fallback_after_two_failures():
    with patch("processing.llm._get_client") as mock_get:
        client = MagicMock()
        mock_get.return_value = client
        client.chat.completions.create.side_effect = [
            _mock_response("bad"),
            _mock_response("also bad"),
        ]
        from processing.llm import triage
        result = triage({"title": "Test", "raw_content": "abstract", "url": "http://x.com"})
        assert result["triage_label"] == "medium"
        assert result["triage_score"] == 0.3


def test_enrich_returns_all_fields():
    with patch("processing.llm._get_client") as mock_get:
        client = MagicMock()
        mock_get.return_value = client
        client.chat.completions.create.return_value = _mock_response(json.dumps({
            "summary": "A paper about agents.",
            "why_matters": "Reduces failure rate by 40%.",
            "what_to_do": "Try integrating this backoff into your agent loop.",
            "relevance_label": "high",
            "relevance_score": 0.88,
        }))
        from processing.llm import enrich
        result = enrich(
            {"title": "Agent paper", "triage_label": "high", "sub_domain": "agents", "url": "http://x.com"},
            "intro text here",
        )
        assert result["summary"] == "A paper about agents."
        assert result["what_to_do"].startswith("Try")
        assert result["relevance_label"] == "high"
        assert result["llm_model"] == "gpt-4o"


def test_enrich_normalizes_bad_label():
    with patch("processing.llm._get_client") as mock_get:
        client = MagicMock()
        mock_get.return_value = client
        client.chat.completions.create.return_value = _mock_response(json.dumps({
            "summary": "s", "why_matters": "w", "what_to_do": "t",
            "relevance_label": "INVALID", "relevance_score": 0.5,
        }))
        from processing.llm import enrich
        result = enrich({"title": "T", "sub_domain": "llms", "url": "http://x.com"}, "content")
        assert result["relevance_label"] == "medium"

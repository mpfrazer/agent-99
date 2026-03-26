"""Tests for tools/search.py — search_google."""

from unittest.mock import MagicMock, patch

from tools.search import search_google


def _mock_response(items: list[dict], error: dict | None = None) -> MagicMock:
    """Build a mock requests.Response."""
    mock = MagicMock()
    mock.raise_for_status.return_value = None
    payload: dict = {"items": items} if error is None else {"error": error}
    mock.json.return_value = payload
    return mock


def _item(n: int) -> dict:
    return {
        "title": f"Result {n}",
        "link": f"https://example.com/{n}",
        "snippet": f"Snippet for result {n}.",
    }


def test_returns_results(monkeypatch):
    monkeypatch.setenv("GOOGLE_CSE_API_KEY", "key")
    monkeypatch.setenv("GOOGLE_CSE_ID", "cx")

    with patch("tools.search.requests.get", return_value=_mock_response([_item(1), _item(2)])):
        result = search_google("python testing", num_results=2)

    assert "Result 1" in result
    assert "https://example.com/1" in result
    assert "Snippet for result 1." in result
    assert "Result 2" in result


def test_result_count_in_header(monkeypatch):
    monkeypatch.setenv("GOOGLE_CSE_API_KEY", "key")
    monkeypatch.setenv("GOOGLE_CSE_ID", "cx")

    with patch("tools.search.requests.get", return_value=_mock_response([_item(i) for i in range(5)])):
        result = search_google("test", num_results=5)

    assert "5 result(s)" in result


def test_paginates_for_more_than_10(monkeypatch):
    monkeypatch.setenv("GOOGLE_CSE_API_KEY", "key")
    monkeypatch.setenv("GOOGLE_CSE_ID", "cx")

    page1 = [_item(i) for i in range(1, 11)]
    page2 = [_item(i) for i in range(11, 16)]

    call_count = 0

    def fake_get(url, params, timeout):
        nonlocal call_count
        call_count += 1
        return _mock_response(page1 if call_count == 1 else page2)

    with patch("tools.search.requests.get", side_effect=fake_get):
        result = search_google("test", num_results=15)

    assert call_count == 2
    assert "15 result(s)" in result


def test_clamps_num_results_to_25(monkeypatch):
    monkeypatch.setenv("GOOGLE_CSE_API_KEY", "key")
    monkeypatch.setenv("GOOGLE_CSE_ID", "cx")

    pages = [[_item(i) for i in range(j, j + 10)] for j in range(0, 30, 10)]
    call_iter = iter(pages)

    with patch("tools.search.requests.get", side_effect=lambda *a, **kw: _mock_response(next(call_iter))):
        result = search_google("test", num_results=99)

    # Should stop at 25
    assert "25 result(s)" in result


def test_clamps_num_results_to_1(monkeypatch):
    monkeypatch.setenv("GOOGLE_CSE_API_KEY", "key")
    monkeypatch.setenv("GOOGLE_CSE_ID", "cx")

    with patch("tools.search.requests.get", return_value=_mock_response([_item(1)])):
        result = search_google("test", num_results=0)

    assert "1 result(s)" in result


def test_no_results(monkeypatch):
    monkeypatch.setenv("GOOGLE_CSE_API_KEY", "key")
    monkeypatch.setenv("GOOGLE_CSE_ID", "cx")

    with patch("tools.search.requests.get", return_value=_mock_response([])):
        result = search_google("xyzzy404notfound")

    assert "No results found" in result


def test_missing_credentials_no_key(monkeypatch):
    monkeypatch.delenv("GOOGLE_CSE_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_CSE_ID", raising=False)

    result = search_google("test")
    assert "GOOGLE_CSE_API_KEY" in result
    assert "GOOGLE_CSE_ID" in result


def test_missing_credentials_partial(monkeypatch):
    monkeypatch.setenv("GOOGLE_CSE_API_KEY", "key")
    monkeypatch.delenv("GOOGLE_CSE_ID", raising=False)

    result = search_google("test")
    assert "not configured" in result


def test_api_error_response(monkeypatch):
    monkeypatch.setenv("GOOGLE_CSE_API_KEY", "key")
    monkeypatch.setenv("GOOGLE_CSE_ID", "cx")

    with patch(
        "tools.search.requests.get",
        return_value=_mock_response([], error={"code": 403, "message": "Daily Limit Exceeded"}),
    ):
        result = search_google("test")

    assert "403" in result
    assert "Daily Limit Exceeded" in result


def test_network_error(monkeypatch):
    import requests as req

    monkeypatch.setenv("GOOGLE_CSE_API_KEY", "key")
    monkeypatch.setenv("GOOGLE_CSE_ID", "cx")

    with patch("tools.search.requests.get", side_effect=req.ConnectionError("timeout")):
        result = search_google("test")

    assert "Search request failed" in result

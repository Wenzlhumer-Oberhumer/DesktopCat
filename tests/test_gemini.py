"""Tests fuer gemini.py: Fehler-Mapping, Modell-Fallback, Bild-Anhang (HTTP gemockt)."""
from unittest.mock import MagicMock, patch

import gemini
from gemini import LLMError


def _resp(status, body):
    r = MagicMock(status_code=status, ok=200 <= status < 300, text=str(body), reason="x")
    r.json.return_value = body
    return r


def _ask(*responses, **kw):
    with patch("gemini.requests.post", side_effect=list(responses)) as post:
        try:
            return gemini.ask("Hallo", key="AIzaTest", **kw), post
        except LLMError as exc:
            return exc, post


def test_no_key_raises_without_http():
    with patch("gemini.get_key", return_value=""), patch("gemini.requests.post") as post:
        try:
            gemini.ask("Hallo")
            assert False
        except LLMError as exc:
            assert "Key" in str(exc)
        post.assert_not_called()


def test_success_returns_text_and_skips_thoughts():
    body = {"candidates": [{"content": {"parts": [{"text": "geheim", "thought": True}, {"text": "Miau!"}]}}]}
    res, post = _ask(_resp(200, body))
    assert res == "Miau!"
    assert post.call_args.kwargs["headers"] == {"x-goog-api-key": "AIzaTest"}


def test_invalid_key_message():
    res, _ = _ask(_resp(400, {"error": {"status": "INVALID_ARGUMENT", "message": "API key not valid. Please pass a valid API key."}}))
    assert isinstance(res, LLMError) and "API-Key" in str(res)


def test_quota_message():
    res, _ = _ask(_resp(429, {"error": {"status": "RESOURCE_EXHAUSTED", "message": "Quota exceeded"}}))
    assert isinstance(res, LLMError) and "Kontingent" in str(res)


def test_404_falls_back_to_next_model():
    ok = _resp(200, {"candidates": [{"content": {"parts": [{"text": "OK"}]}}]})
    res, post = _ask(_resp(404, {"error": {"message": "model not found"}}), ok, model="gibts-nicht")
    assert res == "OK"
    assert "gibts-nicht" in post.call_args_list[0].args[0]
    assert gemini.MODELS[0] in post.call_args_list[1].args[0]


def test_image_is_attached_inline():
    ok = _resp(200, {"candidates": [{"content": {"parts": [{"text": "Schick!"}]}}]})
    res, post = _ask(ok, image_b64="QUJD")
    parts = post.call_args.kwargs["json"]["contents"][0]["parts"]
    assert parts[1] == {"inlineData": {"mimeType": "image/png", "data": "QUJD"}}


def test_response_mentioning_key_words_is_returned_normally():
    body = {"candidates": [{"content": {"parts": [{"text": '{"say": "Login, Auth und API-Key sind ok"}'}]}}]}
    res, _ = _ask(_resp(200, body))
    assert "Login" in res

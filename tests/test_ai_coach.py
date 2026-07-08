"""Tests voor ai_coach — mock zodat nooit echte API-calls."""
from unittest.mock import patch, MagicMock


SAMPLE_CTX = {
    "athlete_name": "Rowan",
    "readiness": 72,
    "hrv": 58,
    "sleep_s": 27000,
    "sleep_score": 75,
    "body_battery": 80,
    "acwr": 0.92,
    "training_today": {"title": "Tempo 10km", "run_type": "quality", "target_pace_s": 295},
}


def test_build_daily_context_includes_key_fields():
    from api.ai_coach import build_daily_context
    ctx_str = build_daily_context(SAMPLE_CTX)
    assert "Rowan" in ctx_str
    assert "72" in ctx_str
    assert "Tempo 10km" in ctx_str


def test_daily_note_calls_haiku_returns_string():
    from api.ai_coach import daily_note
    mock_client = MagicMock()
    mock_client.messages.create.return_value.content = [MagicMock(text="Goed herstel, train vol gas.")]
    with patch("api.ai_coach._client", mock_client):
        result = daily_note(SAMPLE_CTX)
    assert isinstance(result, str)
    assert len(result) > 0
    call_args = mock_client.messages.create.call_args
    assert "haiku" in call_args.kwargs["model"].lower()
    assert call_args.kwargs["max_tokens"] <= 100


def test_chat_calls_sonnet_returns_string():
    from api.ai_coach import chat
    mock_client = MagicMock()
    mock_client.messages.create.return_value.content = [MagicMock(text="Je VO2max is goed.")]
    with patch("api.ai_coach._client", mock_client):
        messages = [{"role": "user", "content": "Hoe ver ben ik van sub-4?"}]
        result = chat(messages, SAMPLE_CTX)
    assert isinstance(result, str)
    call_args = mock_client.messages.create.call_args
    assert "sonnet" in call_args.kwargs["model"].lower()


def test_daily_note_handles_missing_fields():
    from api.ai_coach import daily_note
    ctx = {"athlete_name": "Test"}
    mock_client = MagicMock()
    mock_client.messages.create.return_value.content = [MagicMock(text="Weinig data.")]
    with patch("api.ai_coach._client", mock_client):
        result = daily_note(ctx)
    assert isinstance(result, str)

import json
from unittest.mock import patch

from olney_chat import OpenAIResponsesClient, OPENROUTER_URL


def test_openrouter_request_and_response_contract():
    captured = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return json.dumps({"id": "test", "model": "test/model",
                               "choices": [{"message": {"content": "Bonjour"},
                                            "finish_reason": "stop"}],
                               "usage": {"prompt_tokens": 12, "completion_tokens": 3}}).encode()

    def post(request, timeout):
        assert request.full_url == OPENROUTER_URL
        assert request.get_header("Authorization") == "Bearer router-test"
        captured.append(json.loads(request.data))
        return Response()

    client = OpenAIResponsesClient("router-test", provider="openrouter", model="test/model")
    with patch("olney_chat.urlopen", post):
        result = client.respond(instructions="Règles", context={"card": "5♠"},
                                messages=[{"role": "user", "content": "Salut"}])
    assert captured[0]["messages"][0] == {"role": "system", "content": "Règles"}
    assert captured[0]["messages"][-1]["content"] == "Salut"
    assert "input" not in captured[0]
    assert result["text"] == "Bonjour"
    assert result["input_tokens"] == 12
    assert result["output_tokens"] == 3


def test_provider_switch_keeps_keys_separate():
    client = OpenAIResponsesClient("openai-test", model="original")
    with patch.dict("os.environ", {}, clear=True):
        try:
            client.configure_connection("openrouter")
        except ValueError:
            pass
        else:
            raise AssertionError("OpenAI key must not be reused with OpenRouter")
    assert client.provider == "openai"
    client.configure_connection("openrouter", "router-test", "test/model")
    assert client.api_key == "router-test"
    client.configure_connection("openai")
    assert client.api_key == "openai-test"
    assert client.model == "original"

import pytest
import requests
import responses as resp_mock
from llm_wiki.llm_client import LLMClient, LLMClientError, LLMConfig, load_llm_config


def test_load_llm_config_returns_none_when_base_url_unset():
    assert load_llm_config(env={}) is None


def test_load_llm_config_returns_none_when_base_url_empty():
    assert load_llm_config(env={"LLM_API_BASE_URL": ""}) is None


def test_load_llm_config_populates_fields_when_base_url_set():
    config = load_llm_config(
        env={
            "LLM_API_BASE_URL": "http://localhost:8080/v1",
            "LLM_API_KEY": "sk-test",
            "LLM_API_FORMAT": "openai",
            "LLM_MODEL": "qwen3-30b",
        }
    )
    assert config.base_url == "http://localhost:8080/v1"
    assert config.api_key == "sk-test"
    assert config.api_format == "openai"
    assert config.model == "qwen3-30b"


def test_load_llm_config_defaults_format_to_openai_when_unset():
    config = load_llm_config(env={"LLM_API_BASE_URL": "http://localhost:8080/v1"})
    assert config.api_format == "openai"


def test_load_llm_config_raises_on_unrecognized_format():
    with pytest.raises(ValueError):
        load_llm_config(
            env={
                "LLM_API_BASE_URL": "http://localhost:8080/v1",
                "LLM_API_FORMAT": "cohere",
            }
        )


def test_load_llm_config_fallback_none_when_fallback_base_url_unset():
    config = load_llm_config(env={"LLM_API_BASE_URL": "http://localhost:8080/v1"})
    assert config.fallback is None


def test_load_llm_config_fallback_populated_when_fallback_base_url_set():
    config = load_llm_config(
        env={
            "LLM_API_BASE_URL": "http://localhost:8080/v1",
            "LLM_FALLBACK_API_BASE_URL": "https://api.deepseek.com/v1",
            "LLM_FALLBACK_API_KEY": "sk-fallback",
            "LLM_FALLBACK_MODEL": "deepseek-chat",
        }
    )
    assert config.fallback.base_url == "https://api.deepseek.com/v1"
    assert config.fallback.api_key == "sk-fallback"
    assert config.fallback.model == "deepseek-chat"


def test_load_llm_config_fallback_defaults_format_to_openai_when_unset():
    config = load_llm_config(
        env={
            "LLM_API_BASE_URL": "http://localhost:8080/v1",
            "LLM_FALLBACK_API_BASE_URL": "https://api.deepseek.com/v1",
        }
    )
    assert config.fallback.api_format == "openai"


def test_load_llm_config_uses_os_environ_by_default(monkeypatch):
    monkeypatch.setenv("LLM_API_BASE_URL", "http://localhost:8080/v1")
    config = load_llm_config()
    assert config.base_url == "http://localhost:8080/v1"


@resp_mock.activate
def test_complete_sends_openai_request_and_parses_reply():
    resp_mock.add(
        resp_mock.POST,
        "http://localhost:8080/v1/chat/completions",
        json={"choices": [{"message": {"content": "hello back"}}]},
        status=200,
    )
    config = LLMConfig(
        base_url="http://localhost:8080/v1",
        api_key="sk-test",
        api_format="openai",
        model="qwen3-30b",
    )
    client = LLMClient(config)
    reply = client.complete([{"role": "user", "content": "hi"}])
    assert reply == "hello back"
    sent = resp_mock.calls[0].request
    assert sent.headers["Authorization"] == "Bearer sk-test"
    import json

    body = json.loads(sent.body)
    assert body["model"] == "qwen3-30b"
    assert body["messages"] == [{"role": "user", "content": "hi"}]


@resp_mock.activate
def test_complete_omits_auth_header_when_api_key_empty():
    resp_mock.add(
        resp_mock.POST,
        "http://localhost:8080/v1/chat/completions",
        json={"choices": [{"message": {"content": "ok"}}]},
        status=200,
    )
    config = LLMConfig(
        base_url="http://localhost:8080/v1", api_key="", api_format="openai", model=""
    )
    client = LLMClient(config)
    client.complete([{"role": "user", "content": "hi"}])
    sent = resp_mock.calls[0].request
    assert "Authorization" not in sent.headers


@resp_mock.activate
def test_complete_sends_anthropic_request_and_parses_reply():
    resp_mock.add(
        resp_mock.POST,
        "https://api.anthropic.com/v1/messages",
        json={"content": [{"type": "text", "text": "hello from claude"}]},
        status=200,
    )
    config = LLMConfig(
        base_url="https://api.anthropic.com/v1",
        api_key="sk-ant-test",
        api_format="anthropic",
        model="claude-sonnet-5",
    )
    client = LLMClient(config)
    reply = client.complete([{"role": "user", "content": "hi"}], system="Be terse.")
    assert reply == "hello from claude"
    sent = resp_mock.calls[0].request
    assert sent.headers["x-api-key"] == "sk-ant-test"
    assert sent.headers["anthropic-version"]
    import json

    body = json.loads(sent.body)
    assert body["model"] == "claude-sonnet-5"
    assert body["system"] == "Be terse."
    assert body["messages"] == [{"role": "user", "content": "hi"}]
    assert body["max_tokens"] > 0


@resp_mock.activate
def test_complete_falls_back_on_primary_http_error():
    resp_mock.add(
        resp_mock.POST, "http://localhost:8080/v1/chat/completions", status=500
    )
    resp_mock.add(
        resp_mock.POST,
        "https://api.deepseek.com/v1/chat/completions",
        json={"choices": [{"message": {"content": "fallback reply"}}]},
        status=200,
    )
    config = LLMConfig(
        base_url="http://localhost:8080/v1",
        api_key="",
        api_format="openai",
        model="",
        fallback=LLMConfig(
            base_url="https://api.deepseek.com/v1",
            api_key="sk-fb",
            api_format="openai",
            model="deepseek-chat",
        ),
    )
    client = LLMClient(config)
    reply = client.complete([{"role": "user", "content": "hi"}])
    assert reply == "fallback reply"


@resp_mock.activate
def test_complete_falls_back_on_primary_connection_error():
    resp_mock.add(
        resp_mock.POST,
        "http://localhost:8080/v1/chat/completions",
        body=requests.exceptions.ConnectionError("refused"),
    )
    resp_mock.add(
        resp_mock.POST,
        "https://api.deepseek.com/v1/chat/completions",
        json={"choices": [{"message": {"content": "fallback reply"}}]},
        status=200,
    )
    config = LLMConfig(
        base_url="http://localhost:8080/v1",
        api_key="",
        api_format="openai",
        model="",
        fallback=LLMConfig(
            base_url="https://api.deepseek.com/v1",
            api_key="sk-fb",
            api_format="openai",
            model="deepseek-chat",
        ),
    )
    client = LLMClient(config)
    reply = client.complete([{"role": "user", "content": "hi"}])
    assert reply == "fallback reply"


@resp_mock.activate
def test_complete_raises_when_primary_fails_and_no_fallback_configured():
    resp_mock.add(
        resp_mock.POST, "http://localhost:8080/v1/chat/completions", status=500
    )
    config = LLMConfig(
        base_url="http://localhost:8080/v1", api_key="", api_format="openai", model=""
    )
    client = LLMClient(config)
    with pytest.raises(LLMClientError):
        client.complete([{"role": "user", "content": "hi"}])


@resp_mock.activate
def test_complete_raises_when_primary_and_fallback_both_fail():
    resp_mock.add(
        resp_mock.POST, "http://localhost:8080/v1/chat/completions", status=500
    )
    resp_mock.add(
        resp_mock.POST, "https://api.deepseek.com/v1/chat/completions", status=500
    )
    config = LLMConfig(
        base_url="http://localhost:8080/v1",
        api_key="",
        api_format="openai",
        model="",
        fallback=LLMConfig(
            base_url="https://api.deepseek.com/v1",
            api_key="sk-fb",
            api_format="openai",
            model="deepseek-chat",
        ),
    )
    client = LLMClient(config)
    with pytest.raises(LLMClientError):
        client.complete([{"role": "user", "content": "hi"}])


def test_complete_raises_on_unsupported_format_constructed_directly():
    # load_llm_config() validates api_format, but LLMConfig can be constructed
    # directly (e.g. by a future caller) — complete() must still reject it.
    config = LLMConfig(base_url="http://x", api_key="", api_format="cohere", model="")
    client = LLMClient(config)
    with pytest.raises(LLMClientError):
        client.complete([{"role": "user", "content": "hi"}])


def test_llm_client_import_has_no_side_effects(monkeypatch):
    # No env vars set, no network access — importing/constructing must not
    # reach out to any provider on its own.
    monkeypatch.delenv("LLM_API_BASE_URL", raising=False)
    assert load_llm_config() is None


@resp_mock.activate
def test_complete_openai_malformed_response_falls_back():
    resp_mock.add(
        resp_mock.POST,
        "http://localhost:8080/v1/chat/completions",
        json={"error": "no choices field"},
        status=200,
    )
    resp_mock.add(
        resp_mock.POST,
        "https://api.deepseek.com/v1/chat/completions",
        json={"choices": [{"message": {"content": "fallback reply"}}]},
        status=200,
    )
    config = LLMConfig(
        base_url="http://localhost:8080/v1",
        api_key="",
        api_format="openai",
        model="",
        fallback=LLMConfig(
            base_url="https://api.deepseek.com/v1",
            api_key="sk-fb",
            api_format="openai",
            model="deepseek-chat",
        ),
    )
    client = LLMClient(config)
    reply = client.complete([{"role": "user", "content": "hi"}])
    assert reply == "fallback reply"


@resp_mock.activate
def test_complete_openai_malformed_response_raises_llmclienterror_without_fallback():
    resp_mock.add(
        resp_mock.POST,
        "http://localhost:8080/v1/chat/completions",
        json={"choices": []},
        status=200,
    )
    config = LLMConfig(
        base_url="http://localhost:8080/v1", api_key="", api_format="openai", model=""
    )
    client = LLMClient(config)
    with pytest.raises(LLMClientError):
        client.complete([{"role": "user", "content": "hi"}])


@resp_mock.activate
def test_complete_anthropic_malformed_response_raises_llmclienterror():
    resp_mock.add(
        resp_mock.POST,
        "https://api.anthropic.com/v1/messages",
        json={"content": []},
        status=200,
    )
    config = LLMConfig(
        base_url="https://api.anthropic.com/v1",
        api_key="sk-ant-test",
        api_format="anthropic",
        model="claude-sonnet-5",
    )
    client = LLMClient(config)
    with pytest.raises(LLMClientError):
        client.complete([{"role": "user", "content": "hi"}])


@resp_mock.activate
def test_complete_anthropic_omits_system_key_when_not_passed():
    resp_mock.add(
        resp_mock.POST,
        "https://api.anthropic.com/v1/messages",
        json={"content": [{"type": "text", "text": "ok"}]},
        status=200,
    )
    config = LLMConfig(
        base_url="https://api.anthropic.com/v1",
        api_key="sk-ant-test",
        api_format="anthropic",
        model="claude-sonnet-5",
    )
    client = LLMClient(config)
    client.complete([{"role": "user", "content": "hi"}])
    import json

    body = json.loads(resp_mock.calls[0].request.body)
    assert "system" not in body


@resp_mock.activate
def test_complete_anthropic_omits_auth_header_when_api_key_empty():
    resp_mock.add(
        resp_mock.POST,
        "https://api.anthropic.com/v1/messages",
        json={"content": [{"type": "text", "text": "ok"}]},
        status=200,
    )
    config = LLMConfig(
        base_url="https://api.anthropic.com/v1",
        api_key="",
        api_format="anthropic",
        model="",
    )
    client = LLMClient(config)
    client.complete([{"role": "user", "content": "hi"}])
    sent = resp_mock.calls[0].request
    assert "x-api-key" not in sent.headers


def test_load_llm_config_treats_whitespace_only_base_url_as_unset():
    assert load_llm_config(env={"LLM_API_BASE_URL": "   "}) is None


def test_load_llm_config_fallback_degrades_to_none_on_invalid_fallback_format():
    # An unconfigured/broken fallback must not take down an otherwise-valid
    # primary config for an unattended job.
    config = load_llm_config(
        env={
            "LLM_API_BASE_URL": "http://localhost:8080/v1",
            "LLM_FALLBACK_API_BASE_URL": "https://api.deepseek.com/v1",
            "LLM_FALLBACK_API_FORMAT": "cohere",
        }
    )
    assert config.base_url == "http://localhost:8080/v1"
    assert config.fallback is None

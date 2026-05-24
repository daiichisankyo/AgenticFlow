"""Multi-provider pass-through tests.

These tests verify AF passes model configuration to the SDK unchanged.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

import pytest
from agents import RunConfig
from agents.models.multi_provider import MultiProvider

import agentic_flow as af


def fetch_json(url: str) -> dict:
    with urlopen(url, timeout=2) as response:
        return json.loads(response.read().decode("utf-8"))


def first_llama_cpp_model_id(base_url: str) -> str:
    payload = fetch_json(f"{base_url}/v1/models")
    data = payload.get("data", [])
    if not isinstance(data, list) or not data:
        raise ValueError("No models returned from llama-cpp server")
    first = data[0]
    if not isinstance(first, dict) or not first.get("id"):
        raise ValueError("Invalid model entry from llama-cpp server")
    return str(first["id"])


@pytest.fixture(scope="module")
def llama_cpp_model_path() -> str:
    """Ensure a local GGUF file exists for llama-cpp server."""
    configured = os.getenv("AF_LLAMA_CPP_MODEL_PATH")
    if configured and Path(configured).exists():
        print(f"[e2e] using AF_LLAMA_CPP_MODEL_PATH: {configured}", flush=True)
        return configured

    if importlib.util.find_spec("huggingface_hub") is None:
        pytest.skip("huggingface_hub is not installed and AF_LLAMA_CPP_MODEL_PATH is unset")

    from huggingface_hub import hf_hub_download

    repo = os.getenv("AF_LLAMA_CPP_MODEL_REPO", "TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF")
    filename = os.getenv("AF_LLAMA_CPP_MODEL_FILE", "tinyllama-1.1b-chat-v1.0.Q2_K.gguf")
    local_dir = os.getenv("AF_LLAMA_CPP_CACHE_DIR", ".models/llama-cpp")

    try:
        print(f"[e2e] downloading GGUF from {repo}/{filename} to {local_dir}", flush=True)
        path = hf_hub_download(repo_id=repo, filename=filename, local_dir=local_dir)
        print(f"[e2e] GGUF ready: {path}", flush=True)
        return path
    except Exception as exc:
        pytest.skip(f"Failed to download GGUF model ({repo}/{filename}): {exc}")


@pytest.fixture(scope="module")
def llama_cpp_runtime(llama_cpp_model_path: str) -> tuple[str, str]:
    """Ensure llama-cpp OpenAI-compatible server is reachable for local E2E tests."""
    if importlib.util.find_spec("llama_cpp") is None:
        pytest.skip("llama-cpp-python is not installed")

    base_url = os.getenv("AF_LLAMA_CPP_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
    host = os.getenv("AF_LLAMA_CPP_HOST", "127.0.0.1")
    port = os.getenv("AF_LLAMA_CPP_PORT", "8000")

    original_openai_api_base = os.environ.get("OPENAI_API_BASE")
    original_openai_base_url = os.environ.get("OPENAI_BASE_URL")
    original_openai_api_key = os.environ.get("OPENAI_API_KEY")
    os.environ["OPENAI_API_BASE"] = f"{base_url}/v1"
    os.environ["OPENAI_BASE_URL"] = f"{base_url}/v1"
    os.environ.setdefault("OPENAI_API_KEY", "dummy")

    started_proc: subprocess.Popen[str] | None = None
    try:
        model_id = first_llama_cpp_model_id(base_url)
        print(f"[e2e] using existing llama-cpp server: {base_url} ({model_id})", flush=True)
        yield base_url, model_id
        return
    except (URLError, TimeoutError, OSError):
        pass

    started_proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "llama_cpp.server",
            "--model",
            llama_cpp_model_path,
            "--host",
            host,
            "--port",
            port,
        ],
        stdout=None,
        stderr=None,
        text=True,
    )
    print(f"[e2e] started llama-cpp server at {base_url}", flush=True)
    try:
        timeout_sec = int(os.getenv("AF_LLAMA_CPP_STARTUP_TIMEOUT", "60"))
        checks = max(timeout_sec * 2, 1)
        for _ in range(checks):
            try:
                model_id = first_llama_cpp_model_id(base_url)
                print(f"[e2e] llama-cpp server ready (model_id={model_id})", flush=True)
                yield base_url, model_id
                return
            except (URLError, TimeoutError, OSError, ValueError):
                if started_proc.poll() is not None:
                    break
                time.sleep(0.5)

        pytest.skip(f"llama-cpp server did not become ready at {base_url}")
    finally:
        if started_proc is not None:
            started_proc.terminate()
            try:
                started_proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                started_proc.kill()

        if original_openai_api_base is None:
            os.environ.pop("OPENAI_API_BASE", None)
        else:
            os.environ["OPENAI_API_BASE"] = original_openai_api_base
        if original_openai_base_url is None:
            os.environ.pop("OPENAI_BASE_URL", None)
        else:
            os.environ["OPENAI_BASE_URL"] = original_openai_base_url
        if original_openai_api_key is None:
            os.environ.pop("OPENAI_API_KEY", None)
        else:
            os.environ["OPENAI_API_KEY"] = original_openai_api_key


class TestMultiProviderPassThrough:
    """Verify AF passes model configuration to SDK unchanged."""

    def test_prefix_model_in_agent(self):
        """Agent accepts prefixed model names for LiteLLM routing."""
        agent = af.Agent(
            name="claude",
            instructions="Reply OK",
            model="litellm/anthropic/claude-sonnet-4-20250514",
        )
        spec = agent("test")
        assert spec.sdk_agent.model == "litellm/anthropic/claude-sonnet-4-20250514"

    def test_run_config_model_override(self):
        """RunConfig model override flows through .run_config() modifier."""
        agent = af.Agent(name="test", instructions="OK", model="gpt-5.5")
        config = RunConfig(model="gpt-4o-mini")

        spec = agent("test").run_config(config)

        assert spec.run_kwargs.get("run_config") is config
        assert config.model == "gpt-4o-mini"

    def test_run_config_model_provider(self):
        """RunConfig model_provider flows through .run_config() modifier."""
        agent = af.Agent(name="test", instructions="OK", model="gpt-5.5")
        config = RunConfig(model_provider=MultiProvider())

        spec = agent("test").run_config(config)

        assert spec.run_kwargs.get("run_config") is config
        assert isinstance(config.model_provider, MultiProvider)

    def test_different_models_coexist(self):
        """Agents with different model prefixes coexist in same scope."""
        openai_agent = af.Agent(name="a", instructions="OK", model="gpt-5.5")
        claude_agent = af.Agent(
            name="b",
            instructions="OK",
            model="litellm/anthropic/claude-sonnet-4-20250514",
        )

        spec_a = openai_agent("test")
        spec_b = claude_agent("test")

        assert spec_a.sdk_agent.model == "gpt-5.5"
        assert spec_b.sdk_agent.model == "litellm/anthropic/claude-sonnet-4-20250514"


@pytest.fixture(scope="module")
def ollama_runtime():
    """Ensure Ollama is running and a test model is available."""
    base_url = os.getenv("AF_OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    model_name = os.getenv("AF_OLLAMA_MODEL", "qwen2.5:0.5b")

    try:
        tags = fetch_json(f"{base_url}/api/tags")
    except (URLError, TimeoutError, OSError):
        pytest.skip(f"Ollama not reachable at {base_url}")

    available = [m["name"] for m in tags.get("models", [])]
    if not any(model_name in name for name in available):
        pytest.skip(f"Model {model_name} not available in Ollama (have: {available})")

    yield base_url, model_name


class TestMultiProviderE2E:
    """E2E smoke tests for runtime multi-provider routing."""

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_litellm_ollama_local_model_executes(
        self,
        ollama_runtime: tuple[str, str],
    ):
        """Run a real call through LiteLLM -> Ollama local server."""
        if importlib.util.find_spec("litellm") is None:
            pytest.skip("litellm is not installed")

        base_url, model_name = ollama_runtime
        print(f"[e2e] testing model litellm/ollama_chat/{model_name} via {base_url}", flush=True)

        agent = af.Agent(
            name="ollama_local_e2e",
            instructions="Reply with exactly 'OK'.",
            model=f"litellm/ollama_chat/{model_name}",
        )

        result = await agent("test")
        print(f"[e2e] model response: {result!r}", flush=True)
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_litellm_llama_cpp_local_light_model_executes(
        self,
        llama_cpp_runtime: tuple[str, str],
    ):
        """Run a real call through LiteLLM -> local llama-cpp server."""
        if importlib.util.find_spec("litellm") is None:
            pytest.skip("litellm is not installed")

        _base_url, model_id = llama_cpp_runtime
        print(f"[e2e] testing model litellm/openai/{model_id} via {_base_url}", flush=True)

        agent = af.Agent(
            name="llama_cpp_local_e2e",
            instructions="Reply with exactly 'OK'.",
            model=f"litellm/openai/{model_id}",
        )

        result = await agent("test")
        print(f"[e2e] model response: {result!r}", flush=True)
        assert isinstance(result, str)
        assert "OK" in result.upper()

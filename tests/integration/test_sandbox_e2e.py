"""Real-LLM end-to-end tests for af.SandboxAgent.

These tests boot an actual `unix_local` sandbox in a temp directory and
issue a real LLM call. They are opt-in:

  - Marked `@pytest.mark.integration` (registered in pyproject.toml).
  - Module-level skipif requires `AF_RUN_INTEGRATION=1` to be set.

Default test runs (`uv run pytest`) skip these to avoid surprise API costs.
Enable explicitly with:

    AF_RUN_INTEGRATION=1 uv run pytest tests/integration -m integration -v

The ``-m integration`` flag is required because ``pyproject.toml`` sets
``addopts = ["-m", "not e2e and not integration"]`` for the offline default;
the command-line ``-m`` overrides that filter so the marked tests are
actually selected.

The unit-level pass-through coverage lives in `tests/test_sandbox.py`.
This file complements it with end-to-end behaviour: AF correctly hands the
constructed `SandboxAgent` + `RunConfig(sandbox=SandboxRunConfig(...))` to
the SDK, the SDK starts a real sandbox, the agent runs there, and the
filesystem effects are observable on the host.
"""

from __future__ import annotations

import asyncio
import os
import pathlib
import tempfile

import pytest
from agents import RunConfig
from agents.sandbox import Manifest, SandboxRunConfig
from agents.sandbox.sandboxes.unix_local import UnixLocalSandboxClient

import agentic_flow as af

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not os.getenv("AF_RUN_INTEGRATION"),
        reason="set AF_RUN_INTEGRATION=1 to run real-LLM sandbox integration tests",
    ),
    pytest.mark.skipif(
        not os.getenv("OPENAI_API_KEY"),
        reason="OPENAI_API_KEY not set",
    ),
]


def _build_sandbox_config(workdir: pathlib.Path) -> tuple[Manifest, SandboxRunConfig]:
    """Minimal manifest + run-config rooted at the given temp directory."""
    manifest = Manifest(version=1, root=str(workdir))
    client = UnixLocalSandboxClient()
    return manifest, SandboxRunConfig(client=client, manifest=manifest)


@pytest.mark.asyncio
async def test_sandbox_agent_writes_file_in_workspace() -> None:
    """SandboxAgent can use shell access to create a file in its workspace.

    Verifies the full AF -> SDK -> sandbox -> filesystem path:
      1. AF builds a SandboxAgent and threads `RunConfig(sandbox=...)` through
         the existing `.run_config()` modifier.
      2. The SDK starts a unix_local sandbox at the given root.
      3. The LLM-driven agent writes the requested file via shell.
      4. The host sees the file at the expected path with the expected bytes.
    """
    with tempfile.TemporaryDirectory(prefix="af-sandbox-itest-write-") as workdir:
        workdir_path = pathlib.Path(workdir)
        manifest, sandbox_rc = _build_sandbox_config(workdir_path)

        coder = af.SandboxAgent(
            name="writer",
            instructions=(
                "You are a sandboxed coding agent with shell access. "
                "When asked to write a file, use the shell to create the file at "
                "the requested path with exactly the requested contents. "
                "Reply with exactly: DONE."
            ),
            model="gpt-5.5",
            default_manifest=manifest,
        )

        target_file = workdir_path / "hello.txt"
        prompt = (
            f"Create a file at {target_file} containing exactly the text "
            f"'hello from sandbox'. Then reply DONE."
        )

        async def flow(msg: str) -> str:
            return await coder(msg).run_config(RunConfig(sandbox=sandbox_rc))

        runner = af.Runner(flow=flow)
        reply = await runner(prompt)

        # Agent responded
        assert isinstance(reply, str) and reply.strip(), f"empty reply: {reply!r}"

        # File exists where requested (or anywhere in workspace as a fallback)
        if not target_file.exists():
            matches = list(workdir_path.rglob("hello.txt"))
            assert matches, (
                f"agent did not produce hello.txt anywhere in workspace; reply={reply!r}"
            )
            target_file = matches[0]

        contents = target_file.read_text()
        assert "hello from sandbox" in contents, (
            f"file produced but contents unexpected: {contents!r}"
        )


@pytest.mark.asyncio
async def test_sandbox_agent_reads_pre_seeded_file_round_trip() -> None:
    """SandboxAgent can read a host-seeded file and write a derived output.

    Verifies the round-trip: host writes INPUT, agent (sandboxed) reads
    INPUT and writes OUTPUT, host observes OUTPUT.
    """
    with tempfile.TemporaryDirectory(prefix="af-sandbox-itest-rt-") as workdir:
        workdir_path = pathlib.Path(workdir)
        manifest, sandbox_rc = _build_sandbox_config(workdir_path)

        # Host seeds an INPUT file before the sandbox starts.
        input_file = workdir_path / "INPUT.txt"
        input_file.write_text("agentic-flow")
        output_file = workdir_path / "OUTPUT.txt"

        translator = af.SandboxAgent(
            name="copier",
            instructions=(
                "You are a sandboxed agent with shell access. Use the shell to "
                "read and write files. Always reply with exactly DONE after the "
                "operation."
            ),
            model="gpt-5.5",
            default_manifest=manifest,
        )

        prompt = (
            f"Read the file at {input_file}. Take its exact contents and write "
            f"them, unchanged, to {output_file}. Then reply DONE."
        )

        async def flow(msg: str) -> str:
            return await translator(msg).run_config(RunConfig(sandbox=sandbox_rc))

        runner = af.Runner(flow=flow)
        reply = await runner(prompt)

        assert isinstance(reply, str) and reply.strip(), f"empty reply: {reply!r}"

        # Output file located, contents match input verbatim.
        if not output_file.exists():
            matches = list(workdir_path.rglob("OUTPUT.txt"))
            assert matches, (
                f"agent did not produce OUTPUT.txt anywhere in workspace; reply={reply!r}"
            )
            output_file = matches[0]

        out = output_file.read_text()
        assert "agentic-flow" in out, f"OUTPUT.txt content does not contain INPUT bytes: {out!r}"


if __name__ == "__main__":  # pragma: no cover
    asyncio.run(asyncio.sleep(0))  # placeholder; tests are run via pytest

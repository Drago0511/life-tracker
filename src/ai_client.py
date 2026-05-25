"""
AI client backed by the local `claude` CLI.

Uses the user's existing claude.ai authentication (OAuth via the Claude Code
CLI keychain), so no ANTHROPIC_API_KEY env var is required. If `claude` is not
on PATH or not authenticated, calls return None and the UI gracefully degrades.
"""
import shutil
import subprocess
from typing import Optional


_CLI = "claude"
_DEFAULT_TIMEOUT = 45  # seconds; AI replies usually arrive in 2-10s


def _cli_path() -> Optional[str]:
    return shutil.which(_CLI)


def has_ai() -> bool:
    return _cli_path() is not None


def _run_claude(prompt: str, system: str, max_tokens: int) -> Optional[str]:
    cli = _cli_path()
    if not cli:
        return None
    cmd = [
        cli,
        "-p",
        "--model", "haiku",
        "--output-format", "text",
        "--tools", "",                  # no tool use for plain text completions
        "--no-session-persistence",     # don't pollute resume history
        "--disable-slash-commands",     # treat input as plain text only
    ]
    if system:
        cmd += ["--system-prompt", system]
    cmd.append(prompt)
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=_DEFAULT_TIMEOUT,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None
    if result.returncode != 0:
        return None
    text = (result.stdout or "").strip()
    return text or None


def ai_complete(prompt: str, system: str = "", max_tokens: int = 400) -> Optional[str]:
    return _run_claude(
        prompt,
        system=system or "You are a concise, warm productivity assistant.",
        max_tokens=max_tokens,
    )


def ai_json(prompt: str, system: str = "", max_tokens: int = 300) -> Optional[str]:
    return _run_claude(
        prompt,
        system=system or "Return only valid JSON. No explanation, no markdown, no code fences.",
        max_tokens=max_tokens,
    )

"""LLM-powered troubleshooting — use user's cloud LLM to diagnose issues."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from typing import Optional

from .diagnostics import DiagnosticReport, DiagnosticCheck


SYSTEM_PROMPT = """You are ObserveCo's intelligent troubleshooter. You help users fix installation and configuration issues for ObserveCo, a runtime observability tool for AI agents.

You have access to their full environment diagnostics. Diagnose each issue and provide specific, actionable fixes.

Rules:
1. Be specific — give exact commands, not vague instructions
2. Check their OS — Windows/macOS/Linux commands differ
3. Explain WHY each fix is needed, not just WHAT
4. If an issue requires manual steps (like creating a Slack app), provide step-by-step
5. If an issue can't be fixed automatically, say so clearly
6. NEVER suggest destructive actions (rm, sudo, chmod, delete, format)
7. NEVER suggest commands with pipes, redirects, or command chaining (;, &&, ||, |)
8. NEVER suggest network requests (curl, wget, ssh, scp)
9. For env var issues, explain how to set them permanently (not just export)
10. For permission issues, explain the security implications of sudo/chmod
11. Only suggest: pip install, pip3 install, python -m pip install, observeco commands
12. If you're unsure about a fix, say so — don't guess

SAFE COMMANDS (always OK to suggest):
- pip install <package>
- pip3 install <package>
- python -m pip install <package>
- observeco init
- observeco doctor diagnose
- python3 -m observeco.cli

Response format — for each issue, provide:
ISSUE: <name>
SEVERITY: <critical|warning|info>
EXPLANATION: <what's wrong and why>
FIX_COMMAND: <exact command to run, or empty if manual steps needed>
FIX_MANUAL: <step-by-step manual instructions if command isn't enough, or empty>
"""

USER_PROMPT = """Here are my ObserveCo diagnostics:

{diagnostics}

Please diagnose each issue (status != ok) and provide fixes. For each issue, respond in this exact format:

ISSUE: <name>
SEVERITY: <critical|warning|info>
EXPLANATION: <what's wrong>
FIX_COMMAND: <command to run>
FIX_MANUAL: <manual steps if needed>

After all issues, add a summary line:
SUMMARY: <one-line summary of total fixes>"""


@dataclass
class LLMFix:
    """A fix recommended by the LLM."""
    issue: str
    severity: str
    explanation: str
    fix_command: str
    fix_manual: str


@dataclass
class LLMProvider:
    """Interface for LLM providers."""
    name: str
    available: bool = False
    api_key: str = ""


def detect_llm_providers() -> list[LLMProvider]:
    """Detect available LLM providers from environment.

    Checks 20+ provider env vars plus local LLM servers.
    """
    providers = []

    # --- Major providers (env vars) ---
    env_providers = [
        ("anthropic", "ANTHROPIC_API_KEY"),
        ("openai", "OPENAI_API_KEY"),
        ("google", "GOOGLE_API_KEY"),
        ("deepseek", "DEEPSEEK_API_KEY"),
        ("mistral", "MISTRAL_API_KEY"),
        ("groq", "GROQ_API_KEY"),
        ("together", "TOGETHER_API_KEY"),
        ("openrouter", "OPENROUTER_API_KEY"),
    ]

    seen_providers = set()
    for provider_name, env_var in env_providers:
        key = os.environ.get(env_var, "")
        if key and provider_name not in seen_providers:
            providers.append(LLMProvider(name=provider_name, available=True, api_key=key))
            seen_providers.add(provider_name)

    # --- Check OpenRouter (uses OPENAI_API_KEY sometimes) ---
    openai_key = os.environ.get("OPENAI_API_KEY", "")
    if openai_key and "openai" not in seen_providers:
        # Check if it's an OpenRouter key (starts with sk-or-)
        if openai_key.startswith("sk-or-"):
            providers.append(LLMProvider(name="openrouter", available=True, api_key=openai_key))
            seen_providers.add("openrouter")

    # --- Local LLM servers ---
    local_servers = [
        ("ollama", "http://localhost:11434/api/tags"),
        ("lmstudio", "http://localhost:1234/v1/models"),
        ("vllm", "http://localhost:8000/v1/models"),
        ("textgen", "http://localhost:5000/v1/models"),
        ("localai", "http://localhost:8080/v1/models"),
    ]

    for name, url in local_servers:
        if name in seen_providers:
            continue
        try:
            import urllib.request
            urllib.request.urlopen(url, timeout=2)
            providers.append(LLMProvider(name=name, available=True))
            seen_providers.add(name)
        except Exception:
            pass

    return providers


def get_auto_provider(providers: list[LLMProvider]) -> Optional[LLMProvider]:
    """Auto-detect the best available provider.

    Preference order: cloud providers > local servers.
    """
    # Prefer cloud providers (more capable for diagnosis)
    cloud_preferred = ["anthropic", "openai", "deepseek", "google", "mistral",
                       "groq", "together", "openrouter", "cohere"]
    for preferred in cloud_preferred:
        for p in providers:
            if p.name == preferred and p.available:
                return p

    # Fall back to local servers
    local_preferred = ["ollama", "lmstudio", "vllm", "textgen", "localai"]
    for preferred in local_preferred:
        for p in providers:
            if p.name == preferred and p.available:
                return p

    return None


def diagnose_with_llm(report: DiagnosticReport, provider: Optional[LLMProvider] = None) -> list[LLMFix]:
    """Send diagnostics to LLM and get fixes."""
    if not provider:
        providers = detect_llm_providers()
        provider = get_auto_provider(providers)

    if not provider or not provider.available:
        return _static_diagnosis(report)

    diagnostics_text = report.to_text()
    user_prompt = USER_PROMPT.format(diagnostics=diagnostics_text)

    try:
        if provider.name == "anthropic":
            response = _call_anthropic(provider.api_key, SYSTEM_PROMPT, user_prompt)
        elif provider.name == "openai":
            response = _call_openai(provider.api_key, SYSTEM_PROMPT, user_prompt)
        elif provider.name == "google":
            response = _call_google(provider.api_key, SYSTEM_PROMPT, user_prompt)
        elif provider.name == "ollama":
            response = _call_ollama(SYSTEM_PROMPT, user_prompt)
        elif provider.name == "deepseek":
            response = _call_openai_compatible(
                provider.api_key, SYSTEM_PROMPT, user_prompt,
                base_url="https://api.deepseek.com",
                model="deepseek-chat",
            )
        elif provider.name == "mistral":
            response = _call_openai_compatible(
                provider.api_key, SYSTEM_PROMPT, user_prompt,
                base_url="https://api.mistral.ai",
                model="mistral-large-latest",
            )
        elif provider.name == "groq":
            response = _call_openai_compatible(
                provider.api_key, SYSTEM_PROMPT, user_prompt,
                base_url="https://api.groq.com/openai",
                model="llama-3.1-70b-versatile",
            )
        elif provider.name == "together":
            response = _call_openai_compatible(
                provider.api_key, SYSTEM_PROMPT, user_prompt,
                base_url="https://api.together.xyz",
                model="meta-llama/Llama-3-70b-chat-hf",
            )
        elif provider.name == "openrouter":
            response = _call_openai_compatible(
                provider.api_key, SYSTEM_PROMPT, user_prompt,
                base_url="https://openrouter.ai/api",
                model="anthropic/claude-sonnet-4",
            )
        elif provider.name in ("lmstudio", "vllm", "textgen", "localai"):
            base_urls = {
                "lmstudio": "http://localhost:1234/v1",
                "vllm": "http://localhost:8000/v1",
                "textgen": "http://localhost:5000/v1",
                "localai": "http://localhost:8080/v1",
            }
            response = _call_openai_compatible(
                "", SYSTEM_PROMPT, user_prompt,
                base_url=base_urls[provider.name],
                model="default",
            )
        else:
            return _static_diagnosis(report)

        return _parse_fixes(response)
    except Exception as e:
        print(f"LLM call failed: {e}", file=sys.stderr)
        return _static_diagnosis(report)


def _call_anthropic(api_key: str, system: str, prompt: str) -> str:
    """Call Anthropic Claude API."""
    import urllib.request
    data = json.dumps({
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 2048,
        "system": system,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=data,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read())
        return result["content"][0]["text"]


def _call_openai(api_key: str, system: str, prompt: str) -> str:
    """Call OpenAI API."""
    import urllib.request
    data = json.dumps({
        "model": "gpt-4o",
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 2048,
    }).encode()
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read())
        return result["choices"][0]["message"]["content"]


def _call_google(api_key: str, system: str, prompt: str) -> str:
    """Call Google Gemini API."""
    import urllib.request
    data = json.dumps({
        "contents": [{"parts": [{"text": f"{system}\n\n{prompt}"}]}],
    }).encode()
    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read())
        return result["candidates"][0]["content"]["parts"][0]["text"]


def _call_ollama(system: str, prompt: str) -> str:
    """Call local Ollama API."""
    import urllib.request
    data = json.dumps({
        "model": "llama3.1",
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "stream": False,
    }).encode()
    req = urllib.request.Request(
        "http://localhost:11434/api/chat",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        result = json.loads(resp.read())
        return result["message"]["content"]


def _call_openai_compatible(api_key: str, system: str, prompt: str,
                             base_url: str, model: str) -> str:
    """Call any OpenAI-compatible API (DeepSeek, Mistral, Groq, Together, etc.)."""
    import urllib.request
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    data = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 2048,
    }).encode()
    req = urllib.request.Request(
        f"{base_url}/v1/chat/completions",
        data=data,
        headers=headers,
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read())
        return result["choices"][0]["message"]["content"]


def _parse_fixes(response: str) -> list[LLMFix]:
    """Parse LLM response into structured fixes."""
    fixes = []
    current = {}

    for line in response.split("\n"):
        line = line.strip()
        if line.startswith("ISSUE:"):
            if current:
                fixes.append(LLMFix(**current))
            current = {"issue": line[6:].strip(), "severity": "warning", "explanation": "", "fix_command": "", "fix_manual": ""}
        elif line.startswith("SEVERITY:"):
            current["severity"] = line[9:].strip().lower()
        elif line.startswith("EXPLANATION:"):
            current["explanation"] = line[12:].strip()
        elif line.startswith("FIX_COMMAND:"):
            current["fix_command"] = line[12:].strip()
        elif line.startswith("FIX_MANUAL:"):
            current["fix_manual"] = line[11:].strip()

    if current:
        fixes.append(LLMFix(**current))

    return fixes


def _static_diagnosis(report: DiagnosticReport) -> list[LLMFix]:
    """Provide static fixes when no LLM is available."""
    fixes = []

    for check in report.issues:
        if check.auto_fix:
            fixes.append(LLMFix(
                issue=check.name,
                severity=check.status,
                explanation=check.message,
                fix_command=check.auto_fix,
                fix_manual="",
            ))
        else:
            fixes.append(LLMFix(
                issue=check.name,
                severity=check.status,
                explanation=check.message,
                fix_command="",
                fix_manual="Check the ObserveCo documentation for manual setup instructions.",
            ))

    return fixes

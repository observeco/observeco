"""
ObserveCo Dashboard Configuration — Single Source of Truth

All thresholds, pricing, estimates, and configurable constants live here.
Every hardcoded value in server.py and index.html should reference this module.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List, Optional

# ── Ports ─────────────────────────────────────────────────────────────────────
# Single source of truth for all ObserveCo service ports.
# Override via env vars: OBSERVECO_<NAME>_PORT (e.g. OBSERVECO_DASHBOARD_PORT=8899)

@dataclass
class Ports:
    """All ObserveCo service ports. Every hardcoded port in the codebase should reference this."""
    # Core services
    dashboard: int = int(os.environ.get("OBSERVECO_DASHBOARD_PORT", "9119"))
    otel: int = int(os.environ.get("OBSERVECO_OTEL_PORT", "4318"))
    service: int = int(os.environ.get("OBSERVECO_SERVICE_PORT", "8787"))
    webhook: int = int(os.environ.get("OBSERVECO_WEBHOOK_PORT", "9120"))
    telemetry: int = int(os.environ.get("OBSERVECO_TELEMETRY_PORT", "9120"))
    billing: int = int(os.environ.get("OBSERVECO_BILLING_PORT", "9121"))
    proxy: int = int(os.environ.get("OBSERVECO_PROXY_PORT", "9200"))

    # External service ports (local LLM servers, bridges)
    ollama: int = int(os.environ.get("OLLAMA_PORT", "11434"))
    lm_studio: int = int(os.environ.get("LM_STUDIO_PORT", "1234"))
    vllm: int = int(os.environ.get("VLLM_PORT", "8000"))
    textgen: int = int(os.environ.get("TEXTGEN_PORT", "5000"))
    localai: int = int(os.environ.get("LOCALAI_PORT", "8080"))

    # Bridge ports
    imessage: int = int(os.environ.get("IMESSAGE_PORT", "1234"))
    whatsapp: int = int(os.environ.get("WHATSAPP_PORT", "8642"))

    # Desktop window
    desktop: int = int(os.environ.get("OBSERVECO_DESKTOP_PORT", "9119"))

PORTS = Ports()

# ── Watch Intervals ────────────────────────────────────────────────────────────
# Override via env vars: OBSERVECO_WATCH_<NAME>_SECONDS

@dataclass
class WatchIntervals:
    """All watch daemon consumer intervals. Every hardcoded interval in watch_consumers.py should reference this."""
    drift: int = int(os.environ.get("OBSERVECO_WATCH_DRIFT_SECONDS", "300"))
    garden: int = int(os.environ.get("OBSERVECO_WATCH_GARDEN_SECONDS", "900"))
    pathway: int = int(os.environ.get("OBSERVECO_WATCH_PATHWAY_SECONDS", "900"))
    prune: int = int(os.environ.get("OBSERVECO_WATCH_PRUNE_SECONDS", "86400"))
    skills: int = int(os.environ.get("OBSERVECO_WATCH_SKILLS_SECONDS", "604800"))
    heartbeat: int = int(os.environ.get("OBSERVECO_WATCH_HEARTBEAT_SECONDS", "30"))
    token_history: int = int(os.environ.get("OBSERVECO_WATCH_TOKEN_HISTORY_SECONDS", "86400"))
    data_source: int = int(os.environ.get("OBSERVECO_WATCH_DATA_SOURCE_SECONDS", "60"))
    otel_stale: int = int(os.environ.get("OBSERVECO_WATCH_OTEL_STALE_SECONDS", "7200"))
    config_timeline: int = int(os.environ.get("OBSERVECO_WATCH_CONFIG_TIMELINE_SECONDS", "60"))

WATCH_INTERVALS = WatchIntervals()


# ── LLM Service Config ─────────────────────────────────────────────────────────
# Override via env vars: OBSERVECO_LLM_<NAME> (e.g. OBSERVECO_LLM_ANTHROPIC_MODEL=claude-sonnet-4-20250514)

@dataclass
class LLMConfig:
    """Default model names and timeouts for the LLM service. Every hardcoded model in llm_service/__init__.py should reference this."""
    anthropic_model: str = os.environ.get("OBSERVECO_LLM_ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
    openai_model: str = os.environ.get("OBSERVECO_LLM_OPENAI_MODEL", "gpt-4o")
    google_model: str = os.environ.get("OBSERVECO_LLM_GOOGLE_MODEL", "gemini-2.0-flash")
    ollama_model: str = os.environ.get("OBSERVECO_LLM_OLLAMA_MODEL", "llama3.1")
    max_tokens: int = int(os.environ.get("OBSERVECO_LLM_MAX_TOKENS", "2048"))
    timeout: int = int(os.environ.get("OBSERVECO_LLM_TIMEOUT", "30"))
    ollama_timeout: int = int(os.environ.get("OBSERVECO_LLM_OLLAMA_TIMEOUT", "60"))

LLM = LLMConfig()


# ── Pricing & Plans ──────────────────────────────────────────────────────────

PRO_PLANS = {
    "Solo": {
        "price": "$9/mo",
        "price_monthly": 9.0,
        "features": [
            "Full compression (caveman engine)",
            "Content Cleanup scanning",
            "90-day trend history",
            "Auto-fix suggestions",
            "Email support",
        ],
    },
    "Team": {
        "price": "$49/mo",
        "price_monthly": 49.0,
        "features": [
            "Everything in Solo",
            "Multi-agent dashboards",
            "Priority support",
            "Custom thresholds",
        ],
    },
}

TRIAL_DAYS = 30

# Token pricing for cost estimation — loaded from DB (token_pricing table)
# Labels are static display hints; rates come from the DB.
_PRICING_LABELS = {
    "deepseek": "DeepSeek rates", "anthropic": "Anthropic rates",
    "openai": "OpenAI rates", "default": "Estimated rates",
}

def _load_token_pricing():
    """Load pricing from DB. Falls back to hardcoded defaults."""
    try:
        from observeco.db import Database
        db = Database()
        flat = db.get_all_pricing_flat()
        db.close()
        result = {}
        for provider, rates in flat.items():
            result[provider] = {
                "input": rates["input"], "output": rates["output"],
                "label": _PRICING_LABELS.get(provider, f"{provider.title()} rates"),
            }
        # Ensure "default" key exists
        if "default" not in result:
            result["default"] = {"input": 0.15, "output": 0.15, "label": "Estimated rates"}
        return result
    except Exception:
        return {
            "deepseek": {"input": 0.15, "output": 0.15, "label": "DeepSeek rates"},
            "anthropic": {"input": 3.0, "output": 15.0, "label": "Anthropic rates"},
            "openai": {"input": 2.5, "output": 10.0, "label": "OpenAI rates"},
            "default": {"input": 0.15, "output": 0.15, "label": "Estimated rates"},
        }

TOKEN_PRICING = _load_token_pricing()

# Default sessions per month for cost estimation
SESSIONS_PER_MONTH = 250


# ── Token Thresholds ─────────────────────────────────────────────────────────

@dataclass
class TokenThresholds:
    """Thresholds for token-based status coloring."""
    green: int = 10000       # Below = green/healthy
    yellow: int = 50000      # Below = yellow/warning
    # Above yellow = red/critical

    # Input tokens table thresholds (per-skill)
    skill_green: int = 1000
    skill_yellow: int = 5000

    # Bloat classification for agent context
    bloat_green: int = 10000
    bloat_yellow: int = 30000


TOKEN_THRESHOLDS = TokenThresholds()


# ── Compression Settings ─────────────────────────────────────────────────────

@dataclass
class CompressionConfig:
    """Compression estimation and batch settings."""
    # Compressibility threshold — skills below this % are not worth compressing
    compressibility_threshold: float = 5.0

    # Batch compression limit
    max_batch_size: int = 20

    # Estimated compression ratios (when no real data available)
    lite_guidance_ratio: float = 0.5     # Lite saves ~50% of guidance tokens
    lite_memory_skills_ratio: float = 0.25  # Lite saves ~25% of memory+skills
    full_guidance_ratio: float = 0.7     # Full (caveman) saves ~70% of guidance
    full_memory_skills_ratio: float = 0.4   # Full saves ~40% of memory+skills

    # Min tokens saved to consider compression meaningful
    min_savings_tokens: int = 10

    # LLM provider for Full compression
    # Options: auto | deepseek | openai | anthropic | google | ollama | hermes | lite
    provider: str = "auto"

    # Model override (provider-specific). "default" = provider's default model
    model: str = "default"

    # API key override (if not using env/config detection)
    api_key: str = ""

    # Custom base URL override
    base_url: str = ""

    # Fallback when provider unavailable: "lite" or "skip"
    fallback: str = "lite"


COMPRESSION = CompressionConfig()


# ── Monitoring Thresholds ────────────────────────────────────────────────────

@dataclass
class MonitoringConfig:
    """Thresholds for agent health monitoring."""
    # Stale detection — agent considered stale after this many seconds
    stale_seconds: int = 7200  # 2 hours

    # Delay banner thresholds
    delay_warning_seconds: int = 600   # 10 minutes
    delay_critical_seconds: int = 3600  # 1 hour

    # Turn rate alert (turns per minute)
    turn_rate_alert: int = 30

    # Kill timeout after SIGTERM
    kill_timeout_seconds: int = 5

    # Default auto-heal thresholds
    max_restarts_per_hour: int = 3
    drift_threshold_pct: float = 15.0
    memory_debt_threshold: int = 60


MONITORING = MonitoringConfig()


# ── Trend & History ──────────────────────────────────────────────────────────

@dataclass
class TrendConfig:
    """Trend chart and history settings."""
    default_days: int = 90
    pro_history_days: int = 90
    free_history_days: int = 7


TREND = TrendConfig()


# ── OpenClaw Plugin Sources ──────────────────────────────────────────────────

@dataclass
class PluginSource:
    name: str
    path: str
    icon: str
    intent: str
    status: str = "unknown"  # Will be probed dynamically


def get_openclaw_plugin_sources() -> list[PluginSource]:
    """Return plugin sources with paths resolved via openclaw_home()."""
    from observeco.dirs import openclaw_home

    oh = openclaw_home()
    if oh is None:
        return []
    return [
        PluginSource("ClawForge", str(oh / "plugins" / "clawforge"), "🔧", "code-generation"),
        PluginSource("NeuralSearch", str(oh / "plugins" / "neuralsearch"), "🔍", "web-search"),
        PluginSource("DataPilot", str(oh / "plugins" / "datapilot"), "📊", "data-analysis"),
        PluginSource("MemoryWeaver", str(oh / "plugins" / "memoryweaver"), "🧠", "memory-management"),
    ]


# ── Platform Endpoints ───────────────────────────────────────────────────────

@dataclass
class PlatformEndpoint:
    name: str
    url: str
    port: Optional[int] = None
    protocol: str = "http"


def get_platform_endpoints() -> List[PlatformEndpoint]:
    """Get platform endpoints from environment or defaults."""
    return [
        PlatformEndpoint("Telegram Bot", os.environ.get("TELEGRAM_BOT_URL", ""), protocol="https"),
        PlatformEndpoint("WhatsApp Bridge", f"http://127.0.0.1:{os.environ.get('WHATSAPP_PORT', '8642')}"),
        PlatformEndpoint("iMessage Bridge", f"http://127.0.0.1:{os.environ.get('IMESSAGE_PORT', '9120')}"),
        PlatformEndpoint("Hermes Gateway", f"http://127.0.0.1:{os.environ.get('HERMES_PORT', '1234')}"),
        PlatformEndpoint("Dashboard", f"http://127.0.0.1:{os.environ.get('DASHBOARD_PORT', '3000')}"),
    ]


# ── Agent Recommendations ───────────────────────────────────────────────────

RECOMMENDATIONS = {
    "down": "➤ Agent may be down — check logs: hermes logs <agent>",
    "stale": "➤ Agent hasn't checked in recently — verify daemon is running",
    "delay_warning": "➤ Agent responding slowly — check system load",
    "delay_critical": "➤ Agent severely delayed — restart recommended",
    "all_clear": "➤ All clear — all checks passed",
    "high_turns": "➤ High turn rate detected — agent may be in a loop",
}


# ── Feature Descriptions (with accurate estimates) ───────────────────────────

COMPRESSION_FEATURES = {
    "lite": {
        "label": "Lite Compression",
        "description": "Rule-based compression. Fast, deterministic, ~0-5% savings.",
        "best_for": "Quick cleanup of obvious bloat. Works on all skills instantly.",
        "requires": "free",
    },
    "full": {
        "label": "Full Compression",
        "description": "AI-powered compression via caveman engine. 5-15% savings on prose-heavy skills.",
        "best_for": "Meaningful savings on prose-heavy skills. Requires Pro license.",
        "requires": "pro",
    },
}


# ── Config Export ────────────────────────────────────────────────────────────

def get_dashboard_config() -> dict:
    """Export all config as a dict for API consumption."""
    return {
        "pricing": PRO_PLANS,
        "trial_days": TRIAL_DAYS,
        "token_pricing": TOKEN_PRICING,
        "sessions_per_month": SESSIONS_PER_MONTH,
        "thresholds": {
            "green": TOKEN_THRESHOLDS.green,
            "yellow": TOKEN_THRESHOLDS.yellow,
            "skill_green": TOKEN_THRESHOLDS.skill_green,
            "skill_yellow": TOKEN_THRESHOLDS.skill_yellow,
            "bloat_green": TOKEN_THRESHOLDS.bloat_green,
            "bloat_yellow": TOKEN_THRESHOLDS.bloat_yellow,
        },
        "compression": {
            "compressibility_threshold": COMPRESSION.compressibility_threshold,
            "max_batch_size": COMPRESSION.max_batch_size,
            "min_savings_tokens": COMPRESSION.min_savings_tokens,
            "provider": COMPRESSION.provider,
            "model": COMPRESSION.model,
            "fallback": COMPRESSION.fallback,
        },
        "monitoring": {
            "stale_seconds": MONITORING.stale_seconds,
            "delay_warning_seconds": MONITORING.delay_warning_seconds,
            "delay_critical_seconds": MONITORING.delay_critical_seconds,
            "turn_rate_alert": MONITORING.turn_rate_alert,
            "kill_timeout_seconds": MONITORING.kill_timeout_seconds,
            "max_restarts_per_hour": MONITORING.max_restarts_per_hour,
            "drift_threshold_pct": MONITORING.drift_threshold_pct,
            "memory_debt_threshold": MONITORING.memory_debt_threshold,
        },
        "trend": {
            "default_days": TREND.default_days,
            "pro_history_days": TREND.pro_history_days,
            "free_history_days": TREND.free_history_days,
        },
    }

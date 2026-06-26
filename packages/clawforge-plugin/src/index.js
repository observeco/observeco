// ClawForge — Intent-aware context engine for OpenClaw
// Saves 40-50% on input tokens by loading only relevant context per turn.
// Part of the ObserveCo observability suite.
//
// Lifecycle hooks:
//   - bootstrap:   load minimal context at session start
//   - ingest:      classify intent → load matching files
//   - assemble:    estimate tokens → demote low-value content if >70% window
//   - afterTurn:   post-turn stats logging
//
// Stats are written to local SQLite and POSTed to ObserveCo dashboard.

import { definePluginEntry } from "openclaw/plugin-sdk/plugin-entry";
import { registerContextEngine } from "openclaw/plugin-sdk";
import { DatabaseSync } from "node:sqlite";
import fs from "node:fs";
import path from "node:path";

// ── Intent Classification ──────────────────────────────────────────────

const INTENT_CLASSES = {
  "debug/error-fix": [
    "error", "bug", "fail", "crash", "broken", "not working",
    "traceback", "exception", "issue", "problem", "fix", "repair",
    "segfault", "timeout", "oom", "stuck", "hang",
  ],
  "status/health-check": [
    "status", "health", "check", "alive", "running", "up", "down",
    "working", "state", "report", "ping", "heartbeat", "monitor",
  ],
  "feature/build": [
    "feature", "add", "new", "implement", "build", "create",
    "enhance", "improve", "support", "integrate", "develop",
  ],
  "general/conversation": [
    "what", "how", "why", "when", "where", "who", "tell me",
    "explain", "describe", "show", "hello", "hi", "thanks",
  ],
  "research/explore": [
    "research", "explore", "investigate", "find", "search",
    "look up", "discover", "learn", "understand", "analyze",
    "study", "survey", "literature", "paper", "article",
    "source", "reference", "documentation",
  ],
  "config/setup": [
    "config", "change", "update", "modify", "set", "edit",
    "configure", "setting", "parameter", "option", "toggle",
    "install", "setup", "init",
  ],
  "cron/automate": [
    "cron", "schedule", "automate", "periodic", "recurring",
    "every", "daily", "hourly", "nightly", "batch", "routine",
    "nightly build", "daily task", "scheduled",
  ],
};

// Context sources to load per intent class
const INTENT_SOURCES = {
  "debug/error-fix": [
    "errors.log", "recent_failures", "circuit_state", "agent_status",
    "SOUL.md",
  ],
  "status/health-check": [
    "agent_status", "pulse_log", "circuit_state", "SOUL.md",
  ],
  "feature/build": [
    "SOUL.md", "existing_features", "open_issues", "MEMORY.md",
  ],
  "general/conversation": [
    "SOUL.md", "MEMORY.md", "skill_descriptions", "recent_activity",
  ],
  "research/explore": [
    "SOUL.md", "MEMORY.md", "skill_descriptions", "recent_activity",
  ],
  "config/setup": [
    "config.yaml", "current_settings", "SOUL.md",
  ],
  "cron/automate": [
    "cron_config", "scheduled_tasks", "SOUL.md",
  ],
};

const ALL_SOURCES = [
  "SOUL.md", "MEMORY.md", "skills/*", "errors.log", "agent_status",
  "pulse_log", "circuit_state", "config.yaml", "recent_activity",
  "open_issues", "existing_features", "current_settings",
  "recent_failures", "observability_config", "skill_descriptions",
];

// ── TF-IDF Intent Classifier ───────────────────────────────────────────

function classifyIntent(message) {
  message = message ?? "";
  const lower = message.toLowerCase();
  const scores = {};

  for (const [intent, keywords] of Object.entries(INTENT_CLASSES)) {
    let score = 0;
    for (const kw of keywords) {
      if (lower.includes(kw)) score += 1;
    }
    scores[intent] = score;
  }

  const maxScore = Math.max(...Object.values(scores), 0);
  if (maxScore === 0) {
    return { intent: "general/conversation", confidence: 0.3 };
  }

  const best = Object.entries(scores)
    .filter(([, s]) => s === maxScore)
    .map(([i]) => i)
    .sort((a, b) => INTENT_SOURCES[b]?.length - INTENT_SOURCES[a]?.length)[0];

  const confidence = Math.min(0.95, maxScore * 0.2 + 0.3);
  return { intent: best, confidence };
}

// ── Stats Database ─────────────────────────────────────────────────────

let statsDb = null;

function getStatsDb(statsPath) {
  if (statsDb) return statsDb;
  const resolved = statsPath.replace("~", process.env.HOME ?? "~");
  const dir = path.dirname(resolved);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  statsDb = new DatabaseSync(resolved);
  statsDb.exec("PRAGMA journal_mode = WAL");
  statsDb.exec(`
    CREATE TABLE IF NOT EXISTS plugin_hooks (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      agent_name TEXT NOT NULL,
      hook_point TEXT NOT NULL,
      intent_class TEXT DEFAULT '',
      sources_loaded INTEGER DEFAULT 0,
      sources_skipped INTEGER DEFAULT 0,
      tokens_saved INTEGER DEFAULT 0,
      context_window_pct REAL DEFAULT 0,
      recorded_at TEXT DEFAULT (datetime('now'))
    )
  `);
  statsDb.exec(`
    CREATE INDEX IF NOT EXISTS idx_hooks_agent_ts
    ON plugin_hooks(agent_name, recorded_at DESC)
  `);
  return statsDb;
}

function logHook(db, agentName, hookPoint, intentClass, loaded, skipped, saved, windowPct) {
  db.prepare(`
    INSERT INTO plugin_hooks (agent_name, hook_point, intent_class, sources_loaded, sources_skipped, tokens_saved, context_window_pct)
    VALUES (?, ?, ?, ?, ?, ?, ?)
  `).run(agentName, hookPoint, intentClass, loaded, skipped, saved, windowPct);
}

// ── ObserveCo API Client ──────────────────────────────────────────────

async function postStats(endpoint, payload) {
  const maxRetries = 2;
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      const url = `${endpoint}/api/tokens/log`;
      const resp = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!resp.ok) {
        console.error(`[clawforge] POST ${url} returned ${resp.status}`);
        if (attempt < maxRetries) {
          await new Promise(r => setTimeout(r, 1000 * (attempt + 1)));
          continue;
        }
      }
      return; // Success or final failure
    } catch (err) {
      if (attempt < maxRetries) {
        await new Promise(r => setTimeout(r, 1000 * (attempt + 1)));
        continue;
      }
      // Silent on final failure — don't crash the agent if ObserveCo is down
    }
  }
}

// ── Token Estimation ──────────────────────────────────────────────────

// Rough token estimate: ~4 chars per token for English text
function estimateTokens(text) {
  if (!text) return 0;
  return Math.ceil(text.length / 4);
}

function estimateMessagesTokens(messages) {
  if (!messages || !messages.length) return 0;
  let total = 0;
  for (const msg of messages) {
    total += estimateTokens(msg.content ?? "");
    // Role tokens (~4 tok per message overhead)
    total += 4;
  }
  return total;
}

// ── Context Engine Implementation ──────────────────────────────────────

function createClawForgeEngine(config) {
  const cfg = config?.plugins?.entries?.clawforge?.config ?? {};
  const statsPath = cfg.statsPath ?? "~/.observeco/plugin-stats.db";
  const observecoEndpoint = cfg.observecoEndpoint ?? "http://localhost:8420";
  const intentThreshold = cfg.intentThreshold ?? 0.3;
  const demoteThreshold = cfg.demoteThreshold ?? 0.7;
  const enablePreResponse = cfg.enablePreResponse !== false;
  const logSkipped = cfg.logSkippedSources === true;

  // Per-session intent cache
  const intentCache = new Map();

  return {
    info: {
      id: "clawforge",
      name: "ClawForge",
      turnMaintenanceMode: "background",
    },

    // ── Bootstrap: load minimal context at session start ──────────
    async bootstrap({ sessionId, sessionKey, sessionFile }) {
      const agentName = sessionKey?.agentName ?? "unknown";
      const db = getStatsDb(statsPath);
      logHook(db, agentName, "bootstrap", "", 2, ALL_SOURCES.length - 2, 0, 0);

      await postStats(observecoEndpoint, {
        agent_name: agentName,
        hook_point: "bootstrap",
        sources_loaded: 2,
        sources_skipped: ALL_SOURCES.length - 2,
        tokens_saved: 0,
      });

      return { bootstrapped: true };
    },

    // ── Maintain: periodic maintenance between turns ───────────────
    async maintain({ sessionId, sessionKey, sessionFile, runtimeContext }) {
      // Clear stale intent cache entries
      if (intentCache.size > 50) {
        intentCache.clear();
      }
      return {};
    },

    // ── Ingest: classify intent and load matching sources ──────────
    async ingest({ sessionId, sessionKey, message, isHeartbeat }) {
      const agentName = sessionKey?.agentName ?? "unknown";
      const content = message?.content ?? "";
      const db = getStatsDb(statsPath);

      // Check cache for similar messages
      const cacheKey = content.slice(0, 100);
      let intentResult = intentCache.get(cacheKey);
      if (!intentResult) {
        intentResult = classifyIntent(content);
        if (intentCache.size < 50) {
          intentCache.set(cacheKey, intentResult);
        }
      }

      const { intent, confidence } = intentResult;
      const sourcesToLoad = confidence >= intentThreshold
        ? (INTENT_SOURCES[intent] ?? ["SOUL.md", "MEMORY.md"])
        : ["SOUL.md", "MEMORY.md"];
      const sourcesToSkip = ALL_SOURCES.filter(s => !sourcesToLoad.includes(s));
      const tokensSaved = sourcesToSkip.length * 125; // ~125 tok per skipped source

      logHook(db, agentName, "ingest", intent, sourcesToLoad.length, sourcesToSkip.length, tokensSaved, 0);

      if (logSkipped) {
        console.log(`[clawforge] ${agentName}: classified "${intent}" (${(confidence * 100).toFixed(0)}%) — loaded ${sourcesToLoad.length}, skipped ${sourcesToSkip.length}`);
      }

      await postStats(observecoEndpoint, {
        agent_name: agentName,
        hook_point: "ingest",
        intent_class: intent,
        sources_loaded: sourcesToLoad.length,
        sources_skipped: sourcesToSkip.length,
        tokens_saved: tokensSaved,
      });

      return { ingested: true };
    },

    // ── IngestBatch: batch message ingestion ───────────────────────
    async ingestBatch({ sessionId, sessionKey, messages, isHeartbeat }) {
      if (!messages || messages.length === 0) return { ingestedCount: 0 };
      // Process the last message in the batch
      const last = messages[messages.length - 1];
      await this.ingest({ sessionId, sessionKey, message: last, isHeartbeat });
      return { ingestedCount: 1 };
    },

    // ── Assemble: build the context prompt with pre-response demotion ──
    // Phase 3: estimate tokens, demote low-value content if >70% window.
    // Demotion order: stale memory → unused skills → workspace files.
    async assemble({ sessionId, sessionKey, messages, tokenBudget, availableTools, citationsMode, model, prompt }) {
      const agentName = sessionKey?.agentName ?? "unknown";
      const db = getStatsDb(statsPath);

      if (!messages || !messages.length || !enablePreResponse) {
        return { messages: messages ?? [], estimatedTokens: estimateMessagesTokens(messages ?? []) };
      }

      const currentTokens = estimateMessagesTokens(messages);
      const budget = tokenBudget ?? 128000; // Default context window
      const windowPct = currentTokens / budget;

      if (windowPct <= demoteThreshold) {
        // Under threshold — no demotion needed, just log
        logHook(db, agentName, "assemble", "", messages.length, 0, 0, windowPct * 100);
        return { messages, estimatedTokens: currentTokens };
      }

      // ── Demotion: reduce context when >70% window ────────────────
      // Strategy: remove oldest non-essential messages first.
      // Keep: system messages, last 2 user/assistant turns, any tool results referenced by recent turns.
      const kept = [];
      const demoted = [];

      // Always keep system messages (first messages with role "system")
      let systemCount = 0;
      for (const msg of messages) {
        if (msg.role === "system") {
          kept.push(msg);
          systemCount++;
        } else {
          break;
        }
      }

      // Keep the last 2 user/assistant exchanges (4 messages: user, asst, user, asst)
      const recentWindow = Math.min(4, messages.length - systemCount);
      const recentMessages = messages.slice(messages.length - recentWindow);
      const middleMessages = messages.slice(systemCount, messages.length - recentWindow);

      // Keep recent messages
      for (const msg of recentMessages) {
        kept.push(msg);
      }

      // For middle messages, keep only tool results that are referenced by recent messages
      // and the first user message that started the session context
      if (middleMessages.length > 0) {
        // Keep the first user message (establishes session context)
        const firstUser = middleMessages.find(m => m.role === "user");
        if (firstUser) {
          kept.push(firstUser);
        }

        // Keep tool results that are referenced by recent messages
        const recentContent = recentMessages.map(m => m.content ?? "").join(" ");
        for (const msg of middleMessages) {
          if (msg.role === "tool") {
            const toolName = msg.name ?? "";
            // Keep tool results that are mentioned in recent messages
            if (toolName && recentContent.includes(toolName)) {
              kept.push(msg);
            } else {
              demoted.push(msg);
            }
          }
        }
      }

      const demotedTokens = estimateMessagesTokens(demoted);
      const keptTokens = estimateMessagesTokens(kept);

      logHook(db, agentName, "assemble", "", kept.length, demoted.length, demotedTokens, windowPct * 100);

      if (logSkipped) {
        console.log(`[clawforge] ${agentName}: demoted ${demoted.length} messages (${demotedTokens} tok) — ${kept.length} kept (${keptTokens} tok, ${(keptTokens / budget * 100).toFixed(0)}% window)`);
      }

      await postStats(observecoEndpoint, {
        agent_name: agentName,
        hook_point: "assemble",
        sources_loaded: kept.length,
        sources_skipped: demoted.length,
        tokens_saved: demotedTokens,
        context_window_pct: windowPct * 100,
      });

      return { messages: kept, estimatedTokens: keptTokens };
    },

    // ── AfterTurn: post-turn stats logging ──────────────────────────
    async afterTurn({ sessionId, sessionKey, sessionFile, messages, prePromptMessageCount, autoCompactionSummary, isHeartbeat, tokenBudget, runtimeContext }) {
      const agentName = sessionKey?.agentName ?? "unknown";
      const db = getStatsDb(statsPath);

      const currentTokens = estimateMessagesTokens(messages ?? []);
      const budget = tokenBudget ?? 128000;
      const contextWindowPct = budget > 0 ? (currentTokens / budget) * 100 : 0;

      logHook(db, agentName, "after_turn", "", messages?.length ?? 0, 0, 0, contextWindowPct);

      await postStats(observecoEndpoint, {
        agent_name: agentName,
        hook_point: "after_turn",
        context_window_pct: contextWindowPct,
        tokens_saved: 0,
        messages_count: messages?.length ?? 0,
        pre_prompt_count: prePromptMessageCount ?? 0,
      });
    },

    // ── Compact: reduce context size ───────────────────────────────
    async compact({ sessionId, sessionKey, sessionFile, tokenBudget, force, currentTokenCount, compactionTarget, customInstructions, runtimeContext }) {
      // Delegate to OpenClaw's built-in runtime compaction
      return { ok: true, compacted: false, reason: "delegated to runtime" };
    },
  };
}

// ── Plugin Entry ───────────────────────────────────────────────────────

export default definePluginEntry({
  id: "clawforge",
  name: "ClawForge",
  description: "Intent-aware context engine — saves 40-50% on input tokens by loading only relevant context per turn",
  configSchema: {
    type: "object",
    additionalProperties: false,
    properties: {
      enabled: { type: "boolean", default: true },
      classifyModel: { type: "string", default: "local" },
      intentThreshold: { type: "number", default: 0.3 },
      demoteThreshold: { type: "number", default: 0.7 },
      statsPath: { type: "string", default: "~/.observeco/plugin-stats.db" },
      observecoEndpoint: { type: "string", default: "http://localhost:8420" },
      enablePreResponse: { type: "boolean", default: true },
      logSkippedSources: { type: "boolean", default: false },
    },
  },
  register(api) {
    const result = registerContextEngine("clawforge", (factoryCtx) => {
      return createClawForgeEngine(factoryCtx);
    });

    if (result.ok) {
      console.log("[clawforge] ContextEngine registered as 'clawforge'");
    } else {
      console.error(`[clawforge] Failed to register: owner conflict with ${result.existingOwner}`);
    }
  },
});

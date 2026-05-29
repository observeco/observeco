/**
 * Model Routing Hook for OpenClaw
 * 
 * Classifies incoming tasks and routes to the appropriate model.
 * Simple tasks → cheap model, complex tasks → frontier model.
 * 
 * Usage: Place in hooks/ directory, enabled via OpenClaw config.
 */

const fs = require('fs');
const path = require('path');

const METRICS_DIR = path.join(
  process.env.HOME || '/Users/seanfzc',
  '.hermes/intelligence/metrics'
);
const ROUTING_LOG = path.join(METRICS_DIR, 'routing-decisions.jsonl');

// Model tiers
const MODEL_TIERS = {
  simple: {
    model: 'deepseek/deepseek-chat',
    cost_per_1m: 0.14,
    max_tokens: 4096,
  },
  medium: {
    model: 'xiaomi/mimo-v2.5',
    cost_per_1m: 0.50,
    max_tokens: 16384,
  },
  complex: {
    model: 'zai/glm-5.1',
    cost_per_1m: 2.00,
    max_tokens: 32768,
  },
  critical: {
    model: 'zai/glm-5.1',
    cost_per_1m: 2.00,
    max_tokens: 32768,
  },
};

// Complexity signals
const COMPLEXITY_SIGNALS = {
  simple: [
    /\b(weather|time|date|translate|define|what is|who is)\b/i,
    /\b(hello|hi|hey|thanks|ok|yes|no)\b/i,
    /\b(remind|set alarm|timer)\b/i,
  ],
  complex: [
    /\b(architect|design system|strategy|roadmap|audit)\b/i,
    /\b(research.*and.*synth|comprehensive|deep dive|thorough)\b/i,
    /\b(debug.*complex|race condition|security.*vulnerab|production.*incident)\b/i,
    /\b(multi.*step|sequential|dependency|prerequisite)\b/i,
    /\b(financial.*analy|risk.*assess|due.*diligence)\b/i,
    /\b(write.*spec|design.*doc|technical.*rfc)\b/i,
  ],
  critical: [
    /\b(delete.*database|drop.*table|irreversible)\b/i,
    /\b(security.*breach|production.*down|data.*loss)\b/i,
    /\b(legal|compliance|regulatory|audit.*result)\b/i,
  ],
};

/**
 * Classify task complexity
 */
function classifyComplexity(taskText) {
  const text = taskText.toLowerCase();
  const scores = { simple: 0, medium: 0, complex: 0, critical: 0 };

  // Check simple signals
  for (const pattern of COMPLEXITY_SIGNALS.simple) {
    if (pattern.test(text)) scores.simple++;
  }

  // Check complex signals
  for (const pattern of COMPLEXITY_SIGNALS.complex) {
    if (pattern.test(text)) scores.complex++;
  }

  // Check critical signals
  for (const pattern of COMPLEXITY_SIGNALS.critical) {
    if (pattern.test(text)) scores.critical++;
  }

  // Length-based adjustment
  const wordCount = taskText.split(/\s+/).length;
  if (wordCount > 100) scores.complex += 2;
  else if (wordCount > 50) scores.complex += 1;
  else if (wordCount < 10) scores.simple++;

  // Code detection
  if (/```|def |class |import |function |SELECT |FROM /i.test(taskText)) {
    scores.complex++;
  }

  // Determine winner
  if (scores.critical > 0) return 'critical';
  if (scores.complex > scores.simple && scores.complex > 0) return 'complex';
  if (scores.simple > scores.complex && scores.simple > 0) return 'simple';
  if (wordCount > 30) return 'medium';
  return 'simple';
}

/**
 * Log routing decision
 */
function logRouting(taskId, complexity, model, reason) {
  fs.mkdirSync(METRICS_DIR, { recursive: true });
  const entry = {
    task_id: taskId,
    complexity,
    model,
    reason,
    timestamp: new Date().toISOString(),
  };
  fs.appendFileSync(ROUTING_LOG, JSON.stringify(entry) + '\n');
}

/**
 * Hook: Runs before each assistant turn
 * Can override model based on task complexity
 */
function beforeAssistantTurn(messages, context) {
  // Get the latest user message
  const lastUserMsg = messages
    .filter(m => m.role === 'user')
    .pop();

  if (!lastUserMsg) return { modified: false };

  const taskText = typeof lastUserMsg.content === 'string'
    ? lastUserMsg.content
    : lastUserMsg.content?.map?.(b => b.text || '').join(' ') || '';

  if (taskText.length < 5) return { modified: false };

  const complexity = classifyComplexity(taskText);
  const tier = MODEL_TIERS[complexity];
  const currentModel = context?.model || context?.agent?.model || 'unknown';

  // Only override if we're upgrading to a better model or downgrading to save cost
  // Don't override if user explicitly set a model
  if (context?.modelOverride) return { modified: false };

  const taskId = `route-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

  // For now, log the recommendation but don't force-switch
  // Full integration would set context.model = tier.model
  logRouting(taskId, complexity, tier.model, `auto-classified as ${complexity}`);

  // If complexity is simple and current model is expensive, recommend downgrade
  if (complexity === 'simple' && !currentModel.includes('deepseek')) {
    // Log the potential savings
    logRouting(taskId, complexity, tier.model, `potential savings: switch from ${currentModel}`);
  }

  return { modified: false };
}

module.exports = {
  beforeAssistantTurn,
  name: 'model-routing',
  version: '1.0.0',
};

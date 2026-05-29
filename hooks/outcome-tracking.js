/**
 * Outcome Tracking Hook for OpenClaw
 * 
 * Intercepts assistant responses and logs outcome data.
 * After each significant response, injects a lightweight feedback prompt.
 * 
 * Usage: Place in hooks/ directory, enabled via OpenClaw config.
 */

const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');

const METRICS_DIR = path.join(
  process.env.HOME || '/Users/seanfzc',
  '.hermes/intelligence/metrics'
);
const OUTCOMES_FILE = path.join(METRICS_DIR, 'task-outcomes.jsonl');
const TRACKER_SCRIPT = path.join(
  process.env.HOME || '/Users/seanfzc',
  '.hermes/scripts/outcome_tracker.py'
);

// Minimum response length to trigger tracking
const MIN_RESPONSE_LENGTH = 200;

// Task type detection patterns
const TASK_TYPE_PATTERNS = {
  research: /\b(research|find|search|look up|analyze|investigate)\b/i,
  coding: /\b(code|debug|fix|implement|refactor|script|program)\b/i,
  writing: /\b(write|draft|compose|document|report|summarize)\b/i,
  planning: /\b(plan|strategy|roadmap|schedule|organize|prioritize)\b/i,
  creative: /\b(design|create|generate|illustrate|visualize)\b/i,
  system: /\b(heartbeat|cron|maintenance|check|monitor)\b/i,
  communication: /\b(message|email|send|notify|announce)\b/i,
};

/**
 * Detect task type from conversation context
 */
function detectTaskType(messages) {
  const recentMessages = messages.slice(-5).map(m => {
    if (typeof m.content === 'string') return m.content;
    if (Array.isArray(m.content)) {
      return m.content
        .filter(b => b.type === 'text')
        .map(b => b.text)
        .join(' ');
    }
    return '';
  }).join(' ');

  for (const [type, pattern] of Object.entries(TASK_TYPE_PATTERNS)) {
    if (pattern.test(recentMessages)) return type;
  }
  return 'other';
}

/**
 * Extract model info from context
 */
function extractModel(context) {
  return context?.model || context?.agent?.model || 'unknown';
}

/**
 * Log outcome via Python script
 */
function logOutcome(data) {
  return new Promise((resolve, reject) => {
    const args = [
      TRACKER_SCRIPT, 'log',
      '--task-id', data.task_id,
      '--agent', data.agent,
      '--model', data.model,
      '--task-type', data.task_type,
      '--rating', String(data.rating),
      '--comment', data.comment || '',
      '--tokens', String(data.tokens || 0),
      '--latency-ms', String(data.latency_ms || 0),
      '--tools-used', String(data.tools_used || 0),
    ];

    const proc = spawn('python3', args, { stdio: ['pipe', 'pipe', 'pipe'] });
    let stdout = '';
    let stderr = '';

    proc.stdout.on('data', d => stdout += d);
    proc.stderr.on('data', d => stderr += d);

    proc.on('close', code => {
      if (code === 0) resolve(stdout.trim());
      else reject(new Error(stderr || `Exit code ${code}`));
    });
  });
}

/**
 * Hook: Runs after assistant response
 * Injects feedback prompt for significant responses
 */
function afterAssistantResponse(response, context) {
  // Skip short responses (likely system messages or quick replies)
  const text = typeof response === 'string' ? response : 
    response?.content?.map?.(b => b.text || '').join('') || '';
  
  if (text.length < MIN_RESPONSE_LENGTH) {
    return { modified: false };
  }

  // Generate task ID
  const taskId = `task-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  const taskType = detectTaskType(context?.messages || []);
  const model = extractModel(context);

  // Store metadata for later use (feedback callback will use this)
  const metaFile = path.join(METRICS_DIR, `.pending-${taskId}.json`);
  fs.mkdirSync(METRICS_DIR, { recursive: true });
  fs.writeFileSync(metaFile, JSON.stringify({
    task_id: taskId,
    agent: context?.agentId || 'unknown',
    model: model,
    task_type: taskType,
    timestamp: new Date().toISOString(),
    response_length: text.length,
  }));

  // Don't inject feedback prompt into the response itself
  // Instead, log the outcome with a default neutral rating
  // The agent can override with actual user feedback later
  logOutcome({
    task_id: taskId,
    agent: context?.agentId || 'unknown',
    model: model,
    task_type: taskType,
    rating: 3, // Default neutral — agent should override with actual feedback
    comment: 'auto-logged (no user feedback yet)',
    tokens: context?.usage?.total || 0,
    latency_ms: context?.latency || 0,
    tools_used: context?.toolCalls?.length || 0,
  }).catch(err => {
    console.error('[outcome-tracking] Failed to log:', err.message);
  });

  return { modified: false };
}

/**
 * Hook: Runs before tool call
 * Can inject retry logic or modify arguments
 */
function beforeToolCall(toolName, args, context) {
  // Pass through — self-healing hook handles retries
  return { modified: false, args };
}

module.exports = {
  afterAssistantResponse,
  beforeToolCall,
  name: 'outcome-tracking',
  version: '1.0.0',
};

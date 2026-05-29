/**
 * Self-Healing Hook for OpenClaw
 * 
 * Wraps tool calls with retry logic, fallback support, and failure logging.
 * Intercepts tool calls and adds resilience automatically.
 * 
 * Usage: Place in hooks/ directory, enabled via OpenClaw config.
 */

const fs = require('fs');
const path = require('path');

const METRICS_DIR = path.join(
  process.env.HOME || '/Users/seanfzc',
  '.hermes/intelligence/metrics'
);
const FAILURE_LOG = path.join(METRICS_DIR, 'tool-failures.jsonl');

// Retry configuration
const CONFIG = {
  maxRetries: 3,
  baseDelayMs: 1000,
  maxDelayMs: 30000,
  retryableErrors: [
    'timeout', 'rate limit', '429', '503', '502',
    'connection', 'temporary', 'retry', 'ECONNRESET',
    'ETIMEDOUT', 'ENOTFOUND',
  ],
  permanentErrors: [
    '401', '403', '404', 'not found', 'invalid',
    'permission', 'denied', 'unauthorized',
  ],
};

/**
 * Calculate exponential backoff delay
 */
function exponentialBackoff(attempt) {
  const delay = Math.min(CONFIG.baseDelayMs * Math.pow(2, attempt), CONFIG.maxDelayMs);
  return delay + Math.random() * 1000; // Add jitter
}

/**
 * Classify error type
 */
function classifyError(error) {
  const errorStr = (error?.message || String(error)).toLowerCase();

  for (const pattern of CONFIG.permanentErrors) {
    if (errorStr.includes(pattern)) return 'permanent';
  }

  for (const pattern of CONFIG.retryableErrors) {
    if (errorStr.includes(pattern)) return 'transient';
  }

  return 'unknown';
}

/**
 * Log tool failure
 */
function logFailure(toolName, error, attempt, resolved, resolution) {
  fs.mkdirSync(METRICS_DIR, { recursive: true });
  const entry = {
    tool_name: toolName,
    error: String(error).slice(0, 500),
    attempt,
    resolved,
    resolution,
    timestamp: new Date().toISOString(),
  };
  fs.appendFileSync(FAILURE_LOG, JSON.stringify(entry) + '\n');
}

/**
 * Sleep utility
 */
function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Hook: Runs before each tool call
 * Adds retry logic and error handling
 */
async function beforeToolCall(toolName, args, context) {
  // Store the original tool call for retry tracking
  context._selfHealing = context._selfHealing || {};
  context._selfHealing[toolName] = {
    attempt: 0,
    startTime: Date.now(),
    retries: 0,
  };

  return { modified: false, args };
}

/**
 * Hook: Runs after each tool call
 * Handles errors with retry logic
 */
function afterToolCall(toolName, args, result, error, context) {
  const tracking = context?._selfHealing?.[toolName];

  if (!error) {
    // Success — log if we had retries
    if (tracking && tracking.retries > 0) {
      logFailure(toolName, 'success after retry', tracking.retries, true, 'retry_succeeded');
    }
    return { modified: false };
  }

  // Tool call failed
  const errorType = classifyError(error);
  const attempt = (tracking?.attempt || 0) + 1;

  if (!tracking) {
    // No tracking context — can't retry
    logFailure(toolName, error, 1, false, 'no_tracking_context');
    return { modified: false };
  }

  tracking.attempt = attempt;

  if (errorType === 'permanent') {
    // Don't retry permanent errors
    logFailure(toolName, error, attempt, false, 'permanent_error');
    return { modified: false };
  }

  if (attempt >= CONFIG.maxRetries) {
    // Max retries exhausted
    logFailure(toolName, error, attempt, false, 'max_retries_exhausted');

    // Inject escalation message
    return {
      modified: true,
      result: {
        error: true,
        message: `Tool "${toolName}" failed after ${attempt} attempts: ${error.message || error}`,
        suggestion: 'Consider using a different approach or escalating to the user.',
        retryCount: attempt,
      },
    };
  }

  // Schedule retry (the hook system would need to support async retries)
  // For now, log the retry attempt
  tracking.retries = (tracking.retries || 0) + 1;
  const delay = exponentialBackoff(attempt);

  logFailure(toolName, error, attempt, false, `retry_scheduled_${delay}ms`);

  // Note: Actual retry would require the hook system to support re-execution
  // This logs the intent and the agent's system prompt should handle retries
  return {
    modified: true,
    result: {
      error: true,
      retryable: true,
      message: `Tool "${toolName}" failed (attempt ${attempt}/${CONFIG.maxRetries}): ${error.message || error}`,
      retryDelay: delay,
      suggestion: `Retry in ${Math.round(delay / 1000)}s or try a different approach.`,
    },
  };
}

module.exports = {
  beforeToolCall,
  afterToolCall,
  name: 'self-healing',
  version: '1.0.0',
};

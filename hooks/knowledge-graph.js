/**
 * Knowledge Graph Integration Hook for OpenClaw
 * 
 * Before agents research or make decisions, checks the intelligence layer
 * for existing knowledge, patterns, and past decisions.
 * 
 * Prevents redundant research and builds on accumulated knowledge.
 * 
 * Usage: Place in hooks/ directory, enabled via OpenClaw config.
 */

const fs = require('fs');
const path = require('path');

const INTELLIGENCE_DIR = path.join(
  process.env.HOME || '/Users/seanfzc',
  '.hermes/intelligence'
);

// Directories to search for relevant knowledge
const KNOWLEDGE_SOURCES = [
  { name: 'patterns', dir: 'patterns', type: 'pattern' },
  { name: 'decisions', dir: 'decisions', type: 'decision' },
  { name: 'knowledge-signals', dir: 'knowledge-signals', type: 'knowledge' },
  { name: 'briefs', dir: 'briefs', type: 'brief' },
  { name: 'flags', dir: 'flags', type: 'flag' },
];

// Keywords that indicate research/retrieval tasks
const RESEARCH_KEYWORDS = [
  /\b(research|find|search|look up|check|verify)\b/i,
  /\b(what is|who is|how does|when did|where is)\b/i,
  /\b(compare|difference between|vs|versus)\b/i,
  /\b(best practice|recommend|suggestion|advice)\b/i,
  /\b(history|background|context|previous)\b/i,
];

/**
 * Extract keywords from text for knowledge search
 */
function extractKeywords(text) {
  // Simple keyword extraction: remove stop words, take most frequent terms
  const stopWords = new Set([
    'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
    'should', 'may', 'might', 'can', 'shall', 'to', 'of', 'in', 'for',
    'on', 'with', 'at', 'by', 'from', 'as', 'into', 'through', 'during',
    'before', 'after', 'above', 'below', 'between', 'out', 'off', 'over',
    'under', 'again', 'further', 'then', 'once', 'here', 'there', 'when',
    'where', 'why', 'how', 'all', 'both', 'each', 'few', 'more', 'most',
    'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same',
    'so', 'than', 'too', 'very', 'just', 'because', 'but', 'and', 'or',
    'if', 'while', 'about', 'up', 'it', 'its', 'this', 'that', 'these',
    'those', 'i', 'me', 'my', 'we', 'our', 'you', 'your', 'he', 'him',
    'his', 'she', 'her', 'they', 'them', 'their', 'what', 'which', 'who',
    'whom', 'these', 'those', 'am', 'get', 'got', 'make', 'made',
  ]);

  const words = text.toLowerCase()
    .replace(/[^a-z0-9\s]/g, '')
    .split(/\s+/)
    .filter(w => w.length > 2 && !stopWords.has(w));

  // Count frequency
  const freq = {};
  for (const word of words) {
    freq[word] = (freq[word] || 0) + 1;
  }

  // Return top keywords by frequency
  return Object.entries(freq)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10)
    .map(([word]) => word);
}

/**
 * Search intelligence layer for relevant knowledge
 */
function searchKnowledge(keywords, maxResults = 5) {
  const results = [];

  for (const source of KNOWLEDGE_SOURCES) {
    const sourceDir = path.join(INTELLIGENCE_DIR, source.dir);
    if (!fs.existsSync(sourceDir)) continue;

    const files = fs.readdirSync(sourceDir)
      .filter(f => f.endsWith('.json'))
      .slice(-50); // Last 50 files

    for (const file of files) {
      try {
        const content = fs.readFileSync(path.join(sourceDir, file), 'utf8');
        const data = JSON.parse(content);

        // Search in payload and summary
        const searchText = JSON.stringify(data).toLowerCase();

        let relevance = 0;
        for (const keyword of keywords) {
          if (searchText.includes(keyword)) relevance++;
        }

        if (relevance > 0) {
          results.push({
            source: source.name,
            type: source.type,
            file,
            relevance,
            summary: data.payload?.summary || data.summary || file,
            timestamp: data.written_at || data.timestamp,
          });
        }
      } catch (e) {
        // Skip malformed files
      }
    }
  }

  // Sort by relevance, take top results
  return results
    .sort((a, b) => b.relevance - a.relevance)
    .slice(0, maxResults);
}

/**
 * Check for past decisions on similar topics
 */
function findPastDecisions(keywords) {
  const decisionsDir = path.join(INTELLIGENCE_DIR, 'decisions');
  if (!fs.existsSync(decisionsDir)) return [];

  const decisions = [];
  const files = fs.readdirSync(decisionsDir)
    .filter(f => f.endsWith('.json'))
    .slice(-30);

  for (const file of files) {
    try {
      const content = fs.readFileSync(path.join(decisionsDir, file), 'utf8');
      const data = JSON.parse(content);
      const searchText = JSON.stringify(data).toLowerCase();

      let relevance = 0;
      for (const keyword of keywords) {
        if (searchText.includes(keyword)) relevance++;
      }

      if (relevance > 1) { // At least 2 keyword matches
        decisions.push({
          file,
          decision: data.payload?.decision || data.decision || 'unknown',
          reasoning: data.payload?.reasoning || '',
          timestamp: data.written_at,
          relevance,
        });
      }
    } catch (e) {
      // Skip malformed files
    }
  }

  return decisions.sort((a, b) => b.relevance - a.relevance).slice(0, 3);
}

/**
 * Hook: Runs before assistant turn
 * Injects knowledge context if relevant
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

  // Check if this is a research/retrieval task
  const isResearchTask = RESEARCH_KEYWORDS.some(p => p.test(taskText));
  if (!isResearchTask) return { modified: false };

  // Extract keywords and search knowledge base
  const keywords = extractKeywords(taskText);
  if (keywords.length === 0) return { modified: false };

  const relevantKnowledge = searchKnowledge(keywords, 3);
  const pastDecisions = findPastDecisions(keywords);

  if (relevantKnowledge.length === 0 && pastDecisions.length === 0) {
    return { modified: false };
  }

  // Build knowledge context injection
  let knowledgeContext = '\n\n--- KNOWLEDGE GRAPH CONTEXT ---\n';
  knowledgeContext += 'Before researching, check if this knowledge is already available:\n\n';

  if (relevantKnowledge.length > 0) {
    knowledgeContext += 'Relevant existing knowledge:\n';
    for (const k of relevantKnowledge) {
      knowledgeContext += `- [${k.type}] ${k.summary} (${k.timestamp || 'unknown date'})\n`;
    }
  }

  if (pastDecisions.length > 0) {
    knowledgeContext += '\nPast decisions on similar topics:\n';
    for (const d of pastDecisions) {
      knowledgeContext += `- Decision: ${d.decision}\n`;
      if (d.reasoning) knowledgeContext += `  Reasoning: ${d.reasoning}\n`;
    }
  }

  knowledgeContext += '\nIf the answer is already known, use it. Only research if knowledge is missing or outdated.';
  knowledgeContext += '\n--- END KNOWLEDGE GRAPH CONTEXT ---\n';

  // Inject into the last user message
  // Note: This modifies the message in-place, which is how OpenClaw hooks work
  if (typeof lastUserMsg.content === 'string') {
    lastUserMsg.content += knowledgeContext;
  } else if (Array.isArray(lastUserMsg.content)) {
    lastUserMsg.content.push({
      type: 'text',
      text: knowledgeContext,
    });
  }

  return { modified: true };
}

module.exports = {
  beforeAssistantTurn,
  extractKeywords,
  searchKnowledge,
  findPastDecisions,
  name: 'knowledge-graph',
  version: '1.0.0',
};

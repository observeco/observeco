# ObserveCo Conversational Dashboard Copilot — Panel Design (Feature 80)

**Status:** Design review (for Gladwell)
**Approach:** Page Agent built-in panel + ObserveCo skin + trigger affordance

## 1. YAGNI check — nothing to build

Page Agent v1.10.0 already ships `agent.panel` — a complete chat overlay. The constructor at `packages/page-agent/src/PageAgent.ts` line 24 shows:

```ts
this.panel = new Panel(this, { language: config.language, promptForNextTask: config.promptForNextTask })
```

And `Panel` at `packages/ui/src/panel/Panel.ts` provides:
- Fixed-position floating bar (40px tall) at bottom-center
- Expandable history section above (scrollable, max 500px)
- Collapsible input area below
- Status indicator dot with animation states (thinking → executing → completed/error)
- History cards for task input, tool calls, observations, results
- `onAskUser` question rendering inline
- Stop/dispose action button
- Localized strings (en-US)

The instance is created silently per `new PageAgent()` and hidden (`Panel.hide()`). We never called `.show()`.

**What we add (the minimum):**
1. A floating trigger button on the ObserveCo dashboard to show/hide the panel
2. CSS overrides to remap Page Agent's generic dark theme to ObserveCo's design tokens
3. A keyboard shortcut

No backend, no new JS component, no custom history rendering.

## 2. Placement

**Trigger:** Floating action button, **bottom-right corner**, 24px from edge. Green-tinted circle with `💬` icon.

**Panel position:** Override Page Agent's default `bottom: 100px; left: 50%` to `bottom: 90px; right: 24px`.

**Rationale:** 
- Bottom-right is standard for assistant/chat triggers (Intercom, Crisp, etc.)
- Avoids overlap with the existing dashboard layout grid
- The panel expands *upward* from the trigger, keeping the input at the bottom near the trigger trigger

## 3. Layout & dimensions

```
┌────────────────────────────────────────────┐
│ ┌──────────────────────────────────────┐   │
│ │  🎯 Heal all degraded agents...      │   │  ← History cards
│ │  🔨 Clicking element #3              │   │     (scrollable, max 400px)
│ │  ❌ Agent 'hound' already healthy    │   │
│ └──────────────────────────────────────┘   │
│ ┌──────────────────────────────────────┐   │
│ │ ◉  Ready                  ▼  ✕       │   │  ← Status bar (40px)
│ └──────────────────────────────────────┘   │
│ ┌──────────────────────────────────────┐   │
│ │ [ Type a command...           ]      │   │  ← Input area (48px)
│ └──────────────────────────────────────┘   │
│                                    [💬]    │  ← Trigger FAB (36px)
└────────────────────────────────────────────┘
```

| Zone | Size | Notes |
|------|------|-------|
| History section | 400px × up to 400px | Scrollable, auto-hide when empty |
| Status bar | 400px × 40px | Always visible when panel is open |
| Input area | 400px × 48px | Appears on idle/completion, hidden during execution |
| Trigger FAB | 36px × 36px | Always visible, bottom-right 24px |

On viewport < 480px, panel width = `calc(100vw - 32px)`.

## 4. Color scheme overrides

Page Agent's built-in panel happens to use nearly the same green/red/yellow as ObserveCo's design tokens already:

| Page Agent default | ObserveCo token | Replace with? |
|---|---|---|
| `rgb(34, 197, 94)` completed/input | `--accent: #22c55e` | Keep — already matches |
| `rgb(239, 68, 68)` error | `--danger: #ef4444` | Keep — already matches |
| `rgb(255, 214, 0)` retrying | `--warn: #eab308` | Keep — close enough |
| `rgb(57, 182, 255)` thinking | `--meta: #3b82f6` | Keep — blue is fine |
| `rgba(0,0,0,0.5)` header bar | `--surface: #1e293b` | Override |

The panel draws a semi-transparent dark bar by default. On the ObserveCo dark dashboard (slate-900 bg), we want it opaque:

```css
/* Override Page Agent panel for ObserveCo dark theme */
#page-agent-runtime_agent-panel {
  --width: 400px;
  left: auto !important;
  right: 24px;
  bottom: 90px;
  transform: none !important;    /* Remove default centering translate */
}
#page-agent-runtime_agent-panel .header {
  background: var(--surface, #1e293b) !important;
  backdrop-filter: none !important;
  border: 1px solid var(--border, #334155);
  border-radius: 8px;
}
#page-agent-runtime_agent-panel .historySectionWrapper {
  background: var(--surface, #1e293b) !important;
  backdrop-filter: none !important;
  border: 1px solid var(--border, #334155);
  border-bottom: none;
}
#page-agent-runtime_agent-panel .inputSectionWrapper {
  background: var(--surface, #1e293b) !important;
  backdrop-filter: none !important;
  border: 1px solid var(--border, #334155);
  border-top: none;
}
#page-agent-runtime_agent-panel .taskInput {
  background: var(--bg, #0f172a) !important;
  border: 1px solid var(--border, #334155);
  color: var(--fg, #f8fafc);
}
#page-agent-runtime_agent-panel .statusText {
  font-family: 'Inter', sans-serif;
  color: var(--fg-2, #94a3b8);
}
```

## 5. Trigger FAB

```css
.observeco-copilot-fab {
  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: 2147483641;  /* 1 below Page Agent's z-index */
  width: 36px;
  height: 36px;
  border: none;
  border-radius: 50%;
  background: var(--accent, #22c55e);
  color: #0c1628;
  font-size: 16px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 12px rgba(34,197,94,0.35);
  transition: transform 0.15s, box-shadow 0.15s;
}
.observeco-copilot-fab:hover {
  transform: scale(1.1);
  box-shadow: 0 6px 16px rgba(34,197,94,0.5);
}
.observeco-copilot-fab.active {
  transform: scale(0.95);
  box-shadow: 0 2px 8px rgba(34,197,94,0.3);
}
```

## 6. Interaction flow

```
┌──────────┐    Click FAB / Cmd+Shift+K     ┌─────────────────────┐
│  FAB 💬  │ ─────────────────────────────>  │ Panel shown (idle)  │
│  (hidden)│ <─────────────────────────────  │ with input field    │
└──────────┘    Panel.hide() / ESC           └─────────────────────┘
                                                    │
                                               User types
                                               "Heal degraded agents"
                                                    │
                                                    v
                                            ┌─────────────────────┐
                                            │ Panel input hidden  │
                                            │ Status: "Thinking"  │
                                            │ Dot: blue pulse     │
                                            └─────────────────────┘
                                                    │
                                               Page Agent executes
                                               (reads DOM, clicks)
                                                    │
                                                    v
                                            ┌─────────────────────┐
                                            │ History cards appear│
                                            │ (tool calls, output)│
                                            │ Status: "...clicking"│
                                            └─────────────────────┘
                                                    │
                                               Task completes
                                                    │
                                                    v
                                            ┌─────────────────────┐
                                            │ Status: "Completed" │
                                            │ Dot: green static   │
                                            │ Input re-appears    │
                                            │ "Ask another..."    │
                                            └─────────────────────┘
```

**Keyboard:**
| Keys | Action |
|------|--------|
| `Cmd+Shift+K` | Toggle panel (show/hide) |
| `Escape` | Hide panel (when open and input empty) |
| `Enter` | Submit command |
| `Shift+Enter` | (reserved — multiline if needed) |

## 7. States

### Empty state (no commands yet)
- Panel shows "Ask the copilot anything about your fleet" in the status text
- Input placeholder: "Try: 'heal all degraded agents' or 'summarize errors'"
- No history cards

### Loading state (task executing)
- Input area hidden
- Status bar shows: animated blue dot + "Thinking..." / tool name
- History may show partial cards as steps complete

### Error state
- Status: red dot (static) + error message in status bar
- Error card in history with `❌` prefix
- Input reappears after 500ms for retry

### Completion state
- Status: green dot (static) + "Ready" / result summary
- Final result card highlighted (Page Agent's `.doneSuccess` style)
- Input reappears with placeholder: "Ask the copilot anything..."
- FAB badge shows unread count (ponytail: simple integer, not per-agent grouping)

### htmx swap recovery
The panel is at `document.body` (appended via `document.body.appendChild()` inside Panel.createWrapper). htmx partial swaps only affect the target element, so the panel survives all swaps. No recovery needed.

However, the `__observecoCopilot` instance is created in an IIFE at page load. When the page eventually does a full reload (not a partial swap), a new instance is created. The old DOM elements are destroyed with the old document.

**Edge case:** If htmx swaps the `<head>` script that initializes the copilot (unlikely — it's in the initial page, not a partial), the panel would be orphaned. Fix: gate the IIFE with `if (!window.__observecoCopilot)` and let the panel persist. **Decided: not needed — the copilot init script is in `<head>`, never in an htmx partial.**

### FAB while panel is open
When panel is visible, the FAB becomes inactive (`.active` class, scale down slightly). Toggle behavior: click FAB → hide panel. Click again → show panel. Same as `Cmd+Shift+K`.

### Panel disposal
When the panel is closed (X button), it calls `agent.panel.dispose()` which removes the wrapper from the DOM and detaches event listeners. The FAB remains. Next click creates a fresh panel instance? 

**Decision:** The X button should just hide the panel, not dispose it. Override the action button handler: when status is idle, hide panel instead of disposing. This avoids re-creating the PageAgent instance. (Page Agent's default behavior disposes the *agent*, which disposes the panel. We'll override by setting `promptForNextTask: true` and using our own hide on close.)

## 8. HTML/JS changes required

Minimal. Three additions to the `<head>` block in `index.html` (or `index_new.html` — whichever is live):

```html
<!-- Feature 80: Copilot panel trigger + theme -->
<style>
/* FAB trigger */
.observeco-copilot-fab { /* ... see §5 ... */ }
/* Panel theme override */
#page-agent-runtime_agent-panel { /* ... see §4 ... */ }
</style>

<!-- In the copilot init IIFE, add: -->
<script>
(function() {
  // ... existing PageAgent init ...

  window.__observecoCopilot = new window.PageAgent({
    model: 'ornith:latest',
    baseURL: 'http://localhost:11435/v1',
    language: 'en-US',
    promptForNextTask: true,
  });

  // Create trigger FAB
  var fab = document.createElement('button');
  fab.className = 'observeco-copilot-fab';
  fab.textContent = '💬';
  fab.setAttribute('aria-label', 'Toggle copilot');
  document.body.appendChild(fab);

  var panel = window.__observecoCopilot.panel;
  var visible = false;

  function toggle() {
    visible = !visible;
    if (visible) {
      panel.show();
      fab.classList.add('active');
    } else {
      panel.hide();
      fab.classList.remove('active');
    }
  }

  fab.addEventListener('click', toggle);

  document.addEventListener('keydown', function(e) {
    if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key === 'K') {
      e.preventDefault();
      toggle();
    }
    if (e.key === 'Escape' && visible) {
      toggle();
    }
  });

  console.log('[ObserveCo] Copilot ready — click the 💬 button or press Cmd+Shift+K');
})();
</script>
```

## 9. Visual mockup reference

This evokes the look: a compact bar at bottom-right (400px wide), dark panel surface with green accent, floating green FAB button. No canvas/highlight elements — the panel is pure DOM.

```
┌─────────────────────────────┐
│ 🎯 Heal all degraded agents │  ← History card
│ 🔨? ✓ Agent 'hound' healed │
│ 🔨? ✓ Agent 'echo' healed  │
│ 🎯 Fleet is now healthy:   │
│ 5 alive, 0 degraded        │
│─────────────────────────────│
│ ◉ Ready               ▼ ✕  │  ← Status bar var(--surface)
│─────────────────────────────│
│ [ Type a command...  ]      │  ← Input area var(--bg)
└─────────────────────────────┘
                          💬  ← FAB var(--accent)
```

## 10. Ponytails & known ceilings

1. **Active badge counter:** The FAB doesn't show unread or "active task" badges. The panel itself shows status. If operators want a badge when a task completes in the background, that's a future visual indicator on the FAB (ponytail: `data-count` attribute + CSS `::after` counter badge).

2. **FAB position on mobile:** The <style> includes a `@media(max-width:480px)` override for panel width but not the FAB. On very small viewports the FAB might overlap content. Fix: position at `bottom:16px; right:16px` on narrow screens (ponytail: add `@media(max-width:480px){ .observeco-copilot-fab { bottom: 16px; right: 16px; } }`).

3. **Voice input:** The Page Agent built-in panel has no voice button. Adding voice requires the Web Speech API or a custom input route. Not in scope for v1 (ponytail: add a `🎤` button next to input field that calls `SpeechRecognition`).

4. **No `panel.refresh()` for DOM state:** If the dashboard swaps its fleet content via htmx while the panel is open with stale DOM references, the operator would need to ask again. Page Agent re-reads the DOM on each `execute()` call, so this is only a concern for the *visual state* of the panel, not the agent's actions.

5. **Panel max-height on small screens:** `calc(100vh - 200px)` is fine for 900px+ viewports. On very short screens (<600px height), the panel might be taller than viewport. Fix: add a min clamp (ponytail: `max-height: min(400px, calc(100vh - 160px))`).

## 11. File delta

| File | Change |
|------|--------|
| `src/observeco/dashboard/templates/index.html` (or `index_new.html`) | + ~60 lines (FAB CSS + trigger JS in the copilot init block) |
| `static/observeco-dashboard.css` | + ~30 lines (panel theme override rules) |

Zero new files. Zero backend changes. Zero new dependencies.
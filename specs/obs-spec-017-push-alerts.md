# obs-spec-017: Push Alerts Delivery (Pro)

**Status:** Draft 2026-05-28
**Product:** ObserveCo Pro (Solo $9/mo, Team $49/mo)
**Depends on:** obs-dp-007 (error history), existing in-dashboard alerts

## §1 Problem

Alerts are currently **in-dashboard only** — they appear in the right-rail alerts panel and error timeline, but the user must be viewing the dashboard to see them. For alerts to be useful (circuit trips, drift breaches, agent deaths), they need to push to the user where they already are: Telegram, webhook, or CLI notification.

## §2 Delivery Channels (Priority Order)

1. **Webhook** — fastest to ship, most flexible (can pipe to any service)
2. **Telegram bot** — Sean's primary communication channel
3. **CLI ping** — terminal bell / notification for users running `observeco watch`

## §3 Architecture

### Alert Daemon
- Runs as part of `observeco watch` (already running in background)
- Polls every 60s: errors table, circuit breakers, drift breaches
- Checks against last-sent time per alert type to avoid duplicates
- Checks Pro subscription status before delivery

### Dedup
- Same alert type for same agent within 5 min → suppress (already sent)
- Different alert type for same agent → send (e.g., circuit trip + drift breach)
- Store last-sent in `alert_delivery_log` table

### DB Schema
```sql
CREATE TABLE IF NOT EXISTS alert_delivery_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name TEXT NOT NULL,
    alert_type TEXT NOT NULL,
    channel TEXT NOT NULL,
    delivered_at INTEGER NOT NULL,
    status TEXT DEFAULT 'sent',
    error_message TEXT
);
CREATE TABLE IF NOT EXISTS alert_config (
    agent_name TEXT PRIMARY KEY,
    webhook_url TEXT,
    telegram_chat_id TEXT,
    cli_notify INTEGER DEFAULT 0,
    min_severity TEXT DEFAULT 'warning'
);
```

## §4 Implementation

### Phase 1: Webhook
- Config key: `alerts.webhook_url` in `~/.observeco/config.yaml`
- POST JSON payload: `{agent, type, severity, message, timestamp, fleet_summary}`
- Retry: 3 attempts with 30s backoff

### Phase 2: Telegram
- Config key: `alerts.telegram_chat_id`
- Uses existing Hermes Telegram bridge or direct bot API
- Format: `🔴 [agent] circuit trip — [detail]`

### Phase 3: CLI ping
- macOS: `osascript -e 'display notification "..."'`
- Linux: `notify-send` or terminal bell `\a`
- Logged to stdout when `observeco watch` is running

## §5 Pro Gating
- Webhook: available in Free (log only, no actual push)
- Telegram + CLI ping: Pro only
- Check `observeco billing status` before delivery
- Free mode logs: "Would have sent to [channel] at [time]"

## §6 Edge Cases
- **Channel unreachable** — write to delivery_log with error status, retry in 5 min
- **Rate limited** — backoff 2 min, batch up to 1 alert per 30s per channel
- **Empty payload** — skip (alert was resolved between detection and delivery)
- **No config** — log debug warning, skip channel
- **Multiple agents, same alert** — send once with aggregated summary

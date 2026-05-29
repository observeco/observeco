"""Communication channel adapters for ObserveCo.

Adapters translate agent events between ObserveCo's internal format
and external communication platforms (Slack, Discord, Telegram, etc.).

All adapters implement the ChannelAdapter protocol:
- send_event(event) — send an event to the channel
- receive_event(raw) — parse a raw channel event into OEF format
- verify_webhook(headers, body) — verify webhook signature
"""

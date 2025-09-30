# Telegram Categorizer Bot

A simple Telegram bot that lets you forward messages into personal categories and retrieve them later via search.

## Features

- `/menu` — open quick-action buttons for the most common workflows.
- `/addcategory <name>` — create a bucket for related notes or links.
- `/setcategory <name>` — choose the active category; forwarded messages will be stored there.
- `/categories` — list your categories.
- Forwarded text messages are archived in SQLite along with metadata.
- No active category? The bot prompts you with inline buttons to choose one on the fly or via the `/menu` picker.
- `/setchannel <chat_id>` (optional) — copy every saved message to a private channel you control.
- `/list <name>` — show all stored snippets in a category.
- `/search <term>` — fuzzy search across all saved snippets.

> 📌 **Current focus:** text-only messages. File attachments are stored by caption/text metadata; support for documents/voice/photos can be layered in later.

## Getting Started

1. Create a bot with [BotFather](https://core.telegram.org/bots#botfather) and grab the token.
2. Copy `.env.example` to `.env` and fill in `BOT_TOKEN`.
3. Install dependencies and run the bot:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m bot
```

The bot will create an `telegram_bot.db` SQLite database on first run.

## Roadmap

- [ ] Store Telegram media via `copy_message` for non-text payloads.
- [ ] Allow multi-category tagging per message.
- [ ] Provide export/import of the archive (JSON/CSV).
- [ ] Desktop/web UI to review and manage the archive outside Telegram.
- [ ] Deploy instructions (Docker + fly.io/Render).

Contributions welcome! Open an issue or PR with ideas and improvements.

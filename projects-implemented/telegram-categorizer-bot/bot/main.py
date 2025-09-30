from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from html import escape as html_escape
from typing import Optional

from telegram import ForceReply, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.error import TelegramError
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from .config import load_settings
from .database import Database

logger = logging.getLogger(__name__)
PENDING_KEY = "pending_message"
ADD_CATEGORY_PENDING = "add_category_pending"

HELP_TEXT = (
    "Commands:\n"
    "/menu — show quick action buttons\n"
    "/addcategory <name> — create a category\n"
    "/setcategory <name> — make it the active target for forwarded messages\n"
    "/categories — list your categories\n"
    "/current — show the active category\n"
    "/setchannel <chat_id> — optional archive to a private channel\n"
    "/clearchannel — remove the archive channel\n"
    "/list <name> — display stored messages in a category\n"
    "/search <term> — search across all saved snippets\n"
    "Forward any message to save it under the active or chosen category."
)


def main() -> None:
    logging.basicConfig(
        format="%(asctime)s %(name)s %(levelname)s: %(message)s",
        level=logging.INFO,
    )
    settings = load_settings()
    db = Database(settings.database_path)
    db.initialise()

    application = ApplicationBuilder().token(settings.bot_token).build()

    application.add_handler(CommandHandler("start", start(db)))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("menu", menu_command(db)))
    application.add_handler(CommandHandler("addcategory", add_category(db)))
    application.add_handler(CommandHandler("categories", list_categories(db)))
    application.add_handler(CommandHandler("setcategory", set_category(db)))
    application.add_handler(CommandHandler("current", current_category(db)))
    application.add_handler(CommandHandler("setchannel", set_channel(db)))
    application.add_handler(CommandHandler("clearchannel", clear_channel(db)))
    application.add_handler(CommandHandler("list", list_messages(db)))
    application.add_handler(CommandHandler("search", search_messages(db)))

    application.add_handler(
        MessageHandler(filters.TEXT & (~filters.COMMAND), handle_forwarded(db))
    )
    application.add_handler(CallbackQueryHandler(menu_callback(db), pattern=r"^menu:.+"))
    application.add_handler(CallbackQueryHandler(set_category_direct(db), pattern=r"^set:\d+$"))
    application.add_handler(CallbackQueryHandler(select_category(db), pattern=r"^cat:\d+$"))

    logger.info("Bot started. Listening for updates...")
    application.run_polling()


def start(db: Database):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        message = update.message
        if not (user and message):
            return
        await message.reply_text(
            "👋 Hi! Forward me messages you want to keep safe.\n"
            "Use /menu for quick actions or /help for the full command list."
        )
        active = await asyncio.to_thread(db.get_active_category, user.id)
        if active:
            await message.reply_text(
                f"Current category: <b>{html_escape(active)}</b>",
                parse_mode=ParseMode.HTML,
            )

    return handler


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(HELP_TEXT)


def menu_command(db: Database):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        message = update.message
        if not (user and message):
            return
        categories = await asyncio.to_thread(db.list_categories, user.id)
        markup = build_menu_keyboard(bool(categories))
        await message.reply_text("Quick actions:", reply_markup=markup)

    return handler


def menu_callback(db: Database):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        user = update.effective_user
        if not (query and user):
            return
        await query.answer()
        action = query.data.split(":", 1)[1]

        if action == "list":
            categories = await asyncio.to_thread(db.list_categories, user.id)
            if not categories:
                await context.bot.send_message(query.message.chat_id, "No categories yet. Try adding one.")
                return
            text = "\n".join(f"• {name}" for name in categories)
            await context.bot.send_message(query.message.chat_id, f"Your categories:\n{text}")
            return

        if action == "current":
            active = await asyncio.to_thread(db.get_active_category, user.id)
            if active:
                await context.bot.send_message(
                    query.message.chat_id,
                    f"Currently saving to <b>{html_escape(active)}</b>.",
                    parse_mode=ParseMode.HTML,
                )
            else:
                await context.bot.send_message(
                    query.message.chat_id,
                    "No active category. Set one first.",
                )
            return

        if action == "channel":
            await context.bot.send_message(
                query.message.chat_id,
                "Link a storage channel with /setchannel <chat_id>. Add this bot as admin first, then forward messages to archive them automatically.",
            )
            return

        if action == "help":
            await context.bot.send_message(query.message.chat_id, HELP_TEXT)
            return

        if action == "add":
            context.user_data[ADD_CATEGORY_PENDING] = True
            await context.bot.send_message(
                query.message.chat_id,
                "Send the new category name:",
                reply_markup=ForceReply(selective=True),
            )
            return

        if action == "set":
            categories = await asyncio.to_thread(db.list_categories_full, user.id)
            if not categories:
                await context.bot.send_message(
                    query.message.chat_id,
                    "No categories available. Create one first.",
                )
                return
            await context.bot.send_message(
                query.message.chat_id,
                "Pick a category to set as active:",
                reply_markup=InlineKeyboardMarkup(build_category_keyboard(categories, prefix="set")),
            )
            return

        if action == "no-categories":
            await context.bot.send_message(
                query.message.chat_id,
                "No categories yet. Use the Add category button first.",
            )

    return handler


def build_menu_keyboard(has_categories: bool) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton("List categories", callback_data="menu:list"),
            InlineKeyboardButton(
                "Set active category",
                callback_data="menu:set" if has_categories else "menu:no-categories",
            ),
        ],
        [
            InlineKeyboardButton("Add category", callback_data="menu:add"),
            InlineKeyboardButton("Current category", callback_data="menu:current"),
        ],
        [
            InlineKeyboardButton("Link channel", callback_data="menu:channel"),
            InlineKeyboardButton("Help", callback_data="menu:help"),
        ],
    ]
    return InlineKeyboardMarkup(buttons)


def add_category(db: Database):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        message = update.message
        if not (user and message):
            return
        if not context.args:
            await message.reply_text("Usage: /addcategory <name>")
            return
        name = " ".join(context.args).strip()
        await asyncio.to_thread(db.add_category, user.id, name)
        escaped = html_escape(name)
        await message.reply_text(
            f"Category <b>{escaped}</b> ready!",
            parse_mode=ParseMode.HTML,
        )

    return handler


def list_categories(db: Database):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        message = update.message
        if not (user and message):
            return
        categories = await asyncio.to_thread(db.list_categories, user.id)
        if not categories:
            await message.reply_text("No categories yet. Create one with /addcategory <name>.")
            return
        text = "\n".join(f"• {name}" for name in categories)
        await message.reply_text(f"Your categories:\n{text}")

    return handler


def set_category(db: Database):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        message = update.message
        if not (user and message):
            return
        if not context.args:
            await message.reply_text("Usage: /setcategory <name>")
            return
        name = " ".join(context.args).strip()
        ok = await asyncio.to_thread(db.set_active_category, user.id, name)
        if ok:
            await message.reply_text(
                f"📁 Active category: <b>{html_escape(name)}</b>",
                parse_mode=ParseMode.HTML,
            )
        else:
            await message.reply_text("Unknown category. List them with /categories or create a new one.")

    return handler


def current_category(db: Database):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        message = update.message
        if not (user and message):
            return
        active = await asyncio.to_thread(db.get_active_category, user.id)
        if active:
            await message.reply_text(
                f"Currently saving to <b>{html_escape(active)}</b>.",
                parse_mode=ParseMode.HTML,
            )
        else:
            await message.reply_text("No active category. Set one with /setcategory <name>.")

    return handler


def set_channel(db: Database):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        message = update.message
        if not (user and message):
            return
        if not context.args:
            await message.reply_text("Usage: /setchannel <chat_id> (add me as admin first)")
            return
        try:
            chat_id = int(context.args[0])
        except ValueError:
            await message.reply_text("Chat id must be an integer (e.g. -1001234567890).")
            return

        try:
            confirmation = await context.bot.send_message(
                chat_id=chat_id,
                text="🔗 Channel linked to your categorizer bot. You can delete this confirmation message.",
            )
        except TelegramError as exc:
            await message.reply_text(
                "Could not access that chat. Ensure the bot is added as admin and the chat id is correct."
            )
            logger.warning("Failed linking channel for %s: %s", user.id, exc)
            return

        await asyncio.to_thread(db.set_storage_channel, user.id, chat_id)
        await message.reply_text("Storage channel registered. Forwarded messages will also be copied there.")
        try:
            await confirmation.pin()
        except TelegramError:
            pass

    return handler


def clear_channel(db: Database):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        message = update.message
        if not (user and message):
            return
        await asyncio.to_thread(db.clear_storage_channel, user.id)
        await message.reply_text("Channel link cleared. Messages will remain in the bot database only.")

    return handler


def list_messages(db: Database):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        message = update.message
        if not (user and message):
            return
        if not context.args:
            await message.reply_text("Usage: /list <category>")
            return
        category = " ".join(context.args).strip()
        rows = await asyncio.to_thread(lambda: list(db.list_messages(user.id, category)))
        if not rows:
            await message.reply_text("Nothing stored for that category yet.")
            return
        lines = [
            format_message_summary(idx, text, saved_at, channel_id, channel_msg_id)
            for idx, (_, text, saved_at, channel_id, channel_msg_id) in enumerate(rows)
        ]
        await message.reply_text("\n".join(lines))

    return handler


def search_messages(db: Database):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        message = update.message
        if not (user and message):
            return
        if not context.args:
            await message.reply_text("Usage: /search <term>")
            return
        term = " ".join(context.args)
        rows = await asyncio.to_thread(lambda: list(db.search_messages(user.id, term)))
        if not rows:
            await message.reply_text("No matches found.")
            return
        lines = [
            format_search_result(category, text, saved_at, channel_id, channel_msg_id)
            for category, text, saved_at, channel_id, channel_msg_id in rows
        ]
        await message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)

    return handler


def handle_forwarded(db: Database):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        message = update.message
        user = update.effective_user
        if not (message and user):
            return
        text = message.text or message.caption or ""

        if context.user_data.pop(ADD_CATEGORY_PENDING, False):
            name = text.strip()
            if not name:
                await message.reply_text("Category name cannot be empty.")
                return
            await asyncio.to_thread(db.add_category, user.id, name)
            await message.reply_text(
                f"Category <b>{html_escape(name)}</b> added.",
                parse_mode=ParseMode.HTML,
            )
            return

        if not text.strip():
            await message.reply_text("Cannot archive empty messages yet. Attach some text.")
            return

        original_chat = None
        original_sender = None
        forward_date = None

        if message.forward_origin:
            origin = message.forward_origin
            original_sender_obj = getattr(origin, "sender_user", None)
            if original_sender_obj:
                original_sender = original_sender_obj.full_name
            original_chat_obj = getattr(origin, "sender_chat", None)
            if original_chat_obj:
                original_chat = original_chat_obj.title
            if getattr(origin, "date", None):
                forward_date = origin.date.isoformat()
        else:
            if message.forward_from:
                original_sender = message.forward_from.full_name
            if message.forward_from_chat:
                original_chat = message.forward_from_chat.title
            if message.forward_date:
                forward_date = message.forward_date.isoformat()

        active = await asyncio.to_thread(db.get_active_category, user.id)
        if active:
            row_id = await asyncio.to_thread(
                db.save_message,
                user.id,
                text,
                category_name=active,
                original_chat=original_chat,
                original_sender=original_sender,
                forward_date=forward_date,
            )
            if row_id:
                await maybe_copy_to_channel(
                    context,
                    db,
                    user.id,
                    row_id,
                    message.chat_id,
                    message.message_id,
                    active,
                )
                await message.reply_text(
                    f"Saved to <b>{html_escape(active)}</b> ✅",
                    parse_mode=ParseMode.HTML,
                )
            else:
                await message.reply_text("Unable to save message. Confirm the category still exists.")
            return

        categories = await asyncio.to_thread(db.list_categories_full, user.id)
        if not categories:
            await message.reply_text("No active category. Use /addcategory <name> first.")
            return

        context.user_data[PENDING_KEY] = {
            "text": text,
            "original_chat": original_chat,
            "original_sender": original_sender,
            "forward_date": forward_date,
            "source_chat_id": message.chat_id,
            "source_message_id": message.message_id,
            "categories": {str(cat_id): name for cat_id, name in categories},
        }
        keyboard = InlineKeyboardMarkup(build_category_keyboard(categories))
        await message.reply_text("Choose a category for this snippet:", reply_markup=keyboard)

    return handler


def select_category(db: Database):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        if not query:
            return
        await query.answer()
        payload = context.user_data.get(PENDING_KEY)
        if not payload:
            await query.edit_message_text("No pending message to save.")
            return

        category_id = query.data.split(":", 1)[1]
        category_name = payload["categories"].get(category_id)
        if category_name is None:
            await query.edit_message_text("Category unavailable. Try forwarding again.")
            context.user_data.pop(PENDING_KEY, None)
            return

        row_id = await asyncio.to_thread(
            db.save_message,
            update.effective_user.id,
            payload["text"],
            category_id=int(category_id),
            original_chat=payload["original_chat"],
            original_sender=payload["original_sender"],
            forward_date=payload["forward_date"],
        )
        if not row_id:
            await query.edit_message_text("Could not save message. Please try again.")
            context.user_data.pop(PENDING_KEY, None)
            return

        await maybe_copy_to_channel(
            context,
            db,
            update.effective_user.id,
            row_id,
            payload["source_chat_id"],
            payload["source_message_id"],
            category_name,
        )

        await query.edit_message_text(
            f"Saved to <b>{html_escape(category_name)}</b> ✅",
            parse_mode=ParseMode.HTML,
        )
        context.user_data.pop(PENDING_KEY, None)

    return handler


def set_category_direct(db: Database):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        user = update.effective_user
        if not (query and user):
            return
        await query.answer()
        category_id = int(query.data.split(":", 1)[1])
        name = await asyncio.to_thread(db.set_active_category_by_id, user.id, category_id)
        if not name:
            await query.edit_message_text("Unable to set that category. It may no longer exist.")
            return
        await query.edit_message_text(
            f"📁 Active category: <b>{html_escape(name)}</b>",
            parse_mode=ParseMode.HTML,
        )

    return handler


def build_category_keyboard(categories: list[tuple[int, str]], prefix: str = "cat"):
    buttons = []
    row: list[InlineKeyboardButton] = []
    for cat_id, name in categories:
        button = InlineKeyboardButton(text=name[:32], callback_data=f"{prefix}:{cat_id}")
        row.append(button)
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return buttons


def format_message_summary(
    index: int,
    text: str,
    saved_at: str,
    channel_id: Optional[int],
    channel_msg_id: Optional[int],
) -> str:
    prefix = f"{index + 1}. {truncate(text)}"
    suffix = f"(saved {saved_at})"
    link = format_channel_reference(channel_id, channel_msg_id)
    if link:
        suffix += f" — {link}"
    return f"{prefix} {suffix}"


def format_search_result(
    category: str,
    text: str,
    saved_at: str,
    channel_id: Optional[int],
    channel_msg_id: Optional[int],
) -> str:
    category_html = html_escape(category)
    snippet = html_escape(truncate(text))
    suffix = html_escape(f"(saved {saved_at})")
    link = format_channel_reference(channel_id, channel_msg_id)
    if link:
        suffix = f"{suffix} — {html_escape(link)}"
    return f"• <b>{category_html}</b> — {snippet} {suffix}"


def truncate(text: str, length: int = 150) -> str:
    return text[:length] + ("…" if len(text) > length else "")


def format_channel_reference(chat_id: Optional[int], message_id: Optional[int]) -> Optional[str]:
    if chat_id is None or message_id is None:
        return None
    chat_str = str(chat_id)
    if chat_str.startswith("-100"):
        return f"https://t.me/c/{chat_str[4:]}/{message_id}"
    return f"chat {chat_id} message {message_id}"


ASYNC_COPY_WARNING = "Failed to copy message to storage channel for %s: %s"


async def maybe_copy_to_channel(
    context: ContextTypes.DEFAULT_TYPE,
    db: Database,
    user_id: int,
    message_db_id: int,
    source_chat_id: int,
    source_message_id: int,
    category_name: str,
) -> None:
    channel_id = await asyncio.to_thread(db.get_storage_channel, user_id)
    if not channel_id:
        return
    try:
        copied = await context.bot.copy_message(
            chat_id=channel_id,
            from_chat_id=source_chat_id,
            message_id=source_message_id,
        )
        tag = f"#{category_name.replace(' ', '_')}"
        meta = (
            f"{tag}\nSaved at: {datetime.utcnow().isoformat(timespec='seconds')}\n"
            f"User: {user_id}"
        )
        await context.bot.send_message(chat_id=channel_id, text=meta)
        await asyncio.to_thread(
            db.attach_forward_copy,
            message_db_id,
            copied.chat_id,
            copied.message_id,
        )
    except TelegramError as exc:
        logger.warning(ASYNC_COPY_WARNING, user_id, exc)


if __name__ == "__main__":
    main()

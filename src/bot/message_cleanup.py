"""Helpers for keeping bot chats clean by replacing previous bot responses."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any

from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramNetworkError
from aiogram.types import BufferedInputFile, Message

_LAST_BOT_MESSAGE_ID_BY_CHAT: dict[int, int] = {}
_CHAT_LOCKS: defaultdict[int, asyncio.Lock] = defaultdict(asyncio.Lock)


async def send_and_track_text(
    message: Message,
    text: str,
    *,
    reply_markup: Any = None,
) -> Message:
    """Send a new bot message and remember its id for future cleanup."""

    sent = await message.answer(text, reply_markup=reply_markup)
    _LAST_BOT_MESSAGE_ID_BY_CHAT[message.chat.id] = sent.message_id
    return sent


async def replace_tracked_text(
    message: Message,
    text: str,
    *,
    reply_markup: Any = None,
) -> Message:
    """Delete the previous bot message in this chat and send a new one."""

    lock = _CHAT_LOCKS[message.chat.id]
    async with lock:
        await _delete_previous_bot_message(message)
        sent = await message.answer(text, reply_markup=reply_markup)
        _LAST_BOT_MESSAGE_ID_BY_CHAT[message.chat.id] = sent.message_id
        return sent


async def replace_tracked_document(
    message: Message,
    document: BufferedInputFile,
    *,
    caption: str | None = None,
    reply_markup: Any = None,
) -> Message:
    """Delete the previous bot message in this chat and send a file message."""

    lock = _CHAT_LOCKS[message.chat.id]
    async with lock:
        await _delete_previous_bot_message(message)
        sent = await message.answer_document(
            document=document,
            caption=caption,
            reply_markup=reply_markup,
        )
        _LAST_BOT_MESSAGE_ID_BY_CHAT[message.chat.id] = sent.message_id
        return sent


async def _delete_previous_bot_message(message: Message) -> None:
    """Try deleting the last tracked bot message for this chat."""

    last_message_id = _LAST_BOT_MESSAGE_ID_BY_CHAT.get(message.chat.id)
    if last_message_id is None:
        return

    try:
        await message.bot.delete_message(chat_id=message.chat.id, message_id=last_message_id)
    except (TelegramBadRequest, TelegramForbiddenError, TelegramNetworkError):
        # Ignore if message is too old, already deleted, or chat permissions changed.
        pass

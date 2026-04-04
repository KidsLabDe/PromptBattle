"""Send round results to Telegram."""

from __future__ import annotations

import asyncio
import base64
import logging
from io import BytesIO

from backend.config import settings

logger = logging.getLogger(__name__)


def _enabled() -> bool:
    return bool(settings.telegram_bot_token and settings.telegram_chat_id)


async def send_round_single(
    target_image_name: str,
    prompt: str,
    score: float,
    threshold: float,
    passed: bool,
    generated_b64: str,
    reason: str = "",
) -> None:
    """Send single-player round result to Telegram."""
    if not _enabled():
        return
    passed_text = "Bestanden ✅" if passed else "Nicht bestanden ❌"
    caption = (
        f"🎮 *Prompt Battle — Einzelspieler*\n"
        f"🎯 Zielbild: `{target_image_name}`\n"
        f"💬 Prompt: _{prompt}_\n"
        f"📊 Score: *{score}%* (Schwelle: {threshold}%)\n"
        f"➡️ {passed_text}"
    )
    if reason:
        caption += f"\n💡 {reason}"

    images = _collect_images(generated_b64)
    await _send(caption, images)


async def send_round_multi(
    target_image_name: str,
    player1: dict,
    player2: dict,
    winner: int,
    round_num: int,
    player1_wins: int,
    player2_wins: int,
) -> None:
    """Send multiplayer round result to Telegram."""
    if not _enabled():
        return

    if winner == 1:
        winner_text = "Spieler 1 gewinnt! 🏆"
    elif winner == 2:
        winner_text = "Spieler 2 gewinnt! 🏆"
    else:
        winner_text = "Unentschieden! 🤝"

    caption = (
        f"🎮 *Prompt Battle — Runde {round_num}*\n"
        f"🎯 Zielbild: `{target_image_name}`\n\n"
        f"👤 *Spieler 1:* _{player1.get('prompt', '')}_\n"
        f"📊 Score: *{player1.get('score', 0)}%*\n\n"
        f"👤 *Spieler 2:* _{player2.get('prompt', '')}_\n"
        f"📊 Score: *{player2.get('score', 0)}%*\n\n"
        f"➡️ {winner_text}\n"
        f"🏅 Stand: {player1_wins} : {player2_wins}"
    )

    reason1 = player1.get("reason", "")
    reason2 = player2.get("reason", "")
    if reason1:
        caption += f"\n💡 S1: {reason1}"
    if reason2:
        caption += f"\n💡 S2: {reason2}"

    images = _collect_images(
        player1.get("generated_image", ""),
        player2.get("generated_image", ""),
    )
    await _send(caption, images)


def _collect_images(*b64_strings: str) -> list[BytesIO]:
    """Decode base64 images to BytesIO buffers."""
    images: list[BytesIO] = []
    for b64 in b64_strings:
        if not b64:
            continue
        try:
            buf = BytesIO(base64.b64decode(b64))
            buf.name = "image.webp"
            images.append(buf)
        except Exception:
            pass
    return images


async def _send(caption: str, images: list[BytesIO]) -> None:
    """Send images + caption to Telegram (fire-and-forget, never raises)."""
    try:
        from telegram import Bot, InputMediaPhoto

        bot = Bot(token=settings.telegram_bot_token)
        chat_id = settings.telegram_chat_id

        if len(images) == 0:
            await bot.send_message(chat_id=chat_id, text=caption, parse_mode="Markdown")
        elif len(images) == 1:
            await bot.send_photo(
                chat_id=chat_id,
                photo=images[0],
                caption=caption,
                parse_mode="Markdown",
            )
        else:
            media = []
            for i, img in enumerate(images):
                media.append(InputMediaPhoto(
                    media=img,
                    caption=caption if i == 0 else None,
                    parse_mode="Markdown" if i == 0 else None,
                ))
            await bot.send_media_group(chat_id=chat_id, media=media)
    except Exception as e:
        logger.error(f"Telegram send failed: {e}")

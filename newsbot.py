# newsbot.py
import asyncio
import re
from datetime import datetime
from zoneinfo import ZoneInfo
import html
from typing import Tuple, List

from aiogram import Dispatcher, types
from aiogram.filters import Command
from aiogram.client.bot import Bot, DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession

# ---------- Налаштування ----------
BOT_TOKEN = "8192610652:AAG-ifECYgnuLLpXBs5dJYGjLYGVFzVcsog"  # <- встав свій токен
TIMEZONE = "Europe/Kyiv"               # використовуємо часову зону Києва
# -----------------------------------

# 🟢 Ініціалізація бота для aiogram 3.7+
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode="HTML"),
    session=AiohttpSession()
)
dp = Dispatcher()

# ---------- Функції ----------
def _now_kiev() -> str:
    now = datetime.now(tz=ZoneInfo(TIMEZONE))
    return now.strftime("%d.%m | %H:%M")

def extract_source(text: str) -> Tuple[str, str]:
    """Шукає джерело у тексті і повертає (source, text_without_source)."""
    m = re.search(r"(Джерело[:\s]*)(.+?)(?:\n|$)", text, flags=re.I)
    if m:
        source = m.group(2).strip()
        new_text = text[:m.start()] + text[m.end():]
        return source, new_text.strip()
    m2 = re.search(r"[—–-]\s*([^\n,\.]+)(?:\.|$|\n)", text)
    if m2:
        source = m2.group(1).strip()
        new_text = text[:m2.start()] + text[m2.end():]
        return source, new_text.strip()
    return "", text

def extract_places(text: str) -> List[str]:
    """Повертає список областей/громад/міст/районів, знайдених у тексті."""
    candidates = []
    pattern = re.compile(
        r"([А-ЯҐЄІЇ][\w\'\-ієїґєії\s]{1,60}?(?:област[ія]|громад[аи]|міст[ао]|населених пункт[а-яіїєґ]{0,6}|район[ау]|селищ[ао]))",
        flags=re.I
    )
    for m in pattern.finditer(text):
        s = m.group(1).strip()
        s = re.sub(r"\s+", " ", s)
        s = s[0].upper() + s[1:]
        if s not in candidates:
            candidates.append(s)
    return candidates

def guess_title(text: str, places: List[str], source: str) -> str:
    txt = text.strip()
    if source:
        txt = txt.replace(source, "")
    for p in places:
        txt = txt.replace(p, "")
    lines = [ln.strip() for ln in txt.splitlines() if ln.strip()]
    if not lines:
        return ""
    first = lines[0]
    if len(first) <= 160:
        return _clean_title(first)
    m = re.search(r"(.+?[.!?\n])\s", txt)
    if m:
        return _clean_title(m.group(1).strip())
    return _clean_title(first[:160].rstrip(" ,;:") + "...")

def _clean_title(t: str) -> str:
    t = t.strip()
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"^[^\wА-Яа-яЄєІіЇїҐґ0-9]+", "", t)
    return t

def extract_details(text: str, title: str, places: List[str], source: str) -> str:
    txt = text.strip()
    if title:
        txt = txt.replace(title, "")
    if source:
        txt = txt.replace(source, "")
    for p in places:
        txt = txt.replace(p, "")
    txt = txt.strip(" \n-–—·•")
    if not txt:
        return ""
    paragraphs = [p.strip() for p in re.split(r"\n{1,}", txt) if p.strip()]
    if len(paragraphs) == 1:
        para = paragraphs[0]
        sents = re.split(r"(?<=[\.!\?])\s+", para)
        if len(sents) > 1:
            paragraphs = sents
    return "\n".join(paragraphs)

def format_post(title: str, places: List[str], time_str: str, details: str, source: str) -> str:
    title_html = html.escape(title) if title else "Подія"
    event_line = f"⚡ <b>Подія:</b> {title_html}"
    place_text = " • ".join([html.escape(p) for p in places]) if places else "—"
    place_line = f"📍 <b>Місце:</b> {place_text}"
    time_line = f"🕓 <b>Час:</b> {html.escape(time_str)}"
    details_block = f"\n\n📢 <b>Деталі:</b>\n{html.escape(details)}" if details else ""
    source_block = f"\n\n📚 <b>Джерело:</b> {html.escape(source)}" if source else ""
    hashtags = "\n\n#новинник #оперативно"
    return f"{event_line}\n{place_line}\n{time_line}{details_block}{source_block}{hashtags}"

# ---------- Обробники ----------
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("👋 Привіт! Надішли сирий текст новини — я поверну його в форматі «Новинник».")

@dp.message()
async def handle_message(message: types.Message):
    raw = message.text or ""
    if not raw.strip():
        await message.answer("⚠️ Надішли будь-який текст новини.")
        return
    source, text_wo_source = extract_source(raw)
    places = extract_places(text_wo_source)
    title = guess_title(text_wo_source, places, source)
    if not title:
        title = text_wo_source.strip().splitlines()[0][:120].strip()
    details = extract_details(text_wo_source, title, places, source)
    time_str = _now_kiev()
    post = format_post(title=title, places=places, time_str=time_str, details=details, source=source)
    await message.answer(post)

# ---------- Запуск ----------
async def main():
    print("✅ NewsBot running...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

"""
🎬 Movie & Series Recommendation Telegram Bot
Использует Groq (бесплатно) + TMDB для рекомендаций фильмов и сериалов.
"""

import os
import re
import time
import logging
import requests
from groq import Groq

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger(__name__)

# ──────────────────────────────────────────
#  Конфигурация
# ──────────────────────────────────────────
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
GROQ_API_KEY   = os.environ["GROQ_API_KEY"]
TMDB_KEY       = os.environ.get("TMDB_API_KEY", "")  # Опционально

TG_API   = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
TMDB_API = "https://api.themoviedb.org/3"

client = Groq(api_key=GROQ_API_KEY)

# ──────────────────────────────────────────
#  TMDB — популярные новинки
# ──────────────────────────────────────────
def tmdb_popular_movies(count: int = 8) -> list[dict]:
    if not TMDB_KEY:
        return []
    try:
        r = requests.get(f"{TMDB_API}/movie/popular",
                         params={"api_key": TMDB_KEY, "language": "ru-RU"},
                         timeout=8)
        return [{"title": m["title"], "year": m.get("release_date", "")[:4],
                 "rating": m.get("vote_average", 0), "overview": m.get("overview", ""),
                 "type": "фильм"} for m in r.json().get("results", [])[:count]]
    except Exception as e:
        log.warning(f"TMDB movies error: {e}")
        return []


def tmdb_popular_series(count: int = 8) -> list[dict]:
    if not TMDB_KEY:
        return []
    try:
        r = requests.get(f"{TMDB_API}/tv/popular",
                         params={"api_key": TMDB_KEY, "language": "ru-RU"},
                         timeout=8)
        return [{"title": s.get("name", ""), "year": s.get("first_air_date", "")[:4],
                 "rating": s.get("vote_average", 0), "overview": s.get("overview", ""),
                 "type": "сериал"} for s in r.json().get("results", [])[:count]]
    except Exception as e:
        log.warning(f"TMDB series error: {e}")
        return []


def format_catalog(items: list[dict]) -> str:
    if not items:
        return ""
    lines = [f"- {i['title']} ({i['year']}) ⭐{i['rating']:.1f} [{i['type']}] — {i['overview'][:100]}"
             for i in items]
    return "\n".join(lines)

# ──────────────────────────────────────────
#  Groq — генерация рекомендаций
# ──────────────────────────────────────────
SYSTEM_PROMPT = """Ты — дружелюбный кино-эксперт в Telegram. Помогаешь людям выбрать что посмотреть.

Правила:
- Отвечай только на русском языке
- Предлагай 3–5 конкретных фильмов или сериалов под запрос
- Для каждого: название (год) — одна яркая фраза почему стоит смотреть
- Используй эмодзи, но без фанатизма
- Если пользователь написал что-то не про кино — мягко верни к теме
- Стиль: живой и тёплый, как совет другу

Если в сообщении есть список актуальных новинок из каталога — можешь их использовать,
но не ограничивайся только ими: добавляй классику и другие подходящие варианты."""


def get_recommendations(user_text: str, catalog_hint: str = "") -> str:
    content = user_text
    if catalog_hint:
        content += f"\n\nАктуальные новинки для справки:\n{catalog_hint}"

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",  # Лучшая бесплатная модель на Groq
        max_tokens=800,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": content},
        ],
    )
    return response.choices[0].message.content.strip()

# ──────────────────────────────────────────
#  Telegram
# ──────────────────────────────────────────
def send_message(chat_id: int, text: str):
    requests.post(f"{TG_API}/sendMessage", json={
        "chat_id":    chat_id,
        "text":       text,
        "parse_mode": "HTML",
    }, timeout=10)


def send_typing(chat_id: int):
    requests.post(f"{TG_API}/sendChatAction",
                  json={"chat_id": chat_id, "action": "typing"}, timeout=5)


def get_updates(offset: int = 0) -> list[dict]:
    try:
        r = requests.get(f"{TG_API}/getUpdates",
                         params={"offset": offset, "timeout": 30},
                         timeout=35)
        return r.json().get("result", [])
    except Exception:
        return []

# ──────────────────────────────────────────
#  Команды и обработка сообщений
# ──────────────────────────────────────────
WELCOME = """🎬 <b>Привет! Я кино-бот.</b>

Расскажи, что хочешь посмотреть — подберу фильмы и сериалы специально для тебя.

Например:
• <i>«хочу что-то страшное»</i>
• <i>«комедия на вечер с друзьями»</i>
• <i>«что-то вроде Игры Престолов»</i>
• <i>«документалки про природу»</i>
• <i>«хочу поплакать»</i>

Просто напиши — и я помогу! 🍿"""

HELP = """🆘 <b>Как пользоваться:</b>

Опиши настроение или предпочтения обычным текстом:

🎭 По жанру: <i>«триллер», «мелодрама», «аниме»</i>
😊 По настроению: <i>«хочу поднять настроение»</i>
🎬 По похожему: <i>«что-то вроде Интерстеллара»</i>
⭐ По теме: <i>«про войну», «про космос»</i>

Команды:
/start — начало
/help — эта справка
/новинки — популярное прямо сейчас"""


_bot_username = None
def get_bot_username() -> str:
    global _bot_username
    if not _bot_username:
        try:
            r = requests.get(f"{TG_API}/getMe", timeout=5)
            _bot_username = r.json()["result"]["username"]
        except Exception:
            _bot_username = "bot"
    return _bot_username


def handle_message(chat_id: int, text: str):
    text = text.strip()
    cmd  = text.split("@")[0].lower()

    if cmd == "/start":
        send_message(chat_id, WELCOME)
        return

    if cmd == "/help":
        send_message(chat_id, HELP)
        return

    if cmd in ("/новинки", "/novosti"):
        send_typing(chat_id)
        items = tmdb_popular_movies(5) + tmdb_popular_series(5)
        if items:
            lines = [f"{'🎬' if i['type']=='фильм' else '📺'} <b>{i['title']}</b> ({i['year']}) ⭐{i['rating']:.1f}"
                     for i in items]
            msg = "🔥 <b>Популярно прямо сейчас:</b>\n\n" + "\n".join(lines) + \
                  "\n\nНапиши что тебя интересует — подберу подробнее!"
        else:
            msg = "Не удалось загрузить новинки. Напиши что хочешь посмотреть — помогу!"
        send_message(chat_id, msg)
        return

    # Обычный запрос → Groq
    send_typing(chat_id)
    catalog = format_catalog(tmdb_popular_movies(6) + tmdb_popular_series(6))
    reply   = get_recommendations(text, catalog)
    send_message(chat_id, reply)

# ──────────────────────────────────────────
#  Главный цикл
# ──────────────────────────────────────────
def main():
    log.info("🎬 Movie Bot (Groq) запущен!")
    get_bot_username()
    offset = 0

    while True:
        updates = get_updates(offset)
        for update in updates:
            offset = update["update_id"] + 1
            try:
                msg     = update.get("message", {})
                chat_id = msg.get("chat", {}).get("id")
                text    = msg.get("text", "")
                if chat_id and text:
                    log.info(f"[{chat_id}] {text[:60]}")
                    handle_message(chat_id, text)
            except Exception as e:
                log.error(f"Ошибка: {e}")
        time.sleep(1)


if __name__ == "__main__":
    main()

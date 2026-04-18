"""
🎬 Movie & Series Recommendation Telegram Bot
Пользователь описывает настроение или жанр — бот рекомендует фильмы и сериалы.
"""

import os
import re
import time
import logging
import requests
import anthropic

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger(__name__)

# ──────────────────────────────────────────
#  Конфигурация
# ──────────────────────────────────────────
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
ANTHROPIC_KEY  = os.environ["ANTHROPIC_API_KEY"]
TMDB_KEY       = os.environ.get("TMDB_API_KEY", "")   # Опционально, но улучшает результат

TG_API   = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
TMDB_API = "https://api.themoviedb.org/3"

client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

# ──────────────────────────────────────────
#  TMDB — получаем популярные новинки
# ──────────────────────────────────────────
def tmdb_popular_movies(count: int = 10) -> list[dict]:
    """Топ популярных фильмов прямо сейчас."""
    if not TMDB_KEY:
        return []
    try:
        r = requests.get(f"{TMDB_API}/movie/popular",
                         params={"api_key": TMDB_KEY, "language": "ru-RU", "page": 1},
                         timeout=8)
        movies = r.json().get("results", [])[:count]
        return [{"title": m["title"], "year": m.get("release_date", "")[:4],
                 "rating": m.get("vote_average", 0), "overview": m.get("overview", ""),
                 "type": "фильм"} for m in movies]
    except Exception as e:
        log.warning(f"TMDB error: {e}")
        return []


def tmdb_popular_series(count: int = 10) -> list[dict]:
    """Топ популярных сериалов прямо сейчас."""
    if not TMDB_KEY:
        return []
    try:
        r = requests.get(f"{TMDB_API}/tv/popular",
                         params={"api_key": TMDB_KEY, "language": "ru-RU", "page": 1},
                         timeout=8)
        shows = r.json().get("results", [])[:count]
        return [{"title": s.get("name", ""), "year": s.get("first_air_date", "")[:4],
                 "rating": s.get("vote_average", 0), "overview": s.get("overview", ""),
                 "type": "сериал"} for s in shows]
    except Exception as e:
        log.warning(f"TMDB error: {e}")
        return []


def format_catalog(items: list[dict]) -> str:
    if not items:
        return ""
    lines = [f"- {i['title']} ({i['year']}) ⭐{i['rating']:.1f} — {i['overview'][:120]}" for i in items]
    return "\n".join(lines)

# ──────────────────────────────────────────
#  Claude — генерация рекомендаций
# ──────────────────────────────────────────
SYSTEM_PROMPT = """Ты — дружелюбный кино-эксперт в Telegram. Помогаешь людям выбрать что посмотреть.

Правила:
- Отвечай только на русском языке
- Предлагай 3–5 конкретных фильмов или сериалов, соответствующих запросу
- Для каждого: название (год) — одна яркая фраза почему стоит смотреть
- Используй эмодзи, но без фанатизма
- Если пользователь написал что-то не про кино — мягко верни к теме
- Формат ответа: живой, тёплый, как совет другу

Если в контексте есть список актуальных фильмов/сериалов из TMDB — можешь использовать их,
но не ограничивайся только ими: добавляй классику или другие подходящие варианты.
"""


def get_recommendations(user_text: str, catalog_hint: str = "") -> str:
    context = ""
    if catalog_hint:
        context = f"\n\nАктуальные новинки из каталога для справки:\n{catalog_hint}\n"

    messages = [{
        "role": "user",
        "content": f"{user_text}{context}"
    }]

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=800,
        system=SYSTEM_PROMPT,
        messages=messages,
    )
    return response.content[0].text.strip()

# ──────────────────────────────────────────
#  Telegram — отправка и получение сообщений
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
                         params={"offset": offset, "timeout": 30, "allowed_updates": ["message"]},
                         timeout=35)
        return r.json().get("result", [])
    except Exception:
        return []

# ──────────────────────────────────────────
#  Обработка команд
# ──────────────────────────────────────────
WELCOME = """🎬 <b>Привет! Я кино-бот.</b>

Расскажи мне, что хочешь посмотреть — я подберу фильмы и сериалы специально для тебя.

Например:
• <i>«хочу что-то страшное»</i>
• <i>«посоветуй комедию на вечер»</i>
• <i>«что-то вроде Игры Престолов»</i>
• <i>«документалки про природу»</i>
• <i>«хочу поплакать»</i>

Просто напиши — и я помогу! 🍿"""

HELP = """🆘 <b>Как пользоваться ботом:</b>

Просто опиши своё настроение или предпочтения обычным текстом:

🎭 По жанру: <i>«триллер», «мелодрама», «аниме»</i>
😊 По настроению: <i>«хочу поднять настроение», «что-то грустное»</i>
🎬 По похожему: <i>«что-то вроде Интерстеллара»</i>
⭐ По теме: <i>«про войну», «про космос», «про школу»</i>

Команды:
/start — начало
/help — эта справка
/новинки — популярные новинки прямо сейчас"""


def handle_message(chat_id: int, text: str):
    text = text.strip()

    if text in ("/start", "/start@" + get_bot_username()):
        send_message(chat_id, WELCOME)
        return

    if text in ("/help", "/help@" + get_bot_username()):
        send_message(chat_id, HELP)
        return

    if text.lower() in ("/новинки", "/novosti", "/новости"):
        send_typing(chat_id)
        movies = tmdb_popular_movies(5)
        series = tmdb_popular_series(5)
        all_items = movies + series
        if all_items:
            lines = [f"{'🎬' if i['type']=='фильм' else '📺'} <b>{i['title']}</b> ({i['year']}) ⭐{i['rating']:.1f}" for i in all_items]
            msg = "🔥 <b>Популярно прямо сейчас:</b>\n\n" + "\n".join(lines) + "\n\nНапиши, что тебя интересует — подберу подробнее!"
        else:
            msg = "Не удалось загрузить новинки. Попробуй описать, что хочешь посмотреть — я помогу!"
        send_message(chat_id, msg)
        return

    # Обычный запрос — спрашиваем у Claude
    send_typing(chat_id)
    catalog = format_catalog(tmdb_popular_movies(8) + tmdb_popular_series(8))
    reply = get_recommendations(text, catalog)
    send_message(chat_id, reply)


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

# ──────────────────────────────────────────
#  Главный цикл (long polling)
# ──────────────────────────────────────────
def main():
    log.info("🎬 Movie Bot запущен!")
    get_bot_username()
    offset = 0

    while True:
        updates = get_updates(offset)
        for update in updates:
            offset = update["update_id"] + 1
            try:
                msg = update.get("message", {})
                chat_id = msg.get("chat", {}).get("id")
                text    = msg.get("text", "")
                if chat_id and text:
                    log.info(f"[{chat_id}] {text[:60]}")
                    handle_message(chat_id, text)
            except Exception as e:
                log.error(f"Ошибка обработки: {e}")
        time.sleep(1)


if __name__ == "__main__":
    main()

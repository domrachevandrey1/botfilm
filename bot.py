"""
🎬 @PosmotriBot — рекомендации фильмов и сериалов
Groq (бесплатно)
"""

import os
import time
import logging
import requests
from groq import Groq

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger(__name__)

TELEGRAM_TOKEN  = os.environ["TELEGRAM_TOKEN"]
GROQ_API_KEY    = os.environ["GROQ_API_KEY"]

TG_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

client = Groq(api_key=GROQ_API_KEY)


SYSTEM_PROMPT = """Ты — дружелюбный кино-эксперт в Telegram. Помогаешь людям выбрать что посмотреть.
- Отвечай только на русском языке
- Предлагай 3–5 фильмов или сериалов под запрос
- Для каждого: название (год) — одна яркая фраза почему стоит смотреть
- Используй эмодзи умеренно
- Стиль: живой и тёплый, как совет другу"""


def get_recommendations(text: str) -> str:
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=800,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": text},
        ],
    )
    return response.choices[0].message.content.strip()


def send_message(chat_id: int, text: str):
    requests.post(f"{TG_API}/sendMessage", json={
        "chat_id": chat_id, "text": text, "parse_mode": "HTML",
    }, timeout=10)


def send_typing(chat_id: int):
    requests.post(f"{TG_API}/sendChatAction",
                  json={"chat_id": chat_id, "action": "typing"}, timeout=5)


def get_updates(offset: int = 0) -> list:
    try:
        r = requests.get(f"{TG_API}/getUpdates",
                         params={"offset": offset, "timeout": 30,
                                 "allowed_updates": ["message"]},
                         timeout=35)
        return r.json().get("result", [])
    except Exception:
        return []


WELCOME = """🎬 <b>Привет! Я @PosmotriBot.</b>

Расскажи, что хочешь посмотреть — подберу фильмы и сериалы специально для тебя.

Например:
• <i>«хочу что-то страшное»</i>
• <i>«комедия на вечер с друзьями»</i>
• <i>«что-то вроде Игры Престолов»</i>
• <i>«хочу поплакать»</i>

Просто напиши — и я помогу! 🍿"""

HELP = """🆘 <b>Как пользоваться:</b>

Опиши настроение или предпочтения:
🎭 <i>«триллер», «мелодрама», «аниме»</i>
😊 <i>«хочу поднять настроение»</i>
🎬 <i>«что-то вроде Интерстеллара»</i>

/start — начало
/help — эта справка"""


def handle_message(chat_id: int, text: str):
    cmd = text.strip().split("@")[0].lower()

    if cmd == "/start":
        send_message(chat_id, WELCOME)
        return

    if cmd == "/help":
        send_message(chat_id, HELP)
        return

    send_typing(chat_id)
    send_message(chat_id, get_recommendations(text.strip()))


def main():
    log.info("🎬 @PosmotriBot запущен!")
    offset = 0
    while True:
        for update in get_updates(offset):
            offset = update["update_id"] + 1
            try:
                if "message" in update:
                    msg     = update["message"]
                    chat_id = msg.get("chat", {}).get("id")
                    text    = msg.get("text", "")
                    if chat_id and text:
                        log.info(f"Сообщение: {text[:60]}")
                        handle_message(chat_id, text)
            except Exception as e:
                log.error(f"Ошибка: {e}")
        time.sleep(1)


if __name__ == "__main__":
    main()

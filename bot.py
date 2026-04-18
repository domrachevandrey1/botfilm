"""
🎬 @PosmotriBot — рекомендации фильмов и сериалов
Groq (бесплатно) + SubGram (монетизация)
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
SUBGRAM_API_KEY = os.environ["SUBGRAM_API_KEY"]

TG_API      = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
SUBGRAM_URL = "https://api.subgram.org/get-sponsors"

client = Groq(api_key=GROQ_API_KEY)

def check_subgram(user_id: int, chat_id: int) -> str:
    try:
        resp = requests.post(
            SUBGRAM_URL,
            headers={"Auth": SUBGRAM_API_KEY, "Content-Type": "application/json"},
            json={"user_id": user_id, "chat_id": chat_id},
            timeout=10,
        )
        data = resp.json()
        return data.get("status", "error")
    except Exception as e:
        log.warning(f"SubGram error: {e}")
        return "error"

SYSTEM_PROMPT = """Ты — дружелюбный кино-эксперт в Telegram. Помогаешь людям выбрать что посмотреть.

Правила:
- Отвечай только на русском языке
- Предлагай 3–5 конкретных фильмов или сериалов под запрос
- Для каждого: название (год) — одна яркая фраза почему стоит смотреть
- Используй эмодзи, но без фанатизма
- Если пользователь написал что-то не про кино — мягко верни к теме
- Стиль: живой и тёплый, как совет другу"""


def get_recommendations(user_text: str) -> str:
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=800,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_text},
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


def get_updates(offset: int = 0) -> list[dict]:
    try:
        r = requests.get(f"{TG_API}/getUpdates",
                         params={"offset": offset, "timeout": 30}, timeout=35)
        return r.json().get("result", [])
    except Exception:
        return []


WELCOME = """🎬 <b>Привет! Я @PosmotriBot.</b>

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
/help — эта справка"""


def handle_message(chat_id: int, user_id: int, text: str):
    cmd = text.strip().split("@")[0].lower()

    if cmd == "/help":
        send_message(chat_id, HELP)
        return

    # Проверяем подписку через SubGram
    status = check_subgram(user_id, chat_id)
    if status == "warning":
        return  # SubGram сам отправил блок с подпиской

    if cmd == "/start":
        send_message(chat_id, WELCOME)
        return

    send_typing(chat_id)
    reply = get_recommendations(text.strip())
    send_message(chat_id, reply)


def main():
    log.info("🎬 @PosmotriBot запущен!")
    offset = 0
    while True:
        updates = get_updates(offset)
        for update in updates:
            offset = update["update_id"] + 1
            try:
                msg     = update.get("message", {})
                chat_id = msg.get("chat", {}).get("id")
                user_id = msg.get("from", {}).get("id")
                text    = msg.get("text", "")
                if chat_id and user_id and text:
                    log.info(f"[{user_id}] {text[:60]}")
                    handle_message(chat_id, user_id, text)
            except Exception as e:
                log.error(f"Ошибка: {e}")
        time.sleep(1)


if __name__ == "__main__":
    main()

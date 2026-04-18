# 🎬 Movie & Series Recommendation Bot

Telegram-бот, который подбирает фильмы и сериалы по настроению или жанру.  
Работает на Claude AI + TMDB. Можно запустить на VPS, Railway или локально.

## Что умеет

- 🎭 Рекомендует фильмы и сериалы по описанию ("хочу что-то страшное")
- 🔍 Подбирает похожее ("что-то вроде Интерстеллара")
- 🔥 Показывает актуальные новинки из TMDB (`/новинки`)
- 💬 Общается как живой собеседник, а не выдаёт сухие списки

---

## ⚙️ Настройка

### Шаг 1. Создай бота

1. Напиши [@BotFather](https://t.me/BotFather) → `/newbot`
2. Придумай имя и username
3. Скопируй **токен**

### Шаг 2. Anthropic API Key

1. Зарегистрируйся на [console.anthropic.com](https://console.anthropic.com)
2. API Keys → Create Key → скопируй `sk-ant-...`

### Шаг 3. TMDB API Key (опционально, но рекомендуется)

1. Зарегистрируйся на [themoviedb.org](https://www.themoviedb.org/signup)
2. Settings → API → Request API Key (бесплатно)
3. Скопируй **API Key (v3 auth)**

---

## 🚀 Запуск

### Вариант A — Локально (для теста)

```bash
# Установи зависимости
pip install -r requirements.txt

# Задай переменные окружения
export TELEGRAM_TOKEN="твой_токен"
export ANTHROPIC_API_KEY="sk-ant-..."
export TMDB_API_KEY="твой_tmdb_ключ"   # необязательно

# Запусти
python bot.py
```

### Вариант B — Docker

```bash
docker build -t movie-bot .
docker run -d \
  -e TELEGRAM_TOKEN="твой_токен" \
  -e ANTHROPIC_API_KEY="sk-ant-..." \
  -e TMDB_API_KEY="твой_tmdb_ключ" \
  --name movie-bot \
  --restart unless-stopped \
  movie-bot
```

### Вариант C — Railway (бесплатный хостинг)

1. Зайди на [railway.app](https://railway.app) и создай проект
2. Подключи GitHub-репозиторий с этим кодом
3. В настройках проекта добавь переменные окружения:
   - `TELEGRAM_TOKEN`
   - `ANTHROPIC_API_KEY`
   - `TMDB_API_KEY`
4. Railway автоматически задеплоит бота

---

## 💬 Примеры запросов

| Что написать | Что получишь |
|---|---|
| `хочу что-то страшное` | Топ хорроров с описанием |
| `посоветуй комедию на вечер` | Лёгкие комедии |
| `что-то вроде Игры Престолов` | Похожие эпические сериалы |
| `хочу поплакать` | Мелодрамы и драмы |
| `документалки про природу` | Лучшие документальные |
| `/новинки` | Популярное прямо сейчас |

---

## 💰 Стоимость

- **Telegram Bot API**: бесплатно
- **TMDB API**: бесплатно
- **Anthropic API**: ~$0.005 за запрос → при 100 запросах/день ≈ $15/мес
- **Railway хостинг**: бесплатный tier (500 часов/месяц)

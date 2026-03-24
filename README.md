# GiftAnalystMarkets Bot

Production-ready MVP Telegram-бота аналитики GiftAnalystMarkets на Python 3.11+, aiogram 3.x, PostgreSQL, SQLAlchemy 2.x и Alembic.

## Что уже реализовано

- регистрация пользователя через `/start`
- хранение пользователей, настроек, сделок и логов синхронизации в PostgreSQL
- тестовая синхронизация сделок из mock GiftAnalystMarkets API
- статистика, список сделок, курс TON, экспорт в CSV/XLSX
- конструктор параметров экспорта
- лимит экспорта: `25` успешных выгрузок в день на пользователя
- подписка через Crypto Bot (Crypto Pay)
- первый месяц со скидкой 50%: `0.1 TON`
- далее базовый тариф: `3 TON` за `30` дней доступа
- защита аналитических разделов через paid access gate
- готовность к деплою на Render Background Worker

## Как работает оплата

В проекте реализован MVP-поток оплаты через Crypto Pay API:

1. Пользователь открывает экран `Подписка` или команду `/pay`.
2. Бот создаёт счёт в Crypto Pay на `0.1 TON` для первого платежа.
3. После первого успешного платежа скидка считается использованной.
4. Все последующие продления выставляются уже по `3 TON`.
5. Подписка активируется на `30` дней.

Важно: сейчас используется не webhook-сценарий, а polling/ручная проверка оплаты через кнопку `Проверить оплату`.
Это сделано специально, потому что текущий деплой — `Render Background Worker`, а не публичный HTTP-сервис.

## Стек

- Python 3.11+
- aiogram 3.x
- SQLAlchemy 2.x
- Alembic
- PostgreSQL
- httpx
- pydantic-settings
- openpyxl

## Структура проекта

```text
gift-analytics/
├── src/
├── migrations/
├── tests/
├── .env.example
├── requirements.txt
├── alembic.ini
├── render.yaml
└── README.md
```

## Быстрый старт локально

1. Создай виртуальное окружение:

```bash
python -m venv .venv
```

2. Установи зависимости:

```bash
pip install -r requirements.txt
```

3. Создай `.env` на основе `.env.example`.

4. Подними PostgreSQL.

5. Примени миграции:

```bash
alembic upgrade head
```

6. Запусти бота:

```bash
python -m src.main
```

## Основные переменные окружения

- `BOT_TOKEN` — токен Telegram-бота
- `DATABASE_URL` — строка подключения к PostgreSQL
- `GIFT_ANALYST_MARKETS_BASE_URL` — базовый URL legacy market sync API
- `GIFT_ANALYST_MARKETS_API_KEY` — API-ключ legacy market sync
- `GIFT_ANALYST_MARKETS_USE_MOCK_DATA` — включить mock-данные без реального API
- `TON_API_BASE_URL` — базовый URL TON API
- `TON_API_KEY` — ключ TON API
- `CRYPTO_PAY_BASE_URL` — `https://pay.crypt.bot` для mainnet или testnet URL
- `CRYPTO_PAY_API_TOKEN` — токен приложения Crypto Pay
- `CRYPTO_PAY_ASSET` — валюта оплаты, по умолчанию `TON`
- `CRYPTO_PAY_INVOICE_EXPIRES_IN` — TTL счёта в секундах
- `SUBSCRIPTION_INTRO_PRICE_TON` — цена первого месяца
- `SUBSCRIPTION_MONTHLY_PRICE_TON` — регулярная цена продления
- `SUBSCRIPTION_PERIOD_DAYS` — длительность доступа после оплаты
- `DAILY_EXPORT_LIMIT` — максимум успешных экспортов в день на одного пользователя
- `BUSINESS_TIMEZONE` — таймзона для суточных лимитов и бизнес-логики

## Как настроить Crypto Pay

1. Открой `@CryptoBot`.
2. Перейди в `Crypto Pay`.
3. Создай приложение.
4. Получи `API Token`.
5. Добавь токен в `.env`:

```env
CRYPTO_PAY_BASE_URL=https://pay.crypt.bot
CRYPTO_PAY_API_TOKEN=your_crypto_pay_token
CRYPTO_PAY_ASSET=TON
CRYPTO_PAY_INVOICE_EXPIRES_IN=3600
SUBSCRIPTION_INTRO_PRICE_TON=0.1
SUBSCRIPTION_MONTHLY_PRICE_TON=3
SUBSCRIPTION_PERIOD_DAYS=30
DAILY_EXPORT_LIMIT=25
BUSINESS_TIMEZONE=Europe/Moscow
```

Для тестирования можно использовать testnet-приложение и testnet URL.

## Команды бота

- `/start` — регистрация и главное меню
- `/help` — справка
- `/sync` — синхронизация сделок
- `/deals` — последние сделки
- `/stats` — статистика
- `/ton` — курс TON
- `/export` — экспорт CSV/XLSX
- `/pay` — экран подписки и оплаты
- `/settings` — настройки пользователя

## Экспорт

Команда `/export` поддерживает:

- быстрый экспорт в `CSV`
- быстрый экспорт в `XLSX`
- конструктор параметров по статусу, валюте отчёта, прибыли, периоду, лимиту строк и набору колонок
- суточный лимит `25` успешных экспортов на пользователя

## Миграции

Создание новой миграции:

```bash
alembic revision -m "describe_change"
```

Применение миграций:

```bash
alembic upgrade head
```

Новая платежная схема добавляется миграцией `0004_add_subscription_billing`.

## Deploy на Render

В репозитории уже есть `render.yaml` для `Background Worker` и PostgreSQL.

Базовый поток деплоя:

1. Подключить репозиторий в Render.
2. Создать Blueprint Deploy.
3. Заполнить секреты:
   - `BOT_TOKEN`
  - `GIFT_ANALYST_MARKETS_API_KEY` при необходимости
   - `TON_API_KEY` при необходимости
   - `CRYPTO_PAY_API_TOKEN`
4. Render сам поднимет PostgreSQL и передаст `DATABASE_URL` в worker.

## Что расширять дальше

- webhook endpoint для Crypto Pay, если бот будет вынесен в web service
- автообновление статуса подписки по cron/background task
- история платежей в админском интерфейсе
- отдельный экран истории экспортов и оставшегося дневного лимита
- реальная интеграция с GiftAnalystMarkets API
- unit/integration tests для платежного сервиса и репозиториев

# Deploy on REG.RU VPS

## 1. Connect to the server

```bash
ssh root@YOUR_SERVER_IP
```

## 2. Install Docker and Git

```bash
apt update && apt upgrade -y
apt install -y ca-certificates curl git
curl -fsSL https://get.docker.com | sh
```

## 3. Clone the project

```bash
git clone https://github.com/YOUXO15/giftanalystmarkets-bot.git
cd giftanalystmarkets-bot
```

## 4. Create the server `.env`

```bash
cp .env.example .env
nano .env
```

Minimum required values:

```env
APP_ENV=production
LOG_LEVEL=INFO

BOT_TOKEN=
BOT_POLLING_TIMEOUT=30

POSTGRES_DB=gift_analytics
POSTGRES_USER=gift_analytics_user
POSTGRES_PASSWORD=change_me_strong_password
DATABASE_URL=postgresql://gift_analytics_user:change_me_strong_password@postgres:5432/gift_analytics
DATABASE_ECHO=false

GIFT_ANALYST_MARKETS_USE_MOCK_DATA=false

TON_API_BASE_URL=https://tonapi.io
TON_API_KEY=

CRYPTO_PAY_BASE_URL=https://pay.crypt.bot
CRYPTO_PAY_API_TOKEN=
CRYPTO_PAY_ASSET=TON
CRYPTO_PAY_INVOICE_EXPIRES_IN=3600

SUBSCRIPTION_INTRO_PRICE_TON=0.1
SUBSCRIPTION_MONTHLY_PRICE_TON=3
SUBSCRIPTION_PERIOD_DAYS=30

DAILY_EXPORT_LIMIT=25
BUSINESS_TIMEZONE=Europe/Moscow
HTTP_TIMEOUT_SECONDS=15
```

## 5. Start containers

```bash
docker compose up -d --build
```

## 6. Check logs

```bash
docker compose logs -f bot
```

## 7. Useful commands

Restart bot:

```bash
docker compose restart bot
```

Stop everything:

```bash
docker compose down
```

Update project after `git pull`:

```bash
docker compose up -d --build
```

## Important

After the VPS bot starts, stop the local polling bot on your computer.  
Only one polling instance can work with the same Telegram token at a time.

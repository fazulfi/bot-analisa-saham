# Telegram setup (bot + chat_id)

1. Create bot with @BotFather -> copy token
2. Add bot to target group/channel and send a message
3. Call `https://api.telegram.org/bot<BOT_TOKEN>/getUpdates` to read chat.id
4. Set environment variables:
   - TELEGRAM_BOT_TOKEN
   - TELEGRAM_CHAT_ID
5. Local test:
   export TELEGRAM_BOT_TOKEN=...
   export TELEGRAM_CHAT_ID=-100123...
   python - <<PY
   from bot_analisa.notify.telegram import send_signal
   print(send_signal({"side":"buy","ticker":"PGAS.JK","entry_price":1000,"timestamp":"...","id":"s1"}))
   PY

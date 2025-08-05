import os
import logging
import asyncio
from flask import Flask, request, abort
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

def init_telegram_app():
    token = os.getenv("TELEGRAM_TOKEN")
    application = Application.builder().token(token).build()
    
    from ai_consulting_bot import start, handle_text
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    application.bot.initialize()
    logger.info("Telegram application initialized")
    
    return application

telegram_app = init_telegram_app()

@app.route("/", methods=["GET"])
def health_check():
    return "Bot is running", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    if request.headers.get("content-type") != "application/json":
        abort(403)
        
    try:
        data = request.get_json()
        update = Update.de_json(data, telegram_app.bot)
        telegram_app.update_queue.put(update)
        return "OK", 200
    except Exception as e:
        logger.error(f"Webhook processing error: {e}")
        return "Internal Server Error", 500

async def set_webhook():
    domain = os.getenv("RENDER_EXTERNAL_URL")
    if not domain:
        logger.error("RENDER_EXTERNAL_URL is not set!")
        return
    
    webhook_url = f"{domain}/webhook"
    await telegram_app.bot.set_webhook(webhook_url)
    
    bot_username = telegram_app.bot.username
    logger.info(f"Webhook set for bot @{bot_username} to: {webhook_url}")

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        loop.run_until_complete(set_webhook())
        
        port = int(os.environ.get("PORT", 5000))
        app.run(host="0.0.0.0", port=port)
    finally:
        loop.close()

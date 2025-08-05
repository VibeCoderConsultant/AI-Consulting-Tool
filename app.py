import os
import logging
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackContext
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
    
    return application

telegram_app = init_telegram_app()

@app.route("/", methods=["GET"])
def health_check():
    return "Bot is running", 200

@app.route("/webhook", methods=["POST"])
async def webhook():
    try:
        json_data = await request.get_json()
        update = Update.de_json(json_data, telegram_app.bot)
        await telegram_app.update_queue.put(update)
        return "", 200
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        return "", 500

async def set_webhook():
    domain = os.getenv("RENDER_EXTERNAL_URL")
    if not domain:
        logger.error("RENDER_EXTERNAL_URL is not set!")
        return
    
    webhook_url = f"{domain}/webhook"
    await telegram_app.bot.set_webhook(webhook_url)
    logger.info(f"Webhook set to: {webhook_url}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    
    loop = asyncio.get_event_loop()
    loop.run_until_complete(set_webhook())
    
    app.run(host="0.0.0.0", port=port)

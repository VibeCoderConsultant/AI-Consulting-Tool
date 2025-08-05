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
logger.info("Telegram application initialized")
logger.info(f"Bot username: {telegram_app.bot.username}")


@app.route("/", methods=["GET"])
def health_check():
    return "Bot is running", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    if request.headers.get("content-type") != "application/json":
        abort(403)
        
    try:
        data = request.get_json()
        logger.debug(f"Webhook data: {data}")
        update = Update.de_json(data, telegram_app.bot)
        telegram_app.update_queue.put(update)
        
        logger.info("Update processed successfully")
        return "OK", 200
    except Exception as e:
        logger.exception(f"Webhook processing failed: {e}")
        return "Internal Server Error", 500

async def set_webhook():
    domain = os.getenv("RENDER_EXTERNAL_URL")
    if not domain:
        logger.error("RENDER_EXTERNAL_URL is not set!")
        return
    
    webhook_url = f"{domain}/webhook"
    result = await telegram_app.bot.set_webhook(webhook_url)
    logger.info(f"Webhook set to: {webhook_url}, result: {result}")

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        loop.run_until_complete(set_webhook())
        
        port = int(os.environ.get("PORT", 5000))
        app.run(host="0.0.0.0", port=port)
    finally:
        loop.close()

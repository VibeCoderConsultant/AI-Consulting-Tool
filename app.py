import os
import logging
from flask import Flask, request, abort
from telegram import Bot, Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

TOKEN = os.environ["TELEGRAM_TOKEN"]
bot = Bot(TOKEN)
app = Flask(__name__)

application = (
    ApplicationBuilder()
    .token(TOKEN)
    .build()
)
from ai_consulting_bot import start, handle_text

application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

@app.route("/", methods=["GET"])
def health():
    return "OK", 200

@app.route(f"/webhook/{TOKEN}", methods=["POST"])
def webhook():
    if request.headers.get("content-type") != "application/json":
        abort(403)
    data = request.get_json(force=True)
    update = Update.de_json(data, bot)
    application.dispatcher.process_update(update)
    return "OK", 200

if __name__ == "__main__":
    domain = os.environ.get("RENDER_EXTERNAL_URL")  
    webhook_url = f"{domain}/webhook/{TOKEN}"
    bot.set_webhook(webhook_url)
    logger.info("Webhook set to %s", webhook_url)

    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

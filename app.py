import os
import logging
from flask import Flask, request, abort
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, filters

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

TOKEN = os.environ["TELEGRAM_TOKEN"]
BOT = Bot(TOKEN)
APP = Flask(__name__)

DP = Dispatcher(BOT, None, workers=0)
from AI_Consulting_Bot import start, handle_text

DP.add_handler(CommandHandler("start", start))
DP.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

@APP.route("/", methods=["GET"])
def health():
    return "OK", 200

@app.route(f"/webhook/{TOKEN}", methods=["POST"])
def webhook():
    if request.headers.get("content-type") != "application/json":
        abort(403)
    payload = request.get_data(as_text=True)
    update = Update.de_json(request.get_json(force=True), BOT)
    DP.process_update(update)
    return "OK", 200

if __name__ == "__main__":
    domain = os.environ.get("RENDER_EXTERNAL_URL") 
    webhook_url = f"{domain}/webhook/{TOKEN}"
    BOT.set_webhook(webhook_url)

    port = int(os.environ.get("PORT", 5000))
    APP.run(host="0.0.0.0", port=port)

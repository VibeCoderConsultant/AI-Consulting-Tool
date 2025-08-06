import os
import logging
import asyncio
from flask import Flask, request, abort
from concurrent.futures import ThreadPoolExecutor
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

executor = ThreadPoolExecutor()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.before_request
def log_all_requests():
    logger.info(f"👀 Входящий {request.method} на {request.path}")

def init_telegram_app():
    token = os.getenv("TELEGRAM_TOKEN")
    application = Application.builder().token(token).build()

    from ai_consulting_bot import start, handle_text

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("✅ Telegram application создана")
    return application

telegram_app = init_telegram_app()

@app.route("/", methods=["GET"])
def health_check():
    return "Bot is running", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    logger.info("→ Получен запрос в /webhook")
    logger.info(f"📩 RAW body: {request.data}")

    if request.headers.get("content-type") != "application/json":
        logger.warning("Invalid content-type")
        abort(400, "Invalid content-type")

    data = request.get_json(silent=True)
    if not data:
        logger.warning("Empty request body")
        abort(400, "Empty request body")

    try:
        update = Update.de_json(data, telegram_app.bot)

        def handle():
            asyncio.run(telegram_app.process_update(update))

        executor.submit(handle)

        return "OK", 200

    except Exception as e:
        logger.exception(f"❌ Ошибка при обработке апдейта: {e}")
        return "Internal Server Error", 500

async def setup_bot():
    try:
        await telegram_app.initialize()
        await telegram_app.start()
        logger.info("✅ Telegram application запущена")

        domain = os.getenv("RENDER_EXTERNAL_URL")
        if not domain:
            logger.error("❌ RENDER_EXTERNAL_URL не задан!")
            return False

        webhook_url = f"{domain}/webhook"
        result = await telegram_app.bot.set_webhook(webhook_url)
        logger.info(f"🔗 Webhook установлен: {webhook_url} (результат: {result})")

        webhook_info = await telegram_app.bot.get_webhook_info()
        logger.info(f"ℹ️ Webhook info: {webhook_info}")

        return True

    except Exception as e:
        logger.exception(f"❌ Setup bot failed: {e}")
        return False

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        success = loop.run_until_complete(setup_bot())
        if not success:
            logger.error("❌ Не удалось установить webhook, завершение")
            exit(1)

        port = int(os.environ.get("PORT", 5000))
        logger.info(f"🚀 Запуск Flask-сервера на порту {port}")
        app.run(host="0.0.0.0", port=port, use_reloader=False)

    except Exception as e:
        logger.exception(f"❌ Критическая ошибка при запуске: {e}")
    finally:
        loop.run_until_complete(telegram_app.stop())
        loop.close()

import os, sys
import time
import uuid
import requests
from dotenv import load_dotenv
from telegram import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes, CommandHandler

load_dotenv()
VERIFY_CERT_PATH = os.getenv("VERIFY_CERT_PATH")
AUTH_KEY = os.getenv("AUTH_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

token_cache = {"value": None, "ts": 0, "ttl": 36000}

if not os.getenv("TELEGRAM_TOKEN") or not os.getenv("AUTH_KEY"):
    print("Отсутствует TELEGRAM_TOKEN или AUTH_KEY")
    sys.exit(1)


def get_access_token() -> str:
    now = time.time()
    if token_cache["value"] and now - token_cache["ts"] < token_cache["ttl"]:
        return token_cache["value"]
    url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
        "RqUID": str(uuid.uuid4()),
        "Authorization": f"Basic {AUTH_KEY}"
    }
    resp = requests.post(url, headers=headers, data="scope=GIGACHAT_API_PERS", verify=VERIFY_CERT_PATH)
    resp.raise_for_status()
    token = resp.json()["access_token"]
    token_cache.update({"value": token, "ts": now})
    return token


def call_gigachat(messages: list, temperature: float, top_p: float = 0.9, max_tokens: int = 120) -> str:
    token = get_access_token()
    url = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {
        "model": "GigaChat",
        "messages": messages,
        "temperature": temperature,
        "top_p": top_p,
        "max_tokens": max_tokens
    }
    resp = requests.post(url, headers=headers, json=payload, verify=VERIFY_CERT_PATH)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


def build_rewrite_messages(text: str, lang: str) -> list:
    if lang == "en":
        system = (
            "You are a strategy consultant preparing slides for a business presentation in English. "
            "You will be given a business statement, possibly in another language (e.g., Russian)."
            "Your task is to: "
            "1. Translate the input into clear and professional English. "
            "2. Reformulate it into a concise, insightful presentation slide title (15-20 words) in only one sentence. "
            "3. Keep only the core idea, omit generic or verbose phrasing. "
            "Respond only in English."
        )
    else:
        system = (
            "Ты — консультант и готовишь заголовки слайдов для бизнес-презентации на русском языке. "
            "Тебе передают описание бизнес-ситуации в 10–20 словах. Текст может быть на другом языке (например, на английском). "
            "Твоя задача: "
            "1. Перевести его на русский. "
            "2. Переформулировать как и выразительный action заголовок для презентации в одном предложении на 15-20 слов. "
            "3. Сосредоточься на ключевой мысли, избегай общих формулировок, но не укроачивай ответ слишком сильно. "
            "Отвечай только на русском."
        )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": text}
    ]


def build_questions_messages(position, company, lang):
    if lang == "en":
        user = f"Formulate 5–7 strategic questions to ask a {position} at {company}. Use a numbered list."
    else:
        user = (
            f"Сформулируй 5–7 стратегических вопросов, которые можно задать сотруднику на позиции {position} "
            f"в компании {company}. Формат — нумерованный список."
        )
    return [{"role": "user", "content": user}]


def build_structure_messages(text, lang):
    if lang == "en":
        system = (
            "You are a strategy consultant. Given a couple of paragraphs about the client's task, goals, audience, and presentation format, "
            "Decompose the problem into subproblems and describe an approach to analyzing and generating initiatives and come up with slide headings."
        )
    else:
        system = (
            "Ты — стратегический консультант. Тебе дают пару абзацев про задачу клиента, цели, аудиторию и формат презентации. "
            "Декомпозируй проблему на подпроблемы и опиши подход к анализу и генерации инициатив и придумай заголовки слайдов."
        )
    return [{"role": "system", "content": system}, {"role": "user", "content": text}]


def build_hypotheses_messages(text, lang):
    if lang == "en":
        system = (
            "You are a consulting analyst. Given a brief problem description and market context, "
            "generate 6–8 hypotheses grouped by key drivers."
        )
    else:
        system = (
            "Ты — аналитик в консалтинге. Тебе дают описание проблемы и контекст рынка. "
            "Сгенерируй 6–8 гипотез, сгруппированных по драйверам."
        )
    return [{"role": "system", "content": system}, {"role": "user", "content": text}]


def build_frameworks_messages(text, lang):
    if lang == "en":
        system = (
            "You are a methodology consultant. Given a problem statement in 1-2 sentences, "
            "choose 2–3 analytical models or frameworks with justification and application approach."
        )
    else:
        system = (
            "Ты — консультант по методологиям. Тебе дают формулировку проблемы в 1–2 предложениях. "
            "Подбери 2–3 аналитические модели или фреймворка с обоснованием и описанием подхода."
        )
    return [{"role": "system", "content": system}, {"role": "user", "content": text}]


def make_kb(rows, with_menu=False):
    kb = rows.copy()
    if with_menu:
        kb.append(["Меню"])
    return ReplyKeyboardMarkup([[KeyboardButton(t) for t in row] for row in kb], resize_keyboard=True)


MODE_OPTIONS = {
    "Экшн-тайтлы": "action",
    "Вопросы": "questions",
    "Структура": "structure",
    "Гипотезы": "hypotheses",
    "Фреймворки": "frameworks"
}
LANG_OPTIONS = {"🇷🇺 Русский": "ru", "🇬🇧 Английский": "en"}
LANG_BUTTON = "Язык"


async def show_main_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data.setdefault("lang", "ru")
    ctx.user_data.setdefault("creativity", 3)
    ctx.user_data.setdefault("mode", "action")

    lang = ctx.user_data["lang"]


    if lang == "ru":
        msg = (
            "👋 Привет! Я ИИ-ассистент для стратегического консалтинга. Помогаю профессионалам готовить "
            "материалы для бизнес-презентаций, интервью и аналитических отчетов.\n\n"
            "⚙️ <b>Как я работаю:</b>\n"
            "1. Выберите сценарий работы\n"
            "2. Введите данные по инструкции\n"
            "3. Получите готовый результат за секунды\n"
            "4. Используйте кнопку \"Меню\" для возврата\n\n"
            "🚀 <b>Доступные сценарии:</b>\n"
            "🔁 <b>Экшн-тайтлы</b>: Превращаю сложные формулировки в лаконичные, эффектные заголовки для слайдов. "
            "Идеально для структурирования презентаций.\n\n"
            "❓ <b>Вопросы</b>: Генерирую стратегические вопросы для интервью с экспертами. Помогает подготовиться "
            "к встречам с топ-менеджерами и специалистами.\n\n"
            "🧩 <b>Структура</b>: Разрабатываю логичную структуру презентации на основе вашего описания задачи. "
            "Включаю заголовки слайдов и аналитический подход.\n\n"
            "🔍 <b>Гипотезы</b>: Формулирую проверяемые гипотезы для бизнес-проблем. Группирую по ключевым "
            "драйверам для системного анализа.\n\n"
            "⚙️ <b>Фреймворки</b>: Подбираю аналитические модели и фреймворки, наиболее подходящие для решения "
            "вашей задачи. С обоснованием и способом применения.\n\n"
            "🌐 Текущий язык: <b>Русский</b>\n"
        )
    else:
        msg = (
            "👋 Hello! I'm an AI consulting bot. I help prepare materials for business presentations:\n\n"
            "🔁 Action titles: reformulate phrase into title\n"
            "❓ Questions: generate interview questions\n"
            "🧩 Structure: prepare presentation storyline\n"
            "🔍 Hypotheses: generate problem hypotheses\n"
            "⚙️ Frameworks: select frameworks with descriptions\n\n"
            "Current language: English"
        )

    kb = [[key] for key in MODE_OPTIONS.keys()]
    kb.append([LANG_BUTTON])

    await update.message.reply_text(msg, reply_markup=make_kb(kb), parse_mode="HTML")
    await update.message.delete()


def scenario_instruction(mode, lang):
    if lang == "en":
        instr = {
            "action": (
                "You selected Action titles. Enter a phrase up to 200 characters.\n\n"
                "Example: Rising logistics costs are slowing business scaling"
            ),
            "questions": (
                "You selected Questions generator. Enter position and company in format:\n\n"
                "[position] at [company]\nExample: 'IT Director at VTB'"
            ),
            "structure": (
                "You selected Presentation structure. Enter 1-2 paragraphs about:\n"
                "- Client task\n- Goals\n- Audience\n- Presentation format\n\n"
                "Example: Client X wants to increase revenue through Y. Target audience is Z. Format: pitch deck."
            ),
            "hypotheses": (
                "You selected Hypotheses generator. Enter brief problem description and market context.\n\n"
                "Example: Online education market is declining due to falling demand. Competitors focus on B2B."
            ),
            "frameworks": (
                "You selected Framework selection. Describe your problem in 1-2 sentences.\n\n"
                "Example: Decrease in customer satisfaction with online purchases due to UX issues."
            )
        }
    else:
        instr = {
            "action": (
                "Вы выбрали режим генерации экшн-тайтлов. Введите фразу до 200 символов и я преобразую ее в заголовок.\n\n"
                "Пример ввода: Рост издержек на логистику замедляет масштабирование бизнеса"
            ),
            "questions": (
                "Вы выбрали режим генерации вопросов для интервью. Введите должность и компанию собеседника в формате:\n\n"
                "[должность] в [компания]\nПример ввода: 'Директор по ИТ в ВТБ'"
            ),
            "structure": (
                "Вы выбрали режим генерации структуры презентации. Введите пару предложений про:\n"
                "- Задачу клиента\n- Цели презентации\n- Аудиторию презентации\n- Формат презентации\n\n"
                "Пример ввода: Клиент X хочет увеличить выручку за счет Y. Целевая аудитория — Z. Формат — питч-дек."
            ),
            "hypotheses": (
                "Вы выбрали режим генерации гипотез. Введите краткое описание проблемы и внешний контекст, а я предложу гипотезы.\n\n"
                "Пример ввода: Рынок онлайн-образования падает из-за снижения спроса. Конкуренты фокусируются на B2B."
            ),
            "frameworks": (
                "Вы выбрали режим подбора фреймворков. Опишите проблему в нескольких предложениях, а я предложу фреймворки для анализа.\n\n"
                "Пример ввода: Снижение удовлетворенности клиентов при онлайн-покупках из-за UX."
            )
        }
    return instr.get(mode, "Ошибка: неизвестный сценарий." if lang == "ru" else "Error: unknown scenario.")


async def handle_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_data = ctx.user_data
    lang = user_data.get("lang", "ru")

    if text == "Меню":
        return await show_main_menu(update, ctx)

    if text == LANG_BUTTON:

        kb = [list(LANG_OPTIONS.keys()), ["Меню"]]
        msg = "Выберите язык / Choose language:" if lang == "ru" else "Select language:"
        await update.message.reply_text(msg, reply_markup=make_kb(kb))
        return

    if text in LANG_OPTIONS:
        user_data['lang'] = LANG_OPTIONS[text]
        lang_name = "Русский" if LANG_OPTIONS[text] == "ru" else "English"
        await update.message.reply_text(f"Язык изменен на {lang_name} / Language changed to {lang_name}")
        await show_main_menu(update, ctx)
        return

    if text.isdigit() and 1 <= int(text) <= 5:
        user_data['creativity'] = int(text)
        await update.message.reply_text(f"Креативность: {text}", reply_markup=make_kb([["Меню"]]))
        return

    if text in MODE_OPTIONS:
        mode = MODE_OPTIONS[text]
        user_data['mode'] = mode
        instr = scenario_instruction(mode, lang)
        await update.message.reply_text(instr, reply_markup=make_kb([["Меню"]]))
        return

    await update.message.reply_text("Обрабатываю..." if lang == "ru" else "Processing...",
                                    reply_markup=ReplyKeyboardRemove())
    mode = user_data['mode']

    try:
        if mode == 'action':
            msgs = build_rewrite_messages(text, lang)
            result = call_gigachat(msgs, 0.3, max_tokens=120)

        elif mode == 'questions':
            if lang == "ru":
                if " в " not in text:
                    raise ValueError("Используйте формат: [Должность] в [Компания]")
                pos, comp = text.split(" в ", 1)
            else:
                if " at " not in text:
                    raise ValueError("Use format: [Position] at [Company]")
                pos, comp = text.split(" at ", 1)

            msgs = build_questions_messages(pos.strip(), comp.strip(), lang)
            result = call_gigachat(msgs, 0.3, 0.9, 600)

        elif mode == 'structure':
            msgs = build_structure_messages(text, lang)
            result = call_gigachat(msgs, 0.5, 0.9, 400)

        elif mode == 'hypotheses':
            msgs = build_hypotheses_messages(text, lang)
            result = call_gigachat(msgs, 0.5, 0.9, 500)

        else:
            msgs = build_frameworks_messages(text, lang)
            result = call_gigachat(msgs, 0.5, 0.9, 500)

        await update.message.reply_text(result, reply_markup=make_kb([["Меню"]]))
    except Exception as e:
        error_msg = f"Ошибка: {e}" if lang == "ru" else f"Error: {e}"
        await update.message.reply_text(error_msg, reply_markup=make_kb([["Меню"]]))


def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", show_main_menu))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text))
    app.run_polling()


if __name__ == "__main__":
    main()

from telegram import Update, ReplyKeyboardRemove
from telegram.ext import ContextTypes

from bot.config import (
    MODE_OPTIONS, LANG_OPTIONS, LANG_BUTTON,
    REFINERS,
)
from bot.keyboards import make_kb, make_refiners_kb
from bot.gigachat import call_gigachat
from bot.prompts import (
    build_rewrite_messages, build_structure_messages,
    build_hypotheses_messages, build_frameworks_messages,
    build_refine_messages,
    build_questions_with_context, build_more_questions_messages, build_followups_messages,
    scenario_instruction,
)

BTN_MORE_Q = "Ещё вопросы"
BTN_FOLLOWUPS = "Фоллоу-апы"


def _parse_position_company(t: str, lang: str):
    sep = " в " if lang == "ru" else " at "
    if sep not in t:
        raise ValueError(
            "Используйте формат: [Должность] в [Компания]" if lang == "ru"
            else "Use format: [Position] at [Company]"
        )
    pos, comp = t.split(sep, 1)
    pos, comp = pos.strip(), comp.strip()
    if not pos or not comp:
        raise ValueError(
            "Укажите и должность, и компанию" if lang == "ru" else "Provide both position and company"
        )
    return pos, comp


async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data.setdefault("lang", "ru")
    ctx.user_data.setdefault("creativity", 3)
    ctx.user_data.setdefault("mode", "action")
    lang = ctx.user_data["lang"]

    if lang == "ru":
        msg = (
            "👋 Привет! Я ИИ-ассистент для стратегического консалтинга.\n\n"
            "Сценарии:\n"
            "🔁 Экшн-тайтлы — переформулировать короткую бизнес-фразу в заголовок\n"
            "❓ Вопросы — сгенерировать 5–7 вопросов для интервью\n"
            "🧩 Структура — построить цепочку «вопрос → гипотеза → слайд» + заголовки\n"
            "🔍 Гипотезы — сгенерировать 6–8 гипотез, сгруппированных по драйверам\n"
            "⚙️ Фреймворки — подобрать 2–3 модели анализа с обоснованием\n\n"
            "Выберите режим ниже или нажмите «Язык» для смены языка интерфейса и вывода."
        )
    else:
        msg = (
            "👋 Hello! I'm an AI consulting bot.\n\n"
            "Scenarios:\n"
            "🔁 Action titles — turn a short business phrase into a slide title\n"
            "❓ Questions — generate 5–7 interview questions\n"
            "🧩 Structure — build a chain “question → hypothesis → slide” + titles\n"
            "🔍 Hypotheses — generate 6–8 hypotheses grouped by drivers\n"
            "⚙️ Frameworks — suggest 2–3 analytical models with rationale\n\n"
            "Choose a scenario below or click on 'Language' to change the interface and output language."
        )

    kb = [["Экшн-тайтлы", "Вопросы"], ["Структура", "Гипотезы"], ["Фреймворки", LANG_BUTTON]]
    await update.message.reply_text(msg, reply_markup=make_kb(kb), parse_mode="HTML")
    try:
        await update.message.delete()
    except Exception:
        pass


async def handle_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    ud = ctx.user_data
    lang = ud.get("lang", "ru")

    if text == "Меню":
        ud.pop("q_state", None)
        ud.pop("q_session", None)
        return await start(update, ctx)

    if text == LANG_BUTTON:
        kb = [list(LANG_OPTIONS.keys()), ["Меню"]]
        msg = "Выберите язык / Choose language:" if lang == "ru" else "Select language:"
        return await update.message.reply_text(msg, reply_markup=make_kb(kb))
    if text in LANG_OPTIONS:
        ud["lang"] = LANG_OPTIONS[text]
        lang_name = "Русский" if ud["lang"] == "ru" else "English"
        await update.message.reply_text(f"Язык изменен на {lang_name} / Language changed to {lang_name}")
        return await start(update, ctx)

    if text in MODE_OPTIONS:
        mode = MODE_OPTIONS[text]
        ud["mode"] = mode

        if mode == "questions":
            ud["q_state"] = "await_pc"
            ud.pop("q_session", None)

        instr = scenario_instruction(mode, lang)
        return await update.message.reply_text(instr, reply_markup=make_kb([["Меню"]]))

    if ud.get("mode") == "questions":
        q_state = ud.get("q_state")

        if q_state == "await_pc":
            try:
                pos, comp = _parse_position_company(text, lang)
            except ValueError as e:
                return await update.message.reply_text(str(e), reply_markup=make_kb([["Меню"]]))

            ud["q_session"] = {"position": pos, "company": comp}
            ud["q_state"] = "await_context"

            hint = (
                "Теперь отдельным сообщением опишите контекст интервью (свободный ввод).\n"
                "Примеры: диагностика компании/функции, рост, снижение затрат, выход на рынок, "
                "цифровая трансформация, M&A/интеграция и т.д."
                if lang == "ru" else
                "Now describe the interview context in a separate message (free text).\n"
                "Examples: company/function diagnostics, growth, cost reduction, market entry, "
                "digital transformation, M&A/integration, etc."
            )
            return await update.message.reply_text(hint, reply_markup=make_kb([["Меню"]]))

        if q_state == "await_context":
            sess = ud.get("q_session") or {}
            pos, comp = sess.get("position"), sess.get("company")
            if not (pos and comp):
                ud["q_state"] = "await_pc"
                return await update.message.reply_text(
                    "Введите должность и компанию заново." if lang == "ru" else "Please enter position and company again.",
                    reply_markup=make_kb([["Меню"]])
                )

            context_txt = text
            await update.message.reply_text("Обрабатываю..." if lang == "ru" else "Processing...",
                                            reply_markup=ReplyKeyboardRemove())
            try:
                msgs = build_questions_with_context(pos, comp, context_txt, lang)
                result = call_gigachat(msgs, temperature=0.35, top_p=0.9, max_tokens=700)
                sess.update({"context": context_txt, "questions": result})
                ud["q_session"] = sess
                ud["q_state"] = "ready"

                ud["last_input"] = f"{pos} / {comp} / {context_txt}"
                ud["last_mode"] = "questions"
                ud["last_result"] = result

                kb = [[BTN_MORE_Q, BTN_FOLLOWUPS], ["Меню"]]
                return await update.message.reply_text(result, reply_markup=make_kb(kb))
            except Exception as e:
                return await update.message.reply_text(
                    ("Ошибка: " + str(e)) if lang == "ru" else ("Error: " + str(e)),
                    reply_markup=make_kb([["Меню"]])
                )

        if text == BTN_MORE_Q and ud.get("q_state") == "ready":
            sess = ud.get("q_session")
            if not (sess and sess.get("questions")):
                return await update.message.reply_text(
                    "Сначала сгенерируйте основной список вопросов." if lang == "ru"
                    else "Please generate the main list first.",
                    reply_markup=make_kb([["Меню"]])
                )

            pos, comp = sess["position"], sess["company"]
            context_txt = sess.get("context")
            prev_q = sess["questions"]

            await update.message.reply_text("Добавляю вопросы..." if lang == "ru" else "Adding more questions...",
                                            reply_markup=ReplyKeyboardRemove())
            try:
                msgs = build_more_questions_messages(pos, comp, context_txt, prev_q, lang)
                more = call_gigachat(msgs, temperature=0.35, top_p=0.9, max_tokens=500)
                sess["questions"] = prev_q + "\n\n" + more
                ud["q_session"] = sess
                ud["last_result"] = sess["questions"]

                kb = [[BTN_MORE_Q, BTN_FOLLOWUPS], ["Меню"]]
                return await update.message.reply_text(more, reply_markup=make_kb(kb))
            except Exception as e:
                return await update.message.reply_text(
                    ("Ошибка: " + str(e)) if lang == "ru" else ("Error: " + str(e)),
                    reply_markup=make_kb([["Меню"]])
                )

        if text == BTN_FOLLOWUPS and ud.get("q_state") == "ready":
            sess = ud.get("q_session")
            if not (sess and sess.get("questions")):
                return await update.message.reply_text(
                    "Сначала сгенерируйте вопросы." if lang == "ru"
                    else "Please generate questions first.",
                    reply_markup=make_kb([["Меню"]])
                )

            questions_text = sess["questions"]
            await update.message.reply_text("Готовлю фоллоу-апы..." if lang == "ru" else "Preparing follow-ups...",
                                            reply_markup=ReplyKeyboardRemove())
            try:
                msgs = build_followups_messages(questions_text, lang)
                followups = call_gigachat(msgs, temperature=0.35, top_p=0.9, max_tokens=700)
                kb = [[BTN_MORE_Q], ["Меню"]]
                return await update.message.reply_text(followups, reply_markup=make_kb(kb))
            except Exception as e:
                return await update.message.reply_text(
                    ("Ошибка: " + str(e)) if lang == "ru" else ("Error: " + str(e)),
                    reply_markup=make_kb([["Меню"]])
                )

        instr = scenario_instruction("questions", lang)
        return await update.message.reply_text(instr, reply_markup=make_kb([["Меню"]]))

    if text in sum(REFINERS.values(), []):
        base = ud.get("last_input")
        mode0 = ud.get("last_mode")
        draft = ud.get("last_result")
        if not base or not mode0:
            return await update.message.reply_text(
                "Сначала отправьте исходный запрос." if lang == "ru" else "Send an initial request first.",
                reply_markup=make_kb([["Меню"]])
            )

        await update.message.reply_text("Дорабатываю..." if lang == "ru" else "Refining...",
                                        reply_markup=ReplyKeyboardRemove())

        if mode0 == "action":
            msgs = build_refine_messages(mode0, lang, base, draft, text)
            refined = call_gigachat(msgs, temperature=0.5, top_p=0.9, max_tokens=240)
            ud["last_result"] = refined
            return await update.message.reply_text(refined, reply_markup=make_refiners_kb(mode0))
        else:
            return await update.message.reply_text(
                "Режим не поддерживает доработку этой кнопкой." if lang == "ru"
                else "This mode doesn't support that refinement.",
                reply_markup=make_kb([["Меню"]])
            )

    mode = ud.get("mode", "action")

    if mode == "action":
        await update.message.reply_text("Обрабатываю..." if lang == "ru" else "Processing...",
                                        reply_markup=ReplyKeyboardRemove())
        msgs = build_rewrite_messages(text, lang)
        result = call_gigachat(msgs, 0.3, top_p=0.9, max_tokens=120)

        ud["last_input"] = text
        ud["last_mode"] = "action"
        ud["last_result"] = result
        return await update.message.reply_text(result, reply_markup=make_refiners_kb("action"))

    if mode == "structure":
        await update.message.reply_text("Обрабатываю..." if lang == "ru" else "Processing...",
                                        reply_markup=ReplyKeyboardRemove())
        msgs = build_structure_messages(text, lang)
        result = call_gigachat(msgs, 0.5, 0.9, 800)
        ud.update({"last_input": text, "last_mode": "structure", "last_result": result})
        return await update.message.reply_text(result, reply_markup=make_kb([["Меню"]]))

    if mode == "hypotheses":
        await update.message.reply_text("Обрабатываю..." if lang == "ru" else "Processing...",
                                        reply_markup=ReplyKeyboardRemove())
        msgs = build_hypotheses_messages(text, lang)
        result = call_gigachat(msgs, 0.5, 0.9, 500)
        ud.update({"last_input": text, "last_mode": "hypotheses", "last_result": result})
        return await update.message.reply_text(result, reply_markup=make_kb([["Меню"]]))

    if mode == "frameworks":
        await update.message.reply_text("Обрабатываю..." if lang == "ru" else "Processing...",
                                        reply_markup=ReplyKeyboardRemove())
        msgs = build_frameworks_messages(text, lang)
        result = call_gigachat(msgs, 0.5, 0.9, 500)
        ud.update({"last_input": text, "last_mode": "frameworks", "last_result": result})
        return await update.message.reply_text(result, reply_markup=make_kb([["Меню"]]))

    kb = [["Экшн-тайтлы", "Вопросы"], ["Структура", "Гипотезы"], ["Фреймворки", LANG_BUTTON]]
    return await update.message.reply_text(
        "Выберите режим в меню" if lang == "ru" else "Choose a scenario in the menu",
        reply_markup=make_kb(kb),
    )

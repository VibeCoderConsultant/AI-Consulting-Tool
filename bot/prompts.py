
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
            "Ты — консультант по стратегии. Тебе дают короткий бизнес-ввод.\n"
    "Твоя задача — выдать ОДИН заголовок слайда (16–20 слов ИЛИ ≤150 символов) в деловом стиле.\n"
    "1) Сам выбери уместную рамку (ровно одну):\n"
    "   • Инсайт/вывод (что мы поняли и почему это важно)\n"
    "   • Контраст/бенчмарк (X vs Y → разрыв/импликация)\n"
    "   • Тренд/динамика (на фоне/в результате/из-за)\n"
    "   • Сценарий/прогноз (если/при/в сценарии → исход)\n"
    "   • Драйвер/гипотеза (что движет результатом)\n"
    "   • Решение/действие (что сделать, чтобы получить эффект)\n"
    "2) Сделай логику явной: используй связки типа «из-за/на фоне/в результате/что ведёт к/по сравнению с/если-то/при/чтобы».\n"
    "3) Зафиксируй субъект и масштаб (кто/что/где/когда), если это есть во вводе. Сохрани числа/единицы.\n"
    "4) Никаких списков и перечислений; одна связанная фраза. Без преамбул, кавычек, эмодзи и общих слов.\n"
    "5) Отвечай строго одной строкой на русском."
        )
    return [{"role":"system","content":system},{"role":"user","content":text}]

"""
def build_questions_messages(position: str, company: str, lang: str) -> list:
    if lang == "ru":
        user = (f"Сформулируй 5–7 стратегических вопросов, которые можно задать сотруднику на позиции {position} "
            f"в компании {company}. Формат — нумерованный список.")

    else:
        user = (
            f"Formulate 5–7 strategic questions to ask a {position} at {company}. "
            f"Use a numbered list."
        )
    return [{"role": "user", "content": user}]
"""
def parse_position_company(t: str, lang: str):
    sep = " в " if lang == "ru" else " at "
    if sep not in t:
        raise ValueError("Формат: [должность] в [компания]" if lang == "ru" else "Format: [position] at [company]")
    pos, comp = t.split(sep, 1)
    pos, comp = pos.strip(), comp.strip()
    if not pos or not comp:
        raise ValueError("Укажите и должность, и компанию" if lang == "ru" else "Provide both position and company")
    return pos, comp

def _q_common_header_ru(position, company, context=None):
    c = f" Контекст проекта: {context}." if context else ""
    return (
        f"Ты — стратегический консультант. Подготовь вопросы для интервью с {position} в {company}.{c} "
        "Требования:\n"
        "• вопросы открытые, без наводящих формулировок;\n"
        "• просить конкретику: период/метрики/ответственных/кейсы/артефакты;\n"
        "• избегай общих слов, каждый вопрос имеет фокус;\n"
        "• деловой стиль; формат — нумерованный список;\n"
        "• при необходимости добавляй короткий follow-up в скобках."
    )

def _q_common_header_en(position, company, context=None):
    c = f" Project context: {context}." if context else ""
    return (
        f"You are a strategy consultant. Prepare interview questions for a {position} at {company}.{c} "
        "Requirements: open, non-leading; push for specifics (timeframe, metrics, owners, cases, evidence); "
        "avoid generic phrasing; business tone; numbered list; short follow-up hints in parentheses when helpful."
    )

def build_questions_with_context(position, company, context, lang):
    header = _q_common_header_en(position, company, context) if lang == "en" else _q_common_header_ru(position, company, context)
    body = (
        "Сгенерируй 7–8 стратегических вопросов, чтобы понять цели, текущее состояние, ограничения, инициативы, риски и next steps. "
        "Каждый вопрос — про проверяемые факты; избегай расплывчатости."
        if lang == "ru" else
        "Generate 7–8 strategic questions to uncover goals, current state, constraints, initiatives, risks and next steps. "
        "Each question should target verifiable facts; avoid vagueness."
    )
    return [{"role": "system", "content": header}, {"role": "user", "content": body}]

def build_more_questions_messages(position, company, context, prev_questions_text, lang):
    header = _q_common_header_en(position, company, context) if lang == "en" else _q_common_header_ru(position, company, context)
    body = (
        "Сгенерируй ещё 3–5 новых вопросов без повторов и перефразов ранее полученных. "
        "Ориентируйся на другие аспекты/углы зрения. В ответе не цитируй старые вопросы.\n\n"
        f"Ранее сгенерированные вопросы:\n{prev_questions_text}"
        if lang == "ru" else
        "Generate 3–5 additional NEW questions with no duplicates or paraphrases of the previous ones. "
        "Explore other angles. Do NOT quote previous questions verbatim.\n\n"
        f"Previously generated questions:\n{prev_questions_text}"
    )
    return [{"role": "system", "content": header}, {"role": "user", "content": body}]

def build_followups_messages(questions_text, lang):
    system = (
        "Для каждого вопроса ниже предложи 1–2 follow-up подсказки (в скобках): какие уточнения задать, какие факты/метрики запросить, "
        "как почелленджить ответ. Формат — сохранить исходную нумерацию."
        if lang == "ru" else
        "For each question below, provide 1–2 follow-up hints (in parentheses): what to clarify, which facts/metrics to ask for, how to challenge. "
        "Keep the original numbering."
    )
    user = f"Вопросы:\n{questions_text}" if lang == "ru" else f"Questions:\n{questions_text}"
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]

def build_structure_messages(text, lang):
    if lang == "en":
        system = (
            "You are a strategy consultant. Input: 1–2 paragraphs with client task, goals, audience, format."
            "Output (Markdown): 1) Context (1–2 sentences: client, main goal, key constraint)."
            "2) 8–12 slides. For each: Action title (≤85 chars); Why (so-what, 1 line);"
            "Key analyses/data (3–5 bullets, concrete); Metrics/outcome (1–2)."
            "3) Roadmap 5–7 initiatives: priority (H/M/L), owner (role), timeline (quarter), expected effect."
            "4) Assumptions & Risks (2–4 each)."
            "Rules: avoid vague verbs; use testable specifics."
            "Each slide must support hypotheses and lead to the roadmap. Follow audience/format from input."
            "If data missing, state assumptions."

        )
    else:
        system = (
            "Ты — стратегический консультант. На вход даётся 1–2 абзаца с задачей клиента, целями, аудиторией и форматом."
            "Выведи структуру презентации (Markdown) строго так:"
            "1) Контекст (1–2 предложения: клиент, главная цель, ключевое ограничение)."
            "2) 9–12 слайдов. Для каждого: So What (1 строка, зачем нужен слайд);"
            "Ключевые анализы/данные (3–5 буллета, конкретика) с конкретными метриками"
            "Правила: никаких общих слов («улучшить», «оптимизировать») — только проверяемая конкретика."
            "Каждый слайд должен подтверждать гипотезы и вести к roadmap."
            "Ориентируйся на указанную во входе аудиторию и формат."
            "Если данных не хватает — явно фиксируй допущения."
        )
    return [{"role":"system","content":system},{"role":"user","content":text}]

def build_hypotheses_messages(text, lang):
    if lang == "en":
        system = (
            "You are a consulting analyst. Given a brief problem description and market context, "
            "generate 6–8 hypotheses grouped by key drivers."
        )
    else:
        system = (
            "Ты — аналитик в консалтинге. Тебе дают описание проблемы и контекст рынка. "
            "Сгенерируй 6–8 гипотез, сгруппированных по драйверам. "
            "Для каждой напиши 2-3 примера данных с источниками для проверки (внутри компании и за ее пределами)."
        )
    return [{"role":"system","content":system},{"role":"user","content":text}]

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
    return [{"role":"system","content":system},{"role":"user","content":text}]

def build_refine_messages(mode: str, lang: str, base_text: str, draft: str | None, command: str) -> list:
    if mode == "action":
        if lang == "en":
            system = "You improve slide titles for executive presentations. Output MUST be a short list, no prose."
            style = {
                "Ещё варианты": "Produce 3 ALTERNATIVE titles. Keep one-sentence, punchy, business tone.",
                "Короче": "Return 1 title SHORTER and sharper than the draft.",
                "Длинее": "Return 1 title with LONGER and more detailed, but within the limits of the restrictions.",
                "Ближе к исходнику": "Return 1 title closer to the original wording: keep the terminology and nuances of the original input.",
                "Больше креатива": "Suggest an alternative formulation in one line (< 140 characters), changing the angle of view, but preserving the facts and the causal link.",
            }[command]
            user = (
                f"Original input: {base_text}\nCurrent draft: {draft}\n{style}\n"
                "Constraints: 1 sentence each; up to 140 chars; no fluff."
            )
        else:
            system = "Ты улучшаешь заголовки слайдов для руководителей. Вывод — краткий список, без лишнего текста."
            style = {
                "Ещё варианты": "Дай 3 АЛЬТЕРНАТИВНЫХ заголовка. Один оборот, деловой тон.",
                "Короче": "Дай 1 заголовок КОРОЧЕ и острее текущего.",
                "Длиннее": "Дай 1 заголовок длиннее и подробнее текущего, но в рамках ограничений.",
                "Ближе к исходнику": "Перепиши заголовок ближе к исходной формулировке: сохрани терминологию и нюансы исходного ввода",
                "Больше креатива": "Предложи альтернативную формулировку одной строкой (≤140 символов), меняя угол зрения, но сохраняя факты и причинно-следственную связку. Избегай клише. Без преамбул.",
            }[command]
            user = (
                f"Исходный ввод: {base_text}\nТекущий черновик: {draft}\n{style}\n"
                "Ограничения: 1 предложение; до 140 символов; без воды."
            )
        return [{"role":"system","content":system},{"role":"user","content":user}]
    return [{"role":"user","content": base_text}]

def scenario_instruction(mode, lang):
    if lang == "en":
        instr = {
            "action": "You selected Action titles. Enter a phrase up to 150 characters.\n\nExample: Rising logistics costs are slowing business scaling.",
            "questions": "You selected Questions. Enter: [position] at [company]\nExample: IT Director at a bank.",
            "structure": "You selected Structure. Enter 1–2 paragraphs about client task, goals, audience, format.",
            "hypotheses": "You selected Hypotheses. Enter brief problem & market context.",
            "frameworks": "You selected Frameworks. Enter a 1–2 sentence problem statement."
        }
    else:
        instr = {
            "action": "Вы выбрали Экшн-тайтлы. \n\nВведите бизнес-фразу до 250 символов.\nПример: 'Рост издержек на логистику вследствие введения торговых пошлин замедляет масштабирование бизнеса в нвоых регионах'.\n\n"
                      "Вы также можете внести изменения в сгенерированный тайтл, используя кнопки в интерфейсе.",
            "questions": "Вы выбрали Вопросы.\n\n Введите: [должность] в [компания]\nПример: директор по ИТ в банке.",
            "structure": "Вы выбрали Структуру.\n\nВведите пару абзацев о задаче, целях, аудитории и формате.",
            "hypotheses": "Вы выбрали Гипотезы.\n\nВведите описание проблемы и внешний контекст.",
            "frameworks": "Вы выбрали Фреймворки.\n\nВведите формулировку проблемы в 1–2 предложениях."
        }
    return instr.get(mode, "Ошибка: неизвестный сценарий." if lang == "ru" else "Error: unknown scenario.")

def build_press_test_messages(mode: str, lang: str, user_input: str, draft: str | None):
    if lang == "en":
        user = (
            f"PRESS TEST the draft for mode={mode}.\nInput brief: {user_input}\nDraft:\n{draft}\n\n"
            "Return 4 blocks:\n1) Risks/assumptions\n2) Blind spots\n3) Missing data\n4) Follow-up questions\n"
            "Be concise and actionable."
        )
    else:
        user = (
            f"Сделай ПРЕСС-ТЕСТ черновика для режима={mode}.\nВводные: {user_input}\nЧерновик:\n{draft}\n\n"
            "Верни 4 блока:\n1) Риски/допущения\n2) Слепые зоны\n3) Чего не хватает в данных\n4) Вопросы-фоллоу-апы\n"
            "Коротко и по делу."
        )
    return [{"role": "user", "content": user}]

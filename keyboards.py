from telegram import ReplyKeyboardMarkup, KeyboardButton
from bot.config import REFINERS

def make_kb(rows, with_menu=False):
    kb = rows.copy()
    if with_menu and ["Меню"] not in kb:
        kb.append(["Меню"])
    return ReplyKeyboardMarkup([[KeyboardButton(t) for t in row] for row in kb], resize_keyboard=True)

def make_refiners_kb(mode: str):
    btns = REFINERS.get(mode, [])
    rows = []
    if btns:
        chunk = 3 if mode == "action" else 2
        rows = [btns[i:i+chunk] for i in range(0, len(btns), chunk)]
    rows.append(["Меню"])
    return make_kb(rows)
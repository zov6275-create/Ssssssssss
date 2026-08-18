"""
🎰 FriendsCasino — Telegram Bot
Запуск: pip install aiogram aiofiles && python casino_bot.py
"""

import asyncio
import json
import os
import random
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# ─── Конфиг ───────────────────────────────────────────────────────────────────
BOT_TOKEN = os.getenv("8995809056:AAFoy5r0VUrMDJtJ98eHDc4xLTaVy459_2I")
DB_FILE   = "casino_db.json"
START_BALANCE = 1000

# ─── База данных (JSON-файл) ───────────────────────────────────────────────────
def load_db() -> dict:
    if Path(DB_FILE).exists():
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_db(db: dict):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

def get_user(db: dict, uid: int, name: str) -> dict:
    key = str(uid)
    if key not in db:
        db[key] = {"name": name, "balance": START_BALANCE, "history": [], "stats": {"wins": 0, "losses": 0}}
        save_db(db)
    return db[key]

def update_user(db: dict, uid: int, data: dict):
    db[str(uid)].update(data)
    save_db(db)

def add_history(db: dict, uid: int, game: str, bet: int, result: str, delta: int):
    user = db[str(uid)]
    user["history"] = ([{"game": game, "bet": bet, "result": result, "delta": delta}]
                       + user["history"])[:20]
    if delta > 0:
        user["stats"]["wins"] += 1
    elif delta < 0:
        user["stats"]["losses"] += 1
    save_db(db)

# ─── Состояния FSM ────────────────────────────────────────────────────────────
class BetState(StatesGroup):
    waiting_bet = State()
    game_active  = State()

# ─── Клавиатуры ───────────────────────────────────────────────────────────────
def main_menu_kb():
    return ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[
        [KeyboardButton(text="🎲 Чёт/Нечет"), KeyboardButton(text="📊 Больше/Меньше")],
        [KeyboardButton(text="🎰 Слоты"),      KeyboardButton(text="🎯 Дартс")],
        [KeyboardButton(text="🎳 Боулинг"),    KeyboardButton(text="🤖 Бот-дуэль")],
        [KeyboardButton(text="💰 Баланс"),     KeyboardButton(text="📋 История")],
        [KeyboardButton(text="🏆 Топ игроков")],
    ])

def bet_kb():
    buttons = [[
        InlineKeyboardButton(text="25 🪙",  callback_data="bet_25"),
        InlineKeyboardButton(text="50 🪙",  callback_data="bet_50"),
        InlineKeyboardButton(text="100 🪙", callback_data="bet_100"),
    ],[
        InlineKeyboardButton(text="200 🪙", callback_data="bet_200"),
        InlineKeyboardButton(text="500 🪙", callback_data="bet_500"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="bet_cancel"),
    ]]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def oe_kb():
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🟢 Чётное", callback_data="oe_even"),
        InlineKeyboardButton(text="🔴 Нечётное", callback_data="oe_odd"),
    ]])

def hl_kb():
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="📈 Больше 5", callback_data="hl_higher"),
        InlineKeyboardButton(text="📉 Меньше 5", callback_data="hl_lower"),
    ]])

def slot_mode_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⚡ Классик (×1)",  callback_data="slot_classic"),
            InlineKeyboardButton(text="🍀 Удача (×2)",   callback_data="slot_lucky"),
        ],[
            InlineKeyboardButton(text="💎 Мега (×3)",    callback_data="slot_mega"),
            InlineKeyboardButton(text="❌ Отмена",        callback_data="bet_cancel"),
        ]
    ])

def dart_kb():
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🎯 Бросить!",  callback_data="dart_throw"),
        InlineKeyboardButton(text="❌ Стоп",       callback_data="bet_cancel"),
    ]])

def bowl_aim_kb():
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="⬅️ Влево",  callback_data="bowl_left"),
        InlineKeyboardButton(text="🎳 Бросить", callback_data="bowl_throw"),
        InlineKeyboardButton(text="➡️ Вправо", callback_data="bowl_right"),
    ],[
        InlineKeyboardButton(text="❌ Отмена", callback_data="bet_cancel"),
    ]])

def bot_duel_kb():
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🟢 Чётное", callback_data="bot_even"),
        InlineKeyboardButton(text="🔴 Нечётное", callback_data="bot_odd"),
    ]])

# ─── Утилиты ──────────────────────────────────────────────────────────────────
DICE_EMOJI = ["⚀","⚁","⚂","⚃","⚄","⚅"]
SLOT_SYMBOLS = ["🍒","🍋","🍇","⭐","🔔","💎","🍀","7️⃣"]

def dice_roll():
    return random.randint(1, 6)

def spin_slots():
    return [random.choice(SLOT_SYMBOLS) for _ in range(3)]

def dart_score():
    # Симулируем бросок: случайное расстояние от центра
    dist = random.gauss(50, 30)
    dist = max(0, min(100, abs(dist)))
    if dist < 10:   return 50
    elif dist < 25: return 25
    elif dist < 45: return 15
    elif dist < 65: return 10
    elif dist < 85: return 5
    return 0

BOT_PHRASES_WIN  = ["Ха! Везёт тебе! 😄", "Ладно, ты выиграл... на этот раз.", "Удача на твоей стороне!", "Хм, неплохо!"]
BOT_PHRASES_LOSE = ["Я знал! Чистый анализ 🤖", "Алгоритм не обманешь!", "Берегись — я разогреваюсь! 😤", "Бот побеждает снова!"]
BOT_PHRASES_DRAW = ["Ничья! Ты не так прост...", "Интересно... продолжим?", "Равная игра!"]

# ─── Временное хранилище сессий ───────────────────────────────────────────────
# {uid: {"game": ..., "bet": ..., "data": {...}}}
sessions: dict = {}

# ─── Инициализация ────────────────────────────────────────────────────────────
bot = Bot(token=BOT_TOKEN)
dp  = Dispatcher(storage=MemoryStorage())
db  = load_db()

# ═══════════════════════════════════════════════════════════════════════════════
# ОБРАБОТЧИКИ
# ═══════════════════════════════════════════════════════════════════════════════

@dp.message(CommandStart())
async def cmd_start(msg: Message):
    user = get_user(db, msg.from_user.id, msg.from_user.first_name)
    text = (
        f"🎰 *Добро пожаловать в FriendsCasino, {msg.from_user.first_name}!*\n\n"
        f"{'🆕 Тебе начислено' if user['balance'] == START_BALANCE else '👋 С возвращением!'} "
        f"*{user['balance']} 🪙 поинтов*\n\n"
        "Выбери игру в меню ниже и удачи!\n"
        "_Все игры без реального депозита — только фан!_"
    )
    await msg.answer(text, parse_mode="Markdown", reply_markup=main_menu_kb())

@dp.message(F.text == "💰 Баланс")
async def cmd_balance(msg: Message):
    user = get_user(db, msg.from_user.id, msg.from_user.first_name)
    s = user["stats"]
    total = s["wins"] + s["losses"]
    wr = round(s["wins"]/total*100) if total else 0
    await msg.answer(
        f"💳 *Твой баланс:* {user['balance']} 🪙\n\n"
        f"📊 Статистика:\n"
        f"✅ Побед: {s['wins']} | ❌ Поражений: {s['losses']}\n"
        f"🎯 Винрейт: {wr}%",
        parse_mode="Markdown"
    )

@dp.message(F.text == "📋 История")
async def cmd_history(msg: Message):
    user = get_user(db, msg.from_user.id, msg.from_user.first_name)
    h = user["history"]
    if not h:
        await msg.answer("📋 История пуста — сыграй первую партию!")
        return
    lines = []
    for item in h[:10]:
        sign = "+" if item["delta"] > 0 else ""
        emoji = "✅" if item["delta"] > 0 else "❌"
        lines.append(f"{emoji} {item['game']} | {item['result']} | {sign}{item['delta']} 🪙")
    await msg.answer("📋 *Последние игры:*\n\n" + "\n".join(lines), parse_mode="Markdown")

@dp.message(F.text == "🏆 Топ игроков")
async def cmd_top(msg: Message):
    db_fresh = load_db()
    top = sorted(db_fresh.values(), key=lambda x: x["balance"], reverse=True)[:10]
    lines = []
    medals = ["🥇","🥈","🥉"] + ["🎖️"]*7
    for i, u in enumerate(top):
        lines.append(f"{medals[i]} {u['name']} — {u['balance']} 🪙")
    await msg.answer("🏆 *Топ игроков:*\n\n" + "\n".join(lines), parse_mode="Markdown")

# ─── ЧЁТ / НЕЧЕТ ─────────────────────────────────────────────────────────────
@dp.message(F.text == "🎲 Чёт/Нечет")
async def game_oe_start(msg: Message):
    user = get_user(db, msg.from_user.id, msg.from_user.first_name)
    if user["balance"] < 25:
        await msg.answer("❌ Недостаточно поинтов! Минимум 25 🪙"); return
    sessions[msg.from_user.id] = {"game": "oe", "bet": 50}
    await msg.answer(
        "🎲 *Чёт или Нечет*\n\nВыбери размер ставки:",
        parse_mode="Markdown", reply_markup=bet_kb()
    )

@dp.callback_query(F.data.startswith("bet_"))
async def process_bet(cb: CallbackQuery):
    uid = cb.from_user.id
    if cb.data == "bet_cancel":
        sessions.pop(uid, None)
        await cb.message.edit_text("❌ Отменено.")
        return
    bet = int(cb.data.split("_")[1])
    user = get_user(db, uid, cb.from_user.first_name)
    if user["balance"] < bet:
        await cb.answer("Недостаточно поинтов!", show_alert=True); return
    if uid not in sessions:
        await cb.answer("Сессия устарела. Начни заново.", show_alert=True); return
    sessions[uid]["bet"] = bet
    game = sessions[uid]["game"]

    if game == "oe":
        await cb.message.edit_text(
            f"🎲 *Чёт или Нечет*\nСтавка: *{bet} 🪙*\n\nВыбирай:", parse_mode="Markdown",
            reply_markup=oe_kb()
        )
    elif game == "hl":
        await cb.message.edit_text(
            f"📊 *Больше или Меньше*\nСтавка: *{bet} 🪙*\n\nЧисло от 1 до 10. Угадай: больше 5 или меньше?",
            parse_mode="Markdown", reply_markup=hl_kb()
        )
    elif game == "slot":
        await cb.message.edit_text(
            f"🎰 *Слоты*\nСтавка: *{bet} 🪙*\n\nВыбери режим:", parse_mode="Markdown",
            reply_markup=slot_mode_kb()
        )
    elif game == "dart":
        sessions[uid]["data"] = {"throws": 3, "score": 0}
        await cb.message.edit_text(
            f"🎯 *Дартс*\nСтавка: *{bet} 🪙*\n\nУ тебя 3 броска. Нужно набрать 60+ очков!\nБроски: 3 осталось",
            parse_mode="Markdown", reply_markup=dart_kb()
        )
    elif game == "bowl":
        sessions[uid]["data"] = {"pins": [True]*10, "throws": 0, "aim": 50}
        await cb.message.edit_text(
            f"🎳 *Боулинг*\nСтавка: *{bet} 🪙*\n\n{render_pins([True]*10)}\n🎯 Прицел: 50% | Настрой прицел и бросай!",
            parse_mode="Markdown", reply_markup=bowl_aim_kb()
        )
    elif game == "bot":
        await cb.message.edit_text(
            f"🤖 *Бот-дуэль*\nСтавка: *{bet} 🪙*\n\n_Бот выбирает чёт или нечет втайне..._\nТвой ход:", 
            parse_mode="Markdown", reply_markup=bot_duel_kb()
        )
    await cb.answer()

# ─── Чёт/Нечет результат ─────────────────────────────────────────────────────
@dp.callback_query(F.data.startswith("oe_"))
async def process_oe(cb: CallbackQuery):
    uid = cb.from_user.id
    if uid not in sessions: await cb.answer("Сессия устарела", show_alert=True); return
    bet = sessions[uid]["bet"]
    choice = cb.data.split("_")[1]
    num = dice_roll()
    is_even = num % 2 == 0
    win = (choice == "even" and is_even) or (choice == "odd" and not is_even)
    delta = bet if win else -bet
    user = get_user(db, uid, cb.from_user.first_name)
    user["balance"] += delta
    update_user(db, uid, {"balance": user["balance"]})
    add_history(db, uid, "Чёт/Нечет", bet, f"{DICE_EMOJI[num-1]} {num}", delta)
    sessions.pop(uid, None)
    result_text = (
        f"{'✅ ПОБЕДА!' if win else '❌ Не повезло!'}\n\n"
        f"Кубик: {DICE_EMOJI[num-1]} *{num}* ({'чётное' if is_even else 'нечётное'})\n"
        f"Твой выбор: {'чётное' if choice=='even' else 'нечётное'}\n\n"
        f"{'🎉 +' if win else '💸 '}{delta} 🪙 | Баланс: {user['balance']} 🪙"
    )
    await cb.message.edit_text(result_text, parse_mode="Markdown")
    await cb.answer()

# ─── Больше/Меньше ───────────────────────────────────────────────────────────
@dp.message(F.text == "📊 Больше/Меньше")
async def game_hl_start(msg: Message):
    user = get_user(db, msg.from_user.id, msg.from_user.first_name)
    if user["balance"] < 25:
        await msg.answer("❌ Недостаточно поинтов!"); return
    sessions[msg.from_user.id] = {"game": "hl", "bet": 50}
    await msg.answer("📊 *Больше/Меньше*\n\nВыбери ставку:", parse_mode="Markdown", reply_markup=bet_kb())

@dp.callback_query(F.data.startswith("hl_"))
async def process_hl(cb: CallbackQuery):
    uid = cb.from_user.id
    if uid not in sessions: await cb.answer("Сессия устарела", show_alert=True); return
    bet = sessions[uid]["bet"]
    choice = cb.data.split("_")[1]
    num = random.randint(1, 10)
    win = (choice == "higher" and num > 5) or (choice == "lower" and num < 5)
    delta = bet if win else -bet
    user = get_user(db, uid, cb.from_user.first_name)
    user["balance"] += delta
    update_user(db, uid, {"balance": user["balance"]})
    add_history(db, uid, "Больше/Меньше", bet, str(num), delta)
    sessions.pop(uid, None)
    await cb.message.edit_text(
        f"{'✅ ПОБЕДА!' if win else '❌ Мимо!'}\n\n"
        f"Выпало: *{num}* ({'больше' if num>5 else 'меньше'if num<5 else 'ровно'} 5)\n"
        f"Твой выбор: {'больше' if choice=='higher' else 'меньше'} 5\n\n"
        f"{'🎉 +' if win else '💸 '}{delta} 🪙 | Баланс: {user['balance']} 🪙",
        parse_mode="Markdown"
    )
    await cb.answer()

# ─── Слоты ───────────────────────────────────────────────────────────────────
@dp.message(F.text == "🎰 Слоты")
async def game_slots_start(msg: Message):
    user = get_user(db, msg.from_user.id, msg.from_user.first_name)
    if user["balance"] < 25:
        await msg.answer("❌ Недостаточно поинтов!"); return
    sessions[msg.from_user.id] = {"game": "slot", "bet": 50}
    await msg.answer("🎰 *Слоты*\n\nВыбери ставку:", parse_mode="Markdown", reply_markup=bet_kb())

SLOT_MULTS = {"classic": 1, "lucky": 2, "mega": 3}
SLOT_LABELS = {"classic": "Классик ×1", "lucky": "Удача ×2", "mega": "Мега ×3"}

@dp.callback_query(F.data.startswith("slot_"))
async def process_slot_mode(cb: CallbackQuery):
    uid = cb.from_user.id
    if uid not in sessions: await cb.answer("Сессия устарела", show_alert=True); return
    mode = cb.data.split("_")[1]
    if mode not in SLOT_MULTS: return
    bet = sessions[uid]["bet"]
    mult = SLOT_MULTS[mode]
    reels = spin_slots()
    all_match = reels[0] == reels[1] == reels[2]
    partial = not all_match and (reels[0]==reels[1] or reels[1]==reels[2] or reels[0]==reels[2])
    if all_match:    delta = bet * 3 * mult
    elif partial:    delta = bet // 2
    else:            delta = -bet
    user = get_user(db, uid, cb.from_user.first_name)
    user["balance"] += delta
    update_user(db, uid, {"balance": user["balance"]})
    add_history(db, uid, f"Слоты ({SLOT_LABELS[mode]})", bet, "".join(reels), delta)
    sessions.pop(uid, None)
    if all_match:    header = "🎉 ДЖЕКПОТ!!!"
    elif partial:    header = "💫 Частичный матч!"
    else:            header = "❌ Нет совпадений"
    await cb.message.edit_text(
        f"{header}\n\n{'  '.join(reels)}\n\n"
        f"Режим: {SLOT_LABELS[mode]}\n"
        f"{'🎉 +' if delta>0 else '💸 '}{delta} 🪙 | Баланс: {user['balance']} 🪙",
        parse_mode="Markdown"
    )
    await cb.answer()

# ─── Дартс ───────────────────────────────────────────────────────────────────
@dp.message(F.text == "🎯 Дартс")
async def game_dart_start(msg: Message):
    user = get_user(db, msg.from_user.id, msg.from_user.first_name)
    if user["balance"] < 25:
        await msg.answer("❌ Недостаточно поинтов!"); return
    sessions[msg.from_user.id] = {"game": "dart", "bet": 50}
    await msg.answer("🎯 *Дартс*\n\nВыбери ставку:", parse_mode="Markdown", reply_markup=bet_kb())

DART_ZONES = [(50,"🏆 В яблочко! 50 очков!"),(25,"🎯 Отличный бросок! 25 очков"),(15,"👍 Хороший бросок! 15 очков"),(10,"😐 Неплохо. 10 очков"),(5,"😬 Почти... 5 очков"),(0,"💨 Мимо! 0 очков")]

@dp.callback_query(F.data == "dart_throw")
async def process_dart(cb: CallbackQuery):
    uid = cb.from_user.id
    if uid not in sessions: await cb.answer("Сессия устарела", show_alert=True); return
    s = sessions[uid]
    pts = dart_score()
    s["data"]["score"] += pts
    s["data"]["throws"] -= 1
    remaining = s["data"]["throws"]
    total = s["data"]["score"]
    label = next(l for p, l in DART_ZONES if pts >= p)
    if remaining > 0:
        await cb.message.edit_text(
            f"🎯 *Дартс*\n\n{label}\n\n"
            f"Очков набрано: *{total}*\nОсталось бросков: *{remaining}*",
            parse_mode="Markdown", reply_markup=dart_kb()
        )
    else:
        bet = s["bet"]
        win = total >= 60
        delta = bet * 2 if win else -bet
        user = get_user(db, uid, cb.from_user.first_name)
        user["balance"] += delta
        update_user(db, uid, {"balance": user["balance"]})
        add_history(db, uid, "Дартс", bet, f"{total} очков", delta)
        sessions.pop(uid, None)
        await cb.message.edit_text(
            f"{'✅ ПОБЕДА!' if win else '❌ Не хватило!'}\n\n"
            f"Итог: *{total} очков* (нужно 60+)\n\n"
            f"{'🎉 +' if win else '💸 '}{delta} 🪙 | Баланс: {user['balance']} 🪙",
            parse_mode="Markdown"
        )
    await cb.answer(label.split("!")[0])

# ─── Боулинг ─────────────────────────────────────────────────────────────────
def render_pins(pins: list) -> str:
    rows = [[6,7,8,9],[3,4,5],[1,2],[0]]
    lines = []
    for row in rows:
        lines.append("  ".join("🎳" if pins[i] else "⚫" for i in row))
    return "\n".join(lines)

@dp.message(F.text == "🎳 Боулинг")
async def game_bowl_start(msg: Message):
    user = get_user(db, msg.from_user.id, msg.from_user.first_name)
    if user["balance"] < 25:
        await msg.answer("❌ Недостаточно поинтов!"); return
    sessions[msg.from_user.id] = {"game": "bowl", "bet": 50}
    await msg.answer("🎳 *Боулинг*\n\nВыбери ставку:", parse_mode="Markdown", reply_markup=bet_kb())

@dp.callback_query(F.data.startswith("bowl_"))
async def process_bowl(cb: CallbackQuery):
    uid = cb.from_user.id
    if uid not in sessions: await cb.answer("Сессия устарела", show_alert=True); return
    action = cb.data.split("_")[1]
    s = sessions[uid]
    data = s["data"]

    if action == "left":
        data["aim"] = max(0, data["aim"] - 15)
        pins_render = render_pins(data["pins"])
        await cb.message.edit_text(
            f"🎳 *Боулинг*\nСтавка: *{s['bet']} 🪙*\n\n{pins_render}\n\n🎯 Прицел: {data['aim']}% (влево)",
            parse_mode="Markdown", reply_markup=bowl_aim_kb()
        )
        await cb.answer(f"Прицел: {data['aim']}%"); return

    if action == "right":
        data["aim"] = min(100, data["aim"] + 15)
        pins_render = render_pins(data["pins"])
        await cb.message.edit_text(
            f"🎳 *Боулинг*\nСтавка: *{s['bet']} 🪙*\n\n{pins_render}\n\n🎯 Прицел: {data['aim']}% (вправо)",
            parse_mode="Markdown", reply_markup=bowl_aim_kb()
        )
        await cb.answer(f"Прицел: {data['aim']}%"); return

    if action == "throw":
        bet = s["bet"]
        aim_factor = data["aim"] / 100
        standing = [i for i, up in enumerate(data["pins"]) if up]
        knocked = 0
        for i in standing:
            prob = 0.2 + aim_factor * 0.55 + random.uniform(-0.15, 0.15)
            if random.random() < prob:
                data["pins"][i] = False
                knocked += 1
        data["throws"] += 1
        all_down = all(not p for p in data["pins"])
        pins_render = render_pins(data["pins"])

        if all_down and data["throws"] == 1:
            delta = bet * 3
            user = get_user(db, uid, cb.from_user.first_name)
            user["balance"

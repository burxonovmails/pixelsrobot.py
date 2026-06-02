import sys
import logging
import sqlite3
import asyncio
from typing import Dict, Any, Optional, List

from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import (
    Message, ReplyKeyboardMarkup, KeyboardButton, 
    InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
)
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

# ==========================================
# 1. ASOSIY SOZLAMALAR (TOKEN VA ADMIN)
# ==========================================
BOT_TOKEN = "8963888580:AAGZd-KFQY1mb5_VsYzjaDlxvPyNPYGiV80"
ADMIN_IDS = [6247135484]
DATABASE_NAME = "anime_perfect_bot.db"

# ==========================================
# 2. KO'P TILLI MATNLAR
# ==========================================
LANG_TEXTS = {
    "uz": {
        "welcome": "👋 Xush kelibsiz! Botdan foydalanish uchun tilni tanlang:",
        "main_menu": "🏠 Asosiy menyu",
        "btn_search": "🔍 Kod orqali qidirish",
        "btn_list": "📋 Animelar ro'yxati",
        "btn_vip": "💎 VIP Maqomi",
        "not_found": "🔍 Afsuski, ushbu kod ostida hech qanday anime yoki kino topilmadi.",
        "sub_required": "⚠️ Botdan foydalanish uchun quyidagi hamkor kanallarga a'zo bo'lishingiz shart:",
        "btn_check_sub": "✅ Obunani tekshirish",
        "sub_error": "❌ Siz hali barcha kanallarga a'zo bo'lmadingiz!",
        "vip_msg": "💎 <b>VIP Maqomi</b>\n\nSiz VIP foydalanuvchisiz! Kanallarga obuna bo'lish cheklovlari siz uchun butunlay olib tashlangan. 🍿",
        "not_vip_msg": "💎 <b>VIP Maqomi</b>\n\nSiz hozircha oddiy foydalanuvchisiz.\n\n<b>VIP afzalliklari:</b>\n- Majburiy kanallarga umuman obuna bo'lmasdan to'g'ridan-to'g'ri va tezkor foydalanish.\n\n<i>(VIP status olish uchun adminga murojaat qiling)</i>",
        "enter_code": "Iltimos, anime yoki kino kodini yuboring (Masalan: 001):",
        "select_ep": "👇 Tomosha qilish uchun qismni tanlang:"
    },
    "ru": {
        "welcome": "👋 Добро пожаловать! Выберите язык, чтобы продолжить:",
        "main_menu": "🏠 Главное меню",
        "btn_search": "🔍 Поиск по коду",
        "btn_list": "📋 Список аниме",
        "btn_vip": "💎 VIP Статус",
        "not_found": "🔍 К сожалению, по этому коду ничего не найдено.",
        "sub_required": "⚠️ Для использования бота вы должны подписаться на следующие каналы:",
        "btn_check_sub": "✅ Проверить подписку",
        "sub_error": "❌ Вы не подписались на все каналы!",
        "vip_msg": "💎 <b>VIP Статус</b>\n\nВы являетесь VIP-пользователем! Все ограничения на подписку для вас сняты. 🍿",
        "not_vip_msg": "💎 <b>VIP Статус</b>\n\nНа данный момент вы являетесь обычным пользователем.\n\n<b>Преимущества VIP:</b>\n- Использование бота напрямую без обязательных подписок.\n\n<i>(Для получения VIP статуса обратитесь к админу)</i>",
        "enter_code": "Пожалуйста, отправьте код (Например: 001):",
        "select_ep": "👇 Выберите серию для просмотра:"
    },
    "en": {
        "welcome": "👋 Welcome! Choose a language to continue:",
        "main_menu": "🏠 Main Menu",
        "btn_search": "🔍 Search by Code",
        "btn_list": "📋 Anime List",
        "btn_vip": "💎 VIP Status",
        "not_found": "🔍 Unfortunately, nothing was found under this code.",
        "sub_required": "⚠️ To use the bot, you must subscribe to the following channels:",
        "btn_check_sub": "✅ Check Subscription",
        "sub_error": "❌ You have not subscribed to all channels yet!",
        "vip_msg": "💎 <b>VIP Status</b>\n\nYou are a VIP user! Mandatory channel restrictions are completely lifted for you. 🍿",
        "not_vip_msg": "💎 <b>VIP Status</b>\n\nYou are currently a regular user.\n\n<b>VIP Benefits:</b>\n- Use the bot directly without any mandatory subscriptions.\n\n<i>(Contact admin to get VIP status)</i>",
        "enter_code": "Please send the code (e.g., 001):",
        "select_ep": "👇 Select an episode to watch:"
    }
}

def init_db():
    with sqlite3.connect(DATABASE_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                lang TEXT,
                is_vip INTEGER DEFAULT 0
            )""")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS anime (
                code TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                genre TEXT,
                description TEXT,
                image_id TEXT,
                type TEXT
            )""")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS anime_episodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                anime_code TEXT,
                ep_name TEXT,
                file_id TEXT,
                FOREIGN KEY(anime_code) REFERENCES anime(code) ON DELETE CASCADE
            )""")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS channels (
                username TEXT PRIMARY KEY,
                name TEXT
            )""")
        conn.commit()

def get_user(user_id: int):
    with sqlite3.connect(DATABASE_NAME) as conn:
        conn.row_factory = sqlite3.Row
        res = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(res) if res else None

def add_user(user_id: int, lang: str):
    with sqlite3.connect(DATABASE_NAME) as conn:
        conn.execute("INSERT OR REPLACE INTO users (id, lang, is_vip) VALUES (?, ?, COALESCE((SELECT is_vip FROM users WHERE id = ?), 0))", (user_id, lang, user_id))
        conn.commit()

def get_channels() -> List[Dict]:
    with sqlite3.connect(DATABASE_NAME) as conn:
        conn.row_factory = sqlite3.Row
        return [dict(r) for r in conn.execute("SELECT * FROM channels").fetchall()]

class BotStates(StatesGroup):
    waiting_lang = State()
    user_search = State()
    admin_add_meta = State()
    admin_add_poster = State()
    admin_ep_meta = State()
    admin_ep_video = State()
    admin_add_channel = State()
    admin_remove_channel = State()
    admin_set_vip = State()

def get_lang_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="lang_uz")],
        [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru")],
        [InlineKeyboardButton(text="🇺🇸 English", callback_data="lang_en")]
    ])

def get_user_menu(lang: str):
    t = LANG_TEXTS[lang]
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text=t["btn_search"]), KeyboardButton(text=t["btn_list"])],
        [KeyboardButton(text=t["btn_vip"])]
    ], resize_keyboard=True)

def get_admin_menu():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="➕ Kontent Qo'shish"), KeyboardButton(text="📊 Statistika")],
        [KeyboardButton(text="📢 Kanal Qo'shish"), KeyboardButton(text="❌ Kanal O'chirish")],
        [KeyboardButton(text="💎 VIP Berish/Olish")]
    ], resize_keyboard=True)

router = Router()

async def check_subscription(user_id: int) -> bool:
    channels = get_channels()
    if not channels:
        return True
    user = get_user(user_id)
    if user and user.get('is_vip'):
        return True
    return False

@router.message(CommandStart())
async def start_cmd(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user = get_user(user_id)
    
    if not user:
        await state.set_state(BotStates.waiting_lang)
        await message.answer(LANG_TEXTS["uz"]["welcome"], reply_markup=get_lang_keyboard())
    else:
        if user_id in ADMIN_IDS:
            await message.answer("🔐 Admin Paneli", reply_markup=get_admin_menu())
        else:
            await message.answer(LANG_TEXTS[user["lang"]]["main_menu"], reply_markup=get_user_menu(user["lang"]))

@router.callback_query(F.data.startswith("lang_"))
async def lang_select(callback: CallbackQuery, state: FSMContext):
    lang = callback.data.split("_")[1]
    user_id = callback.from_user.id
    add_user(user_id, lang)
    
    if user_id in ADMIN_IDS:
        await callback.message.delete()
        await callback.message.answer("🔐 Admin Paneli", reply_markup=get_admin_menu())
    else:
        await callback.message.delete()
        await callback.message.answer(LANG_TEXTS[lang]["main_menu"], reply_markup=get_user_menu(lang))
    
    await state.clear()

@router.message(F.text == "➕ Kontent Qo'shish")
async def admin_add_content_menu(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🆕 Yangi Paket (Anime/Kino) Yaratish", callback_data="add_pack")],
        [InlineKeyboardButton(text="📹 Mavjud paketga Qism (Video) qo'shish", callback_data="add_ep")]
    ])
    await message.answer("Nimani qo'shishni xohlaysiz? Tanlang:", reply_markup=kb)

@router.callback_query(F.data == "add_pack")
async def admin_pack_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await callback.message.answer(
        "Ma'lumotlarni aniq formatda yuboring:\n\n"
        "<code>KOD | TURI (anime/kino) | NOMI | JANRI | TA'RIF</code>\n\n"
        "<b>Misol:</b>\n"
        "<code>001 | anime | Naruto | Sarguzasht, Jangari | Yosh ninjaning hikoyasi.</code>",
        parse_mode="HTML"
    )
    await state.set_state(BotStates.admin_add_meta)

@router.message(BotStates.admin_add_meta, F.text)
async def admin_pack_meta_save(message: Message, state: FSMContext):
    try:
        parts = [p.strip() for p in message.text.split("|")]
        if len(parts) < 5: raise ValueError()
        code, c_type, name, genre, description = parts
        if c_type.lower() not in ['anime', 'kino']:
            await message.answer("❌ Turi faqat 'anime' yoki 'kino' bo'lishi shart!")
            return
        
        await state.update_data(code=code.upper(), type=c_type.lower(), name=name, genre=genre, description=description)
        await message.answer("🖼️ Endi ushbu anime/kinoning <b>Poster Rasmini</b> (Rasm shaklida) yuboring:")
        await state.set_state(BotStates.admin_add_poster)
    except Exception:
        await message.answer("⚠️ Format xato! Quyidagicha yuboring:\nKOD | TURI | NOMI | JANRI | TA'RIF")

@router.message(BotStates.admin_add_poster, F.photo)
async def admin_pack_poster_save(message: Message, state: FSMContext):
    data = await state.get_data()
    image_id = message.photo[-1].file_id
    
    with sqlite3.connect(DATABASE_NAME) as conn:
        conn.execute("""
            INSERT OR REPLACE INTO anime (code, name, genre, description, image_id, type)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (data['code'], data['name'], data['genre'], data['description'], image_id, data['type']))
        conn.commit()
    await message.answer(f"✅ Yangi katalog paketi muvaffaqiyatli ochildi!\nKod: <code>{data['code']}</code>", parse_mode="HTML")
    await state.clear()

@router.callback_query(F.data == "add_ep")
async def admin_ep_start_flow(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await callback.message.answer(
        "Qism ma'lumotlarini quyidagi formatda yuboring:\n\n"
        "<code>KOD | QISM NOMI</code>\n\n"
        "<b>Misol:</b>\n"
        "<code>001 | 1-qism (Tarjima)</code>", parse_mode="HTML"
    )
    await state.set_state(BotStates.admin_ep_meta)

@router.message(BotStates.admin_ep_meta, F.text)
async def admin_ep_meta_save(message: Message, state: FSMContext):
    try:
        code, ep_name = [i.strip() for i in message.text.split("|")]
        with sqlite3.connect(DATABASE_NAME) as conn:
            exists = conn.execute("SELECT code FROM anime WHERE code = ?", (code.upper(),)).fetchone()
        if not exists:
            await message.answer(f"❌ Bazada <code>{code.upper()}</code> kodli paket mavjud emas! Avval yangi paket oching.", parse_mode="HTML")
            await state.clear()
            return
        await state.update_data(anime_code=code.upper(), ep_name=ep_name)
        await message.answer(f"📹 Endi <code>{code.upper()}</code> kodi uchun <b>Video faylini</b> o'zini yuboring:")
        await state.set_state(BotStates.admin_ep_video)
    except Exception:
        await message.answer("⚠️ Format xato! Format: KOD | QISM NOMI")

@router.message(BotStates.admin_ep_video, F.video)
async def admin_ep_video_save(message: Message, state: FSMContext):
    data = await state.get_data()
    file_id = message.video.file_id
    with sqlite3.connect(DATABASE_NAME) as conn:
        conn.execute("INSERT INTO anime_episodes (anime_code, ep_name, file_id) VALUES (?, ?, ?)", 
                     (data['anime_code'], data['ep_name'], file_id))
        conn.commit()
    await message.answer(f"✅ Video saqlandi! [<code>{data['anime_code']}</code>] jildiga [<b>{data['ep_name']}</b>] qo'shildi.", parse_mode="HTML")
    await state.clear()

@router.message(F.text == "📢 Kanal Qo'shish")
async def admin_add_ch_start(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    await message.answer("Kanal ma'lumotlarini quyidagicha yuboring:\n\n<code>@username | Kanal Nomi</code>", parse_mode="HTML")
    await state.set_state(BotStates.admin_add_channel)

@router.message(BotStates.admin_add_channel, F.text)
async def admin_add_ch_save(message: Message, state: FSMContext):
    try:
        username, name = [i.strip() for i in message.text.split("|")]
        if not username.startswith("@"):
            await message.answer("❌ Kanal username @ belgisi bilan boshlanishi shart!")
            return
        with sqlite3.connect(DATABASE_NAME) as conn:
            conn.execute("INSERT OR REPLACE INTO channels (username, name) VALUES (?, ?)", (username, name))
            conn.commit()
        await message.answer("✅ Kanal majburiy obunalar ro'yxatiga qo'shildi.")
        await state.clear()
    except Exception:
        await message.answer("❌ Sintaksis xato! Qayta urinib ko'ring.")

@router.message(F.text == "❌ Kanal O'chirish")
async def admin_rm_ch_start(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    channels = get_channels()
    if not channels:
        await message.answer("Hozirda majburiy kanallar ro'yxati bo'sh.")
        return
    res = "O'chirmoqchi bo'lgan kanal usernamesini to'liq yuboring:\n\n"
    for c in channels: res += f"- <code>{c['username']}</code>\n"
    await message.answer(res, parse_mode="HTML")
    await state.set_state(BotStates.admin_remove_channel)

@router.message(BotStates.admin_remove_channel, F.text)
async def admin_rm_ch_done(message: Message, state: FSMContext):
    username = message.text.strip()
    with sqlite3.connect(DATABASE_NAME) as conn:
        conn.execute("DELETE FROM channels WHERE username = ?", (username,))
        conn.commit()
    await message.answer("🗑️ Kanal muvaffaqiyatli o'chirildi.")
    await state.clear()

@router.message(F.text == "💎 VIP Berish/Olish")
async def admin_vip_control_start(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    await message.answer("Foydalanuvchi IDsi va maqomini yuboring (1 - Vip berish, 0 - Vipni olish):\n\nFormat: <code>USER_ID | STATUS</code>\nMisol: <code>987654321 | 1</code>", parse_mode="HTML")
    await state.set_state(BotStates.admin_set_vip)

@router.message(BotStates.admin_set_vip, F.text)
async def admin_vip_control_done(message: Message, state: FSMContext):
    try:
        uid, status = [int(i.strip()) for i in message.text.split("|")]
        with sqlite3.connect(DATABASE_NAME) as conn:
            conn.execute("UPDATE users SET is_vip = ? WHERE id = ?", (status, uid))
            conn.commit()
        msg = "💎 VIP status muvaffaqiyatli berildi." if status == 1 else "❌ VIP status olib tashlandi."
        await message.answer(f"Foydalanuvchi {uid} uchun {msg}")
        await state.clear()
    except Exception:
        await message.answer("❌ Xatolik! ID va statusni tekshirib qayta yuboring.")

async def main():
    init_db()
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    
    await bot.delete_webhook(drop_pending_updates=True)
    print("🚀 Bot barcha modullari bilan muvaffaqiyatli ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("🤖 Bot faoliyati yakunlandi.")

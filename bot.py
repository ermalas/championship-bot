
import os
import sqlite3
from datetime import datetime

from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

TOKEN = os.environ 9136302825:AAHUiId73Wu4I9PM-EwreWYWwQrkTXCNTXE
OWNER_ID = int(os.environ 6521440750
ADMIN_GROUP_ID = int(os.environ -5303157472
WEBHOOK_SECRET = os.environ championship_secret_2026_abc123

BASE_URL = os.environ["RENDER_EXTERNAL_URL"]
WEBHOOK_PATH = "/webhook"

ADMIN_USER_IDS = {OWNER_ID}

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

db = sqlite3.connect("championship.db")
db.execute("""
CREATE TABLE IF NOT EXISTS tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    username TEXT,
    category TEXT,
    created_at TEXT
)
""")
db.commit()

menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="⚖️ Жалобы на судейство")],
        [KeyboardButton(text="🛡️ Запрос на админа/судью")],
        [KeyboardButton(text="💬 Свой вопрос")],
        [KeyboardButton(text="🚨 Жалобы на админов")]
    ],
    resize_keyboard=True
)

categories = [
    "⚖️ Жалобы на судейство",
    "🛡️ Запрос на админа/судью",
    "💬 Свой вопрос",
    "🚨 Жалобы на админов"
]

class Support(StatesGroup):
    waiting_message = State()

def is_admin(message: Message):
    return (
        message.from_user is not None
        and message.from_user.id in ADMIN_USER_IDS
    )

async def send_to_admins(message: Message, ticket_id: int, category: str):
    user = message.from_user
    username = f"@{user.username}" if user.username else "Не указан"

    info = (
        "🏆 CHAMPIONSHIP | НОВОЕ ОБРАЩЕНИЕ\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"🎫 Номер: #{ticket_id}\n"
        f"📂 Категория: {category}\n"
        f"👤 Игрок: {user.full_name}\n"
        f"🔗 Username: {username}\n"
        f"🆔 ID: {user.id}\n"
        f"🕒 Время: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "📩 Сообщение игрока находится ниже.\n\n"
        f"/reply {ticket_id} Ваш ответ"
    )

    for destination in {OWNER_ID, ADMIN_GROUP_ID}:
        try:
            await bot.send_message(destination, info)
            await bot.copy_message(
                chat_id=destination,
                from_chat_id=message.chat.id,
                message_id=message.message_id
            )
        except Exception as error:
            print(f"Ошибка отправки {destination}: {error}")

@dp.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "🏆 CHAMPIONSHIP\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "Привет! 👋\n\n"
        "Ты написал в поддержку футбольной лиги CHAMPIONSHIP!\n\n"
        "Выбери, что ты хочешь написать, в нижнем меню.\n\n"
        "📩 Все обращения поступают администрации.\n"
        "⚖️ Каждое обращение рассматривается отдельно.\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "OFFICIAL LEAGUE SUPPORT",
        reply_markup=menu
    )

@dp.message(F.text.in_(categories))
async def choose_category(message: Message, state: FSMContext):
    await state.update_data(category=message.text)
    await state.set_state(Support.waiting_message)
    await message.answer(
        "📩 НОВОЕ ОБРАЩЕНИЕ\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"Выбрана категория:\n{message.text}\n\n"
        "✍️ Теперь отправь своё обращение.\n\n"
        "Можешь отправить текст, фотографию или видео.\n\n"
        "После отправки оно будет передано администрации.",
        reply_markup=menu
    )

@dp.message(Support.waiting_message)
async def receive_message(message: Message, state: FSMContext):
    if message.text and message.text.startswith("/"):
        await message.answer("Сначала отправь обращение или выбери категорию.")
        return

    data = await state.get_data()
    category = data["category"]

    username = message.from_user.username or ""

    cursor = db.execute(
        """
        INSERT INTO tickets (user_id, username, category, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (
            message.from_user.id,
            username,
            category,
            datetime.now().isoformat()
        )
    )

    ticket_id = cursor.lastrowid
    db.commit()

    await send_to_admins(message, ticket_id, category)

    await message.answer(
        "✅ ОБРАЩЕНИЕ ОТПРАВЛЕНО!\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"🎫 Номер обращения: #{ticket_id}\n\n"
        "Твоё обращение передано администрации CHAMPIONSHIP.\n\n"
        "Ожидай ответа в этом боте.\n\n"
        "Спасибо за обращение! 🏆",
        reply_markup=menu
    )

    await state.clear()

@dp.message(Command("reply"))
async def admin_reply(message: Message):
    if not is_admin(message):
        await message.answer("⛔ У тебя нет доступа к этой команде.")
        return

    parts = (message.text or "").split(maxsplit=2)

    if len(parts) < 3:
        await message.answer(
            "Используй:\n/reply НОМЕР ТЕКСТ"
        )
        return

    try:
        ticket_id = int(parts[1])
    except ValueError:
        await message.answer("Номер обращения должен быть числом.")
        return

    answer = parts[2]

    ticket = db.execute(
        "SELECT user_id FROM tickets WHERE id = ?",
        (ticket_id,)
    ).fetchone()

    if not ticket:
        await message.answer("❌ Обращение не найдено.")
        return

    try:
        await bot.send_message(
            ticket[0],
            "🏆 CHAMPIONSHIP | ОТВЕТ АДМИНИСТРАЦИИ\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"🎫 Обращение: #{ticket_id}\n\n"
            f"💬 Ответ:\n{answer}\n\n"
            "━━━━━━━━━━━━━━━━━━"
        )
        await message.answer(
            f"✅ Ответ на обращение #{ticket_id} отправлен игроку."
        )
    except Exception as error:
        await message.answer(f"❌ Не удалось отправить ответ: {error}")

@dp.message(Command("cancel"))
async def cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "❌ Создание обращения отменено.",
        reply_markup=menu
    )

async def on_startup(app):
    await bot.set_webhook(
        url=BASE_URL + WEBHOOK_PATH,
        secret_token=WEBHOOK_SECRET
    )
    print("CHAMPIONSHIP SUPPORT запущен!")

async def main():
    app = web.Application()

    SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=WEBHOOK_SECRET
    ).register(app, path=WEBHOOK_PATH)

    setup_application(app, dp, bot=bot)
    app.on_startup.append(on_startup)

    port = int(os.environ.get("PORT", 10000))
    web.run_app(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
    

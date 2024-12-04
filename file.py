import logging
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.utils import executor

API_TOKEN = '7241924537:AAEYn86OYcTSQ1fAexpbpq1Tmlog3Dn76nw'
ADMIN_ID = 1262676599  # Replace with your admin Telegram ID

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())

# Connect to SQLite database (or create it if it doesn't exist)
conn = sqlite3.connect('users.db')
cursor = conn.cursor()

# Create a table for storing user IDs if it doesn't exist
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY
)
''')
conn.commit()

# Dictionary to track user messages for admin replies
user_message_mapping = {}

# Helper function to add user ID to database
def add_user_id(user_id):
    try:
        cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()
    except sqlite3.Error as e:
        logging.error(f"Error adding user ID {user_id} to database: {e}")


@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    """
    Handles the /start command.
    """
    user_id = message.from_user.id
    add_user_id(user_id)
    username = message.from_user.username or message.from_user.full_name
    logging.info(f"@{username} started the bot")

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = ["English", "Русский"]
    keyboard.add(*buttons)
    await message.answer("Select language / Выберите язык", reply_markup=keyboard)


@dp.message_handler(commands=['h'])
async def broadcast_message(message: types.Message):
    """
    Handles the /h command for broadcasting messages.
    """
    if message.chat.id != ADMIN_ID:
        return  # Restrict /h to admin only

    try:
        if len(message.text.split()) <= 1:
            await message.reply("Usage: /h <message>")
            return

        broadcast_text = message.text.split(' ', 1)[1]
        cursor.execute("SELECT user_id FROM users")
        user_ids = cursor.fetchall()

        if not user_ids:
            await message.reply("No users found in the database.")
            return

        sent_count = 0
        sent_to_users = []

        for user_id_tuple in user_ids:
            user_id = user_id_tuple[0]
            try:
                user_info = await bot.get_chat(user_id)
                username = f"@{user_info.username}" if user_info.username else user_info.full_name
                await bot.send_message(user_id, broadcast_text)
                sent_count += 1
                sent_to_users.append(username)
            except Exception as e:
                logging.error(f"Failed to send message to user {user_id}: {e}")

        user_list = "\n".join(sent_to_users) or "No users"
        await message.reply(f"Message sent to {sent_count} users:\n{user_list}")
    except Exception as e:
        logging.error(f"Error in /h command: {e}")
        await message.reply("Failed to broadcast the message.")


@dp.message_handler(lambda message: message.text in ["English", "Русский"])
async def select_language(message: types.Message):
    """
    Handles language selection.
    """
    username = message.from_user.username or message.from_user.full_name
    logging.info(f"@{username}: {message.text}")

    if message.text == "English":
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        buttons = ["Hosting", "Hosting + Domain", "Website Development"]
        keyboard.add(*buttons)
        await message.answer("Select option:", reply_markup=keyboard)
    elif message.text == "Русский":
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        buttons = ["Хостинг", "Хостинг + Домен", "Разработка сайта"]
        keyboard.add(*buttons)
        await message.answer("Выберите опцию:", reply_markup=keyboard)


# Service selection handler
@dp.message_handler(lambda message: message.text in ["Hosting", "Hosting + Domain", "Website Development", "Хостинг", "Хостинг + Домен", "Разработка сайта"])
async def select_service(message: types.Message):
    username = message.from_user.username or message.from_user.full_name
    logging.info(f"@{username}: {message.text}")
    keyboard = types.ReplyKeyboardRemove()
    await message.answer("Enter coupon code for discount (if any) / Введите код купона для скидки (если есть):", reply_markup=keyboard)

@dp.message_handler(lambda message: not message.text.startswith("/"), content_types=types.ContentTypes.ANY)
async def forward_to_admin(message: types.Message):
    """
    Forwards non-command messages from users to the admin.
    """
    try:
        if message.chat.id == ADMIN_ID:
            return  # Prevent looping if admin sends a message

        user_id = message.from_user.id
        username = message.from_user.username or message.from_user.full_name
        add_user_id(user_id)

        await bot.send_message(
            ADMIN_ID,
            f"Message from @{username} (ID: {user_id}):\n{message.text or '[Non-text message]'}"
        )
    except Exception as e:
        logging.error(f"Error forwarding message from {message.from_user.id}: {e}")


# Coupon code entry handler
@dp.message_handler(lambda message: True)
async def enter_coupon(message: types.Message):
    username = message.from_user.username or message.from_user.full_name
    logging.info(f"@{username}: {message.text}")

    payment_methods = ["Visa", "Paypal", "Crypto"]
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(*payment_methods)
    await message.answer("Select payment method / Выберите способ оплаты:", reply_markup=keyboard)


# Payment method selection handler
@dp.message_handler(lambda message: message.text in ["Visa", "Paypal", "Crypto"])
async def handle_payment_method(message: types.Message):
    username = message.from_user.username or message.from_user.full_name
    logging.info(f"@{username}: {message.text}")
    payment_method = message.text

    if payment_method == "Visa":
        await message.answer("Enter card details / Введите данные карты:")
    elif payment_method in ["Paypal", "Crypto"]:
        await message.answer("Unavailable in your country / Не доступно в вашей стране")
    else:
        await message.answer("Invalid option / Недопустимый вариант")



if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)


#U Jayasingha, [1/4/2025 12:29 AM]
import os
import uuid
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from pymongo import MongoClient
from pyrogram.errors import FloodWait

# Bot Configuration
API_ID = "22903347"  # Telegram API ID
API_HASH = "d4164bdce355a4f5864e1e9be667df08"  # Telegram API Hash
BOT_TOKEN = "7071263695:AAG8rbanIDFigYH2A1I58aIuMUFJBA0I3ik"  # Bot token from BotFather

# Custom Variables
ADMIN_IDS = [1053942430]  # List of admin Telegram IDs
DATABASE_CHANNEL_ID = -1002143528531  # Channel ID for storing files
FORCESUB_CHANNEL_ID = "@IraSubscribe"  # Forcesub group/channel username or ID
WELCOME_MESSAGE = "Welcome to the bot! Please send a file to get started."  # Custom welcome message
BASE_URL = "https://t.me/@Tjsttore_bot?start="  # Replace with your bot's username

# MongoDB Configuration
MONGO_URI = "mongodb+srv://oshadisandeepani8:<db_password>@filesharebot.8b1x8xi.mongodb.net/?retryWrites=true&w=majority&appName=FileShareBot"  # MongoDB connection string
mongo_client = MongoClient(MONGO_URI)
db = mongo_client['telegram_bot']
users_collection = db['users']
files_collection = db['files']

# Initialize the bot
app = Client("file_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Function to save file metadata in MongoDB
def save_file_metadata(file_id, unique_id, channel_message_id):
    files_collection.insert_one({
        "file_id": file_id,
        "unique_id": unique_id,
        "channel_message_id": channel_message_id
    })

# Function to check if a user has joined the Forcesub channel
async def check_forcesub(user_id):
    try:
        member = await app.get_chat_member(FORCESUB_CHANNEL_ID, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

# Start command: Welcome message or handle unique link
@app.on_message(filters.command("start"))
async def start(_, message: Message):
    user_id = message.from_user.id

    # Add user to the database if not already added
    if not users_collection.find_one({"user_id": user_id}):
        users_collection.insert_one({"user_id": user_id})

    # Check if the user sent a unique link
    if len(message.command) > 1:
        unique_id = message.command[1]

        # Check Forcesub status
        if not await check_forcesub(user_id):
            join_button = InlineKeyboardMarkup(
                [[InlineKeyboardButton("Join Group/Channel", url=f"https://t.me/{FORCESUB_CHANNEL_ID}")]]
            )
            await message.reply("❌ You must join the Forcesub channel to use this bot.", reply_markup=join_button)
            return

        # Fetch file metadata
        file_metadata = files_collection.find_one({"unique_id": unique_id})

        if file_metadata:
            await app.forward_messages(
                chat_id=message.chat.id,
                from_chat_id=DATABASE_CHANNEL_ID,
                message_ids=file_metadata["channel_message_id"]
            )
        else:
            await message.reply("❌ Invalid or expired link!")
        return

    # If no unique link is provided, send welcome message
    await message.reply(WELCOME_MESSAGE)

# Store files: Only admins can use this feature
@app.on_message(filters.document | filters.video | filters.photo & filters.user(ADMIN_IDS))
async def store_file(_, message: Message):
    user_id = message.from_user.id

    if user_id not in ADMIN_IDS:
        await message.reply("❌ You are not authorized to store files.")
        return

    # Forward file to the storage channel
    forwarded_message = await message.forward(DATABASE_CHANNEL_ID)

    # Generate a unique ID for the file
    unique_id = str(uuid.uuid4())[:8]

    # Save file metadata in MongoDB
    save_file_metadata(forwarded_message.message_id, unique_id, forwarded_message.message_id)

    # Add a button to copy the link
    button = InlineKeyboardMarkup(
        [[InlineKeyboardButton("Copy Link", url=f"{BASE_URL}{unique_id}")]]
    )

    await app.edit_message_reply_markup(
        chat_id=DATABASE_CHANNEL_ID,
        message_id=forwarded_message.message_id,
        reply_markup=button
    )

U Jayasingha, [1/4/2025 12:29 AM]
await message.reply(f"✅ File stored successfully! Access it using this link:\n{BASE_URL}{unique_id}")

# User count command: Admins only
@app.on_message(filters.command("usercount") & filters.user(ADMIN_IDS))
async def user_count(_, message: Message):
    user_count = users_collection.count_documents({})
    await message.reply(f"👥 Total bot users: {user_count}")

# Broadcast command: Admins only
@app.on_message(filters.command("broadcast") & filters.user(ADMIN_IDS))
async def broadcast(_, message: Message):
    if len(message.command) < 2:
        await message.reply("❌ Usage: /broadcast <message>")
        return

    broadcast_message = message.text.split(maxsplit=1)[1]

    for user in users_collection.find():
        try:
            await app.send_message(chat_id=user["user_id"], text=broadcast_message)
        except Exception as e:
            print(f"Failed to send message to {user['user_id']}: {e}")
            if isinstance(e, FloodWait):
                await asyncio.sleep(e.x)

    await message.reply("✅ Broadcast sent!")

# Prevent forwarding or saving bot messages
@app.on_message(filters.chat(BOT_TOKEN))
async def prevent_forward(_, message: Message):
    await message.delete()

# Run the bot
print("Bot is running...")
app.run()
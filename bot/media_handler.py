import os
import json
import random
import sqlite3
import asyncio
from collections import defaultdict
import aiosqlite
from telegram import Update
from telegram.ext import ContextTypes
from utils.utils import(
    is_ddos,
    get_settings,
    send_to_channel,
    load_persona
)
from telegram.constants import ChatAction
from google import genai
from google.genai import types
from utils.config import(
    channel_id,
    media_count_limit,
    media_size_limit,
    premium_media_count_limit,
    premium_media_size_limit,
    db
)
from ext.user_content_tools import(
    create_prompt,
    reset
)
from utils.db import(
    gemini_api_keys,
    premium_users
)
import time
from utils.utils import(
    is_ddos,
    send_to_channel,
    safe_send,
    get_settings,
    is_code_block_open
)
from ext.user_content_tools import(
    save_conversation,
    reset
)
from telegram.error import TimedOut









media_queue = asyncio.Queue()
media_user_locks = defaultdict(asyncio.Lock)

async def media_worker():
    while True:
        item = await media_queue.get()
        try:
            if item is None:
                break
            update, content = item
            user_id = update.effective_user.id
            lock = media_user_locks[user_id]
            async with lock:
                await process_media_update(update, content)
        finally:
            media_queue.task_done()

async def run_media_workers(n):
    tasks = []
    for _ in range(n):
        task = asyncio.create_task(media_worker())
        tasks.append(task)
    return tasks



valid_ext = [
    ".pdf", ".json", ".txt", ".docx", ".py", ".c", ".cpp",
    ".cxx", ".html", ".htm", ".js" , ".java", ".css", ".xml",
    ".php", ".json", ".doc", ".ppt", ".pptx", ".xls", "xlsx",
    ".csv", ".md", ".log", ".yaml", ".png", ".jpg", ".jpeg",
    ".gif", ".webp", ".mp4", ".avi", ".mkv", ".webm", ".mp3",
    ".ogg", ".wav", ".m4a"
]




#a function to save media conversation history with media description
async def save_media_conversation(update:Update, content:ContextTypes.DEFAULT_TYPE, prompt, response, user_id, path, file_id, file_type):
    try:
        size = os.path.getsize(path)/(1024*1024)
        await media_manager(update, content, path, os.path.getsize(path)/(1024*1024))
        if file_type:
            await save_conversation(f"<{file_type}>Path: {path}, Size: {size} MB</{file_type}>\n" + prompt + "\n", response.text, user_id)
        else:
            await save_conversation(f"<{file_type}>"+prompt, response.text, user_id)
    except Exception as e:
        print(f"Error in save_media_conversation function.\n\nError Code -{e}")


#function for editing and sending message
async def send_message(update : Update, content : ContextTypes.DEFAULT_TYPE, response, user_message, msg_obj) -> None:
    try:
        count = 0
        message = update.message or update.edited_message
        if not response:
            await message.reply_text("Failed to precess your request. Try again later.")
            return
        if hasattr(response, 'parts'):
            text_parts = [part.text for part in response.parts if hasattr(part, 'text') and part.text is not None]
            message_to_send = "".join(text_parts)
        else:
            message_to_send = response.text if hasattr(response, "text") else str(response)
        if len(message_to_send) > 4080:
            message_chunks = [message_to_send[i:i+4080] for i in range(0, len(message_to_send), 4080)]
            for i,msg in enumerate(message_chunks):
                if count != 0:
                    msg_obj =  None
                if is_code_block_open(msg):
                    message_chunks[i] += "```"
                    message_chunks[i+1] = "```\n" + message_chunks[i+1]
                await safe_send(update, content, message_chunks[i], msg_obj)
                count += 1
        else:
            await safe_send(update, content, message_to_send, msg_obj)
            count += 1
    except Exception as e:
        print(f"Error in send_message function Error Code - {e}")
        await send_to_channel(update, content, channel_id, f"Error in send_message function \n\nError Code -{e}")





async def media_manager(update: Update, content: ContextTypes.DEFAULT_TYPE, path, size):
    try:
        user_id = update.effective_user.id
        timestamp = int(time.time())
        conn = await aiosqlite.connect('user_media/user_media.db')

        # Limits based on user type
        size_limit = media_size_limit if str(user_id) not in premium_users else premium_media_size_limit
        count_limit = media_count_limit if str(user_id) not in premium_users else premium_media_count_limit

        # Fetch user’s current media
        c = await conn.execute('''SELECT * FROM user_media WHERE user_id=? ORDER BY timestamp ASC''', (user_id,))
        existing_media = await c.fetchall()

        # Enforce media count limit
        while len(existing_media) >= count_limit:
            oldest_media = existing_media[0]
            oldest_path = oldest_media[2]
            if os.path.exists(oldest_path):
                os.remove(oldest_path)
            await conn.execute('''DELETE FROM user_media WHERE media_path=?''', (oldest_media[2],))
            await conn.commit()
            # Refresh list after deletion
            c = await conn.execute('''SELECT * FROM user_media WHERE user_id=? ORDER BY timestamp ASC''', (user_id,))
            existing_media = await c.fetchall()

        # Enforce size limit
        while sum(media[3] for media in existing_media) + size > size_limit:
            if not existing_media:
                break  # Safety check
            oldest_media = existing_media[0]
            oldest_path = oldest_media[2]
            if os.path.exists(oldest_path):
                os.remove(oldest_path)
            await conn.execute('''DELETE FROM user_media WHERE media_path=?''', (oldest_media[2],))
            await conn.commit()
            # Refresh list after deletion
            c = await conn.execute('''SELECT * FROM user_media WHERE user_id=? ORDER BY timestamp ASC''', (user_id,))
            existing_media = await c.fetchall()

        # Insert new media
        await conn.execute('''
            INSERT INTO user_media (user_id, timestamp, media_path, media_size)
            VALUES (?, ?, ?, ?)
        ''', (user_id, timestamp, path, size))
        await conn.commit()
        await conn.close()
    except Exception as e:
        print(f"Error in media_manager function: {e}")




#function to handle location
async def handle_location(update:Update, content:ContextTypes.DEFAULT_TYPE):
    try:
        if update.message.location:
            location = update.message.location
            location = (location.latitude, location.longitude)
            await update.message.reply_text(f"Your latitude is {{location[0]}} and longitude is {{location[1]}}")
    except Exception as e:
        print(f"Error in handle_location function. \n\nError code - {e}")


#function to put media request in a queue
async def handle_media(update:Update, content:ContextTypes.DEFAULT_TYPE) -> None:
    for retry in range(5):
        try:
            if await is_ddos(update, content, update.effective_user.id):
                return
            await media_queue.put((update, content))
            return
        except TimedOut:
            print(f"Timeout, Retrying for the {retry+1} times.")
        except Exception as e:
            print(f"Error in handle_media function. \n\nError code - {e}")
            return



#function to process media updates
async def process_media_update(update:Update, content:ContextTypes.DEFAULT_TYPE) -> None:
    try:
        global gemini_api_keys, valid_ext
        tools = [
            types.Tool(google_search=types.GoogleSearch),
            types.Tool(url_context=types.UrlContext)
        ]
        message = update.message or update.edited_message
        os.makedirs("data/media", exist_ok=True)
        chat_id = update.effective_chat.id
        settings = await get_settings(chat_id)
        await message.chat.send_action(action=ChatAction.TYPING)
        if(
            not message and not message.photo and not message.video
            and not message.audio and not message.voice 
            and not message.sticker and not message.document
            and message.chat.type != "private"
        ):
            return
        msg = await update.message.reply_text("Downloading...")
        if message.photo:
            media_type = "image"
            file = message.photo[-1]
            photo = await message.photo[-1].get_file()
            ext = os.path.splitext(os.path.basename(photo.file_path))[1]
            caption = message.caption or "If there is any question answer them if there is code find error and suggest improvement if there is no question and code then describe the content."
            prompt = await create_prompt(update, content, caption, chat_id, 1)
        elif message.voice:
            media_type = "voice"
            file = message.voice
            ext = ".ogg"
            caption = message.caption or "If there is any question answer them if there is code find error and suggest improvement if there is no question and code then describe the content."
            prompt = await create_prompt(update, content, caption, chat_id, 1)
        elif message.document:
            media_type = "document"
            file = message.document
            file_obj = await file.get_file()
            ext = os.path.splitext(os.path.basename(file_obj.file_path))[1]
            caption = message.caption or "If there is any question answer them if there is code find error and suggest improvement if there is no question and code then describe the content."
            prompt = caption
        else:
            file = message.video or message.audio or message.sticker
            if message.video:
                media_type = "video"
            elif message.audio:
                media_type = "audio"
            elif message.sticker:
                media_type = "sticker"
            file_obj = await file.get_file()
            ext = os.path.splitext(os.path.basename(file_obj.file_path))[1]
            caption = message.caption or "If there is any question answer them if there is code find error and suggest improvement if there is no question and code then describe the content."
            prompt = await create_prompt(update, content, caption, chat_id, 1)
        file_size = file.file_size/(1024*1024)
        if file_size > 20:
            await message.reply_text("Failed to process your request. Telegram bot only  supports file up to 20 MB.")
            return
        if ext not in valid_ext:
            await update.message.reply_text("Unsupported Format...")
            return
        
        file_id = file.file_unique_id
        path = f"data/media/{file_id}{ext}"
        media_file = await file.get_file()
        await media_file.download_to_drive(path)
        if not os.path.exists(path):
            await msg.edit_text("Download failed.. Try again later.")
            return
        await msg.edit_text("🤖 Analyzing content...\nThis may take a while ⏳")


        temp_api = gemini_api_keys.copy()
        model = "gemini-2.5-pro" if settings[2] == "gemini-2.5-pro" else "gemini-2.5-flash"
        for _ in range(len(gemini_api_keys)):
            api_key = random.choice(temp_api)
            try:
                client = genai.Client(api_key=api_key)
                media = client.files.upload(file=path)
                response = await client.aio.models.generate_content(
                    model=model,
                    contents = [media, prompt],
                    config=types.GenerateContentConfig(
                        system_instruction=load_persona(settings),
                        tools = tools,
                        thinking_config=types.ThinkingConfig(thinking_budget=settings[3]),
                        temperature = settings[4],
                        safety_settings=[
                        types.SafetySetting(
                            category="HARM_CATEGORY_HARASSMENT",
                            threshold="BLOCK_NONE",
                        ),
                        types.SafetySetting(
                            category="HARM_CATEGORY_HATE_SPEECH",
                            threshold="BLOCK_NONE",
                        ),
                        types.SafetySetting(
                            category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
                            threshold="BLOCK_NONE",
                        ),
                        types.SafetySetting(
                            category="HARM_CATEGORY_DANGEROUS_CONTENT",
                            threshold="BLOCK_NONE",
                        ),
                    ],
                    )
                )
                print(response)
                if response.prompt_feedback and response.prompt_feedback.block_reason:
                    return f"Your response is blocked by gemini because of {response.prompt_feedback.block_reason}. Your conversation history is deleted."
                response.text
                break
            except Exception as e:
                temp_api.remove(api_key)
                if not temp_api:
                    response = "Failed to process your request. Please try again later."
                print(f"Error getting response for API{{gemini_api_keys.index(api_key)}}.\n\nError Code - {e}")

        if type(response) == str:
            if "blocked" in response.lower():
                await reset(update, content, None)
            await msg.edit_text(response)
            return
        if response:
            await send_message(update, content, response, caption, msg)
            await save_media_conversation(update,content, caption, response, chat_id, path, file_id, media_type)
            return
    except Exception as e:
        print(f"Error in handle_media function.\n\n Error Code - {e}")
        await send_to_channel(update, content, channel_id, f"Error in handle_media function \n\nError Code -{e}")
        
        
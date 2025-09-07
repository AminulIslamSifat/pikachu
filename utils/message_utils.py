import asyncio
from collections import defaultdict
from utils.config import channel_id
from telegram import (
    Update,
)
from telegram.ext import(
    ContextTypes,
)
from utils.utils import(
    is_ddos,
    send_to_channel,
    safe_send,
    get_settings,
    is_code_block_open
)
from ext.user_content_tools import (
    save_conversation,
    save_group_conversation
)
import random, os
from ext.user_content_tools import create_prompt
from ai.gemini_schema import gemini_non_stream
from utils.db import gemini_api_keys
import aiofiles
import time





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
        if message.chat.type == "private":
            await save_conversation(user_message, message_to_send, update.effective_user.id)
        elif message.chat.type != "private":
            await save_group_conversation(update, user_message, message_to_send)
    except Exception as e:
        print(f"Error in send_message function Error Code - {e}")
        await send_to_channel(update, content, channel_id, f"Error in send_message function \n\nError Code -{e}")




#a code to handle multiple user at the same time
user_locks = defaultdict(asyncio.Lock)
queue = asyncio.Queue()
async def handle_all_messages():
    while True:
        item = await queue.get()
        try:
            if item is None:
                break
            update, content, bot_name = item
            user_id = update.effective_user.id
            lock = user_locks[user_id]
            async with lock:
                await user_message_handler(update, content, bot_name)
        finally:
            queue.task_done()

#a function to add multiple workers to handle response
async def run_workers(n):
    tasks = []
    for _ in range(n):
        task = asyncio.create_task(handle_all_messages())
        tasks.append(task)
    return tasks



#function to get response from gemini
async def user_message_handler(update:Update, content:ContextTypes.DEFAULT_TYPE, bot_name) -> None:
    try:
        message = update.message or update.edited_message
        global gemini_api_keys
        user_message = message.text.strip()
        user_id = update.effective_user.id
        chat_type = message.chat.type
        if await is_ddos(update, content, user_id):
            return
        if chat_type != "private" and f"{bot_name.lower()}" not in user_message.lower() and "bot" not in user_message.lower() and "@" not in user_message.lower() and "mama" not in user_message.lower() and "pika" not in user_message.lower():
            return
        settings = await get_settings(user_id)
        if message.chat.type != "private":
            group_id = update.effective_chat.id
            settings = (group_id,"group","gemini-2.5-flash",0,0.7,0,"data/persona/Pikachu.shadow")
        prompt = await create_prompt(update, content, user_message, user_id, 0)
        temp_api = gemini_api_keys.copy()
        for _ in range(len(gemini_api_keys)):
            try:
                api = random.choice(temp_api)
                temp_api.remove(api)
                response = await gemini_non_stream(update, content, prompt, api,settings, user_message)
                if response == "false" or response[0].text:
                    break
                if response[0].prompt_feedback and response[0].prompt_feedback.block_reason:
                    await message.reply_text(f"Your response is blocked by gemini because of {response[1].prompt_feedback.block_reason} Conversation history is erased.")
                    break
            except Exception as e:
                print(f"Error getting gemini response for API-{gemini_api_keys.index(api)}. \n Error Code -{e}")
                continue
        if response[0] == None:
            await update.message.reply_text("Failed to get response from gemini. Your conversation history is erased.")
            if os.path.exists(f"data/Conversation/conversation-{user_id}.shadow"):
                async with aiofiles.pen(f"data/Conversation/conversation-{user_id}.shadow", "wb") as f:
                    pass
        elif response != "false" and response[0] != None:
            await send_message(update, content, response[0], user_message, response[1])
            from bot.echo import start_time
            end_time = time.time()
            print(f"Response time - {end_time - start_time}")
    except Exception as e:
        await update.message.reply_text(f"Telegram Limit hit, need to wait {e.retry_after} seconds.")
        await send_to_channel(update, content, channel_id, f"Telegram Limit hit for user {user_id}, He need to wait {e.retry_after} seconds.")

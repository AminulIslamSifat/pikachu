import time
from utils.config import (
    db,
    mdb,
    mongo_url,
    fernet,
    channel_id,
    g_ciphers,
    secret_nonce
)
from utils.db import (
    gemini_api_keys,
    all_user_info
)
from telegram import Update
from telegram.ext import ContextTypes
from google import genai
import asyncio
from utils.message_utils import send_to_channel
import pytz
from google.genai import types
import os
import sqlite3
import aiosqlite
from datetime import datetime
from utils.utils import (
    get_settings,
    load_persona
)
import html
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from flask import request
import aiofiles
from motor.motor_asyncio import AsyncIOMotorClient
import aiosqlite





mdb = AsyncIOMotorClient(mongo_url)["phantom_bot"]



#A function to delete n times convo from conversation history
async def delete_n_convo(user_id, n):
    try:
        key = bytes.fromhex(all_user_info[user_id][6])
        nonce = bytes.fromhex(all_user_info[user_id][7])
        ciphers = AESGCM(key)
        conn = await aiosqlite.connect("user_media/user_media.db")
        c = await conn.execute("select media_path from user_media where user_id = ?", (user_id,))
        paths = await c.fetchall()
        if user_id < 0:
            async with aiofiles.open(f"data/Conversation/conversation-group.txt", "r+", encoding="utf-8") as f:
                data = await f.read()
                data = data.split("You: ")
                if len(data) >= n+1:
                    data = data[n:]
                    await f.seek(0)
                    await f.truncate(0)
                    data =  "You: ".join(data)
                    await f.write(data)
                    await mdb[f"group"].update_one(
                        {"id" : "group"},
                        {"$set" : {"conversation" : data}}
                    )
                elif len(data)-n > n:
                    data = data[-n:]
                    await f.seek(0)
                    await f.truncate(0)
                    data = "You: ".join(data)
                    await f.write(data)
                    await mdb[f"group"].update_one(
                        {"id" : "group"},
                        {"$set" : {"conversation" : data}}
                    )
            return
        async with aiofiles.open(f"data/Conversation/conversation-{user_id}.shadow", "rb") as f:
            data = ciphers.decrypt(nonce, await f.read(), None).decode("utf-8")
            data = data.split("You: ")

            if len(data) >= n+1 and len(data)-n < n:
                data = data[n:]
            elif len(data)-n > n:
                data = data[-n:]

            data = "You: ".join(data)
            data = ciphers.encrypt(nonce, data.encode("utf-8"), None)

            async with aiofiles.open(f"data/Conversation/conversation-{user_id}.shadow", "wb") as f:
                await f.write(data)

            await mdb[f"{user_id}"].update_one(
                {"id" : user_id},
                {"$set" : {"conversation" : data}}
            )

        async with aiofiles.open(f"data/Conversation/conversation-{user_id}.txt", "rb") as file:
            conv_data = ciphers.decrypt(nonce, await file.read(), None).decode("utf-8")
            if not paths:
                return
            for path in paths:
                path = path[0]
                if path not in conv_data:
                    await conn.execute("delete from user_media where media_path = ?", (path,))
                    if os.path.exists(path):
                        os.remove(path)
        await conn.commit()
        await conn.close()
    except Exception as e:
        print(f"Failed to delete conversation history \n Error Code - {e}")


#creating memory, SPECIAL_NOTE: THIS FUNCTION ALWAYS REWRITE THE WHOLE MEMORY, SO THE MEMORY SIZE IS LIMITED TO THE RESPONSE SIZE OF GEMINI, IT IS DONE THIS WAY BECAUSE OTHERWISE THERE WILL BE DUPLICATE DATA 
async def create_memory(update:Update, content:ContextTypes.DEFAULT_TYPE, api, user_id):
    try:
        key = bytes.fromhex(all_user_info[user_id][6])
        nonce = bytes.fromhex(all_user_info[user_id][7])
        ciphers = AESGCM(key)
        message = update.message or update.edited_message
        settings = await get_settings(update.effective_user.id)
        if user_id > 0:
            async with aiofiles.open("data/persona/memory_persona.shadow", "rb") as f:
                instruction = g_ciphers.decrypt(secret_nonce, await f.read(), None).decode("utf-8")
            data = ""
            async with aiofiles.open(f"data/memory/memory-{user_id}.shadow", "rb", encoding = "utf-8") as f:
                pre_mem = await f.read()
                if pre_mem:
                    try:
                        data += "***PREVIOUS MEMORY***\n\n" + ciphers.decrypt(nonce, pre_mem, None).decode("utf-8") + "\n\n***END OF MEMORY***\n\n"
                    except:
                        async with aiofiles.open(f"data/memory/memory-{user_id}.shadow", "wb") as f:
                            pass
                        await mdb[f"{user_id}"].update_one(
                            {"id" : user_id},
                            {"$set" : {"memory" : None}}
                        )
            async with aiofiles.open(f"data/Conversation/conversation-{user_id}.shadow", "rb") as f:
                try:
                    data += "\n\n***CONVERSATION HISTORY***\n\n" + ciphers.decrypt(nonce, await f.read(), None).decode("utf-8") +  "\n\n***END OF CONVERSATION***\n\n"
                except:
                    await reset(update, content, None)
        elif user_id < 0:
            group_id = user_id
            async with aiofiles.open("data/persona/memory_persona.txt", "rb") as f:
                instruction = g_ciphers.decrypt(secret_nonce, await f.read(), None).decode("utf-8")
            async with aiofiles.open(f"data/memory/memory-group.txt", "r", encoding = "utf-8") as f:
                data = "***PREVIOUS MEMORY***\n\n" + await f.read() + "\n\n***END OF MEMORY***\n\n"
            async with aiofiles.open(f"data/Conversation/conversation-group.txt", "r", encoding = "utf-8") as f:
                data += "\n\n***CONVERSATION HISTORY***\n\n" + await f.read() + "\n\n***END OF CONVERSATION***\n\n"
        client = genai.Client(api_key=api)
        prompt = (
                "\n\n Make memory based on the above data."
                "Make it as short and summarized as possible but without missing important information from coversation history and previous memory(if exists)."
                "Again make it short like instead of using user talked about a image about AI that contains blah blah blah use you talked about AI. "
                "And cut out unnecessary information like timestamp, media description etc."
                "And cut out unnecessary info in previous memory and conversation history."
            )
        response = await client.aio.models.generate_content(
            model = "gemini-2.5-flash",
            contents = data + prompt,
            config = types.GenerateContentConfig(
                thinking_config = types.ThinkingConfig(thinking_budget=128),
                temperature = 0.3,
                system_instruction =  instruction,
            ),
        )
        if response.prompt_feedback and response.prompt_feedback.block_reason:
            await message.reply_text(f"Your response is blocked by gemini because of {response.prompt_feedback.block_reason} Conversation history is erased.")
            if os.path.exists(f"data/Conversation/conversation-{user_id}.shadow"):
                await reset(update, content, None)
            return True
        if response.text is not None:
            if user_id > 0:
                async with aiofiles.open(f"data/memory/memory-{user_id}.shadow", "wb") as f:
                    memory = ciphers.encrypt(nonce, response.text.encode("utf-8"), None)
                    await f.write(memory)
                await mdb[f"{user_id}"].update_one(
                    {"id": user_id},
                    {"$set": {"memory": memory}}
                )
                await delete_n_convo(user_id, 15)
            elif user_id < 0:
                group_id = user_id
                async with aiofiles.open(f"data/memory/memory-group.txt", "a+", encoding="utf-8") as f:
                    await f.write(response.text)
                    await f.seek(0)
                    memory = await f.read()
                await mdb[f"group"].update_one(
                    {"id": "group"},
                    {"$set": {"memory": memory}}
                )
                await delete_n_convo(group_id, 100)
            return True
        else:
            if (gemini_api_keys.index(api) > len(gemini_api_keys)-3):
                if os.path.exists(f"data/Conversation/conversation-{user_id}.shadow"):
                    await reset(update, content, None)
                    return True
            else:
                return False
    except Exception as e:
        print(f"Failed to create memory\n Error code-{e}")



#create the conversation history as prompt
async def create_prompt(update:Update, content:ContextTypes.DEFAULT_TYPE, user_message, user_id, media):
    try:
        key = bytes.fromhex(all_user_info[user_id][6])
        nonce = bytes.fromhex(all_user_info[user_id][7])
        ciphers = AESGCM(key)
        bd_tz = pytz.timezone("Asia/Dhaka")
        now = datetime.now(bd_tz).strftime("%d-%m-%Y, %H:%M:%S")
        message = update.message or update.edited_message
        
        if message.chat.type == "private":
            data = "***RULES***\n"
            data += (
                "Never ever user any timestamp in your response."
                "Timestamp is only for you to understand the user better and provide more realistic response"
                "So, You must not use timestamp in your response."
            )
            async with aiofiles.open("data/info/rules.shadow", "rb" ) as f:
                try:
                    data += g_ciphers.decrypt(secret_nonce, await f.read(), None).decode("utf-8")
                except:
                    print("Failed to add rules in prompt")
            async with aiofiles.open(f"data/memory/memory-{user_id}.shadow", "rb") as f:
                mem_data = await f.read()
                if mem_data:
                    try:
                        data += "\n\n***MEMORY***\n" + ciphers.decrypt(nonce, mem_data, None).decode("utf-8")
                    except:
                        async with aiofiles.open(f"data/memory/memory-{user_id}.shadow", "wb") as f:
                            pass
                        await mdb[f"{user_id}"].update_one(
                            {"id": user_id},
                            {"$set": {"memory": None}}
                        )
            async with aiofiles.open(f"data/Conversation/conversation-{user_id}.shadow", "rb") as f:
                conv_data = await f.read()
                if conv_data:
                    try:
                        data += "\n\n***CONVERSATION HISTORY***\n\n" + ciphers.decrypt(nonce, conv_data, None).decode("utf-8") + f"\n[{now}] {all_user_info[user_id][1]}: " + user_message
                        if(data.count("You: ")>30):
                            await asyncio.create_task(background_memory_creation(update, content, user_id))
                    except:
                        data += f"\n[{now}] {all_user_info[user_id][1]}: " + user_message
                        await reset(update, content, None)
                else:
                    data += f"\n\n***CONVERSATION HISTORY***\n\n[{now}] {all_user_info[user_id][1]}: " + user_message
            if data:
                return data
            else:
                return "Hi"
        if message.chat.type != "private":
            data = "***RULES***\n"
            async with aiofiles.open("data/info/group_rules.shadow", "rb") as f:
                data += g_ciphers.decrypt(secret_nonce, await f.read(), None).decode("utf-8") + "\n***END OF RULES***\n\n\n"
            async with aiofiles.open("data/info/group_training_data.shadow", "rb") as f:
                try:
                    data +=  "******TRAINING DATA******\n\n" + g_ciphers.decrypt(secret_nonce, await f.read(), None).decode("utf-8") + "******END OF TRAINING DATA******\n\n"
                except:
                    pass         
            async with aiofiles.open(f"data/memory/memory-group.txt", "r", encoding="utf-8") as f:
                data += "***MEMORY***\n" + await f.read() + "\n***END OF MEMORY***\n\n\n"
            async with aiofiles.open(f"data/Conversation/conversation-group.txt", "r", encoding="utf-8") as f:
                data += "\n\n***CONVERSATION HISTORY***\n\n" + await f.read() + "\nUser: " + user_message
                if(data.count("You: ")>200):
                    asyncio.create_task(background_memory_creation(update, content, user_id))
            if data:
                return data
            else:
                return "Hi"
    except Exception as e:
        print(f"Error in create_promot function. \n\n Error Code - {e}")
        await send_to_channel(update, content, channel_id, f"Error in create_prompt function. \n\n Error Code - {e}")


#function to save conversation
async def save_conversation(user_message : str , gemini_response:str , user_id:int) -> None:
    try:
        key = bytes.fromhex(all_user_info[user_id][6])
        nonce = bytes.fromhex(all_user_info[user_id][7])
        ciphers = AESGCM(key)
        bd_tz = pytz.timezone("Asia/Dhaka")
        now = datetime.now(bd_tz).strftime("%d-%m-%Y, %H:%M:%S")
        name = all_user_info[user_id][1]
        
        async with aiofiles.open(f"data/Conversation/conversation-{user_id}.shadow", "rb") as f:
            conv_data = await f.read()
            if conv_data:
                data = ciphers.decrypt(nonce,conv_data, None).decode("utf-8")
            else:
                data = ""
        async with aiofiles.open(f"data/Conversation/conversation-{user_id}.shadow", "wb") as f:
            if user_message == None:
                data += gemini_response + "\n"
                data = ciphers.encrypt(nonce, data.encode("utf-8"), None)
                await f.write(data)
            else:
                data += f"\n[{now}] {name}: {user_message}\nYou: {gemini_response}\n"
                data = ciphers.encrypt(nonce, data.encode("utf-8"), None)
                await f.write(data)
        await mdb[f"{user_id}"].update_one(
            {"id" : user_id},
            {"$set" : {"conversation" : data}}
        )
    except Exception as e:
        async with aiofiles.open(f"data/Conversation/conversation-{user_id}.shadow", "wb") as f:
            pass
        await mdb[f"{user_id}"].update_one(
            {"id" : user_id},
            {"$set" : {"conversation" : None}}
        )
        print(f"Error in saving conversation. \n\n Error Code - {e}")


#function to save group conversation
async def save_group_conversation(update : Update,user_message, gemini_response):
    try:
        name = update.effective_user.first_name or "X" +" "+ update.effective_user.last_name or "X"
        async with aiofiles.open(f"data/Conversation/conversation-group.txt", "a+", encoding="utf-8") as f:
            await f.write(f"\n{name}: {user_message}\nYou: {gemini_response}\n")
            await f.seek(0)
            data = await f.read()
        await mdb["group"].update_one(
            {"id": "group"},
            {"$set": {"conversation": data}}
        )
    except Exception as e:
        print(f"Error in saving conversation. \n\n Error Code - {e}")


#function to create memory in background
async def background_memory_creation(update: Update,content,user_id):
    try:
        message = update.message or update.edited_message
        if message.chat.type == "private":
            for api in gemini_api_keys:
                result = await asyncio.create_task(create_memory(update, content, api, user_id))
                if result:
                    break
        elif message.chat.type != "private":
            group_id = update.effective_chat.id
            for api in gemini_api_keys:
                result = await asyncio.create_task(create_memory(update, content, api, group_id))
                if result:
                    break
    except Exception as e:
        print(f"Error in background_memory_creation function.\n\n Error Code -{e}")
        await send_to_channel(update, content, channel_id, f"Error in background_memory_creation function.\n\n Error Code -{e}")



#function for deleting memory
async def delete_memory(update : Update, content : ContextTypes.DEFAULT_TYPE, query) -> None:
    try:
        user_id = update.effective_chat.id
        async with aiofiles.open(f"data/memory/memory-{update.callback_query.from_user.id}.shadow", "wb") as f:
            pass
        await mdb[f"{user_id}"].update_one(
            {"id": user_id},
            {"$set": {"memory": None}}
        )
        await query.edit_message_text("You cleared my memory about you, It really makes me sad.")
    except Exception as e:
        print(f"Error in delete_memory function.\n\nError Code - {e}")
        await send_to_channel(update, content, channel_id, f"Error in delete_memory function \n\nError Code -{e}")



#function for the resetting the conversation history
async def reset(update : Update, content : ContextTypes.DEFAULT_TYPE, query) -> None:
    try:
        if query:
            user_id = update.callback_query.from_user.id
            try:
                if update.message.chat.type != "private":
                    await update.message.reply_text("This function is not available in group. I don't save conversation of group.")
                    return
            except:
                pass
            if os.path.exists(f"data/Conversation/conversation-{user_id}.shadow"):
                async with aiofiles.open(f"data/Conversation/conversation-{user_id}.shadow", "wb") as f:
                    pass
                await mdb[f"{user_id}"].update_one(
                    {"id": user_id},
                    {"$set": {"conversation": None}}
                )
                await query.edit_message_text("All clear, Now we are starting fresh.")
            else:
                await query.edit_message_text("It seems you don't have a conversation at all.")
            conn = await aiosqlite.connect("user_media/user_media.db")
            c = await conn.execute("select media_path from user_media where user_id = ?", (user_id,))
            paths = await c.fetchall()
            if not paths:
                return
            for path in paths:
                path = path[0]
                await conn.execute("delete from user_media where media_path = ?", (path,))
                if os.path.exists(path):
                    os.remove(path)
            await conn.commit()
            await conn.close()
        else:
            user_id = update.effective_chat.id
            try:
                if update.message.chat.type != "private":
                    await update.message.reply_text("This function is not available in group. I don't save conversation of group.")
                    return
            except:
                pass
            if os.path.exists(f"data/Conversation/conversation-{user_id}.shadow"):
                async with aiofiles.open(f"data/Conversation/conversation-{user_id}.shadow", "wb") as f:
                    pass
                await mdb[f"{user_id}"].update_one(
                    {"id": user_id},
                    {"$set": {"conversation": None}}
                )
                await update.message.reply_text("All clear, Now we are starting fresh.")
            else:
                await update.message.reply_text("It seems you don't have a conversation at all.")
            conn = await aiosqlite.connect("user_media/user_media.db")
            c = await conn.execute("select media_path from user_media where user_id = ?", (user_id,))
            paths = await c.fetchall()
            if not paths:
                return
            for path in paths:
                path = path[0]
                await conn.execute("delete from user_media where media_path = ?", (path,))
                if os.path.exists(path):
                    os.remove(path)
            await conn.commit()
            await conn.close()
    except Exception as e:
        if update.callback_query:
            await update.callback_query.message.reply_text(f"Sorry, The operation failed. Here's the error message:\n<pre>{html.escape(str(e))}</pre>", parse_mode="HTML")
        else:
            await update.message.reply_text(f"Sorry, The operation failed. Here's the error message:\n<pre>{html.escape(str(e))}</pre>", parse_mode="HTML")
        await send_to_channel(update, content, channel_id, f"Error in reset function \n\nError Code -{e}")


   #A function to return memory for user convention
async def see_memory(update : Update, content : ContextTypes.DEFAULT_TYPE, query) -> None:
    try:
        user_id = update.callback_query.from_user.id
        key = bytes.fromhex(all_user_info[user_id][6])
        nonce = bytes.fromhex(all_user_info[user_id][7])
        ciphers = AESGCM(key)
        try:
            if update.message.chat.type != "private":
                await update.message.reply_text("Memory is not visible from group. Privacy concern idiot.")
                return
        except:
            pass
        async with aiofiles.open(f"data/memory/memory-{user_id}.shadow", "rb") as f:
            mem_data = await f.read()
            if mem_data:
                data = ciphers.decrypt(nonce, mem_data, None).decode("utf-8")
                await query.edit_message_text("Here is my Diary about you:")
            
                if len(data) > 4080:
                    messages = [data[i:i+4080] for i in range(0, len(data), 4080)]
                else:
                    messages = [data]
                for message in messages:
                    try:
                        await update.callback_query.message.reply_text(message, parse_mode="Markdown")
                    except:
                        await update.callback_query.message.reply_text(message)
            else:
                await query.edit_message_text("I haven't written anything about you. You expected something huh\nLOL")
                
    except Exception as e:
        print(f"Error in see_memory function.\n\nError Code - {e}")
        await send_to_channel(update.callback_query, content, channel_id, f"Error in see_memory function \n\nError Code -{e}")

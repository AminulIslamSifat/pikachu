import os
import shutil
import sqlite3
import asyncio
from utils.db import (
    all_users,
    db,
    mdb,
    all_user_info
)
from utils.config import (
    g_ciphers,
    secret_nonce,
    fernet
)
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import aiofiles
import aiosqlite








#function to create settings file MongoDB to offline for optimization
async def create_settings_file():
    try:
        print("settings, ", end="")
        shutil.rmtree("data/settings", ignore_errors=True)
        os.makedirs("data/settings", exist_ok=True)
        conn = await aiosqlite.connect("data/settings/user_settings.db")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS user_settings(
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                model TEXT,
                thinking_budget INTEGER,
                temperature REAL,
                streaming INTEGER,
                persona TEXT
            )
        """)
        for user in all_users:
            settings = tuple((await mdb[f"{user}"].find_one({}))["settings"])
            await conn.execute("""
                INSERT OR IGNORE INTO user_settings 
                (id, name, model, thinking_budget, temperature, streaming, persona)
                VALUES (?,?,?,?,?,?,?)
        """, settings
        )
        await conn.commit()
        await conn.close()
    except Exception as e:
        print(f"Error in create_settings_file function.\n\nError Code - {e}")


#function to create offline file for conversation history
async def create_conversation_file():
    try:
        print("conversation file")
        shutil.rmtree("data/Conversation", ignore_errors=True)
        os.makedirs("data/Conversation", exist_ok=True)
        for user in all_users:
            conv_data = (await mdb[f"{user}"].find_one({}))["conversation"]
            async with aiofiles.open(f"data/Conversation/conversation-{user}.shadow", "wb") as file:
                if conv_data:
                    await file.write(conv_data)
                else:
                    pass
        try:
            conv_data = await mdb["group"].find_one({})["conversation"]
            async with aiofiles.open(f"data/Conversation/conversation-group.txt", "w") as file:
                await file.write(conv_data)
        except:
            print("Group conversation doesn't exist")
            async with aiofiles.open(f"data/Conversation/conversation-group.txt", "w") as file:
                pass
    except Exception as e:
        print(f"Error in create_conversation_file function. \n\n Error Code  {e}")


#function to create offline file for memory
async def create_memory_file():
    try:
        print("memory, ", end="")
        shutil.rmtree("data/memory", ignore_errors=True)
        os.makedirs("data/memory", exist_ok=True)
        for user in all_users:
            mem_data = (await mdb[f"{user}"].find_one({}))["memory"]
            async with aiofiles.open(f"data/memory/memory-{user}.shadow", "wb") as file:
                if mem_data:
                    await file.write(mem_data)
                else:
                    pass
        try:
            mem_data = await mdb["group"].find_one({})["memory"]
            async with aiofiles.open(f"data/memory/memory-group.txt", "w") as file:
                await file.write(mem_data)
        except:
            async with aiofiles.open(f"data/memory/memory-group.txt", "w") as file:
                pass
    except Exception as e:
        print(f"Error in create_memory_file function. \n\n Error Code  {e}")


#function to create offline file for memory
async def create_persona_file():
    try:
        print("persona, ", end="")
        shutil.rmtree("data/persona", ignore_errors=True)
        os.makedirs("data/persona", exist_ok=True)
        personas = await mdb["persona"].find({"type":"persona"}).to_list(None)
        for persona in personas:
            async with aiofiles.open(f"data/persona/{persona['name']}.shadow", "wb") as f:
                await f.write(g_ciphers.encrypt(secret_nonce, persona["persona"].encode("utf-8"), None))
    except Exception as e:
        print(f"Error in create_persona_file function. \n\n Error Code  {e}")

    
#function to create user_data file MongoDB to offline for optimization
async def create_user_data_file():
    try:
        print("user_data, ", end="")
        if os.path.exists("data/info/user_data.db"):
            try:
                os.remove("data/info/user_data.db")
            except:
                pass
        os.makedirs("data/info", exist_ok=True)
        conn = await aiosqlite.connect("data/info/user_data.db")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users(
                user_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                gender TEXT,
                roll INTEGER,
                password TEXT,
                api TEXT,
                secret_key TEXT,
                nonce TEXT
            )
        """)
        for user in all_users:
            user_data = tuple(data for data in (await mdb[f"{user}"].find_one({"id":user}))["user_data"])
            await conn.execute("""
                INSERT OR IGNORE INTO users 
                (user_id, name, gender, roll, password, api, secret_key, nonce)
                VALUES (?,?,?,?,?,?,?,?)
        """, user_data
        )
        await conn.commit()
        await conn.close()
    except Exception as e:
        print(f"Error in create_user_data_file function. \n\nError Code- {e}")


#function to create a password file for admin
async def create_admin_pass_file():
    try:
        print("admin, ", end="")
        shutil.rmtree("data/admin", ignore_errors=True)
        os.makedirs("data/admin", exist_ok=True)
        content = (await mdb["admin"].find_one({"type" : "admin"}))["admin_password"]
        content = fernet.encrypt(content.encode())
        async with aiofiles.open("data/admin/admin_password.shadow", "wb") as f:
            await f.write(content)
    except Exception as e:
        print(f"Error in create_admin_pass_file function.\n\nError Code - {e}")


#function to create routine folder offline
async def create_routine_file():
    try:
        print("routine, ", end="")
        shutil.rmtree("data/routine", ignore_errors=True)
        os.makedirs("data/routine", exist_ok=True)
        async with aiofiles.open("data/routine/lab_routine.txt", "w") as f:
            data = (await mdb["routine"].find_one({"type" : "routine"}))["lab_routine"]
            await f.write(data)
        async with aiofiles.open("data/routine/rt1.png", "wb") as f:
            data = (await mdb["routine"].find_one({"type" : "routine"}))["rt1"]
            await f.write(data)
        async with aiofiles.open("data/routine/rt2.png", "wb") as f:
            data = (await mdb["routine"].find_one({"type" : "routine"}))["rt2"]
            await f.write(data)
    except Exception as e:
        print(f"Error in create_routine_file function. Error Code - {e}")


#function to create info file locally from MongoDB
async def create_info_file():
    try:
        print("Creating info, ", end="")
        shutil.rmtree("data/info", ignore_errors=True)
        os.makedirs("data/info",exist_ok=True)
        collection = mdb["info"]
        info_files = await collection.find({"type" : "info"}).to_list(None)
        for file in info_files:
            file_name = file["name"]
            path = f"data/info/{file_name}.shadow"
            async with aiofiles.open(path, "wb") as f:
                await f.write(g_ciphers.encrypt(secret_nonce, file["data"].encode("utf-8"), None))
    except Exception as e:
        print(f"Error in create_info_file function.\n\nError Code - {e}")


#calling all those function to create offline file from MongoDB
async def load_all_files():
    try:
        print("Loading all files and folder...")
        os.makedirs("ext", exist_ok=True)
        await create_info_file()
        await create_memory_file()
        await create_persona_file()
        await create_routine_file()
        await create_settings_file()
        await create_user_data_file()
        await create_admin_pass_file()
        await create_conversation_file()
        print("Successfully loaded all file and folder.")
    except Exception as e:
        print(f"Error in load_all_file function. \n\nError code - {e}")

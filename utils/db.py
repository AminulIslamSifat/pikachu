from utils.config import g_ciphers, secret_nonce, db, mongo_url
import aiofiles
import aiosqlite
from glob import glob
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient



mdb = AsyncIOMotorClient(mongo_url)["phantom_bot"]


# Global variables
TOKEN: str | None = None
premium_users: tuple = ()
gemini_api_keys: list = []
gemini_model_list: list = []
all_users: list = []
all_admins: list = []
all_persona: dict = {}
all_settings: dict = {}
all_user_info: dict = {}



#loading the bot api
async def get_token():
    try:
        TOKENs = (await mdb["API"].find_one({}))["bot_api"]
        return TOKENs
    except Exception as e:
        print(f"Error Code -{e}")


#all registered user
async def load_all_user():
    try:
        users = tuple(int(user) for user in (await mdb.list_collection_names()) if user.isdigit())
        return users
    except Exception as e:
        print(f"Error in load_all_user fnction.\n\n Error code -{e}")
        return ()


#function to load all admin
async def load_admin():
    try:
        admins = tuple(int(admin) for admin in (await mdb["admin"].find_one({}))["admin"])
        return admins
    except Exception as e:
        print(f"Error in load_admin function.\n\nError Code - {e}")
        return ()


#function to load all gemini model
async def load_gemini_model():
    try:
        models = tuple((await mdb["ai_model"].find_one({}))["model_name"])
        return models
    except Exception as e:
        print(f"Error Loading Gemini Model.\n\nError Code -{e}")
        return None
    

#function to load gemini_api
async def load_gemini_api():
    try:
        api_list = (await mdb["API"].find_one({}))["gemini_api"]
        api_list = tuple(api_list)
        return api_list
    except Exception as e:
        print(f"Error lading gemini API. \n\nError Code -{e}")
        return ()


#function to load all user settings as dictionary
async def load_all_user_settings():
    try:
        user_settings = {}
        conn = await aiosqlite.connect("data/settings/user_settings.db")
        c = await conn.execute("select * from user_settings")
        for settings in await c.fetchall():
            user_settings[settings[0]] = settings
        await conn.close()
        return user_settings
    except Exception as e:
        print(f"Error in load_all_user_settings function.\n\nError Code - {e}")
        return {}


#function to load all users info
async def load_all_user_info():
    try:
        user_info = {}
        conn = await aiosqlite.connect("data/info/user_data.db")
        c = await conn.execute("select * from users")
        for info in await c.fetchall():
            user_info[info[0]] = info
        await conn.close()
        return user_info
    except Exception as e:
        print(f"Error in load_all_user_info function.\n\nError Code - {e}")
        return {}


#function to load all persona in dictionary for faster access
async def load_all_persona():
    try:
        all_persona_local = {}
        persons_link = sorted(glob("data/persona/*shadow"))
        for link in persons_link:
            async with aiofiles.open(link, "rb") as f:
                persona = g_ciphers.decrypt(secret_nonce, await f.read(), None).decode("utf-8")
                all_persona_local[link] = persona
        return all_persona_local
    except Exception as e:
        print(f"Error in load_all_persona function.\n\nError Code - {e}")
        return {}
                




async def initialize_bot():
    global premium_users, gemini_api_keys, gemini_model_list, all_users, all_admins, TOKEN
    premium_users = ("5888166321", "6226239719")
    
    loaded_gemini_api_keys = await load_gemini_api()
    gemini_api_keys.clear()
    if loaded_gemini_api_keys:
        gemini_api_keys.extend(loaded_gemini_api_keys)

    loaded_gemini_model_list = await load_gemini_model()
    gemini_model_list.clear()
    if loaded_gemini_model_list:
        gemini_model_list.extend(loaded_gemini_model_list)

    loaded_all_users = await load_all_user()
    all_users.clear()
    if loaded_all_users:
        all_users.extend(loaded_all_users)

    loaded_all_admins = await load_admin()
    all_admins.clear()
    if loaded_all_admins:
        all_admins.extend(loaded_all_admins)
        
    tokens = await get_token()
    if tokens:
        TOKEN = tokens[0]




async def populate_db_caches():
    """Populates the global settings and user info dictionaries from the database files."""
    global all_settings, all_user_info, all_persona
    
    settings_from_db = await load_all_user_settings()
    all_settings.clear()
    all_settings.update(settings_from_db)
        
    user_info_from_db = await load_all_user_info()
    all_user_info.clear()
    all_user_info.update(user_info_from_db)

    all_persona_from_db = await load_all_persona()
    all_persona.clear()
    all_persona.update(all_persona_from_db)

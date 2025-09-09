from telegram import (
    Update,
    ReplyKeyboardMarkup,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton
)
from telegram.ext import(
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
    ConversationHandler,
    CallbackQueryHandler,
)
import asyncio, html

from utils.config import (
    fernet,
    db,
    mdb,
    channel_id,
    g_ciphers,
    secret_nonce
)
from utils.db import (
    load_admin,
    load_gemini_api,
    load_all_user,
    load_gemini_model,
    gemini_api_keys,
    load_all_user_info,
    all_user_info
)
import sqlite3
import aiosqlite
import aiofiles
from utils.utils import get_settings
from utils.utils import (
    add_escape_character,
    send_to_channel
)
from telegram.constants import ChatAction
from google import genai
import os
from fpdf import FPDF
from glob import glob
from datetime import datetime, timezone
from io import BytesIO
from geopy.distance import geodesic
from google import genai
from circulation.circulate import (
    circulate_message,
    circulate_attendance,
    user_message_id
)
from utils.db import (
    all_users,
    all_admins,
    all_settings,
    load_all_user_settings
)
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import aiofiles
from telegram.error import TimedOut







#function for the command api
async def api(update : Update, content : ContextTypes.DEFAULT_TYPE) -> None:
    for retry in range(5):
        try:
            if update.message.chat.type != "private":
                await update.message.reply_text("This function is only available in private chat.")
                return
            keyboard = [[InlineKeyboardButton("cancel", callback_data="cancel_conv")]]
            markup = InlineKeyboardMarkup(keyboard)
            async with aiofiles.open("data/info/getting_api.shadow", "rb") as f:
                data = g_ciphers.decrypt(secret_nonce, await f.read(), None).decode("utf-8")
                await update.message.reply_text(data, reply_markup=markup)
            return 1
        except TimedOut:
            print(f"Timed out error. Retrying for the {retry+1} times")
        except Exception as e:
            print(f"Error in api function.\nError Code - {e}")
            await send_to_channel(update, content, channel_id, f"Error in api function \n\nError Code -{e}")
            return


#function to handle api
async def handle_api(update : Update, content : ContextTypes.DEFAULT_TYPE) -> None:
    try:
        global gemini_api_keys
        user_api = update.message.text.strip()
        await update.message.chat.send_action(action = ChatAction.TYPING)
        try:
            client = genai.Client(api_key=user_api)
            response = await client.aio.models.generate_content(
                model = "gemini-2.5-flash",
                contents = ["Checking if the gemini api working or not respond with one word."]
            )
            chunk = response.text
            if(
                user_api.startswith("AIza")
                and user_api not in gemini_api_keys
                and " " not in user_api
                and len(user_api) >= 39
                and chunk
            ):
                await mdb["API"].update_one(
                    {"type" : "api"},
                    {"$push" : {"gemini_api" : user_api}}
                )
                await update.message.reply_text("The API is saved successfully.")
                gemini_api_keys = await load_gemini_api()
                return ConversationHandler.END
            else:
                await update.message.reply_text("Sorry, This is an invalid or Duplicate API, try again with a valid API.")
                return ConversationHandler.END
        except Exception as e:
            await update.message.reply_text(f"Sorry, It doesn't seems like a valid API. Here's the error message:\n<pre>{html.escape(str(e))}</pre>", parse_mode="HTML")
            return ConversationHandler.END
    except Exception as e:
        print(f"Error in handling api. \n Error Code - {e}")
        await send_to_channel(update, content, channel_id, f"Error in handle_api function \n\nError Code -{e}")





#function to take message for circulate message
async def message_taker(update:Update, content:ContextTypes.DEFAULT_TYPE) -> None:
    try:
        query = update.callback_query
        await query.answer()
        content.user_data["circulate_message_query"] = query.data
        keyboard = [[InlineKeyboardButton("Cancel", callback_data="cancel_conv")]]
        mt_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text("Enter the message here:", reply_markup=mt_markup)
        return "CM"
    except Exception as e:
        print(f"Error in message_taker function.\n\nError Code -{e}")
        await query.edit_message_text(f"Internal Error - {e}.\n\n. Please try again later or contact admin.")
        return ConversationHandler.END


#function to take password for admin function
async def admin_password_taker(update: Update, content:ContextTypes.DEFAULT_TYPE) -> None:
    try:
        Keyboard = [[InlineKeyboardButton("Cancel", callback_data="cancel_conv")]]
        pt_markup = InlineKeyboardMarkup(Keyboard)
        msg = await update.callback_query.edit_message_text("Password for Admin:", reply_markup=pt_markup)
        content.user_data["pt_message_id"] = msg.message_id
        return "MA"
    except Exception as e:
        print(f"Error in admin_password_taker function.\n\nError Code -{e}")
        await update.message.reply_text(f"Internal Error - {e}.\n\n. Please try again later or contact admin.")
        return ConversationHandler.END


#function to create background task for circulate message
async def handle_circulate_message(update:Update, content:ContextTypes.DEFAULT_TYPE) -> None:
    try:
        asyncio.create_task(circulate_message(update, content))
        return ConversationHandler.END
    except Exception as e:
        print(f"Error in handle_circulate_message function.\n\nError Code -{e}")
        await update.message.reply_text(f"Internal Error - {e}.\n\n. Please try again later or contact admin.")
        return ConversationHandler.END


#function to manage admin
async def manage_admin(update:Update, content:ContextTypes.DEFAULT_TYPE) -> None:
    try:
        msg_id = content.user_data.get("pt_message_id")
        try:
            await content.bot.delete_message(chat_id=update.effective_chat.id, message_id=msg_id)
        except:
            pass
        given_password = update.message.text.strip()
        async with aiofiles.open("data/admin/admin_password.shadow", "rb") as file:
            password = fernet.decrypt(await file.read().strip()).decode("utf-8")
        if password != given_password:
            await update.message.reply_text("Wrong Password.")
            return ConversationHandler.END
        else:
            keyboard = [
                [InlineKeyboardButton("See All Admin", callback_data="see_all_admin")],
                [InlineKeyboardButton("Add Admin", callback_data="add_admin"), InlineKeyboardButton("Delete Admin", callback_data="delete_admin")],
                [InlineKeyboardButton("Cancel", callback_data="cancel_conv")]
            ]
            ma_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("Please chose an option:", reply_markup=ma_markup)
            
            return "ADMIN_ACTION"
    except Exception as e:
        print(f"Error in manage_admin function.\n\nError Code -{e}")
        await update.message.reply_text(f"Internal Error - {e}.\n\n. Please try again later or contact admin.")
        return ConversationHandler.END


#function to manage admin action
async def admin_action(update:Update, content:ContextTypes.DEFAULT_TYPE) -> None:
    try:
        query = update.callback_query
        await query.answer()
        keyboard = [[InlineKeyboardButton("cancel", callback_data="cancel_conv")]]
        markup = InlineKeyboardMarkup(keyboard)
        if query.data == "add_admin":
            msg = await query.edit_message_text("Enter the user_id to add as admin:", reply_markup=markup)
            content.user_data["admin_action"] = "add_admin"
            content.user_data["aa_message_id"] = msg.message_id
        elif query.data == "delete_admin":
            msg = await query.edit_message_text("Enter the user_id to delete an admin:", reply_markup=markup)
            content.user_data["admin_action"] = "delete_admin"
            content.user_data["aa_message_id"] = msg.message_id
        elif query.data == "see_all_admin":
            if all_admins:
                admin_data = "All Active Admin:\n"
                for i,admin in enumerate(all_admins):
                    admin_data += f"{i+1}. {admin}\n"
                await query.edit_message_text(admin_data)
                return ConversationHandler.END
            else:
                await query.edit_message_text("There is currently no active admin.")
        return "ENTER_USER_ID"
    except Exception as e:
        print(f"Error in manage_admin function.\n\nError Code -{e}")
        await update.message.reply_text(f"Internal Error - {e}.\n\n. Please try again later or contact admin.")
        return ConversationHandler.END


#function to add or delete admin
async def add_or_delete_admin(update:Update, content:ContextTypes.DEFAULT_TYPE) -> None:
    try:
        global all_admins
        user_id = int(update.message.text.strip())
        action = content.user_data.get("admin_action")
        msg_id = content.user_data.get("aa_message_id")
        await content.bot.delete_message(chat_id=update.effective_chat.id, message_id=msg_id)
        global all_admins
        if action == "add_admin":
            if user_id not in all_admins:
                await mdb["admin"].update_one(
                    {"type" : "admin"},
                    {"$push" : {"admin" : user_id}}
                )
                await update.message.reply_text(f"Successfully added {user_id} user_id as Admin.")
                all_admins = await load_admin()
            else:
                await update.message.reply_text(f"{user_id} is already an Admin.")
            return ConversationHandler.END
        elif action == "delete_admin":
            if user_id in all_admins or str(user_id) in all_admins:
                try:
                    await mdb["admin"].update_one(
                        {"type" : "admin"},
                        {"$pull" : {"admin" : user_id}}
                    )
                except:
                    await mdb["admin"].update_one(
                        {"type" : "admin"},
                        {"$pull" : {"admin" : str(user_id)}}
                    )
                await update.message.reply_text(f"Successfully deleted {user_id} from admin.")
                all_admins = await load_admin()
            else:
                await update.message.reply_text(f"{user_id} is not an Admin.")
            return ConversationHandler.END
    except Exception as e:
        print(f"Error in add_or_delete_admin function.\n\nError Code -{e}")
        await update.message.reply_text(f"Internal Error - {e}.\n\n. Please try again later or contact admin.")
        return ConversationHandler.END


#function to register a new user
async def take_name(update:Update, content:ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.callback_query.from_user.id if update.callback_query else update.effective_user.id
        if user_id in all_users:
            await update.message.reply_text("You are already registered.")
            return ConversationHandler.END
        keyboard = [[InlineKeyboardButton("Cancel", callback_data="cancel_conv")]]
        markup = InlineKeyboardMarkup(keyboard)
        if update.callback_query:
            msg = await update.callback_query.edit_message_text("Enter Your Name: ", reply_markup=markup)
            content.user_data["tn_message_id"] = msg.message_id
            return "TG"
        else:
            msg = await update.message.reply_text("Enter Your Name: ", reply_markup=markup)
            content.user_data["tn_message_id"] = msg.message_id
            return "TG"
    except Exception as e:
        print(f"Error in take_name function.\n\nError Code -{e}")
        await update.message.reply_text(f"Internal Error - {e}.\n\n. Please try again later or contact admin.")
        return ConversationHandler.END


#fuction to take gender from user
async def take_gender(update:Update, content: ContextTypes.DEFAULT_TYPE):
    try:
        name = update.message.text.strip()
        content.user_data["user_name"] = name
        keyboard = [
            [InlineKeyboardButton("Male", callback_data="c_male"), InlineKeyboardButton("Female", callback_data="c_female")],
            [InlineKeyboardButton("Cancel", callback_data="cancel_conv")]
        ]
        markup = InlineKeyboardMarkup(keyboard)
        msg = await update.message.reply_text("Select Your Gender: ", reply_markup=markup)
        await content.bot.delete_message(chat_id=update.effective_user.id, message_id=content.user_data.get("tn_message_id"))
        
        content.user_data["tg_message_id"] = msg.message_id
        return "TR"
    except Exception as e:
        print(f"Error in take_gender function.\n\nError Code -{e}")
        await update.message.reply_text(f"Internal Error - {e}.\n\n. Please try again later or contact admin.")
        return ConversationHandler.END


#function to handle gender action
async def take_roll(update: Update, content:ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        if query.data == "c_male":
            content.user_data["gender"] = "male"
        elif query.data == "c_female":
            content.user_data["gender"] = "female"
        keyboard = [[InlineKeyboardButton("Cancel", callback_data="cancel_conv")]]
        markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Please Enter Your Roll number:", reply_markup=markup)
        return "RA"
    except Exception as e:
        print(f"Error in take_roll function.\n\nError Code -{e}")
        await update.message.reply_text(f"Internal Error - {e}.\n\n. Please try again later or contact admin.")
        return ConversationHandler.END


#function to check if the provided roll is valid
async def roll_action(update:Update, content:ContextTypes.DEFAULT_TYPE):
    try:
        roll = update.message.text.strip()
        if len(roll) != 7:
            msg = await update.message.reply_text("Invalid format. Try again with your full roll number.")
            content.user_data["tr_message_id"] = msg.message_id
            await content.bot.delete_message(chat_id=update.effective_user.id, message_id=content.user_data.get("tg_message_id"))
            
            return ConversationHandler.END
        if not roll.startswith("2403"):
            msg = await update.message.reply_text("This bot is only available for CSE Section C of 24 series.")
            content.user_data["tr_message_id"] = msg.message_id
            await content.bot.delete_message(chat_id=update.effective_user.id, message_id=content.user_data.get("tg_message_id"))
            
            return ConversationHandler.END
        else:
            try:
                conn = await aiosqlite.connect("data/info/user_data.db")
                cursor = await conn.execute("SELECT roll FROM users")
                roll = int(roll)
                rows = await cursor.fetchall()
                await conn.close()
                all_rolls = tuple(row[0] for row in rows)
            except:
                msg = await update.message.reply_text("Invalid Roll Number.")
                content.user_data["tr_message_id"] = msg.message_id
                await content.bot.delete_message(chat_id=update.effective_user.id, message_id=content.user_data.get("tg_message_id"))
                
                return ConversationHandler.END
            if roll<2403120 or roll>2403180:
                msg = await update.message.reply_text("Sorry you are not allowed to use this bot")
                content.user_data["tr_message_id"] = msg.message_id
                await content.bot.delete_message(chat_id=update.effective_user.id, message_id=content.user_data.get("tg_message_id"))
                
                return ConversationHandler.END
            else:
                if roll in all_rolls:
                    content.user_data["roll"] = roll
                    await update.message.reply_text("This account already exists.\n\nPlease enter your password to login:")
                    return "TUP"
                content.user_data["roll"] = roll
                keyboard = [[InlineKeyboardButton("Skip", callback_data="c_skip"),InlineKeyboardButton("Cancel",callback_data="cancel_conv")]]
                markup = InlineKeyboardMarkup(keyboard)
                async with aiofiles.open("data/info/getting_api.shadow", "rb") as file:
                    help_data = add_escape_character(g_ciphers.decrypt(secret_nonce, await file.read(), None).decode("utf-8"))
                msg = await update.message.reply_text(help_data, reply_markup=markup, parse_mode="MarkdownV2")
                content.user_data["ra_message_id"] = msg.message_id
                await content.bot.delete_message(chat_id=update.effective_user.id, message_id=content.user_data.get("tg_message_id"))
                
                return "AH"
    except Exception as e:
        print(f"Error in roll_action function.\n\nError Code -{e}")
        await update.message.reply_text(f"Internal Error - {e}.\n\n. Please try again later or contact admin.")
        return ConversationHandler.END



#function to take user password for login or confidential report
async def take_user_password(update:Update, content:ContextTypes.DEFAULT_TYPE) -> None:
    try:
        user_password = update.message.text.strip()
        conn = await aiosqlite.connect("data/info/user_data.db")
        cursor = await conn.execute("SELECT password FROM users WHERE roll = ?", (content.user_data.get("roll"),))
        password = (await cursor.fetchone())[0]
        await conn.close()
        if user_password == password:
            keyboard = [[InlineKeyboardButton("Skip", callback_data="c_skip"),InlineKeyboardButton("Cancel",callback_data="cancel_conv")]]
            markup = InlineKeyboardMarkup(keyboard)
            async with aiofiles.open("data/info/getting_api.shadow", "rb") as file:
                help_data = add_escape_character(g_ciphers.decrypt(secret_nonce, await file.read(), None).decode("utf-8"))
                msg = await update.message.reply_text(help_data, reply_markup=markup, parse_mode="MarkdownV2")
            content.user_data["ra_message_id"] = msg.message_id
            await content.bot.delete_message(chat_id=update.effective_user.id, message_id=content.user_data.get("tg_message_id"))
            
            content.user_data["guest"] = True
            return "AH"
        else:
            await update.message.reply_text("Wrong Password..\n\nIf you are having problem contact admin. Or mail here: shadow_mist0@proton.me")
            return ConversationHandler.END
    except Exception as e:
        print(f"Error in take_user_password function.\n\nError Code - {e}")
        await update.message.reply_text("Internal Error. Please contact admin or Try Again later.")
        return ConversationHandler.END


#function to handler skip
async def handle_skip(update:Update, content:ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        keyboard = [[InlineKeyboardButton("Cancel", callback_data="cancel_conv")]]
        markup = InlineKeyboardMarkup(keyboard)
        if query.data == "c_skip":
            msg = await query.edit_message_text("You might sometime face problem getting answer. You can always register your api by /api command.\n\nSet Your Password:", reply_markup=markup, parse_mode="Markdown")
            content.user_data["hac_message_id"] = msg.message_id
            content.user_data["user_api"] = None
            return "TP"
    except Exception as e:
        print(f"Error in handle_skip function.\n\nError Code -{e}")
        await query.edit_message_text(f"Internal Error - {e}.\n\n. Please try again later or contact admin.")
        return ConversationHandler.END


#function to take api
async def handle_api_conv(update : Update, content : ContextTypes.DEFAULT_TYPE) -> None:
    try:
        global gemini_api_keys
        user_api = update.message.text.strip()
        await update.message.chat.send_action(action = ChatAction.TYPING)
        keyboard = [[InlineKeyboardButton("Cancel", callback_data="cancel_conv")]]
        markup = InlineKeyboardMarkup(keyboard)
        try:
            client = genai.Client(api_key=user_api)
            response = await client.aio.models.generate_content(
                model = gemini_model_list[1],
                contents = "hi, respond in one word.",
            )
            if(
                user_api.startswith("AIza")
                and user_api not in gemini_api_keys
                and " " not in user_api
                and len(user_api) >= 39
                and response.text
            ):
                await mdb["API"].update_one(
                    {"type" : "api"},
                    {"$push" : {"gemini_api" : user_api}}
                )
                msg = await update.message.reply_text("The API is saved successfully.\nSet you password:", reply_markup=markup)
                gemini_api_keys = await load_gemini_api()
                content.user_data["user_api"] = user_api
                await content.bot.delete_message(chat_id=update.effective_user.id, message_id=content.user_data.get("ra_message_id"))
                
                content.user_data["hac_message_id"] = msg.message_id
                return "TP"
            elif user_api in gemini_api_keys:
                msg = await update.message.reply_text("The API already exists, you are excused.\n Set your password:", reply_markup=markup)
                content.user_data["user_api"] = None
                await content.bot.delete_message(chat_id=update.effective_user.id, message_id=content.user_data.get("ra_message_id"))
                
                content.user_data["hac_message_id"] = msg.message_id
                return "TP"
            else:
                await update.message.reply_text("Sorry, This is an invalid or Duplicate API, try again with a valid API.")
                await content.bot.delete_message(chat_id=update.effective_user.id, message_id=content.user_data.get("ra_message_id"))
                
                return ConversationHandler.END
        except Exception as e:
            await update.message.reply_text(f"Sorry, This doesn't seems like a valid API. Here's the error message:\n<pre>{html.escape(str(e))}</pre>", parse_mode="HTML")
            await content.bot.delete_message(chat_id=update.effective_user.id, message_id=content.user_data.get("ra_message_id"))
            
            return ConversationHandler.END
    except Exception as e:
        print(f"Error in handling api. \n Error Code - {e}")
        await send_to_channel(update, content, channel_id, f"Error in handle_api function \n\nError Code -{e}")



#function to take password from user
async def take_password(update:Update, content:ContextTypes.DEFAULT_TYPE):
    try:
        password = update.message.text.strip()
        keyboard = [[InlineKeyboardButton("Cancel",callback_data="cancel_conv")]]
        markup = InlineKeyboardMarkup(keyboard)
        msg = await update.message.reply_text("Confirm Your password:", reply_markup=markup)
        content.user_data["password"] = password
        content.user_data["tp_message_id"] = msg.message_id
        await content.bot.delete_message(chat_id = update.effective_user.id, message_id=content.user_data.get("hac_message_id"))
        
        return "CP"
    except Exception as e:
        print(f"Error in take_password function.\n\nError Code -{e}")
        await update.message.reply_text(f"Internal Error - {e}.\n\n. Please try again later or contact admin.")
        return ConversationHandler.END


#function to confirm user password
async def confirm_password(update:Update, content:ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        global gemini_api_keys,all_user_info
        is_guest = content.user_data.get("guest")
        keyboard = [
            ["Routine", "Schedule"],
            ["⚙️Settings", "🔗Resources"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False, selective=False, is_persistent=True)
        c_password = update.message.text.strip()
        password = content.user_data.get("password")
        if password == c_password:
            try:
                key = AESGCM.generate_key(bit_length=256)
                key = key.hex()
                nonce = os.urandom(12).hex()
                conn = await aiosqlite.connect("data/info/user_data.db")
                if is_guest:
                    user_info = [
                        user_id,
                        content.user_data.get("user_name"),
                        content.user_data.get("gender"),
                        0,
                        content.user_data.get("password"),
                        content.user_data.get("user_api"),
                        key,
                        nonce
                    ]
                else:
                    user_info = [
                        user_id,
                        content.user_data.get("user_name"),
                        content.user_data.get("gender"),
                        content.user_data.get("roll"),
                        content.user_data.get("password"),
                        content.user_data.get("user_api"),
                        key,
                        nonce
                    ]
                await conn.execute("""
                    INSERT OR IGNORE INTO users(user_id, name, gender, roll, password, api, secret_key, nonce)
                    VALUES(?,?,?,?,?,?,?,?)
                """,
                tuple(info for info in user_info)
                )
                persona = "data/persona/Pikachu.shadow"
                data = {
                    "id" : user_info[0],
                    "name" : user_info[1],
                    "memory" : None,
                    "conversation" : None,
                    "settings" : (user_info[0], user_info[1], "gemini-2.5-flash", 0, 0.7, 0, persona),
                    "user_data" : user_info
                }
                await asyncio.to_thread(
                    db[f"{user_info[0]}"].insert_one,
                    data
                )
                await conn.commit()
                await conn.close()
                conn = await aiosqlite.connect("data/settings/user_settings.db")
                await conn.execute("""
                    INSERT OR IGNORE INTO user_settings
                        (id, name, model, thinking_budget, temperature, streaming, persona)
                        VALUES(?,?,?,?,?,?,?)
                """,
                (user_info[0], user_info[1], "gemini-2.5-flash", 0, 0.7, 0, persona)
                )
                await conn.commit()
                await conn.close()

                global all_users
                global all_settings
                print(len(all_users))

                all_users_local = await load_all_user()
                all_settings_local = await load_all_user_settings()
                all_user_info_local = await load_all_user_info()

                all_users.clear()
                all_user_info.clear()
                all_settings.clear()

                all_users[:] = all_users_local
                print(len(all_users))
                all_settings.update(all_settings_local)
                all_user_info.update(all_user_info_local)

                if not os.path.exists(f"data/Conversation/conversation-{user_id}.shadow"):
                    async with aiofiles.open(f"data/Conversation/conversation-{user_id}.shadow", "wb") as f:
                        pass
                
                if not os.path.exists(f"data/memory/memory-{user_id}.shadow"):
                    async with aiofiles.open(f"data/memory/memory-{user_id}.shadow", "wb") as f:
                        pass
                
                if user_info[3] == 0:
                    await update.message.reply_text("You have been registered as a guest with limited functionality.", reply_markup=reply_markup)
                else:
                    await update.message.reply_text("Registration Seccessful. Now press /start", reply_markup=reply_markup)
                await content.bot.delete_message(chat_id = update.effective_user.id, message_id=content.user_data.get("tp_message_id"))
                
            except Exception as e:
                print(f"Error adding user.\n\nError code - {e}")
            if content.user_data.get("from_totp") == "true":
                del content.user_data["from_totp"]
                keyboard = [
                    [InlineKeyboardButton("Mark Attendance", callback_data="c_mark_attendance")]
                ]
                markup = InlineKeyboardMarkup(keyboard)
                if os.path.exists("data/info/active_attendance.txt"):
                    message = await update.message.reply_text("Redirecting to attendance circular.\n please wait...", reply_markup=markup)
                    user_message_id[f"{update.effective_user.id}"] = message.message_id
                else:
                    await update.message.reply_text("Time limit is over for attendance, please contact admin.")
            return ConversationHandler.END
        else:
            await update.message.reply_text("Passwords are not identical. Try again later.")
            await content.bot.delete_message(chat_id = update.effective_user.id, message_id=content.user_data.get("tp_message_id"))
            return ConversationHandler.END
            
    except Exception as e:
        print(f"Error in confirm_password function.\n\nError Code -{e}")
        await update.message.reply_text(f"Internal Error - {e}.\n\n. Please try again later or contact admin.")
        return ConversationHandler.END
 
    

#function to enter temperature conversation
async def temperature(update:Update, content:ContextTypes.DEFAULT_TYPE):
    try:
        settings = await get_settings(update.effective_user.id)
        keyboard = [
            [InlineKeyboardButton("Cancel", callback_data="cancel_conv")]
        ]
        markup = InlineKeyboardMarkup(keyboard)
        query = update.callback_query
        msg = await query.edit_message_text(f"Configure the creativity(Temperature) of the bots response.\nCurrent Temperature is {settings[4]}\n\nEnter a value between 0.0 to 1.0:", reply_markup=markup)
        content.user_data["t_message_id"] = msg.message_id
        return "TT"
    except Exception as e:
        print(f"Error in temperatre function.\n\nError Code -{e}")
        await query.edit_message_text(f"Internal Error - {e}.\n\n. Please try again later or contact admin.")
        return ConversationHandler.END


#function to take temperature
async def take_temperature(update:Update, content:ContextTypes.DEFAULT_TYPE):
    try:
        data = update.message.text.strip()
        user_id = update.effective_user.id
        try:
            data = round(float(data),1)
        except:
            await update.message.reply_text("Invalid Input. Try Again Later.")
            await content.bot.delete_message(chat_id=user_id, message_id=content.user_data.get("t_message_id"))
            
            return ConversationHandler.END
        if data > 2.0 or data < 0.0:
            await update.message.reply_text("Invalid Input. Temperature should be between 0.0 to 1.0")
            await content.bot.delete_message(chat_id=user_id, message_id=content.user_data.get("t_message_id"))
            
            return ConversationHandler.END
        else:
            conn = await aiosqlite.connect("data/settings/user_settings.db")
            await conn.execute("UPDATE user_settings SET temperature = ? WHERE id = ?", (data, user_id))
            await conn.commit()
            await conn.close()
            await mdb[f"{user_id}"].update_one(
                {"id" : user_id},
                {"$set" : {"settings.4":data}}
            )
            global all_settings
            new_settings = await load_all_user_settings()
            all_settings.clear()
            all_settings.update(new_settings)
            await update.message.reply_text(f"Temperature is successfully set to {data}.")
            await content.bot.delete_message(chat_id=user_id, message_id=content.user_data.get("t_message_id"))
            
            return ConversationHandler.END
    except Exception as e:
        print(f"Error in take_temperature function.\n\nError Code -{e}")
        await update.message.reply_text(f"Internal Error - {e}.\n\n. Please try again later or contact admin.")
        return ConversationHandler.END
        

#function to enter thinking conversation
async def thinking(update:Update, content:ContextTypes.DEFAULT_TYPE):
    try:
        settings = await get_settings(update.effective_user.id)
        keyboard = [
            [InlineKeyboardButton("Cancel", callback_data="cancel_conv")]
        ]
        markup = InlineKeyboardMarkup(keyboard)
        query = update.callback_query
        msg = await query.edit_message_text(f"Thinking represents the thinking budget of the bot measured in token.\nCurrent Thinking budger is {settings[3]}\nAllowed Range - (0 to 24576)\nRecommended Range - (0 to 5000)\n\nEnter a value:", reply_markup=markup)
        content.user_data["t_message_id"] = msg.message_id
        return "TT"
    except Exception as e:
        print(f"Error in thinking function.\n\nError Code -{e}")
        await query.edit_message_text(f"Internal Error - {e}.\n\n. Please try again later or contact admin.")
        return ConversationHandler.END


#function to take temperature
async def take_thinking(update:Update, content:ContextTypes.DEFAULT_TYPE):
    try:
        data = update.message.text.strip()
        user_id = update.effective_user.id
        try:
            data = int(data)
        except:
            await update.message.reply_text("Invalid Input. Try Again Later.")
            await content.bot.delete_message(chat_id=user_id, message_id=content.user_data.get("t_message_id"))
            
            return ConversationHandler.END
        if data > 24576 or data < -1:
            await update.message.reply_text("Invalid Input. Temperature should be between 0 to 24576")
            await content.bot.delete_message(chat_id=user_id, message_id=content.user_data.get("t_message_id"))
            
            return ConversationHandler.END
        else:
            settings = await get_settings(update.effective_user.id)
            conn = await aiosqlite.connect("data/settings/user_settings.db")
            if settings[2] != "gemini-2.5-pro":
                await conn.execute("UPDATE user_settings SET thinking_budget = ? WHERE id = ?", (data, user_id))
                await conn.commit()
                await conn.close()
                await mdb[f"{user_id}"].update_one(
                    {"id" : user_id},
                    {"$set" : {"settings.3":data}}
                )
                await update.message.reply_text(f"Thinking Budget is successfully set to {data}.")
                global all_settings
                new_settings = await load_all_user_settings()
                all_settings.clear()
                all_settings.update(new_settings)
                await content.bot.delete_message(chat_id=user_id, message_id=content.user_data.get("t_message_id"))
                
                return ConversationHandler.END
            else:
                data = data if data>=128 or data==-1 else 1024
                await conn.execute("UPDATE user_settings SET thinking_budget = ? WHERE id = ?", (data, user_id))
                await conn.commit()
                await conn.close()
                await mdb[f"{user_id}"].update_one(
                    {"id" : user_id},
                    {"$set" : {"settings.3":data}}
                )
                await update.message.reply_text(f"Thinking Budget is successfully set to {data}. Gemini 2.5 pro only works with thinking budget greater than 128.")
                await content.bot.delete_message(chat_id=user_id, message_id=content.user_data.get("t_message_id"))
                
                return ConversationHandler.END
    except Exception as e:
        print(f"Error in take_thinking function.\n\nError Code -{e}")
        await update.message.reply_text(f"Internal Error - {e}.\n\n. Please try again later or contact admin.")
        return ConversationHandler.END
    

#funtion to enter manage model conversation
async def manage_model(update:Update, content:ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        keyboard = [[InlineKeyboardButton("Cancel", callback_data="cancel_conv")]]
        markup = InlineKeyboardMarkup(keyboard)
        if query.data == "c_add_model":
            msg = await query.edit_message_text("Enter the model name:", reply_markup=markup)
            content.user_data["action"] = "c_add_model"
        elif query.data == "c_delete_model":
            msg = await query.edit_message_text("Enter the model name to delete:", reply_markup=markup)
            content.user_data["action"] = "c_delete_model"
        content.user_data["mm_message_id"] = msg.message_id
        return "TMN"
    except Exception as e:
        print(f"Error in manage_model function.\n\nError Code -{e}")
        await update.message.reply_text(f"Internal Error - {e}.\n\n. Please try again later or contact admin.")
        return ConversationHandler.END


#function to take model_name
async def take_model_name(update:Update, content:ContextTypes.DEFAULT_TYPE):
    try:
        data = update.message.text.strip()
        action = content.user_data.get("action")
        global gemini_model_list
        if action == "c_add_model":
            if data not in gemini_model_list:
                try:
                    client = genai.Client(api_key=gemini_api_keys[-1])
                    response = await client.aio.models.generate_content(
                    model = data,
                    contents = "hi, respond in one word.",
                    )
                    response.text
                    await mdb["ai_model"].update_one(
                        {"type" : "gemini_model_name"},
                        {"$push" : {"model_name" : data}}
                    )
                    await update.message.reply_text(f"{data} added successfully as a model.")
                except Exception as e:
                    await update.message.reply_text(f"Invalid Model Name.\n\nError Code - {e}")
                gemini_model_list = await load_gemini_model()
            elif data in gemini_model_list:
                await update.message.reply_text("The model name is already registered.")
            else:
                await update.message.reply_text("The model name is invalid.")
        elif action == "c_delete_model":
            if data not in gemini_model_list:
                await update.message.reply_text(f"Sorry there is no model named {data}")
            else:
                await mdb["ai_model"].update_one(
                        {"type" : "gemini_model_name"},
                        {"$pull" : {"model_name" : data}}
                    )
                gemini_model_list = await load_gemini_model()
                await update.message.reply_text(f"The model named {data} is deleted successfully")
        await content.bot.delete_message(chat_id=update.effective_user.id, message_id=content.user_data.get("mm_message_id"))
        
        return ConversationHandler.END
    except Exception as e:
        print(f"Error in take_model_name function.\n\nError Code -{e}")
        await update.message.reply_text(f"Internal Error - {e}.\n\n. Please try again later or contact admin.")
        return ConversationHandler.END


#function to take attendance detail
async def take_attendance_detail(update:Update, content:ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        keybaord = [
            [InlineKeyboardButton("Cancel", callback_data="cancel_conv")]
        ]
        markup = InlineKeyboardMarkup(keybaord)
        msg = await query.edit_message_text("Enter the teacher name:", reply_markup=markup)
        content.user_data["tad_msg_id"] = msg.message_id
        return "TTN"
    except Exception as e:
        print(f"Error in take_attendance function.\n\nError code - {e}")
        return ConversationHandler.END


#function to take teachers name
async def take_teachers_name(update:Update, content:ContextTypes.DEFAULT_TYPE):
    try:
        name = update.message.text.strip()
        if name.isdigit():
            await update.message.reply_text("Operation Failed. \nName should not contain only number.")
            return ConversationHandler.END
        keybaord = [
            [InlineKeyboardButton("Cancel", callback_data="cancel_conv")]
        ]
        markup = InlineKeyboardMarkup(keybaord)
        msg = await update.message.reply_text("Enter the subject name:", reply_markup=markup)
        content.user_data["ttn_msg_id"] = msg.message_id
        content.user_data["teacher"] = name
        return "TSN"
    except Exception as e:
        print(f"Error in take_teachers_name function. Error Code - {e}")
        await update.message.reply_text("Internal Error. Contact admin or try again later.")
        return ConversationHandler.END
    

#function to take subjet name for attendance
async def take_subject_name(update:Update, content:ContextTypes.DEFAULT_TYPE):
    try:
        name = update.message.text.strip()
        if name.isdigit():
            await update.message.reply_text("Operation Failed. \nSubject name should not contain only number.")
            return ConversationHandler.END
        keybaord = [
            [InlineKeyboardButton("Cancel", callback_data="cancel_conv")]
        ]
        markup = InlineKeyboardMarkup(keybaord)
        msg = await update.message.reply_text("Enter the time limit as seconds, Make sure to give only number: ", reply_markup=markup)
        content.user_data["tsn_msg_id"] = msg.message_id
        content.user_data["subject"] = name
        return "TTL"
    except Exception as e:
        print(f"Error in take_subject_name function. Error Code - {e}")
        await update.message.reply_text("Internal Error. Contact admin or try again later.")
        return ConversationHandler.END


#function to take time limit for attendance
async def take_time_limit(update:Update, content:ContextTypes.DEFAULT_TYPE):
    try:
        ikeyboard = [
            [InlineKeyboardButton("Cancel", callback_data="cancel_conv")]
        ]
        limit = update.message.text.strip()
        if not limit.isdigit():
            await update.message.reply_text("Operation Failed. \nTime limit should only contain number.")
            return ConversationHandler.END
        imarkup = InlineKeyboardMarkup(ikeyboard)
        rkeyboard = [
            [KeyboardButton("Give location", request_location=True)]
        ]
        rmarkup = ReplyKeyboardMarkup(rkeyboard, resize_keyboard=True, is_persistent=True, selective=False, one_time_keyboard=True)
        content.user_data["time_limit"] = limit
        msg0 = await update.message.reply_text("Please give location to verify user attendance.", reply_markup=rmarkup)
        msg = await update.message.reply_text("Attendance will be allowed within 200 meter radius.", reply_markup=imarkup)
        content.user_data["ttl_msg0_id"] = msg0.message_id 
        content.user_data["ttl_msg_id"] = msg.message_id
        return "TL"
    except Exception as e:
        print(f"Error in take_time_limit function. Error Code - {e}")
        await update.message.reply_text("Internal Error. Contact admin or try again later.")
        return ConversationHandler.END
    

#function to handle attendace by given location
async def take_location(update:Update, content:ContextTypes.DEFAULT_TYPE):
    try:
        message = update.message or update.edited_message
        keyboard = [
            ["Routine", "Schedule"],
            ["⚙️Settings", "🔗Resources"]
        ]
        markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False, selective=False, is_persistent=True)
        if message.location:
            location = update.message.location
        msg = await message.reply_text("Location Recieved Successfully. Please wait while bot is sending the attendance circular.", reply_markup = markup)

        #extea processing here
        date = datetime.today().strftime("%d-%m-%Y")
        collection = db[f"Attendance-{date}"]
        await content.bot.delete_message(chat_id=update.effective_user.id, message_id=content.user_data.get("tad_msg_id"))
        await content.bot.delete_message(chat_id=update.effective_user.id, message_id=content.user_data.get("ttn_msg_id"))
        await content.bot.delete_message(chat_id=update.effective_user.id, message_id=content.user_data.get("tsn_msg_id"))
        await content.bot.delete_message(chat_id=update.effective_user.id, message_id=content.user_data.get("ttl_msg_id"))
        await content.bot.delete_message(chat_id=update.effective_user.id, message_id=content.user_data.get("ttl_msg0_id"))
        teacher = content.user_data.get("teacher")
        subject = content.user_data.get("subject")
        limit = int(content.user_data.get("time_limit"))
        data = {
            "type" : f"attendance-{date}",
            "teacher" : teacher,
            "subject" : subject,
            "present" : [],
            "absent" : [],
            "distance" : []
        }
        async with aiofiles.open(f"data/info/location-{date}-{subject}.txt", "w") as f:
            await f.write(f"{location.latitude}\n{location.longitude}")
        async with aiofiles.open("data/info/active_attendance.txt", "w") as f:
            await f.write(f"{subject}-{teacher}")
        collection.insert_one(data)
        content.user_data["message_id"] = msg.message_id
        asyncio.create_task(circulate_attendance(update, content, teacher, subject, limit))
        asyncio.create_task(delete_attendace_circular(update, content, limit))
        return ConversationHandler.END
    except Exception as e:
        print(f"Error in take_location function. Error Code - {e}")
        await update.message.reply_text("Internal Error. Contact admin or try again later.")
        return ConversationHandler.END





async def delete_attendace_circular(update:Update, content:ContextTypes.DEFAULT_TYPE, limit):
    try:
        await asyncio.sleep(limit+5)
        for key, value in user_message_id.items():
            try:
                await content.bot.delete_message(chat_id=int(key), message_id=value)
            except Exception as e:
                print(e)
        asyncio.create_task(process_attendance_data(update, content))
    except Exception as e:
        print(f"Error in delete_attendance_circular function.\n\nError Code - {e}")
        return ConversationHandler.END


#function to prepare pdf to send attendance data
async def process_attendance_data(update:Update, content:ContextTypes.DEFAULT_TYPE):
    try:
        message = await update.message.reply_text("Processing data...\nPlease wait...")
        os.makedirs("data/media", exist_ok=True)
        all_rolls = [roll for roll in range(2403121, 2403181)]
        date = datetime.today().strftime("%d-%m-%Y")
        async with aiofiles.open("data/info/active_attendance.txt", "r") as f:
            file_content = await f.read()
            list = file_content.split("-")
        present_students = tuple(db[f"Attendance-{date}"].find_one({"type" : f"attendance-{date}", "teacher" : f"{list[1]}", "subject" : f"{list[0]}"})["present"])
        student_data = db["names"].find_one({"type" : "official_data"})["data"]
        pdf = FPDF()
        pdf.add_page()
        pdf.add_font('Arial', '', 'font/arial.ttf', uni=True)
        pdf.add_font('DejaVu', 'B', 'font/DejaVuB.ttf', uni=True)
        pdf.add_font('DejaVu', 'I', 'font/DejaVuI.ttf', uni=True)
        pdf.set_font("Arial", size=10, style="B")
        pdf.cell(190,5,"ATTENDANCE SHEET",ln=1, align="C")
        pdf.set_font("Arial",size=10,style="B")
        pdf.cell(62, 5, f"Date: {date}", align="L")
        pdf.cell(62, 5, f"Subject: {list[0]}", align="C")
        pdf.cell(62, 5, f"Teacher: {list[1]}",ln=1,align="R")
        pdf.set_font("Arial", size=8)
        pdf.cell(10,4,"SI", border=1)
        pdf.cell(60,4,"Roll", border=1)
        pdf.cell(60,4,"Name", border=1)
        pdf.cell(60,4,"Status", border=1, ln=1)
        for roll in all_rolls:
            if roll in present_students:
                pdf.set_text_color(0,0,0)
                pdf.cell(10,4,f"{roll-2403120}", border=1)
                pdf.cell(60,4,f"{roll}", border=1)
                try:
                    name = student_data[str(roll)][0]
                except:
                    name = "Unknown"
                pdf.cell(60,4,name, border=1)
                pdf.cell(60,4,"Present", border=1, ln=1)
            else:
                pdf.set_text_color(255,0,0)
                pdf.cell(10,4,f"{roll-2403120}", border=1)
                pdf.cell(60,4,f"{roll}", border=1)
                try:
                    name = student_data[str(roll)][0]
                except:
                    name = "Unknown"
                pdf.cell(60,4,name, border=1)
                pdf.cell(60,4,"Absent", border=1, ln=1)
        pdf.set_text_color(0,0,0)
        pdf.set_font("Arial", size=10, style="B")
        pdf.cell(190, 4, ln=1)
        pdf.cell(25, 6, "Present", border=1, align="C")
        pdf.cell(70, 6, f"{len(present_students)}      ({round((len(present_students)/60)*100, 2)}%)",border=1,align="C")
        pdf.cell(25, 6, "Absent", border=1 , align="C")
        pdf.cell(70, 6, f"{60 - len(present_students)}      ({round(((60 - len(present_students))/60)*100, 2)}%)", border=1, align="C")
        pdf.output(f"data/media/attendance-{date}-{list[0]}.pdf")
        async with aiofiles.open(f"data/media/attendance-{date}-{list[0]}.pdf", "rb") as f:
            pdf_file = BytesIO(await f.read())
            pdf_file.name = f"attendance-{date}-{list[0]}.pdf"
        for admin in all_admins:
            try:
                await content.bot.send_document(chat_id=admin, document=pdf_file, caption=f"Attendance sheet of {list[0]} by {list[1]} for {date}")
            except:
                pdf_file.seek(0)
                print(f"Admin-{admin} not found to send document")
            try:
                await content.bot.delete_message(chat_id=update.effective_user.id, message_id=message.message_id)
            except:
                pass
        try:
            if os.path.exists("data/info/active_attendance.txt"):
                os.remove("data/info/active_attendance.txt")
            if os.path.exists(f"data/info/location-{date}-{list[0]}.txt"):
                os.remove(f"data/info/location-{date}-{list[0]}.txt")
            if os.path.exists(f"data/media/attendance-{date}-{list[0]}.pdf"):
                os.remove(f"data/media/attendance-{date}-{list[0]}.pdf")
        except:
            pass
    except Exception as e:
        print(f"Error in process_attendance_data function.\n\nError Code - {e}")
        return ConversationHandler.END


#function to cancel conversation by cancel button
async def cancel_conversation(update: Update, content: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        await update.callback_query.delete_message()
        return ConversationHandler.END
    except Exception as e:
        print(f"Error in cancel_conversation function.\n\nError Code -{e}")
        await update.message.reply_text(f"Internal Error - {e}.\n\n. Please try again later or contact admin.")
        return ConversationHandler.END
    

#function to take location from user to validate the attendance
async def take_user_location(update:Update, content:ContextTypes.DEFAULT_TYPE):
    try:
        location_help = (
            "1. Turn on location service on your device\n"
            "2. Go to the attachment option\n"
            "3. Go to the location option\n"
            "4. Press 'Share My Live Location for...'\n"
            "5. Press share"
        )
        user_id = update.effective_user.id
        if user_id not in all_users:
            keyboard = [
                [InlineKeyboardButton("Register", callback_data="c_register"), InlineKeyboardButton("Cancel", callback_data="cancel")]
            ]
            markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("You are not registerd yet.", reply_markup=markup)
            content.user_data["from_totp"] = "true"
            return ConversationHandler.END
        if update.callback_query:
            query = update.callback_query
            await query.answer()
            await query.edit_message_text(f"Share your location to verify the attendance, Follow the steps below:\n\n{location_help}")
            return "VL"
        else:
            await update.message.reply_text(f"Follow the steps below:\n\n{location_help}")
            return "VL"
    except Exception as e:
        print(f"Error in take_user_location function.\n\nError Code -{e}")
        return ConversationHandler.END


#function to verify user location for attendance
async def verify_user_location(update:Update, content:ContextTypes.DEFAULT_TYPE):
    try:
        date = datetime.today().strftime("%d-%m-%Y")
        async with aiofiles.open("data/info/active_attendance.txt", "r") as f:
            file_content = await f.read()
            list = file_content.split("-")
        try:
            async with aiofiles.open(f"data/info/location-{date}-{list[0]}.txt") as file:
                cr_location_lines = await file.readlines()
                cr_location = tuple(float(loc.strip()) for loc in cr_location_lines)
        except Exception as e:
            print("The location file may not exists")
            return ConversationHandler.END
        message = update.message or update.edited_message
        if not message or not message.location:
            await message.reply_text("Enter your location, not some random message.")
            if os.path.exists(f"data/info/location-{date}-{list[0]}.txt"):
                return "VL"
            else:
                await message.reply_text("Time limit exceeded, Contact CR if you are facing problem.")
                return ConversationHandler.END
        elif not getattr(message.location, 'live_period', None):
            await message.reply_text("Sorry, static location will not work, give a live location.")
            if os.path.exists(f"data/info/location-{date}-{list[0]}.txt"):
                return "VL"
            else:
                await message.reply_text("Time limit exceeded, Contact CR if you are facing problem.")
                return ConversationHandler.END
        if message.location and getattr(message.location, 'live_period', None):
            location = message.location
            message_time = message.date.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            message_age = (now - message_time).total_seconds()
            if message_age > 20:
                await message.reply_text("Sorry, scamming is not allowed. Your location is not fresh. If there is an active live location sharing, stop it and try again.")
                return "VL"
            user_location = (location.latitude, location.longitude)
            user_id = update.effective_user.id
            conn = await aiosqlite.connect("data/info/user_data.db")
            cursor = await conn.execute("SELECT name, roll FROM users WHERE user_id = ?", (user_id,))
            info = await cursor.fetchone()
            user_roll = info[1]
            await conn.close()
            # logic to handle the location difference
            allowed_distance = 200
            distance = geodesic(cr_location, user_location).meters
            if distance >= allowed_distance:
                await message.reply_text(f"You are not allowed to take the attendance as you are {distance:.2f} meters away from CR. If you are facing problem contact admin")
                return ConversationHandler.END
            elif user_roll == 0:
                await message.reply_text(f"Guest members are not allowed to take attendance.")
                return ConversationHandler.END
            else:
                collection = mdb[f"Attendance-{date}"]
                await collection.update_one(
                    {"type" : f"attendance-{date}", "teacher" : f"{list[1]}", "subject" : f"{list[0]}"},
                    {"$push" : {"present" : user_roll}}
                )
                await collection.update_one(
                    {"type" : f"attendance-{date}", "teacher" : f"{list[1]}", "subject" : f"{list[0]}"},
                    {"$push" : {"distance" : {f"{user_roll}" : distance}}}
                )
                await message.reply_text(f"Name: {info[0]}\nRoll: {info[1]}\nYour attendance submitted successfully.\n\nIf you are seeing wrong information here please contact admin.")
                return ConversationHandler.END
        else:
            return ConversationHandler.END
    except Exception as e:
        print(f"Error in verify_user_location function.\n\nError Code - {e}")
        return ConversationHandler.END




verify_attendance_conv = ConversationHandler(
    entry_points = [CallbackQueryHandler(take_user_location, pattern="^c_mark_attendance$")],
    states = {
        "VL" : [
            MessageHandler(filters.LOCATION, verify_user_location),
            MessageHandler(filters.TEXT & ~ filters.COMMAND, verify_user_location)
        ]
    },
    fallbacks=[CallbackQueryHandler(cancel_conversation, pattern="^cancel_conv$")]
)

#conversation to handle taking attendance for cse sec c
take_attendance_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(take_attendance_detail, pattern="^c_take_attendance$")],
    states = {
        "TTN" : [MessageHandler(filters.TEXT & ~filters.COMMAND, take_teachers_name)],
        "TSN" : [MessageHandler(filters.TEXT & ~filters.COMMAND, take_subject_name)],
        "TTL" : [MessageHandler(filters.TEXT & ~filters.COMMAND, take_time_limit)],
        "TL" : [
            MessageHandler(filters.LOCATION, take_location),
            CallbackQueryHandler(take_location, pattern="^c_location_skip$")
        ]
    },
    fallbacks=[CallbackQueryHandler(cancel_conversation, pattern="^cancel_conv$")]
)

#conversation handler for managing model
manage_ai_model_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(manage_model, pattern="^(c_add_model|c_delete_model)$")],
    states = {
        "TMN" : [MessageHandler(filters.TEXT & ~filters.COMMAND, take_model_name)]
    },
    fallbacks=[CallbackQueryHandler(cancel_conversation, pattern="^cancel_conv$")]
)

#conversation handler for taking thinking token
thinking_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(thinking, pattern="^c_thinking$")],
    states={
        "TT" : [MessageHandler(filters.TEXT & ~filters.COMMAND, take_thinking)]
    },
    fallbacks=[CallbackQueryHandler(cancel_conversation, pattern="^cancel_conv$")]
)

#conversation handler for taking temperature
temperature_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(temperature, pattern="^c_temperature$")],
    states={
        "TT" : [MessageHandler(filters.TEXT & ~filters.COMMAND, take_temperature)]
    },
    fallbacks=[CallbackQueryHandler(cancel_conversation, pattern="^cancel_conv$")]
)

#conversation handler for registering new user
register_conv = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(take_name, pattern="c_register")
    ],
    states = {
        "TG" : [MessageHandler(filters.TEXT & ~filters.COMMAND, take_gender)],
        "TR" : [CallbackQueryHandler(take_roll, pattern="^(c_male|c_female)$")],
        "TUP" : [MessageHandler(filters.TEXT & ~filters.COMMAND, take_user_password)],
        "RA" : [MessageHandler(filters.TEXT & ~filters.COMMAND, roll_action)],
        "AH" : [
                CallbackQueryHandler(handle_skip, pattern="^c_skip$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_api_conv)
        ],
        "TP" : [MessageHandler(filters.TEXT & ~filters.COMMAND, take_password)],
        "CP" : [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_password)],
        
    },
    fallbacks=[CallbackQueryHandler(cancel_conversation, pattern="^cancel_conv$")],
    per_chat=True,
    per_user=True
)

#conversation handler for managing admin commad
manage_admin_conv = ConversationHandler(
    entry_points = [CallbackQueryHandler(admin_password_taker, pattern="^c_manage_admin$")],
    states = {
        "MA" : [MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            manage_admin,
        )],
        "ADMIN_ACTION" : [CallbackQueryHandler(admin_action, pattern="^(add_admin|delete_admin|see_all_admin)$")],
        "ENTER_USER_ID" : [MessageHandler(filters.TEXT & ~filters.COMMAND, add_or_delete_admin)]
    },
    fallbacks=[CallbackQueryHandler(cancel_conversation, pattern="^cancel_conv$")],
    per_chat=True,
    per_user=True
)

#conversation handler for circulate message
circulate_message_conv = ConversationHandler(
    entry_points = [CallbackQueryHandler(message_taker, pattern="^(c_notice|c_normal_message)$")],
    states = {
        "CM" : [MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_circulate_message,
        )],
    },
    fallbacks=[CallbackQueryHandler(cancel_conversation, pattern="^cancel_conv$")],
    per_chat=True,
    per_user=True
)

#conversation handler for adding a new api
api_conv_handler = ConversationHandler(
    entry_points = [CommandHandler("api", api)],
    states = {
        1 : [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_api)]
    },
    fallbacks = [CallbackQueryHandler(cancel_conversation, pattern="^cancel_conv$")],
)

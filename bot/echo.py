from telegram import(
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import ContextTypes
from utils.utils import(
    is_ddos,
    send_to_channel
)
from telegram.constants import ChatAction
from bot.info_handler import(
    routine_handler,
    handle_ct,
    resources_handler,
    handle_settings
)
from utils.db import all_users
from utils.config import channel_id
from utils.message_utils import queue
from telegram.error import TimedOut
import time
from utils.config import mdb








#function for all other messager that are directly send to bot without any command
async def echo(update : Update, content : ContextTypes.DEFAULT_TYPE) -> None:
    for retry in range(5):
        try:
            bot_name_obj = await content.bot.get_my_name()
            bot_name = bot_name_obj.name.lower()
            user_id = update.effective_user.id
            ddos = await is_ddos(update, content, update.effective_user.id)
            message = update.message or update.edited_message
            if user_id not in all_users and message.chat.type == "private":
                keyboard = [
                    [InlineKeyboardButton("Register", callback_data="c_register"), InlineKeyboardButton("Cancel", callback_data="cancel")]
                ]
                markup = InlineKeyboardMarkup(keyboard)
                await message.reply_text("You are not registered.", reply_markup=markup)
                return
            user_message = (message.text or "...").strip()
            try:
                if (update.message and message.chat.type == "private") or (message.chat.type != "private" and (f"@{bot_name}" in user_message.lower() or f"{bot_name}" in user_message.lower() or "mama" in user_message.lower() or "@" in user_message.lower() or "bot" in user_message.lower() or "pika" in user_message.lower())):
                    if not update.edited_message and not ddos:
                        await message.chat.send_action(action = ChatAction.TYPING)
            except:
                pass
            if user_message == "Routine":
                await routine_handler(update, content)
                await mdb[f"{user_id}"].update_one(
                    {"id" : user_id},
                    {"$push" : {"statistics" : {"routine" : time.time()}}}
                )
                return
            elif user_message == "⚙️Settings" and message.chat.type == "private":
                await handle_settings(update, content)
                await mdb[f"{user_id}"].update_one(
                    {"id" : user_id},
                    {"$push" : {"statistics" : {"settings" : time.time()}}}
                )
                return
            elif user_message == "Schedule":
                await handle_ct(update, content)
                await mdb[f"{user_id}"].update_one(
                    {"id" : user_id},
                    {"$push" : {"statistics" : {"schedule" : time.time()}}}
                )
                return
            elif user_message == "🔗Resources" and message.chat.type == "private":
                await resources_handler(update, content)
                await mdb[f"{user_id}"].update_one(
                    {"id" : user_id},
                    {"$push" : {"statistics" : {"resource" : time.time()}}}
                )
                return
            else:
                if ddos:
                    return
                #await user_message_handler(update, content, bot_name)
                await queue.put((update, content, bot_name))
                await mdb[f"{user_id}"].update_one(
                    {"id" : user_id},
                    {"$push" : {"statistics" : {"message" : time.time()}}}
                )
                return
        except TimedOut:
            print(f"Timeout error. Trying for the {retry+1} times")
        except Exception as e:
            print(f"Error in echo function.\n\n Error Code - {e}")
            await send_to_channel(update, content, channel_id, f"Error in echo function \n\nError Code -{e}")
            break


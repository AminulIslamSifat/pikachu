from ast import parse
from datetime import(
    datetime,
    timedelta
)
from telegram import(
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import ContextTypes
from utils.utils import send_to_channel
from utils.config import(
    channel_id,
    FIREBASE_URL,
    db
)
import httpx
from telegram.constants import ChatAction
import aiofiles









#function to identify it is lab for 1st 30 or 2nd 30
async def lab_participant():
    async with aiofiles.open("data/routine/lab_routine.txt", "r", encoding="utf-8") as f:
        data = await f.read()
    lab = [0, '0']
    start_date = datetime.strptime("3-7-2025", "%d-%m-%Y")
    today = datetime.now()
    if (today.weekday()) in [3,4]:
        days = (5-today.weekday())%7
        saturday = today + timedelta(days)
        lab[1] = saturday.strftime("%d-%m-%Y")
    else:
        days = (today.weekday() - 5)%7
        saturday = today - timedelta(days)
        lab[1] = saturday.strftime("%d-%m-%Y")
    if int((today-start_date).days / 7) % 2 == 0:
        lab[0] = 1 if data == "first" else 0
    else:
        lab[0] = 0 if data == "first" else 1
    return lab






#all function for cse sec c


async def routine_handler(update : Update, content : ContextTypes.DEFAULT_TYPE) -> None:
    try:
        lab = await lab_participant()
        if lab[0]:
            rt = "data/routine/rt1.png"
        else:
            rt = "data/routine/rt2.png"
        keyboard = [
            [InlineKeyboardButton("Live Routine", url="https://routine-c.vercel.app")]
        ]
        routine_markup = InlineKeyboardMarkup(keyboard)
        async with aiofiles.open(rt, "rb") as photo:
            photo = await photo.read()
            await content.bot.send_photo(update.effective_chat.id, photo, caption = f"This routine is applicable from {lab[1]}.", reply_markup=routine_markup)
    except Exception as e:
        print(f"Error in routine_handler function.\n\n Error Code -{e}")
        await send_to_channel(update, content, channel_id, f"Error in routine_handler function.\n\n Error Code -{e}")

    
#function to fetch ct data from firebase url
async def get_ct_data():
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(FIREBASE_URL)
            response.raise_for_status()
            return response.json() or {}
    except Exception as e:
        print(f"Error in get_ct_data functio. \n\n Error Code -{e}")
        return None



#function to handle ct command
async def handle_ct(update:Update, content:ContextTypes.DEFAULT_TYPE) -> None:
    try:
        c_keyboard = [
            [InlineKeyboardButton("Cover Page", url="https://coverpage-c.vercel.app/")]
        ]
        c_markup = InlineKeyboardMarkup(c_keyboard)

        e_keyboard = [
            [InlineKeyboardButton("Syllabus", callback_data="syllabus")]
        ]
        e_markup = InlineKeyboardMarkup(e_keyboard)

        ct_data = await get_ct_data()
        if ct_data == None:
            await update.message.reply_text("Couldn't Connect to FIREBASE URL. Try again later.")
            return
        elif not ct_data:
            await update.message.reply_text("📭 No CTs scheduled yet.")
            return
        else:
            now = datetime.now()
            upcoming = []

            for ct_id, ct in ct_data.items():
                try:
                    ct_date = datetime.strptime(ct['date'], "%Y-%m-%d")
                    if ct_date >= now:
                        days_left = (ct_date - now).days
                        upcoming.append({
                            'subject': ct.get('subject', 'No Subject'),
                            'date': ct_date,
                            'days_left': days_left,
                            'teacher': ct.get('teacher', 'Not specified'),
                            'syllabus': ct.get('syllabus', 'No syllabus'),
                            'type': ct.get('type','CT')
                        })
                except (KeyError, ValueError) as e:
                    print(f"Skipping malformed CT {ct_id}: {e}")

            if not upcoming:
                await update.message.reply_text("🎉 No upcoming CTs! You're all caught up!")
                return

            # Sort by nearest date
            upcoming.sort(key=lambda x: x['date'])

            # Format message
            
            message = ["📅 <b> Current Schedule </b>"]
            c_message = []
            e_message = []

            for i, ct in enumerate(upcoming):
                days_text = f"{ct['days_left']+1} days"
                date_str = ct['date'].strftime("%a, %d %b")

                cover_type = ["Assignment", "Lab Report", "Presentation", "Semester Final Exam"]

                if ct["type"] not in cover_type:
                    if i == 0:
                        message.append(f"\n⏰ <b>NEXT:</b>\n<b> {ct['subject']}</b>")
                    else:
                        message.append(f"\n📅 <b>{ct['subject']}</b>")
                    
                    
                    message.append(
                        f"❓ <u>{ct['type']}</u>\n"
                        f"🗓️ {date_str} ({days_text})\n"
                        f"👨‍🏫 {ct['teacher']}\n"
                        f"📖 {ct['syllabus']}"
                    )
                elif ct["type"] == "Semester Final Exam":
                    if i == 0:
                        e_message.append(f"\n⏰ <b>NEXT:</b>\n<b> {ct['subject']}</b>")
                    else:
                        e_message.append(f"\n📅 <b>{ct['subject']}</b>")

                    e_message.append(
                        f"❓ <u>{ct['type']}</u>\n"
                        f"🗓️ {date_str} ({days_text})\n"
                        f"👨‍🏫 {ct['teacher']}\n"
                    )

                else:
                    if i == 0:
                        c_message.append(f"\n⏰ <b>NEXT:</b>\n<b> {ct['subject']}</b>")
                    else:
                        c_message.append(f"\n📅 <b>{ct['subject']}</b>")
                    
                    c_message.append(
                        f"❓ <u>{ct['type']}</u>\n"
                        f"🗓️ {date_str} ({days_text})\n"
                        f"👨‍🏫 {ct['teacher']}\n"
                        f"📖 {ct['syllabus']}"
                    )
            
            await update.message.reply_text("\n".join(message), parse_mode='HTML')
            if c_message:
                await update.message.reply_text("\n".join(c_message), parse_mode="HTML", reply_markup=c_markup)
            if e_message:
                await update.message.reply_text("\n".join(e_message), parse_mode="HTML", reply_markup=e_markup)
    except Exception as e:
        print(f"Error in handle_ct function. \n\nError Code - {e}")
        await update.message.reply_text(f"Internal Error\n {e}. \nPlease contact admin or try again later.")




async def information_handler(update:Update, content:ContextTypes.DEFAULT_TYPE, info_name):
    try:
        if info_name == "drive":
            keyboard = [[InlineKeyboardButton("Drive", url="https://drive.google.com/drive/folders/1xbyCdj3XQ9AsCCF8ImI13HCo25JEhgUJ")]]
            markup = InlineKeyboardMarkup(keyboard)
            return markup
        elif info_name == "cover_page":
            keyboard = [[InlineKeyboardButton("Lab Cover Page", url="https://ruet-cover-page.github.io/")]]
            markup = InlineKeyboardMarkup(keyboard)
            return markup
        elif info_name == "website":
            keyboard = [[InlineKeyboardButton("All Websites", callback_data="c_all_websites")]]
            markup = InlineKeyboardMarkup(keyboard)
            return markup
        elif info_name == "g_class_code":
            return "CSE Google classroom code: ```2o2ea2k3```\n\nMath G. Classroom code: ```aq4vazqi```\n\nChemistry G. Classroom code: ```wnlwjtbg```"
        elif info_name == "orientation_file":
            keyboard = [[InlineKeyboardButton("Orientation Files", url = "https://drive.google.com/drive/folders/10_-xTV-FsXnndtDiw_StqH2Zy9tQcWq0")]]
            markup = InlineKeyboardMarkup(keyboard)
            return markup
        else:
            return "Sorry i don't have your requested data."
    except Exception as e:
        print(f"Error in information_handler function.\n\nError Code - {e}")
        await update.message.reply_text("Internal Error. Contact admin or try again later.")



#a function to handle resources of cse 24
async def resources_handler(update:Update, content:ContextTypes.DEFAULT_TYPE):
    try:
        keyboard = [
            [InlineKeyboardButton("Drive", url="https://drive.google.com/drive/folders/1xbyCdj3XQ9AsCCF8ImI13HCo25JEhgUJ"), InlineKeyboardButton("Syllabus", url="https://drive.google.com/file/d/1pVF40-E0Oe8QI-EZp9S7udjnc0_Kquav/view?usp=drive_link")],
            [InlineKeyboardButton("Cover Page Website", url = "https://coverpage-c.vercel.app/")],
            [InlineKeyboardButton("Cover Page Github", url="https://ruet-cover-page.github.io/")],
            [InlineKeyboardButton("G. Classroom Code", callback_data="g_classroom"), InlineKeyboardButton("All Websites", callback_data="c_all_websites")],
            [InlineKeyboardButton("Cancel", callback_data="cancel")]
        ]
        resource_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("All the resources available for CSE SECTION C", reply_markup=resource_markup, parse_mode="Markdown")
    except Exception as e:
        print(f"Error in resource_handler function.\n\nError Code - {e}")
        await update.message.reply_text("Internal Error. Please contact admin or try again later.")


 

#a function to handle settings
async def handle_settings(update : Update, content : ContextTypes.DEFAULT_TYPE) -> None:
    try:
        await update.message.chat.send_action(action=ChatAction.TYPING)
        keyboard= [
            [InlineKeyboardButton("🤖AI Engine", callback_data = "c_model"),InlineKeyboardButton("🧠Creativity", callback_data="c_temperature")],
            [InlineKeyboardButton("🤔Thinking", callback_data = "c_thinking"), InlineKeyboardButton("🎭Persona", callback_data="c_persona")],
            [InlineKeyboardButton("📒Conversation History", callback_data="c_conv_history"), InlineKeyboardButton("📜Memory", callback_data="c_memory")],
            [InlineKeyboardButton("cancel", callback_data="cancel")]
        ]
        settings_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("You can change the bot configuration from here.\nBot Configuration Menu:", reply_markup=settings_markup)
    except Exception as e:
        await send_to_channel(update, content, channel_id, f"Error in handle_settings function \n\nError Code -{e}")
        print(f"Error in handle_settings function. \n\n Error Code -{e}")

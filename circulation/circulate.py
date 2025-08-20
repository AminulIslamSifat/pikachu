from datetime import (
    datetime,
    timedelta
)
from telegram import(
    Update,
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from telegram.ext import (
    ContextTypes,
    ConversationHandler
) 
import requests
from utils.config import (
    db,
    FIREBASE_URL
)
import asyncio
from utils.utils import add_escape_character
from utils.db import all_users
import httpx
import aiofiles
import os






#function to identify it is lab for 1st 30 or 2nd 30
def lab_participant():
    with open("data/routine/lab_routine.txt", "r", encoding="utf-8") as f:
        data = f.read()
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




#function to inform all the student 
async def inform_all(query, content:ContextTypes.DEFAULT_TYPE) -> None:
    try:
        keyboard = [
            ["Routine", "Schedule"],
            ["⚙️Settings", "🔗Resources"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False, selective=False, is_persistent=True)
        await query.edit_message_text("please wait while the bot is sending the message to all user.")
        ct_data = await get_ct_data()
        if ct_data == None:
            await query.message.reply_text("Couldn't Connect to FIREBASE URL. Try again later.")
            return
        elif not ct_data:
            await query.message.reply_text("📭 No CTs scheduled yet.")
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
                            'type' : ct.get('type', 'CT')
                        })
                except (KeyError, ValueError) as e:
                    print(f"Skipping malformed CT {ct_id}: {e}")

            if not upcoming:
                await query.message.reply_text("🎉 No upcoming CTs! You're all caught up!")
                return

            # Sort by nearest date
            upcoming.sort(key=lambda x: x['date'])

            # Format message
            message = ["📚 <b>Upcoming CTs</b>"]
            for i, ct in enumerate(upcoming):
                days_text = f"{ct['days_left']+1} days"
                date_str = ct['date'].strftime("%a, %d %b")

                if i == 0:
                    message.append(f"\n⏰ <b>NEXT:</b> {ct['subject']}")
                else:
                    message.append(f"\n📅 {ct['subject']}")

                message.append(
                    f"❓ <u>{ct['type']}</u>\n"
                    f"🗓️ {date_str} ({days_text})\n"
                    f"👨‍🏫 {ct['teacher']}\n"
                    f"📖 {ct['syllabus']}"
                )
        try:
            failed = 0
            failed_list = "Failed to send message to those user:\n"
            tasks = []

            async def send_ct_routine(user):
                nonlocal failed, failed_list
                try:
                    await content.bot.send_message(
                        chat_id=user,
                        text="\n".join(message),
                        parse_mode="HTML",
                        reply_markup=reply_markup
                    )
                    return True
                except:
                    failed += 1
                    failed_list += str(user) + "\n"
                    return False

            for user in all_users:
                tasks.append(send_ct_routine(user))
            result = await asyncio.gather(*tasks)
            sent = sum(result)
            report = (
                    f"📊 Notification sent to {sent} users\n"
                    f"⚠️ Failed to send to {failed} users\n"
                )
            await query.edit_message_text(report)
            if failed != 0:
                await query.message.reply_text(failed_list, parse_mode="Markdown")
        except Exception as e:
            print(f"Error in inform_all function.\n\n Error Code - {e}")
    except Exception as e:
        print(f"Error in inform_all function. Error Code - {e}")


#fuction to circulate message
async def circulate_message(update : Update, content : ContextTypes.DEFAULT_TYPE):
    try:
        keyboard = [
            ["Routine", "Schedule"],
            ["⚙️Settings", "🔗Resources"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False, selective=False, is_persistent=True)
 
        message_type = content.user_data.get("circulate_message_query")
        message = update.message.text.strip()
        msg = await update.message.reply_text("Please wait while bot is circulating the message.")
        failed = 0
        tasks = []
        failed_list = "Failed to send message to those user:\n"
        if message_type=="c_notice":
            notice = f"```NOTICE\n\n{message}\n```"
        else:
            notice = message
        async def send_notice(user):
            nonlocal failed, failed_list
            try:
                if message_type == "c_notice":
                    try:
                        await content.bot.send_message(
                            chat_id=user,
                            text=notice,
                            parse_mode="Markdown",
                            reply_markup=reply_markup
                        )
                        return True
                    except:
                        try:
                            await content.bot.send_message(
                                chat_id=user,
                                text=add_escape_character(notice),
                                parse_mode="MarkdownV2",
                                reply_markup=reply_markup
                            )
                            return True
                        except:
                            try:
                                await content.bot.send_message(
                                    chat_id=user,
                                    text=notice,
                                    reply_markup=reply_markup
                                )
                                return True
                            except Exception as e:
                                print(e)
                                failed += 1
                                failed_list += f"{user}\n"
                                return False
                else:
                    await content.bot.send_message(
                    chat_id=user,
                    text=notice,
                    parse_mode="HTML",
                    reply_markup=reply_markup
                )
                return True
            except:
                try:
                    await content.bot.send_message(
                        chat_id=user,
                        text=add_escape_character(notice),
                        parse_mode="MarkdownV2",
                        reply_markup=reply_markup
                    )
                    return True
                except:
                    try:
                        await content.bot.send_message(
                            chat_id=user,
                            text= f"NOTICE\n\n{message}" if message_type=="c_notice" else message,
                            reply_markup=reply_markup
                        )
                        return True 

                    except Exception as e:
                        failed += 1
                        failed_list += str(user) + "\n"
                        print(e)
                        return False

        for user in all_users:
            tasks.append(send_notice(user))
        result = await asyncio.gather(*tasks)
        sent = sum(result)

        report = (
                f"📊 Notification sent to {sent} users\n"
                f"⚠️ Failed to send to {failed} users\n"
            )
        await msg.edit_text(report)
        if failed != 0:
            await update.message.reply_text(failed_list, parse_mode="Markdown")
    except Exception as e:
        print(f"Error in circulate_message function.\n\n Error Code - {e}")


#function to circulate routine among all users
async def circulate_routine(query, content:ContextTypes.DEFAULT_TYPE) -> None:
    try:
        lab = lab_participant()
        if lab[0]:
            rt = "data/routine/rt1.png"
        else:
            rt = "data/routine/rt2.png"
        failed = 0
        tasks = []
        failed_list = "Failed to send routine to those user:\n"

        if os.path.exists(rt):
            async with aiofiles.open(rt, "rb") as photo:
                photo = await photo.read()

        async def send_ct_routine(user):
                nonlocal failed, failed_list
                try:
                    await content.bot.send_photo(chat_id=user, photo=photo, caption="Renewed Routine")
                    return True
                except:
                    failed += 1
                    failed_list += str(user) + "\n"
                    return False

        for user in all_users:
            tasks.append(send_ct_routine(user))
        result = await asyncio.gather(*tasks)
        sent = sum(result)
        report = (
                f"📊 Notification sent to {sent} users\n"
                f"⚠️ Failed to send to {failed} users\n"
            )
        await query.message.reply_text(report, parse_mode="HTML")
        if failed != 0:
            await query.message.reply_text(failed_list, parse_mode="Markdown")
    except Exception as e:
        print(f"Error in circulate message function.\n\nError Code - {e}")



user_message_id = {}



#function to circulate attendance to all 60 user
async def circulate_attendance(update:Update, content:ContextTypes.DEFAULT_TYPE, teacher, subject, limit):
    try:
        rkeyboard = [
            ["Routine", "Schedule"],
            ["⚙️Settings", "🔗Resources"]
        ]
        rmarkup = ReplyKeyboardMarkup(rkeyboard, resize_keyboard=True, one_time_keyboard=False, selective=False, is_persistent=True)
        await content.bot.delete_message(chat_id=update.effective_user.id, message_id=content.user_data.get("message_id"))
        await update.message.reply_text("The attendace circular has been circulated successfully. Please wait the time limit to end..", reply_markup=rmarkup)
        failed = 0
        tasks = []
        user_id = update.effective_user.id
        failed_list = "FAILED TO SEND ATTENDANCE TO THOSE USER:\n"
        keyboard = [
            [InlineKeyboardButton("Mark Attendance", callback_data="c_mark_attendance")]
        ]
        markup = InlineKeyboardMarkup(keyboard)
        data = (
            "📢 *IMPORTANT NOTICE*\n"
            f"📋 *Attendance*:\n"
            f"👨‍🏫 Teacher: {teacher}\n"
            f"📚 Subject: {subject}\n"
            f"⏳ Please mark your attendance in {limit} seconds!"
        )
        async def send_attendance(student):
            nonlocal failed, failed_list
            try:
                if int(student) != user_id:
                    msg = await content.bot.send_message(chat_id=student, text=data, reply_markup=markup, parse_mode="Markdown")
                    user_message_id[f"{student}"] = msg.message_id
                    return True
                else:
                    return True
            except Exception as e:
                print(e)
                failed += 1
                failed_list += f"{student}\n"
                return False
            
        for student in all_users:
            tasks.append(send_attendance(student))
            
        results = await asyncio.gather(*tasks)
        sent = sum(results)
        report = (
                f"📋 Attendance Circular sent to {sent} users\n"
                f"⚠️ Failed to send to {failed} users\n"
            )
        await update.message.reply_text(report, reply_markup=rmarkup)
        if failed != 0:
            await update.message.reply_text(failed_list)
            msg = await update.message.reply_text(data, reply_markup=markup, parse_mode="Markdown")
            user_message_id[f"{user_id}"] = msg.message_id
        else:
            msg = await update.message.reply_text(data, reply_markup=markup, parse_mode="Markdown")
            user_message_id[f"{user_id}"] = msg.message_id
    except Exception as e:
        print(f"Error in circulate_attendance function. Error Code - {e}")
        await update.message.reply_text("Internal Error. Contact admin or try again later.")
        return ConversationHandler.END

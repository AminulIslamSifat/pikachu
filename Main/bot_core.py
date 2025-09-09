import os
import sys
import io
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import asyncio
import warnings
import uvicorn
from telegram.request import HTTPXRequest
from telegram._utils.warnings import PTBUserWarning
from telegram import Update
from telegram.ext import(
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler,
)
from routes.web_panel_fastapi import app as web_app
import utils.db as db_utils
from utils.file_utils import load_all_files
from utils.message_utils import run_workers, queue as message_queue
from bot.command_handler import(
    restart,
    start,
    help,
    admin_handler
)
from bot.media_handler import(
    handle_media,
    handle_location,
    run_media_workers,
    media_queue
)
from utils.config import(
    WEBHOOK_URL
)



#code to ignore warning about per_message in conv handler and increase poll size
warnings.filterwarnings("ignore",category=PTBUserWarning)
warnings.filterwarnings("ignore", message="There are non-text parts in the response")



#importing all conversation handlers
from conv.conv_tool import(
    api_conv_handler,
    register_conv,
    thinking_conv,
    temperature_conv,
    take_attendance_conv,
    manage_ai_model_conv,
    manage_admin_conv,
    circulate_message_conv,
    verify_attendance_conv
)
from bot.callback import button_handler
from bot.echo import echo
from fastapi import Request, Response






#setting this to alter defult connection pool size and timeout for telegram
tg_request = HTTPXRequest(connection_pool_size=50, pool_timeout=30, read_timeout=60.0, write_timeout=60.0)








#The main function consisting all core functionality for this bot
#This is the starting point of the bot
async def main():
    try:
        await db_utils.initialize_bot()                     #initializing the database
        await load_all_files()                              #loading all the files
        await db_utils.populate_db_caches()                 #Loading all data into ram

        TOKENs = await db_utils.get_token()                   #getting the bot token
        TOKEN = TOKENs[1]

        #Initializing the main telegram bot application
        bot_app = ApplicationBuilder().token(TOKEN).request(tg_request).concurrent_updates(True).build()

        # Add webhook handler to the FastAPI app
        @web_app.post(f"/{db_utils.TOKEN}")
        async def telegram_webhook(request: Request):
            """Handle incoming telegram updates"""
            update_data = await request.json()
            update = Update.de_json(update_data, bot_app.bot)
            await bot_app.process_update(update)
            return Response(status_code=200)
        

        # Register conversation handlers
        bot_app.add_handler(register_conv)
        bot_app.add_handler(api_conv_handler)
        bot_app.add_handler(thinking_conv)
        bot_app.add_handler(temperature_conv)
        bot_app.add_handler(manage_admin_conv)
        bot_app.add_handler(take_attendance_conv)
        bot_app.add_handler(manage_ai_model_conv)
        bot_app.add_handler(circulate_message_conv)
        bot_app.add_handler(verify_attendance_conv)

        # Register Handlers
        bot_app.add_handler(CommandHandler("help", help))
        bot_app.add_handler(CommandHandler("start",start))
        bot_app.add_handler(CommandHandler("restart",restart))
        bot_app.add_handler(CallbackQueryHandler(button_handler))
        bot_app.add_handler(CommandHandler("admin", admin_handler))
        bot_app.add_handler(MessageHandler(filters.LOCATION, handle_location))
        bot_app.add_handler(MessageHandler(
            (filters.PHOTO |
            filters.Document.ALL | 
            filters.AUDIO |
            filters.VOICE |
            filters.VIDEO |
            filters.Sticker.ALL) &
            ~filters.ChatType.CHANNEL, handle_media
        ))
        bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.ChatType.CHANNEL, echo))
        
        # Setup Uvicorn server to run our FastAPI app
        config = uvicorn.Config(web_app, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)), log_level="info")
        server = uvicorn.Server(config)


        #Configuring and running workers to process multiple users request simulataneously
        workers = await run_workers(12)
        media_workers = await run_media_workers(6)
        


        # --- WEBHOOK MODE (Currently Active) ---
        # This runs the bot with webhooks.
        async with bot_app:
            await bot_app.start()
            # Set webhook
            await bot_app.bot.set_webhook(
                url=f"{WEBHOOK_URL}/{db_utils.TOKEN}",
                allowed_updates=Update.ALL_TYPES
            )


            # Run the web server
            await server.serve()
            

            # On shutdown, stop the bot and delete the webhook
            #This function waits for all the workers to finish
            for _ in workers:
                await message_queue.put(None)
            for _ in media_workers:
                await media_queue.put(None)
            await asyncio.gather(*workers, *media_workers)


            # Stop the bot by deleteing webhook
            await bot_app.bot.delete_webhook()
            await bot_app.stop()

        # --- POLLING MODE (Currently Inactive) ---

        # await bot_app.initialize()
        # await bot_app.start()
        # # This will run the bot and the web server concurrently
        # await asyncio.gather(
        #     bot_app.updater.start_polling(allowed_updates=Update.ALL_TYPES),
        #     server.serve()
        # )

    except Exception as e:
        print(f"Error in main function. Error Code - {e}")


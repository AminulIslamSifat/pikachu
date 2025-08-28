from fileinput import filename
from google import genai
from google.genai import types
from utils.utils import load_persona
from telegram import Update
from telegram.ext import ContextTypes
import asyncio
from PIL import Image
from io import BytesIO
import os, time
from fpdf import FPDF
import random
from bot.info_handler import get_ct_data, routine_handler, information_handler
from utils.func_description import(
    func_list
)
import json
from ext.user_content_tools import(
    save_conversation,
    save_group_conversation
)
from utils.utils import(
    is_ddos,
    send_to_channel,
    safe_send,
    is_code_block_open
)
from utils.config import(
    channel_id,
    db,
    g_ciphers,
    secret_nonce
)
from utils.db import(
    gemini_api_keys,
    all_user_info
)
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from ext.user_content_tools import reset
from types import SimpleNamespace
import aiosqlite
import aiofiles






#a function to convert hex to rgb
def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) for i in (0,2,4))



#function for editing and sending message
async def send_message(update : Update, content : ContextTypes.DEFAULT_TYPE, response, user_message, msg_obj) -> None:    
    try:
        count = 0
        message = update.message or update.edited_message
        if not response:
            await message.reply_text("Failed to precess your request. Try again later.")
            return
        if await is_ddos(update, content, update.effective_user.id):
            return
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
            await safe_send(update,content, message_to_send, msg_obj)
            count += 1
        if message.chat.type == "private":
            await save_conversation(user_message, message_to_send, update.effective_user.id)
        elif message.chat.type != "private":
            await save_group_conversation(update, user_message, message_to_send)
    except Exception as e:
        print(f"Error in send_message function Error Code - {e}")
        await send_to_channel(update, content, channel_id, f"Error in send_message function \n\nError Code -{e}")





async def search_online(user_message, api, settings):
    try:
        tools=[
            types.Tool(google_search=types.GoogleSearch),
            types.Tool(url_context=types.UrlContext)
        ]
        
        if settings[2] == "gemini-2.5-pro" or settings[2] == "gemini-2.5-flash":
            config = types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_budget=settings[3]),
                temperature = settings[4],
                system_instruction=load_persona(settings),
                tools = tools,
                response_modalities=["TEXT"],
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
        else:
            config = types.GenerateContentConfig(
                temperature = settings[4],
                system_instruction=load_persona(settings),
                tools = tools,
                response_modalities=["TEXT"],
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
        
        temp_api = gemini_api_keys.copy()
        for _ in range(len(gemini_api_keys)):
            try:
                api_key = random.choice(temp_api)
                client = genai.Client(api_key=api_key)
                response = await client.aio.models.generate_content(
                model = settings[2],
                contents = [user_message],
                config = config,
                )
                if response:
                    return response
                else:
                    raise Exception
            except Exception as e:
                print(f"Error in searching online with API key {gemini_api_keys.index(api_key)}. Retrying with next key.\n\nError Code - {e}")
                temp_api.remove(api_key)
                if not temp_api:
                    return None
    except Exception as e:
        print(f"Error getting gemini response in search_online function.\n\n Error Code - {e}")
        return None

#a function to use gemini CodeExecution Tool
async def execute_code(update: Update, content: ContextTypes.DEFAULT_TYPE, user_message, settings, usr_msg, msg_obj):
    try:
        if msg_obj:
            tmsg = await msg_obj.edit_text("Working...")
        else:
            tmsg = await update.message.reply_text("Working...")
        tools=[]
        tools.append(types.Tool(code_execution=types.ToolCodeExecution))
        if settings[2] == "gemini-2.5-pro" or settings[2] == "gemini-2.5-flash":
            config = types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_budget=settings[3]),
                temperature = settings[4],
                system_instruction=load_persona(settings),
                tools = tools,
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
        else:
            config = types.GenerateContentConfig(
                temperature = settings[4],
                system_instruction=load_persona(settings),
                tools = tools,
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

        temp_api = gemini_api_keys.copy()
        for _ in range(len(gemini_api_keys)):
            try:
                api_key = random.choice(temp_api)
                client = genai.Client(api_key=api_key)
                response = await client.aio.models.generate_content(
                    model = settings[2],
                    contents = [user_message],
                    config = config,
                )
                if not response:
                    raise Exception
                break
            except:
                temp_api.remove(api_key)
                if not temp_api:
                    response = None

        within_response = False
        if not response:
            await update.message.reply_text("Failed to get response from gemini. Try again later.")

        count = 0

        for part in response.candidates[0].content.parts:
            if count != 0:
                tmsg = None
            if hasattr(part, "text") and part.text is not None:
                count += 1
                if within_response:
                    await send_message(update, content, part.text, None, tmsg)
                else:
                    await send_message(update, content, part.text, usr_msg, tmsg)
                    within_response = True
            if hasattr(part, "executable_code") and part.executable_code is not None:
                if within_response:
                    await send_message(update, content, "Code:\n```\n" + str(part.executable_code.code) + "\n```", None, tmsg)
                else:
                    await send_message(update, content, "Code:\n```\n" + str(part.executable_code.code) + "\n```", usr_msg, tmsg)
                    within_response = True
            if hasattr(part, "code_execution_result") and part.code_execution_result is not None:
                if within_response:
                    await send_message(update, content, "Output:\n" + str(part.code_execution_result.output), None, tmsg)
                else:
                    await send_message(update, content, "Output:\n" + str(part.code_execution_result.output), usr_msg, tmsg)
                    within_response = True
    except Exception as e:
        print(f"Error in execute_code function.\n\nError Code - {e}")
        await send_to_channel(update, content, channel_id, f"Error in execute_code function.\n\nError Code - {e}")




async def create_pdf(update: Update, content: ContextTypes.DEFAULT_TYPE, argument: dict, usr_msg, msg_obj):
    try:
        now = int(time.time())
        user_id = update.effective_user.id
        os.makedirs("data/media", exist_ok=True)
        pdf_filename = f"data/media/{user_id}-{now}.pdf"
        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_font('DejaVu', '', 'font/DejaVu.ttf', uni=True)
        pdf.add_font('DejaVu', 'B', 'font/DejaVuB.ttf', uni=True)
        pdf.add_font('DejaVu', 'I', 'font/DejaVuI.ttf', uni=True)
        pdf.add_font('DejaVu', 'BI', 'font/DejaVuBI.ttf', uni=True)
        texts = argument.get("text", [])
        font_sizes = argument.get("font_size", [])
        font_colors_hex = argument.get("font_color", [])
        font_styles = argument.get("font_style", [])
        alignments = argument.get("text_alignment", [])

        # Set default values
        default_font_size = 12
        default_font_color = "#000000"
        default_font_style = ''
        default_alignment = 'L'

        # Pad lists to match texts length
        def pad_list(lst, default):
            return lst + [default] * (len(texts) - len(lst))

        font_sizes = pad_list(font_sizes, default_font_size)
        font_colors_hex = pad_list(font_colors_hex, default_font_color)
        font_styles = pad_list(font_styles, default_font_style)
        alignments = pad_list(alignments, default_alignment)
        font_colors_rgb = [hex_to_rgb(color) for color in font_colors_hex]

        for i in range(len(texts)):
            current_text = texts[i].replace("💋", "[kiss]")
            pdf.set_font("DejaVu", style=font_styles[i], size=font_sizes[i])
            r, g, b = font_colors_rgb[i]
            pdf.set_text_color(r, g, b)
            pdf.multi_cell(w=0, txt=current_text, border=0, align=alignments[i], ln=1)
            pdf.ln(5)
            texts[i] = f"[color:{font_colors_rgb[i]}, size:{font_sizes[i]}, align:{alignments[i]}, font_style:{font_styles[i]}] {current_text}"
        pdf.output(pdf_filename)
        try:
            with open(pdf_filename, "rb") as file:
                await content.bot.send_document(
                    chat_id=user_id, 
                    document=file, 
                    caption="Here is your PDF, created by AI."
                )
        except Exception as e:
            print(f"Error sending PDF: {e}")
        response = "\n".join(texts)
        await save_conversation(None,  "\n<PDF CONTENT>\n" + response + "\n</PDF CONTENT>", user_id)
        return pdf_filename
    except Exception as e:
        print(f"Error in create_pdf function.\n\nError Code -{e}")
        await msg_obj.edit_text(f"Internal Error, Contact admin ot try again later.\n\nError Code - {e}")


#function to get response using group data
async def get_group_data(update:Update, content:ContextTypes.DEFAULT_TYPE, user_message, settings, api, func_name, msg_obj):
    try:
        if msg_obj:
            msg = await msg_obj.edit_text("Analyzing huge chunk of data, please wait...")
        else:
            msg = await update.message.reply_text("Analyzing huge chunk of data, please wait...")
        tools=[
            types.Tool(google_search=types.GoogleSearch),
            types.Tool(url_context=types.UrlContext)
        ]
        
        if func_name == "get_group_data":
            data = "****TRAINING DATA****\n\n"
            async with asyncio.open("data/info/group_training_data.shadow", "rb") as f:
                data += g_ciphers.decrypt(secret_nonce, await f.read(), None).decode("utf-8")
            data += "\n\n****END OF TRAINIG DATA****\n\n"
            data += user_message
        elif func_name == "get_ct_data":
            data = "***ALL CT DATA***\n\n"
            data += str(await get_ct_data())
            data += "***END OF CT DATA***\n\n"
            data += """Use this format to represent CT data
            📚 Upcoming CTs

            ⏰ NEXT: <Subject>
            🗓️ <date>
            👨‍🏫 <teacher name>
            📖 <topic1>
            →<topic2>
            →<topic3>
            """
            data += "Rules: Recheck the time and date"
            data += "\n\n" + user_message
        if settings[2] == "gemini-2.5-pro" or settings[2] == "gemini-2.5-flash":
            config = types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_budget=settings[3]),
                temperature = settings[4],
                system_instruction=load_persona(settings),
                tools = tools,
                response_modalities=["TEXT"],
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
        else:
            config = types.GenerateContentConfig(
                temperature = settings[4],
                system_instruction=load_persona(settings),
                tools = tools,
                response_modalities=["TEXT"],
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
        

        temp_api = gemini_api_keys.copy()
        for _ in range(len(gemini_api_keys)):
            try:
                api_key = random.choice(temp_api)
                client = genai.Client(api_key=api_key)
                response = await client.aio.models.generate_content(
                model = settings[2],
                contents = [data],
                config = config,
                )
                if response:
                    return (response, msg)
                else:
                    raise Exception
            except Exception as e:
                print(f"Error: {e}")
                temp_api.remove(api_key)
                if not temp_api:
                    return (None, msg)

    except Exception as e:
        print(f"Error in get_group_data function.\n\nError Code - {e}")
        return None


#function to create image based on user request
async def create_image(update:Update, content:ContextTypes.DEFAULT_TYPE, api, prompt, msg_obj):
    try:
        message = update.message or update.edited_message
        user_id = update.effective_user.id
        if msg_obj:
            msg = await msg_obj.edit_text("Image creation is in process, This may take a while please wait patiently.")
        else:
            msg = await message.reply_text("Image creation is in process, This may take a while please wait patiently.")
        
        temp_api = gemini_api_keys.copy()
        for _ in range(len(gemini_api_keys)):
            try:
                api_key = random.choice(temp_api)
                client = genai.Client(api_key=api)
                response = await client.aio.models.generate_content(
                    model = "gemini-2.5-flash-image-preview",
                    contents = prompt,
                    config = types.GenerateContentConfig(
                        response_modalities=["TEXT", "IMAGE"],
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
                if response and (response.candidates[0].content.parts[0].text is not None or response.candidates[0].content.parts[0].inline_data is not None):
                    break
                else:
                    raise Exception
            except:
                temp_api.remove(api_key)

        if not response:
            await msg.edit_text("Failed to create image, Please try again later.")
        for part in response.candidates[0].content.parts:
            if hasattr(part, "text") and part.text is not None:
                await msg.edit_text(part.text)
                await save_conversation(None, part.text, update.effective_user.id)
            elif hasattr(part, "inline_data") and part.inline_data is not None:
                image = Image.open(BytesIO(part.inline_data.data))
                bio = BytesIO()
                image.save(bio, "PNG")
                bio.seek(0)
                await content.bot.send_photo(chat_id=user_id, photo=bio, caption="Generated By AI")
    except Exception as e:
        print(f"Error in create_image function.\n\nError Code - {e}")


#function to add a piece of information to memory
async def add_memory_content(update:Update, content:ContextTypes.DEFAULT_TYPE, data, msg_obj):
    try:
        if msg_obj:
            msg = await msg_obj.edit_text("📝🧠 Memory Updated")
        else:
            msg = await update.message.reply_text("📝🧠 Memory Updated")
        user_id = update.effective_user.id
        key = bytes.fromhex(all_user_info[user_id][6])
        nonce = bytes.fromhex(all_user_info[user_id][7])
        ciphers = AESGCM(key)
        if os.path.exists(f"data/memory/memory-{user_id}.shadow"):
            async with aiofiles.open(f"data/memory/memory-{user_id}.shadow", "rb") as file:
                mem_data = await file.read()
                if mem_data:
                    pre_mem = ciphers.decrypt(nonce, mem_data, None).decode("utf-8")
                else:
                    pre_mem = ""
            mem = pre_mem + data
            mem = ciphers.encrypt(nonce, mem.encode("utf-8"), None)
            async with aiofiles.open(f"data/memory/memory-{user_id}.shadow", "wb") as file:
                await file.write(mem)
    except Exception as e:
        print(f"Error in add_memory_content function.\n\nError Code - {e}")




#All the global function 
async def analyze_media(update: Update, content: ContextTypes.DEFAULT_TYPE, media_list, prompt, settings, usr_msg, msg_obj):
    try:
        print(media_list)
        user_id = update.effective_user.id
        if msg_obj:
            message = await msg_obj.edit_text("Analyzing all available file and media, please wait...")
        else:
            message = await update.message.reply_text("Analyzing all available file and media, please wait...")
        if not media_list:
            await content.bot.delete_message(chat_id=user_id, message_id=message.message_id)
            await update.message.reply_text("No media found to analyze.")
            return None
        temp_api = gemini_api_keys.copy()
        model = "gemini-2.5-pro" if settings[2] == "gemini-2.5-pro" else "gemini-2.5-flash"

        for _ in range(len(gemini_api_keys)):
            try:
                api = random.choice(temp_api)
                client = genai.Client(api_key=api)
                contents = []
                for media in media_list:
                    if os.path.exists(media):
                        contents.append(client.files.upload(file=media))
                    else:
                        print(f"File {media} does not exist.")
                        return None
                contents.append(prompt)
                response = await client.aio.models.generate_content(
                    model = model,
                    contents = contents,
                    config = types.GenerateContentConfig(
                        thinking_config=types.ThinkingConfig(thinking_budget=settings[3]),
                        temperature=settings[4],
                        system_instruction=load_persona(settings),
                        response_modalities=["TEXT"],
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
                response.text
                break
            except Exception as e:
                temp_api.remove(api)
                if not temp_api:
                    response = None
                print(f"Error in analyzing media with API key {gemini_api_keys.index(api)}. Retrying with next key.\n\nError Code - {e}")

        
        if response is not None:
            await send_message(update, content, response, usr_msg, message)
        else:
            await update.message.reply_text("Failed to analyze the media")
    except Exception as e:
        print(f"Error in analyze_media function. \n\nError Code - {e}")
        return None 





#gemini response for stream off
async def gemini_non_stream(update:Update, content:ContextTypes.DEFAULT_TYPE, user_message, api, settings, usr_msg):
    try:
        tmsg = None
        user_id = update.effective_user.id
        tools=[types.Tool(function_declarations=func_list)]
        if settings[2] == "gemini-2.5-pro" or settings[2] == "gemini-2.5-flash":
            if settings[3] != 0 and not tmsg:
                tmsg = await update.message.reply_text("Thinking...")
            config = types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_budget=settings[3]),
                temperature = settings[4],
                system_instruction=load_persona(settings),
                tools = tools,
                response_modalities=["TEXT"],
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
        else:
            config = types.GenerateContentConfig(
                temperature = settings[4],
                system_instruction=load_persona(settings),
                tools = tools,
                response_modalities=["TEXT"],
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


        client = genai.Client(api_key=api)
        response = await client.aio.models.generate_content(
            model = settings[2],
            contents = [user_message],
            config = config,
        )

        if response.prompt_feedback and response.prompt_feedback.block_reason:
            await update.message.reply_text("Prohibited content detected. Conversation history will be deleted.")
            if os.path.exists(f"data/Conversation/conversation-{user_id}.shadow"):
                await reset(update, content, query = None)
            return "false"
        has_function = False


        for part in response.candidates[0].content.parts:
            if hasattr(part, "function_call") and part.function_call is not None:
                has_function = True
                function_call = part.function_call

        if has_function:
            if function_call.name == "search_online":
                text = ""
                for part in response.candidates[0].content.parts:
                    if hasattr(part, "text") and part.text is not None:
                        if tmsg:
                            await tmsg.edit_text(part.text)
                            tmsg = None
                        else:
                            await update.message.reply_text(part.text)
                    if hasattr(part, "function_call") and part.function_call is not None:
                        if not tmsg:
                            tmsg = await update.message.reply_text("Searching...")
                        else:
                            tmsg = await tmsg.edit_text("Searching...")
                        query = user_message + f"[!COMMAND: Search online and collect all the necessary information to provide a accurate and helpful response. Specially search with this query: {function_call.args['query']}]"
                        response = await search_online(query, api, settings)
                        if response.text is not None:
                            await send_message(update, content, response, usr_msg, tmsg)

            elif function_call.name == "get_group_data":
                response = await get_group_data(update, content, user_message, settings, api, function_call.name, tmsg)
                return response
            
            elif function_call.name == "get_ct_data":
                response = await get_group_data(update, content, user_message, settings, api, function_call.name, tmsg)
                return response
            
            elif function_call.name == "create_image":
                for part in response.candidates[0].content.parts:
                    if hasattr(part, "text") and part.text is not None:
                        await update.message.reply_text(part.text)
                await save_conversation(usr_msg, response.text, user_id)
                prompt = function_call.args["prompt"]
                await create_image(update,content, api, prompt, tmsg)
            
            elif function_call.name == "get_routine":
                for part in response.candidates[0].content.parts:
                    if hasattr(part, "text") and part.text is not None:
                        if tmsg:
                            await tmsg.edit_text(part.text)
                        else:
                            await update.message.reply_text(part.text)
                        await save_conversation(usr_msg, part.text + "\n <Routine Image>\n", user_id)
                await routine_handler(update, content)
            
            elif function_call.name == "add_memory_content":
                data = function_call.args["memory_content"]
                text = ""
                for part in response.candidates[0].content.parts:
                    if hasattr(part, "text") and part.text is not None:
                        text += part.text
                await add_memory_content(update, content, data, tmsg)
                if text.strip():
                    await send_message(update, content, text, usr_msg, None)
                return "false"
            
            elif function_call.name == "information_handler":
                markup = await information_handler(update, content, function_call.args["info_name"])
                for part in response.candidates[0].content.parts:
                    if hasattr(part, "text") and part.text is not None:
                        if type(markup) == str and markup:
                            text = response.text + markup
                            await update.message.reply_text(text, parse_mode="Markdown")
                            await save_conversation(usr_msg, text, user_id)
                        else:
                            text = part.text
                            await update.message.reply_text(text, reply_markup=markup, parse_mode="Markdown")
                            await save_conversation(usr_msg, text, user_id)
                            return "false"
                    else:
                        if type(markup) == str and markup:
                            text = markup
                            await save_conversation(usr_msg,text, user_id)
                            await update.message.reply_text(text, parse_mode="Markdown")
                            return "false"
                        else:
                            await update.message.reply_text("Click the button to see your requested data", reply_markup=markup)
                            await save_conversation(usr_msg, "Click the button to see your requested data", user_id)
                            return 'false'
            
            elif function_call.name == "fetch_media_content":
                media_paths = function_call.args["media_paths"]
                await analyze_media(update, content, media_paths, user_message, settings, usr_msg, tmsg)
                return 'false'
            
            elif function_call.name == "run_code":
                data = ""
                for part in response.candidates[0].content.parts:
                    if hasattr(part, "text") and part.text is not None:
                        data += part.text
                    if hasattr(part, "function_call") and part.function_call is not None:
                        code = part.function_call.args["code"]
                        if code:
                            data += "\n" + code
                if data:
                    await send_message(update, content, data, user_message, tmsg)
                    return 'false'
            
            elif function_call.name == "create_pdf":
                if tmsg:
                    tmsg = await tmsg.edit_text("Creating PDF...")
                if hasattr(response, "text"):
                    if response.text:
                        await send_message(update, content, response, usr_msg, tmsg)
                else:
                    await send_message(update, content, "Here is your requested PDF: \n", usr_msg, tmsg)
                path = await create_pdf(update, content, function_call.args, usr_msg, tmsg)
                if os.path.exists(path):
                    os.remove(path)
            
            elif function_call.name == "execute_code":
                await asyncio.create_task(execute_code(update, content, user_message, settings, usr_msg, tmsg))
            return 'false'
        
        return (response, tmsg)
    
    except Exception as e:
        if tmsg:
            await content.bot.delete_message(chat_id=user_id, message_id=tmsg.message_id)
            tmsg = None
        print(f"Error getting gemini response.\n\n Error Code - {e}")
        


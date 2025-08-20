create_image_function = {
    "name" : "create_image",
    "description" :"Generates a highly detailed and visually appealing image based on the user's prompt — designed to go beyond plain representations and create beautiful, vivid, and stylized visuals that capture the essence of the subject.",
    "parameters" : {
        "type" : "object",
        "properties" : {
            "prompt" : {
                "type" : "string",
                "description" : "A rich, descriptive prompt that guides the image generation — include details like subject, environment, lighting, emotion, style, and mood to get the most beautiful and expressive result.",
            },
        },
        "required" : ["prompt"],
    },
}


search_online_function = {
    "name": "search_online",
    "description": (
        "Performs a real-time online search to retrieve accurate and current information. "
        "Can search the web based on a query or extract context from a specific URL if provided."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search term or question to look up online. Or A specific URL to fetch and extract information from with a perfect command for what to do."
            },
        },
        "required" : ["query"],
    },
}


get_group_data_function ={
    "name" : "get_group_data",
    "description" : (
        "Fetch data that holds all the message and description about our class and all the user and give response from it"
        "This are the class member:\n"
        """ 1. Umme Kulsum
            2. Urboshi Mahmud
            3. Shahriar Joy
            4. Tasnimul Hassan Tanim
            5. Mahdi Haque
            6. Suprio Roy Chowdhury
            7. Tahmim Ullah
            8. Shafayet Hossain Shuvo
            9. Athai Dey
            10. Abdullah Sifat
            11. Tanvir Chowdhury
            12. Esika Tanzum
            13. Saroar Jahan Tius
            14. Tafsirul Ahmed Azan
            15. Muhammad Khushbo Nahid
            16. Reyano Kabir
            17. MD Tasdid Hossain
            18. Fazle Rabbi
            19. Fahad Kabir
            20. Md Shibli Sadik Sihab
            21. Tasaouf Ahnaf
            22. Shariqul Islam
            23. Shohanur Rahman Shadhin
            24. Rabib Rehman
            25. Sumon Majumder
            26. Shadman Ahmed
            27. Bitto Saha
            28. Nazmus Saquib Sinan
            29. Fajle Hasan Rabbi
            30. Nilay Paul
            31. Afra Tahsin Anika
            32. MD Shoykot Molla
            33. Arefin Noused Ratul
            34. Avijet Chakraborty
            35. A Bid
            36. Aftab Uddin Antu
            37. Prantik Paul
            38. Eram Ohid
            39. Sazedul Islam
            40. Mirajul Islam
            41. Sayem Bin Salim
            42. Fardin Numan
            43. Anjum Shahitya
            44. Tanvir Ahmed
            45. Sujoy Rabidas
            46. Samiul Islam Wrivu
            47. Md. Sami Sadik
            48. Aminul Islam Sifat
            49. Salman Ahmed Sabbir
            50. Aqm Mahdi Haque
            51. Mehedi Hasan
            52. Shahriar Joy
            53. Mawa Tanha
            54. Sara Arpa
            55. Md Tausif Al Sahad
            56. Mubin R.
            57. Abdul Mukit
            58. Arnob Benedict Tudu
            59. Sajid Ahmed
            60. Yasir Arafat
            61. Morchhalin Alam Amio"""
        "Get info about CR, teacher etc"
        """Retrieves and analyzes a comprehensive dataset for the 'CSE Section C' university student group (24 Series, RUET).
        This function is the primary source of information for any query related to the internal affairs, members, and culture of this specific group.
        The dataset contains a complete list of its 61 members, a detailed summary of important group dynamics, and an extensive log of their informal group chat messages.
        Use this function when asked about key individuals, teachers, inside jokes, or recurring topics of conversation within the group.
        Key individuals include: CRs Sumon Majumder (gaming enthusiast, 1st 30) and Fazle Rabbi (serious, 2nd 30);
        bot programmers Bitto Saha and Sifat (shadow_mist); all-rounder Mirajul Islam ('the Faculty');
        Competitive Programming expert Nilay Paul;
        and EEE expert Shadman Ahmed ('Dr. Snake').
        Key teachers frequently discussed are the very strict Helal Sir (Maths), and the highly-praised Mainul Sir (EEE) and Shahiduzzaman Sir (CSE).
        The data is rich with inside jokes like 'sikhan vai', 'kibabe sombob', 'dirim', 'dream vhai', 'sheet e to lekha nai', 'CG 4.69', and complaints about 'Helal sir er sheet'.
        The message logs cover topics such as academic planning (class routines, CTs, lab reports), social coordination (hangouts, football, CSE Night), technical projects (group website, Telegram bot), coding (CP, GitHub), and general student banter in a mix of Bengali and English ('Banglish')."""
    ),
    "parameters" : {
        "type" : "object",
        "properties" : {
            
        }
    }
}


get_ct_data_function = {
    "name" : "get_ct_data",
    "description" : """Fetch data of upcoming class test or CT""",
    "parameters" : {
        "type" :"object",
        "properties" : {

        }
    }
}

get_routine_function = {
    "name" : "get_routine",
    "description" : "Provide class routine if asked about routine run this function.",
    "parameters" : {
        "type" :"object",
        "properties" : {

        }
    }
}


create_memory_function = {
    "name" : "add_memory_content",
    "description" : (
        "Used to store user-specific memories or preferences when the user explicitly asks the assistant "
        "to remember something. This may include names, dates, preferences, personal facts, instructions, "
        "or frequently mentioned information. The assistant should extract the relevant part from the user's message "
        "and store it for future context-aware interactions."
        "like 'remember that...', 'don't forget...', or 'store this...'."
        "for future reference—such as preferences, important facts, habits, names, birthdays, or any "
        "custom instruction. The assistant should extract the relevant content from the user message "
        "and pass it as a structured parameter for long-term storage."
        "Make sure to say something before, don't just call the function without any text"
    ),
    "parameters" : {
        "type" : "object",
        "properties" : {
            "memory_content" : {
                "type" : "string",
                "description" : (
                    "The exact information or fact the user wants to store"
                    "It should be clear and useful for future context."
                )
            }
        },
        "required" : ["memory_content"]
    }
}




information_handler_function = {
    "name": "information_handler",
    "description": (
        "Handles all queries related to our class resources such as the Drive link, cover page generator, "
        "class website, Google Classroom code, and orientation materials. Responds with a helpful message and, "
        "if applicable with a clickable button (except for Google Classroom code)."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "info_name": {
                "type": "string",
                "description": (
                    "'drive' When the user asks for the class Drive (for notes, CTs, labs, etc).\n"
                    "'cover_page' When the user asks for a cover page generator for assignments or lab reports.\n"
                    "'website' When asked for the official class website.\n"
                    "'g_class_code' When the user asks for the Google Classroom code.\n"
                    "'orientation_file' When the user wants the file that includes student list, CSE '24 syllabus, and the prospectus."
                )
            }
        },
        "required": ["info_name"]
    }
}



media_description_generator_function = {
    "name": "media_description_generator",
    "description": (
        "Generates a detailed and engaging description for media files based on the content of the provised media for future accessibility and understanding.\n"
        "Discribes the media's content, context, and any relevant details that would help to understand its significance, purpose and use case.\n"
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "media_type": {
                "type": "string",
                "description": "The type of media being described (e.g., 'image', 'video', 'audio', 'pdf', 'txt' ...)."
            },
            "media_description": {
                "type": "string",
                "description": "A detailed but sumamrized description of the media content, including its context, purpose, and any relevant details that would help understand its use case and significance."
            }
        },
        "required": ["media_type", "media_description"]
    }
}




fetch_media_content = {
    "name": "fetch_media_content",
    "description": (
        "Accesses the content of previous media files for in-depth analysis. "
        "Call this function to answer specific questions about a media's contents when a general description is insufficient."
        "Do not guess or assume the media content, call this too to find out."
        "Do not guess or assume that the requested content is not available in the media, call this function to find out."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "media_paths": {
                "type": "array",
                "items": {"type": "string"},
                "description": "The file paths of the media from the conversation history that need to be inspected."
            }
        },
        "required": ["media_paths"]
    }
}




create_pdf_function = {
    "name" : "create_pdf",
    "description" : "Generates pdf",
    "parameters" : {
        "type" : "object",
        "properties" : {
            "text" : {
                "type" : "array",
                "items" : {"type" : "string"},
                "description" : "The text that will be written in the pdf, separated by design difference from top to bottom. Add '\n' for newline."
            },
            "font_size" : {
                "type" : "array",
                "items" : {"type" : "integer"},
                "description" : "Font size for every text separated by design from top to bottom. Must be added for every text part"
            },
            "font_color" : {
                "type" : "array",
                "items" : {"type" : "string"},
                "description" : "Font color in hex format for every text separated by design from top to bottom. Must be added for every text part"
            },
            "font_style" : {
                "type" : "array",
                "items" : {"type" : "string"},
                "description" : (
                    "Text style for for every part separated by design from top to bottom."
                    "Allowed style (I, B, U, '')"
                    "I for italic, B for bold, U for underline, '' for normal"
                    "Combining them also possible like IU, IB etc."
                    "Must be added for every text part"
                )
            },
            "text_alignment" : {
                "type" : "array",
                "items" : {"type" : "string"},
                "description" : (
                    "Text alignment for every part separated by design from top to bottom"
                    "Allowed alignment 'C' for center, 'L' for left, 'R' for right" 
                    "Must be added for every text part"
                )
            }
        },
        "required" : ["text", "font_size", "font_color", "font_style", "text_alignment"]
    }
}



execute_code_function = {
    "name": "execute_code",
    "description": (
        "get the response with gemini CodeExecution tools. It does not run the code, it generate response with gemini CodeExecution tools from user message."
        "this function don't take anything as argument, it take user message in the backend."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            
        }
    }
}

 




func_list = [
    search_online_function,
    create_image_function,
    get_group_data_function,
    get_ct_data_function,
    get_routine_function,
    create_memory_function,
    information_handler_function,
    fetch_media_content,
    create_pdf_function,
    execute_code_function
]
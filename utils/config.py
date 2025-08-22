import os
from cryptography.fernet import Fernet
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from collections import defaultdict
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from motor.motor_asyncio import AsyncIOMotorClient






#All the environment variables
decryption_key = os.getenv("decryption_key")
mongo_pass = os.getenv("MDB_pass_shadow")
secret_key = os.getenv("secret_key")
secret_nonce = bytes.fromhex(os.getenv("secret_nonce"))


#configuring fernet for fernet encryption
fernet = Fernet(decryption_key)

#A channel id to send all the error message
channel_id = -1002575042671


#configuring AESGCM for encrypting data
g_ciphers = AESGCM(bytes.fromhex(secret_key))


#All the url for managing data in database
mongo_url = f"mongodb+srv://Shadow:{mongo_pass}@cluster0.zozzwwv.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
FIREBASE_URL = 'https://last-197cd-default-rtdb.firebaseio.com/routines.json'


#Base directory for program to find files and content
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


# Configurable rate limits
short_term_limit = 4        # seconds
short_term_max_request = 5  # max 5 requests in 5 sec

long_term_limit = 60        # seconds
long_term_max_request = 30  # max 20 requests in 60 sec

global_time_limit = 5
global_max_request = 100

banned_time = 300           # short-term ban = 5 min
long_term_ban_time = 600    # long-term ban = 10 min



#Store user requests to determine excessive usage and ddos attack
user_requests = defaultdict(list)
global_requests = []
banned_users = {}


#Configurable media limits
media_count_limit = 5
media_size_limit = 20
premium_media_count_limit = 10
premium_media_size_limit = 60



#Connecting to database as sync
try:
    db = MongoClient(mongo_url, server_api=ServerApi("1"))["phantom_bot"]
except:
    db = None



#Connecting to database as async
try:
    mdb = AsyncIOMotorClient(mongo_url)["phantom_bot"]
except:
    mdb = None




#Configuring webhooks url
#WEBHOOK_URL = "https://2d6320edc592.ngrok-free.app"              #local testing
#WEBHOOK_URL = "https://pikachu-zhx7.onrender.com"                #original render url
WEBHOOK_URL = "https://phantom-bot-9r8d.onrender.com"                #new render url
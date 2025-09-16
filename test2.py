from utils.utils import db

collections = db.list_collection_names()
users = [user for user in collections if user.isdigit()]


for user in users:
    col = db[user]
    col.update_one(
        {"id" : int(user)},
        {"$push" : {"statistics" : [{"start" : "00:00"}]}}
    )
    print(f"Done for the user {user}")

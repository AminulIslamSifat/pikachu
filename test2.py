from utils.utils import db as source
from utils.config import client

target = client["pikachu"]
collections = source.list_collection_names()

for col in collections:
    data = list(source[col].find())  # convert cursor to list
    if not data:
        print(f"Collection {col} is empty, skipping.")
        continue
    
    # remove _id if you want to avoid duplicates
    for doc in data:
        doc.pop("_id", None)
    
    target[col].insert_many(data)
    print(f"Copied {len(data)} documents of {col}")
#herrlo
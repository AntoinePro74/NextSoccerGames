import os
import json
from datetime import datetime

def load_last_update():
    file_path = "config/last_update.json"
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            data = json.load(f)
            return datetime.strptime(data["last_update"], "%Y-%m-%d %H:%M:%S")
    return None

def save_last_update(dt):
    file_path = "config/last_update.json"
    with open(file_path, "w") as f:
        json.dump({"last_update": dt.strftime("%Y-%m-%d %H:%M:%S")}, f)
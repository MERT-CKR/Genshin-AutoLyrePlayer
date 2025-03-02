import os
import time
import json

current_dir = os.path.dirname(os.path.realpath(__file__))
settings_dir = os.path.join(current_dir, "settings.json")

with open(settings_dir, "r", encoding = "utf-8") as settings:
    settings = json.load(settings)
    version = settings["settings"][0]["version"]#get version from settings
    

new_data = {
    "settings": [
        {
            "firstTime": 0,
            "Default_keys": "q w e r t y u a s d f g h j z x c v b n m",
            "language": "",
            "keys": "",
            "changelog": "",
            "version": version,
        }
    ]
}


with open(settings_dir, "w", encoding = "utf-8") as old_settings:
    json.dump(new_data, old_settings, indent = 4, ensure_ascii = False)

print("key rest successfull.")
time.sleep(1.25)
import json

new_data = {
    "settings": [
        {
            "firstTime": 0,
            "Default_keys": "q w e r t y u a s d f g h j z x c v b n m",
            "example": "q w e r t y u a s d f g h j z x c v b n m",
            "language": "",
            "keys": "q w e r t y u a s d f g h j z x c v b n m"
        }
    ]
}


with open("settings.json", "w", encoding="utf-8") as file:
    json.dump(new_data, file, indent=4, ensure_ascii=False)

print("key rest successfull.")
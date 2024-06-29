import json

# Değişkeninizdeki değer
new_data = {
    "settings": [
        {
            "firstTime": 0,
            "Default_keys": "y u ı o p h j k l ş n m ö ç b",
            "keys": "y u ı o p h j k l ş n m ö ç b",
            "language": ""
        }
    ]
}
# JSON dosyasına yeni veriyi yaz
with open("settings.json", "w", encoding="utf-8") as file:
    json.dump(new_data, file, indent=4, ensure_ascii=False)

print("key rest successfull.")
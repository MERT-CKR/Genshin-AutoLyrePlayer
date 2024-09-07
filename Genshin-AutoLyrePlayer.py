import columnPlayer
import notePlayer
import os
import json


current_directory = os.getcwd()
with open(os.path.join(current_directory,"settings.json"), "r", encoding="utf-8") as file:
    data = json.load(file)


translations_path = os.path.join(current_directory, "translations.json")



def load_translations():
    if data["settings"][0]["firstTime"] == 0 or data["settings"][0]["language"] == "":
        print("Select your language: \n1.Türkçe \n2.English")
        lang = int(input(">> "))
        if lang == 1:
            user_locale = "tr"
        elif lang == 2:
            user_locale = "en"

        data["settings"][0]["language"] = user_locale

        with open('settings.json', 'w', encoding="utf-8") as dosya:
            json.dump(data, dosya, indent=4, ensure_ascii=False)
    else:
        user_locale = data["settings"][0]["language"]

    with open(translations_path, 'r', encoding='utf-8') as f:
        translations = json.load(f)

    global _
    _ = lambda key: translations['languages'][key][user_locale]

load_translations()
if data["settings"][0]["firstTime"] == 1:
    pass
else:
    print(_("first_opening"))

    data["settings"][0]["firstTime"] = 1

    print(_("tutorial3"))
    print(_("tutorial4"))
    print(_("tutorial1"))
    print(_("tutorial2"))

    newKeys = int(input(">> "))
    newKeys = newKeys.replace(",", " ")

    if newKeys == "":
        data["settings"][0]["keys"] = data["settings"][0]["Default_keys"]
    else:
        data["settings"][0]["keys"] = newKeys

with open(os.path.join(current_directory,"settings.json"), "w", encoding="utf-8") as file:
    json.dump(data, file, indent=4, ensure_ascii=False)

print(_("key_assigned"))
key = data["settings"][0]["keys"][::-1]
key = key.split()

def specialized_speed(selection):
    selection = str(selection+1)
    print("selection: ",selection)
    if selection in ["4","8","11"]:
        selected = [0.09, 0.11, 0.11]# ideal hız
        print("selected speed: ",selected)
        return selected
    
    elif selection in ["3","16"]:# normalden biraz hızlılar için yavaşlatma
        selected = [0.12, 0.15, 0.15]
        print("selected speed: ",selected)
        return selected
    
    elif selection in ["6"]:# yavaşlar için hızlandırma
        selected = [0.08, 0.10, 0.10]
        print("selected speed: ",selected)
        return selected
    
    elif selection in ["17"]:# çok yavaşlar için hızlandırma
        selected = [0.06, 0.07, 0.05]
        print("selected speed: ",selected)
        return selected
    
    else:
        selected = [0.09, 0.11, 0.11]# ideal hız
        print("selected speed: ",selected)
        return selected

        
    


musicList = os.listdir(os.path.join(current_directory, "sheets"))

numbers = ["0", "1", "2", "3", "4", "5", "6", "7","8", "9", "10", "11", "12", "13", "14", "15","16", "17", "18", "19", "20"][::-1]
keys =    ["q", "w", "e", "r", "t", "y", "u", "a", "s", "d", "f", "g", "h", "j","z", "x", "c", "v", "b", "n", "m"][::-1]



musicDict = {}

def return_notes(selection):
    if selection > len(musicList) or selection <=0:
            showList()
            return

    selection -= 1
    
    musicDict[selection] = musicList[selection]
    with open(os.path.join(current_directory, "sheets", musicList[selection]), "r", encoding="UTF-8") as data:
        data = json.load(data)

    if  "notes" in data[0]:
        # dtype = "notes"
        notePlayer.play_music(data[0]["notes"])

    elif  "columns" in data[0]:
        # dtype = "columns"
        columnPlayer.playMusic(data[0]["columns"],specialized_speed(selection))

    else:
        raise TypeError("unknown format")

    

def showList():
    counter = 0
    for x in musicList:
        ext = x.split(".")[1]
        x = x.replace("."+ext,"")
        counter += 1
        print(counter, x)
        
    selection = int(input("choose from list\n>> "))
    return_notes(selection)



while __name__ == "__main__":
    print("Script is running with admin privileges.")
    showList()
    print(_("restart"))
    keep_continue = input(">> ")
    if keep_continue == "0":
        break
    else:
        print("Script is not running with admin privileges. Restarting...")
    

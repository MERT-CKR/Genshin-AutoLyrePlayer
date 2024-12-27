import columnPlayer
import notePlayer
import os
import json
import elevate
import requests
import random

os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "1"
from pygame import mixer,time as pytime

elevate.elevate()#run as admin

current_directory = os.getcwd()


def speak(mode, sfx):
    if sfx:
        path = os.path.join(current_directory,"sounds",mode)
        options = os.listdir(path)
        choise = random.choice(options)
        choise = os.path.join(path,choise)
    
        mixer.init()
        mixer.music.load(choise)
        mixer.music.play()
        
        
        while mixer.music.get_busy():
            pytime.Clock().tick(10)
        mixer.quit()



speak("initialize",True)


with open(os.path.join(current_directory,"settings.json"), "r", encoding="utf-8") as file:
    settings = json.load(file)


translations_path = os.path.join(current_directory, "translations.json")


def load_translations():
    if settings["settings"][0]["firstTime"] == 0 or settings["settings"][0]["language"] == "":
        print("Select your language: \n1.Türkçe \n2.English")
        lang = int(input(">> "))
        if lang == 1:
            user_locale = "tr"
        elif lang == 2:
            user_locale = "en"

        settings["settings"][0]["language"] = user_locale

        with open('settings.json', 'w', encoding="utf-8") as dosya:
            json.dump(settings, dosya, indent=4, ensure_ascii=False)
    else:
        user_locale = settings["settings"][0]["language"]

    with open(translations_path, 'r', encoding='utf-8') as f:
        translations = json.load(f)

    global _
    _ = lambda key: translations['languages'][key][user_locale]

load_translations()


def check_Updates():
    print(_("Checking_updates"))
    current_rel = settings["settings"][0]["version"]

    url ="https://raw.githubusercontent.com/MERT-CKR/Genshin-AutoLyrePlayer/main/settings.json"
    connection =True
    try:
        response = requests.get(url,timeout=3)
    except requests.ConnectionError:
        speak("error", True)
        print(_("connection_error"))
        connection=False

        
    if connection:
        try:
            json_content = response.json()
            new_rel = json_content["settings"][0]["version"]


            if new_rel == current_rel:
                print(_("using_last_version"))
                
            elif new_rel > current_rel:
                new_ver = _("new_version_available").replace("*current_rel",current_rel).replace("*new_rel",new_rel)
                print(new_ver)
                
        except Exception:
            speak("error", sfx)
            print(_("version_could_not_be_checked"))
            


    
check_Updates()

def sound():
    global sfx
    print("Scriptin seslerini kapatmak istermisiniz ? \n1 Evet \n2 Hayır")
    try:
        sfx = int(input(">> "))
        if sfx not in [1,2]:
            raise ValueError
        
        if sfx == 1:
            sfx = False

        else:
            sfx = True
    except:
        speak("error", sfx)
        sound()
sound()


if settings["settings"][0]["firstTime"] == 1:
    pass
else:
    print(_("first_opening"))

    settings["settings"][0]["firstTime"] = 1

    print(_("tutorial3"))
    print(_("tutorial4"))
    print(_("tutorial1"))
    print(_("tutorial2"))

    newKeys = input(">> ")

    if newKeys == "":
        settings["settings"][0]["keys"] = settings["settings"][0]["Default_keys"]
    else:
        settings["settings"][0]["keys"] = newKeys

with open(os.path.join(current_directory,"settings.json"), "w", encoding="utf-8") as file:
    json.dump(settings, file, indent=4, ensure_ascii=False)

print(_("key_assigned"))
key = settings["settings"][0]["keys"][::-1]
key = key.split()


musicList = os.listdir(os.path.join(current_directory, "sheets"))

numbers = ["0", "1", "2", "3", "4", "5", "6", "7","8", "9", "10", "11", "12", "13", "14", "15","16", "17", "18", "19", "20"][::-1]
keys =    ["q", "w", "e", "r", "t", "y", "u", "a", "s", "d", "f", "g", "h", "j","z", "x", "c", "v", "b", "n", "m"][::-1]



musicDict = {}

def return_notes(selection):

    selection -= 1
    
    musicDict[selection] = musicList[selection]
    with open(os.path.join(current_directory, "sheets", musicList[selection]), "r", encoding="UTF-8") as data:
        data = json.load(data)

    if  "notes" in data[0]:
        # file type = "notes"
        notePlayer.play_music(data[0]["notes"], sfx)

    elif  "columns" in data[0]:
        # file type = "columns"
        bpm = data[0]["bpm"]
        columnPlayer.play_music(data[0]["columns"],bpm, sfx)
        

    else:
        speak("error", sfx)
        raise TypeError(_("unknown_format"))
        



def showList():
    speak("searching", sfx)
    counter = 0
    for x in musicList:
        ext = x.split(".")[1]
        x = x.replace("."+ext,"")
        counter += 1
        print(counter, x)
        
    selection = int(input("choose from list\n>> "))

    if selection > len(musicList) or selection <=0:
        speak("error", sfx)
        showList()
        return
    
    return_notes(selection)

    


while __name__ == "__main__":
    print("Script is running with admin privileges.")
    showList()
    print(_("restart"))
    keep_continue = input(">> ")
    if keep_continue == "0":
        speak("close app", sfx)
        break
    else:
        print("Script is not running with admin privileges. Restarting...")
    

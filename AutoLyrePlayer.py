import os
import json
import requests
import elevate
elevate.elevate()#run as admin
# Required to be able to press keys in Genshin Impact running as admin.


current_directory = os.getcwd()
with open(os.path.join(current_directory, "settings.json"), "r", encoding="utf-8") as file:
    settings = json.load(file)

user_locale = settings["settings"][0]["language"]
if user_locale not in ["tr","en"]:
    print("Select your language: \n1.Türkçe \n2.English")
    lang = int(input(">> "))
    if lang == 1:
        user_locale = "tr"
    elif lang == 2:
        user_locale = "en"

    settings["settings"][0]["language"] = user_locale
       

    with open('settings.json', 'w', encoding="utf-8") as dosya:
        json.dump(settings, dosya, indent=4, ensure_ascii=False)
        


import ColumnPlayer
import NotePlayer
from common import load_translations, speak

_ = load_translations()

if settings["settings"][0]["firstTime"] != 1:
    #first_opening
    settings["settings"][0]["firstTime"] = 1
    print(_("tutorial1"))
    print(_("tutorial2"))

    newKeys = input(">> ")

    print(_("talking_script"))
    talk_mode = int(input(">> "))

    if talk_mode == 1:
        settings["settings"][0]["talk_mode"] = 1

    else:
        settings["settings"][0]["talk_mode"] = 0

    if newKeys == "":
        settings["settings"][0]["keys"] = settings["settings"][0]["Default_keys"]

    else:
        settings["settings"][0]["keys"] = newKeys

    with open('settings.json', 'w', encoding="utf-8") as dosya:
        json.dump(settings, dosya, indent=4, ensure_ascii=False)

    print(_("key_assigned"))



sfx = settings["settings"][0]["talk_mode"]
speak("initialize", sfx)


def check_Updates():
    print(_("Checking_updates"))
    current_rel = settings["settings"][0]["version"]

    url ="https://raw.githubusercontent.com/MERT-CKR/Genshin-AutoLyrePlayer/main/settings.json"
    connection = True
    try:
        response = requests.get(url, timeout=4)
    except requests.ConnectionError:
        speak("error", sfx)
        print(_("connection_error"))
        connection = False

        
    if connection:
        try:
            json_content = response.json()
            new_rel = json_content["settings"][0]["version"]
           
            changelog = json_content["settings"][0]["changelog"]

            if new_rel == current_rel:
                print(_("using_last_version"))
                
            elif new_rel > current_rel:
                new_ver = _("new_version_available").replace("*current_rel", current_rel).replace("*new_rel", new_rel)
                print(new_ver)

                if changelog != "":
                    print(_("changelog"), changelog)
                
        except Exception as e:
            speak("error", sfx)
            print(e)
            print(_("version_could_not_be_checked"))
            
check_Updates()





musicList = os.listdir(os.path.join(current_directory, "sheets"))
musicDict = {}

def return_notes(selection):
    selection -= 1
    musicDict[selection] = musicList[selection]
    with open(os.path.join(current_directory, "sheets", musicList[selection]), "r", encoding="UTF-8") as data:
        data = json.load(data)

    if  "notes" in data[0]:
        # file type = "notes"
        NotePlayer.play_music(data[0]["notes"], sfx)

    elif  "columns" in data[0]:
        # file type = "columns"
        bpm = data[0]["bpm"]
        ColumnPlayer.play_music(data[0]["columns"], bpm, sfx)
        
    else:
        speak("error", sfx)
        raise TypeError(_("unknown_format"))
        



def showList():
    speak("searching", sfx)
    counter = 0
    for x in musicList:
        ext = x.split(".")[1]
        x = x.replace("." + ext, "")
        counter += 1
        print(counter, x)
        
    selection = int(input(_("choose_music")))
    
    if selection > len(musicList) or selection <=0:
        speak("error", sfx)
        showList()
        return
    
    return_notes(selection)

    

while __name__ == "__main__":
    showList()
    print(_("restart"))
    keep_continue = input(">> ")
    if keep_continue == "0":
        speak("close app", sfx)
        break
    

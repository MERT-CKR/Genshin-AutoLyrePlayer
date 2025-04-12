import os
import json
import requests
import sys
import ctypes
import subprocess


# Genshin impact is running as an Administrator so only applications running as an Administrator can interact with it.
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

if not is_admin():
    script_path = os.path.abspath(sys.argv[0])
    
    # Run Windows Terminal as admin
    subprocess.run([
        "powershell", "-Command",
        f"Start-Process wt -ArgumentList '-w 0 nt -p \"PowerShell\" -- python \"{script_path}\"' -Verb RunAs"
    ])
    sys.exit()



current_directory = os.path.dirname(os.path.realpath(__file__))
settings_path = os.path.join(current_directory, "settings.json")
                             
with open(settings_path, "r", encoding = "utf-8") as file:
    settings = json.load(file)
    settings = settings["settings"][0]
    
    

user_locale = settings["language"]

lang_dict = {
    "1" : "tr",
    "2" : "en"
}

supported_languages = lang_dict.values()
supported_lang_index = lang_dict.keys()


if user_locale not in supported_languages:

    print(f"\033[32mSelect your language:\033[0m")
    counter = 0
    for item in supported_languages:    
        counter += 1
        print(f"\033[93m{counter}\033[0m \033[91m{item}\033[0m") #Colorfull list
    input_lang_index = input(">> ")
    
    if input_lang_index in supported_lang_index:
        selected_lang = lang_dict[input_lang_index]

        if selected_lang in supported_languages:
            user_locale = selected_lang

    else:
        raise ValueError(f"Language not selected \nOptions are {supported_languages} !!!")
    

    settings["language"] = user_locale   
    

    with open(settings_path, 'w', encoding = "utf-8") as old_file:
        json.dump({"settings": [settings]}, old_file, indent = 4, ensure_ascii = False)


import ColumnPlayer
import NotePlayer
from common import load_translations
from common import print_red, print_yellow, print_green, print_colorful_list
_ = load_translations()

if settings["firstTime"] != 1:
    #first_opening
    settings["firstTime"] = 1
    print_yellow(_("tutorial1"))
    print_yellow(_("tutorial2"))


    new_keys = input(">> ")
    if new_keys == "":
        settings["keys"] = settings["Default_keys"]

    else:
        settings["keys"] = new_keys

    with open(settings_path, 'w', encoding = "utf-8") as old_settings:
        json.dump({"settings": [settings]}, old_settings, indent = 4, ensure_ascii = False)

    print_yellow(_("key_assigned"))



def check_Updates():
    print_yellow(_("Checking_updates"))
    current_rel = settings["version"]

    url = "https://raw.githubusercontent.com/MERT-CKR/Genshin-AutoLyrePlayer/main/settings.json"
    connection = True
    try:
        response = requests.get(url, timeout=4)
    except requests.ConnectionError:
        print_red(_("connection_error"))
        connection = False

        
    if connection:
        try:
            json_content = response.json()
            json_content = json_content["settings"][0]
            new_rel = json_content["version"]
            changelog = json_content["changelog"]

            if new_rel == current_rel:
                print_green(_("using_latest_version"))
                
            elif new_rel > current_rel:
                new_ver = _("new_version_available").replace("*current_rel", current_rel).replace("*new_rel", new_rel)
                print_green(new_ver)

                if changelog != "":
                    print_green(_("changelog"))
                    print_yellow(changelog)
            else:
                print_yellow("Developing\n")
        except Exception as err:
            print_red(err)
            print_red(_("version_could_not_be_checked"))
            
check_Updates()


musicList = os.listdir(os.path.join(current_directory, "sheets"))
musicDict = {}

# Determine the note type and send sheets to player
def return_notes(selection):
    try:
        selection -= 1
        musicDict[selection] = musicList[selection]
    except:
        showList()
        return

    with open(os.path.join(current_directory, "sheets", musicList[selection]), "r", encoding = "UTF-8") as data:
        data = json.load(data)

    if  "notes" in data[0]:
        # file type = "notes" (Generally, complex notes are in this format.)
        NotePlayer.play_music(data[0]["notes"])

    elif  "columns" in data[0]:
        # file type = "columns" (simpler and more systematic note format)
        bpm = data[0]["bpm"] #bpm: beats per minute 
        ColumnPlayer.play_music(data[0]["columns"], bpm)
        
    else:
        raise TypeError(_("unknown_format"))
        
# Show user music list
def showList():
    counter = 0
    for item in musicList:
        ext = item.split(".")[1]
        item = item.replace("." + ext, "")#remove extension like .txt
        counter += 1
        print_colorful_list(counter, item)
    
    try:
        selection = int(input(f"\033[32m{_("choose_music")}\033[0m"))# green input message
    except:
        showList()
        return
    
    if selection > len(musicList) or selection <= 0:
        showList()
        return
    
    return_notes(selection)

    

while __name__ == "__main__":
    showList()
    print_green(_("restart"))
    keep_continue = input(">> ")

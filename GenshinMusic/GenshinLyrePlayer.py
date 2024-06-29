import time
import keyboard
import pandas as pd
import os
import json


with open("settings.json", "r", encoding="utf-8") as file:
    data = json.load(file)

current_directory = os.getcwd()
jsonFilePath = os.path.join(current_directory, "translations.json")

def inputForce(prompt, Typ=int):
    while True:
        try:
            Input0 = Typ(input(prompt))
            return Input0
        except ValueError:
            print(_("invalid_prompt"))

def load_translations():
    if data["settings"][0]["firstTime"] == 0 or data["settings"][0]["language"] == "":
        print("Select your language: \n1.Türkçe \n2.English")
        lang = inputForce(">> ")
        if lang == 1:
            user_locale = "tr"
        elif lang == 2:
            user_locale = "en"

        data["settings"][0]["language"] = user_locale

        with open('settings.json', 'w', encoding="utf-8") as dosya:
            json.dump(data, dosya, indent=4, ensure_ascii=False)
    else:
        user_locale = data["settings"][0]["language"]

    with open(jsonFilePath, 'r', encoding='utf-8') as f:
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

    newKeys = inputForce(">> ", str)
    newKeys = newKeys.replace(",", " ")

    if newKeys == "":
        data["settings"][0]["keys"] = data["settings"][0]["Default_keys"]
    else:
        data["settings"][0]["keys"] = newKeys

with open("settings.json", "w", encoding="utf-8") as file:
    json.dump(data, file, indent=4, ensure_ascii=False)

print(_("key_assigned"))
key = data["settings"][0]["keys"][::-1]
key = key.split()


musicList = os.listdir(os.path.join(current_directory, "GenshinSheets"))

numbers = ["0", "1", "2", "3", "4", "5", "6", "7","8", "9", "10", "11", "12", "13", "14", "15","16", "17", "18", "19", "20"][::-1]
keys =    ["q", "w", "e", "r", "t", "y", "u", "a", "s", "d", "f", "g", "h", "j","z", "x", "c", "v", "b", "n", "m"][::-1]
#  asdfghj
musicDict = {}

def bring(id):
    id -= 1
    musicDict[id] = musicList[id]
    with open(os.path.join(current_directory, "GenshinSheets", musicList[id]), "r", encoding="UTF-8") as data:
        data = json.load(data)
    filedata = data[0]
    columns_data = filedata["columns"]
    return columns_data

def showList():
    sayac = 0
    for x in musicList:
        sayac += 1
        print(sayac, x)

def countDown():
    print(_("starting"))
    time.sleep(1)
    print(4)
    time.sleep(1)
    print(3)
    time.sleep(1)
    print(2)
    time.sleep(1)
    print(1)

listw2 = ""
def mergeFromList(listw):
    global listw2
    print("girdi: ", listw)
    for i in range(len(listw)):
        listw2 += listw[i]
    return listw2

def playMusic(sheets):
    global replaced_elements
    countDown()
    for i in sheets:
        if i[1] == []:
            replaced_elements = "boş sayfa"
        else:
            first_elements = [item[0] for item in i[1]]
            replaced_elements = [keys[numbers.index(str(elem))] if str(elem) in numbers else str(elem) for elem in first_elements]

        print(replaced_elements)
        print("-----------")

        if keyboard.is_pressed('"'):
            print(_("loop_ending"))
            break
        
        if replaced_elements != "boş sayfa":
            if len(replaced_elements) > 1:
                for char in replaced_elements:
                    keyboard.press(char)
                time.sleep(0.080)
                for char in replaced_elements:
                    keyboard.release(char)
            else:
                keyboard.press_and_release(replaced_elements[0])
                time.sleep(0.080)
        else:
            time.sleep(0.1000)


def Run():
    showList()
    print("müzik seç")
    selection = inputForce("\n>> ")
    playMusic(bring(selection))

while True:
    print("run çalışıyor")
    Run()
    print(_("restart"))
    keepContinue = input(">> ")
    if keepContinue != "1":
        break

import os
import json
import time
import pygetwindow as gw
# module: common

current_dir = os.path.dirname(os.path.realpath(__file__))
translations_path = os.path.join(current_dir, "translations.json")
settings_path = os.path.join(current_dir, "settings.json")


with open(settings_path, "r", encoding = "utf-8") as file:
    settings = json.load(file)


numbers = ["0", "1", "2", "3", "4", "5", "6", "7","8", "9", "10", "11", "12", "13", "14", "15","16", "17", "18", "19", "20"][::-1]
keys =    ["q", "w", "e", "r", "t", "y", "u", "a", "s", "d", "f", "g", "h", "j","z", "x", "c", "v", "b", "n", "m"][::-1]


def load_translations():
    with open(translations_path, 'r', encoding = 'utf-8') as f:
        translations = json.load(f)
        
    user_locale = settings["settings"][0]["language"]
    return lambda key: translations['languages'][key][user_locale]

_ = load_translations()

def countDown():
    print(4)
    time.sleep(1)
    print(3)
    time.sleep(1)
    print(2)
    time.sleep(1)
    print(_("starting"))

def select_window():
    global target

    windows = gw.getAllTitles()
    windows = list(set(windows))
    
    # Clear the list to show users
    recommended = ["Genshin", "Oynatıcı", "Player"] # windows where these words appear
    unwanted = ["AutoLyrePlayer", "Dosya Gezgini", "File Explorer", "Visual Studio Code"]# Dont appear these
    windows = [win for win in windows if win != ""] # Remove empty list elements

    related_windows = []
    for window in windows:
        for recommend in recommended:
            if recommend in window:
                related_windows.append(window)

    related_windows.sort()

    for item in unwanted:
        related_windows = [win for win in related_windows if item not in win]


    if related_windows == []:
        window = 0
        target = None
        
    else:
        counter = 0
        print(_("select_window"))
       
        for i in range(len(related_windows)):
            counter += 1
            print(counter, related_windows[i])
        try:
            choise = int(input(">> "))
        except Exception as e:
            print(e)
            select_window()
            return
        
        if choise == 0:
            target = None
            return countDown()
        
        else:
            target = related_windows[choise-1]
            window = gw.getWindowsWithTitle(target)[0]
        
            print(_("give_focus"))
            while gw.getActiveWindowTitle() != target:
                time.sleep(0.5)
            return target
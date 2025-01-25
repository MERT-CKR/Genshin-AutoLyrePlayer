import os
import random
import json
import time
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "1"
from pygame import mixer, time as pytime
import pygetwindow as gw

current_directory = os.getcwd()

with open(os.path.join(current_directory, "settings.json"), "r", encoding="utf-8") as file:
    settings = json.load(file)

translations_path = os.path.join(current_directory, "translations.json")


numbers = ["0", "1", "2", "3", "4", "5", "6", "7","8", "9", "10", "11", "12", "13", "14", "15","16", "17", "18", "19", "20"][::-1]
keys =    ["q", "w", "e", "r", "t", "y", "u", "a", "s", "d", "f", "g", "h", "j","z", "x", "c", "v", "b", "n", "m"][::-1]




def speak(say, sfx):
    if sfx:
        path = os.path.join(current_directory, "sounds", say)
        options = os.listdir(path)
        choise = random.choice(options)
        choise = os.path.join(path,choise)
    
        mixer.init()
        mixer.music.load(choise)
        mixer.music.play()
        
        
        while mixer.music.get_busy():
            pytime.Clock().tick(10)
        mixer.quit()


def load_translations():
    with open(translations_path, 'r', encoding='utf-8') as f:
        translations = json.load(f)
        
    user_locale = settings["settings"][0]["language"]
    return lambda key: translations['languages'][key][user_locale]

_ = load_translations

def countDown():
    print(4)
    time.sleep(1)
    print(3)
    time.sleep(1)
    print(2)
    time.sleep(1)
    print(_()("starting"))

def select_window(sfx):
    global target
    windows = gw.getAllTitles()
    windows = list(set(windows))
    windows = [win for win in windows if win != ""] # Remove empty list elements
    windows = [win for win in windows if "AutoLyrePlayer" not in win] # remove itself from list

    recommended = ["Genshin", "Oynatıcı", "Player"] # windows where these words appear

    related_windows = []

    for window in windows:
        for recommend in recommended:
            if recommend in window:
                related_windows.append(window)

    related_windows.sort()

    if related_windows == []:
        window = 0
        target = None
        
    else:
        counter = 0
        print(_()("select_window"))
       
        for i in range(len(related_windows)):
            counter += 1
            print(counter, related_windows[i])
        try:
            choise = int(input(">> "))
        except Exception as e:
            print(e)
            speak("error", sfx)
            select_window()
            return
        
        if choise == 0:
            target = None
            return countDown()
        
        else:
            target = related_windows[choise-1]
            window = gw.getWindowsWithTitle(target)[0]
        
            print(_()("give_focus"))
            while gw.getActiveWindowTitle() != target:
                time.sleep(0.5)
            speak("focused", sfx)
            return target
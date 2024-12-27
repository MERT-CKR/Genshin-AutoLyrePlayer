import time
import keyboard
import pygetwindow as gw
import os
import random

os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "1"
from pygame import mixer,time as pytime


current_directory = os.getcwd()

def speak(say, sfx):
    if sfx:
        path = os.path.join(current_directory,"sounds",say)
        options = os.listdir(path)
        choise = random.choice(options)
        choise = os.path.join(path,choise)
    
        mixer.init()
        mixer.music.load(choise)
        mixer.music.play()
        
        
        while mixer.music.get_busy():
            pytime.Clock().tick(10)
        mixer.quit()





numbers = ["0", "1", "2", "3", "4", "5", "6", "7","8", "9", "10", "11", "12", "13", "14", "15","16", "17", "18", "19", "20"][::-1]
keys =    ["q", "w", "e", "r", "t", "y", "u", "a", "s", "d", "f", "g", "h", "j","z", "x", "c", "v", "b", "n", "m"][::-1]



def countDown():
    print(4)
    time.sleep(1)
    print(3)
    time.sleep(1)
    print(2)
    time.sleep(1)
    print("Starting...")



def timer(function=0):
    global salise
    global now
    if function == 1:
        now = time.time()
        salise = int((now - int(now)) * 1000)

    else:
        elapsed_time = time.time() - now
        return salise + int(elapsed_time * 1000)


def select_window(sfx):
    global target
    windows = gw.getAllTitles()
    windows = list(set(windows))
    windows = [win for win in windows if win != ""] # Remove empty list elements
    windows = [win for win in windows if "Genshin-AutoLyrePlayer.py" not in win] # remove itself from list

    recommended = ["Genshin", "Oynatıcı", "Player"] # windows where these words appear

    related_windows = []

    for window in windows:
        for recommend in recommended:
            if recommend in window:
                related_windows.append(window)


    if related_windows == []:
        window = 0
        target = None
        
    else:
        counter = 0
        print("\nSelect the window you want to focus on")
        print("0 Continue without selection")
        for i in range(len(related_windows)):
            counter+=1
            print(counter, related_windows[i])
        try:
            choise = int(input(">> "))
        except:
            speak("error", sfx)
            select_window()
            return
        
        if choise == 0:
            target = None
            return countDown()
        
        else:
            target = related_windows[choise-1]
            window = gw.getWindowsWithTitle(target)[0]
        
            print("Give focus")
            while gw.getActiveWindowTitle() != target:
                time.sleep(0.5)
            speak("initialize", sfx)
                


def play_music(notes,sfx):
    select_window(sfx)
    Note_dict = {}

    for i in notes:
        Note_dict[i[1]] = i[0]
        
    for key,value in Note_dict.items():
        
        for x in range(0,21):
            if value == int(numbers[x]):
                Note_dict[key] = keys[x]
                

    timer(1)
    counter =0
    t1 = time.time()
    for key,value in Note_dict.items():
        counter+=1
        current_time = timer()
        while current_time < key:  # Wait for correct time
            current_time = timer()
            time.sleep(0.0005)
        
        keyboard.send(value)
        print(f"Time: {key} Key {value.capitalize()}")

        if keyboard.is_pressed('"'):
                break
        
        if target != None:
            if gw.getActiveWindowTitle() != target:
                speak("focus lost", sfx)
                break

    t2=time.time()
    playtime = round(t2-t1,1)
    print("playback duration",playtime,"second")


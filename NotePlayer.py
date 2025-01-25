import time
import keyboard
import pygetwindow as gw
import os
from common import load_translations, speak
from common import select_window
import common


_ = load_translations()
numbers = common.numbers
keys = common.keys


current_directory = os.getcwd()


def timer(function = 0):
    global salise
    global now
    if function == 1:
        now = time.time()
        salise = int((now - int(now)) * 1000)

    else:
        elapsed_time = time.time() - now
        return salise + int(elapsed_time * 1000)



def play_music(notes, sfx):

    target = select_window(sfx)
    Note_dict = {}

    for i in notes:
        Note_dict[i[1]] = i[0]
    
    for key,value in Note_dict.items():
        for i in range(len(numbers)):
            if value == int(numbers[i]):
                Note_dict[key] = keys[i]
                

    timer(1)
    counter = 0
    t1 = time.time()
    for key,value in Note_dict.items():
        counter += 1
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
                if not sfx:
                    print(_("focus_lost"))
                break

    t2=time.time()
    playtime = round(t2-t1, 1)
    print(_("playback_duration").replace("*", str(playtime)))


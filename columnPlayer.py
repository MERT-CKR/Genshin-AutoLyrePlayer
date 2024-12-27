import time
import keyboard
import pygetwindow as gw
import os
import random
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "1"
from pygame import mixer,time as pytime


current_directory = os.getcwd()


def speak(say,sfx):
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
    print("Starting... ")


def select_window(sfx):
    global target
    windows = gw.getAllTitles()
    windows = list(set(windows))
    windows = [win for win in windows if win != ""] # Remove empty list elements
    windows = [win for win in windows if "Genshin-AutoLyrePlayer.py" not in win] # remove itself from list

    recommended = ["Genshin", "Oynatıcı", "Player"]  # windows where these phrases appear

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
            print(counter,related_windows[i])
        try:
            choise = int(input(">> "))
        except:
            speak("error",sfx)
            select_window()
            return
        
        if choise == 0:
            target = None
            return countDown()
        
        else:
            target = related_windows[choise-1]
            window = gw.getWindowsWithTitle(target)[0]
        
            print("give focus")
            while gw.getActiveWindowTitle() != target:
                time.sleep(1)
                print(gw.getActiveWindowTitle(),target)
            speak("focused",sfx)


tempo_dict={
    0:1,
    1:2,
    2:4,
    3:8
}



def play_music(sheets,bpm,sfx):
    global replaced_elements

    print("bpm",bpm)#bpm: beats per minute | bps: peats per second
    bps = bpm/60
    # bps -= bps *-0.10 # %10 play speed
    wait = 1/bps
    
    select_window(sfx)
    t1 = time.time()
    
    for i in sheets:
        tempo = tempo_dict[i[0]]
        wait_among_notes = wait/tempo
        
        if i[1] == []:
            replaced_elements = "Empty Page"
        else:
            first_elements = [item[0] for item in i[1]]
            replaced_elements = [keys[numbers.index(str(elem))] if str(elem) in numbers else str(elem) for elem in first_elements]

        print(f"{replaced_elements} Tempo: {tempo}")
        print("-----------")

        if keyboard.is_pressed('"'):
            print("loop ending")
            break
        
        if target != None:
            if gw.getActiveWindowTitle() != target:
                speak("focus lost",sfx)
                break

        if "Empty Page" not in replaced_elements  :
            if len(replaced_elements) > 1:
                for char in replaced_elements:
                    keyboard.press_and_release(char)
                time.sleep(wait_among_notes)
            else:
                keyboard.press_and_release(replaced_elements[0])
                time.sleep(wait_among_notes)
        else:
            time.sleep(wait_among_notes)
    t2=time.time()
    playtime = round(t2-t1,1)
    print("playback duration",playtime,"second")

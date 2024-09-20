import time
import keyboard
import math

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


def play_music(sheets,bpm):
    global replaced_elements

    print("bpm",bpm)
    beats_per_sec = bpm/60
    beats_per_sec -= beats_per_sec *-0.19
    wait = 1/beats_per_sec
    
    countDown()
    t1 = time.time()
    
    for i in sheets:
        if i[1] == []:
            replaced_elements = "Empty Page"
        else:
            first_elements = [item[0] for item in i[1]]
            replaced_elements = [keys[numbers.index(str(elem))] if str(elem) in numbers else str(elem) for elem in first_elements]

        print(replaced_elements)
        print("-----------")

        if keyboard.is_pressed('"'):
            print("loop ending")
            break
        
        if replaced_elements != "Empty Page":
            if len(replaced_elements) > 1:
                for char in replaced_elements:
                    keyboard.press_and_release(char)
                time.sleep(wait)
            else:
                keyboard.press_and_release(replaced_elements[0])
                time.sleep(wait)
        else:
            time.sleep(wait)
    t2=time.time()
    playtime = str(t2-t1)[0:4]
    print("playback duration",playtime)

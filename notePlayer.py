import json
import time
import keyboard
import os


def timer(function="return-timer"):
    global salise
    global now
    if function == "start":
        now = time.time()
        salise = int((now - int(now)) * 1000)

    else:
        elapsed_time = time.time() - now 
        return salise + int(elapsed_time * 1000)
    
def countDown():
    print(4)
    time.sleep(1)
    print(3)
    time.sleep(1)
    print(2)
    time.sleep(1)
    print(1)

numbers = ["0", "1", "2", "3", "4", "5", "6", "7","8", "9", "10", "11", "12", "13", "14", "15","16", "17", "18", "19", "20"][::-1]
keys =    ["q", "w", "e", "r", "t", "y", "u", "a", "s", "d", "f", "g", "h", "j","z", "x", "c", "v", "b", "n", "m"][::-1]


def play_music(columns):
    countDown()
    Note_dict = {}

    for i in columns:
        Note_dict[i[1]] = i[0]
        


    for key,value in Note_dict.items():
        
        for x in range(0,21):
            if value == int(numbers[x]):
                Note_dict[key] = keys[x]
                

    timer("start")
    for key,value in Note_dict.items():
        current_time = timer()
        while current_time < key:  # Wait for correct time
            current_time = timer()
            time.sleep(0.0005)
        
        keyboard.send(value)
        print(value)

        if keyboard.is_pressed('"'):
                break



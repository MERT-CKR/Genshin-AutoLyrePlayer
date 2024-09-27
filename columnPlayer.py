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


tempo_dict={
    0:1,
    1:2,
    2:4,
    3:8
}
def play_music(sheets,bpm):
    global replaced_elements

    print("bpm",bpm)#bpm: beats per minute | bps: peats per second
    bps = bpm/60
    # bps -= bps *-0.10 # %10 play speed
    wait = 1/bps
    
    countDown()
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
    playtime = str(t2-t1)[0:4]
    print("playback duration",playtime)

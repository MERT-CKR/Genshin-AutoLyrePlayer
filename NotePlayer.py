import time
import keyboard
import pygetwindow as gw

#import module common
import common
from common import load_translations
from common import select_window
from rich.progress import Progress

_ = load_translations()
numbers = common.numbers
keys = common.keys


def timer(function = 0):
    global salise
    global now
    if function == 1:
        now = time.time()
        salise = int((now - int(now)) * 1000)

    else:
        elapsed_time = time.time() - now
        return salise + int(elapsed_time * 1000)



def play_music(notes):

    target = select_window()
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
    with Progress() as progress:
        task = progress.add_task("[cyan]Playing...", total=len(Note_dict))

        for key,value in Note_dict.items():
            counter += 1
            current_time = timer()
            while current_time < key:  # Wait for correct time
                current_time = timer()
                time.sleep(0.0005)
            
            keyboard.send(value)
            progress.console.print(f"Time: {key} Key {value.capitalize()}")

            if keyboard.is_pressed('"'):
                    break
            
            if target != None:
                if gw.getActiveWindowTitle() != target:
                    progress.console.print(_("focus_lost"))
                    break

            progress.update(task, advance=1)

    t2 = time.time()
    playtime = round(t2 - t1, 1)
    print(_("sheet_type_note"))
    print(_("playback_duration").replace("*", str(playtime)))


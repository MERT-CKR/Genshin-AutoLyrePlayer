import time
import keyboard
import pygetwindow as gw

#import module common
import common
from common import load_translations
from common import select_window
from common import print_red, print_yellow
from rich.progress import Progress

_ = load_translations()


numbers = common.numbers
keys = common.keys


tempo_dict = {
    0:1,
    1:2,
    2:4,
    3:8
}



def play_music(sheets, bpm):
    global replaced_elements
    target = select_window()


    print_yellow(f"bpm: {bpm}")
    print("\n\n\n")
    #bpm: beats per minute 
    #bps: peats per second

    bps = bpm/60
    # bps -= bps *-0.10 # %10 play speed
    wait = 1/bps
    t1 = time.time()
    with Progress() as progress:
        task = progress.add_task("[yellow]Playing...", total = len(sheets))
        for i in sheets:
            progress.update(task, advance=1)
            tempo = tempo_dict[i[0]]
            wait_among_notes = wait/tempo
            
            if i[1] == []:
                replaced_elements = "Empty Column"
            else:
                
                first_elements = [item[0] for item in i[1]]
                replaced_elements = []
                for item in first_elements:
                    item = str(item)
                    index = numbers.index(item)
                    replaced = item.replace(numbers[index], keys[index])
                    replaced_elements.append(replaced)
                    
            

            if replaced_elements == "Empty Column":
                progress.console.print("\n")
               
            else:
                if tempo >1:
                    progress.console.print(f"{replaced_elements} Tempo: {tempo}")
                else:
                    progress.console.print(f"{replaced_elements}")
            

            if keyboard.is_pressed('"'):
                print_red(_("loop_ending"))
                break
            
            if target != None:
                if gw.getActiveWindowTitle() != target:
                    print_red(_("focus_lost"))
                    break


            if "Empty Column" not in replaced_elements:
                if len(replaced_elements) > 1:
                    for char in replaced_elements:
                        keyboard.press_and_release(char)

                    time.sleep(wait_among_notes)

                else:
                    keyboard.press_and_release(replaced_elements[0])
                    time.sleep(wait_among_notes)
                    
            else:
                time.sleep(wait_among_notes)
        
    t2 = time.time()
    playtime = round(t2-t1, 1)
    print_yellow(_("sheet_type_column"))
    progress.console.print(_("playback_duration").replace("*", str(playtime)))
    progress.console.print("Bpm:", bpm,"\n")
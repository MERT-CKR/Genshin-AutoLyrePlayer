import time
import keyboard

song_notes = [{"time":400,"key":"1Key7"},{"time":1000,"key":"1Key9"},{"time":1600,"key":"1Key12"},{"time":2050,"key":"1Key7"},{"time":2500,"key":"1Key9"},{"time":2950,"key":"1Key12"},{"time":3325,"key":"1Key7"},{"time":3700,"key":"1Key9"},{"time":4075,"key":"1Key12"},{"time":4412,"key":"1Key7"},{"time":4749,"key":"1Key9"},{"time":5086,"key":"1Key12"},{"time":5423,"key":"1Key7"},{"time":5423,"key":"1Key9"},{"time":5423,"key":"1Key12"},{"time":5723,"key":"1Key7"},{"time":5723,"key":"1Key9"},{"time":5723,"key":"1Key12"},{"time":6023,"key":"1Key7"},{"time":6023,"key":"1Key9"},{"time":6023,"key":"1Key12"},{"time":6323,"key":"1Key7"},{"time":6323,"key":"1Key9"},{"time":6323,"key":"1Key12"},{"time":6623,"key":"1Key7"},{"time":6623,"key":"1Key9"},{"time":6623,"key":"1Key12"},{"time":6923,"key":"1Key7"},{"time":6923,"key":"1Key9"},{"time":6923,"key":"1Key12"},{"time":7223,"key":"1Key7"},{"time":7223,"key":"1Key9"},{"time":7223,"key":"1Key12"},{"time":7523,"key":"1Key7"},{"time":7523,"key":"1Key9"},{"time":7523,"key":"1Key12"},{"time":7823,"key":"1Key6"},{"time":7823,"key":"1Key9"},{"time":7823,"key":"1Key12"},{"time":8123,"key":"1Key6"},{"time":8123,"key":"1Key9"},{"time":8123,"key":"1Key12"},{"time":8423,"key":"1Key6"},{"time":8423,"key":"1Key9"},{"time":8423,"key":"1Key12"},{"time":8723,"key":"1Key6"},{"time":8723,"key":"1Key9"},{"time":8723,"key":"1Key11"},{"time":9023,"key":"1Key6"},{"time":9023,"key":"1Key9"},{"time":9023,"key":"1Key11"},{"time":9323,"key":"1Key6"},{"time":9323,"key":"1Key9"},{"time":9323,"key":"1Key11"},{"time":9623,"key":"1Key6"},{"time":9623,"key":"1Key9"},{"time":9623,"key":"1Key11"},{"time":9923,"key":"1Key6"},{"time":9923,"key":"1Key9"},{"time":9923,"key":"1Key11"},{"time":10223,"key":"1Key5"},{"time":10223,"key":"1Key7"},{"time":10223,"key":"1Key9"},{"time":10223,"key":"1Key12"},{"time":10523,"key":"1Key7"},{"time":10523,"key":"1Key9"},{"time":10523,"key":"1Key12"},{"time":10823,"key":"1Key7"},{"time":10823,"key":"1Key9"},{"time":10823,"key":"1Key12"},{"time":11123,"key":"1Key7"},{"time":11123,"key":"1Key9"},{"time":11123,"key":"1Key12"},{"time":11423,"key":"1Key7"},{"time":11423,"key":"1Key9"},{"time":11423,"key":"1Key12"},{"time":11723,"key":"1Key7"},{"time":11723,"key":"1Key9"},{"time":11723,"key":"1Key12"},{"time":12023,"key":"1Key6"},{"time":12023,"key":"1Key7"},{"time":12023,"key":"1Key9"},{"time":12023,"key":"1Key12"},{"time":12323,"key":"1Key7"},{"time":12323,"key":"1Key9"},{"time":12323,"key":"1Key12"},{"time":12623,"key":"1Key2"},{"time":12623,"key":"1Key6"},{"time":12623,"key":"1Key9"},{"time":12623,"key":"1Key12"},{"time":12923,"key":"1Key6"},{"time":12923,"key":"1Key9"},{"time":12923,"key":"1Key12"},{"time":13223,"key":"1Key6"},{"time":13223,"key":"1Key9"},{"time":13223,"key":"1Key12"},{"time":13523,"key":"1Key6"},{"time":13523,"key":"1Key9"},{"time":13523,"key":"1Key11"},{"time":13823,"key":"1Key6"},{"time":13823,"key":"1Key9"},{"time":13823,"key":"1Key11"},{"time":14123,"key":"1Key6"},{"time":14123,"key":"1Key9"},{"time":14123,"key":"1Key11"},{"time":14423,"key":"1Key6"},{"time":14423,"key":"1Key9"},{"time":14423,"key":"1Key11"},{"time":14723,"key":"1Key6"},{"time":14723,"key":"1Key9"},{"time":14723,"key":"1Key11"}]
oldNotes = "q w e r t a s d f g z x c v b".split()[::-1]
newNotes = "1Key0 1Key1 1Key2 1Key3 1Key4 1Key5 1Key6 1Key7 1Key8 1Key9 1Key10 1Key11 1Key12 1Key13 1Key14".split()[::-1]

def sleeper(zaman):

    while time.time() ==zaman/10000:
        pass

zaman_anahtarları = {}
for note in song_notes:
    zaman = note['time']
    anahtar = note['key']
    if zaman not in zaman_anahtarları:
        zaman_anahtarları[zaman] = [anahtar]
    else:
        zaman_anahtarları[zaman].append(anahtar)




for zaman, anahtarlar in zaman_anahtarları.items():
    # Anahtarları değiştir ve bir dizeye dönüştür
    anahtarlar_str = ' '.join(anahtarlar)
    for i in range(15):
        anahtarlar_str = anahtarlar_str.replace(newNotes[i], oldNotes[i])

    # Tuşları bas
    keys_to_press = []
    for anahtar in anahtarlar_str.split():
        keys_to_press.append(anahtar)
        if len(keys_to_press) == 3:  # Eğer 3 tuş biriktirildiyse
            keyboard.press(keys_to_press)  # 3 tuşu bas
            time.sleep(0.01)  # Tuşlar arasında bekleyin
            keyboard.release(keys_to_press)  # 3 tuşu serbest bırak
            keys_to_press = []  # Listeyi sıfırla
           

    # Eğer 3 tuş kalmışsa, onları da bas
    if keys_to_press:
        keyboard.press(keys_to_press)
        time.sleep(0.01)
        keyboard.release(keys_to_press)
    sleeper(zaman/10000)



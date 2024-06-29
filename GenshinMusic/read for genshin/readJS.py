import json
import os

numbers = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20"][::-1]
keys = ["u", "y", "t", "r", "e", "w", "q", "j", "h", "g", "f", "d", "s", "a", "m", "n", "b", "v", "c", "x", "z"][::-1]

# JSON dosyasının yolunu al
current_dir = os.getcwd()
json_path = os.path.join(current_dir, "Gigachad.genshinsheet.json")

# JSON dosyasını oku
with open(json_path, 'r', encoding='utf-8') as file:
    data = json.load(file)

# İlk öğeyi al (sizin JSON örneğinizde sadece bir öğe var gibi görünüyor)
gigachad_data = data[0]

# "columns" verisine erişim
columns_data = gigachad_data["columns"]
x=0
time=400
for i in columns_data:
    if i[1] == []:
        print("boş sayfa")
        x+=time
    else:
        # İç içe listelerdeki ilk elemanları al
        first_elements = [item[0] for item in i[1]]
        
        # İlk elemanları keys listesi ile eşleştir
        replaced_elements = [keys[numbers.index(str(elem))] if str(elem) in numbers else str(elem) for elem in first_elements]
        
        print(replaced_elements)

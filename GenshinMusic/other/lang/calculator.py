import json
import os

current_directory = os.getcwd()
jsonFilePath = os.path.join(current_directory,"translations.json")


def load_translations():
    print("select your language: \n1.Türkçe \n2.English \n3.Deutsch \n4.Japanese ")
    lang = int(input(">> "))
    if lang == 1:
        user_locale = "tr"
    elif lang == 2:
        user_locale = "en"
    elif lang == 3:
        user_locale = "de"
    elif lang == 4:
        user_locale = "ja"


    with open(jsonFilePath, 'r', encoding='utf-8') as f:
        translations = json.load(f)

    # _() lambda fonksiyonunu tanımla
    global _
    _ = lambda key: translations['languages'][key][user_locale]



def main():
    # Çevirileri yükle
    load_translations()


    def toplama(x, y):
        return int(x + y)

    def cikarma(x, y):
        return int(x - y)

    def carpma(x, y):
        return int(x * y)

    def bolme(x, y):
        if y == 0:
            return _("zero_division_error")
        else:
            if x%y==0:
                return int(x / y)
            else:
                return x/y

    print(_("operation_options"))
    print(_("addition"))
    print(_("subtraction"))
    print(_("multiplication"))
    print(_("division"))

    secim = input(_("select_operation"))

    sayi1 = float(input(_("enter_first_number")))
    sayi2 = float(input(_("enter_second_number")))

    if secim == '1':
        print(_("result"), toplama(sayi1, sayi2))
    elif secim == '2':
        print(_("result"), cikarma(sayi1, sayi2))
    elif secim == '3':
        print(_("result"), carpma(sayi1, sayi2))
    elif secim == '4':
        print(_("result"), bolme(sayi1, sayi2))
    else:
        print(_("invalid_number"))


main()


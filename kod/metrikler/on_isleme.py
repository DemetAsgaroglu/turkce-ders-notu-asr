# metrik hesabından önce metni aynı biçime getirir ve terimleri bulur
# diğer metrik betikleri bu dosyadaki fonksiyonları kullanır

import csv
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TERM_PATH = ROOT / "veri" / "sozluk" / "terimler.csv"

ONES = ["", "bir", "iki", "üç", "dört", "beş", "altı", "yedi", "sekiz", "dokuz"]
TENS = ["", "on", "yirmi", "otuz", "kırk", "elli", "altmış", "yetmiş", "seksen", "doksan"]

# terim kökünden sonra gelebilecek türkçe ekler
# ek hatası thoya girmez ama for ile format gibi kelimeler de karışmamalı
SUFFIX = re.compile(
    r"(l[ae]r)?"
    r"(ım|im|um|üm|ın|in|un|ün|ı|i|u|ü|sı|si|su|sü)?"
    r"(n?[ıiuü]n|y?[ıiuü]|y?[ae]|n?d[ae]n|n?t[ae]n|n?d[ae]|n?t[ae]|y?l[ae]|d[ıiuü]r|t[ıiuü]r)?"
    r"(ki)?"
)


# sayıyı yazıya çevirir, whisper rakam yazıyor, kılavuzda sayılar yazıyla
def number_to_words(number):
    if number == 0:
        return "sıfır"
    if number >= 1000000:
        # çok büyük sayılar rakam rakam okunur
        return " ".join(ONES[int(d)] or "sıfır" for d in str(number))

    parts = []
    thousands, rest = divmod(number, 1000)
    if thousands:
        if thousands > 1:
            parts.append(number_to_words(thousands))
        parts.append("bin")

    hundreds, rest = divmod(rest, 100)
    if hundreds:
        if hundreds > 1:
            parts.append(ONES[hundreds])
        parts.append("yüz")

    tens, ones = divmod(rest, 10)
    if tens:
        parts.append(TENS[tens])
    if ones:
        parts.append(ONES[ones])
    return " ".join(parts)


# metni küçük harfli kelime listesine çevirir
def normalize_text(text):
    # köşeli parantezli özel işaretler metne girmez
    text = re.sub(r"\[[^\]]*\]", " ", text)

    # türkçe büyük i ve ı harfleri elle çevrilir, yoksa lower yanlış sonuç verir
    text = text.replace("İ", "i").replace("I", "ı").lower()

    # set1 gibi yazımlarda harf ve rakam ayrılır, ekten önce yapılmalı
    text = re.sub(r"([a-zçğıöşü])(\d)", r"\1 \2", text)

    # 8'i gibi eki olan sayılar eki ile birleşik yazılır
    text = re.sub(r"(\d+)['’´]([a-zçğıöşü]+)", lambda m: number_to_words(int(m.group(1))) + m.group(2), text)

    # apostrof kelimeyi bölmesin, array'in arrayin olur, ´ işareti de apostrof sayılır
    text = re.sub(r"['’`´]", "", text)

    # 3.90 veya 3,90 gibi sayılar iki ayrı sayı olarak okunur
    text = re.sub(r"(\d)[.,](\d)", r"\1 \2", text)

    # 5inci gibi rakamdan sonra gelen harfler de ayrılır
    text = re.sub(r"(\d)([a-zçğıöşü])", r"\1 \2", text)

    # kalan rakamlar yazıya çevrilir
    text = re.sub(r"\d+", lambda m: " " + number_to_words(int(m.group())) + " ", text)

    # harf ve boşluk dışındaki her şey silinir
    text = re.sub(r"[^a-zçğıöşüâîû ]", " ", text)
    return text.split()


# terim sözlüğünü okur, varyantlar aynı terime bağlanır
def load_terms():
    terms = []
    with open(TERM_PATH, encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            forms = [row["terim"]] + [form for form in row["varyantlar"].split(";") if form.strip()]
            for form in forms:
                terms.append({"terim": row["terim"], "dil": row["dil"], "kelimeler": normalize_text(form)})

    # uzun terimler önce denenir, bubble sort varken sort ayrıca sayılmasın
    terms.sort(key=lambda term: -len(term["kelimeler"]))
    return terms


# kelime terimin kendisi mi ya da terim artı türkçe ek mi
def word_matches(word, stem):
    return word.startswith(stem) and SUFFIX.fullmatch(word[len(stem):]) is not None


# kelime listesinde geçen terimleri sayar
def match_terms(tokens, terms):
    found = Counter()
    position = 0

    while position < len(tokens):
        step = 1
        for term in terms:
            size = len(term["kelimeler"])
            window = tokens[position:position + size]

            # çok kelimeli terimde ek sadece son kelimeye gelir
            if len(window) == size and window[:-1] == term["kelimeler"][:-1] \
                    and word_matches(window[-1], term["kelimeler"][-1]):
                found[term["terim"]] += 1
                step = size
                break
        position += step

    return found

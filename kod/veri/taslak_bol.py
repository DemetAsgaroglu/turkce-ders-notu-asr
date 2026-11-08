# youtube altyazısını 45 saniyelik bölümlere ayırıp tsv taslağı üretir
# seçilen aralıklar konuşmanın yoğun, terimlerin sık geçtiği yerlerdir
# çıktı veri/taslak_referans/ham_tsv/<video_id>.tsv
# çalıştırma: python kod/veri/taslak_bol.py

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "veri" / "taslak_referans" / "ham"
OUTPUT_DIR = ROOT / "veri" / "taslak_referans" / "ham_tsv"

# video id: (başlangıç saniyesi, bitiş saniyesi), her biri 15 dakika
WINDOWS = {
    "lXHvHFOFric": (480, 1380),
    "7xrfiligjCo": (1320, 2220),
    "sNf0Xd01H5U": (60, 960),
    "EEFm-EhVjTk": (300, 1200),
    "xSD3j9aUPk8": (300, 1200),
}
SEGMENT_SECONDS = 45


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for video_id, (start, end) in WINDOWS.items():
        words = json.loads((RAW_DIR / f"{video_id}.json").read_text(encoding="utf-8"))

        rows = []
        for begin in range(start, end, SEGMENT_SECONDS):
            finish = begin + SEGMENT_SECONDS
            text = " ".join(word["word"] for word in words if begin <= word["start"] < finish)
            rows.append({"baslangic": begin, "bitis": finish, "cs": "", "metin": text})

        with open(OUTPUT_DIR / f"{video_id}.tsv", "w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=["baslangic", "bitis", "cs", "metin"], delimiter="\t")
            writer.writeheader()
            writer.writerows(rows)
        print(video_id, len(rows), "bölüm")


if __name__ == "__main__":
    main()

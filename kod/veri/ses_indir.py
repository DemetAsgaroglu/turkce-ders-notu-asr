# veri/lisans/videolar.csv içindeki videoların sesini indirir
# sesler veri/ses klasörüne yazılır, bu klasör depoya gönderilmez
# çalıştırma: python kod/veri/ses_indir.py

import csv
from pathlib import Path

import yt_dlp

ROOT = Path(__file__).resolve().parents[2]
VIDEO_LIST = ROOT / "veri" / "lisans" / "videolar.csv"
AUDIO_DIR = ROOT / "veri" / "ses"


# listedeki video adreslerini okur
def read_urls():
    with open(VIDEO_LIST, encoding="utf-8-sig", newline="") as file:
        return [row["url"] for row in csv.DictReader(file) if row["url"].strip()]


def main():
    AUDIO_DIR.mkdir(exist_ok=True)

    # m4a doğrudan alınır, böylece ffmpeg gerekmez
    # dosya adı video id olur, inen dosyalar tekrar indirilmez
    options = {
        "format": "bestaudio[ext=m4a]/bestaudio",
        "outtmpl": str(AUDIO_DIR / "%(id)s.%(ext)s"),
        "ignoreerrors": True,
        "overwrites": False,
        "sleep_interval": 2,
    }

    urls = read_urls()
    print(f"{len(urls)} video indirilecek")

    with yt_dlp.YoutubeDL(options) as ydl:
        ydl.download(urls)

    print(f"bitti: {AUDIO_DIR}")


if __name__ == "__main__":
    main()

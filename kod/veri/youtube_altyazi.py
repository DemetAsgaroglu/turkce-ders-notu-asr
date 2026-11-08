# referans için seçilen videoların youtube otomatik altyazısını zamanlarıyla indirir
# sonuç veri/taslak_referans/ham/<video_id>.json dosyasına yazılır
# bu metin referans değil, sadece elle düzeltmeye başlamak için taslaktır
# çalıştırma: python kod/veri/youtube_altyazi.py

import json
import time
import urllib.error
import urllib.request
from pathlib import Path

import yt_dlp

ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT / "veri" / "taslak_referans" / "ham"

# dört konuşmacıdan seçilen videolar, xSD3j9aUPk8 NEÜ kaydı anlaşılmadığı için eklendi
VIDEO_IDS = ["lXHvHFOFric", "7xrfiligjCo", "sNf0Xd01H5U", "EEFm-EhVjTk", "xSD3j9aUPk8"]

# youtube çok istekte 429 hatası veriyor, beklenip tekrar denenir
WAIT_SECONDS = 60
MAX_TRY = 5


# altyazı adresini açar, 429 gelirse bekler
def fetch_json(url):
    for attempt in range(MAX_TRY):
        try:
            with urllib.request.urlopen(url, timeout=60) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            if error.code != 429 or attempt == MAX_TRY - 1:
                raise
            print(f"429 alındı, {WAIT_SECONDS} sn bekleniyor")
            time.sleep(WAIT_SECONDS)


# json3 biçimindeki altyazıyı (saniye, kelime) listesine çevirir
def parse_words(data):
    words = []
    for event in data.get("events", []):
        start_ms = event.get("tStartMs", 0)
        for seg in event.get("segs") or []:
            text = seg.get("utf8", "").strip()
            if text and text != "[Müzik]":
                words.append({"start": round((start_ms + seg.get("tOffsetMs", 0)) / 1000, 2), "word": text})
    return words


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    options = {"quiet": True, "no_warnings": True, "skip_download": True, "ignore_no_formats_error": True}

    with yt_dlp.YoutubeDL(options) as ydl:
        for video_id in VIDEO_IDS:
            output_path = OUTPUT_DIR / f"{video_id}.json"
            if output_path.exists():
                print(f"{video_id} zaten var")
                continue

            info = ydl.extract_info("https://www.youtube.com/watch?v=" + video_id, download=False)

            # tr-orig konuşmanın kendi dilindeki otomatik altyazı, çeviri değil
            tracks = (info.get("automatic_captions") or {}).get("tr-orig") or []
            url = next((track["url"] for track in tracks if track.get("ext") == "json3"), None)
            if not url:
                print(f"{video_id} altyazı yok")
                continue

            words = parse_words(fetch_json(url))
            output_path.write_text(json.dumps(words, ensure_ascii=False), encoding="utf-8")
            print(f"{video_id} {len(words)} kelime")
            time.sleep(5)


if __name__ == "__main__":
    main()

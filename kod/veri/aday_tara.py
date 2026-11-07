# youtube'da türkçe ders videosu adaylarını tarar, video indirmez
# kanal, süre, lisans ve altyazı bilgisi veri/adaylar.csv dosyasına yazılır
# çalıştırma: python kod/veri/aday_tara.py

import csv
import time
import urllib.parse
from pathlib import Path

import yt_dlp

# youtube'da aranacak konular
QUERIES = [
    "veri yapıları dersi",
    "algoritma analizi dersi",
    "bağlı liste veri yapıları",
    "yığın kuyruk veri yapıları stack queue",
    "ikili arama ağacı binary search tree ders",
    "sıralama algoritmaları dersi",
    "nesne yönelimli programlama dersi",
    "c programlama dersi üniversite",
]

# her konu için bakılacak video sayısı
CC_LIMIT = 25
NORMAL_LIMIT = 15

# 10 dakikadan kısa videolar alınmaz
MIN_DURATION = 600

# youtube'un creative commons arama filtresi
CC_FILTER = "EgIwAQ%3D%3D"

# çıktı dosyası ve sütunları
OUTPUT_PATH = Path(__file__).resolve().parents[2] / "veri" / "adaylar.csv"
COLUMNS = ["lisans", "elle_tr_altyazi", "kanal", "sure_dk", "baslik", "url", "sorgu", "arama"]

# yt-dlp ayarları, indirme kapalı ve hatalı videolar atlanır
BASE_OPTIONS = {"quiet": True, "no_warnings": True, "ignoreerrors": True, "skip_download": True}


# arama sonucundaki video id'lerini döndürür
def search_videos(query, limit, only_cc):
    url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote(query)

    # istenirse sadece creative commons videolar aranır
    if only_cc:
        url += "&sp=" + CC_FILTER

    # extract_flat ile sadece liste alınır, video ayrıntısına girilmez
    options = {**BASE_OPTIONS, "extract_flat": True, "playlistend": limit}
    with yt_dlp.YoutubeDL(options) as ydl:
        result = ydl.extract_info(url, download=False) or {}

    return [entry["id"] for entry in result.get("entries") or [] if entry and entry.get("id")]


# tek videonun lisans ve altyazı bilgisini alır
def get_video_info(video_id):
    options = {**BASE_OPTIONS, "ignore_no_formats_error": True}
    with yt_dlp.YoutubeDL(options) as ydl:
        return ydl.extract_info("https://www.youtube.com/watch?v=" + video_id, download=False)


# video bilgisini csv satırına çevirir
def to_row(info, query, only_cc):
    # subtitles elle yazılmış altyazıları tutar, otomatik altyazılar burada olmaz
    has_manual_tr = "tr" in (info.get("subtitles") or {})

    return {
        "lisans": info.get("license") or "belirtilmemis",
        "elle_tr_altyazi": "evet" if has_manual_tr else "hayir",
        "kanal": info.get("channel") or info.get("uploader") or "",
        "sure_dk": round(info["duration"] / 60, 1),
        "baslik": info.get("title") or "",
        "url": info.get("webpage_url") or "",
        "sorgu": query,
        "arama": "cc" if only_cc else "normal",
    }


def main():
    OUTPUT_PATH.parent.mkdir(exist_ok=True)

    # aynı video farklı aramalarda çıkarsa bir kez işlenir
    seen_ids = set()

    # utf-8-sig ile excel türkçe karakterleri doğru gösterir
    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=COLUMNS)
        writer.writeheader()

        for query in QUERIES:
            # her konu önce cc filtresiyle, sonra filtresiz aranır
            for only_cc, limit in ((True, CC_LIMIT), (False, NORMAL_LIMIT)):
                for video_id in search_videos(query, limit, only_cc):
                    if video_id in seen_ids:
                        continue
                    seen_ids.add(video_id)

                    # youtube'u yormamak için istekler arasında beklenir
                    info = get_video_info(video_id)
                    time.sleep(1)

                    # bilgisi alınamayan ve kısa videolar atlanır
                    if not info or (info.get("duration") or 0) < MIN_DURATION:
                        continue

                    # satır hemen yazılır, tarama yarıda kalırsa veri kaybolmaz
                    writer.writerow(to_row(info, query, only_cc))
                    file.flush()
                    print(f"{info.get('license') or '-'} | {info.get('title')}")

    print(f"bitti: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()

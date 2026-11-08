# ses dosyalarını seçilen whisper modeliyle yazıya çevirir
# sonuç veri/asr_ciktilari/<model>/<video_id>.json dosyasına yazılır
# çalıştırma: python kod/asr/whisper_calistir.py --model small
# sadece belli videolar için: python kod/asr/whisper_calistir.py --model small --video cURUDLEvSck

import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VIDEO_LIST = ROOT / "veri" / "lisans" / "videolar.csv"
AUDIO_DIR = ROOT / "veri" / "ses"
OUTPUT_DIR = ROOT / "veri" / "asr_ciktilari"

# karşılaştırılacak üç model
MODELS = ["small", "medium", "large-v3"]

# üç modelde de aynı ayarlar kullanılır, fark sadece modelden gelsin
# float16 ile large-v3 de 8 gb karta sığar
COMPUTE_TYPE = "float16"
SETTINGS = {
    "language": "tr",
    "beam_size": 5,
    # sessiz yerlerde uydurma metin üretmesin diye
    "vad_filter": True,
    # altın transkriptin zaman aralıklarıyla eşleştirmek için kelime zamanı gerekiyor
    "word_timestamps": True,
    # uzun derslerde aynı cümleyi tekrar etmeye girmesin diye
    "condition_on_previous_text": False,
}


# windows'ta gpu kütüphanelerinin yeri bulunur, yoksa whisper gpu'yu açamaz
def add_gpu_libraries():
    nvidia_dir = Path(sys.prefix) / "Lib" / "site-packages" / "nvidia"
    folders = {dll.parent for pattern in ("cublas64_*.dll", "cudnn64_*.dll") for dll in nvidia_dir.rglob(pattern)}
    for folder in folders:
        os.environ["PATH"] = str(folder) + os.pathsep + os.environ["PATH"]


# listedeki video id'lerini okur
def read_video_ids():
    with open(VIDEO_LIST, encoding="utf-8-sig", newline="") as file:
        return [row["video_id"] for row in csv.DictReader(file)]


# tek videoyu yazıya çevirir, ses süresi ve segmentleri döndürür
def transcribe(model, audio_path):
    segments, info = model.transcribe(str(audio_path), **SETTINGS)

    # segments bir generator, asıl çeviri bu döngüde yapılır
    rows = []
    for segment in segments:
        words = [
            {"start": round(word.start, 2), "end": round(word.end, 2), "word": word.word}
            for word in segment.words or []
        ]
        rows.append({
            "start": round(segment.start, 2),
            "end": round(segment.end, 2),
            "text": segment.text.strip(),
            "words": words,
        })

    return info.duration, rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True, choices=MODELS)
    parser.add_argument("--video", nargs="*", help="sadece bu video id'leri, verilmezse hepsi")
    args = parser.parse_args()

    # kütüphane yolu whisper yüklenmeden önce eklenmeli
    add_gpu_libraries()
    from faster_whisper import WhisperModel

    model_dir = OUTPUT_DIR / args.model
    model_dir.mkdir(parents=True, exist_ok=True)

    # model ilk çalıştırmada internetten iner
    print(f"model yükleniyor: {args.model}")
    model = WhisperModel(args.model, device="cuda", compute_type=COMPUTE_TYPE)

    video_ids = args.video or read_video_ids()
    for index, video_id in enumerate(video_ids, start=1):
        output_path = model_dir / f"{video_id}.json"

        # biten video tekrar çevrilmez, işlem yarıda kalırsa kaldığı yerden devam eder
        if output_path.exists():
            print(f"[{index}/{len(video_ids)}] {video_id} zaten var, atlandı")
            continue

        audio_path = AUDIO_DIR / f"{video_id}.m4a"
        if not audio_path.exists():
            print(f"[{index}/{len(video_ids)}] {video_id} ses dosyası yok, atlandı")
            continue

        started = time.time()
        duration, rows = transcribe(model, audio_path)
        elapsed = time.time() - started

        result = {
            "video_id": video_id,
            "model": args.model,
            "compute_type": COMPUTE_TYPE,
            "settings": SETTINGS,
            "duration_sec": round(duration, 1),
            "elapsed_sec": round(elapsed, 1),
            "segments": rows,
        }

        # önce geçici dosyaya yazılır, yarım kalan dosya bitmiş sanılmasın
        temp_path = output_path.with_suffix(".tmp")
        with open(temp_path, "w", encoding="utf-8") as file:
            json.dump(result, file, ensure_ascii=False)
        temp_path.replace(output_path)

        # hız: 1 dakikada kaç dakikalık ses çevrildi
        speed = duration / max(elapsed, 1)
        print(f"[{index}/{len(video_ids)}] {video_id} {duration / 60:.1f} dk ses, {elapsed / 60:.1f} dk sürdü, {speed:.1f}x")

    print(f"bitti: {model_dir}")


if __name__ == "__main__":
    main()

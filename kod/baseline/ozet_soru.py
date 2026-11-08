# referanstan ve whisper çıktılarından aynı model ve aynı promptla özet ve soru üretir
# llm bilgisayarda çalışır, internete metin gönderilmez, model ilk çalıştırmada iner
# sonuç sonuclar/<referans>/baseline/<kaynak>/<video_id>_<baslangic>.json dosyasına yazılır
# çalıştırma: python kod/baseline/ozet_soru.py --referans taslak

import argparse
import json
import sys
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "kod" / "metrikler"))

from hesapla import ASR_DIR, MODELS, REFERENCE_DIRS, read_reference, words_in_range

LLM_MODEL = "Qwen/Qwen3-4B"

# örnekleme kapalı, aynı girdi aynı çıktıyı verir
MAX_NEW_TOKENS = 500

# bir parça en fazla 10 bölüm yani 7.5 dakika, 4 bölümden kısası alınmaz
MAX_SEGMENTS = 10
MIN_SEGMENTS = 4
SEGMENT_SECONDS = 45

SUMMARY_PROMPT = """Aşağıda bir üniversite dersinin konuşma metni var. Metin otomatik yazıya çevrildiği için hatalar içerebilir.
Bu bölümü Türkçe olarak en fazla 5 cümleyle özetle. Dersin teknik terimlerini koru. Sadece özeti yaz.

Metin:
{text}"""

QUESTION_PROMPT = """Aşağıda bir üniversite dersinin konuşma metni var. Metin otomatik yazıya çevrildiği için hatalar içerebilir.
Bu bölümde anlatılan kavramları ölçen 3 Türkçe sınav sorusu yaz. Konuşmacının cümlelerini kopyalama, kavramı sor. Her soru tek satır olsun ve soru işaretiyle bitsin. Cevap yazma. Sadece soruları yaz.

Metin:
{text}"""


# model 4 bit ile yüklenir, böylece 8 gb karta sığar
def load_llm():
    tokenizer = AutoTokenizer.from_pretrained(LLM_MODEL)
    settings = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.float16, bnb_4bit_quant_type="nf4")
    model = AutoModelForCausalLM.from_pretrained(LLM_MODEL, quantization_config=settings, device_map="cuda")
    return tokenizer, model


# modele prompt verip cevabı döndürür
def ask_llm(llm, prompt):
    tokenizer, model = llm

    # düşünme kısmı kapatılır, sadece cevap üretilsin
    text = tokenizer.apply_chat_template(
        [{"role": "user", "content": prompt}], tokenize=False, add_generation_prompt=True, enable_thinking=False
    )
    inputs = tokenizer(text, return_tensors="pt").to(model.device)

    with torch.no_grad():
        output = model.generate(**inputs, max_new_tokens=MAX_NEW_TOKENS, do_sample=False)

    # girdi kısmı atılır, sadece yeni üretilen metin çözülür
    answer = tokenizer.decode(output[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
    return answer.replace("<think>", "").replace("</think>", "").strip()


# art arda gelen bölümleri 5-10 dakikalık parçalarda birleştirir
def build_chunks(segments):
    chunks, current = [], []

    for segment in segments:
        # araya elenen bölüm girdiyse yeni parçaya geçilir
        is_gap = current and float(segment["baslangic"]) != float(current[-1]["baslangic"]) + SEGMENT_SECONDS
        if is_gap or len(current) == MAX_SEGMENTS:
            chunks.append(current)
            current = []
        current.append(segment)
    chunks.append(current)

    return [chunk for chunk in chunks if len(chunk) >= MIN_SEGMENTS]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--referans", required=True, choices=list(REFERENCE_DIRS))
    args = parser.parse_args()

    output_root = ROOT / "sonuclar" / args.referans / "baseline"
    llm = load_llm()

    for reference_path in sorted(REFERENCE_DIRS[args.referans].glob("*.tsv")):
        video_id = reference_path.stem

        # whisper çıktıları bir kere okunur
        model_words = {}
        for model in MODELS:
            data = json.loads((ASR_DIR / model / f"{video_id}.json").read_text(encoding="utf-8"))
            model_words[model] = [word for segment in data["segments"] for word in segment["words"]]

        for chunk in build_chunks(read_reference(reference_path)):
            start, end = float(chunk[0]["baslangic"]), float(chunk[-1]["bitis"])

            # aynı parçanın referans ve üç whisper metni
            sources = {"referans": " ".join(segment["metin"] for segment in chunk)}
            for model in MODELS:
                sources[model] = words_in_range(model_words[model], start, end)

            for source, text in sources.items():
                output_path = output_root / source / f"{video_id}_{int(start)}.json"

                # biten parça tekrar üretilmez
                if output_path.exists():
                    continue
                output_path.parent.mkdir(parents=True, exist_ok=True)

                result = {
                    "video_id": video_id,
                    "baslangic": start,
                    "bitis": end,
                    "kaynak": source,
                    "llm": LLM_MODEL,
                    "max_new_tokens": MAX_NEW_TOKENS,
                    "ozet": ask_llm(llm, SUMMARY_PROMPT.format(text=text)),
                    "sorular": ask_llm(llm, QUESTION_PROMPT.format(text=text)),
                }
                output_path.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
                print(f"{video_id} {int(start)} {source} tamam")

    print("bitti")


if __name__ == "__main__":
    main()

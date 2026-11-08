# whisper metninden üretilen özet ve soruları referans metninden üretilenlerle karşılaştırır
# rouge türkçe metinde kendi kelime ayırıcımızla hesaplanır
# sonuç sonuclar/<referans>/baseline_ozet.csv dosyasına yazılır
# çalıştırma: python kod/baseline/degerlendir.py --referans taslak

import argparse
import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "kod" / "metrikler"))

from hesapla import MODELS
from on_isleme import load_terms, match_terms, normalize_text


# n'li kelime gruplarının kesişiminden f1 hesaplar
def rouge_f1(reference, candidate, size):
    reference_grams = Counter(tuple(reference[i:i + size]) for i in range(len(reference) - size + 1))
    candidate_grams = Counter(tuple(candidate[i:i + size]) for i in range(len(candidate) - size + 1))
    overlap = sum((reference_grams & candidate_grams).values())

    if not overlap:
        return 0.0
    precision = overlap / sum(candidate_grams.values())
    recall = overlap / sum(reference_grams.values())
    return 2 * precision * recall / (precision + recall)


# cevabı satırlara bölüp soru işaretiyle bitenleri alır
def split_questions(text):
    lines = [re.sub(r"^\s*[\d\-*.)]+\s*", "", line).strip() for line in text.splitlines()]
    return [line for line in lines if line.endswith("?")]


# referans özetindeki terimlerin kaçı whisper özetinde de var
def term_retention(reference_terms, candidate_terms):
    total = sum(reference_terms.values())
    kept = sum(min(count, candidate_terms[term]) for term, count in reference_terms.items())
    return kept, total


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--referans", required=True)
    args = parser.parse_args()

    root = ROOT / "sonuclar" / args.referans
    terms = load_terms()

    rows = []
    for reference_path in sorted((root / "baseline" / "referans").glob("*.json")):
        reference = json.loads(reference_path.read_text(encoding="utf-8"))
        reference_summary = normalize_text(reference["ozet"])
        reference_questions = [normalize_text(question) for question in split_questions(reference["sorular"])]
        reference_terms = match_terms(reference_summary, terms)

        for model in MODELS:
            path = root / "baseline" / model / reference_path.name
            candidate = json.loads(path.read_text(encoding="utf-8"))
            candidate_summary = normalize_text(candidate["ozet"])
            questions = split_questions(candidate["sorular"])

            # her whisper sorusu için referans sorularından en benzeri bulunur
            question_scores = [
                max((rouge_f1(item, normalize_text(question), 1) for item in reference_questions), default=0)
                for question in questions
            ]
            kept, total = term_retention(reference_terms, match_terms(candidate_summary, terms))

            rows.append({
                "model": model,
                "parca": reference_path.stem,
                "rouge1": rouge_f1(reference_summary, candidate_summary, 1),
                "rouge2": rouge_f1(reference_summary, candidate_summary, 2),
                "terim_kept": kept,
                "terim_toplam": total,
                "soru_sayisi": len(questions),
                "soru_benzerlik": sum(question_scores) / len(question_scores) if question_scores else 0,
            })

    with open(root / "baseline_parca.csv", "w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    # model başına ortalamalar
    table = []
    for model in MODELS:
        group = [row for row in rows if row["model"] == model]
        table.append({
            "model": model,
            "parca": len(group),
            "rouge1": sum(row["rouge1"] for row in group) / len(group),
            "rouge2": sum(row["rouge2"] for row in group) / len(group),
            "terim_koruma": sum(row["terim_kept"] for row in group) / max(sum(row["terim_toplam"] for row in group), 1),
            "soru_sayisi": sum(row["soru_sayisi"] for row in group) / len(group),
            "soru_benzerlik": sum(row["soru_benzerlik"] for row in group) / len(group),
        })

    with open(root / "baseline_ozet.csv", "w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(table[0].keys()))
        writer.writeheader()
        writer.writerows(table)

    print(table)


if __name__ == "__main__":
    main()

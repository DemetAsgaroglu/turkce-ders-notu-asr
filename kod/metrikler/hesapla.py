# referans ile whisper çıktılarını karşılaştırıp wer, cer ve tho hesaplar
# bölüm sonuçları, özet tablolar ve terim hataları sonuclar/<referans>/ altına yazılır
# altın transkript bitince: python kod/metrikler/hesapla.py --referans altin
# taslak için: python kod/metrikler/hesapla.py --referans taslak

import argparse
import csv
import json
import random
from collections import Counter

from on_isleme import ROOT, load_terms, match_terms, normalize_text

MODELS = ["small", "medium", "large-v3"]
ASR_DIR = ROOT / "veri" / "asr_ciktilari"
VIDEO_LIST = ROOT / "veri" / "lisans" / "videolar.csv"
REFERENCE_DIRS = {"altin": ROOT / "veri" / "altin_transkript", "taslak": ROOT / "veri" / "taslak_referans"}

# güven aralığı için kaç kez yeniden örnekleme yapılacak
BOOTSTRAP_COUNT = 2000
SEED = 42


# iki dizi arasındaki s, d, i sayılarını ve eşleşen çiftleri döndürür
def edit_operations(reference, hypothesis):
    rows, cols = len(reference) + 1, len(hypothesis) + 1

    # tablonun ilk satır ve sütunu sadece silme ve ekleme maliyeti
    table = [[0] * cols for _ in range(rows)]
    for i in range(rows):
        table[i][0] = i
    for j in range(cols):
        table[0][j] = j

    for i in range(1, rows):
        for j in range(1, cols):
            cost = 0 if reference[i - 1] == hypothesis[j - 1] else 1
            table[i][j] = min(table[i - 1][j - 1] + cost, table[i - 1][j] + 1, table[i][j - 1] + 1)

    # tablonun sonundan başa dönülerek hata türleri sayılır
    substitutions = deletions = insertions = 0
    pairs = []
    i, j = rows - 1, cols - 1
    while i > 0 or j > 0:
        if i > 0 and j > 0 and table[i][j] == table[i - 1][j - 1] + (reference[i - 1] != hypothesis[j - 1]):
            if reference[i - 1] != hypothesis[j - 1]:
                substitutions += 1
                pairs.append((reference[i - 1], hypothesis[j - 1]))
            i, j = i - 1, j - 1
        elif i > 0 and table[i][j] == table[i - 1][j] + 1:
            deletions += 1
            pairs.append((reference[i - 1], ""))
            i -= 1
        else:
            insertions += 1
            j -= 1

    return substitutions, deletions, insertions, pairs


# referans dosyasını okur, güveni düşük ve işaretli bölümler ölçüme girmez
def read_reference(path):
    with open(path, encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file, delimiter="\t"))

    kept = []
    for row in rows:
        if row.get("guven", "yuksek") == "dusuk":
            continue
        if "[anlaşılmıyor]" in row["metin"] or "[öğrenci]" in row["metin"]:
            continue
        kept.append(row)
    return kept


# whisper çıktısından verilen aralıktaki kelimeleri alır
def words_in_range(words, start, end):
    return " ".join(word["word"].strip() for word in words if start <= word["start"] < end)


# bir grup satırdan toplam oranları hesaplar
def summarize(rows):
    words = sum(row["kelime"] for row in rows)
    chars = sum(row["karakter"] for row in rows)
    terms = sum(row["terim"] for row in rows)
    term_en = sum(row["terim_en"] for row in rows)
    term_tr = sum(row["terim_tr"] for row in rows)
    return {
        "bolum": len(rows),
        "kelime": words,
        "terim": terms,
        "wer": sum(row["s"] + row["d"] + row["i"] for row in rows) / words if words else 0,
        "cer": sum(row["cer_hata"] for row in rows) / chars if chars else 0,
        "tho": sum(row["terim_hata"] for row in rows) / terms if terms else 0,
        "tho_en": sum(row["terim_hata_en"] for row in rows) / term_en if term_en else 0,
        "tho_tr": sum(row["terim_hata_tr"] for row in rows) / term_tr if term_tr else 0,
    }


# bölümleri yeniden örnekleyerek bir istatistiğin %95 aralığını bulur
def bootstrap(rows, statistic):
    generator = random.Random(SEED)
    values = sorted(
        statistic([generator.choice(rows) for _ in rows]) for _ in range(BOOTSTRAP_COUNT)
    )
    return values[int(0.025 * BOOTSTRAP_COUNT)], values[int(0.975 * BOOTSTRAP_COUNT)]


# csv yazma işlemini tek yerde toplar
def write_csv(path, rows):
    with open(path, "w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--referans", required=True, choices=list(REFERENCE_DIRS))
    args = parser.parse_args()

    output_dir = ROOT / "sonuclar" / args.referans
    output_dir.mkdir(parents=True, exist_ok=True)

    terms = load_terms()
    language = {term["terim"]: term["dil"] for term in terms}

    with open(VIDEO_LIST, encoding="utf-8-sig", newline="") as file:
        videos = {row["video_id"]: row for row in csv.DictReader(file)}

    rows = []
    term_mistakes = Counter()

    for reference_path in sorted(REFERENCE_DIRS[args.referans].glob("*.tsv")):
        video_id = reference_path.stem
        segments = read_reference(reference_path)

        for model in MODELS:
            data = json.loads((ASR_DIR / model / f"{video_id}.json").read_text(encoding="utf-8"))
            words = [word for segment in data["segments"] for word in segment["words"]]

            for segment in segments:
                start, end = float(segment["baslangic"]), float(segment["bitis"])
                reference = normalize_text(segment["metin"])
                hypothesis = normalize_text(words_in_range(words, start, end))
                if not reference:
                    continue

                # kelime düzeyinde hata
                s, d, i, pairs = edit_operations(reference, hypothesis)

                # karakter düzeyinde hata, boşluklar da karakter sayılır
                reference_chars, hypothesis_chars = " ".join(reference), " ".join(hypothesis)
                cs_, cd, ci, _ = edit_operations(reference_chars, hypothesis_chars)

                # terim düzeyinde hata, ingilizce ve türkçe ayrı tutulur
                # eksik veya yanlış yazılan terim hatadır, fazladan yazılan thoya girmez
                reference_terms = match_terms(reference, terms)
                hypothesis_terms = match_terms(hypothesis, terms)
                errors = {term: max(count - hypothesis_terms[term], 0) for term, count in reference_terms.items()}

                # hangi terimin neye dönüştüğü örnek olarak saklanır
                if model == "large-v3":
                    for wrong, written in pairs:
                        # index ile indeks gibi aynı terimin varyantları hata sayılmaz
                        if match_terms([wrong], terms) and match_terms([wrong], terms) != match_terms([written], terms):
                            term_mistakes[(wrong, written)] += 1

                rows.append({
                    "model": model,
                    "video_id": video_id,
                    "kanal": videos[video_id]["kanal"],
                    "ayrim": videos[video_id]["ayrim"],
                    "baslangic": start,
                    "bitis": end,
                    "cs": segment["cs"],
                    "kelime": len(reference),
                    "s": s,
                    "d": d,
                    "i": i,
                    "karakter": len(reference_chars),
                    "cer_hata": cs_ + cd + ci,
                    "terim": sum(reference_terms.values()),
                    "terim_hata": sum(errors.values()),
                    "terim_en": sum(c for t, c in reference_terms.items() if language[t] == "en"),
                    "terim_hata_en": sum(c for t, c in errors.items() if language[t] == "en"),
                    "terim_tr": sum(c for t, c in reference_terms.items() if language[t] == "tr"),
                    "terim_hata_tr": sum(c for t, c in errors.items() if language[t] == "tr"),
                })

    write_csv(output_dir / "bolum_sonuclari.csv", rows)

    # genel tablo, test ve geliştirme konuşmacıları da ayrı verilir
    table = []
    for model in MODELS:
        model_rows = [row for row in rows if row["model"] == model]
        groups = {"tum": model_rows}
        for ayrim in ("gelistirme", "test"):
            groups[ayrim] = [row for row in model_rows if row["ayrim"] == ayrim]
        for kanal in sorted({row["kanal"] for row in model_rows}):
            groups[kanal] = [row for row in model_rows if row["kanal"] == kanal]
        for name, group in groups.items():
            if group:
                table.append({"model": model, "grup": name, **summarize(group)})
    write_csv(output_dir / "ozet.csv", table)

    # h1 üç şekilde bakılır
    # 1) cs etiketli ve etiketsiz bölümler, 2) aynı bölümlerde ingilizce ve türkçe terimler
    # 3) ingilizce terim yoğunluğu yüksek ve düşük bölümler
    # 45 sn'lik bölümlerin çoğunda ingilizce terim olduğu için tek başına ilki yetmeyebilir
    h1 = []
    for model in MODELS:
        model_rows = [row for row in rows if row["model"] == model]
        with_cs = [row for row in model_rows if row["cs"] == "var"]
        without_cs = [row for row in model_rows if row["cs"] == "yok"]

        # ingilizce ve türkçe terim farkı
        def language_gap(sample):
            summary = summarize(sample)
            return summary["tho_en"] - summary["tho_tr"]

        # yoğunluk: bölümdeki ingilizce terim sayısı bölü kelime sayısı, ortancaya göre ayrılır
        def split_by_density(sample):
            densities = sorted(row["terim_en"] / row["kelime"] for row in sample)
            middle = densities[len(densities) // 2]
            dense = [row for row in sample if row["terim_en"] / row["kelime"] >= middle]
            sparse = [row for row in sample if row["terim_en"] / row["kelime"] < middle]
            return dense, sparse

        def density_gap(sample):
            dense, sparse = split_by_density(sample)
            return summarize(dense)["tho"] - summarize(sparse)["tho"]

        dense, sparse = split_by_density(model_rows)
        language_low, language_high = bootstrap(model_rows, language_gap)
        density_low, density_high = bootstrap(model_rows, density_gap)

        h1.append({
            "model": model,
            "cs_var_bolum": len(with_cs),
            "cs_yok_bolum": len(without_cs),
            "tho_cs_var": summarize(with_cs)["tho"],
            "tho_cs_yok": summarize(without_cs)["tho"],
            "tho_en": summarize(model_rows)["tho_en"],
            "tho_tr": summarize(model_rows)["tho_tr"],
            "dil_farki": language_gap(model_rows),
            "dil_farki_alt": language_low,
            "dil_farki_ust": language_high,
            "tho_yogun": summarize(dense)["tho"],
            "tho_seyrek": summarize(sparse)["tho"],
            "yogunluk_farki": density_gap(model_rows),
            "yogunluk_farki_alt": density_low,
            "yogunluk_farki_ust": density_high,
        })
    write_csv(output_dir / "h1.csv", h1)

    # h2: small'dan large'a göreli iyileşme, wer ile tho karşılaştırılır
    key = lambda row: (row["video_id"], row["baslangic"])
    small = {key(row): row for row in rows if row["model"] == "small"}
    large = {key(row): row for row in rows if row["model"] == "large-v3"}
    pairs_of_rows = [(small[k], large[k]) for k in small if k in large]

    def improvement(sample):
        small_summary = summarize([pair[0] for pair in sample])
        large_summary = summarize([pair[1] for pair in sample])
        wer = (small_summary["wer"] - large_summary["wer"]) / small_summary["wer"] if small_summary["wer"] else 0
        tho = (small_summary["tho"] - large_summary["tho"]) / small_summary["tho"] if small_summary["tho"] else 0
        return wer, tho

    wer_gain, tho_gain = improvement(pairs_of_rows)
    low, high = bootstrap(pairs_of_rows, lambda sample: improvement(sample)[0] - improvement(sample)[1])
    write_csv(output_dir / "h2.csv", [{
        "wer_iyilesme": wer_gain,
        "tho_iyilesme": tho_gain,
        "fark": wer_gain - tho_gain,
        "fark_alt": low,
        "fark_ust": high,
    }])

    # en sık yapılan terim hataları
    mistakes = [{"referans": wrong, "whisper": written, "adet": count} for (wrong, written), count in term_mistakes.most_common(40)]
    if mistakes:
        write_csv(output_dir / "terim_hatalari.csv", mistakes)

    print(f"bitti: {output_dir}, {len(rows)} satır")


if __name__ == "__main__":
    main()

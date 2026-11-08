# referans tsv dosyalarının cs sütununu terim sözlüğüne göre otomatik doldurur
# bölümde sözlükteki ingilizce terim geçiyorsa var, geçmiyorsa yok yazar
# altın transkriptte bu etiket dinlerken elle kontrol edilir
# çalıştırma: python kod/veri/cs_etiketle.py veri/taslak_referans

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "kod" / "metrikler"))

from on_isleme import load_terms, match_terms, normalize_text


def main():
    folder = ROOT / sys.argv[1]
    terms = [term for term in load_terms() if term["dil"] == "en"]

    for path in sorted(folder.glob("*.tsv")):
        with open(path, encoding="utf-8", newline="") as file:
            rows = list(csv.DictReader(file, delimiter="\t"))

        for row in rows:
            tokens = normalize_text(row["metin"])
            row["cs"] = "var" if match_terms(tokens, terms) else "yok"

        with open(path, "w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()), delimiter="\t")
            writer.writeheader()
            writer.writerows(rows)

        count = sum(row["cs"] == "var" for row in rows)
        print(f"{path.name}: {len(rows)} bölüm, {count} cs=var")


if __name__ == "__main__":
    main()

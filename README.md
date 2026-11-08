# Türkçe Ders Kayıtlarından Otomatik Ders Notu Üretimi

Konuşma tanıma hatalarının özet ve soru üretimine yayılımını inceleyen NLP 2 dönem projesi.

Ders kaydının sesi Whisper ile yazıya çevrilir, bu yazıdan LLM ile özet ve soru üretilir. Projede Whisper'ın yaptığı hataların, özellikle teknik terim hatalarının, bu çıktıları ne kadar etkilediği ölçülür.

## Klasör yapısı

```
kod/
  veri/        video tarama ve indirme
  asr/         Whisper ile yazıya çevirme
  metrikler/   WER, CER ve THO hesabı
  baseline/    özet ve soru üretimi
veri/
  lisans/            video listesi ve lisans bilgileri
  sozluk/            terim sözlükleri
  altin_transkript/  elle kontrol edilmiş transkriptler
  asr_ciktilari/     Whisper çıktıları
sonuclar/      metrik tabloları
rapor/         IEEE raporu
```

Ses dosyaları depoda tutulmaz, indirme betiğiyle alınır.

## Kurulum

PyTorch CUDA sürümü kendi adresinden kurulur, sonra diğer paketler kurulur. NVIDIA GPU gerekir, deneyler RTX 4060 (8 GB) üzerinde yapıldı.

```
python -m venv venv
venv\Scripts\python.exe -m pip install torch==2.14.1 --index-url https://download.pytorch.org/whl/cu126
venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Çalıştırma

Aday videoları taramak için (video indirmez, sonucu `veri/adaylar.csv` dosyasına yazar):

```
python kod/veri/aday_tara.py
```

Seçilen videoların sesini indirmek için (`veri/lisans/videolar.csv` listesini kullanır):

```
python kod/veri/ses_indir.py
```

Sesleri Whisper ile yazıya çevirmek için (NVIDIA GPU gerekir, model ilk çalıştırmada iner):

```
python kod/asr/whisper_calistir.py --model small
python kod/asr/whisper_calistir.py --model medium
python kod/asr/whisper_calistir.py --model large-v3
```

Taslak referansı hazırlamak için (YouTube altyazısını indirir ve 45 saniyelik bölümlere ayırır):

```
python kod/veri/youtube_altyazi.py
python kod/veri/taslak_bol.py
```

Bölümlerin `cs` etiketini terim sözlüğüne göre doldurmak için:

```
python kod/veri/cs_etiketle.py veri/taslak_referans
```

WER, CER ve THO hesabı için (sonuçlar `sonuclar/` altına yazılır):

```
python kod/metrikler/hesapla.py --referans altin
```

Özet ve soru üretip değerlendirmek için (LLM bilgisayarda çalışır):

```
python kod/baseline/ozet_soru.py --referans altin
python kod/baseline/degerlendir.py --referans altin
```

## Referans durumu

`veri/altin_transkript/` sesi dinlenerek elle düzeltilmiş 1 saatlik altın transkripttir: Murat Özalp (lXHvHFOFric, geliştirme), Berk Bayar (EEFm-EhVjTk, xSD3j9aUPk8, test) ve Recai Oktaş'tan (7xrfiligjCo, test) 15'er dakika, 80 bölüm × 45 saniye. NEÜ kaydı dinlenerek de güvenilir biçimde yazılamadığı için altın transkripte alınmamıştır.

`veri/taslak_referans/` altın transkript değildir. YouTube otomatik altyazısından gelir ve sesi dinlenmeden bağlamdan düzeltilmiştir. `sonuclar/taslak/` yalnızca işlem hattının sınanması için tutulur; raporda kullanılan değerler `sonuclar/altin/` altındadır.

## Altın transkript sonuçları

| Model | WER | CER | THO | THO İngilizce | THO Türkçe |
|---|---|---|---|---|---|
| small | %20,0 | %7,4 | %13,4 | %21,9 | %7,8 |
| medium | %15,5 | %6,1 | %8,7 | %15,2 | %4,4 |
| large-v3 | %14,9 | %6,4 | %7,1 | %13,1 | %3,1 |

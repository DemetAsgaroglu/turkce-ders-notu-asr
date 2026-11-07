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

```
pip install -r requirements.txt
```

## Çalıştırma

Aday videoları taramak için (video indirmez, sonucu `veri/adaylar.csv` dosyasına yazar):

```
python kod/veri/aday_tara.py
```

Diğer adımlar tamamlandıkça buraya eklenecek.

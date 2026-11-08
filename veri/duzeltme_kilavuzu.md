# Düzeltme Kılavuzu

Altın transkript, kayıtta söylenenin yazıya geçirilmiş referans halidir. Tüm kayıtlar aynı kurallarla hazırlanır, böylece hata oranları karşılaştırılabilir olur.

## Temel kural

Söylenen yazılır, söylenmesi gereken değil. Konuşmacının dil bilgisi hatası düzeltilmez, cümle güzelleştirilmez.

## Dolgu sesleri ve tekrarlar

| Durum | Kural | Söylenen | Yazılan |
|---|---|---|---|
| Dolgu sesi | Yazılmaz | "ee dizinin ıı boyutu" | dizinin boyutu |
| Yarım kalan kelime | Yazılmaz | "ar- array'in" | array'in |
| Tam tekrar | Yazılır | "bu bu fonksiyon" | bu bu fonksiyon |

## Sayılar

Sayılar söylendiği gibi yazıyla yazılır: "üç eleman", "yüz yirmi". Metrik hesabından önce Whisper çıktısındaki rakamlar da yazıya çevrilir.

## İngilizce terimler

- Özgün yazımıyla yazılır, ek apostrofla ayrılır: `array'in`, `stack'e`, `pointer'ı`.
- Türkçeleşmiş kelimeler Türkçe yazılır: `fonksiyon`, `algoritma`, `program`.
- İki yazımı da yaygın olanlar terim sözlüğünde varyant olarak tanımlanır: `index` ve `indeks`.
- İngilizce fiil kalıpları ayrı yazılır: `call ediyoruz`, `push ediyoruz`.

## Kod ve semboller

Okunduğu gibi yazılır: `i artı artı`, `n kare`, `o n log n`. Kısaltmalar söylenen biçimiyle büyük harfle yazılır: `CPU`, `RAM`.

## Noktalama

Cümle sonuna nokta konur. Metrik hesabında noktalama, apostrof ve büyük harf etkisi ön işlemle kaldırılır.

## Özel işaretler

| İşaret | Anlamı | Ölçüme etkisi |
|---|---|---|
| `[anlaşılmıyor]` | Dinlenip çözülemeyen kısım | Bölüm ölçümden çıkarılır |
| `[öğrenci]` | Öğrenci konuşması | Bölüm ölçümden çıkarılır |
| `[konuşma yok]` | Uzun sessizlik veya yazı yazma | Metne girmez |

## Çalışma sırası

1. Başlangıç metni `veri/taslak_referans/<video_id>.tsv` dosyasıdır. Bu metin YouTube otomatik altyazısından gelir ve sesi dinlenmeden yalnızca bağlamdan düzeltilmiştir, bu yüzden altın sayılmaz. Dosya `veri/altin_transkript/` klasörüne kopyalanarak çalışılır.
2. Kayıt baştan sona dinlenir ve metin bu kurallara göre düzeltilir.
3. Terimlerin geçtiği yerler ikinci kez dinlenir.
4. Whisper çıktısına bakarak düzeltme yapılmaz, çünkü referans değerlendirilen sistemden etkilenmemelidir.

## Dosya biçimi

Her video için `veri/altin_transkript/<video_id>.tsv` dosyası hazırlanır. Her satır 30-60 saniyelik bir bölümdür:

| Sütun | Açıklama | Örnek |
|---|---|---|
| `baslangic` | Başlangıç saniyesi | 120.0 |
| `bitis` | Bitiş saniyesi | 165.5 |
| `cs` | İngilizce kelime varsa `var`, yoksa `yok` | var |
| `guven` | Taslakta bağlamdan düzeltmenin güveni. Dinlenip düzeltilen satırda `yuksek` yapılır | yuksek |
| `metin` | Altın metin | array'in boyutunu tutuyoruz. |

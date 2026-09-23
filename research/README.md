# research/ — IC ölçüm düzeneği

DEVIR.md bölüm 8 madde 8, IC ölçümünü "projenin en eksik parçası" diye
işaretliyordu. Bu klasör onun ilk çalışan hali.

**Burası paketin dışındadır.** `src/ratio_engine` sıfır bağımlılık özelliğini
korur (K10); buradaki betikler `yfinance` ve `pandas` kullanır. Paket bunlara
asla bağlanmaz, bağımlılık tek yönlüdür: research → ratio_engine.

```bash
pip install yfinance
python research/harvest_annual.py      # veriyi cek (~90 hisse, ~6 dk)
python research/annual_ic.py           # 6 aylik rank-IC
python research/ls_spread.py           # ilk10/son10 getiri farki
```

Veri önbellekleri (`research/*.json`) git'e girmez — çekilen veri, kaynak değil.

## Sentetik çeyrek kurgusu — ne uyduruluyor, ne uydurulmuyor

Motor çeyrek serisi istiyor. yfinance'ın çeyreklik tabloları **delikli** ve
sadece 5 çeyrek; yıllık tabloları deliksiz ve 4-5 yıl. Bu yüzden her mali yıl
dört sentetik çeyreğe açılıyor:

| Alan tipi | Ne konuyor | Sonuç |
|---|---|---|
| Akış (`revenue`, `net_income`, `cfo`, …) | yıllık / 4 | `sum4q()` yıl sonunda **birebir** yıllık rakamı verir |
| Stok (`total_assets`, `total_equity`, …) | yıl sonu bakiyesi | `avg()` yıl sonu okumasıdır |

**Uydurulan:** yıl içi dağılım. Bu yüzden `avg()` gerçek ortalama değil yıl sonu
değeridir ve bu düzenek mevsimsellik hakkında hiçbir şey söyleyemez.
**Uydurulmayan:** rasyolar yalnız mali yıl sonlarında okunur, orada tüm TTM
toplamları ve yıldan yıla karşılaştırmalar gerçek rakamlardır.

Bu kurgu olmadan dönem başına ~900 rasyo hesaplanıyordu; kurguyla ~4200.

## Ölçüm tasarımı

- Yayın gecikmesi 75 gün: yıl sonu + 75 gün skor tarihi. Motor hiçbir zaman
  yayınlanmamış bir bilançoyu görmez.
- İleriye dönük pencere 182 gün.
- Mali yıl başına bir pencere, **pencereler çakışmaz** — dolayısıyla dönemler
  arası ortalama ve t-istatistiği meşrudur.
- Finansallarını TRY dışında raporlayanlar elenir (fiyat TRY, aksi halde tüm
  değerleme çarpanları ~40 kat yanlış çıkar).

## Bilinen yanlılıklar — hepsi IC'yi YUKARI çeker

1. **Yeniden düzenleme.** yfinance finansalların bugünkü düzeltilmiş halini
   verir, rapor tarihi yoktur. Motor o tarihte bilinmeyen bir rakamı görüyor
   olabilir. Ana projenin `t0_date` / `version_tag` / PIT denetimi tam da bunun
   içindi; bu düzenek onu **atlar**.
2. **Hayatta kalma.** Evren listesi bugünkü BIST'ten kuruldu; dönem içinde
   çöküp listeden düşenler yok.
3. **İşlem maliyeti ve likidite yok.** `G_likidite` kapısı uygulanmıyor.

Yani çıkan sayı bir **üst sınır tahminidir**, gerçek değer bundan düşüktür.

## Bu düzeneğin bulduğu iki motor hatası

Gerçek veri, sentetik veriyle görünmeyen iki kusuru ortaya çıkardı:

- `evaluator.py` — bilinmeyen operand taşıyan domain kapısı sessizce `False`
  okunuyor, veri deliği `WORST` diye etiketleniyordu. Commit `132ec8b`.
- `scoring.py` — uç bir değer lojistiği taşırıp **tüm evrenin** skorlamasını
  `OverflowError` ile çökertiyordu. Commit sonrası kararlı forma geçildi.

İkisi de sentetik fikstürle asla görünmezdi. Düzeneğin ilk getirisi bu oldu.

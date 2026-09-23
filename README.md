# total-rasyo-fit-version

Borsa İstanbul için fail-closed bir finansal rasyo motoru. **67 rasyo**, 19 aile,
7 pillar; sektör bazlı uygulanabilirlik, açık kapsam ölçümü ve rasyo sayısından
bağımsız ağırlıklandırma.

Üçüncü parti bağımlılığı **yok** — sadece Python standart kütüphanesi. Test için
`pytest` yeterli.

```bash
pip install pytest
pytest -q          # 105 passed
```


## Total Rasyo 2.0 — GREENFIELD aktif yön

2026-09-23 itibarıyla bu repository'deki mevcut rasyo motoru **legacy/baseline**
olarak ele alınır. Hiçbir oran, formül, pillar, family, ağırlık, eşik veya
kompozit yeni sistem tarafından otomatik olarak doğru kabul edilmez.

Yeni Total Rasyo 2.0 ayrı namespace altında sıfırdan kurulacaktır:

```
src/tr2/
research/tr2/
tests/tr2/
config/tr2/
```

Legacy bir parça yalnız şu audit sonucundan sonra taşınabilir:

```
KEEP_AS_IS / PORT_WITH_CHANGES / REWRITE / DELETE
```

Yeni sistemin hedefi yüksek görünen puan üretmek değil; point-in-time temiz,
tekrarlanabilir ve ileri dönem sektör/piyasa düzeltilmiş getiriyi istikrarlı
sıralayan bir alpha üretmektir.

Üretim hedef çıktıları:

- `raw_alpha`
- `total_rasyo_0_100`
- `confidence_0_100`
- `risk_0_100`

Kullanıcının InvestingPro+ üyeliği aktif durumdadır. Pro+; feature factory,
forward expectations/revisions, valuation challenger/ensemble ve bağımsız
benchmark olarak kullanılacaktır. Hazır vendor skorları doğrudan Total Rasyo'ya
eklenmez.

**Tek yaşayan uygulama planı:** [ROADMAP.md](ROADMAP.md)  
**Greenfield matematik/veri mimarisi:** [docs/TOTAL_RASYO_2_0_MIMARI.md](docs/TOTAL_RASYO_2_0_MIMARI.md)

### TR2 private CSV snapshot

The new `src/tr2/ingest.py` captures a vendor CSV without changing its bytes.
It records SHA256, exact headers and schema fingerprint, row/column counts,
declared BIST universe/filters, export time, ingest time and parser version.
The export timestamp must have a timezone. This first parser handles UTF-8 CSV;
XLSX support and vendor field mapping require an actual export to validate.
The raw bytes are stored by hash, and each capture writes a new manifest.

```bash
python src/tr2/ingest.py /path/to/export.csv \
  --private-root data/private/tr2 \
  --exported-at '2026-09-23T15:30:00+03:00' \
  --universe 'BIST primary shares' \
  --filters 'Trading Region: Turkey; exchange: Borsa Istanbul'
```

`data/private/` and `data/vendor/` are ignored by Git. Never commit licensed
raw exports, credentials or cookies to this public repository. Manifests
record what the caller supplied for filters and universe; actual UI settings
must be checked against the export receipt. A current snapshot is usable only
at or after its `snapshot_at`; it does not reconstruct historical availability.

> Aşağıdaki mevcut motor açıklaması tarihsel/legacy bağlamdır; TR2 tasarım kararı değildir.
> Bir iş, ilgili `TR2-XXX` maddesi ve doğrulama kanıtı ROADMAP'te güncellenmeden
> `DONE` sayılamaz.

## Neden ayrı bir motor

Bu katman, Total Rasyo projesinin v1 rasyo katmanında **ölçülmüş** üç kusuru
gidermek için yazıldı. Üçü de tahmin değil; canlı kod üzerinde çalıştırılıp
gözlendi.

### 1. Tek eksik rasyo tüm skoru siliyordu

v1'de skor toplama `numpy` ile yapılıyordu, dolayısıyla bir CORE rasyo `NA`
olunca tüm bileşik skor `NaN` oluyor, sonra günlük hat onu `0.0` ile
dolduruyordu. Pratik sonucu: **borçsuz bir şirket**, faiz gideri olmadığı için
`INTEREST_COVERAGE` hesaplanamıyor diye kalitede sıfır alıyordu.

v2 tek `is_na` boolean'ı beşe ayırır:

| Sonuç | Ne zaman | Skorda |
|---|---|---|
| `OK` | Hesaplandı | Değeri skorlanır |
| `MISSING` | Gerekli alan yok | Kapsamı düşürür |
| `BEST` / `WORST` | Tanımsız ama ekonomik anlamı net | **Ölçülmüş sayılır**, 1.0 / 0.0 |
| `NOT_APPLICABLE` | Bu şirkette/sektörde anlamsız | **Paydadan tamamen çıkar** |

Borçsuz şirkette faiz karşılama → `BEST`. Envantersiz hizmet şirketinde stok
devir günü → `NOT_APPLICABLE`. Zarardaki şirkette F/K → `WORST` (tanımsız bir
çarpan yüzünden "ucuz" görünmesin diye).

### 2. Pillar ağırlığı rasyo sayısına bağlıydı

v1'de her rasyoya `pillar_w × ratio_w` veriliyor ve ağırlık toplamına
bölünüyordu; bir pillar'ın gerçek payı `(rasyo sayısı × pillar_w) / Σ` oluyordu.
Yani bir pillar'a rasyo eklemek, config'e dokunmadan onun ağırlığını
artırıyordu — **rasyo seti büyütülemez durumdaydı.**

v2'de ağırlık üç kademeli:

```
w = pillar_payı / o_pillar'daki_uygulanabilir_aile_sayısı
                / o_ailedeki_uygulanabilir_rasyo_sayısı
```

Aileye rasyo eklemek ağırlığı **sadece o ailenin içinde** dağıtır. Doğrulama:
NONFIN'de LEV pillar'ı 12 rasyo, BANK'ta 2 rasyo taşır — payı ikisinde de
config'in dediğidir.

### 3. Sektörler arası çarpıklık

v1'de sektör izinleri rasyo tanımından ayrı bir dosyada duruyordu. İzinli CORE
rasyo sayısı BANK'ta 10, NONFIN'de 26 olmuştu ve kimse fark etmemişti. Sonucu:
mutlak bir `good_count` eşiği kullanıldığı için bir bankanın ilgili modülü
**0.56 tavanını** aşamıyor, veto eşiğini geçmesi sanayi şirketine göre ~2,6 kat
zorlaşıyordu.

v2'de `applies_to` rasyonun kendi üzerindedir ve `good_ratio` mutlak sayı değil
**ağırlık oranı**dır. Tavan her grupta 1.0.

## Kapsam — ne bugün hesaplanabilir

Motor her rasyonun hangi alana bağlı olduğunu, her alanın da nereden geldiğini
bilir. Bu, "şu alanı getirirsem kaç rasyo açılır" sorusunu hesaplanabilir yapar:

| Grup | Uygulanabilir | Aile | Bugün hesaplanabilir | Engelleyen |
|---|---|---|---|---|
| NONFIN | 67 | 19 | 47 | KAP_XBRL 15, PROPLUS 4, dipnot 1 |
| HOLDING | 58 | 17 | 42 | KAP_XBRL 11, PROPLUS 4, dipnot 1 |
| GYO | 54 | 17 | 41 | KAP_XBRL 10, PROPLUS 2, dipnot 1 |
| FINANCIAL | 27 | 14 | 22 | KAP_XBRL 3, PROPLUS 2 |
| INSURANCE | 27 | 14 | 22 | KAP_XBRL 3, PROPLUS 2 |
| BANK | 23 | 11 | 18 | KAP_XBRL 3, PROPLUS 2 |

Okunuşu: **dokuz KAP XBRL alanı NONFIN'de 15 rasyo açıyor.** En yüksek getirili
tek alan `depreciation_amortization` — tek başına EV/FAVÖK, FAVÖK marjı, net
borç/FAVÖK, FAVÖK faiz karşılama, nakit dönüşümü ve capex/D&A'yı açıyor. v1
BIST'in en çok kullanılan çarpanını, sırf bu alan yok diye hiç hesaplayamıyordu.

## Tasarım kararları

**Çapa politikası.** 67 rasyonun 21'inde mutlak çapa var (`weak`/`strong`), geri
kalanı tamamen görecelidir. ROE/ROA/ROIC ve tüm değerleme çarpanlarında çapa
**bilerek yok**: Türkiye enflasyonunda nominal %30 ROE reel zarar olabilir, F/K 6
sıradan bir piyasa seviyesi olabilir. Uydurulmuş çapa, çapasızlıktan kötüdür.

Çapanın işlevi şu: saf yüzdelik her zaman birini 10. desile koyar — tüm piyasa
kötüyken bile. Çapa, skorun "bu çeyrek kimse iyi değil" diyebilmesini sağlar.

**Medyan/MAD, ortalama/std değil.** BIST kesitleri kalın kuyrukludur;
winsorize edilmiş standart sapma bile winsorizasyondan sağ çıkanlar tarafından
sürüklenir.

**İstikrar rasyo değildir.** Sette hiç `*_STABILITY` rasyosu yok. İstikrar,
skorlama katmanının 8 çeyrek üzerinden türettiği `(seviye, eğim, istikrar)`
üçlüsünün üçüncü bileşenidir.

**Rasyo ağırlıkları asla fit edilmez.** Aile içi eşit ağırlık bilinçli bir
kısıttır: ~40 bağımsız çeyreklik BIST geçmişi kabaca 4-7 parametre fit etmeye
yeter. O bütçe eksen ağırlıkları ve kapı eşikleri için harcanır, 67 rasyo
ağırlığı için değil.

**Üç kompozit, bir tane değil.** `quality` (LIQ+LEV+CASH+PROFIT+EFF), `growth`
(GROWTH) ve `value` (VAL) ayrı ayrı üretilir. v1 büyümeyi kalitenin içine
ortalıyordu; ileriye bakan bir sinyal geriye bakan bir skorda kayboluyordu.

## Yapı

```
config/ratio_fields.v2.json   48 alan: tier (nereden geliyor) + flow
config/ratios.v2.json         67 skorlanan rasyo + 9 ara büyüklük
src/ratio_engine/spec.py      şema yükleyici + fail-closed doğrulayıcı
src/ratio_engine/calc.py      formül → beş sonuçtan biri
src/ratio_engine/scoring.py   aile normalizasyonlu kesitsel skorlama
src/ratio_engine/evaluator.py güvenli formül değerlendirici (vendor'lanmış)
src/ratio_engine/trend.py     8 çeyrek üzerinden (seviye, eğim, istikrar)
src/ratio_engine/liquidity.py 60 günlük ortalama TL işlem hacmi
src/engines/base.py           EngineResult sözleşmesi, kapılar çarpılır
src/engines/saf_deger.py      değer ekseni + muhasebe kapısı
src/engines/kalite_bilesik.py kalite 0.70 + marj istikrarı 0.30
src/board/comparison.py       sıralama, uzlaşma, ayrışma
src/board/report.py           terminal tablosu + CSV
research/                     IC ölçüm düzeneği (paket dışı)
sql/043_ratio_set_v2.sql      PostgreSQL şeması (2 tablo, 15 CHECK, 2 trigger)
tests/                        63 test
```

`evaluator.py`, Total Rasyo projesinin `src/analytics/ratios_calc.py`
dosyasından `adf3f81` commit'inde birebir alındı; sadece pandas/PostgreSQL
katmanı geride bırakıldı. Yukarı akış değişirse bu dosya otomatik takip etmez —
ayrılmanın kabul edilmiş bedeli budur.

## Kullanım

```python
from ratio_engine import load_ratio_set, compute_ratios_for_ticker, score_universe

rs = load_ratio_set("config/ratios.v2.json", "config/ratio_fields.v2.json")

# Bir şirketin çeyreklerini rasyo sonuçlarına çevir
outcomes = compute_ratios_for_ticker("THYAO", rows, rs, "NONFIN", price_map)

# Evreni kesitsel olarak skorla
results = score_universe(rs, observations, {"THYAO": "NONFIN", ...})
results["THYAO"].composites["quality"].score      # 0..1 ya da None
results["THYAO"].composites["quality"].coverage   # ne kadarı ölçüldü
results["THYAO"].composites["quality"].status     # OK / YETERSIZ_KAPSAM
```

Kapsam eşiğinin altında skor `None` döner ve durum `YETERSIZ_KAPSAM` olur —
`NaN` değil, sessiz `0.0` hiç değil.

## Doğrulama durumu

```
105 test                         passed
Mutasyon testi (rasyo katmanı)   5/5 yakalandı
Mutasyon testi (trend+likidite)  4/4 yakalandı
Mutasyon testi (motor+tahta)     5/5 yakalandı
Üçüncü parti bağımlılık          yok
PostgreSQL migration             canlı veritabanında HENÜZ KOŞULMADI
```

Beş mutasyonun her biri en az bir testi kırdı: aile normalizasyonu kaldırıldı,
`NOT_APPLICABLE` paydada bırakıldı, yetersiz kapsam sessizce 0.0 döndü,
`BEST`/`WORST` ölçülmüş sayılmadı, bağ çözümü giriş sırasına bırakıldı.

Trend ve likidite katmanında dört mutasyon daha koşuldu ve dördü de en az bir
testi kırdı: çeyrek indeksi liste sırasına indirgendi, yetersiz çeyrek sayısı
sessizce 0.0 döndü, `OK` olmayan statüler regresyona alındı, `as_of` sonrası
barlar pencereye sızdı. Üçüncüsü ilk koşuda **kaçtı** — `RatioOutcome`'ın kendi
değişmezi `BEST` satırlarını zaten eliyordu, dolayısıyla statü kapısı test
açısından ölüydü. Kapı korundu ve eksik test yazıldı
(`test_a_non_ok_status_is_skipped_even_when_it_carries_a_value`).

`sql/043_ratio_set_v2.sql` yalnızca yapısal olarak kontrol edildi; gerçek bir
PostgreSQL üzerinde çalıştırılması gerekiyor.

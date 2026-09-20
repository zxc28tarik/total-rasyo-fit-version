# DEVİR DÖKÜMANI — total-rasyo-fit-version

Bu belge, Total Rasyo Hesaplayıcı projesinde başlayıp ayrı bir projeye evrilen
işin tam devridir. Bu sohbeti hiç görmemiş bir oturum, yalnızca bunu okuyarak
devam edebilmelidir.

**Yayınlanmış hali:** https://github.com/zxc28tarik/total-rasyo-fit-version
(public, commit `541e37a`, 16 dosya, 3080 satır, 39 test geçiyor)

Boş klasörde sıfırdan kuruyorsan en hızlı yol:
`git clone https://github.com/zxc28tarik/total-rasyo-fit-version`
Bölüm 6'daki kod, o repodaki dosyaların birebir aynısıdır.

---

## 1. PROJE NEDİR

Borsa İstanbul için fail-closed bir **finansal rasyo motoru**. Girdi olarak bir
şirketin çeyreklik finansal kalemlerini ve fiyatını alır; çıktı olarak her
rasyonun beş durumdan birini (`OK`, `MISSING`, `BEST`, `WORST`,
`NOT_APPLICABLE`) ve evren genelinde kesitsel skorlanmış üç kompozit
(`quality`, `growth`, `value`) üretir. 67 rasyo, 19 aile, 7 pillar, 6 sektör
grubu. Üçüncü parti bağımlılığı yoktur — yalnız Python standart kütüphanesi.

Çözdüğü problem: yaygın rasyo skorlama kodları, hesaplanamayan bir rasyoyu tek
bir "NA" kovasına atar. Bu, birbirinden tamamen farklı üç durumu birleştirir —
"veri yok", "bu şirkette anlamsız", "tanımsız ama ekonomik anlamı mükemmel" —
ve sonuçta ölçülemeyen şirketi ölçülmüş gibi, hatta kötü gibi gösterir. Motor
bu üçünü ayırır, ne kadarının gerçekten ölçüldüğünü (`coverage`) açık bir sayı
olarak taşır ve kapsam eşiğinin altında skor yerine **durum** döndürür: `NaN`
değil, sessiz `0.0` hiç değil.

İkinci çözdüğü problem: rasyo setini büyütebilir kılmak. Pillar ağırlığının
rasyo sayısına bağlı olduğu bir toplulaştırmada rasyo eklemek, config'e
dokunmadan ağırlıkları kaydırır; set pratikte dondurulmuş olur.

---

## 2. NASIL KOPTU

**Başlangıç sorusu:** Kullanıcı "InvestingPro alırsam projeyi ne kadar ileri
taşıyabilirim, rasyo sayısını artırabilir miyiz" diye sordu. Total Rasyo'nun
rasyo katmanı incelendi.

**Kopuşu tetikleyen bulgu:** İnceleme sırasında rasyo katmanında üç kusur
**ölçüldü** (tahmin edilmedi — canlı kod üzerinde çalıştırılıp gözlendi):

1. Tek eksik rasyo tüm skoru siliyordu. 6 şirketlik bir koşuda, 3 rasyodan
   1'i `NA` olan şirketin `rsc_core_norm` değeri `NaN` çıktı; günlük hat onu
   `0.0` ile dolduruyordu.
2. Pillar payı rasyo sayısına bağlıydı — yani rasyo seti büyütülemezdi.
3. Sektörler arası çarpıklık: izinli rasyo sayısı BANK'ta 10, NONFIN'de 26;
   mutlak `good_count` eşiği yüzünden bankanın ilgili modülü 0.56 tavanını
   aşamıyordu.

**Ayrı proje yapmaya değer kılan fikir:** Kusurları gidermek için yazılan v2
katmanı tasarlanırken şu ortaya çıktı — `spec.py` ve `scoring.py` **saf
stdlib**. Ana projenin veritabanına, pandas'ına, pipeline'ına hiçbir bağı yok.
Tek bağ `calc.py`'nin formül değerlendiricisiydi, o da incelendiğinde
`ratios_calc.py`'nin **kullanılan kısmının** pandas'sız olduğu görüldü;
ağırlık sadece modülün tepesindeki `import pandas` ve `bulk_upsert_ratios`
satırlarından geliyordu.

Yani ortada, ana projeden çıkarıldığında **sıfır bağımlılıkla çalışan, kendi
başına anlamlı bir kütüphane** vardı. Kullanıcı "yeni bir github projesinde
açabilir misin" diye sorduğunda ayrılma kararı verildi.

**Ayrılmanın kabul edilmiş bedeli:** Değerlendirici artık iki yerde. Yukarı
akış (`ratios_calc.py`) değişirse bu repo otomatik takip etmez.

---

## 3. DEVRALINAN vs YENİ

### Devralınan — kod

| Yeni dosya | Kaynak | Ne alındı |
|---|---|---|
| `src/ratio_engine/evaluator.py` | `src/analytics/ratios_calc.py` @ `adf3f81` | 13 tanım birebir: `OPS`, `CMP`, `ALLOWED_FUNCS`, `coalesce`, `nz`, `_is_finite`, `_quarter_end`, `_shift_quarter_end`, `_row_version_key`, `QuarterSeries`, `safe_eval_expr`, `safe_eval_condition`, `derive_fields_per_ticker` |

Geride bırakılanlar (pandas/PostgreSQL katmanı, bilinçli):
`fill_missing_t0_dates`, `fetch_financials`, `apply_unit_scale`,
`load_ratio_specs`, `RatioSpec` (v1'inki), `compute_ratios_for_ticker` (v1),
`compute_all_ratios`, `run_ratios_calc`, `fetch_prices_for_pairs`.

### Devralınan — mantık ve taksonomi

- **Formül dili**, `config/ratios.json`'dan: `avg(x)`, `lag(x,n)`, `lag4q(x)`,
  `sum4q(x)`, `ttm(x)`, `days_in_period()`, `abs`, `min`, `max`, `log`,
  `log1p`, `coalesce`, `nz`.
- **Rasyonun kod değil veri olması** fikri — v1'in en doğru kararı, aynen
  korundu ve genişletildi.
- **Pillar taksonomisi** `config/ratios.json`'dan: LIQ, LEV, CASH, PROFIT,
  EFF, GROWTH, VAL.
- **Sektör grubu taksonomisi** `config/sectors.json`'dan: BANK, FINANCIAL,
  HOLDING, GYO, NONFIN (+ INSURANCE, v1'de motoru vardı ama
  `index_to_group` eşlemesi yoktu; v2'de grup olarak eklendi).
- **33 v1 rasyosu**, 67'lik setin çekirdeği olarak. İsimler büyük ölçüde
  korundu; iki tanesi düzeltilerek yeniden adlandırıldı (aşağıda).
- **Fail-closed disiplini**: her ihlal `raise`, hiçbiri `warning`.
- **Değişmezlik trigger deseni**, `sql/042_backtest_schedule_registry.sql` ve
  `sql/033_impact_runtime_roles.sql`'den.
- **Mutasyon testi kültürü** (V19–V23 oturumlarının disiplini): her korumanın
  en az bir testle kanıtlanması.

### Devralınan — veri

Hiçbir gerçek veri taşınmadı. Ana projede de zaten gerçek veri akışı yoktu:
KAP/MKK adaptörü yazılmış ama bağlanmamış, config'ler `.example.invalid`
yer tutucuları taşıyor, backtest sentetik 24 hisselik veriyle koşulmuş ve
`optimize-weights` gerçek koşuda IC 0.057 (gürültü seviyesi) vermişti.

### Düzeltilen iki v1 formülü

| Rasyo | v1 | v2 |
|---|---|---|
| `DPO_DAYS_PROXY` → `DPO_DAYS` | `(debt_st / cogs) * days_in_period()` — **kısa vadeli finansal borcu** ticari borç sanıyordu; hata `CCC_DAYS_PROXY`'ye de yayılıyordu | `(avg(accounts_payable) / sum4q(cogs)) * 365` |
| `ROIC_PROXY` → `ROIC` | `ebit / (avg(total_assets) - avg(current_liabilities))` — vergi öncesi | `NOPAT / INVESTED_CAPITAL` |

### Tamamen yeni

- **Aile katmanı** (19 aile) ve pillar payının rasyo sayısından bağımsız
  olmasını sağlayan üç kademeli ağırlık formülü.
- **Üç sonuç semantiği**: `MISSING` / `BEST` / `WORST` / `NOT_APPLICABLE`
  ayrımı (v1'de tek `is_na` boolean).
- **Açık kapsam** (`coverage`) ve `YETERSIZ_KAPSAM` durumu.
- **Mutlak çapa** (`anchor`) mekanizması ve 21 rasyoda uygulanması.
- **Medyan/MAD** robust skorlama (v1 yüzdelik sıralama kullanıyordu).
- **`role: INTERMEDIATE`** — hesaplanıp env'e giren ama skorlanmayan ara
  büyüklükler (v1 bunu `EV_PROXY`'yi VAL rasyosu yapıp sonra filtreyle
  dışlayarak taklit ediyordu).
- **Alan kaydı** (`ratio_fields.v2.json`) ve `tier` kademeleri — "şu alanı
  getirirsem kaç rasyo açılır" sorusunu hesaplanabilir yapan yapı.
- **Üç kompozit** (`quality` / `growth` / `value`) — v1 tek
  `rsc_core_norm` + `rsc_val_norm` üretiyordu.
- **`applies_to` rasyonun üzerinde** (v1'de ayrı dosyada `allowed_ratios`).
- **`good_ratio`** ağırlık oranı olarak (v1: mutlak `good_count_ge8`).
- `spec.py`, `calc.py`, `scoring.py`, `sql/043`, 39 testin tamamı.

---

## 4. INVESTING PRO ENTEGRASYONU

**Durum: HİÇBİR KOD YAZILMADI. Bu bölümün tamamı araştırma ve tasarımdır.**
Abonelik alınmadı, tek bir satır entegrasyon kodu yok.

### Uç noktalar

**YOK.** Investing.com'un kendi destek sayfası doğrudan API sunmadıklarını
açıkça söylüyor; yalnız web geliştiricileri için widget'lar var. Pro+ paketi
dahil hiçbir kademede API yok. Bu bir paket meselesi değil, ürün meselesi.

Kaynaklar (bu sohbette web araması ile doğrulandı):
- https://pro.investing-support.com/hc/en-us/articles/4408847632017-Do-You-Offer-API-Access-at-Investing-com
- https://www.investing-support.com/hc/en-us/articles/115005473825-Do-You-Offer-API-Access-at-Investing-com

### Kimlik doğrulama yöntemi

**KARARLAŞMADI** — API olmadığı için tasarlanacak bir auth mekanizması yok.
Öngörülen akış elle export temellidir, dolayısıyla kimlik doğrulama
kullanıcının tarayıcı oturumudur; kod tarafında hiçbir kimlik bilgisi
tutulmaz.

### Rate limit'ler

**UYGULANMAZ / KARARLAŞMADI** — programatik çağrı olmadığı için rate limit
kavramı yok. Ana projedeki KAP adaptöründe `Retry-After`, asgari istek
aralığı ve response/item byte sınırları vardı; InvestingPro tarafında
karşılığı yok.

### Paket kademeleri (web araması ile doğrulandı)

| | Pro | Pro+ |
|---|---|---|
| Finansal geçmiş | 5 yıl | **10 yıl** |
| Araştırma metriği | ~100 filtre | **1.200+ metrik, 160+ screener filtresi** |
| Export | yok | **CSV / Excel** |
| Ek skorlar | — | **Altman Z, Beneish M** |
| Fiyat | ~$91/yıl ilk yıl | ~$229–293 ilk yıl, **~$539 yenileme** |

Screener export'u **toplu**: tüm BIST + seçili metrikler → tek CSV. Yani
hisse hisse açmak gerekmiyor.

Kaynaklar: https://www.matchmybroker.com/articles/investingpro-pricing ·
https://pro.investing-support.com/hc/en-us/articles/4408832850193-Using-the-Stock-Screener

### Çekilecek alanlar

Alan kaydında `tier: PROPLUS` olarak işaretli **7 alan**:

```
eps_fwd_1y            ileri 1 yıl konsensüs EPS
eps_fwd_1y_3m_ago     3 ay önceki ileri EPS  → tahmin revizyonu için
ebitda_fwd_1y         ileri 1 yıl FAVÖK
revenue_fwd_1y        ileri 1 yıl satış
eps_surprise_4q_avg   son 4 çeyrek kazanç sürprizi ortalaması
altman_z              Altman Z skoru
beneish_m             Beneish M skoru
```

Bu 7 alan, NONFIN'de **4 rasyo** açıyor (`REVENUE_FWD_GROWTH`, `PE_FWD`,
`ALTMAN_Z_SCORE`, `BENEISH_M_SCORE`). Kıyas: 9 KAP XBRL alanı NONFIN'de
**15 rasyo** açıyor. Yani Pro+'ın rasyo sayısına katkısı küçük; asıl değeri
**tahmin ekseni**, ki mevcut sistemde hiç yok.

### Veri modeli ve alan eşlemeleri

Tasarlanan akış (ana projenin mevcut KAP deseniyle aynı):

```
data/investingpro/BIST_YYYY-MM.csv   (elle bırakılan export)
→ SHA256 + export_date + satır sayısı
→ raw.investingpro_export             (değişmez payload)
→ SemanticFactMapper(profile="INVESTINGPRO_EXPORT", version=1)
→ core.semantic_financial_facts       (ana projede ZATEN VAR)
```

**CSV kolon adları → kanonik alan eşlemesi: KARARLAŞMADI.** Gerçek bir export
dosyası görülmeden yazılmayacak. Bu bilinçli bir kural — ana projenin README'si
KAP alan yollarını tahmin etmeyi açıkça reddediyor ve config'leri çalışmayan
`.example.invalid` değerleriyle bırakıyor; aynı disiplin burada da geçerli.

**Kritik kısıt — point-in-time yok.** InvestingPro bugünkü *restated* rakamı
verir; yayın anı damgası ve ilk açıklanan hali yoktur. Bu yüzden:

- `knowledge_time = export tarihi` ile yazılır
- Yalnız `CURRENT_KNOWLEDGE_RESTATE` hattını besler, **PIT hattını değil**
- Geriye dönük backtest'te **look-ahead yanlılığı** taşır

**İleriye dönük telafi:** Her ay export alınıp değişmez arşivlenirse, 3 yıl
sonra kimsenin satmadığı gerçek bir PIT arşivi oluşur. Maliyeti bir klasör ve
bir hash. Geciktirilen her ay kalıcı kayıp.

### Denenip çalışmayan yaklaşımlar

| Yaklaşım | Sonuç |
|---|---|
| Resmî API ile çekme | **Ürün yok.** Destek sayfası doğrudan söylüyor. |
| Scraping (giriş yapılmış Pro+ sayfaları) | **Reddedildi.** Üç gerekçe: (a) ToS otomatik veri çekmeyi yasaklıyor, ihlalin pratik sonucu ~$539'luk hesabın kapatılması; (b) Cloudflare bot koruması, çalışan bir scraper bir sonraki ay kırılır; (c) **asıl mesele** — kazınmış HTML'in yayın anı ve sürümü yoktur, aynı sayfa yarın sessizce farklı gelir; bu, ana projenin V21/V22/V23'te aylarca uğraşıp kapattığı "kanıt yok ama PASS" sınıfını arka kapıdan geri sokar. |
| Pro+ Fair Value / Financial Health'i motor girdisi yapmak | **Reddedildi.** Girdi yapılırsa motor başkasının modelinin sarmalayıcısına döner ve tek motor sahipliği sözleşmesi bozulur. Yalnız **yan sütun** olarak, kıyas amaçlı kullanılır. |

### Kapsam uyarısı

BIST30/50 dışında analist konsensüsü zayıflar; Fair Value çoğu orta/küçük
ölçekli isimde "yeterli veri yok" döner. Yani en çok işe yarayacak forward
eksen, tam da en çok fırsatın olduğu yerde en zayıf. Tahmin yoksa `MISSING`
olur, trailing'e **düşülmez** — sessiz ikame yanlış güven üretir.

### Ayrıca değerlendirilen alternatifler

API'si ve arşivi olan sağlayıcılar, otomatik fail-closed bir hat için
InvestingPro'dan daha uygun bulundu: **Finnet, Matriks, Foreks, Rasyonet**
(yerel), **FMP, EODHD, LSEG** (uluslararası). Seçim **KARARLAŞMADI**.

---

## 5. KARARLAR

### K1 — v1 hiç değiştirilmez, v2 yanına kurulur
Ana projede tek bir mevcut dosyaya dokunulmadı. Doğrulandı: 1295 test passed,
222 skipped, 0 failed; BANK v4.7 regresyonu 277 passed + 1 xfail (önceden var
olan bilinen sınır).
**Reddedilen:** v1'i yerinde güncellemek. Geçmiş skorların anlamı sessizce
değişirdi ve mevcut regresyonun çoğu yeniden yazılırdı.

### K2 — Rasyo sayısı 67, 81 değil
İlk taslak "12 aile × 4-8" diye yukarıdan aşağı kurulup 81'e çıkmıştı. Fit
kapasitesi hesaplanınca hem sayı hem gerekçe değişti: aile başına marjinal
fayda hızla doyuyor (1→3 rasyo idiyosinkratik gürültüyü ~%42 kısar, 3→6 bir
%29 daha, 6→10 neredeyse kopya ekler). Aile başına 3-5 tatlı nokta.
**Reddedilen:** 81 ve üzeri. Ayrıca Pro+'ın 1.200 metriğini olduğu gibi almak
— metriklerin çoğu aynı soru × farklı dönem × farklı varyant, yani
`(seviye, eğim, istikrar)` üçlüsünde zaten eriyor.

### K3 — Rasyo ağırlıkları ASLA fit edilmez
10 yıl × 4 çeyrek = 40 dönem. Kesitsel korelasyon yüksek olduğu için dönem
başına ~1 bağımsız gözlem. Parametre başına ≥10 gözlem kuralıyla güvenle
**4-7 parametre** fit edilebilir. Bu bütçe eksen ağırlıkları ve kapı eşikleri
için harcanır.
**Reddedilen:** Aile içi korelasyon ölçüp ağırlık kırpmak. Daha önce bu sohbette
önerildi, sonra **geri alındı** — veri taşımıyor.

### K4 — Aile normalizasyonu
`w = pillar_payı / aile_sayısı / ailedeki_rasyo_sayısı`. Doğrulandı: NONFIN'de
LEV 12 rasyo, BANK'ta 2 rasyo taşıyor; pay ikisinde de config'in dediği.
**Reddedilen:** v1'in düz ağırlıklandırması — pillar payı `(rasyo sayısı ×
pillar_w)/Σ` oluyordu.

### K5 — Üç sonuç semantiği
`MISSING` kapsamı düşürür · `BEST`/`WORST` ölçülmüş sayılır · `NOT_APPLICABLE`
paydadan tamamen çıkar.
**Reddedilen:** Tek `is_na` boolean.

### K6 — Çapa yalnız savunulabilir yerde: 67'nin 21'i
ROE/ROA/ROIC ve **tüm değerleme çarpanlarında** çapa bilerek yok: Türkiye
enflasyonunda nominal %30 ROE reel zarar olabilir, F/K 6 sıradan bir piyasa
seviyesi olabilir.
**Reddedilen:** Her rasyoya çapa koymak. Uydurulmuş çapa çapasızlıktan kötüdür.
Çapanın işlevi, saf yüzdelik her zaman birini 10. desile koyduğu için skorun
"bu çeyrek kimse iyi değil" diyebilmesini sağlamaktır.

### K7 — Medyan/MAD
**Reddedilen:** Ortalama/standart sapma. BIST kesitleri kalın kuyruklu;
winsorize edilmiş std bile winsorizasyondan sağ çıkanlar tarafından sürüklenir.

### K8 — `*_STABILITY` rasyosu yok
İstikrar bir rasyo değil, skorlama katmanının 8 çeyrek üzerinden türettiği
`(seviye, eğim, istikrar)` üçlüsünün üçüncü bileşeni. **Not: bu üçlünün
`eğim` ve `istikrar` bileşenleri HENÜZ KODLANMADI**, sadece `seviye` var.

### K9 — Üç kompozit
`quality` (LIQ+LEV+CASH+PROFIT+EFF) · `growth` (GROWTH) · `value` (VAL).
**Reddedilen:** v1'in tek `rsc_core_norm`'u — büyüme, ileriye bakan bir sinyal
olmasına rağmen geriye bakan kalite skorunun içinde kayboluyordu.

### K10 — Değerlendirici vendor'lanır
**Reddedilen:** Bağımlılık zincirini olduğu gibi taşımak
(`ratios_calc.py` + `bulk_upsert_ratios.py` + `calendar.py`), ki bu repoyu
pandas ve psycopg2'ye bağımlı hale getirirdi.

### K11 — Ek9 (volatilite) skordan çıkar
Düşük volatilite bir portföy inşası girdisidir, hisse seçim sinyali değil.
Doğru yeri: seçilen isimler arasında ters-volatilite ağırlıklandırma.
**Reddedilen:** v1'deki .06 ağırlıklı modül olarak kalması.

### K12 — Sulandırma modül değil, rasyo
`SHARE_COUNT_GROWTH` (shares_out YoY, LOWER_BETTER).
**Reddedilen:** Bedelli duyurusuna −0.10 sabit ceza veren bir modül. Üç
gerekçe: sabit uydurma bir sayıydı; KAP kurumsal işlem akışı bağlı olmadığı
için uygulanamazdı; rasyo hali sürekli bir değişken ve dönüştürülebilir tahvil
ile çalışan opsiyonunu da yakalıyor.

### K13 — İşlem likiditesi ≠ bilanço likiditesi
Kullanıcı önce likidite kapısının bilançodan yapılmasını önerdi, tartışma
sonrası **geri aldı**. Karar: bilanço likiditesi (cari/asit-test/nakit oranı)
LIQ pillar'ında kalite ekseninde durur; **işlem likiditesi** (60g ortalama TL
hacim) ayrı bir sert kapıdır.
Gerekçe: aksi halde LIQ pillar'ı çift sayılır ve model günde 200 bin TL işlem
gören bir hisseyi 1 numara yapabilir — sinyal gerçek ama kullanılamaz. Ayrıca
illikit hissede fiyat bayatlar, ölçülen volatilite düşer, Sharpe şişer; ana
projenin backtest raporu bu hatayı bir kez zaten yakalamıştı (Sharpe 291).

### K14 — Karar mutlak eşikle değil sıralamayla
**Reddedilen:** v1'in `final_score >= 0.70` kuralı. Kendi raporuna göre
dönemlerin yalnızca %25'inde sinyal üretmişti; piyasa geneli bozulunca sinyal
tamamen kesilir.

### K15 — Kapılar çarpılır, toplanmaz
Dövizle borçlanmış, batma riski olan bir şirket "ucuz olduğu için"
telafi edilmemeli — değer tuzağı böyle oluşur. v1'in `good_count < 5 → ×0.60`
vetosu doğru içgüdü, yanlış değişkendi.

### K16 — Scraping yok
Bkz. Bölüm 4.

### K17 — Repo public
Kullanıcıya private önerildi, gerekçesiyle birlikte iki kez uyarıldı
(67 rasyo tanımı, çapalar, pillar payları, sektör politikaları herkese açık
olur; fork'lanabilir, indekslenebilir, silinse bile önbellekte kalabilir).
Kullanıcı "public devam" dedi. Karar kullanıcınındır ve uygulandı.

---

## 6. KOD

Aşağıdaki dosyaların tamamı `https://github.com/zxc28tarik/total-rasyo-fit-version`
reposunda commit `541e37a` altında birebir bulunur. Yollar o repodaki yollardır.


### `src/ratio_engine/spec.py`

Şema yükleyici ve fail-closed doğrulayıcı. Hiçbir skor hesaplamaz; yalnız 'bu rasyo seti kendi içinde tutarlı mı' sorusunu yüksek sesle cevaplar.

```python
from __future__ import annotations

"""v2 ratio specification: loader and fail-closed validator.

The v1 set carried 33 ratios across two files: ``config/ratios.json`` held the
formulas and ``config/sectors.json`` held the per-sector ``allowed_ratios``
lists.  Splitting a ratio's definition across two files is why nobody noticed
that BANK ended up with 10 eligible CORE ratios against NONFIN's 26, which in
turn capped a bank's ``ek1`` at 10/18 = 0.56 and made the ``good_count < 5``
veto roughly 2.6x easier to trip for a bank than for an industrial.  In v2 a
ratio declares its own sector applicability, so that class of drift cannot
recur.

Nothing here computes a score.  This module only answers "is this ratio set
internally consistent", and does so loudly: every violation raises, none warn.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence
import ast
import json


DIRECTIONS = ("HIGHER_BETTER", "LOWER_BETTER", "BAND")
OUT_OF_DOMAIN = ("MISSING", "BEST", "WORST", "NOT_APPLICABLE")
TRANSFORMS = (None, "signed_log", "clip")
ROLE_SCORED = "SCORED"
ROLE_INTERMEDIATE = "INTERMEDIATE"

# Functions the v1 AST evaluator (ratios_calc.safe_eval_expr) accepts.  A v2
# formula reaching for anything else would raise at compute time on live data;
# it is rejected at load time instead.
ALLOWED_FUNCS = frozenset(
    {"avg", "lag", "lag4q", "sum4q", "ttm", "abs", "coalesce", "nz",
     "days_in_period", "log", "log1p", "max", "min"}
)


class RatioSpecError(ValueError):
    pass


@dataclass(frozen=True)
class Anchor:
    weak: float
    strong: float

    def score(self, value: float) -> float:
        """Map an absolute level onto [0.05, 0.95]; weak -> 0.30, strong -> 0.80.

        Direction is already encoded in the ordering: for a LOWER_BETTER ratio
        ``weak`` is numerically greater than ``strong``.  A pure percentile
        always crowns somebody, even in a quarter when the whole market is bad;
        the anchor is what lets a score say nobody is good.
        """
        span = self.strong - self.weak
        if span == 0:
            raise RatioSpecError("anchor weak ve strong esit olamaz")
        t = (value - self.weak) / span
        return max(0.05, min(0.95, 0.30 + t * 0.50))


@dataclass(frozen=True)
class RatioSpec:
    name: str
    role: str
    pillar: str
    family: str
    formula: str
    requires: tuple[str, ...]
    domain: tuple[str, ...]
    direction: str | None = None
    out_of_domain: str = "MISSING"
    anchor: Anchor | None = None
    band: Mapping[str, float] | None = None
    applies_to: frozenset[str] = frozenset()
    winsor: float = 0.02
    transform: str | None = None
    clip: Mapping[str, float] | None = None

    @property
    def is_scored(self) -> bool:
        return self.role == ROLE_SCORED

    def applicable_to(self, group: str) -> bool:
        return self.is_scored and group in self.applies_to


@dataclass(frozen=True)
class RatioSet:
    version: str
    field_set_version: str
    families: Mapping[str, str]
    sector_groups: frozenset[str]
    specs: Mapping[str, RatioSpec]
    order: tuple[str, ...]
    _composites: Mapping[str, tuple[str, ...]]
    _pillar_shares_default: Mapping[str, float]
    _pillar_shares_by_group: Mapping[str, Mapping[str, float]]

    def scored(self) -> tuple[RatioSpec, ...]:
        return tuple(self.specs[n] for n in self.order if self.specs[n].is_scored)

    def intermediates(self) -> tuple[RatioSpec, ...]:
        return tuple(self.specs[n] for n in self.order if not self.specs[n].is_scored)

    def applicable(self, group: str) -> tuple[RatioSpec, ...]:
        if group not in self.sector_groups:
            raise RatioSpecError(f"bilinmeyen sektor grubu: {group!r}")
        return tuple(s for s in self.scored() if s.applicable_to(group))

    def families_of(self, group: str) -> tuple[str, ...]:
        seen: list[str] = []
        for spec in self.applicable(group):
            if spec.family not in seen:
                seen.append(spec.family)
        return tuple(seen)

    def composites(self) -> Mapping[str, tuple[str, ...]]:
        return self._composites

    def pillar_of_composite(self, composite: str) -> tuple[str, ...]:
        if composite not in self._composites:
            raise RatioSpecError(f"bilinmeyen kompozit: {composite!r}")
        return self._composites[composite]

    def pillar_shares(self, group: str) -> Mapping[str, float]:
        if group not in self.sector_groups:
            raise RatioSpecError(f"bilinmeyen sektor grubu: {group!r}")
        override = self._pillar_shares_by_group.get(group)
        return dict(override) if override else dict(self._pillar_shares_default)


def _obj(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise RatioSpecError(f"{name} nesne olmali")
    return value


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RatioSpecError(f"{name} dolu metin olmali")
    return value.strip()


def _number(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RatioSpecError(f"{name} sayi olmali")
    out = float(value)
    if out != out or out in (float("inf"), float("-inf")):
        raise RatioSpecError(f"{name} sonlu olmali")
    return out


def _str_tuple(value: Any, name: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise RatioSpecError(f"{name} liste olmali")
    return tuple(_text(v, f"{name}[]") for v in value)


def load_field_registry(path: str | Path) -> dict[str, dict]:
    data = _obj(json.loads(Path(path).read_text(encoding="utf-8")), "field registry")
    fields = _obj(data.get("fields"), "fields")
    if not fields:
        raise RatioSpecError("field registry bos olamaz")
    for fname, fdef in fields.items():
        fdef = _obj(fdef, f"fields.{fname}")
        _text(fdef.get("tier"), f"fields.{fname}.tier")
        _text(fdef.get("flow"), f"fields.{fname}.flow")
    return {str(k): dict(v) for k, v in fields.items()}


def _formula_names(formula: str, ratio_name: str) -> set[str]:
    """Identifiers a formula reads, after rejecting disallowed calls."""
    try:
        tree = ast.parse(formula, mode="eval")
    except SyntaxError as exc:
        raise RatioSpecError(f"{ratio_name}: formul ayristirilamadi") from exc

    names: set[str] = set()
    called: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fn = node.func.id if isinstance(node.func, ast.Name) else None
            if fn is None or fn not in ALLOWED_FUNCS:
                raise RatioSpecError(f"{ratio_name}: izin verilmeyen fonksiyon {fn!r}")
            called.add(fn)
        elif isinstance(node, ast.Name):
            names.add(node.id)
    return names - called


def _parse_anchor(raw: Any, name: str, direction: str | None) -> Anchor | None:
    if raw is None:
        return None
    obj = _obj(raw, f"{name}.anchor")
    weak = _number(obj.get("weak"), f"{name}.anchor.weak")
    strong = _number(obj.get("strong"), f"{name}.anchor.strong")
    if weak == strong:
        raise RatioSpecError(f"{name}.anchor weak ve strong esit olamaz")
    if direction == "HIGHER_BETTER" and strong <= weak:
        raise RatioSpecError(f"{name}.anchor: HIGHER_BETTER icin strong > weak olmali")
    if direction == "LOWER_BETTER" and strong >= weak:
        raise RatioSpecError(f"{name}.anchor: LOWER_BETTER icin strong < weak olmali")
    if direction == "BAND":
        raise RatioSpecError(f"{name}: BAND rasyosu anchor tasiyamaz, band kullanir")
    return Anchor(weak=weak, strong=strong)


def load_ratio_set(ratios_path: str | Path, fields_path: str | Path) -> RatioSet:
    data = _obj(json.loads(Path(ratios_path).read_text(encoding="utf-8")), "ratio set")
    meta = _obj(data.get("meta"), "meta")
    families = _obj(meta.get("families"), "meta.families")
    groups = frozenset(_str_tuple(meta.get("sector_groups"), "meta.sector_groups"))
    if not groups:
        raise RatioSpecError("meta.sector_groups bos olamaz")

    registry = load_field_registry(fields_path)
    raw_ratios = _obj(data.get("ratios"), "ratios")
    if not raw_ratios:
        raise RatioSpecError("ratios bos olamaz")

    specs: dict[str, RatioSpec] = {}
    order: list[str] = []
    defined_so_far: set[str] = set()

    for name, raw in raw_ratios.items():
        raw = _obj(raw, f"ratios.{name}")
        role = raw.get("role", ROLE_SCORED)
        if role not in (ROLE_SCORED, ROLE_INTERMEDIATE):
            raise RatioSpecError(f"{name}: gecersiz role {role!r}")

        family = _text(raw.get("family"), f"{name}.family")
        if family not in families:
            raise RatioSpecError(f"{name}: meta.families icinde olmayan aile {family!r}")
        pillar = str(families[family])

        formula = _text(raw.get("formula"), f"{name}.formula")
        requires = _str_tuple(raw.get("requires"), f"{name}.requires")
        domain = _str_tuple(raw.get("domain"), f"{name}.domain")

        unknown_fields = [f for f in requires if f not in registry]
        if unknown_fields:
            raise RatioSpecError(
                f"{name}: alan kaydinda olmayan alan(lar): {sorted(unknown_fields)}"
            )

        # Every identifier a formula reads must be either a registry field or a
        # ratio already defined above it.  This is what keeps intermediates in
        # dependency order instead of relying on dict iteration luck.
        for ident in sorted(_formula_names(formula, name)):
            if ident in registry or ident in defined_so_far:
                continue
            raise RatioSpecError(
                f"{name}: formul tanimsiz {ident!r} okuyor "
                f"(alan kaydinda yok ve bu satirdan once tanimlanmamis)"
            )

        direction = raw.get("direction")
        out_of_domain = raw.get("out_of_domain", "MISSING")
        band = raw.get("band")
        applies_to: frozenset[str] = frozenset()

        if role == ROLE_SCORED:
            direction = _text(direction, f"{name}.direction")
            if direction not in DIRECTIONS:
                raise RatioSpecError(f"{name}: gecersiz direction {direction!r}")
            if out_of_domain not in OUT_OF_DOMAIN:
                raise RatioSpecError(f"{name}: gecersiz out_of_domain {out_of_domain!r}")
            applies_to = frozenset(_str_tuple(raw.get("applies_to"), f"{name}.applies_to"))
            if not applies_to:
                raise RatioSpecError(f"{name}: applies_to bos olamaz")
            unknown_groups = applies_to - groups
            if unknown_groups:
                raise RatioSpecError(f"{name}: bilinmeyen grup(lar) {sorted(unknown_groups)}")
            if direction == "BAND":
                bobj = _obj(band, f"{name}.band")
                low = _number(bobj.get("low"), f"{name}.band.low")
                high = _number(bobj.get("high"), f"{name}.band.high")
                if low >= high:
                    raise RatioSpecError(f"{name}.band: low < high olmali")
                band = {"low": low, "high": high}
            elif band is not None:
                raise RatioSpecError(f"{name}: band yalniz BAND rasyosunda olabilir")
        else:
            direction = None
            band = None

        anchor = _parse_anchor(raw.get("anchor"), name, direction)

        transform = raw.get("transform")
        if transform not in TRANSFORMS:
            raise RatioSpecError(f"{name}: gecersiz transform {transform!r}")
        clip = raw.get("clip")
        if transform == "clip":
            cobj = _obj(clip, f"{name}.clip")
            clip = {
                "low": _number(cobj.get("low"), f"{name}.clip.low"),
                "high": _number(cobj.get("high"), f"{name}.clip.high"),
            }
            if clip["low"] >= clip["high"]:
                raise RatioSpecError(f"{name}.clip: low < high olmali")
        elif clip is not None:
            raise RatioSpecError(f"{name}: clip yalniz transform=clip ile olabilir")

        winsor = _number(raw.get("winsor", 0.02), f"{name}.winsor")
        if not 0.0 <= winsor < 0.5:
            raise RatioSpecError(f"{name}.winsor [0, 0.5) araliginda olmali")

        specs[name] = RatioSpec(
            name=name, role=role, pillar=pillar, family=family, formula=formula,
            requires=requires, domain=domain, direction=direction,
            out_of_domain=out_of_domain, anchor=anchor, band=band,
            applies_to=applies_to, winsor=winsor, transform=transform, clip=clip,
        )
        order.append(name)
        defined_so_far.add(name)

    all_pillars = {str(p) for p in families.values()}

    raw_composites = _obj(meta.get("composites"), "meta.composites")
    if not raw_composites:
        raise RatioSpecError("meta.composites bos olamaz")
    composites: dict[str, tuple[str, ...]] = {}
    seen_pillars: set[str] = set()
    for cname, pillars in raw_composites.items():
        plist = _str_tuple(pillars, f"meta.composites.{cname}")
        if not plist:
            raise RatioSpecError(f"meta.composites.{cname} bos olamaz")
        unknown = set(plist) - all_pillars
        if unknown:
            raise RatioSpecError(f"meta.composites.{cname}: bilinmeyen pillar {sorted(unknown)}")
        overlap = seen_pillars & set(plist)
        if overlap:
            raise RatioSpecError(
                f"meta.composites.{cname}: pillar birden fazla kompozitte {sorted(overlap)}"
            )
        seen_pillars |= set(plist)
        composites[str(cname)] = plist
    missing_pillars = all_pillars - seen_pillars
    if missing_pillars:
        raise RatioSpecError(f"hicbir kompozite girmeyen pillar(lar): {sorted(missing_pillars)}")

    shares_obj = _obj(meta.get("pillar_shares"), "meta.pillar_shares")
    default_shares = _obj(shares_obj.get("default"), "meta.pillar_shares.default")
    parsed_default = {
        str(k): _number(v, f"meta.pillar_shares.default.{k}") for k, v in default_shares.items()
    }
    unknown = set(parsed_default) - all_pillars
    if unknown:
        raise RatioSpecError(f"meta.pillar_shares.default: bilinmeyen pillar {sorted(unknown)}")
    absent = all_pillars - set(parsed_default)
    if absent:
        raise RatioSpecError(f"meta.pillar_shares.default eksik pillar: {sorted(absent)}")
    if any(v < 0 for v in parsed_default.values()):
        raise RatioSpecError("meta.pillar_shares.default negatif pay tasiyamaz")

    by_group_raw = shares_obj.get("by_group") or {}
    by_group: dict[str, dict[str, float]] = {}
    for gname, gshares in _obj(by_group_raw, "meta.pillar_shares.by_group").items():
        if gname not in groups:
            raise RatioSpecError(f"meta.pillar_shares.by_group: bilinmeyen grup {gname!r}")
        parsed = {
            str(k): _number(v, f"meta.pillar_shares.by_group.{gname}.{k}")
            for k, v in _obj(gshares, f"meta.pillar_shares.by_group.{gname}").items()
        }
        if set(parsed) != all_pillars:
            raise RatioSpecError(
                f"meta.pillar_shares.by_group.{gname}: pillar kumesi default ile ayni olmali"
            )
        if any(v < 0 for v in parsed.values()):
            raise RatioSpecError(f"meta.pillar_shares.by_group.{gname} negatif pay tasiyamaz")
        by_group[str(gname)] = parsed

    ratio_set = RatioSet(
        version=_text(meta.get("ratio_set_version"), "meta.ratio_set_version"),
        field_set_version=_text(meta.get("field_set_version"), "meta.field_set_version"),
        families={str(k): str(v) for k, v in families.items()},
        sector_groups=groups,
        specs=specs,
        order=tuple(order),
        _composites=composites,
        _pillar_shares_default=parsed_default,
        _pillar_shares_by_group=by_group,
    )

    # A sector group with no applicable ratio would score every one of its
    # companies as YETERSIZ_KAPSAM forever, silently.
    for group in sorted(groups):
        if not ratio_set.applicable(group):
            raise RatioSpecError(f"{group}: hicbir rasyo uygulanabilir degil")
        shares = ratio_set.pillar_shares(group)
        live = {
            s.pillar for s in ratio_set.applicable(group) if shares.get(s.pillar, 0.0) > 0
        }
        for cname, pillars in composites.items():
            if not (live & set(pillars)):
                raise RatioSpecError(
                    f"{group}: {cname!r} kompoziti icin payi sifirdan buyuk hicbir "
                    f"pillar uygulanabilir degil"
                )

    return ratio_set


def coverage_report(ratio_set: RatioSet, registry: Mapping[str, dict]) -> dict[str, dict]:
    """Per sector group: how many ratios apply, and what blocks the rest.

    ``blocked_by_tier`` counts applicable ratios that cannot be computed until a
    field of that tier is actually populated.  This is the ingestion backlog
    expressed in the currency that matters: ratios unlocked per field landed.
    """
    out: dict[str, dict] = {}
    for group in sorted(ratio_set.sector_groups):
        applicable = ratio_set.applicable(group)
        blocked: dict[str, set[str]] = {}
        for spec in applicable:
            for fld in spec.requires:
                tier = registry[fld]["tier"]
                if tier == "CURRENT":
                    continue
                blocked.setdefault(tier, set()).add(spec.name)
        out[group] = {
            "applicable": len(applicable),
            "families": len(ratio_set.families_of(group)),
            "computable_today": len(
                [s for s in applicable
                 if all(registry[f]["tier"] == "CURRENT" for f in s.requires)]
            ),
            "blocked_by_tier": {k: len(v) for k, v in sorted(blocked.items())},
        }
    return out
```

### `src/ratio_engine/calc.py`

Formülü beş sonuçtan birine çevirir. Sıra önemli: uygulanabilirlik → gerekli alanlar → domain koruması → formül.

```python
from __future__ import annotations

"""v2 ratio computation: three outcomes where v1 had one.

v1 collapsed every failure into a single ``is_na`` boolean
(``ratios_calc.compute_ratios_for_ticker``).  That conflated three unrelated
situations, and the consequence was measured on the live code: a debt-free
company has no interest expense, so ``INTEREST_COVERAGE`` went NA, the NaN
propagated through ``rsc_scoring._wmean`` and wiped ``rsc_core_norm`` entirely,
and ``run_daily_pipeline`` then filled the resulting NaN M1 with 0.0.  The
company was scored zero on quality for the crime of having no debt.

v2 separates them::

    NOT_APPLICABLE  the ratio is meaningless here (a service business has no
                    inventory, so DIO is not a bad score - it is no score).
                    Leaves the denominator entirely.
    MISSING         a required field is null, or a cross-quarter aggregate
                    could not be formed. Stays in the denominator and lowers
                    coverage, because this is genuinely unmeasured.
    BEST / WORST    mathematically undefined but economically unambiguous.
                    Counts as measured and carries a score.
    OK              computed.

The AST evaluator, ``QuarterSeries`` and the field-derivation helper come from
``ratio_engine.evaluator``, vendored unchanged out of the upstream project; only
the outcome contract here is new.
"""

from dataclasses import dataclass
from datetime import date
from typing import Any, Iterable, Mapping, Sequence

from ratio_engine.spec import RatioSet, RatioSpec
from ratio_engine.evaluator import (
    QuarterSeries,
    derive_fields_per_ticker,
    safe_eval_condition,
    safe_eval_expr,
    _is_finite,
)


STATUS_OK = "OK"
STATUS_MISSING = "MISSING"
STATUS_BEST = "BEST"
STATUS_WORST = "WORST"
STATUS_NOT_APPLICABLE = "NOT_APPLICABLE"


class RatioCalcV2Error(ValueError):
    pass


@dataclass(frozen=True)
class RatioOutcome:
    ticker: str
    period_end: date
    version_tag: str
    ratio_name: str
    value: float | None
    status: str

    def __post_init__(self) -> None:
        if self.status == STATUS_OK and not _is_finite(self.value):
            raise RatioCalcV2Error(
                f"{self.ticker}/{self.ratio_name}: status OK ise deger sonlu olmali"
            )
        if self.status != STATUS_OK and self.value is not None:
            raise RatioCalcV2Error(
                f"{self.ticker}/{self.ratio_name}: status {self.status} ise deger None olmali"
            )


def _requires_present(spec: RatioSpec, env: Mapping[str, Any]) -> bool:
    """True when every declared field is present on the current period row.

    This is the fast path for a field that is simply not ingested yet.  A field
    that exists now but is absent in an earlier quarter is caught later, when
    the cross-quarter aggregate returns None.
    """
    for field in spec.requires:
        if field not in env or env[field] is None:
            return False
    return True


def _domain_holds(spec: RatioSpec, env: Mapping[str, Any], qs: QuarterSeries, pe: date) -> bool | None:
    """True/False for the domain guard, or None when it cannot be evaluated.

    A guard that raises means we cannot tell whether the ratio is in domain, so
    the outcome is MISSING rather than an assumed best or worst case.
    """
    for rule in spec.domain:
        try:
            if not safe_eval_condition(rule, dict(env), qs, pe):
                return False
        except Exception:
            return None
    return True


def _evaluate(spec: RatioSpec, env: Mapping[str, Any], qs: QuarterSeries, pe: date) -> float | None:
    try:
        value = safe_eval_expr(spec.formula, dict(env), qs, pe)
    except Exception:
        return None
    return float(value) if _is_finite(value) else None


def resolve_ratio(
    spec: RatioSpec,
    env: Mapping[str, Any],
    qs: QuarterSeries,
    pe: date,
    group: str,
) -> tuple[float | None, str]:
    """Resolve one ratio for one period into (value, status).

    Order matters: applicability first (a ratio that does not apply is never
    "missing"), then required fields, then the domain guard, then the formula.
    """
    if spec.is_scored and not spec.applicable_to(group):
        return None, STATUS_NOT_APPLICABLE

    if not _requires_present(spec, env):
        return None, STATUS_MISSING

    holds = _domain_holds(spec, env, qs, pe)
    if holds is None:
        return None, STATUS_MISSING
    if not holds:
        if spec.out_of_domain == STATUS_NOT_APPLICABLE:
            return None, STATUS_NOT_APPLICABLE
        if spec.out_of_domain == STATUS_BEST:
            return None, STATUS_BEST
        if spec.out_of_domain == STATUS_WORST:
            return None, STATUS_WORST
        return None, STATUS_MISSING

    value = _evaluate(spec, env, qs, pe)
    if value is None:
        return None, STATUS_MISSING
    return value, STATUS_OK


def compute_ratios_for_ticker(
    ticker: str,
    rows: Sequence[Mapping[str, Any]],
    ratio_set: RatioSet,
    group: str,
    price_map: Mapping[tuple[str, date], float] | None = None,
) -> list[RatioOutcome]:
    """Compute every scored ratio for one ticker across its quarters.

    Intermediates are evaluated in declaration order and injected into the
    environment so later ratios can read them by name, but they never produce
    an outcome row: they are plumbing, not measurements.  v1 had no such role
    and faked it by making ``EV_PROXY`` a VAL ratio that a later filter had to
    exclude by hand.
    """
    if group not in ratio_set.sector_groups:
        raise RatioCalcV2Error(f"bilinmeyen sektor grubu: {group!r}")

    prepared = [dict(r) for r in rows]
    for rec in prepared:
        for key, value in list(rec.items()):
            if value is not None and not isinstance(value, (str, date)):
                try:
                    if value != value:  # NaN
                        rec[key] = None
                except Exception:
                    pass
    prepared = derive_fields_per_ticker(prepared)
    qs = QuarterSeries(prepared)
    prices = price_map or {}

    out: list[RatioOutcome] = []
    for rec in prepared:
        pe = rec["period_end"]
        version_tag = str(rec.get("version_tag", "ORIGINAL"))
        t0 = rec.get("t0_date")
        env: dict[str, Any] = dict(rec)
        env["price"] = prices.get((ticker, t0)) if t0 is not None else None

        for name in ratio_set.order:
            spec = ratio_set.specs[name]
            value, status = resolve_ratio(spec, env, qs, pe, group)
            # Intermediates feed the environment; a failed one leaves None
            # behind so dependants resolve to MISSING rather than inventing a
            # substitute value.
            env[name] = value
            if spec.is_scored:
                out.append(
                    RatioOutcome(
                        ticker=ticker,
                        period_end=pe,
                        version_tag=version_tag,
                        ratio_name=name,
                        value=value,
                        status=status,
                    )
                )
    return out


def status_summary(outcomes: Iterable[RatioOutcome]) -> dict[str, int]:
    counts: dict[str, int] = {
        STATUS_OK: 0, STATUS_MISSING: 0, STATUS_BEST: 0,
        STATUS_WORST: 0, STATUS_NOT_APPLICABLE: 0,
    }
    for o in outcomes:
        counts[o.status] += 1
    return counts
```

### `src/ratio_engine/scoring.py`

Aile normalizasyonlu kesitsel skorlama, üç kompozit, açık kapsam.

```python
from __future__ import annotations

"""v2 scoring: family-normalised, coverage-explicit, no NaN propagation.

Three v1 defects this replaces, each measured on the live code rather than
inferred:

1. A single missing CORE ratio wiped the whole score.  ``rsc_scoring._wmean``
   summed ``score_1_10`` with numpy, so one NaN made ``rsc_core_norm`` NaN for
   the company; ``run_daily_pipeline`` then filled the NaN M1 with 0.0.

2. A pillar's share of the score scaled with how many ratios it contained,
   because ``_policy_weight`` handed ``pillar_w * ratio_w`` to every ratio and
   ``_wmean`` divided by the weight sum.  Adding ratios silently reweighted,
   which is why the v1 set could not grow.

3. ``good_count_ge8`` was an absolute count against a fixed threshold of 5 and
   ``ek1`` divided by a hardcoded 18.  With 10 eligible ratios a bank could not
   push ``ek1`` past 0.56 and tripped the veto on 50% of its ratios against
   19% for an industrial with 26.

The v2 weight of a ratio, inside one composite, is::

    w = pillar_share / families_applicable(pillar) / ratios_applicable(family)

renormalised so the composite's applicable weights sum to 1.  Adding a ratio to
a family therefore redistributes weight *inside that family only*; the pillar's
share is whatever config says and nothing else.  Coverage is then the weight
actually observed, which turns "how much of this company did we measure" into a
number the rest of the system can read instead of a silence.
"""

from dataclasses import dataclass, field as dc_field
from typing import Iterable, Mapping, Sequence
import math

from ratio_engine.spec import RatioSet, RatioSpec


STATUS_OK = "OK"
STATUS_MISSING = "MISSING"
STATUS_BEST = "BEST"
STATUS_WORST = "WORST"
STATUS_NOT_APPLICABLE = "NOT_APPLICABLE"
VALID_STATUSES = frozenset(
    {STATUS_OK, STATUS_MISSING, STATUS_BEST, STATUS_WORST, STATUS_NOT_APPLICABLE}
)

RESULT_OK = "OK"
RESULT_INSUFFICIENT_COVERAGE = "YETERSIZ_KAPSAM"

# A determinate out-of-domain outcome is knowledge, not absence: it carries a
# score and counts towards coverage.
DETERMINATE = {STATUS_BEST: 1.0, STATUS_WORST: 0.0}

GOOD_SCORE_THRESHOLD = 0.80
DEFAULT_MIN_COVERAGE = 0.40
DEFAULT_MIN_POOL = 5
ANCHOR_BLEND = 0.40
MAD_SCALE = 1.4826


class ScoringError(ValueError):
    pass


@dataclass(frozen=True)
class RatioObservation:
    ticker: str
    ratio_name: str
    value: float | None
    status: str

    def __post_init__(self) -> None:
        if self.status not in VALID_STATUSES:
            raise ScoringError(
                f"{self.ticker}/{self.ratio_name}: gecersiz status {self.status!r}"
            )
        if self.status == STATUS_OK and not _is_finite(self.value):
            raise ScoringError(
                f"{self.ticker}/{self.ratio_name}: status OK ise deger sonlu olmali"
            )


@dataclass(frozen=True)
class CompositeResult:
    status: str
    score: float | None
    coverage: float
    good_ratio: float
    measured: int
    applicable: int


@dataclass(frozen=True)
class TickerResult:
    ticker: str
    group: str
    composites: Mapping[str, CompositeResult]
    ratio_scores: Mapping[str, float] = dc_field(default_factory=dict)

    def score(self, composite: str) -> float | None:
        result = self.composites.get(composite)
        return None if result is None else result.score


def _is_finite(value: object) -> bool:
    if value is None or isinstance(value, bool):
        return False
    try:
        out = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(out)


def _median(values: Sequence[float]) -> float:
    ordered = sorted(values)
    n = len(ordered)
    if n == 0:
        raise ScoringError("medyan bos dizide hesaplanamaz")
    mid = n // 2
    return ordered[mid] if n % 2 else (ordered[mid - 1] + ordered[mid]) / 2.0


def _winsorize(values: Sequence[float], p: float) -> list[float]:
    if p <= 0 or len(values) < 3:
        return list(values)
    ordered = sorted(values)
    lo = ordered[max(0, int(math.floor(p * (len(ordered) - 1))))]
    hi = ordered[min(len(ordered) - 1, int(math.ceil((1 - p) * (len(ordered) - 1))))]
    return [min(max(v, lo), hi) for v in values]


def _transform(spec: RatioSpec, value: float) -> float:
    if spec.transform == "signed_log":
        return math.copysign(math.log1p(abs(value)), value)
    if spec.transform == "clip" and spec.clip is not None:
        return min(max(value, spec.clip["low"]), spec.clip["high"])
    return value


def _orient(spec: RatioSpec, value: float) -> float:
    """Map a transformed value onto a 'higher is better' axis."""
    if spec.direction == "LOWER_BETTER":
        return -value
    if spec.direction == "BAND" and spec.band is not None:
        centre = (spec.band["low"] + spec.band["high"]) / 2.0
        return -abs(value - centre)
    return value


def _band_absolute(spec: RatioSpec, value: float) -> float | None:
    """Absolute score for a BAND ratio: inside the band is good on its own terms."""
    if spec.band is None:
        return None
    low, high = spec.band["low"], spec.band["high"]
    half = (high - low) / 2.0
    if half <= 0:
        return None
    if low <= value <= high:
        return 0.80
    excess = (low - value) if value < low else (value - high)
    return max(0.05, 0.80 - 0.50 * (excess / half))


def _relative_scores(spec: RatioSpec, pool: Mapping[str, float]) -> dict[str, float]:
    """Robust cross-sectional score in [0, 1] for one ratio over one pool.

    Median/MAD rather than mean/std: BIST cross-sections are fat-tailed and a
    winsorised standard deviation is still dragged by whatever survived the
    winsorisation.
    """
    tickers = list(pool)
    raw = _winsorize([_transform(spec, pool[t]) for t in tickers], spec.winsor)
    oriented = [_orient(spec, v) for v in raw]

    centre = _median(oriented)
    mad = _median([abs(v - centre) for v in oriented])

    if mad > 0:
        scale = MAD_SCALE * mad
        return {
            t: 1.0 / (1.0 + math.exp(-((v - centre) / scale)))
            for t, v in zip(tickers, oriented)
        }

    # Degenerate spread (identical values, or a very small pool). Fall back to
    # a rank so the ratio stays usable instead of collapsing to a constant.
    if len(tickers) == 1:
        return {tickers[0]: 0.5}
    order = sorted(range(len(oriented)), key=lambda i: oriented[i])
    ranks = {tickers[idx]: pos / (len(order) - 1) for pos, idx in enumerate(order)}
    # Ties must not be broken by input order.
    by_value: dict[float, list[str]] = {}
    for t, v in zip(tickers, oriented):
        by_value.setdefault(v, []).append(t)
    for tied in by_value.values():
        if len(tied) > 1:
            shared = sum(ranks[t] for t in tied) / len(tied)
            for t in tied:
                ranks[t] = shared
    return ranks


def _blend_anchor(spec: RatioSpec, relative: float, raw_value: float) -> float:
    if spec.anchor is not None:
        absolute: float | None = spec.anchor.score(raw_value)
    elif spec.direction == "BAND":
        absolute = _band_absolute(spec, raw_value)
    else:
        absolute = None
    if absolute is None:
        return relative
    return ANCHOR_BLEND * absolute + (1.0 - ANCHOR_BLEND) * relative


def compute_ratio_weights(
    ratio_set: RatioSet, group: str, composite: str
) -> dict[str, float]:
    """Applicable-ratio weights for one composite of one sector group; sum to 1.

    The share a pillar carries is fixed by config; families split it evenly and
    ratios split their family's share evenly. This is the property that lets the
    ratio set grow without silently reweighting anything.
    """
    pillars = set(ratio_set.pillar_of_composite(composite))
    shares = ratio_set.pillar_shares(group)

    by_pillar: dict[str, dict[str, list[RatioSpec]]] = {}
    for spec in ratio_set.applicable(group):
        if spec.pillar not in pillars:
            continue
        by_pillar.setdefault(spec.pillar, {}).setdefault(spec.family, []).append(spec)

    live = {p: shares.get(p, 0.0) for p in by_pillar if shares.get(p, 0.0) > 0}
    total = sum(live.values())
    if total <= 0:
        return {}

    weights: dict[str, float] = {}
    for pillar, share in live.items():
        families = by_pillar[pillar]
        per_family = (share / total) / len(families)
        for specs in families.values():
            per_ratio = per_family / len(specs)
            for spec in specs:
                weights[spec.name] = per_ratio
    return weights


def score_universe(
    ratio_set: RatioSet,
    observations: Iterable[RatioObservation],
    group_of: Mapping[str, str],
    *,
    min_coverage: float = DEFAULT_MIN_COVERAGE,
    min_pool: int = DEFAULT_MIN_POOL,
) -> dict[str, TickerResult]:
    """Score every ticker present in ``observations`` for one period.

    Each ratio is ranked inside its own sector-group pool; a pool smaller than
    ``min_pool`` falls back to the full universe, because a percentile over
    three companies is not a percentile.
    """
    obs_list = list(observations)
    tickers = sorted({o.ticker for o in obs_list})
    unknown = [t for t in tickers if t not in group_of]
    if unknown:
        raise ScoringError(f"sektor grubu bilinmeyen ticker(lar): {unknown}")

    stray = sorted({o.ratio_name for o in obs_list} - set(ratio_set.specs))
    if stray:
        raise ScoringError(f"rasyo setinde olmayan rasyo(lar): {stray}")

    by_ratio: dict[str, dict[str, RatioObservation]] = {}
    for o in obs_list:
        by_ratio.setdefault(o.ratio_name, {})[o.ticker] = o

    group_members: dict[str, list[str]] = {}
    for t in tickers:
        group_members.setdefault(group_of[t], []).append(t)

    # --- 1) per-ratio cross-sectional scores ------------------------------
    ratio_scores: dict[str, dict[str, float]] = {}
    for ratio_name, per_ticker in by_ratio.items():
        spec = ratio_set.specs[ratio_name]
        if not spec.is_scored:
            continue
        ok_values = {
            t: float(o.value)
            for t, o in per_ticker.items()
            if o.status == STATUS_OK and spec.applicable_to(group_of[t])
        }
        if not ok_values:
            continue
        scores: dict[str, float] = {}
        for grp, members in group_members.items():
            pool = {t: v for t, v in ok_values.items() if t in members}
            if not pool:
                continue
            if len(pool) < min_pool:
                pool = ok_values  # full-universe fallback
            relative = _relative_scores(spec, pool)
            for t in members:
                if t in ok_values:
                    scores[t] = _blend_anchor(spec, relative[t], ok_values[t])
        ratio_scores[ratio_name] = scores

    # --- 2) composites, in two passes so shrinkage has a target -----------
    composites = ratio_set.composites()
    weights = {
        (g, c): compute_ratio_weights(ratio_set, g, c)
        for g in group_members
        for c in composites
    }

    raw: dict[str, dict[str, tuple[float, float, float, int, int]]] = {}
    for t in tickers:
        grp = group_of[t]
        raw[t] = {}
        for comp_name in composites:
            applicable_w = measured_w = good_w = acc = 0.0
            measured = applicable = 0
            for ratio_name, w in weights[(grp, comp_name)].items():
                o = by_ratio.get(ratio_name, {}).get(t)
                if o is not None and o.status == STATUS_NOT_APPLICABLE:
                    continue  # leaves the denominator entirely
                applicable_w += w
                applicable += 1
                if o is None or o.status == STATUS_MISSING:
                    continue
                if o.status in DETERMINATE:
                    s = DETERMINATE[o.status]
                else:
                    s = ratio_scores.get(ratio_name, {}).get(t)
                    if s is None:
                        continue
                measured_w += w
                measured += 1
                acc += w * s
                if s >= GOOD_SCORE_THRESHOLD:
                    good_w += w
            if applicable_w <= 0:
                raw[t][comp_name] = (0.0, 0.0, 0.0, 0, 0)
                continue
            coverage = measured_w / applicable_w
            mean = (acc / measured_w) if measured_w > 0 else 0.0
            raw[t][comp_name] = (
                mean, coverage, good_w / applicable_w, measured, applicable
            )

    pool_median: dict[str, float] = {}
    for comp_name in composites:
        well_covered = [
            raw[t][comp_name][0] for t in tickers if raw[t][comp_name][1] >= min_coverage
        ]
        pool_median[comp_name] = _median(well_covered) if well_covered else 0.5

    results: dict[str, TickerResult] = {}
    for t in tickers:
        comps: dict[str, CompositeResult] = {}
        for comp_name in composites:
            mean, coverage, good_ratio, measured, applicable = raw[t][comp_name]
            if applicable == 0 or coverage < min_coverage:
                comps[comp_name] = CompositeResult(
                    status=RESULT_INSUFFICIENT_COVERAGE, score=None, coverage=coverage,
                    good_ratio=good_ratio, measured=measured, applicable=applicable,
                )
                continue
            # Partial coverage is pulled towards the cross-section rather than
            # being reported as if fully measured.
            shrunk = coverage * mean + (1.0 - coverage) * pool_median[comp_name]
            comps[comp_name] = CompositeResult(
                status=RESULT_OK, score=min(max(shrunk, 0.0), 1.0), coverage=coverage,
                good_ratio=good_ratio, measured=measured, applicable=applicable,
            )
        results[t] = TickerResult(
            ticker=t, group=group_of[t], composites=comps,
            ratio_scores={r: s[t] for r, s in ratio_scores.items() if t in s},
        )
    return results
```

### `src/ratio_engine/evaluator.py`

Güvenli formül değerlendirici. ratios_calc.py @ adf3f81'den vendor'landı, pandas/PostgreSQL katmanı çıkarıldı.

```python
from __future__ import annotations

"""Safe formula evaluator, vendored from the Total Rasyo project.

Copied verbatim from ``src/analytics/ratios_calc.py`` at commit adf3f81 of
zxc28tarik/TOTAL-RASYO-HESAPLAYICI.  Only the DB and pandas layers were left
behind: ``fill_missing_t0_dates``, ``fetch_financials`` and ``apply_unit_scale``
read from PostgreSQL and are not needed to evaluate a ratio formula.

What remains is pure standard library, which is what lets this package run with
no third-party dependency at all.  If the upstream evaluator changes, this file
does not follow automatically - that is the accepted cost of the split.

The formula language:
  fields          bare identifiers, resolved from the period row
  avg(x)          mean of this quarter and the previous one
  lag(x, n)       value n quarters back          lag4q(x) == lag(x, 4)
  sum4q(x)        trailing four-quarter sum      ttm(x) is an alias
  days_in_period()  calendar length of the quarter, 91 when unknown
  abs, min, max, log, log1p, coalesce, nz
Anything else is rejected at parse time.
"""

import ast
import math
from datetime import date, datetime, timedelta
from typing import List

OPS = {ast.Add: lambda a, b: a + b, ast.Sub: lambda a, b: a - b, ast.Mult: lambda a, b: a * b, ast.Div: lambda a, b: a / b, ast.USub: lambda a: -a}


CMP = {ast.Lt: lambda a, b: a < b, ast.LtE: lambda a, b: a <= b, ast.Gt: lambda a, b: a > b, ast.GtE: lambda a, b: a >= b, ast.Eq: lambda a, b: a == b, ast.NotEq: lambda a, b: a != b, ast.Is: lambda a, b: a is b, ast.IsNot: lambda a, b: a is not b}


ALLOWED_FUNCS = {"avg", "lag", "lag4q", "sum4q", "ttm", "abs", "coalesce", "nz", "days_in_period", "log", "log1p", "max", "min"}


def coalesce(*args):
    for a in args:
        if a is not None:
            return a
    return None


def nz(x, default=0):
    return default if x is None else x


def _is_finite(x):
    try:
        return x is not None and math.isfinite(float(x))
    except Exception:
        return False


def _quarter_end(value: date) -> date:
    if not isinstance(value, date) or isinstance(value, datetime):
        raise ValueError("period_end date olmali")
    quarter = (value.month - 1) // 3
    next_month = quarter * 3 + 4
    year = value.year
    if next_month > 12:
        next_month -= 12
        year += 1
    return date(year, next_month, 1) - timedelta(days=1)


def _shift_quarter_end(value: date, offset: int) -> date:
    anchor = _quarter_end(value)
    q_index = anchor.year * 4 + ((anchor.month - 1) // 3) + offset
    year, quarter = divmod(q_index, 4)
    month = quarter * 3 + 3
    if month == 12:
        return date(year, 12, 31)
    return date(year, month + 1, 1) - timedelta(days=1)


def _row_version_key(row: dict) -> tuple:
    # Legacy core.financials_quarterly has no published_at. Use its available
    # report/t0 trace deterministically instead of physical row order.
    return (
        row.get("t0_date") or row.get("report_date") or date.min,
        str(row.get("version_tag") or ""),
    )


class QuarterSeries:
    def __init__(self, rows: List[dict]):
        selected: dict[date, dict] = {}
        for row in rows:
            pe = row.get("period_end")
            if not isinstance(pe, date) or isinstance(pe, datetime):
                raise ValueError("QuarterSeries period_end date olmali")
            pe = _quarter_end(pe)
            previous = selected.get(pe)
            if previous is None or _row_version_key(row) > _row_version_key(previous):
                selected[pe] = row
        self.by_period = selected
        self.rows = [selected[pe] for pe in sorted(selected)]

    def get(self, pe: date, field: str):
        row = self.by_period.get(_quarter_end(pe))
        return None if row is None else row.get(field)

    def lag(self, pe: date, field: str, n: int):
        if isinstance(n, bool) or not isinstance(n, int) or n < 0:
            return None
        return self.get(_shift_quarter_end(pe, -n), field)

    def avg(self, pe: date, field: str):
        x0 = self.get(pe, field)
        x1 = self.lag(pe, field, 1)
        if x0 is None and x1 is None:
            return None
        if x0 is None:
            return x1
        if x1 is None:
            return x0
        return (x0 + x1) / 2.0

    def sum4q(self, pe: date, field: str):
        vals = []
        for offset in (-3, -2, -1, 0):
            v = self.get(_shift_quarter_end(pe, offset), field)
            if v is None:
                return None
            vals.append(float(v))
        return float(sum(vals))

    def days_in_period(self, pe: date) -> int:
        current = _quarter_end(pe)
        previous = _shift_quarter_end(current, -1)
        if previous not in self.by_period:
            return 91
        d = (current - previous).days
        return int(d) if 60 <= d <= 120 else 91


def safe_eval_expr(expr: str, env: dict, qs: QuarterSeries, pe: date):
    tree = ast.parse(expr, mode="eval")

    def eval_node(node):
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            return env.get(node.id)
        if isinstance(node, ast.UnaryOp) and type(node.op) in OPS:
            v = eval_node(node.operand)
            return None if v is None else OPS[type(node.op)](v)
        if isinstance(node, ast.BinOp) and type(node.op) in OPS:
            a, b = eval_node(node.left), eval_node(node.right)
            if a is None or b is None:
                return None
            if isinstance(node.op, ast.Div) and float(b) == 0.0:
                return None
            return OPS[type(node.op)](a, b)
        if isinstance(node, ast.Call):
            fn = node.func.id if isinstance(node.func, ast.Name) else None
            if fn not in ALLOWED_FUNCS:
                raise ValueError(f"Function not allowed: {fn}")
            if fn in {"avg", "lag", "lag4q", "sum4q", "ttm"}:
                if len(node.args) < 1:
                    return None
                a0 = node.args[0]
                field = a0.id if isinstance(a0, ast.Name) else (a0.value if isinstance(a0, ast.Constant) and isinstance(a0.value, str) else None)
                if not field:
                    return None
                if fn == "avg":
                    return qs.avg(pe, field)
                if fn == "lag":
                    if len(node.args) < 2:
                        return None
                    n = eval_node(node.args[1])
                    return None if n is None else qs.lag(pe, field, int(n))
                if fn == "lag4q":
                    return qs.lag(pe, field, 4)
                return qs.sum4q(pe, field)
            args = [eval_node(a) for a in node.args]
            if fn == "abs":
                return None if args[0] is None else abs(float(args[0]))
            if fn == "coalesce":
                return coalesce(*args)
            if fn == "nz":
                return nz(args[0], 0 if len(args) == 1 else args[1])
            if fn == "days_in_period":
                return qs.days_in_period(pe)
            if fn == "log":
                return None if args[0] is None or args[0] <= 0 else math.log(float(args[0]))
            if fn == "log1p":
                return None if args[0] is None else math.log1p(float(args[0]))
            if fn == "max":
                aa = [a for a in args if a is not None]
                return None if not aa else float(max(aa))
            if fn == "min":
                aa = [a for a in args if a is not None]
                return None if not aa else float(min(aa))
        raise ValueError(f"Unsupported expression: {ast.dump(node)}")

    return eval_node(tree.body)


def safe_eval_condition(cond: str, env: dict, qs: QuarterSeries, pe: date) -> bool:
    s = cond.strip().replace(" is not null", " is not None").replace(" is null", " is None")
    tree = ast.parse(s, mode="eval")

    def eval_node(node):
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            return env.get(node.id)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            return not bool(eval_node(node.operand))
        if isinstance(node, ast.BoolOp):
            if isinstance(node.op, ast.And):
                return all(bool(eval_node(v)) for v in node.values)
            if isinstance(node.op, ast.Or):
                return any(bool(eval_node(v)) for v in node.values)
        if isinstance(node, ast.Compare):
            left = eval_node(node.left)
            for op_node, comp in zip(node.ops, node.comparators):
                right = eval_node(comp)
                op_type = type(op_node)
                if op_type in (ast.Is, ast.IsNot):
                    ok = CMP[op_type](left, right)
                else:
                    ok = False if left is None or right is None else CMP[op_type](left, right)
                if not ok:
                    return False
                left = right
            return True
        if isinstance(node, (ast.Call, ast.BinOp, ast.UnaryOp)):
            return safe_eval_expr(ast.unparse(node), env, qs, pe)
        return bool(eval_node(node))

    return bool(eval_node(tree.body))


def derive_fields_per_ticker(rows: List[dict]) -> List[dict]:
    for r in rows:
        if r.get("gross_profit") is None:
            rev, cogs = r.get("revenue"), r.get("cogs")
            if rev is not None and cogs is not None:
                r["gross_profit"] = rev - cogs
    return rows
```

### `src/ratio_engine/__init__.py`

Paket yüzeyi.

```python
"""A fail-closed financial ratio engine for Borsa Istanbul.

    spec       ratio-set schema, loaded and validated fail-closed
    calc       formula evaluation into one of five explicit outcomes
    scoring    family-normalised cross-sectional scoring
    evaluator  the safe formula evaluator (vendored, pure stdlib)
"""
from ratio_engine.spec import (
    RatioSet, RatioSpec, RatioSpecError, coverage_report, load_field_registry,
    load_ratio_set,
)
from ratio_engine.calc import RatioOutcome, compute_ratios_for_ticker, resolve_ratio
from ratio_engine.scoring import (
    CompositeResult, RatioObservation, TickerResult, compute_ratio_weights,
    score_universe,
)

__all__ = [
    "RatioSet", "RatioSpec", "RatioSpecError", "coverage_report",
    "load_field_registry", "load_ratio_set", "RatioOutcome",
    "compute_ratios_for_ticker", "resolve_ratio", "CompositeResult",
    "RatioObservation", "TickerResult", "compute_ratio_weights",
    "score_universe",
]
```

### `config/ratio_fields.v2.json`

48 alan: her biri tier (nereden geliyor) ve flow taşır.

```json
{
  "meta": {
    "field_set_version": "v2",
    "profile": "PROPLUS_TARGET",
    "notes": [
      "Canonical financial fields the v2 ratio set depends on.",
      "Every ratio in ratios.v2.json declares its fields via 'requires'; the loader",
      "rejects any ratio naming a field that is absent from this registry.",
      "'tier' records where the field actually comes from. It is NOT a promise that",
      "the field is populated today - it is the ingestion debt each field carries.",
      "A ratio whose fields are not yet populated resolves to MISSING and lowers",
      "coverage. It never resolves to a fabricated value and never to a silent zero."
    ],
    "tiers": {
      "CURRENT": "already populated today - a core.financials_quarterly column or the core.prices_daily join",
      "KAP_XBRL": "present in official KAP XBRL filings; needs a schema column + semantic mapping",
      "PROPLUS": "available from an InvestingPro Pro+ export; restated-only, CURRENT_KNOWLEDGE lane",
      "KAP_FOOTNOTE": "only in filing footnotes; extraction is unsolved, ratios depending on it stay MISSING",
      "MARKET_EXT": "market series that exists upstream but is not ingested yet (volume)"
    },
    "flows": {
      "PERIOD": "flow item - aggregate with sum4q/ttm across quarters",
      "POINT": "balance-sheet stock - aggregate with avg across period start/end",
      "MARKET": "market observation at t0",
      "DERIVED": "computed from other registry fields, never ingested directly"
    }
  },

  "fields": {
    "revenue":                  {"tier": "CURRENT", "flow": "PERIOD", "sign": "POSITIVE"},
    "cogs":                     {"tier": "CURRENT", "flow": "PERIOD", "sign": "POSITIVE"},
    "gross_profit":             {"tier": "CURRENT", "flow": "PERIOD", "sign": "ANY"},
    "ebit":                     {"tier": "CURRENT", "flow": "PERIOD", "sign": "ANY"},
    "net_income":               {"tier": "CURRENT", "flow": "PERIOD", "sign": "ANY"},
    "interest_exp":             {"tier": "CURRENT", "flow": "PERIOD", "sign": "POSITIVE"},
    "cfo":                      {"tier": "CURRENT", "flow": "PERIOD", "sign": "ANY"},
    "capex":                    {"tier": "CURRENT", "flow": "PERIOD", "sign": "ANY"},

    "total_assets":             {"tier": "CURRENT", "flow": "POINT", "sign": "POSITIVE"},
    "total_equity":             {"tier": "CURRENT", "flow": "POINT", "sign": "ANY"},
    "current_assets":           {"tier": "CURRENT", "flow": "POINT", "sign": "POSITIVE"},
    "current_liabilities":      {"tier": "CURRENT", "flow": "POINT", "sign": "POSITIVE"},
    "cash_and_eq":              {"tier": "CURRENT", "flow": "POINT", "sign": "POSITIVE"},
    "st_investments":           {"tier": "CURRENT", "flow": "POINT", "sign": "POSITIVE"},
    "receivables":              {"tier": "CURRENT", "flow": "POINT", "sign": "POSITIVE"},
    "inventory":                {"tier": "CURRENT", "flow": "POINT", "sign": "POSITIVE"},
    "debt_st":                  {"tier": "CURRENT", "flow": "POINT", "sign": "POSITIVE"},
    "debt_lt":                  {"tier": "CURRENT", "flow": "POINT", "sign": "POSITIVE"},
    "shares_out":               {"tier": "CURRENT", "flow": "POINT", "sign": "POSITIVE"},
    "shares_diluted":           {"tier": "CURRENT", "flow": "POINT", "sign": "POSITIVE"},
    "price":                    {"tier": "CURRENT", "flow": "MARKET", "sign": "POSITIVE"},

    "depreciation_amortization": {
      "tier": "KAP_XBRL", "flow": "PERIOD", "sign": "POSITIVE",
      "unlocks": "EBITDA - the single highest-value missing field. Without it EV/EBITDA, the most used BIST multiple, cannot be computed."
    },
    "tax_expense":              {"tier": "KAP_XBRL", "flow": "PERIOD", "sign": "ANY"},
    "pretax_income":            {"tier": "KAP_XBRL", "flow": "PERIOD", "sign": "ANY"},
    "accounts_payable": {
      "tier": "KAP_XBRL", "flow": "POINT", "sign": "POSITIVE",
      "unlocks": "Real DPO. The v1 set used debt_st (financial debt) as a payables proxy, which is wrong and also corrupts CCC."
    },
    "dividends_paid":           {"tier": "KAP_XBRL", "flow": "PERIOD", "sign": "POSITIVE"},
    "minority_interest":        {"tier": "KAP_XBRL", "flow": "POINT", "sign": "ANY"},
    "lease_liabilities":        {"tier": "KAP_XBRL", "flow": "POINT", "sign": "POSITIVE"},
    "net_ppe":                  {"tier": "KAP_XBRL", "flow": "POINT", "sign": "POSITIVE"},
    "intangibles_goodwill":     {"tier": "KAP_XBRL", "flow": "POINT", "sign": "POSITIVE"},

    "eps_fwd_1y":               {"tier": "PROPLUS", "flow": "MARKET", "sign": "ANY"},
    "eps_fwd_1y_3m_ago":        {"tier": "PROPLUS", "flow": "MARKET", "sign": "ANY"},
    "ebitda_fwd_1y":            {"tier": "PROPLUS", "flow": "MARKET", "sign": "ANY"},
    "revenue_fwd_1y":           {"tier": "PROPLUS", "flow": "MARKET", "sign": "POSITIVE"},
    "eps_surprise_4q_avg":      {"tier": "PROPLUS", "flow": "MARKET", "sign": "ANY"},
    "altman_z":                 {"tier": "PROPLUS", "flow": "MARKET", "sign": "ANY"},
    "beneish_m":                {"tier": "PROPLUS", "flow": "MARKET", "sign": "ANY"},

    "fx_debt": {
      "tier": "KAP_FOOTNOTE", "flow": "POINT", "sign": "POSITIVE",
      "unlocks": "FX debt share. Not available from Pro+ at any tier. Kills BIST companies on a TL move and no profitability ratio warns first."
    },
    "fx_revenue": {
      "tier": "KAP_FOOTNOTE", "flow": "PERIOD", "sign": "POSITIVE",
      "unlocks": "Natural hedge. FX debt is only dangerous without matching FX revenue."
    },

    "adv_60d_try": {
      "tier": "MARKET_EXT", "flow": "MARKET", "sign": "POSITIVE",
      "unlocks": "The trading-liquidity gate. Not a ratio - it decides whether a name is tradeable at all. core.prices_daily.volume exists and yfinance already returns volume; only the wiring is missing."
    },

    "EBITDA": {
      "tier": "KAP_XBRL", "flow": "DERIVED", "sign": "ANY",
      "derived_from": ["ebit", "depreciation_amortization"]
    },
    "MARKET_CAP": {
      "tier": "CURRENT", "flow": "DERIVED", "sign": "POSITIVE",
      "derived_from": ["price", "shares_out"]
    },
    "NET_DEBT": {
      "tier": "CURRENT", "flow": "DERIVED", "sign": "ANY",
      "derived_from": ["debt_st", "debt_lt", "cash_and_eq", "st_investments"]
    },
    "EV": {
      "tier": "CURRENT", "flow": "DERIVED", "sign": "POSITIVE",
      "derived_from": ["MARKET_CAP", "NET_DEBT", "minority_interest"]
    },
    "INVESTED_CAPITAL": {
      "tier": "CURRENT", "flow": "DERIVED", "sign": "ANY",
      "derived_from": ["total_equity", "debt_st", "debt_lt", "cash_and_eq"]
    },
    "NOPAT": {
      "tier": "KAP_XBRL", "flow": "DERIVED", "sign": "ANY",
      "derived_from": ["ebit", "tax_expense", "pretax_income"]
    },
    "TANGIBLE_BOOK": {
      "tier": "KAP_XBRL", "flow": "DERIVED", "sign": "ANY",
      "derived_from": ["total_equity", "intangibles_goodwill"]
    },
    "FCF": {
      "tier": "CURRENT", "flow": "DERIVED", "sign": "ANY",
      "derived_from": ["cfo", "capex"]
    }
  }
}
```

### `config/ratios.v2.json`

67 skorlanan rasyo + 9 ara büyüklük, 19 aile, pillar payları, kompozitler.

```json
{
  "meta": {
    "ratio_set_version": "v2",
    "field_set_version": "v2",
    "profile": "PROPLUS_TARGET",
    "sector_groups": ["BANK", "FINANCIAL", "INSURANCE", "HOLDING", "GYO", "NONFIN"],
    "families": {
      "WORKING_CAPITAL":    "LIQ",
      "CASH_BUFFER":        "LIQ",
      "DEBT_LEVEL":         "LEV",
      "DEBT_SERVICE":       "LEV",
      "DEBT_STRUCTURE":     "LEV",
      "CASH_GENERATION":    "CASH",
      "CASH_CONVERSION":    "CASH",
      "CAPEX_INTENSITY":    "CASH",
      "MARGIN":             "PROFIT",
      "RETURN_ON_CAPITAL":  "PROFIT",
      "WC_CYCLE":           "EFF",
      "ASSET_PRODUCTIVITY": "EFF",
      "TOP_LINE":           "GROWTH",
      "BOTTOM_LINE":        "GROWTH",
      "PER_SHARE":          "GROWTH",
      "EARNINGS_MULTIPLE":  "VAL",
      "CASHFLOW_MULTIPLE":  "VAL",
      "ASSET_MULTIPLE":     "VAL",
      "YIELD":              "VAL"
    },
    "composites": {
      "quality": ["LIQ", "LEV", "CASH", "PROFIT", "EFF"],
      "growth":  ["GROWTH"],
      "value":   ["VAL"]
    },
    "pillar_shares": {
      "default": {"LIQ": 0.12, "LEV": 0.24, "CASH": 0.24, "PROFIT": 0.28, "EFF": 0.12, "GROWTH": 1.0, "VAL": 1.0},
      "by_group": {
        "BANK":      {"LIQ": 0.00, "LEV": 0.30, "CASH": 0.20, "PROFIT": 0.40, "EFF": 0.10, "GROWTH": 1.0, "VAL": 1.0},
        "FINANCIAL": {"LIQ": 0.00, "LEV": 0.30, "CASH": 0.20, "PROFIT": 0.40, "EFF": 0.10, "GROWTH": 1.0, "VAL": 1.0},
        "INSURANCE": {"LIQ": 0.00, "LEV": 0.25, "CASH": 0.20, "PROFIT": 0.45, "EFF": 0.10, "GROWTH": 1.0, "VAL": 1.0}
      },
      "note": [
        "A pillar's share is what this table says and nothing else. It does NOT",
        "scale with how many ratios the pillar contains - that was the v1 defect",
        "where pillar_w * ratio_w was handed to every ratio and then divided by",
        "the weight sum, so a pillar's real share was (ratio count x pillar_w)/sum.",
        "Shares are renormalised over the pillars that actually have data, per",
        "composite. GROWTH and VAL sit alone in their composites, so their raw",
        "share is irrelevant and set to 1.0."
      ]
    },
    "contract": [
      "Families split the pillar share; ratios split the family share. Adding a",
      "ratio therefore never silently reweights a pillar.",
      "",
      "Three distinct outcomes replace v1's single 'na_if' bucket:",
      "  MISSING        - a required field is null. Lowers coverage.",
      "  BEST / WORST   - mathematically undefined but economically unambiguous",
      "                   (a debt-free company has perfect interest coverage).",
      "  NOT_APPLICABLE - meaningless for this company. Leaves the denominator",
      "                   entirely, so it neither helps nor hurts.",
      "",
      "Ratio weights are NEVER fitted. Equal weight inside a family is a",
      "deliberate constraint: ~40 independent quarters of BIST history support",
      "fitting roughly 4-7 parameters, which is spent on the axis weights and",
      "gate thresholds, not on 67 ratio weights.",
      "",
      "Anchors are supplied only where a defensible economic level exists.",
      "Nominal return ratios (ROE/ROA/ROIC) and valuation multiples carry NO",
      "anchor on purpose: under Turkish inflation a nominal 30% ROE may be a",
      "real loss, and a PE of 6 may be an ordinary market level. An invented",
      "anchor is worse than no anchor; those ratios score purely relative.",
      "",
      "There are no *_STABILITY ratios. Stability is not a ratio - it is the",
      "third component of the (level, slope, stability) triple the scoring layer",
      "derives for every ratio over 8 quarters."
    ]
  },

  "ratios": {

    "MARKET_CAP": {
      "role": "INTERMEDIATE", "family": "ASSET_MULTIPLE",
      "formula": "price * shares_out",
      "requires": ["price", "shares_out"],
      "domain": ["price > 0", "shares_out > 0"]
    },
    "NET_DEBT": {
      "role": "INTERMEDIATE", "family": "DEBT_LEVEL",
      "formula": "(nz(debt_st, 0) + nz(debt_lt, 0)) - (nz(cash_and_eq, 0) + nz(st_investments, 0))",
      "requires": ["debt_st", "debt_lt", "cash_and_eq", "st_investments"],
      "domain": []
    },
    "EV": {
      "role": "INTERMEDIATE", "family": "EARNINGS_MULTIPLE",
      "formula": "max(MARKET_CAP + NET_DEBT + nz(minority_interest, 0), 0)",
      "requires": ["price", "shares_out", "debt_st", "debt_lt", "cash_and_eq", "st_investments"],
      "domain": ["MARKET_CAP + NET_DEBT + nz(minority_interest, 0) > 0"]
    },
    "EBITDA_TTM": {
      "role": "INTERMEDIATE", "family": "MARGIN",
      "formula": "sum4q(ebit) + sum4q(depreciation_amortization)",
      "requires": ["ebit", "depreciation_amortization"],
      "domain": []
    },
    "FCF_TTM": {
      "role": "INTERMEDIATE", "family": "CASH_GENERATION",
      "formula": "sum4q(cfo) - abs(sum4q(capex))",
      "requires": ["cfo", "capex"],
      "domain": []
    },
    "EFFECTIVE_TAX_RATE": {
      "role": "INTERMEDIATE", "family": "RETURN_ON_CAPITAL",
      "formula": "sum4q(tax_expense) / sum4q(pretax_income)",
      "requires": ["tax_expense", "pretax_income"],
      "domain": ["sum4q(pretax_income) > 0"]
    },
    "NOPAT": {
      "role": "INTERMEDIATE", "family": "RETURN_ON_CAPITAL",
      "formula": "sum4q(ebit) * (1 - min(max(EFFECTIVE_TAX_RATE, 0), 0.6))",
      "requires": ["ebit", "tax_expense", "pretax_income"],
      "domain": []
    },
    "INVESTED_CAPITAL": {
      "role": "INTERMEDIATE", "family": "RETURN_ON_CAPITAL",
      "formula": "avg(total_equity) + avg(debt_st) + avg(debt_lt) - avg(cash_and_eq)",
      "requires": ["total_equity", "debt_st", "debt_lt", "cash_and_eq"],
      "domain": ["avg(total_equity) + avg(debt_st) + avg(debt_lt) - avg(cash_and_eq) > 0"]
    },
    "TANGIBLE_BOOK": {
      "role": "INTERMEDIATE", "family": "ASSET_MULTIPLE",
      "formula": "total_equity - nz(intangibles_goodwill, 0)",
      "requires": ["total_equity"],
      "domain": ["total_equity - nz(intangibles_goodwill, 0) > 0"]
    },

    "CURRENT_RATIO": {
      "family": "WORKING_CAPITAL", "direction": "HIGHER_BETTER",
      "formula": "current_assets / current_liabilities",
      "requires": ["current_assets", "current_liabilities"],
      "domain": ["current_liabilities > 0"],
      "out_of_domain": "NOT_APPLICABLE",
      "anchor": {"weak": 1.0, "strong": 2.0},
      "applies_to": ["NONFIN", "HOLDING", "GYO"]
    },
    "QUICK_RATIO": {
      "family": "WORKING_CAPITAL", "direction": "HIGHER_BETTER",
      "formula": "(current_assets - nz(inventory, 0)) / current_liabilities",
      "requires": ["current_assets", "current_liabilities"],
      "domain": ["current_liabilities > 0"],
      "out_of_domain": "NOT_APPLICABLE",
      "anchor": {"weak": 0.7, "strong": 1.3},
      "applies_to": ["NONFIN", "HOLDING", "GYO"]
    },
    "CASH_RATIO": {
      "family": "WORKING_CAPITAL", "direction": "HIGHER_BETTER",
      "formula": "(cash_and_eq + st_investments) / current_liabilities",
      "requires": ["cash_and_eq", "st_investments", "current_liabilities"],
      "domain": ["current_liabilities > 0"],
      "out_of_domain": "NOT_APPLICABLE",
      "anchor": {"weak": 0.15, "strong": 0.60},
      "applies_to": ["NONFIN", "HOLDING", "GYO"]
    },

    "CASH_TO_ASSETS": {
      "family": "CASH_BUFFER", "direction": "HIGHER_BETTER",
      "formula": "(cash_and_eq + st_investments) / total_assets",
      "requires": ["cash_and_eq", "st_investments", "total_assets"],
      "domain": ["total_assets > 0"],
      "out_of_domain": "MISSING",
      "applies_to": ["NONFIN", "HOLDING", "GYO", "FINANCIAL", "INSURANCE"]
    },
    "OCF_TO_CL": {
      "family": "CASH_BUFFER", "direction": "HIGHER_BETTER",
      "formula": "sum4q(cfo) / current_liabilities",
      "requires": ["cfo", "current_liabilities"],
      "domain": ["current_liabilities > 0"],
      "out_of_domain": "NOT_APPLICABLE",
      "applies_to": ["NONFIN", "HOLDING", "GYO"]
    },
    "CASH_TO_ST_DEBT": {
      "family": "CASH_BUFFER", "direction": "HIGHER_BETTER",
      "formula": "(cash_and_eq + st_investments) / debt_st",
      "requires": ["cash_and_eq", "st_investments", "debt_st"],
      "domain": ["debt_st > 0"],
      "out_of_domain": "BEST",
      "anchor": {"weak": 0.5, "strong": 2.0},
      "applies_to": ["NONFIN", "HOLDING", "GYO", "FINANCIAL", "INSURANCE"]
    },

    "DEBT_TO_EQUITY": {
      "family": "DEBT_LEVEL", "direction": "LOWER_BETTER",
      "formula": "(nz(debt_st, 0) + nz(debt_lt, 0)) / total_equity",
      "requires": ["debt_st", "debt_lt", "total_equity"],
      "domain": ["total_equity > 0"],
      "out_of_domain": "WORST",
      "anchor": {"weak": 1.5, "strong": 0.4},
      "applies_to": ["NONFIN", "HOLDING", "GYO", "BANK", "FINANCIAL", "INSURANCE"]
    },
    "DEBT_TO_CAPITAL": {
      "family": "DEBT_LEVEL", "direction": "LOWER_BETTER",
      "formula": "(nz(debt_st, 0) + nz(debt_lt, 0)) / ((nz(debt_st, 0) + nz(debt_lt, 0)) + total_equity)",
      "requires": ["debt_st", "debt_lt", "total_equity"],
      "domain": ["total_equity > 0", "(nz(debt_st, 0) + nz(debt_lt, 0)) + total_equity > 0"],
      "out_of_domain": "WORST",
      "anchor": {"weak": 0.60, "strong": 0.25},
      "applies_to": ["NONFIN", "HOLDING", "GYO", "BANK", "FINANCIAL", "INSURANCE"]
    },
    "NET_DEBT_TO_EQUITY": {
      "family": "DEBT_LEVEL", "direction": "LOWER_BETTER",
      "formula": "NET_DEBT / total_equity",
      "requires": ["debt_st", "debt_lt", "cash_and_eq", "st_investments", "total_equity"],
      "domain": ["total_equity > 0"],
      "out_of_domain": "WORST",
      "anchor": {"weak": 1.0, "strong": 0.0},
      "applies_to": ["NONFIN", "HOLDING", "GYO"]
    },
    "NET_DEBT_TO_EBITDA": {
      "family": "DEBT_LEVEL", "direction": "LOWER_BETTER",
      "formula": "NET_DEBT / EBITDA_TTM",
      "requires": ["debt_st", "debt_lt", "cash_and_eq", "st_investments", "ebit", "depreciation_amortization"],
      "domain": ["EBITDA_TTM > 0"],
      "out_of_domain": "WORST",
      "anchor": {"weak": 4.0, "strong": 1.0},
      "transform": "clip",
      "clip": {"low": -3.0, "high": 15.0},
      "applies_to": ["NONFIN", "HOLDING", "GYO"]
    },

    "INTEREST_COVERAGE": {
      "family": "DEBT_SERVICE", "direction": "HIGHER_BETTER",
      "formula": "sum4q(ebit) / sum4q(interest_exp)",
      "requires": ["ebit", "interest_exp"],
      "domain": ["sum4q(interest_exp) > 0"],
      "out_of_domain": "BEST",
      "out_of_domain_note": "No interest expense means no debt service burden, not missing data. v1 marked this NA and the NaN wiped the company's entire score.",
      "anchor": {"weak": 2.0, "strong": 8.0},
      "transform": "signed_log",
      "applies_to": ["NONFIN", "HOLDING", "GYO"]
    },
    "EBITDA_INTEREST_COVERAGE": {
      "family": "DEBT_SERVICE", "direction": "HIGHER_BETTER",
      "formula": "EBITDA_TTM / sum4q(interest_exp)",
      "requires": ["ebit", "depreciation_amortization", "interest_exp"],
      "domain": ["sum4q(interest_exp) > 0"],
      "out_of_domain": "BEST",
      "anchor": {"weak": 3.0, "strong": 10.0},
      "transform": "signed_log",
      "applies_to": ["NONFIN", "HOLDING", "GYO"]
    },
    "CFO_TO_TOTAL_DEBT": {
      "family": "DEBT_SERVICE", "direction": "HIGHER_BETTER",
      "formula": "sum4q(cfo) / (nz(debt_st, 0) + nz(debt_lt, 0))",
      "requires": ["cfo", "debt_st", "debt_lt"],
      "domain": ["(nz(debt_st, 0) + nz(debt_lt, 0)) > 0"],
      "out_of_domain": "BEST",
      "anchor": {"weak": 0.15, "strong": 0.45},
      "applies_to": ["NONFIN", "HOLDING", "GYO"]
    },
    "REFINANCING_WALL": {
      "family": "DEBT_SERVICE", "direction": "LOWER_BETTER",
      "formula": "debt_st / (cash_and_eq + st_investments + max(sum4q(cfo), 0))",
      "requires": ["debt_st", "cash_and_eq", "st_investments", "cfo"],
      "domain": ["(cash_and_eq + st_investments + max(sum4q(cfo), 0)) > 0"],
      "out_of_domain": "WORST",
      "out_of_domain_note": "No cash and no operating cash flow against short-term debt is the worst case, not a missing measurement.",
      "anchor": {"weak": 1.5, "strong": 0.5},
      "applies_to": ["NONFIN", "HOLDING", "GYO", "FINANCIAL", "INSURANCE"]
    },

    "ST_DEBT_RATIO": {
      "family": "DEBT_STRUCTURE", "direction": "LOWER_BETTER",
      "formula": "debt_st / (nz(debt_st, 0) + nz(debt_lt, 0))",
      "requires": ["debt_st", "debt_lt"],
      "domain": ["(nz(debt_st, 0) + nz(debt_lt, 0)) > 0"],
      "out_of_domain": "BEST",
      "anchor": {"weak": 0.70, "strong": 0.25},
      "applies_to": ["NONFIN", "HOLDING", "GYO", "FINANCIAL", "INSURANCE"]
    },
    "LEASE_ADJ_NET_DEBT_TO_EBITDA": {
      "family": "DEBT_STRUCTURE", "direction": "LOWER_BETTER",
      "formula": "(NET_DEBT + nz(lease_liabilities, 0)) / EBITDA_TTM",
      "requires": ["debt_st", "debt_lt", "cash_and_eq", "st_investments", "lease_liabilities", "ebit", "depreciation_amortization"],
      "domain": ["EBITDA_TTM > 0"],
      "out_of_domain": "WORST",
      "anchor": {"weak": 4.5, "strong": 1.5},
      "transform": "clip",
      "clip": {"low": -3.0, "high": 15.0},
      "applies_to": ["NONFIN", "HOLDING", "GYO"]
    },
    "FX_DEBT_RATIO": {
      "family": "DEBT_STRUCTURE", "direction": "LOWER_BETTER",
      "formula": "max(fx_debt - nz(fx_revenue, 0), 0) / (nz(debt_st, 0) + nz(debt_lt, 0))",
      "requires": ["fx_debt", "debt_st", "debt_lt"],
      "domain": ["(nz(debt_st, 0) + nz(debt_lt, 0)) > 0"],
      "out_of_domain": "BEST",
      "anchor": {"weak": 0.50, "strong": 0.10},
      "source_note": "fx_debt/fx_revenue are KAP_FOOTNOTE tier and unavailable from Pro+ at any price. Until footnote extraction lands this ratio resolves to MISSING and lowers coverage - it is never silently treated as zero FX risk.",
      "applies_to": ["NONFIN", "HOLDING", "GYO"]
    },
    "ALTMAN_Z_SCORE": {
      "family": "DEBT_STRUCTURE", "direction": "HIGHER_BETTER",
      "formula": "altman_z",
      "requires": ["altman_z"],
      "domain": [],
      "out_of_domain": "MISSING",
      "anchor": {"weak": 1.8, "strong": 3.0},
      "applies_to": ["NONFIN", "HOLDING"]
    },

    "CFO_MARGIN": {
      "family": "CASH_GENERATION", "direction": "HIGHER_BETTER",
      "formula": "sum4q(cfo) / sum4q(revenue)",
      "requires": ["cfo", "revenue"],
      "domain": ["sum4q(revenue) > 0"],
      "out_of_domain": "NOT_APPLICABLE",
      "applies_to": ["NONFIN", "HOLDING", "GYO"]
    },
    "FCF_MARGIN": {
      "family": "CASH_GENERATION", "direction": "HIGHER_BETTER",
      "formula": "FCF_TTM / sum4q(revenue)",
      "requires": ["cfo", "capex", "revenue"],
      "domain": ["sum4q(revenue) > 0"],
      "out_of_domain": "NOT_APPLICABLE",
      "applies_to": ["NONFIN", "HOLDING", "GYO"]
    },
    "FCF_TO_ASSETS": {
      "family": "CASH_GENERATION", "direction": "HIGHER_BETTER",
      "formula": "FCF_TTM / avg(total_assets)",
      "requires": ["cfo", "capex", "total_assets"],
      "domain": ["avg(total_assets) > 0"],
      "out_of_domain": "MISSING",
      "applies_to": ["NONFIN", "HOLDING", "GYO"]
    },

    "CFO_TO_NET_INCOME": {
      "family": "CASH_CONVERSION", "direction": "HIGHER_BETTER",
      "formula": "sum4q(cfo) / sum4q(net_income)",
      "requires": ["cfo", "net_income"],
      "domain": ["sum4q(net_income) > 0"],
      "out_of_domain": "NOT_APPLICABLE",
      "out_of_domain_note": "With a loss the ratio inverts sign and stops meaning 'earnings quality'. Excluded from the denominator rather than scored as bad.",
      "anchor": {"weak": 0.6, "strong": 1.1},
      "applies_to": ["NONFIN", "HOLDING", "GYO", "BANK", "FINANCIAL", "INSURANCE"]
    },
    "CFO_TO_EBITDA": {
      "family": "CASH_CONVERSION", "direction": "HIGHER_BETTER",
      "formula": "sum4q(cfo) / EBITDA_TTM",
      "requires": ["cfo", "ebit", "depreciation_amortization"],
      "domain": ["EBITDA_TTM > 0"],
      "out_of_domain": "NOT_APPLICABLE",
      "anchor": {"weak": 0.55, "strong": 0.95},
      "applies_to": ["NONFIN", "HOLDING", "GYO"]
    },
    "ACCRUALS_TO_ASSETS": {
      "family": "CASH_CONVERSION", "direction": "LOWER_BETTER",
      "formula": "(sum4q(net_income) - sum4q(cfo)) / avg(total_assets)",
      "requires": ["net_income", "cfo", "total_assets"],
      "domain": ["avg(total_assets) > 0"],
      "out_of_domain": "MISSING",
      "anchor": {"weak": 0.10, "strong": -0.02},
      "applies_to": ["NONFIN", "HOLDING", "GYO", "BANK", "FINANCIAL", "INSURANCE"]
    },
    "BENEISH_M_SCORE": {
      "family": "CASH_CONVERSION", "direction": "LOWER_BETTER",
      "formula": "beneish_m",
      "requires": ["beneish_m"],
      "domain": [],
      "out_of_domain": "MISSING",
      "anchor": {"weak": -1.78, "strong": -2.50},
      "applies_to": ["NONFIN", "HOLDING"]
    },

    "CAPEX_TO_SALES": {
      "family": "CAPEX_INTENSITY", "direction": "LOWER_BETTER",
      "formula": "abs(sum4q(capex)) / sum4q(revenue)",
      "requires": ["capex", "revenue"],
      "domain": ["sum4q(revenue) > 0"],
      "out_of_domain": "NOT_APPLICABLE",
      "applies_to": ["NONFIN", "GYO"]
    },
    "CAPEX_TO_DA": {
      "family": "CAPEX_INTENSITY", "direction": "BAND",
      "formula": "abs(sum4q(capex)) / sum4q(depreciation_amortization)",
      "requires": ["capex", "depreciation_amortization"],
      "domain": ["sum4q(depreciation_amortization) > 0"],
      "out_of_domain": "MISSING",
      "band": {"low": 0.8, "high": 1.8},
      "band_note": "Below 1 the asset base is shrinking; far above it capital is being sunk faster than it is earned back. Neither end is 'better'.",
      "applies_to": ["NONFIN", "GYO"]
    },
    "CAPEX_TO_CFO": {
      "family": "CAPEX_INTENSITY", "direction": "LOWER_BETTER",
      "formula": "abs(sum4q(capex)) / sum4q(cfo)",
      "requires": ["capex", "cfo"],
      "domain": ["sum4q(cfo) > 0"],
      "out_of_domain": "NOT_APPLICABLE",
      "applies_to": ["NONFIN", "GYO"]
    },

    "GROSS_MARGIN": {
      "family": "MARGIN", "direction": "HIGHER_BETTER",
      "formula": "sum4q(gross_profit) / sum4q(revenue)",
      "requires": ["gross_profit", "revenue"],
      "domain": ["sum4q(revenue) > 0"],
      "out_of_domain": "NOT_APPLICABLE",
      "applies_to": ["NONFIN", "HOLDING"]
    },
    "EBITDA_MARGIN": {
      "family": "MARGIN", "direction": "HIGHER_BETTER",
      "formula": "EBITDA_TTM / sum4q(revenue)",
      "requires": ["ebit", "depreciation_amortization", "revenue"],
      "domain": ["sum4q(revenue) > 0"],
      "out_of_domain": "NOT_APPLICABLE",
      "applies_to": ["NONFIN", "HOLDING", "GYO"]
    },
    "OPERATING_MARGIN": {
      "family": "MARGIN", "direction": "HIGHER_BETTER",
      "formula": "sum4q(ebit) / sum4q(revenue)",
      "requires": ["ebit", "revenue"],
      "domain": ["sum4q(revenue) > 0"],
      "out_of_domain": "NOT_APPLICABLE",
      "applies_to": ["NONFIN", "HOLDING", "GYO"]
    },
    "NET_MARGIN": {
      "family": "MARGIN", "direction": "HIGHER_BETTER",
      "formula": "sum4q(net_income) / sum4q(revenue)",
      "requires": ["net_income", "revenue"],
      "domain": ["sum4q(revenue) > 0"],
      "out_of_domain": "NOT_APPLICABLE",
      "applies_to": ["NONFIN", "HOLDING", "GYO", "BANK", "FINANCIAL", "INSURANCE"]
    },

    "ROE": {
      "family": "RETURN_ON_CAPITAL", "direction": "HIGHER_BETTER",
      "formula": "sum4q(net_income) / avg(total_equity)",
      "requires": ["net_income", "total_equity"],
      "domain": ["avg(total_equity) > 0"],
      "out_of_domain": "WORST",
      "anchor_note": "No anchor on purpose - a nominal 30% ROE can be a real loss under Turkish inflation. Relative only until a real-terms numeraire lands.",
      "applies_to": ["NONFIN", "HOLDING", "GYO", "BANK", "FINANCIAL", "INSURANCE"]
    },
    "ROA": {
      "family": "RETURN_ON_CAPITAL", "direction": "HIGHER_BETTER",
      "formula": "sum4q(net_income) / avg(total_assets)",
      "requires": ["net_income", "total_assets"],
      "domain": ["avg(total_assets) > 0"],
      "out_of_domain": "MISSING",
      "applies_to": ["NONFIN", "HOLDING", "GYO", "BANK", "FINANCIAL", "INSURANCE"]
    },
    "ROIC": {
      "family": "RETURN_ON_CAPITAL", "direction": "HIGHER_BETTER",
      "formula": "NOPAT / INVESTED_CAPITAL",
      "requires": ["ebit", "tax_expense", "pretax_income", "total_equity", "debt_st", "debt_lt", "cash_and_eq"],
      "domain": ["INVESTED_CAPITAL > 0"],
      "out_of_domain": "MISSING",
      "supersedes": "ROIC_PROXY",
      "supersedes_note": "v1's ROIC_PROXY used pre-tax EBIT over (assets - current liabilities). This uses real NOPAT over invested capital.",
      "applies_to": ["NONFIN", "HOLDING"]
    },
    "ROCE": {
      "family": "RETURN_ON_CAPITAL", "direction": "HIGHER_BETTER",
      "formula": "sum4q(ebit) / INVESTED_CAPITAL",
      "requires": ["ebit", "total_equity", "debt_st", "debt_lt", "cash_and_eq"],
      "domain": ["INVESTED_CAPITAL > 0"],
      "out_of_domain": "MISSING",
      "applies_to": ["NONFIN", "HOLDING"]
    },

    "DSO_DAYS": {
      "family": "WC_CYCLE", "direction": "LOWER_BETTER",
      "formula": "(avg(receivables) / sum4q(revenue)) * 365",
      "requires": ["receivables", "revenue"],
      "domain": ["sum4q(revenue) > 0"],
      "out_of_domain": "NOT_APPLICABLE",
      "applies_to": ["NONFIN"]
    },
    "DIO_DAYS": {
      "family": "WC_CYCLE", "direction": "LOWER_BETTER",
      "formula": "(avg(inventory) / sum4q(cogs)) * 365",
      "requires": ["inventory", "cogs"],
      "domain": ["sum4q(cogs) > 0", "avg(inventory) > 0"],
      "out_of_domain": "NOT_APPLICABLE",
      "out_of_domain_note": "Zero inventory is a service business, not missing data. It leaves the denominator instead of being scored.",
      "applies_to": ["NONFIN"]
    },
    "DPO_DAYS": {
      "family": "WC_CYCLE", "direction": "HIGHER_BETTER",
      "formula": "(avg(accounts_payable) / sum4q(cogs)) * 365",
      "requires": ["accounts_payable", "cogs"],
      "domain": ["sum4q(cogs) > 0"],
      "out_of_domain": "NOT_APPLICABLE",
      "supersedes": "DPO_DAYS_PROXY",
      "supersedes_note": "v1 divided short-term FINANCIAL debt by COGS and called it days payable. Trade payables and bank debt are unrelated; the error also propagated into CCC.",
      "applies_to": ["NONFIN"]
    },
    "CCC_DAYS": {
      "family": "WC_CYCLE", "direction": "LOWER_BETTER",
      "formula": "DSO_DAYS + DIO_DAYS - DPO_DAYS",
      "requires": ["receivables", "revenue", "inventory", "cogs", "accounts_payable"],
      "domain": [],
      "out_of_domain": "MISSING",
      "applies_to": ["NONFIN"]
    },

    "ASSET_TURNOVER": {
      "family": "ASSET_PRODUCTIVITY", "direction": "HIGHER_BETTER",
      "formula": "sum4q(revenue) / avg(total_assets)",
      "requires": ["revenue", "total_assets"],
      "domain": ["avg(total_assets) > 0"],
      "out_of_domain": "MISSING",
      "applies_to": ["NONFIN", "HOLDING"]
    },
    "FIXED_ASSET_TURNOVER": {
      "family": "ASSET_PRODUCTIVITY", "direction": "HIGHER_BETTER",
      "formula": "sum4q(revenue) / avg(net_ppe)",
      "requires": ["revenue", "net_ppe"],
      "domain": ["avg(net_ppe) > 0"],
      "out_of_domain": "NOT_APPLICABLE",
      "applies_to": ["NONFIN"]
    },
    "WC_TO_SALES": {
      "family": "ASSET_PRODUCTIVITY", "direction": "LOWER_BETTER",
      "formula": "(avg(current_assets) - avg(current_liabilities)) / sum4q(revenue)",
      "requires": ["current_assets", "current_liabilities", "revenue"],
      "domain": ["sum4q(revenue) > 0"],
      "out_of_domain": "NOT_APPLICABLE",
      "applies_to": ["NONFIN"]
    },

    "REVENUE_YOY_GROWTH": {
      "family": "TOP_LINE", "direction": "HIGHER_BETTER",
      "formula": "(revenue - lag4q(revenue)) / abs(lag4q(revenue))",
      "requires": ["revenue"],
      "domain": ["lag4q(revenue) != 0"],
      "out_of_domain": "MISSING",
      "inflation_note": "Nominal. Under Turkish inflation most of this is price level, not volume. Becomes meaningful only against a real-terms numeraire.",
      "applies_to": ["NONFIN", "HOLDING", "GYO", "BANK", "FINANCIAL", "INSURANCE"]
    },
    "REVENUE_CAGR_3Y": {
      "family": "TOP_LINE", "direction": "HIGHER_BETTER",
      "formula": "(revenue / lag(revenue, 12)) - 1",
      "requires": ["revenue"],
      "domain": ["lag(revenue, 12) > 0"],
      "out_of_domain": "MISSING",
      "applies_to": ["NONFIN", "HOLDING", "GYO", "BANK", "FINANCIAL", "INSURANCE"]
    },
    "REVENUE_FWD_GROWTH": {
      "family": "TOP_LINE", "direction": "HIGHER_BETTER",
      "formula": "(revenue_fwd_1y - sum4q(revenue)) / abs(sum4q(revenue))",
      "requires": ["revenue_fwd_1y", "revenue"],
      "domain": ["sum4q(revenue) > 0"],
      "out_of_domain": "MISSING",
      "applies_to": ["NONFIN", "HOLDING", "GYO", "BANK", "FINANCIAL", "INSURANCE"]
    },

    "EBITDA_YOY_GROWTH": {
      "family": "BOTTOM_LINE", "direction": "HIGHER_BETTER",
      "formula": "(EBITDA_TTM - (lag(ebit, 4) + lag(depreciation_amortization, 4))) / abs(lag(ebit, 4) + lag(depreciation_amortization, 4))",
      "requires": ["ebit", "depreciation_amortization"],
      "domain": ["(lag(ebit, 4) + lag(depreciation_amortization, 4)) != 0"],
      "out_of_domain": "MISSING",
      "applies_to": ["NONFIN", "HOLDING", "GYO"]
    },
    "EBIT_YOY_GROWTH": {
      "family": "BOTTOM_LINE", "direction": "HIGHER_BETTER",
      "formula": "(ebit - lag4q(ebit)) / abs(lag4q(ebit))",
      "requires": ["ebit"],
      "domain": ["lag4q(ebit) != 0"],
      "out_of_domain": "MISSING",
      "applies_to": ["NONFIN", "HOLDING", "GYO", "BANK", "FINANCIAL", "INSURANCE"]
    },
    "NET_INCOME_YOY_GROWTH": {
      "family": "BOTTOM_LINE", "direction": "HIGHER_BETTER",
      "formula": "(net_income - lag4q(net_income)) / abs(lag4q(net_income))",
      "requires": ["net_income"],
      "domain": ["lag4q(net_income) != 0"],
      "out_of_domain": "MISSING",
      "applies_to": ["NONFIN", "HOLDING", "GYO", "BANK", "FINANCIAL", "INSURANCE"]
    },
    "CFO_YOY_GROWTH": {
      "family": "BOTTOM_LINE", "direction": "HIGHER_BETTER",
      "formula": "(cfo - lag4q(cfo)) / abs(lag4q(cfo))",
      "requires": ["cfo"],
      "domain": ["lag4q(cfo) != 0"],
      "out_of_domain": "MISSING",
      "applies_to": ["NONFIN", "HOLDING", "GYO", "BANK", "FINANCIAL", "INSURANCE"]
    },
    "FCF_YOY_GROWTH": {
      "family": "BOTTOM_LINE", "direction": "HIGHER_BETTER",
      "formula": "(FCF_TTM - (lag(cfo, 4) - abs(lag(capex, 4)))) / abs(lag(cfo, 4) - abs(lag(capex, 4)))",
      "requires": ["cfo", "capex"],
      "domain": ["(lag(cfo, 4) - abs(lag(capex, 4))) != 0"],
      "out_of_domain": "MISSING",
      "applies_to": ["NONFIN", "HOLDING", "GYO"]
    },

    "EPS_YOY_GROWTH": {
      "family": "PER_SHARE", "direction": "HIGHER_BETTER",
      "formula": "((net_income / shares_diluted) - (lag4q(net_income) / lag(shares_diluted, 4))) / abs(lag4q(net_income) / lag(shares_diluted, 4))",
      "requires": ["net_income", "shares_diluted"],
      "domain": ["shares_diluted > 0", "lag(shares_diluted, 4) > 0", "lag4q(net_income) != 0"],
      "out_of_domain": "MISSING",
      "applies_to": ["NONFIN", "HOLDING", "GYO", "BANK", "FINANCIAL", "INSURANCE"]
    },
    "SHARE_COUNT_GROWTH": {
      "family": "PER_SHARE", "direction": "LOWER_BETTER",
      "formula": "(shares_out - lag4q(shares_out)) / lag4q(shares_out)",
      "requires": ["shares_out"],
      "domain": ["lag4q(shares_out) > 0"],
      "out_of_domain": "MISSING",
      "anchor": {"weak": 0.05, "strong": 0.0},
      "replaces_module": "Ek5_dilution",
      "replaces_module_note": "Dilution was going to be a flat -0.10 module penalty on announced rights issues. As a ratio it is continuous instead of a cliff, needs no corporate-action feed, and also catches convertibles and stock compensation.",
      "applies_to": ["NONFIN", "HOLDING", "GYO", "BANK", "FINANCIAL", "INSURANCE"]
    },
    "BVPS_GROWTH": {
      "family": "PER_SHARE", "direction": "HIGHER_BETTER",
      "formula": "((total_equity / shares_out) - (lag(total_equity, 4) / lag(shares_out, 4))) / abs(lag(total_equity, 4) / lag(shares_out, 4))",
      "requires": ["total_equity", "shares_out"],
      "domain": ["shares_out > 0", "lag(shares_out, 4) > 0", "lag(total_equity, 4) > 0"],
      "out_of_domain": "MISSING",
      "applies_to": ["NONFIN", "HOLDING", "GYO", "BANK", "FINANCIAL", "INSURANCE"]
    },

    "PE_TTM": {
      "family": "EARNINGS_MULTIPLE", "direction": "LOWER_BETTER",
      "formula": "MARKET_CAP / sum4q(net_income)",
      "requires": ["price", "shares_out", "net_income"],
      "domain": ["sum4q(net_income) > 0"],
      "out_of_domain": "WORST",
      "out_of_domain_note": "A loss-making company must not rank as cheap because its multiple is undefined.",
      "transform": "signed_log",
      "applies_to": ["NONFIN", "HOLDING", "GYO", "BANK", "FINANCIAL", "INSURANCE"]
    },
    "PE_FWD": {
      "family": "EARNINGS_MULTIPLE", "direction": "LOWER_BETTER",
      "formula": "price / eps_fwd_1y",
      "requires": ["price", "eps_fwd_1y"],
      "domain": ["eps_fwd_1y > 0"],
      "out_of_domain": "WORST",
      "transform": "signed_log",
      "coverage_note": "Consensus estimates thin out below BIST50. Resolves to MISSING there rather than falling back to trailing.",
      "applies_to": ["NONFIN", "HOLDING", "GYO", "BANK", "FINANCIAL", "INSURANCE"]
    },
    "EV_EBITDA": {
      "family": "EARNINGS_MULTIPLE", "direction": "LOWER_BETTER",
      "formula": "EV / EBITDA_TTM",
      "requires": ["price", "shares_out", "debt_st", "debt_lt", "cash_and_eq", "st_investments", "ebit", "depreciation_amortization"],
      "domain": ["EBITDA_TTM > 0"],
      "out_of_domain": "WORST",
      "transform": "signed_log",
      "priority_note": "The most used multiple on BIST and the one v1 could not compute at all, for want of a single field: depreciation_amortization.",
      "applies_to": ["NONFIN", "HOLDING", "GYO"]
    },
    "EV_EBIT": {
      "family": "EARNINGS_MULTIPLE", "direction": "LOWER_BETTER",
      "formula": "EV / sum4q(ebit)",
      "requires": ["price", "shares_out", "debt_st", "debt_lt", "cash_and_eq", "st_investments", "ebit"],
      "domain": ["sum4q(ebit) > 0"],
      "out_of_domain": "WORST",
      "transform": "signed_log",
      "applies_to": ["NONFIN", "HOLDING", "GYO"]
    },

    "P_FCF": {
      "family": "CASHFLOW_MULTIPLE", "direction": "LOWER_BETTER",
      "formula": "MARKET_CAP / FCF_TTM",
      "requires": ["price", "shares_out", "cfo", "capex"],
      "domain": ["FCF_TTM > 0"],
      "out_of_domain": "WORST",
      "transform": "signed_log",
      "applies_to": ["NONFIN", "HOLDING", "GYO"]
    },
    "EV_SALES": {
      "family": "CASHFLOW_MULTIPLE", "direction": "LOWER_BETTER",
      "formula": "EV / sum4q(revenue)",
      "requires": ["price", "shares_out", "debt_st", "debt_lt", "cash_and_eq", "st_investments", "revenue"],
      "domain": ["sum4q(revenue) > 0"],
      "out_of_domain": "NOT_APPLICABLE",
      "transform": "signed_log",
      "applies_to": ["NONFIN", "HOLDING", "GYO"]
    },
    "P_CFO": {
      "family": "CASHFLOW_MULTIPLE", "direction": "LOWER_BETTER",
      "formula": "MARKET_CAP / sum4q(cfo)",
      "requires": ["price", "shares_out", "cfo"],
      "domain": ["sum4q(cfo) > 0"],
      "out_of_domain": "WORST",
      "transform": "signed_log",
      "applies_to": ["NONFIN", "HOLDING", "GYO", "BANK", "FINANCIAL", "INSURANCE"]
    },

    "PB": {
      "family": "ASSET_MULTIPLE", "direction": "LOWER_BETTER",
      "formula": "MARKET_CAP / total_equity",
      "requires": ["price", "shares_out", "total_equity"],
      "domain": ["total_equity > 0"],
      "out_of_domain": "WORST",
      "transform": "signed_log",
      "applies_to": ["NONFIN", "HOLDING", "GYO", "BANK", "FINANCIAL", "INSURANCE"]
    },
    "P_TANGIBLE_BOOK": {
      "family": "ASSET_MULTIPLE", "direction": "LOWER_BETTER",
      "formula": "MARKET_CAP / TANGIBLE_BOOK",
      "requires": ["price", "shares_out", "total_equity", "intangibles_goodwill"],
      "domain": ["TANGIBLE_BOOK > 0"],
      "out_of_domain": "WORST",
      "transform": "signed_log",
      "applies_to": ["NONFIN", "HOLDING", "BANK", "FINANCIAL", "INSURANCE"]
    },
    "EV_TO_ASSETS": {
      "family": "ASSET_MULTIPLE", "direction": "LOWER_BETTER",
      "formula": "EV / avg(total_assets)",
      "requires": ["price", "shares_out", "debt_st", "debt_lt", "cash_and_eq", "st_investments", "total_assets"],
      "domain": ["avg(total_assets) > 0"],
      "out_of_domain": "MISSING",
      "transform": "signed_log",
      "applies_to": ["NONFIN", "HOLDING", "GYO"]
    },

    "DIVIDEND_YIELD": {
      "family": "YIELD", "direction": "HIGHER_BETTER",
      "formula": "sum4q(dividends_paid) / MARKET_CAP",
      "requires": ["dividends_paid", "price", "shares_out"],
      "domain": ["MARKET_CAP > 0"],
      "out_of_domain": "MISSING",
      "zero_note": "A zero dividend is a real observation, not a gap. Only a null dividends_paid is MISSING.",
      "applies_to": ["NONFIN", "HOLDING", "GYO", "BANK", "FINANCIAL", "INSURANCE"]
    },
    "FCF_YIELD": {
      "family": "YIELD", "direction": "HIGHER_BETTER",
      "formula": "FCF_TTM / MARKET_CAP",
      "requires": ["cfo", "capex", "price", "shares_out"],
      "domain": ["MARKET_CAP > 0"],
      "out_of_domain": "MISSING",
      "applies_to": ["NONFIN", "HOLDING", "GYO"]
    },
    "PAYOUT_RATIO": {
      "family": "YIELD", "direction": "BAND",
      "formula": "sum4q(dividends_paid) / sum4q(net_income)",
      "requires": ["dividends_paid", "net_income"],
      "domain": ["sum4q(net_income) > 0"],
      "out_of_domain": "NOT_APPLICABLE",
      "band": {"low": 0.15, "high": 0.60},
      "band_note": "Paying nothing and paying out everything are both warnings; neither extreme is 'better'.",
      "applies_to": ["NONFIN", "HOLDING", "GYO", "BANK", "FINANCIAL", "INSURANCE"]
    }
  }
}
```

### `sql/043_ratio_set_v2.sql`

PostgreSQL şeması. CANLI VERİTABANINDA KOŞULMADI.

```sql
-- v2 ratio layer storage.
--
-- v1's analytics.ratios_quarterly and analytics.rsc_summary_quarterly are NOT
-- touched: the existing production line and its regression suite keep running
-- unchanged.  v2 lands beside them, keyed additionally by ratio_set_version, so
-- the same company can be scored under both sets and the difference inspected.
-- That comparison is exactly what the V20 change-impact machinery was built for.

CREATE SCHEMA IF NOT EXISTS analytics;

-- One row per (company, period, disclosure version, ratio set, ratio).
--
-- status replaces v1's single is_na boolean, which conflated three unrelated
-- situations and cost a debt-free company its entire quality score:
--   OK              computed
--   MISSING         a required field is null - lowers coverage
--   BEST / WORST    undefined but economically unambiguous - counts as measured
--   NOT_APPLICABLE  meaningless here - leaves the denominator entirely
CREATE TABLE IF NOT EXISTS analytics.ratios_quarterly_v2 (
  ticker            TEXT NOT NULL,
  period_end        DATE NOT NULL,
  version_tag       TEXT NOT NULL,
  ratio_set_version TEXT NOT NULL,
  ratio_name        TEXT NOT NULL,
  sector_group      TEXT NOT NULL,
  ratio_value       NUMERIC,
  status            TEXT NOT NULL,
  computed_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (ticker, period_end, version_tag, ratio_set_version, ratio_name),
  CONSTRAINT ratios_v2_status_domain
    CHECK (status IN ('OK', 'MISSING', 'BEST', 'WORST', 'NOT_APPLICABLE')),
  -- An OK row without a value, or a non-OK row carrying one, would let a
  -- fabricated number through under a status that says nothing was measured.
  CONSTRAINT ratios_v2_ok_has_value
    CHECK (status <> 'OK' OR ratio_value IS NOT NULL),
  CONSTRAINT ratios_v2_non_ok_is_null
    CHECK (status = 'OK' OR ratio_value IS NULL)
);

CREATE INDEX IF NOT EXISTS idx_ratios_v2_pe
  ON analytics.ratios_quarterly_v2 (period_end, ratio_set_version);
CREATE INDEX IF NOT EXISTS idx_ratios_v2_ratio
  ON analytics.ratios_quarterly_v2 (ratio_name, period_end);

-- Three composites, not one.  v1 collapsed everything but VAL into a single
-- rsc_core_norm, so growth - a forward-looking signal - was averaged into a
-- backward-looking quality score.
CREATE TABLE IF NOT EXISTS analytics.rsc_summary_v2 (
  ticker            TEXT NOT NULL,
  period_end        DATE NOT NULL,
  version_tag       TEXT NOT NULL,
  ratio_set_version TEXT NOT NULL,
  sector_group      TEXT NOT NULL,

  quality_score     NUMERIC,
  quality_coverage  NUMERIC NOT NULL,
  quality_status    TEXT NOT NULL,
  quality_measured  INT NOT NULL,
  quality_applicable INT NOT NULL,

  growth_score      NUMERIC,
  growth_coverage   NUMERIC NOT NULL,
  growth_status     TEXT NOT NULL,
  growth_measured   INT NOT NULL,
  growth_applicable INT NOT NULL,

  value_score       NUMERIC,
  value_coverage    NUMERIC NOT NULL,
  value_status      TEXT NOT NULL,
  value_measured    INT NOT NULL,
  value_applicable  INT NOT NULL,

  -- Weight share of ratios scoring in the top decile, NOT an absolute count.
  -- v1's good_count_ge8 against a fixed threshold of 5 capped a bank's ek1 at
  -- 10/18 = 0.56 and made the veto 2.6x easier to trip for a bank.
  good_ratio        NUMERIC NOT NULL,

  computed_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (ticker, period_end, version_tag, ratio_set_version),

  CONSTRAINT rsc_v2_quality_status_domain
    CHECK (quality_status IN ('OK', 'YETERSIZ_KAPSAM')),
  CONSTRAINT rsc_v2_growth_status_domain
    CHECK (growth_status IN ('OK', 'YETERSIZ_KAPSAM')),
  CONSTRAINT rsc_v2_value_status_domain
    CHECK (value_status IN ('OK', 'YETERSIZ_KAPSAM')),

  -- An OK composite must carry a score; an insufficient one must NOT. This is
  -- the database-level half of the "no silent 0.0, no NaN" contract.
  CONSTRAINT rsc_v2_quality_ok_has_score
    CHECK (quality_status <> 'OK' OR quality_score IS NOT NULL),
  CONSTRAINT rsc_v2_growth_ok_has_score
    CHECK (growth_status <> 'OK' OR growth_score IS NOT NULL),
  CONSTRAINT rsc_v2_value_ok_has_score
    CHECK (value_status <> 'OK' OR value_score IS NOT NULL),
  CONSTRAINT rsc_v2_quality_bad_has_no_score
    CHECK (quality_status = 'OK' OR quality_score IS NULL),
  CONSTRAINT rsc_v2_growth_bad_has_no_score
    CHECK (growth_status = 'OK' OR growth_score IS NULL),
  CONSTRAINT rsc_v2_value_bad_has_no_score
    CHECK (value_status = 'OK' OR value_score IS NULL),

  CONSTRAINT rsc_v2_scores_in_unit_range
    CHECK (
      (quality_score IS NULL OR quality_score BETWEEN 0 AND 1) AND
      (growth_score  IS NULL OR growth_score  BETWEEN 0 AND 1) AND
      (value_score   IS NULL OR value_score   BETWEEN 0 AND 1)
    ),
  CONSTRAINT rsc_v2_coverage_in_unit_range
    CHECK (
      quality_coverage BETWEEN 0 AND 1 AND
      growth_coverage  BETWEEN 0 AND 1 AND
      value_coverage   BETWEEN 0 AND 1 AND
      good_ratio       BETWEEN 0 AND 1
    ),
  CONSTRAINT rsc_v2_measured_within_applicable
    CHECK (
      quality_measured BETWEEN 0 AND quality_applicable AND
      growth_measured  BETWEEN 0 AND growth_applicable AND
      value_measured   BETWEEN 0 AND value_applicable
    )
);

CREATE INDEX IF NOT EXISTS idx_rsc_v2_pe
  ON analytics.rsc_summary_v2 (period_end, ratio_set_version);

-- Immutability, matching the pattern already used by the backtest registries
-- (sql/042) and the impact runtime roles (sql/033): a recomputation replaces a
-- row through an explicit DELETE-then-INSERT under a privileged role, never by
-- an in-place UPDATE that would leave no trace of what changed.
CREATE OR REPLACE FUNCTION analytics.ratio_set_v2_immutable()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  RAISE EXCEPTION '% degistirilemez: % denendi', TG_TABLE_NAME, TG_OP;
END;
$$;

DROP TRIGGER IF EXISTS trg_ratios_quarterly_v2_immutable
  ON analytics.ratios_quarterly_v2;
CREATE TRIGGER trg_ratios_quarterly_v2_immutable
    BEFORE UPDATE ON analytics.ratios_quarterly_v2
    FOR EACH ROW EXECUTE FUNCTION analytics.ratio_set_v2_immutable();

DROP TRIGGER IF EXISTS trg_rsc_summary_v2_immutable
  ON analytics.rsc_summary_v2;
CREATE TRIGGER trg_rsc_summary_v2_immutable
    BEFORE UPDATE ON analytics.rsc_summary_v2
    FOR EACH ROW EXECUTE FUNCTION analytics.ratio_set_v2_immutable();
```

### `tests/_fixtures.py`

Testlerin kendi şekillerini kontrol ettiği rasyo setlerini gerçek yükleyiciden geçirerek kurar.

```python
"""Shared builders for the v2 ratio-layer tests.

The structural tests need ratio sets whose shape they control (how many ratios
sit in a family, which groups a ratio applies to).  Building those from JSON on
disk keeps them going through the real loader, so a test can never assert
against a set the validator would have rejected.
"""
from __future__ import annotations

import json
from pathlib import Path

from ratio_engine.spec import load_ratio_set


REAL_RATIOS = "config/ratios.v2.json"
REAL_FIELDS = "config/ratio_fields.v2.json"


def real_set():
    return load_ratio_set(REAL_RATIOS, REAL_FIELDS)


def write_registry(tmp_path: Path, fields: dict[str, str] | None = None) -> Path:
    fields = fields or {"a": "CURRENT", "b": "CURRENT", "c": "CURRENT", "d": "CURRENT"}
    path = tmp_path / "fields.json"
    path.write_text(json.dumps({
        "meta": {"field_set_version": "test"},
        "fields": {k: {"tier": v, "flow": "PERIOD"} for k, v in fields.items()},
    }), encoding="utf-8")
    return path


def build_set(
    tmp_path: Path,
    ratios: dict,
    *,
    families: dict[str, str],
    groups: list[str],
    pillar_shares: dict[str, float],
    composites: dict[str, list[str]],
    by_group: dict | None = None,
    name: str = "ratios.json",
    fields: dict[str, str] | None = None,
):
    ratios_path = tmp_path / name
    ratios_path.write_text(json.dumps({
        "meta": {
            "ratio_set_version": "test",
            "field_set_version": "test",
            "sector_groups": groups,
            "families": families,
            "composites": composites,
            "pillar_shares": {"default": pillar_shares, "by_group": by_group or {}},
        },
        "ratios": ratios,
    }), encoding="utf-8")
    return load_ratio_set(ratios_path, write_registry(tmp_path, fields))


def simple_ratio(family: str, groups: list[str], field: str = "a", **extra) -> dict:
    spec = {
        "family": family,
        "direction": "HIGHER_BETTER",
        "formula": field,
        "requires": [field],
        "domain": [],
        "out_of_domain": "MISSING",
        "applies_to": groups,
    }
    spec.update(extra)
    return spec
```

### `tests/test_spec.py`

13 test — doğrulayıcının reddetme kuralları.

```python
"""The v2 loader must reject a malformed ratio set loudly, not warn.

67 ratio definitions cannot be reviewed by eye, so every consistency rule the
design depends on is enforced at load time.  Each test here corresponds to a
class of silent misconfiguration that v1 could not detect - most importantly the
sector-applicability drift that let BANK end up with 10 eligible ratios against
NONFIN's 26 without anyone noticing.
"""
from __future__ import annotations

import pytest

from ratio_engine.spec import RatioSpecError, load_ratio_set, coverage_report, load_field_registry
from tests._fixtures import build_set, real_set, simple_ratio


FAMILIES = {"FAM_A": "P1", "FAM_B": "P2"}
SHARES = {"P1": 0.5, "P2": 0.5}
COMPOSITES = {"c1": ["P1", "P2"]}
GROUPS = ["G1"]


def _build(tmp_path, ratios, **kw):
    return build_set(tmp_path, ratios, families=FAMILIES, groups=GROUPS,
                     pillar_shares=SHARES, composites=COMPOSITES, **kw)


def test_real_set_loads_with_expected_shape():
    rs = real_set()
    assert len(rs.scored()) == 67
    assert len(rs.intermediates()) == 9
    assert len({s.family for s in rs.scored()}) == 19
    assert set(rs.composites()) == {"quality", "growth", "value"}


def test_real_set_coverage_report_counts_the_ingestion_backlog():
    rs = real_set()
    report = coverage_report(rs, load_field_registry("config/ratio_fields.v2.json"))
    nonfin = report["NONFIN"]
    assert nonfin["applicable"] == 67
    # Every applicable ratio is either computable now or blocked by a named tier.
    assert 0 < nonfin["computable_today"] < nonfin["applicable"]
    assert nonfin["blocked_by_tier"]


def test_unknown_field_is_rejected(tmp_path):
    with pytest.raises(RatioSpecError, match="alan kaydinda olmayan"):
        _build(tmp_path, {"R1": simple_ratio("FAM_A", GROUPS, field="a") | {"requires": ["nope"]}})


def test_unknown_family_is_rejected(tmp_path):
    with pytest.raises(RatioSpecError, match="olmayan aile"):
        _build(tmp_path, {"R1": simple_ratio("FAM_MISSING", GROUPS)})


def test_unknown_sector_group_is_rejected(tmp_path):
    with pytest.raises(RatioSpecError, match="bilinmeyen grup"):
        _build(tmp_path, {"R1": simple_ratio("FAM_A", ["G_NOPE"])})


def test_disallowed_function_is_rejected(tmp_path):
    with pytest.raises(RatioSpecError, match="izin verilmeyen fonksiyon"):
        _build(tmp_path, {"R1": simple_ratio("FAM_A", GROUPS) | {"formula": "eval(a)"}})


def test_formula_reading_an_undefined_name_is_rejected(tmp_path):
    """Intermediates must be declared before their dependants, not by dict luck."""
    with pytest.raises(RatioSpecError, match="tanimsiz"):
        _build(tmp_path, {"R1": simple_ratio("FAM_A", GROUPS) | {"formula": "LATER + a"}})


def test_anchor_must_agree_with_direction(tmp_path):
    with pytest.raises(RatioSpecError, match="HIGHER_BETTER"):
        _build(tmp_path, {"R1": simple_ratio("FAM_A", GROUPS) | {"anchor": {"weak": 5, "strong": 1}}})


def test_band_ratio_cannot_carry_an_anchor(tmp_path):
    with pytest.raises(RatioSpecError, match="anchor tasiyamaz"):
        _build(tmp_path, {"R1": simple_ratio("FAM_A", GROUPS) | {
            "direction": "BAND", "band": {"low": 1, "high": 2}, "anchor": {"weak": 1, "strong": 2}}})


def test_group_with_no_applicable_ratio_is_rejected(tmp_path):
    with pytest.raises(RatioSpecError, match="uygulanabilir degil"):
        build_set(tmp_path, {"R1": simple_ratio("FAM_A", ["G1"])},
                  families=FAMILIES, groups=["G1", "G2"],
                  pillar_shares=SHARES, composites=COMPOSITES)


def test_pillar_in_two_composites_is_rejected(tmp_path):
    with pytest.raises(RatioSpecError, match="birden fazla kompozitte"):
        build_set(tmp_path, {"R1": simple_ratio("FAM_A", GROUPS)},
                  families=FAMILIES, groups=GROUPS, pillar_shares=SHARES,
                  composites={"c1": ["P1", "P2"], "c2": ["P1"]})


def test_pillar_missing_from_every_composite_is_rejected(tmp_path):
    with pytest.raises(RatioSpecError, match="hicbir kompozite girmeyen"):
        build_set(tmp_path, {"R1": simple_ratio("FAM_A", GROUPS)},
                  families=FAMILIES, groups=GROUPS, pillar_shares=SHARES,
                  composites={"c1": ["P1"]})


def test_composite_with_no_live_pillar_for_a_group_is_rejected(tmp_path):
    """A group whose composite has only zero-share pillars would score
    YETERSIZ_KAPSAM forever, silently. The loader refuses instead."""
    with pytest.raises(RatioSpecError, match="payi sifirdan buyuk"):
        build_set(
            tmp_path,
            {"R1": simple_ratio("FAM_A", GROUPS), "R2": simple_ratio("FAM_B", GROUPS, field="b")},
            families=FAMILIES, groups=GROUPS, pillar_shares=SHARES,
            composites={"c1": ["P1"], "c2": ["P2"]},
            by_group={"G1": {"P1": 1.0, "P2": 0.0}},
        )
```

### `tests/test_calc.py`

13 test — üç sonuç semantiği.

```python
"""Three outcomes where v1 had one boolean.

The defect being fixed was measured on the live v1 code: a debt-free company
has no interest expense, INTEREST_COVERAGE went NA, the NaN propagated through
rsc_scoring._wmean and wiped rsc_core_norm entirely, and run_daily_pipeline then
filled the NaN M1 with 0.0.  The company scored zero on quality for having no
debt.  These tests pin the distinction that prevents it.
"""
from __future__ import annotations

from datetime import date

import pytest

from ratio_engine.calc import (
    STATUS_BEST, STATUS_MISSING, STATUS_NOT_APPLICABLE, STATUS_OK, STATUS_WORST,
    RatioCalcV2Error, RatioOutcome, compute_ratios_for_ticker, status_summary,
)
from tests._fixtures import real_set


QUARTERS = [date(2025, 3, 31), date(2025, 6, 30), date(2025, 9, 30), date(2025, 12, 31),
            date(2026, 3, 31), date(2026, 6, 30), date(2026, 9, 30), date(2026, 12, 31)]


def _rows(**overrides):
    rows = []
    for i, pe in enumerate(QUARTERS):
        row = dict(
            period_end=pe, version_tag="ORIGINAL", t0_date=pe,
            revenue=1000.0 + 50 * i, cogs=400.0 + 20 * i, gross_profit=None,
            ebit=200.0 + 10 * i, net_income=150.0 + 8 * i, interest_exp=20.0,
            cfo=180.0 + 9 * i, capex=-30.0,
            total_assets=5000.0, total_equity=4000.0, current_assets=2000.0,
            current_liabilities=500.0, cash_and_eq=900.0, st_investments=100.0,
            receivables=300.0, inventory=250.0, debt_st=200.0, debt_lt=300.0,
            shares_out=1000.0, shares_diluted=1000.0,
        )
        row.update(overrides)
        rows.append(row)
    return rows


def _latest(ticker="X", group="NONFIN", **overrides):
    rs = real_set()
    rows = _rows(**overrides)
    out = compute_ratios_for_ticker(
        ticker, rows, rs, group, {(ticker, pe): 20.0 for pe in QUARTERS}
    )
    return {o.ratio_name: o for o in out if o.period_end == QUARTERS[-1]}


def test_debt_free_company_gets_best_not_missing():
    """The exact v1 failure: no interest expense is perfect coverage, not a gap."""
    latest = _latest(interest_exp=0.0, debt_st=0.0, debt_lt=0.0)
    assert latest["INTEREST_COVERAGE"].status == STATUS_BEST
    assert latest["CFO_TO_TOTAL_DEBT"].status == STATUS_BEST
    assert latest["ST_DEBT_RATIO"].status == STATUS_BEST


def test_service_business_without_inventory_is_not_applicable():
    latest = _latest(inventory=0.0)
    assert latest["DIO_DAYS"].status == STATUS_NOT_APPLICABLE


def test_loss_making_company_is_worst_on_pe_not_cheap():
    """An undefined multiple must not let a loss-maker rank as cheap."""
    latest = _latest(net_income=-100.0)
    assert latest["PE_TTM"].status == STATUS_WORST


def test_uningested_field_is_missing_not_zero():
    """depreciation_amortization is KAP_XBRL tier and not populated yet."""
    latest = _latest()
    assert latest["EV_EBITDA"].status == STATUS_MISSING
    assert latest["EV_EBITDA"].value is None
    assert latest["DPO_DAYS"].status == STATUS_MISSING


def test_ratio_outside_its_sector_is_not_applicable():
    latest = _latest(group="BANK")
    # DSO_DAYS applies only to NONFIN.
    assert latest["DSO_DAYS"].status == STATUS_NOT_APPLICABLE


def test_ordinary_company_computes_ok_values():
    latest = _latest()
    for name in ("CURRENT_RATIO", "ROE", "PE_TTM", "INTEREST_COVERAGE", "DIO_DAYS"):
        assert latest[name].status == STATUS_OK, name
        assert latest[name].value is not None


def test_intermediates_never_emit_outcome_rows():
    rs = real_set()
    latest = _latest()
    for spec in rs.intermediates():
        assert spec.name not in latest


def test_failed_intermediate_makes_dependants_missing_not_substituted():
    """EBITDA_TTM cannot form without D&A, so EV_EBITDA is MISSING - never a
    silently substituted EV/EBIT."""
    latest = _latest()
    assert latest["EV_EBITDA"].status == STATUS_MISSING
    assert latest["EV_EBIT"].status == STATUS_OK  # the substitute exists separately


def test_every_scored_ratio_gets_exactly_one_outcome_per_period():
    rs = real_set()
    rows = _rows()
    out = compute_ratios_for_ticker("X", rows, rs, "NONFIN", {("X", pe): 20.0 for pe in QUARTERS})
    per_period = [o for o in out if o.period_end == QUARTERS[-1]]
    assert len(per_period) == len(rs.scored())
    assert len({o.ratio_name for o in per_period}) == len(rs.scored())


def test_status_counts_sum_to_the_scored_set():
    rs = real_set()
    latest = _latest()
    assert sum(status_summary(latest.values()).values()) == len(rs.scored())


def test_outcome_rejects_ok_without_value():
    with pytest.raises(RatioCalcV2Error):
        RatioOutcome("X", QUARTERS[0], "ORIGINAL", "ROE", None, STATUS_OK)


def test_outcome_rejects_non_ok_carrying_a_value():
    """A value under a status that says nothing was measured is a fabrication."""
    with pytest.raises(RatioCalcV2Error):
        RatioOutcome("X", QUARTERS[0], "ORIGINAL", "ROE", 0.5, STATUS_MISSING)


def test_unknown_sector_group_is_rejected():
    rs = real_set()
    with pytest.raises(RatioCalcV2Error):
        compute_ratios_for_ticker("X", _rows(), rs, "NO_SUCH_GROUP", {})
```

### `tests/test_scoring.py`

13 test — skorlama katmanının sekiz garantisi.

```python
"""The eight properties the v2 scoring layer exists to guarantee.

Each maps to a defect measured on the live v1 code:

  1  a single missing ratio wiped the whole score (NaN through _wmean)
  2  a debt-free company therefore scored 0.0 on quality
  3  NA conflated "does not apply" with "not measured"
  4  a pillar's share scaled with its ratio count, so the set could not grow
  5  good_count_ge8 was absolute, capping a bank's ek1 at 10/18 = 0.56
  6  insufficient data surfaced as a silent 0.0 instead of a status
  7  determinate and absent outcomes were indistinguishable
  8  tie handling depended on input order
"""
from __future__ import annotations

import collections

import pytest

from ratio_engine.scoring import (
    RESULT_INSUFFICIENT_COVERAGE, RESULT_OK, RatioObservation, ScoringError,
    compute_ratio_weights, score_universe,
)
from tests._fixtures import build_set, simple_ratio


FAMILIES = {"FAM_A": "P1", "FAM_B": "P1", "FAM_C": "P2"}
SHARES = {"P1": 0.6, "P2": 0.4}
COMPOSITES = {"c1": ["P1", "P2"]}


def _set(tmp_path, ratios, groups=("G1",), by_group=None, name="ratios.json"):
    return build_set(tmp_path, ratios, families=FAMILIES, groups=list(groups),
                     pillar_shares=SHARES, composites=COMPOSITES,
                     by_group=by_group, name=name,
                     fields={"a": "CURRENT", "b": "CURRENT", "c": "CURRENT", "d": "CURRENT"})


def _pool(names, tickers, base=1.0, step=1.0):
    """OK observations with a clean spread so ranking is well defined."""
    obs = []
    for i, t in enumerate(tickers):
        for n in names:
            obs.append(RatioObservation(t, n, base + step * i, "OK"))
    return obs


TICKERS = [f"T{i}" for i in range(1, 7)]


# --- 1 -----------------------------------------------------------------
def test_one_missing_ratio_does_not_wipe_the_score(tmp_path):
    rs = _set(tmp_path, {
        "R1": simple_ratio("FAM_A", ["G1"], "a"),
        "R2": simple_ratio("FAM_B", ["G1"], "b"),
        "R3": simple_ratio("FAM_C", ["G1"], "c"),
    })
    obs = _pool(["R1", "R2", "R3"], TICKERS)
    obs = [o for o in obs if not (o.ticker == "T1" and o.ratio_name == "R3")]
    obs.append(RatioObservation("T1", "R3", None, "MISSING"))

    res = score_universe(rs, obs, {t: "G1" for t in TICKERS})
    c = res["T1"].composites["c1"]
    assert c.status == RESULT_OK
    assert c.score is not None and 0.0 <= c.score <= 1.0
    assert c.coverage < 1.0          # the gap is visible
    assert c.measured == 2 and c.applicable == 3


# --- 2 -----------------------------------------------------------------
def test_determinate_best_is_rewarded_not_penalised(tmp_path):
    """The debt-free company. BEST must beat a mid-pool OK, never equal zero."""
    rs = _set(tmp_path, {
        "R1": simple_ratio("FAM_A", ["G1"], "a"),
        "R2": simple_ratio("FAM_B", ["G1"], "b"),
        "R3": simple_ratio("FAM_C", ["G1"], "c"),
    })
    obs = [o for o in _pool(["R1", "R2", "R3"], TICKERS) if o.ticker != "T1"]
    for n in ("R1", "R2", "R3"):
        obs.append(RatioObservation("T1", n, None, "BEST"))

    res = score_universe(rs, obs, {t: "G1" for t in TICKERS})
    assert res["T1"].composites["c1"].score == pytest.approx(1.0)
    assert res["T1"].composites["c1"].coverage == pytest.approx(1.0)
    assert res["T1"].composites["c1"].good_ratio == pytest.approx(1.0)


# --- 3 -----------------------------------------------------------------
def test_not_applicable_leaves_the_denominator(tmp_path):
    rs = _set(tmp_path, {
        "R1": simple_ratio("FAM_A", ["G1"], "a"),
        "R2": simple_ratio("FAM_B", ["G1"], "b"),
        "R3": simple_ratio("FAM_C", ["G1"], "c"),
    })
    base = _pool(["R1", "R2", "R3"], TICKERS)

    na = [o for o in base if not (o.ticker == "T1" and o.ratio_name == "R3")]
    na.append(RatioObservation("T1", "R3", None, "NOT_APPLICABLE"))
    missing = [o for o in base if not (o.ticker == "T1" and o.ratio_name == "R3")]
    missing.append(RatioObservation("T1", "R3", None, "MISSING"))

    gm = {t: "G1" for t in TICKERS}
    na_res = score_universe(rs, na, gm)["T1"].composites["c1"]
    missing_res = score_universe(rs, missing, gm)["T1"].composites["c1"]

    assert na_res.applicable == 2 and na_res.coverage == pytest.approx(1.0)
    assert missing_res.applicable == 3 and missing_res.coverage < 1.0


# --- 4 -----------------------------------------------------------------
def test_pillar_share_is_independent_of_ratio_count(tmp_path):
    """The property that lets the ratio set grow. In v1 a pillar's real share
    was (ratio count x pillar_w)/sum, so this test would have failed."""
    small = _set(tmp_path, {
        "R1": simple_ratio("FAM_A", ["G1"], "a"),
        "R9": simple_ratio("FAM_C", ["G1"], "c"),
    }, name="small.json")
    big = _set(tmp_path, {
        **{f"R{i}": simple_ratio("FAM_A", ["G1"], "a") for i in range(1, 8)},
        "R9": simple_ratio("FAM_C", ["G1"], "c"),
    }, name="big.json")

    def pillar_share(rs):
        agg = collections.defaultdict(float)
        for name, w in compute_ratio_weights(rs, "G1", "c1").items():
            agg[rs.specs[name].pillar] += w
        return dict(agg)

    assert pillar_share(small) == pytest.approx(pillar_share(big))
    assert pillar_share(big)["P1"] == pytest.approx(0.6)
    assert sum(compute_ratio_weights(big, "G1", "c1").values()) == pytest.approx(1.0)


def test_families_split_the_pillar_evenly_regardless_of_size(tmp_path):
    rs = _set(tmp_path, {
        "A1": simple_ratio("FAM_A", ["G1"], "a"),
        **{f"B{i}": simple_ratio("FAM_B", ["G1"], "b") for i in range(1, 6)},
        "C1": simple_ratio("FAM_C", ["G1"], "c"),
    })
    w = compute_ratio_weights(rs, "G1", "c1")
    fam = collections.defaultdict(float)
    for name, x in w.items():
        fam[rs.specs[name].family] += x
    # FAM_A and FAM_B share P1's 0.6 evenly even though B has five members.
    assert fam["FAM_A"] == pytest.approx(0.3)
    assert fam["FAM_B"] == pytest.approx(0.3)


# --- 5 -----------------------------------------------------------------
def test_good_ratio_ceiling_is_one_for_every_group(tmp_path):
    """v1's absolute good_count capped a bank at 10/18 = 0.56 while an
    industrial could reach 1.0. A weight share cannot do that."""
    rs = _set(tmp_path, {
        "WIDE1": simple_ratio("FAM_A", ["G_WIDE"], "a"),
        "WIDE2": simple_ratio("FAM_B", ["G_WIDE"], "b"),
        "BOTH": simple_ratio("FAM_C", ["G_WIDE", "G_NARROW"], "c"),
        "NARROW": simple_ratio("FAM_A", ["G_NARROW"], "a"),
    }, groups=("G_WIDE", "G_NARROW"))

    obs = []
    for t in ("W1", "W2"):
        for n in ("WIDE1", "WIDE2", "BOTH"):
            obs.append(RatioObservation(t, n, None, "BEST"))
    for t in ("N1", "N2"):
        for n in ("NARROW", "BOTH"):
            obs.append(RatioObservation(t, n, None, "BEST"))

    res = score_universe(rs, obs, {"W1": "G_WIDE", "W2": "G_WIDE",
                                   "N1": "G_NARROW", "N2": "G_NARROW"})
    wide = res["W1"].composites["c1"]
    narrow = res["N1"].composites["c1"]
    assert wide.applicable == 3 and narrow.applicable == 2
    assert wide.good_ratio == pytest.approx(1.0)
    assert narrow.good_ratio == pytest.approx(1.0)   # no structural ceiling
    assert wide.score == pytest.approx(narrow.score)


# --- 6 -----------------------------------------------------------------
def test_below_coverage_threshold_is_a_status_not_a_silent_zero(tmp_path):
    rs = _set(tmp_path, {
        "R1": simple_ratio("FAM_A", ["G1"], "a"),
        "R2": simple_ratio("FAM_B", ["G1"], "b"),
        "R3": simple_ratio("FAM_C", ["G1"], "c"),
    })
    obs = _pool(["R1", "R2", "R3"], TICKERS)
    obs = [o for o in obs if o.ticker != "T1"]
    obs.append(RatioObservation("T1", "R1", 1.0, "OK"))
    obs.append(RatioObservation("T1", "R2", None, "MISSING"))
    obs.append(RatioObservation("T1", "R3", None, "MISSING"))

    res = score_universe(rs, obs, {t: "G1" for t in TICKERS}, min_coverage=0.5)
    c = res["T1"].composites["c1"]
    assert c.status == RESULT_INSUFFICIENT_COVERAGE
    assert c.score is None          # not 0.0, not NaN
    assert c.coverage < 0.5


# --- 7 -----------------------------------------------------------------
def test_determinate_counts_as_measured_but_missing_does_not(tmp_path):
    rs = _set(tmp_path, {
        "R1": simple_ratio("FAM_A", ["G1"], "a"),
        "R2": simple_ratio("FAM_B", ["G1"], "b"),
        "R3": simple_ratio("FAM_C", ["G1"], "c"),
    })
    gm = {t: "G1" for t in TICKERS}

    def coverage(status):
        obs = [o for o in _pool(["R1", "R2", "R3"], TICKERS) if o.ticker != "T1"]
        obs += [RatioObservation("T1", "R1", 1.0, "OK"),
                RatioObservation("T1", "R2", 1.0, "OK"),
                RatioObservation("T1", "R3", None, status)]
        return score_universe(rs, obs, gm)["T1"].composites["c1"]

    assert coverage("WORST").coverage == pytest.approx(1.0)
    assert coverage("BEST").coverage == pytest.approx(1.0)
    assert coverage("MISSING").coverage < 1.0
    assert coverage("WORST").score < coverage("BEST").score


# --- 8 -----------------------------------------------------------------
def test_tied_values_do_not_depend_on_input_order(tmp_path):
    rs = _set(tmp_path, {
        "R1": simple_ratio("FAM_A", ["G1"], "a"),
        "R3": simple_ratio("FAM_C", ["G1"], "c"),
    })
    gm = {t: "G1" for t in TICKERS}
    obs = [RatioObservation(t, n, 5.0, "OK") for t in TICKERS for n in ("R1", "R3")]

    forward = score_universe(rs, obs, gm)
    backward = score_universe(rs, list(reversed(obs)), gm)
    for t in TICKERS:
        assert forward[t].composites["c1"].score == pytest.approx(
            backward[t].composites["c1"].score
        )


# --- guards -------------------------------------------------------------
def test_unknown_ticker_group_is_rejected(tmp_path):
    rs = _set(tmp_path, {"R1": simple_ratio("FAM_A", ["G1"], "a"),
                         "R3": simple_ratio("FAM_C", ["G1"], "c")})
    with pytest.raises(ScoringError, match="sektor grubu bilinmeyen"):
        score_universe(rs, [RatioObservation("T1", "R1", 1.0, "OK")], {})


def test_observation_outside_the_ratio_set_is_rejected(tmp_path):
    rs = _set(tmp_path, {"R1": simple_ratio("FAM_A", ["G1"], "a"),
                         "R3": simple_ratio("FAM_C", ["G1"], "c")})
    with pytest.raises(ScoringError, match="rasyo setinde olmayan"):
        score_universe(rs, [RatioObservation("T1", "GHOST", 1.0, "OK")], {"T1": "G1"})


def test_ok_observation_requires_a_finite_value():
    with pytest.raises(ScoringError):
        RatioObservation("T1", "R1", None, "OK")


def test_invalid_status_is_rejected():
    with pytest.raises(ScoringError):
        RatioObservation("T1", "R1", 1.0, "WHATEVER")
```

### `pytest.ini`

```ini
[pytest]
pythonpath = src .
testpaths = tests
```

### `.gitignore`

```text
__pycache__/
*.py[cod]
.pytest_cache/
.venv/
venv/
*.egg-info/
```

### Belgede gömülü OLMAYAN iki dosya

**`tests/__init__.py`** — boş dosya (0 bayt), ama **gerekli**. `pytest.ini`
`pythonpath = src .` diyor ve testler `from tests._fixtures import ...`
şeklinde import ediyor; bu dosya olmazsa import kırılır. Sıfırdan
kuruyorsan: `touch tests/__init__.py`.

**`README.md`** — içeriği bu belgenin 1-5. bölümleriyle büyük ölçüde
örtüştüğü için tekrar gömülmedi. Repoda mevcut; gerekirse oradan alınır ya da
bu belgeden yeniden yazılır.

Bunlar dışında repodaki 16 dosyanın 14'ü yukarıda tam haliyle var.

---

## 7. AÇIK SORULAR

### Doğrulanmamış sabitler — hepsi iddia, hiçbiri ölçülmedi

Skorlama kodundaki bu değerler makul seçimlerdir ama **hiçbiri veriyle
doğrulanmadı**:

```
GOOD_SCORE_THRESHOLD   0.80     "iyi rasyo" eşiği
DEFAULT_MIN_COVERAGE   0.40     altında YETERSIZ_KAPSAM
DEFAULT_MIN_POOL       5        altında tüm evrene düşülür
ANCHOR_BLEND           0.40     mutlak çapa ağırlığı (0.40 mutlak + 0.60 göreli)
MAD_SCALE              1.4826   normal dağılım sabiti (bu standart, tartışmasız)
pillar_shares          LIQ .12 LEV .24 CASH .24 PROFIT .28 EFF .12
anchor weak→0.30, strong→0.80   çapa eşleme noktaları
```

21 çapanın `weak`/`strong` değerleri de aynı şekilde: standart finans
sezgisinden geliyor, BIST verisiyle kalibre edilmedi.

### Tasarlanan ama kodlanmamış

- **`(seviye, eğim, istikrar)` üçlüsü** — sadece `seviye` var. `eğim`
  (8 çeyrek) ve `istikrar` hiç yazılmadı. Kalite motoru "marj istikrarı"
  bileşenini bunlardan alacaktı.
- **4 eksen + 3 kapı modeli** (`0.34·DEĞERLEME + 0.24·TEMEL_MOMENTUM +
  0.22·KALİTE + 0.20·FİYAT_MOMENTUM`, `× G_risk × G_muhasebe × G_likidite`)
  — tasarlandı, tek satır kod yok. Ağırlıklar iddia.
- **Motor B (Saf Değer), C (Kalite Bileşik), D (Momentum/Revizyon)** —
  tasarlandı, yazılmadı.
- **Karşılaştırma yüzeyi** (yan yana sıralı tablo, uzlaşma/ayrışma listeleri)
  — tasarlandı, yazılmadı.
- **İki eksenli değerleme** (emsale göre .60 + kendi 3-5 yıl medyanına göre
  .40) — tasarlandı, yazılmadı. 10 yıllık geçmiş gerektiriyor.

### Veri tarafı

- **PostgreSQL migration canlı koşulmadı.** `sql/043_ratio_set_v2.sql` yalnız
  yapısal olarak kontrol edildi (2 tablo, 15 CHECK, 2 trigger, DDL'de v1
  tablosuna referans yok). Konteynerde DSN yoktu.
- **Pro+ CSV kolon adları bilinmiyor** — gerçek export görülmeden yazılmayacak.
- **Pro+ abonesi olunacak mı: KARARLAŞMADI.**
- **Alternatif sağlayıcı seçimi: KARARLAŞMADI** (Finnet / Matriks / Foreks /
  Rasyonet / FMP / EODHD / LSEG).
- **9 KAP XBRL alanının semantik eşlemesi** yazılmadı.
- **FX borç dipnot çıkarımı çözülmedi** — `fx_debt` ve `fx_revenue` alanları
  `KAP_FOOTNOTE` kademesinde, hiçbir kaynaktan gelmiyor. `FX_DEBT_RATIO`
  rasyosu bu yüzden her zaman `MISSING`. Kapı **sıfır FX riski varsaymıyor**,
  bu bilinçli.
- **Hacim ingest yapılmadı** — `adv_60d_try` alanı tanımlı ama üretilmiyor,
  dolayısıyla `G_likidite` kapısı çalışamaz.

### Yapısal

- **TMS 29 / enflasyon düzeltmesi hiç ele alınmadı.** Şemada `numeraire`
  alanı yer tutucu olarak bile yok — sadece planda bahsi geçti. Büyüme
  rasyoları nominal TL; Türkiye'de bunun büyük kısmı fiyat seviyesi.
- **Motor yalıtımı arayüzü** (`EngineResult`) tasarlandı, yazılmadı.
- **`tests/__init__.py` boş** ve `pytest.ini`'de `pythonpath = src .` var;
  bu kurulum çalışıyor ama paketleme (`pyproject.toml`, kurulabilir paket)
  **KARARLAŞMADI**.
- **Lisans dosyası yok. KARARLAŞMADI.**
- **CI yok.** Ana projede GitHub Actions vardı; bu repoda kurulmadı.
- **Ana repodaki 10 kopya dosyanın akıbeti KARARLAŞMADI** —
  `TOTAL-RASYO-HESAPLAYICI` çalışma ağacında `config/ratio_fields.v2.json`,
  `config/ratios.v2.json`, `sql/043_ratio_set_v2.sql`,
  `src/analytics/{ratio_spec_v2,ratios_calc_v2,rsc_scoring_v2}.py`,
  `tests/{_v2_fixtures,test_ratio_spec_v2,test_ratios_calc_v2,test_rsc_scoring_v2}.py`
  hâlâ untracked duruyor. Commit edilmedi, push edilmedi. Silinsin mi kalsın mı
  sorusu cevapsız.

---

## 8. SONRAKİ ADIMLAR

Öncelik sırasıyla. İlk üçü dış veri gerektirmiyor.

**1. Hacim ingest + işlem likiditesi kapısı.**
En ucuz yüksek etkili iş. Ana projede `core.prices_daily.volume` kolonu zaten
var ve yfinance hacmi zaten döndürüyor — sadece yazılmıyor. 60 günlük ortalama
TL hacim hesaplanır, `adv_60d_try` üretilir. Yarım günlük iş, sıfır dış veri.

**2. `(seviye, eğim, istikrar)` üçlüsü.**
8 çeyrek üzerinden eğim ve istikrar bileşenleri. Kalite motorunun "marj
istikrarı" bileşeni buna bağlı; ayrıca ana projenin M1 modülü trendi özet
skordan yeniden türetmek yerine doğrudan eğimi okuyabilir.

**3. Motor arayüzü + dört motor.**
`EngineResult` sözleşmesi, sonra Total Rasyo v2 / Saf Değer / Kalite Bileşik /
Momentum-Revizyon. Bugünkü 47 hesaplanabilir rasyoyla dördü de çalışır.

**4. Karşılaştırma yüzeyi.**
Tek satır = tek hisse; motor sıraları + ham oranlar (F/K, PD/DD, EV/FAVÖK,
net borç/FAVÖK, temettü) yan yana. Uzlaşma listesi (3-4 motor hemfikir) ve
ayrışma listesi (çelişki → araştırma kuyruğu). **Kullanıcının asıl istediği
ekran budur.**

**5. Canlı PostgreSQL doğrulaması.**
`psql -f sql/043_ratio_set_v2.sql` ve CHECK kısıtlarının ihlal senaryolarında
gerçekten reddettiğinin görülmesi.

**6. Dokuz KAP XBRL alanı.**
`depreciation_amortization`, `tax_expense`, `pretax_income`,
`accounts_payable`, `dividends_paid`, `minority_interest`,
`lease_liabilities`, `net_ppe`, `intangibles_goodwill`. NONFIN'de 47 → 62
rasyo. En yüksek getirili tek alan `depreciation_amortization`: tek başına
EV/FAVÖK, FAVÖK marjı, net borç/FAVÖK, FAVÖK faiz karşılama, nakit dönüşümü
ve capex/D&A açıyor.

**7. Pro+ export arşivi + tahmin ekseni.**
Abonelik alınırsa. Aylık export → SHA256 → değişmez arşiv. İleriye dönük PIT
arşivi burada başlar.

**8. IC ölçümü ve walk-forward.**
Motor başına Spearman rank-IC. **Projenin en eksik parçası:** bugün hiçbir
ağırlık doğrulanmadı. Ana projede `optimize-weights` gerçek koşuda IC 0.057
vermişti — gürültü seviyesi, çünkü sentetik 24 hisselik veriyle çalışıyordu.
Fit bütçesi: 4 eksen ağırlığı + 3 kapı eşiği ≈ 7 parametre. Rasyo ağırlıkları
fit edilmez (K3).

---

## 9. KLASÖR YAPISI

### Bugünkü hali (repoda var)

```
total-rasyo-fit-version/
├── README.md
├── pytest.ini                        pythonpath = src .
├── .gitignore
├── config/
│   ├── ratio_fields.v2.json          48 alan
│   └── ratios.v2.json                67 rasyo + 9 ara
├── sql/
│   └── 043_ratio_set_v2.sql          2 tablo, 15 CHECK, 2 trigger
├── src/ratio_engine/
│   ├── __init__.py
│   ├── spec.py                       şema + doğrulayıcı
│   ├── calc.py                       formül → 5 sonuç
│   ├── scoring.py                    aile normalizasyonlu skorlama
│   └── evaluator.py                  vendor'lanmış değerlendirici
└── tests/
    ├── __init__.py
    ├── _fixtures.py
    ├── test_spec.py                  13
    ├── test_calc.py                  13
    └── test_scoring.py               13
```

### Önerilen genişleme

```
├── src/ratio_engine/
│   ├── trend.py                      (seviye, eğim, istikrar) üçlüsü
│   └── liquidity.py                  adv_60d_try
├── src/engines/
│   ├── base.py                       EngineResult sözleşmesi
│   ├── total_rasyo_v2.py             4 eksen × 3 kapı
│   ├── saf_deger.py
│   ├── kalite_bilesik.py
│   ├── momentum_revizyon.py
│   └── external_proplus.py           yalnız yan sütun, motor girdisi DEĞİL
├── src/board/
│   ├── comparison.py                 yan yana sıralı tablo
│   └── report.py                     CSV + terminal çıktısı
├── src/ingest/
│   └── investingpro_export.py        elle bırakılan CSV → değişmez arşiv
├── data/investingpro/                BIST_YYYY-MM.csv (git'e girmez)
└── sql/
    ├── 044_engine_result.sql
    └── 045_investingpro_export.sql
```

`src/engines/` ve `src/board/` ayrı paketler olarak tutulmalı: `ratio_engine`
sıfır bağımlılık özelliğini koruyabilir, motorlar ve tablo katmanı gerekirse
pandas kullanabilir.

---

## EK — DOĞRULAMA DURUMU

Bu sohbette gerçekten koşulan ve gözlenen şeyler:

```
v2 testleri (taze GitHub klonunda)     39 passed
Ana proje tam regresyonu             1295 passed, 222 skipped, 0 failed
BANK v4.7 regresyonu                  277 passed, 1 xfailed (önceden var olan)
Mutasyon testi                        5/5 yakalandı
Üçüncü parti bağımlılık               yok (saf stdlib + pytest)
Değiştirilen v1 dosyası               0
PostgreSQL migration                  KOŞULMADI
```

Beş mutasyonun her biri en az bir testi kırdı:

| Mutasyon | Kırılan test |
|---|---|
| Aile normalizasyonu kaldırıldı | 1 |
| `NOT_APPLICABLE` paydada bırakıldı | 1 |
| Yetersiz kapsam sessizce 0.0 döndü | 1 |
| `BEST`/`WORST` ölçülmüş sayılmadı | 3 |
| Bağ çözümü giriş sırasına bırakıldı | 1 |

Ölçülen v1 kusurlarının kanıtı — borçsuz, envantersiz bir hizmet şirketi
fikstürüyle:

```
INTEREST_COVERAGE   BEST             v1'de NA → tüm skor NaN → m1=0.0
CFO_TO_TOTAL_DEBT   BEST
ST_DEBT_RATIO       BEST
DIO_DAYS            NOT_APPLICABLE   paydadan çıkıyor
DPO_DAYS            MISSING          accounts_payable henüz yok
EV_EBITDA           MISSING          depreciation_amortization henüz yok
PE_TTM              OK  25.773
ROE                 OK   0.194
CURRENT_RATIO       OK   4.000
```

Pillar payının rasyo sayısından bağımsızlığı:

```
NONFIN  LEV = 12 rasyo → pay 0.2400   (config: 0.2400)
BANK    LEV =  2 rasyo → pay 0.3333   (config: 0.30/0.90 renormalize)
```

Kapsam tablosu (doğrulayıcının canlı çıktısı):

```
grup        uygulanabilir  aile  bugün  engelleyen
NONFIN               67     19     47   KAP_XBRL 15, PROPLUS 4, dipnot 1
HOLDING              58     17     42   KAP_XBRL 11, PROPLUS 4, dipnot 1
GYO                  54     17     41   KAP_XBRL 10, PROPLUS 2, dipnot 1
FINANCIAL            27     14     22   KAP_XBRL 3, PROPLUS 2
INSURANCE            27     14     22   KAP_XBRL 3, PROPLUS 2
BANK                 23     11     18   KAP_XBRL 3, PROPLUS 2
```

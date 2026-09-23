# TOTAL RASYO FIT — YAŞAYAN ROADMAP

**Tek plan otoritesi:** Bu dosya.  
**Son güncelleme:** 2026-09-23  
**Plan başlangıç HEAD:** `4fb840e635d193419c8028e85ae7b10c133684c8`  
**Mimari:** [docs/TOTAL_RASYO_2_0_MIMARI.md](docs/TOTAL_RASYO_2_0_MIMARI.md)

---

## Durum kodları

- `DONE` — Kod/veri/doküman + doğrulama kanıtı tamam.
- `IN_PROGRESS` — Aktif olarak çalışılıyor.
- `READY` — Ön koşulları tamam, başlanabilir.
- `BLOCKED` — Dış veri/karar/altyapı bekliyor.
- `PLANNED` — Planlandı, öncelik sırası gelmedi.
- `REJECTED` — Denendi veya incelendi, gerekçeyle reddedildi.
- `LEGACY` — Karşılaştırma için korunuyor, yeni mimarinin otoritesi değil.

---

# ZORUNLU ÇALIŞMA KURALI

Bu projede **her gerçek iş GitHub'da bu planı güncellemek zorundadır.**

Her iş için sıra:

1. Güncel remote `main` / aktif çalışma dalı ve HEAD doğrulanır.
2. İş bu dosyadaki bir `TR2-XXX` maddesine bağlanır.
3. Gerekirse madde `IN_PROGRESS` yapılır.
4. Kod/veri/test/doküman değişikliği uygulanır.
5. Test / veri receipt / araştırma sonucu kaydedilir.
6. **Aynı çalışma paketinde bu roadmap tekrar güncellenir.**
7. Kanıt yoksa madde `DONE` yapılamaz.
8. Yeni bulgu planı değiştirirse eski yön sessizce silinmez; aşağıdaki changelog'a neden yazılır.
9. Kullanıcıya "yapıldı" denmeden önce GitHub'daki durum bu dosyada `DONE` olmalıdır.

Bu kural, insan veya AI fark etmeksizin projede çalışan herkes için geçerlidir.

---

# ÜST SEVİYE DURUM

| ID | Faz | Durum | Amaç |
|---|---|---|---|
| TR2-000 | Baseline ve mevcut motor | DONE | Sağlam v2 rasyo motorunu ve araştırma baseline'ını sabitle |
| TR2-010 | Total Rasyo 2.0 mimari kararı | DONE | Yeni skor matematiği + Pro+ rolünü tanımla |
| TR2-020 | Pro+ veri sözleşmesi | READY | Gerçek export'u tanı, immutable raw ingest tasarla |
| TR2-030 | Kanonik feature registry | PLANNED | 1.200+ alanı kontrollü aday havuzuna çevir |
| TR2-040 | PIT / provenance katmanı | PLANNED | Gelecek bilgi sızıntısını engelle |
| TR2-050 | Quality 2.0 | PLANNED | Seviye kalitesini bağımsız faktör yap |
| TR2-060 | Fundamental Trend | PLANNED | İyileşme/kötüleşmeyi quality'den ayır |
| TR2-070 | Valuation 2.0 | PLANNED | M2 yerine saf ve çok-kaynaklı değerleme faktörü |
| TR2-080 | Growth + Expectations | PLANNED | Forward tahmin ve revision faktörlerini ekle |
| TR2-090 | Momentum / Residual Alpha | PLANNED | Fiyat sinyalini valuation'dan ayır |
| TR2-100 | Confidence 2.0 | PLANNED | Sinyal gücü ile veri/model güvenini ayır |
| TR2-110 | Risk 2.0 | PLANNED | Volatilite ve downside riskini alpha'dan ayır |
| TR2-120 | Feature selection / redundancy | PLANNED | Tekrarlı 1.200+ metriği 15–40 üretim faktörüne indir |
| TR2-130 | Walk-forward model | PLANNED | Kısıtlı, PIT güvenli faktör ağırlıklarını öğren |
| TR2-140 | 0–100 kalibrasyon | PLANNED | Raw Alpha → kesitsel Total Rasyo 0–100 |
| TR2-150 | Selection / portfolio policy | PLANNED | Score'dan ayrı seçim ve portföy kuralları |
| TR2-160 | OOS kabul testi | PLANNED | IC, spread, benchmark, maliyet, rejim testleri |
| TR2-170 | Shadow / parallel run | PLANNED | Legacy ile TR2'yi paralel canlı gözlemle |
| TR2-180 | Production cutover | PLANNED | Yalnız kabul kriterleri geçilirse TR2'yi varsayılan yap |

---

# TR2-000 — BASELINE VE MEVCUT MOTOR

**Durum: DONE**

Korunan temel:

- 67 rasyo.
- 19 family.
- 7 pillar.
- 6 sektör grubu.
- `OK/MISSING/BEST/WORST/NOT_APPLICABLE`.
- Fail-closed coverage.
- Rasyo sayısından bağımsız family/pillar ağırlığı.
- Sektöre göre `applies_to`.
- Mutlak good-count yerine weighted good-ratio.
- Medyan/MAD robust scoring.
- Quality / Growth / Value ayrımı.
- Araştırma IC harness.

2026-09-23 baseline araştırma receipt:

- Value monthly / 6m forward mean IC ≈ +0.136, NW t ≈ +2.03.
- Quality mean IC ≈ +0.092, NW t ≈ +2.08.
- Growth mean IC ≈ +0.004, NW t ≈ +0.05.
- 12 aylık mevcut strateji ≈ +%5.5 net.
- Aynı evren ≈ +%9.2.
- Picks hit rate ≈ %48; universe ≈ %48.
- Top-10 kuralı mevcut kısa örnekte üstünlük göstermedi.
- Holding-period ve threshold sonuçları kararsız; kısa örnek üzerine production kararı verilmeyecek.

**Kanıt commitleri:** `04d5796`, `52c9855`, `2df34be`, `055420f`, `be62176`.

---

# TR2-010 — TOTAL RASYO 2.0 MİMARİ KARARI

**Durum: DONE**

Belge:

- `docs/TOTAL_RASYO_2_0_MIMARI.md`

Kabul edilen ana kararlar:

- 0–100 artık teorik maksimum yüzdesi değil, kesitsel yatırım-sinyali rank/kalibrasyonudur.
- Raw Alpha ayrıca saklanır.
- Quality, Valuation, Growth, Expectations, Momentum, Fundamental Trend ayrı faktör aileleridir.
- Confidence alpha'dan ayrıdır.
- Risk alpha'dan ayrıdır.
- InvestingPro+ hazır skorları sorgusuz sabit ağırlıkla Total'e eklenmez.
- Pro+ feature factory + challenger + valuation ensemble + benchmark rolündedir.
- Weight fitting yalnız faktör/eksen düzeyinde ve walk-forward yapılır.
- PIT disiplini kırılmaz.
- Score model ile portfolio policy ayrıdır.
- Legacy sonuçlar karşılaştırma için korunur.

**Kanıt commit:** `4fb840e`.

---

# TR2-020 — INVESTINGPRO+ VERİ SÖZLEŞMESİ

**Durum: READY**

**Yeni gerçek:** Kullanıcının InvestingPro+ üyeliği 2026-09-23 itibarıyla mevcut.

## TR2-021 — İlk gerçek export envanteri

**Durum: BLOCKED**

Gereken:

- InvestingPro+ üzerinden BIST için gerçek bir CSV/XLSX export örneği.
- Mümkünse mümkün olan en geniş kolon seti.
- Export zamanı.
- Kullanılan screener / ülke / evren filtresi.

**Kural:** Gerçek dosya görülmeden kolon adı veya mapping uydurulmayacak.

## TR2-022 — Raw immutable snapshot formatı

**Durum: READY**

Tasarlanacak:

- source
- export_at
- ingest_at
- SHA256
- original filename
- row count
- column count
- schema fingerprint
- universe/filter metadata
- raw file path
- parser version

Acceptance:

- aynı raw dosya değişmeden tekrar doğrulanabilmeli;
- transformed fact'ten raw kaynağa geri gidilebilmeli.

## TR2-023 — Canonical field mapper

**Durum: BLOCKED → TR2-021**

İlk gerçek export'tan sonra:

```
vendor_column
→ canonical_field
→ semantic_group
→ unit
→ period_type
→ currency
→ PIT status
→ transformation
```

mapping oluşturulacak.

## TR2-024 — Import validation

**Durum: PLANNED**

- duplicate ticker
- unknown ticker
- impossible type
- unit mismatch
- missing period
- stale export
- schema drift
- vendor field disappearance

fail-closed testleri.

---

# TR2-030 — KANONİK FEATURE REGISTRY

**Durum: PLANNED**

Amaç: "1.200+ veri"yi doğrudan modele sokmamak.

Her feature için:

- canonical name
- source
- economic family
- sign/direction
- point/flow
- period
- lag
- sector applicability
- coverage
- PIT confidence
- missing semantics
- expected range
- redundancy cluster
- production status

Aşamalar:

```
1200+ raw
→ semantik audit
→ usable candidates
→ coverage screen
→ redundancy clusters
→ IC screen
→ incremental IC
→ 15–40 production factors
```

---

# TR2-040 — POINT-IN-TIME / PROVENANCE

**Durum: PLANNED**

Ana kurallar:

- KAP publication timestamp historical truth için ana otorite.
- Pro+ current export geriye dönük "o gün biliniyordu" sayılmaz.
- Estimate/forecast snapshot tarihi olmadan historical backteste girmez.
- Revision ancak iki gerçek snapshot mevcutsa hesaplanır.
- Restatement ile original reported fact ayrılır.
- Her feature `available_at` taşımalıdır.

Acceptance test:

- Bir as-of tarihi verildiğinde model o tarihten sonra oluşmuş hiçbir field'a erişememeli.

---

# TR2-050 — QUALITY 2.0

**Durum: PLANNED**

Amaç: "iyi şirket" ile "iyileşen şirket" kavramını ayırmak.

Alt family adayları:

- Profitability
- Cash Flow Quality
- Balance Sheet Strength
- Capital Efficiency
- Operating Efficiency
- Earnings Quality
- Accounting/Distress Quality

Kaynak:

- mevcut 67 rasyo motoru
- Pro+ ile doğrulanmış ek metrikler
- Altman/Beneish gibi uygun challenger/feature alanları

Acceptance:

- sekiz dönemdir çok yüksek ve stabil kalite taşıyan şirket yalnız "artık iyileşmiyor" diye cezalandırılamaz.
- rasyo sayısı pillar ağırlığını değiştiremez.

---

# TR2-060 — FUNDAMENTAL TREND

**Durum: PLANNED**

Quality'den bağımsız:

- 1Q delta
- 4Q delta
- 8Q robust slope
- acceleration/deceleration
- margin trend
- cash-conversion trend
- leverage trend

Acceptance:

- seviye ile trend aynı değişkenin içine gömülmeyecek;
- trend negatif ama seviye çok yüksek ise iki gerçek ayrı ayrı görülebilecek.

---

# TR2-070 — VALUATION 2.0

**Durum: PLANNED**

Eski M2/FOLLOW hibrit mantığının yerine:

- relative multiples
- own valuation model
- InvestingPro Fair Value
- mevcutsa consensus/target evidence
- sector-relative valuation
- historical-relative valuation

**Yasak:** Fiyat yükseldi diye "ucuzluk" puanını mekanik olarak yok etmek.

Output:

- `valuation_signal`
- `valuation_confidence`
- `valuation_disagreement`

Ablation:

- own only
- Pro+ only
- ensemble
- ensemble + disagreement

---

# TR2-080 — GROWTH + EXPECTATIONS

**Durum: PLANNED**

Growth:

- revenue
- EPS
- EBITDA
- FCF
- multi-year CAGR

Expectations / Revisions:

- forward EPS
- forward revenue
- forward EBITDA
- 1m/3m revisions
- earnings surprise
- target/consensus revisions (mevcutsa)

Önemli baseline:

- mevcut Growth IC ≈ +0.004; bu nedenle Growth yüksek ağırlığı **kanıtlamak zorunda**.

---

# TR2-090 — MOMENTUM / RESIDUAL ALPHA

**Durum: PLANNED**

Adaylar:

- 20d
- 63d
- 126d
- sector-adjusted
- market-adjusted
- residual alpha
- persistence

Kural:

- valuation ile momentum birbirini cezalandıran tek bir hibrit skor olmayacak;
- korelasyonu yüksek momentum varyantları double-count edilmeyecek.

---

# TR2-100 — CONFIDENCE 2.0

**Durum: PLANNED**

Aday girdiler:

- coverage
- freshness
- source count
- source agreement
- peer sample size
- model dispersion
- forecast age
- provenance quality

Örnek çıktı:

```
Total Rasyo: 91
Confidence:   43
```

Alpha 91 iken confidence düşük olabilir. Confidence sinyalin anlamını değiştirmez.

---

# TR2-110 — RISK 2.0

**Durum: PLANNED**

Adaylar:

- realized volatility
- downside volatility
- max drawdown
- beta
- liquidity / ADV
- gap/tail risk
- leverage/distress overlays

Ek9 benzeri düşük-vol mantığı alpha puanının içine gömülmeyecek.

---

# TR2-120 — FEATURE SELECTION / REDUNDANCY

**Durum: PLANNED**

Her aday feature için:

- coverage
- distribution
- outlier behavior
- sector neutrality
- Spearman IC
- rolling IC
- ICIR
- positive-month ratio
- correlation cluster
- incremental IC
- regime stability

Hedef:

**15–40 civarı gerçekten farklı üretim faktörü.**

1.200 field kullanmak başarı kriteri değildir.

---

# TR2-130 — WALK-FORWARD MODEL

**Durum: PLANNED**

Kavramsal:

```
RawAlpha =
    βQ * Quality
  + βV * Valuation
  + βG * Growth
  + βE * Expectations
  + βM * Momentum
  + βF * FundamentalTrend
```

Kurallar:

- expanding/rolling walk-forward
- future leakage yok
- bounded weights
- shrinkage
- correlated-factor penalty
- parameter-count discipline
- sector stability
- no per-ratio overfitting

Aday yöntemler ancak benchmark sonucu ile seçilecek; karmaşıklık kendisi amaç değildir.

---

# TR2-140 — TOTAL RASYO 0–100

**Durum: PLANNED**

Üretilecek:

- `raw_alpha`
- `total_rasyo_0_100`
- `confidence_0_100`
- `risk_0_100`

İlk tercih:

```
total_rasyo_0_100 = cross_sectional_percentile(raw_alpha) * 100
```

Gerekirse tarihsel empirical-CDF kalibrasyonu ayrıca challenger olarak test edilir.

Acceptance:

- tüm ölçek anlamlı kullanılmalı;
- 50 civarı evren medyanı olmalı;
- score inflation yapılmamalı;
- rank IC ham alpha ile doğrulanmalı.

---

# TR2-150 — SELECTION / PORTFOLIO POLICY

**Durum: PLANNED**

Score'dan ayrı test edilecek:

- top-N
- top percentile
- raw-alpha threshold
- confidence gate
- risk cap
- sector cap
- liquidity floor
- rebalance interval
- holding period
- transaction costs

Bugünkü Top-10 yaklaşımı otomatik olarak korunmayacak.

---

# TR2-160 — OUT-OF-SAMPLE KABUL TESTİ

**Durum: PLANNED**

Zorunlu rapor:

- mean rank IC
- ICIR
- Newey-West t
- positive IC months
- top-minus-bottom
- top decile excess return
- benchmark relative return
- hit rate
- max drawdown
- turnover
- transaction-cost net
- sector slices
- bull/bear/sideways slices
- inflation/regime slices
- factor ablation

Yeni model yalnız "daha yüksek CAGR" gerekçesiyle kabul edilemez.

---

# TR2-170 — SHADOW / PARALLEL RUN

**Durum: PLANNED**

Aynı gün için:

```
legacy_score
tr2_raw_alpha
tr2_total_0_100
tr2_confidence
tr2_risk
```

yan yana saklanır.

Amaç:

- canlı drift
- missing-data behavior
- Pro+ schema drift
- factor disagreement
- confidence calibration
- gerçek ileri dönem performansı

---

# TR2-180 — PRODUCTION CUTOVER

**Durum: PLANNED**

Geçiş için:

- OOS kabul kriterleri tamam.
- PIT audit PASS.
- Pro+ ingestion fail-closed.
- Legacy karşılaştırması tamam.
- Shadow döneminde kritik hata yok.
- Production run reproducible.
- Receipt ve model version saklanıyor.

Geçişten sonra Legacy silinmez; karşılaştırma/audit yolu olarak korunur.

---

# ŞİMDİKİ EN KÜÇÜK ENGELSİZ SONRAKİ İŞ

**TR2-022 — Raw immutable snapshot formatını uygulamak.**

Bunun paralelindeki en değerli veri bağımlılığı:

**TR2-021 — Kullanıcının InvestingPro+ hesabından ilk gerçek BIST CSV/XLSX export örneğini elde etmek.**

Gerçek dosya geldiği anda TR2-023 canonical mapping başlayabilir.

---

# DEĞİŞİKLİK KAYDI

## 2026-09-23

- `DONE` TR2-000: Mevcut v2 ratio engine + güncel IC/backtest araştırmaları baseline olarak kabul edildi.
- `DONE` TR2-010: Total Rasyo 2.0 matematik ve InvestingPro+ mimarisi kabul edildi.
- Yeni karar: InvestingPro+ üyeliği artık mevcut; eski "abonelik alınmadı" varsayımı tarihsel kaldı.
- Yeni karar: Total Rasyo 0–100 raw weighted average değil, doğrulanmış Raw Alpha'nın kesitsel rank/kalibrasyon katmanı olacak.
- Yeni karar: Confidence ve Risk Total'in içine gömülmeyecek.
- Yeni karar: Pro+ hazır skorları doğrudan kopyalanmayacak; feature/challenger/ensemble olarak kullanılacak.
- Yeni kural: Bundan sonraki her iş bu roadmap'i aynı çalışma paketinde güncellemeden `DONE` sayılamaz.

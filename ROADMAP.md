# TOTAL RASYO FIT — GREENFIELD YAŞAYAN ROADMAP

**Tek plan otoritesi:** Bu dosya  
**Son güncelleme:** 2026-09-23  
**Aktif mimari:** [docs/TOTAL_RASYO_2_0_MIMARI.md](docs/TOTAL_RASYO_2_0_MIMARI.md)  
**Greenfield reset commit:** `52040f42ca0cf2a146a105ddcdd4905ccf53901f`

---

## Zorunlu çalışma kuralı

Bu repository'de hiçbir eski matematik, oran, eşik, ağırlık veya modül otomatik olarak doğru kabul edilmez.

Her iş şu sırayla yürür:

1. Güncel remote HEAD doğrulanır.
2. İlgili `TR2-XXX` işi `IN_PROGRESS` yapılır.
3. Gerekli legacy kod yalnız inceleme/kanıt amacıyla okunur.
4. Yeni çözüm sıfırdan `src/tr2`, `research/tr2`, `tests/tr2`, `config/tr2` altında geliştirilir.
5. Eğer eski bir parça taşınacaksa KEEP/PORT/REWRITE/DELETE kararı ve gerekçesi kaydedilir.
6. Test, backtest veya veri receipt'i üretilir.
7. Bu roadmap aynı çalışma paketinde güncellenir.
8. Kanıt yoksa iş `DONE` yapılamaz.
9. Kullanıcıya "tamamlandı" denmeden önce GitHub'daki durum `DONE` olmalıdır.

Durumlar:

- `DONE`
- `IN_PROGRESS`
- `READY`
- `BLOCKED`
- `PLANNED`
- `REJECTED`

---

# Ana fazlar

| ID | Faz | Durum | Çıktı |
|---|---|---|---|
| TR2-000 | Greenfield reset | DONE | Eski sistem varsayım olmaktan çıkarıldı |
| TR2-010 | Legacy forensic audit | READY | KEEP / PORT / REWRITE / DELETE matrisi |
| TR2-020 | Veri sözleşmesi | READY | KAP + market + Pro+ kanonik veri modeli |
| TR2-030 | PIT/provenance çekirdeği | PLANNED | leakage-safe feature store |
| TR2-040 | Feature registry | PLANNED | ekonomik anlamı tanımlı aday feature evreni |
| TR2-050 | Factor discovery | PLANNED | forward IC taşıyan bağımsız faktör aileleri |
| TR2-060 | InvestingPro+ feature factory | BLOCKED | ilk gerçek export sonrası |
| TR2-070 | Alpha model v1 | PLANNED | basit/robust challenger modeller |
| TR2-080 | Confidence model | PLANNED | alpha'dan ayrı güven skoru |
| TR2-090 | Risk model | PLANNED | alpha'dan ayrı risk skoru |
| TR2-100 | 0–100 calibration | PLANNED | raw alpha → Total Rasyo 0–100 |
| TR2-110 | Nested walk-forward | PLANNED | gerçek OOS model selection |
| TR2-120 | Portfolio policy | PLANNED | score'dan bağımsız seçim motoru |
| TR2-130 | Shadow production | PLANNED | legacy vs TR2 paralel canlı kayıt |
| TR2-140 | Cutover / legacy cleanup | PLANNED | yalnız kanıtlanan yeni sistem üretime |

---

# TR2-000 — GREENFIELD RESET

**Durum: DONE**

Karar:

- Mevcut 67 ratio seti otomatik korunmayacak.
- Mevcut family/pillar yapısı otomatik korunmayacak.
- Mevcut quality/growth/value kompozitleri otomatik korunmayacak.
- Mevcut IC/backtest sonuçları tasarım gerçeği değil, yalnız **baseline evidence**.
- Mevcut kod production TR2 tarafından import edilmeyecek.
- Yeni motor ayrı namespace'te sıfırdan kurulacak.
- Legacy parçalar ancak audit sınavını geçerse port edilecek.

Kanıt:

- `docs/TOTAL_RASYO_2_0_MIMARI.md`
- commit `52040f42`

---

# TR2-010 — LEGACY FORENSIC AUDIT

**Durum: READY**

Bu ilk gerçek teknik iştir.

Amaç: eski sistemi "korumak" değil, hangi parçaların gerçekten ekonomik ve matematiksel olarak işe yaradığını belirlemek.

## TR2-011 — Oran envanteri

**Durum: IN_PROGRESS**

Statik envanter (`research/tr2/legacy_ratio_inventory.json`) 67 skorlanan
oranın tamamını legacy tanım dosyasının hash'iyle birlikte kaydeder. Üretici:
`research/tr2/legacy_inventory.py`. Formül, yön, sektör, gerekli alan ve
alanların dönem/kaynak etiketleri aktarılmıştır. Ekonomik tez, formül doğruluğu,
PIT güvenliği, gerçekleşen coverage ve IC **henüz ölçülmediği için boş**
bırakılmıştır. Üç formül incelemesi `REWRITE` kararı aldı: `REVENUE_CAGR_3Y`
yıllıklandırılmamış üç yıllık değişim; `EBITDA_YOY_GROWTH` ve
`FCF_YOY_GROWTH` mevcut TTM ile önceki yılın tek çeyreğini karşılaştırıyor.
Bu karar yalnız hatalı legacy formülün taşınamayacağını söyler; TR2 feature
olarak kabul kararı değildir. Kalan 64 karar açık. `tests/tr2/test_legacy_inventory.py`
67/67 kapsama, uydurma IC bulunmaması ve kaynak formül değişince yeniden
inceleme gerekliliği için 3 test içerir. Bu envanter
tam forensic audit değildir; kalan inceleme ve PIT OOS analizi açıktır.

Her legacy ratio için tablo:

```
ratio_name
economic_thesis
formula
direction
sector_applicability
required_fields
period_semantics
PIT_safety
outlier_behavior
coverage
redundancy_cluster
current_forward_IC
incremental_IC
decision
reason
```

Decision:

- KEEP_AS_IS
- PORT_WITH_CHANGES
- REWRITE
- DELETE

## TR2-012 — Kompozit ve pillar audit

**Durum: PLANNED**

Eski:

- quality
- growth
- value
- pillar weights
- family normalization

tek tek sınanacak.

Soru:

> Bu toplulaştırma gerçekten forward bilgi artırıyor mu, yoksa yalnız muhasebe sınıflandırması mı?

## TR2-013 — Transform/eşik audit

**Durum: PLANNED**

Tüm:

- hard thresholds
- anchors
- sigmoid/logistic
- winsorization
- median/MAD transforms
- coverage gates

tek tek forward test edilecek.

## TR2-014 — Araştırma baseline doğrulaması

**Durum: PLANNED**

Mevcut IC sonuçları yeniden üretilecek:

- aynı evren
- aynı as-of
- aynı horizon
- aynı price source
- aynı availability assumptions

Amaç önceki sonucu kutsamak değil, reproducibility testidir.

---

# TR2-020 — VERİ SÖZLEŞMESİ

**Durum: READY**

Yeni model önce veri sözleşmesini kuracak.

Canonical observation:

```
entity_id
feature_id
value
unit
currency
period_start
period_end
published_at
available_at
snapshot_at
source
source_record_id
revision_state
quality_flag
parser_version
```

Kaynak sınıfları:

- KAP reported
- market
- InvestingPro+ export
- derived
- consensus/estimate
- manual audited input

---

# TR2-021 — İlk InvestingPro+ gerçek export

**Durum: BLOCKED**

Gerekli:

- BIST evreninden gerçek CSV/XLSX export
- export zamanı
- seçili kolonlar
- screener filtreleri
- mümkün olan en geniş alan seti

**Gerçek dosya gelmeden kolon mapping yazılmayacak.**

---

# TR2-022 — Immutable raw ingest

**Durum: DONE — CSV snapshot çekirdeği; gerçek Pro+ export kanıtı TR2-021'de bekliyor**

Her source snapshot:

```
sha256
source
snapshot_at
filename
schema_fingerprint
row_count
column_count
universe_definition
parser_version
```

saklamalı.

Raw dosya overwrite edilmez.

Uygulama kanıtı (`TR2-022`): `src/tr2/ingest.py` ham CSV baytlarını
SHA256 adresli özel depoya kopyalar; her ingest için ayrı JSON manifest yazar.
Timezone'suz export zamanı, bozuk CSV, yinelenen başlık veya güvensiz depo
konumu reddedilir. `tests/tr2/test_ingest.py`: **7 passed**; tam repo:
**112 passed** (2026-09-23 yerel çalışma). Gerçek InvestingPro+ dosyasının
satır/sütun/şema receipt'i henüz yoktur; TR2-021 kapanmadan gerçek vendor
entegrasyonu veya canonical mapping tamamlanmış sayılmaz. XLSX parserı gerçek
dosya görülünce kararlaştırılacaktır.

## TR2-023 — InvestingPro+ canonical field mapping

**Durum: BLOCKED → TR2-021**

Gerçek export başlıkları, kimlik alanları, birimler, dönem ve PIT anlamları
görülmeden vendor alanları canonical feature'lara eşlenmeyecek.

---

# TR2-030 — PIT / PROVENANCE ÇEKİRDEĞİ

**Durum: PLANNED**

Ana invariant:

```
feature.available_at <= model_as_of
```

Test zorunlulukları:

- future filing blocked
- later restatement blocked unless explicitly requested
- current Pro+ historical view cannot leak backward
- estimate revision requires two real historical snapshots
- price window cannot include bars after as-of

---

# TR2-040 — FEATURE REGISTRY

**Durum: PLANNED**

Eski ve yeni bütün feature adayları aynı registry'ye girecek.

Her feature:

```
feature_id
economic_thesis
source
formula
direction
sector_scope
normalization_candidates
missing_semantics
PIT_grade
coverage
redundancy_cluster
status
```

Hiçbir feature yalnız "yaygın kullanılan rasyo" olduğu için production'a alınmaz.

---

# TR2-050 — FACTOR DISCOVERY

**Durum: PLANNED**

Başlangıç aileleri yalnız hipotezdir:

- Quality
- Valuation
- Growth
- Expectations/Revisions
- Fundamental Momentum
- Price Momentum/Residual Alpha
- Capital Allocation
- Earnings Quality
- Liquidity/Microstructure

Her aile için:

1. univariate rank IC
2. rolling IC
3. positive-month ratio
4. sector IC
5. regime IC
6. incremental IC
7. correlation/redundancy
8. monotonic decile spread

kanıtlanacak.

Forward bilgi taşımayan aile silinir.

---

# TR2-060 — INVESTINGPRO+ FEATURE FACTORY

**Durum: BLOCKED → TR2-021**

Gerçek export sonrası:

```
1200+ vendor fields
→ semantic mapping
→ availability audit
→ PIT classification
→ coverage filter
→ redundancy clustering
→ candidate transforms
→ univariate IC
→ incremental IC
→ OOS survival
```

Özel kullanım:

- Fair Value = challenger/ensemble input
- Financial Health = benchmark/challenger
- Altman/Beneish = candidate features
- forward estimates = expectations
- revisions = expectations momentum
- surprises = earnings-information factor

**Hazır vendor score doğrudan Total Rasyo'ya eklenmez.**

---

# TR2-070 — ALPHA MODEL V1

**Durum: PLANNED**

İlk challenger'lar:

```
A) equal-weight factor ranks
B) bounded linear model
C) ridge / elastic-net
D) rank ensemble
```

Kural:

- en basit model OOS'da yeterliyse karmaşık model reddedilir.
- tüm model selection training fold içinde yapılır.
- factor direction training dışında keyfi çevrilmez.

Primary target:

**future sector/market-adjusted return rank**

İlk horizon seti:

- 1M
- 3M
- 6M
- 12M

Horizon sonradan cherry-pick edilmeyecek; hepsi raporlanacak.

---

# TR2-080 — CONFIDENCE MODEL

**Durum: PLANNED**

Alpha'dan bağımsız.

Adaylar:

- source coverage
- feature coverage
- freshness
- PIT grade
- peer count
- valuation dispersion
- source disagreement
- estimate age
- schema stability

Confidence score'un görevi:

> alpha'nın doğru olma olasılığını veya veri sağlamlığını açıklamak.

Alpha'yı otomatik 0.5'e çekmek değildir.

---

# TR2-090 — RISK MODEL

**Durum: PLANNED**

Adaylar:

- realized volatility
- downside volatility
- max drawdown
- beta
- liquidity
- gap risk
- tail risk
- balance-sheet distress

Risk yüksek diye şirket otomatik "kötü alpha" sayılmaz.

---

# TR2-100 — 0–100 TOTAL RASYO

**Durum: PLANNED**

Default challenger:

```
TotalRasyo = 100 * cross_sectional_percentile(raw_alpha)
```

Alternatif:

- empirical CDF calibration
- sector-neutral percentile then global blend

Seçim yalnız OOS davranış ve yorumlanabilirlikle yapılacak.

---

# TR2-110 — NESTED WALK-FORWARD

**Durum: PLANNED**

Dış fold:

- gerçek OOS test.

İç fold:

- transform seçimi
- feature selection
- regularization
- coefficient fitting
- threshold selection

Rapor:

- mean IC
- ICIR
- NW t
- positive months
- decile monotonicity
- top-bottom spread
- turnover
- cost-adjusted return
- drawdown
- sector robustness
- regime robustness

---

# TR2-120 — PORTFOLIO POLICY

**Durum: PLANNED**

Alpha modelden bağımsız test:

- top N
- percentile threshold
- confidence gate
- risk cap
- sector cap
- liquidity floor
- rebalance schedule
- holding period
- turnover cap

Eski Top-10 / fixed threshold kuralları sıfırdan yarışmaya girer; otomatik korunmaz.

---

# TR2-130 — SHADOW PRODUCTION

**Durum: PLANNED**

Canlı olarak birlikte kayıt:

```
legacy_output
tr2_raw_alpha
tr2_total_rasyo
tr2_confidence
tr2_risk
model_version
feature_snapshot_id
```

Bu fazda TR2 yatırım kararı otoritesi olmaz; gerçek forward outcome biriktirir.

---

# TR2-140 — CUTOVER / LEGACY CLEANUP

**Durum: PLANNED**

Production geçiş şartı:

- nested OOS PASS
- PIT audit PASS
- reproducibility PASS
- data drift monitoring hazır
- Pro+ contribution ölçülmüş
- benchmark comparison tamam
- shadow period kritik hata yok

Sonrasında:

- TR2 production default olur.
- Kullanılmayan legacy production kodu silinir.
- Gerekli araştırma kayıtları Git history'de kalır.

---

# ŞİMDİKİ EN KÜÇÜK ENGELSİZ İŞ

**TR2-011 — Legacy oran envanteri ve KEEP/PORT/REWRITE/DELETE auditi.**

Bu iş eski sistemi kabul etmek için değil, sıfırdan kuracağımız feature evrenine neyin girmeye değer olduğunu belirlemek içindir.

Paralel dış bağımlılık:

**TR2-021 — İlk gerçek InvestingPro+ BIST export dosyası.**

---

# CHANGELOG

## 2026-09-23 — Greenfield reset

- Önceki "mevcut v2 motorunu koru" varsayımı iptal edildi.
- Mevcut 67 rasyo, pillar/family ve kompozitlerin tamamı yeniden denetime açıldı.
- Total Rasyo 2.0 ayrı namespace altında sıfırdan kurulacak.
- Eski kod yalnız evidence/baseline olarak kullanılacak.
- Eski parça ancak KEEP/PORT/REWRITE/DELETE auditi sonrası TR2'ye girebilir.
- InvestingPro+ entegrasyonu yeni sistemin feature discovery katmanına bağlandı.
- Roadmap'in her işlemde güncellenmesi zorunluluğu korundu.
- README aktif yön bölümü greenfield reset'e geçirildi; legacy motor açıkça yalnız baseline olarak işaretlendi (`f3b0825`).
- `DEVIR.md` eski kararların yanlışlıkla aktif kabul edilmesini önlemek için LEGACY/otorite değil olarak damgalandı (`9c7185a`).

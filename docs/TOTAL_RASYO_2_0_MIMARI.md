# TOTAL RASYO 2.0 — Matematik ve InvestingPro+ Mimari Kararı

**Durum:** KABUL EDİLEN YENİ YÖN  
**Tarih:** 2026-09-23  
**Başlangıç HEAD:** `be6217600eb69ca7248f72b56400eae03c2d6fe4`  
**Kapsam:** Total Rasyo Fit Version — skor matematiğinin yeniden kurulması ve InvestingPro+ veri avantajının sisteme eklenmesi.

> Bu belge bir "puanları yükseltme" çalışması değildir. Amaç, 0–100 sayısının gerçekten gelecekteki göreli performansı sıralayan, sektörler arasında adil, point-in-time güvenli ve tarihsel olarak doğrulanabilir bir yatırım sinyaline dönüşmesidir.

---

## 1. Mevcut sağlam temel korunacak

Bu repo eski Total Rasyo matematiğinin bazı temel kusurlarını zaten gidermiş durumda ve bu işler çöpe atılmayacak:

- 67 rasyo / 19 aile / 7 pillar.
- Sektör bazlı `applies_to`.
- `OK / MISSING / BEST / WORST / NOT_APPLICABLE` ayrımı.
- Explicit coverage ve fail-closed davranış.
- Rasyo sayısından bağımsız family/pillar ağırlıklandırması.
- Mutlak `good_count` yerine ağırlıklı `good_ratio`.
- Medyan/MAD tabanlı robust kesitsel skorlama.
- Quality / Growth / Value kompozitlerinin birbirinden ayrılması.
- Tarihsel araştırma ve IC ölçüm düzeneği.

Yani Total Rasyo 2.0, **rasyo motorunu yıkıp yeniden yazmak değil; onun üstündeki yatırım-sinyali matematiğini yeniden kurmaktır.**

---

## 2. 2026-09-23 araştırma baseline'ı

Yeni mimarinin başarısı aşağıdaki bugünkü sonuçlara göre ölçülecek. Bunlar nihai sonuç değil, başlangıç baseline'ıdır.

Mevcut repo araştırmalarında:

- Aylık kesit / 6 aylık ileri getiri:
  - Value mean IC yaklaşık **+0.136**, Newey-West t yaklaşık **+2.03**, pozitif ay oranı %78.
  - Quality mean IC yaklaşık **+0.092**, Newey-West t yaklaşık **+2.08**, pozitif ay oranı %75.
  - Growth mean IC yaklaşık **+0.004**, Newey-West t yaklaşık **+0.05**, pozitif ay oranı %44.
- Mevcut 12 aylık seçim backtest'i:
  - Strateji yaklaşık **+%5.5 net**.
  - Aynı evren yaklaşık **+%9.2**.
  - Strateji benchmarkın yaklaşık **3.7 puan** gerisinde.
- Seçimlerin pozitif olma oranı yaklaşık **%48**, evrenin pozitif olma oranı da yaklaşık **%48**.
- Top-10-by-rank yaklaşımı mevcut kısa örnekte güvenilir üstünlük göstermedi.
- Mutlak score barları ve holding period değişimleri arasında geniş oynaklık var; mevcut örnek boyutu bunlardan sağlam bir stratejik karar çıkarmak için yetersiz.

**Sonuç:** Rasyo motorunda sinyal izi var; sorun yalnız veri eksikliği değil. Üst seviye faktör birleştirme, ölçekleme, seçim, güven ve risk matematiği yeniden tasarlanmalıdır.

---

## 3. Total Rasyo 2.0'ın temel ilkesi

Eski yaklaşım:

```
çeşitli 0..1 modüller
    ↓
sabit ağırlıklı ortalama
    ↓
0..100
```

Yeni yaklaşım:

```
KAP + InvestingPro+ + piyasa verisi
    ↓
kanonik ve PIT güvenli ham özellikler
    ↓
sektör/ekonomik aile içinde robust normalizasyon
    ↓
bağımsız faktör aileleri
    ↓
walk-forward doğrulanmış ve kısıtlı faktör birleşimi
    ↓
Raw Alpha
    ↓
BIST kesitsel rank / calibrated percentile
    ↓
TOTAL RASYO 0–100
```

Paralel olarak ayrıca:

```
Coverage + veri tazeliği + model anlaşmazlığı → CONFIDENCE 0–100
Volatilite + drawdown + likidite + tail risk → RISK 0–100
```

**Alpha, confidence ve risk aynı sayı içinde eritilmeyecek.**

---

## 4. 0–100'ün yeni anlamı

Total Rasyo 2.0'da 0–100, "teorik kusursuzluğun yüzdesi" olmayacak.

Hedef semantik:

- 100 ≈ o as-of tarihinde yatırım evrenindeki en güçlü birleşik sinyal.
- 90 ≈ yaklaşık üst %10.
- 50 ≈ evren medyanı.
- 10 ≈ yaklaşık alt %10.
- 0 ≈ evrenin en zayıf uçları.

Üretimde iki skor birlikte saklanacak:

1. **Raw Alpha / model score** — araştırma, IC ve backtest için.
2. **Total Rasyo 0–100 display rank** — kullanıcının yorumlayacağı ortak ölçek.

Böylece 0–100 tamamı kullanılan bir ölçek olur; fakat model matematiği kozmetik olarak "yüksek puan üretmeye" zorlanmaz.

---

## 5. Faktör aileleri

Üretim seviyesinde eski M1/M2/M3/Ek1/Ek4/Ek9 adları belirleyici mimari olmayacak. Uyumluluk/izleme için tutulabilirler.

### 5.1 Quality

Amaç: Şirketin bugünkü ekonomik/muhasebesel kalitesini ölçmek.

Alt eksenler:

- Profitability
- Cash Flow Quality
- Balance Sheet Strength
- Capital Efficiency
- Operating Efficiency
- Earnings Quality
- Accounting / distress quality

Mevcut 67 rasyo motoru bunun ana kaynağıdır.

**Kural:** İyi şirketin puanı "artık daha da iyileşmiyor" diye düşürülemez.

### 5.2 Fundamental Trend

Quality seviyesinden ayrı tutulur.

Ölçülebilecek bileşenler:

- 1Q değişim
- 4Q değişim
- 8Q trend
- marj eğimi
- nakit dönüşümü eğimi
- bilanço iyileşmesi/kötüleşmesi

Trend bir **bonus/erken değişim sinyali**dir; quality seviyesinin yerine geçmez.

### 5.3 Valuation

Eski M2 mantığı kaldırılacak.

Valuation yalnızca değerlemeyi ölçer:

- relative multiples
- earnings / book / sales / cash-flow multiples
- own fair-value models
- InvestingPro Fair Value ailesi
- mevcutsa analyst target / consensus gibi bağımsız kaynaklar

Fiyatın yakın dönemde yükselmiş olması "ucuzluk" sinyalini otomatik olarak silmez.

### 5.4 Growth

Büyüme kaliteden ayrı tutulur:

- revenue growth
- EPS growth
- EBITDA growth
- FCF growth
- 3Y / 5Y CAGR
- sektör-nötr büyüme

Mevcut baseline'da Growth IC zayıf olduğu için bu faktör **kanıtlanmadan yüksek ağırlık alamaz**.

### 5.5 Expectations / Revisions

InvestingPro+ ile eklenmesi hedeflenen kritik yeni eksen.

Adaylar:

- forward EPS
- forward revenue
- forward EBITDA
- 1M / 3M estimate revision
- earnings surprise
- consensus change
- mevcutsa analyst target revision

Örnek:

```
revision = (EPS_fwd_now / EPS_fwd_3m_ago) - 1
```

Bu eksen şirketin yalnız geçmişini değil, piyasanın temel beklentisinin hangi yönde değiştiğini ölçer.

### 5.6 Momentum / Residual Alpha

Valuation'dan tamamen ayrı tutulur.

Adaylar:

- 20d relative momentum
- 63d relative momentum
- 126d relative momentum
- sector-adjusted momentum
- market/sector residual alpha
- trend persistence

Aynı bilgi iki farklı modülde tekrar ağırlıklandırılmayacak. Korelasyon ve redundancy kontrolü yapılacak.

---

## 6. Confidence ayrı bir eksendir

Eski tür:

```
güven düşük → sinyali 0.50'ye çek
```

yaklaşımı yeni tasarımda kullanılmayacak.

Örnek:

```
Valuation = 91
Confidence = 43
```

Bu ikisi ayrı gerçektir.

Confidence bileşenleri:

- veri coverage
- veri freshness
- model availability
- source agreement
- valuation dispersion
- InvestingPro vs own-model disagreement
- point-in-time provenance strength
- küçük peer group cezası
- stale forecast cezası

Confidence alpha'yı yok etmez; gerekirse **etkin faktör ağırlığını** azaltır veya üretim kararına ayrı kapı koyar.

---

## 7. Risk ayrı bir eksendir

Volatilite artık "şirket kalitesi" veya "ucuzluk" puanını doğrudan azaltmayacak.

Risk adayları:

- realized volatility
- downside volatility
- max drawdown
- liquidity / ADV
- beta
- gap risk
- tail-risk ölçüleri
- leverage/distress risk

Çıktı:

- `TOTAL_RASYO_0_100`
- `CONFIDENCE_0_100`
- `RISK_0_100`

Gerekirse bunlardan ayrıca `RISK_ADJUSTED_TOTAL_RASYO` türetilebilir; fakat ham alpha saklanır.

---

## 8. InvestingPro+ rolü

Kullanıcının InvestingPro+ üyeliği **2026-09-23 itibarıyla edinildi**.

InvestingPro+ projeye "hazır skoru kopyalama" şeklinde eklenmeyecek.

Dört rolü vardır:

### 8.1 Veri zenginleştirme

Pro+ export'larından erişilebildiği ölçüde:

- uzun tarihsel finansal seri
- forward estimates
- estimate revisions
- earnings / surprise alanları
- gelişmiş finansal metrikler
- Altman Z
- Beneish M
- diğer doğrulanabilir export alanları

kanonik şemaya alınır.

### 8.2 Valuation challenger / ensemble

InvestingPro Fair Value, bizim değerleme motorunun yerine geçmez.

```
Own Valuation
InvestingPro Fair Value
Other independent valuation evidence
```

ayrı tutulur.

Agreement/disagreement hem feature hem confidence girdisi olabilir.

### 8.3 Independent benchmark

InvestingPro Financial Health / ilgili hazır skorlar doğrudan Total Rasyo'ya sabit yüzdeyle eklenmez.

Ama:

- kendi Quality faktörümüzle karşılaştırılır,
- disagreement üretilir,
- challenger model olarak backtest edilir.

Bu, double counting riskini azaltır.

### 8.4 Feature factory

Pro+ tarafındaki 1.200+ metrik doğrudan modele doldurulmaz.

Hedef süreç:

```
1200+ raw field
→ availability / semantics / PIT audit
→ ekonomik kümelendirme
→ redundancy / correlation filtresi
→ coverage filtresi
→ univariate IC ve stability
→ incremental IC / orthogonality
→ yaklaşık 15–40 üretim faktörü
```

Sayının yüksek olması kalite değildir. Sadece **daha iyi aday havuzu** sağlar.

---

## 9. InvestingPro+ veri alım kuralı

Mevcut resmi ürün bilgisi ve repo araştırmasına göre aboneliğin programatik API erişimi sunduğu varsayılmayacak.

İlk güvenli tasarım:

```
manual CSV/XLSX export
→ immutable raw snapshot
→ SHA256
→ export timestamp
→ source metadata
→ schema fingerprint
→ canonical field mapper
→ feature store
```

**Gerçek export görülmeden kolon isimleri uydurulmayacak.**

Her raw export sonradan değiştirilemez şekilde saklanmalı; dönüştürülmüş veri raw kaynağa geri izlenebilir olmalıdır.

---

## 10. Point-in-time (PIT) kuralı

InvestingPro'nun bugün gösterdiği tarihsel bir metrik, otomatik olarak "o tarihte yatırımcı tarafından biliniyordu" kabul edilemez.

Backtest için:

- KAP publication timestamp ana otorite olmaya devam eder.
- Pro+ export'ları alındıkları tarihten itibaren güvenli forward snapshot olarak kullanılabilir.
- Historical Pro+ alanların revision/restatement riski ayrıca işaretlenir.
- Availability timestamp bilinmiyorsa geçmişe sızdırılmaz.
- Analyst/estimate verileri snapshot tarihi olmadan historical backteste sokulmaz.

Amaç yüksek görünen sahte IC değil, **gerçek zamanlı uygulanabilir IC**dir.

---

## 11. Normalizasyon

Aynı ekonomik büyüklükler şirketler arasında mutlak eşiklerle kör biçimde puanlanmayacak.

Tercih sırası:

1. Sektör/peer cross-sectional percentile.
2. Robust z-score (median/MAD).
3. Gerekliyse sektör-nötr residualization.
4. Sadece ekonomik anlamı gerçekten sabit olan değişkenlerde mutlak anchor.

Banka, GYO, holding ve sanayi şirketleri aynı keyfi eşiklerle ölçülmez.

---

## 12. Model matematiği

İlk kavramsal form:

```
RawAlpha =
    βQ * Quality
  + βV * Valuation
  + βG * Growth
  + βE * Expectations
  + βM * Momentum
  + βF * FundamentalTrend
  + validated_interactions
```

Ancak `β` değerleri elle kutsal sayı olarak belirlenmeyecek.

Öğrenme:

- expanding / rolling walk-forward
- yalnız geçmişte mevcut bilgi
- bounded weights
- shrinkage / regularization
- correlated factor penalty
- minimum coverage gates
- sektör stabilitesi kontrolü

67 rasyonun her birine ayrı fit ağırlığı vermek yasaktır. Mevcut repo prensibi korunur: model serbestliği faktör/eksen seviyesinde tutulur.

---

## 13. Ana optimizasyon hedefi

Model "yüksek Total Rasyo" üretmek için optimize edilmez.

Ana araştırma hedefleri:

- Spearman rank IC
- IC mean
- ICIR
- Newey-West adjusted significance
- positive-IC month ratio
- top-minus-bottom spread
- top decile excess return
- hit rate
- drawdown
- turnover
- transaction-cost sonrası sonuç
- sektör ve rejim stabilitesi

Ayrıca **ablation** zorunludur:

```
model - Quality
model - Valuation
model - Momentum
model - Pro+ fields
...
```

Bir faktör çıkarılınca performans bozulmuyorsa o faktör üretimde yer almamalıdır.

---

## 14. Seçim stratejisi skor modelinden ayrılacak

Bugünkü araştırma şunu gösteriyor: pozitif IC, otomatik olarak başarılı Top-10 portföy anlamına gelmiyor.

Bu nedenle:

**Score model** ve **portfolio/selection policy** iki farklı bileşendir.

Önce alpha sıralamasının geçerliliği kanıtlanır.

Sonra ayrı test edilir:

- top-N
- percentile threshold
- absolute raw-alpha threshold
- both-factor gates
- confidence gates
- sector caps
- liquidity constraints
- rebalance frequency
- holding period

Bunların hiçbiri score modelinin içine gizlenmez.

---

## 15. Eski Total Rasyo ile ilişki

Eski üretim matematiği silinmeden önce **Legacy** olarak dondurulur.

Yeni sistem paralel çalışır:

```
legacy_score
tr2_raw_alpha
tr2_total_0_100
tr2_confidence
tr2_risk
```

Aynı tarih/evren üzerinde karşılaştırma yapılır.

Yeni sistem yalnız kabul kriterlerini geçtiğinde varsayılan hale gelir.

---

## 16. Yasaklar

Aşağıdakiler Total Rasyo 2.0'da yasaktır:

- Puanları güzel göstermek için skor inflasyonu.
- Eksik veriye sessiz 0.5 / 0 / ortalama doldurma.
- Historical timestamp bilinmeyen forecast'i geçmişe sızdırma.
- Aynı ekonomik sinyali farklı isimlerle iki kere ağırlıklandırma.
- Pro+ hazır skorunu sorgusuz Total'e ekleme.
- In-sample sonucu production başarı kanıtı sayma.
- Birkaç aylık backtest sonucuna göre sabit ağırlık seçme.
- Sadece CAGR'a bakıp benchmark ve risk ölçülerini yok sayma.
- Current-period veriyle historical model selection yapma.
- Mevcut güçlü fail-closed veri semantiğini bozma.

---

## 17. Başarı tanımı

Total Rasyo 2.0 başarılı sayılmak için yalnız "100'e çıkan hisse var" şartını değil, aşağıdakileri karşılamalı:

1. 0–100 skala tam ve yorumlanabilir kullanılmalı.
2. PIT backtest temiz olmalı.
3. Quality/Value gibi baseline pozitif sinyaller korunmalı veya iyileştirilmeli.
4. Yeni faktörler incremental out-of-sample bilgi getirmeli.
5. Score sıralaması, evrene karşı ileri getirilerde istikrarlı ayrım yaratmalı.
6. Portfolio policy, işlem maliyeti sonrası benchmarka karşı değerlendirilmelidir.
7. Confidence gerçekten düşük-güvenli gözlemleri ayırabilmeli.
8. Risk ayrı raporlanmalı.
9. Pro+ veri katkısı ablation ile kanıtlanmalı.
10. Her değişiklik yaşayan roadmap'te işlenmeli.

---

## 18. Yönetim kuralı

Uygulama planının tek otoritesi repository root'taki `ROADMAP.md` dosyasıdır.

Her geliştirme işleminde:

1. Önce güncel HEAD alınır.
2. Yapılacak iş roadmap'teki bir Work Item'a bağlanır.
3. Kod/veri/test değişikliği yapılır.
4. Kanıt/test sonucu kaydedilir.
5. **Aynı iş içinde ROADMAP.md güncellenir.**
6. İş `DONE` olmadan "tamamlandı" denmez.
7. Yeni bulgu planı değiştiriyorsa eski karar silinmez; değişikliğin nedeni changelog'a eklenir.


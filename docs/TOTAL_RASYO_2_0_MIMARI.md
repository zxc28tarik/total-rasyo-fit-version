# TOTAL RASYO 2.0 — GREENFIELD MİMARİ

**Durum:** AKTİF TASARIM OTORİTESİ  
**Tarih:** 2026-09-23  
**Başlangıç ilkesi:** Mevcut sistemden hiçbir matematiksel karar, oran, ağırlık, eşik, modül veya veri dönüşümü otomatik olarak devralınmaz.

> Total Rasyo 2.0 eski sistemin düzeltilmiş sürümü değil; aynı problemi daha doğru çözmek için sıfırdan tasarlanan yeni motordur.

---

## 1. Greenfield kuralı

Mevcut repository üç şey için kullanılabilir:

1. tarihsel araştırma kanıtı,
2. yeniden kullanılabilecek veri erişimi / test fikri,
3. karşılaştırma için legacy baseline.

Bunların dışında hiçbir parça "korunacak" kabul edilmez.

Her legacy bileşeni şu dört sonuçtan birini alır:

- KEEP_AS_IS
- PORT_WITH_CHANGES
- REWRITE
- DELETE

Karar ancak ekonomik mantık + matematik + veri semantiği + PIT güvenliği + test/backtest sonucu birlikte incelendikten sonra verilir.

---

## 2. Ana hedef

Total Rasyo 2.0'ın görevi:

**Bir şirketin gelecekteki sektör/piyasa düzeltilmiş göreli getiri potansiyelini sıralamak.**

Dolayısıyla ana başarı ölçüsü:

- skorun yüksek görünmesi değil,
- geçmiş finansalların iyi açıklanması değil,
- 100'e ulaşılması değil,
- forward out-of-sample rank IC ve ekonomik olarak uygulanabilir spread üretmesidir.

---

## 3. Üç ayrı çıktı

Yeni motor tek sayı üretmeye zorlanmaz.

### Alpha
Şirketin göreli ileri getiri sinyali.

### Confidence
Bu sinyalin veri ve model açısından ne kadar güvenilir olduğu.

### Risk
Bu fırsatın volatilite, drawdown, likidite ve tail-risk profili.

Üretim çıktısı:

```
raw_alpha
total_rasyo_0_100
confidence_0_100
risk_0_100
```

Risk veya confidence alpha'nın içine gizlenmez.

---

## 4. 0–100 semantiği

Total Rasyo 0–100 teorik kusursuzluk yüzdesi değildir.

Hedef:

```
total_rasyo_0_100 = calibrated cross-sectional rank(raw_alpha)
```

Yaklaşık yorum:

- 100: o tarihte evrendeki en güçlü sinyallerin ucu
- 90: üst yaklaşık %10
- 50: medyan
- 10: alt yaklaşık %10
- 0: en zayıf uç

Raw alpha ayrıca saklanır ve bütün araştırma raw alpha üzerinden doğrulanır.

---

## 5. Veri kaynakları

### KAP
Historical point-in-time finansal gerçekliğin ana otoritesi.

### Piyasa verisi
Fiyat, hacim, endeks/sektör getirileri, volatilite, beta, liquidity.

### InvestingPro+
Kullanıcının Pro+ üyeliği aktif.

Rolleri:

- current data enrichment
- forward estimates / revisions
- metric feature factory
- Fair Value challenger / ensemble input
- Financial Health ve benzeri skorları bağımsız benchmark/challenger
- ileri tarihler için düzenli snapshot üretimi

**Yasak:** InvestingPro'nun hazır puanını doğrudan Total Rasyo ağırlığına koymak.

---

## 6. PIT kuralı

Her feature aşağıdaki bilgiye sahip olmalıdır:

```
value
period_end
published_at / available_at
source
source_snapshot_at
revision_state
provenance
```

Historical backtest:

```
feature.available_at <= as_of
```

olmadan feature kullanamaz.

Bugün Pro+ ekranında görülen geçmiş değer otomatik olarak historical PIT veri değildir.

---

## 7. Factor discovery yaklaşımı

Faktör aileleri başlangıç hipotezidir; kutsal modüller değildir.

İlk araştırma aileleri:

- Quality
- Valuation
- Growth
- Expectations / Revisions
- Fundamental Momentum
- Price Momentum / Residual Alpha
- Capital Allocation
- Earnings Quality / Accounting Risk
- Liquidity / Market Microstructure
- Risk

Bir aile forward bilgi taşımıyorsa silinir.

Bir feature başka feature ile aynı bilgiyi taşıyorsa birleştirilir veya silinir.

---

## 8. Finansal oran politikası

Eski 67 oran otomatik devralınmaz.

Her oran için sıfırdan audit:

```
ekonomik tez
formül doğruluğu
işaret yönü
sektör uygulanabilirliği
pay/payda semantiği
TTM / point-in-time kullanımı
enflasyon etkisi
outlier davranışı
coverage
forward IC
incremental IC
redundancy
```

Sınavı geçmeyen oran silinir.

Yeni Pro+ alanı daha iyi bir feature veriyorsa eski oran sırf geçmişte kullanıldı diye korunmaz.

---

## 9. Normalizasyon

Tek bir normalizasyon her feature'a uygulanmaz.

Aday yöntemler:

- sector/peer percentile
- median/MAD robust z-score
- rank-gaussian
- historical own-company percentile
- sector-neutral residual
- economically justified hard transform

Her feature'ın dönüşümü forward test ile seçilir.

Mutlak eşik yalnız ekonomik olarak zamanlar ve sektörler arasında anlamı sabitse kullanılabilir.

---

## 10. Quality

Quality yalnız geçmiş seviyeyi ölçer.

Aday temalar:

- profitability
- return on capital
- balance-sheet strength
- cash-flow conversion
- earnings quality
- operating efficiency
- financial distress
- accounting manipulation risk

Stabil yüksek kalite, "iyileşmiyor" diye cezalandırılmaz.

---

## 11. Fundamental Momentum

Quality'den ayrı faktördür.

Adaylar:

- QoQ change
- YoY change
- 8Q robust slope
- acceleration
- margin inflection
- FCF conversion inflection
- leverage improvement/deterioration
- estimate-linked fundamental surprise

Seviye ve değişim aynı skora zorla karıştırılmaz.

---

## 12. Valuation

Valuation yalnız "fiyata göre ekonomik değer" problemidir.

Aday kaynaklar:

- relative multiples
- historical relative multiples
- sector-relative multiples
- FCF / earnings yield
- own fair-value models
- InvestingPro Fair Value
- consensus/target data mevcut ve PIT güvenli ise

Fiyatın yükselmesi kendi başına valuation sinyalini düşürmez; bu momentum tarafında değerlendirilir.

---

## 13. Expectations / Revisions

Pro+ üyeliğinin en önemli potansiyel katkılarından biri.

Adaylar:

- forward EPS
- forward revenue
- forward EBITDA
- 1M / 3M revision
- dispersion
- earnings surprise
- target/consensus revision

Historical kullanımı yalnız gerçek snapshot geçmişi varsa mümkündür.

---

## 14. Momentum / Residual Alpha

Adaylar:

- 20d
- 63d
- 126d
- 252d
- sector relative
- market relative
- residual momentum
- momentum quality / consistency
- reversal controls

Valuation ile tek bir FOLLOW formülünde birleştirilmez.

---

## 15. Confidence

Confidence ayrı modeldir.

Aday girdiler:

- feature coverage
- source coverage
- data freshness
- PIT provenance quality
- peer-group size
- valuation-model dispersion
- source disagreement
- estimate age
- schema stability

Düşük confidence, sinyal değerini mekanik olarak 0.50'ye çekmek zorunda değildir.

---

## 16. Risk

Adaylar:

- realized volatility
- downside volatility
- drawdown
- beta
- liquidity
- gap risk
- tail risk
- balance-sheet distress
- concentration/event risk

Risk ayrıca raporlanır.

---

## 17. InvestingPro+ feature factory

1.200+ alanın tamamını modele sokmak yasaktır.

Akış:

```
raw export
→ immutable snapshot
→ schema/profile
→ canonical mapping
→ semantic families
→ coverage/PIT audit
→ redundancy clustering
→ univariate IC
→ incremental IC
→ rolling stability
→ OOS survival
→ production feature set
```

Üretim setinin büyüklüğü önceden belirlenmez; kanıt ne kadarını destekliyorsa o kadar kalır.

---

## 18. Model öğrenimi

Amaç lineer model kullanmak değildir; amaç **overfit olmayan en basit yeterli modeli** bulmaktır.

Challenger seti:

- equal-weight ranks
- bounded linear factor model
- ridge / elastic-net
- monotonic GAM benzeri modeller
- rank ensemble

Daha karmaşık yöntem ancak walk-forward OOS avantajı kanıtlanırsa ilerler.

Model selection nested walk-forward yapılmalıdır.

---

## 19. Weight politikası

Ağırlıklar elle kutsal sayı değildir.

Ancak özgür optimizasyon da yapılmaz.

Zorunlu korumalar:

- bounded coefficients
- regularization
- minimum training window
- parameter budget
- correlated-feature penalty
- sector stability checks
- coefficient drift monitoring

Per-ratio yüzlerce serbest ağırlık default olarak reddedilir.

---

## 20. Ana hedef fonksiyonu

Primary:

- forward sector/market-adjusted Spearman Rank IC

Secondary:

- ICIR
- positive IC month ratio
- top-minus-bottom spread
- monotonic decile return profile
- top-decile excess return
- turnover
- transaction-cost net return
- drawdown
- breadth
- sector/regime stability

Hiçbir tek metrik tek başına production geçiş kararı veremez.

---

## 21. Portfolio policy ayrı sistemdir

Alpha model "hangi hisse daha güçlü?" sorusunu cevaplar.

Portfolio policy:

- kaç hisse
- threshold
- sector cap
- liquidity floor
- confidence gate
- risk cap
- rebalance frequency
- holding period
- transaction cost

sorularını ayrı çözer.

Top-10, >0.60 veya başka eski kurallar otomatik devralınmaz.

---

## 22. Legacy kod politikası

Yeni uygulama ayrı namespace ile başlayacaktır:

```
src/tr2/
research/tr2/
tests/tr2/
config/tr2/
```

Legacy kod yeni motor tarafından import edilmez.

Bir legacy parça kullanılacaksa:

1. audit edilir,
2. davranışı testle tanımlanır,
3. yeni TR2 sözleşmesine port edilir,
4. kaynak/provenance notu eklenir.

Port edilmeyen legacy kod production TR2'nin parçası değildir.

---

## 23. Kabul / silme politikası

Eski dosya veya modül sırf çalışıyor diye korunmaz.

Silme adayları:

- ekonomik anlamı zayıf formüller
- redundantly aynı sinyal
- arbitrary thresholds
- score-inflation transforms
- confidence-alpha karışımı
- risk-alpha karışımı
- leakage riski
- vendor field tahmini
- backward-looking olup forward bilgi taşımayan feature
- kısa backtestte tesadüfen iyi görünen kural

Repository history zaten eski kodu korur; production ağacında gereksiz legacy taşımak zorunlu değildir.

---

## 24. Başarı tanımı

Total Rasyo 2.0 ancak şu durumda başarılıdır:

```
PIT clean
+ reproducible
+ forward IC positive and stable
+ incremental Pro+ contribution demonstrated
+ monotonic ranking
+ transaction-cost aware
+ sector/regime robustness
+ interpretable provenance
```

0–100 görsel olarak güzel dağılıyor fakat forward ayrım üretmiyorsa sistem başarısızdır.

---

## 25. Yönetim

Tek yaşayan uygulama planı:

`ROADMAP.md`

Her işte roadmap güncellenir.

Eski varsayım geri gelirse açık kanıtla yeniden kabul edilmek zorundadır.

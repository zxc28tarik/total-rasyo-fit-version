# Faz 2 — Motor Sözleşmesi, İki Motor ve Karşılaştırma Yüzeyi: Uygulama Planı

> **Ajan çalışanlar için:** GEREKLİ ALT SKILL: Bu planı görev görev uygulamak
> için superpowers:subagent-driven-development (önerilen) veya
> superpowers:executing-plans kullan. Adımlar takip için checkbox (`- [x]`)
> sözdizimi kullanır.

**Hedef:** Projenin varış noktası olan ekranı çalışır hale getirmek — tek satır
= tek hisse, yan yana motor sıraları, ham oranlar, uzlaşma ve ayrışma listeleri.

**Mimari:** `EngineResult` sözleşmesi bir motorun ne döndüreceğini sabitler;
motorlar `score_universe` çıktısını (`TickerResult`) okur, kendi eksenlerini
ağırlıklandırır, kapılarını **çarpar** (K15) ve tek bir skor + statü üretir.
`src/board/` motorlardan bağımsız durur: N motor alır, sıralar, uzlaşma ve
ayrışma listelerini çıkarır. Karar mutlak eşikle değil sıralamayla verilir (K14).

**Teknoloji:** Python 3.10+, yalnız standart kütüphane, pytest.

---

## Kapsam Kararı — Neden Dört Değil İki Motor

DEVIR.md bölüm 8, madde 3 dört motoru birlikte istiyor. Bu plan **ikisini**
yapıyor. Gerekçe veri, tercih değil — `config/ratios.v2.json` sayıldı:

- 19 ailenin hiçbiri momentum ailesi değil. `price` geçen 16 rasyonun tamamı
  değerleme çarpanı. Fiyat **seviyesi** var (`price_map`), fiyat **geçmişi**
  yok.
- `FX_DEBT_RATIO` tanımlı ama `fx_debt` alanı `KAP_FOOTNOTE` kademesinde ve
  hiçbir kaynaktan gelmiyor; rasyo daima `MISSING`.
- `ACCRUALS_TO_ASSETS` tanımlı ve hesaplanabilir.

Buradan çıkan tablo:

| Motor | Gerektirdiği | Bugün |
|---|---|---|
| Saf Değer | `value` kompoziti | ✅ |
| Kalite Bileşik | `quality` kompoziti + Faz 1 istikrarı | ✅ |
| Total Rasyo v2 | 4 eksen, biri fiyat momentumu | ❌ eksen yok |
| Momentum/Revizyon | fiyat geçmişi + tahmin revizyonu | ❌ veri yok |

Dört motor beklenirse ekran fiyat/hacim ingest'ine kilitlenir; o iş bu repoda
yapılamaz (bkz. Faz 1 Kapsam Kararı). İki motor uzlaşma/ayrışma için yeterlidir:
iki sıralama arasındaki fark da ölçülebilir bir ayrışmadır.

**Faz 3** kalan iki motoru alır ve `G_likidite` ile `G_risk`'i açar; ikisi de
ana projedeki ingest işine bağlıdır.

---

## Bugün Açılamayan Kapılar

Üç kapıdan yalnız biri çalışır. Bu plan eksik kapıyı **sessizce 1.0 kabul
etmez** — motor hangi kapıların uygulanmadığını `notes` alanında taşır, böylece
ekran "bu skor FX riski ölçülmeden üretildi" diyebilir.

| Kapı | Girdi | Durum |
|---|---|---|
| `G_muhasebe` | `ACCRUALS_TO_ASSETS` | ✅ uygulanır |
| `G_risk` | `FX_DEBT_RATIO` | ❌ daima MISSING, uygulanmaz |
| `G_likidite` | `adv_try` | ❌ ingest yok, uygulanmaz |

**K22 — Uygulanamayan kapı 1.0 ile geçilir ama sessiz geçilmez.**
Alternatif, kapı ölçülemediğinde tüm motoru `MISSING` yapmaktı. Reddedildi:
`FX_DEBT_RATIO` bugün **her** hisse için MISSING, dolayısıyla o kural hiçbir
hissenin skorlanmamasıyla sonuçlanırdı — fail-closed değil, fail-useless.
Uzlaşma `notes`'ta taşınır ve ekranda görünür.

---

## Dosya Yapısı

| Dosya | Sorumluluk |
|---|---|
| `src/engines/__init__.py` | YENİ. Paket yüzeyi. |
| `src/engines/base.py` | YENİ. `EngineResult`, `Engine` protokolü, ortak eksen/kapı yardımcıları. |
| `src/engines/saf_deger.py` | YENİ. Tek eksenli değer motoru. |
| `src/engines/kalite_bilesik.py` | YENİ. Kalite + marj istikrarı motoru. |
| `src/board/__init__.py` | YENİ. |
| `src/board/comparison.py` | YENİ. N motoru sıralar, uzlaşma/ayrışma çıkarır. |
| `src/board/report.py` | YENİ. Terminal tablosu + CSV. |
| `tests/test_engine_base.py` | YENİ. |
| `tests/test_engines.py` | YENİ. |
| `tests/test_comparison.py` | YENİ. |
| `pytest.ini` | DEĞİŞTİR. `pythonpath`'e yeni paketler zaten `src` altında, değişiklik gerekmeyebilir — Görev 1'de doğrula. |

`src/engines/` ve `src/board/` ayrı paketlerdir: `ratio_engine` sıfır bağımlılık
özelliğini korur (K10), üst katmanlar gerekirse ileride pandas alabilir. Bu
fazda ikisi de saf stdlib kalır.

---

## Görev 1: `EngineResult` Sözleşmesi

**Dosyalar:**
- Oluştur: `src/engines/__init__.py`, `src/engines/base.py`
- Test: `tests/test_engine_base.py`

- [x] **Adım 1: Başarısız testi yaz**

```python
import pytest

from engines.base import EngineResult, EngineError


def test_ok_result_carries_a_finite_score():
    r = EngineResult(engine="saf_deger", ticker="AAA", score=0.82,
                     status="OK", axes={"value": 0.82}, gates={},
                     coverage=0.75, notes=())
    assert r.score == 0.82


def test_missing_result_carries_no_score():
    r = EngineResult(engine="saf_deger", ticker="AAA", score=None,
                     status="MISSING", axes={}, gates={},
                     coverage=0.10, notes=("coverage below threshold",))
    assert r.score is None


def test_ok_status_without_a_score_is_rejected():
    with pytest.raises(EngineError):
        EngineResult(engine="e", ticker="AAA", score=None, status="OK",
                     axes={}, gates={}, coverage=0.5, notes=())


def test_missing_status_with_a_score_is_rejected():
    with pytest.raises(EngineError):
        EngineResult(engine="e", ticker="AAA", score=0.5, status="MISSING",
                     axes={}, gates={}, coverage=0.5, notes=())


def test_gated_result_keeps_its_score_so_the_board_can_show_why():
    # A gate that multiplies to zero is a measured verdict, not a missing one.
    r = EngineResult(engine="e", ticker="AAA", score=0.0, status="GATED",
                     axes={"value": 0.9}, gates={"G_muhasebe": 0.0},
                     coverage=0.8, notes=("G_muhasebe vetoed",))
    assert r.status == "GATED"
    assert r.axes["value"] == 0.9


def test_coverage_outside_zero_one_is_rejected():
    with pytest.raises(EngineError):
        EngineResult(engine="e", ticker="AAA", score=0.5, status="OK",
                     axes={}, gates={}, coverage=1.4, notes=())
```

- [x] **Adım 2: Testi koş, başarısız olduğunu gör**

Çalıştır: `python -m pytest tests/test_engine_base.py -q`

Beklenen: FAIL — `ModuleNotFoundError: No module named 'engines'`

Burada `pythonpath` doğrulanır: `pytest.ini` `pythonpath = src .` diyor,
`src/engines/` de `src` altında olduğu için ek ayar gerekmemeli. Gerekiyorsa
`pytest.ini` bu adımda düzeltilir.

- [x] **Adım 3: Asgari uygulamayı yaz**

`src/engines/base.py`:

```python
from __future__ import annotations

"""What every engine returns, and the vocabulary they share.

An engine turns the composites of ``ratio_engine.scoring`` into one number per
ticker.  Engines differ in which axes they weigh and which gates they apply;
they do not differ in what they hand back, because the board ranks them side by
side and a ranking across inconsistent shapes is meaningless.

Three statuses, mirroring the ratio layer's distinction between unmeasured and
measured-and-bad:

    OK       scored.
    MISSING  not enough measured input to score at all.
    GATED    scored, and a gate vetoed it.  The score stays visible so the
             board can show what was vetoed rather than hiding the company.
"""

from dataclasses import dataclass
from typing import Mapping, Protocol, Sequence

STATUS_OK = "OK"
STATUS_MISSING = "MISSING"
STATUS_GATED = "GATED"

_STATUSES = (STATUS_OK, STATUS_MISSING, STATUS_GATED)


class EngineError(ValueError):
    pass


@dataclass(frozen=True)
class EngineResult:
    engine: str
    ticker: str
    score: float | None
    status: str
    axes: Mapping[str, float]
    gates: Mapping[str, float]
    coverage: float
    notes: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.status not in _STATUSES:
            raise EngineError(f"{self.ticker}: bilinmeyen status {self.status!r}")
        if self.status == STATUS_MISSING:
            if self.score is not None:
                raise EngineError(
                    f"{self.ticker}: status MISSING ise score None olmali"
                )
        elif self.score is None:
            raise EngineError(
                f"{self.ticker}: status {self.status} ise score sonlu olmali"
            )
        if not 0.0 <= float(self.coverage) <= 1.0:
            raise EngineError(f"{self.ticker}: coverage 0..1 disinda")
```

`Engine` protokolü aynı dosyada:

```python
class Engine(Protocol):
    name: str

    def run(self, universe: Mapping[str, "TickerResult"]) -> dict[str, EngineResult]:
        ...
```

`TickerResult` için `TYPE_CHECKING` altında
`from ratio_engine.scoring import TickerResult` kullan.

- [x] **Adım 4: Testi koş, geçtiğini gör**

Çalıştır: `python -m pytest tests/test_engine_base.py -q`

Beklenen: 6 passed

- [x] **Adım 5: Commit**

```bash
git add src/engines tests/test_engine_base.py
git commit -m "feat(engines): define the EngineResult contract"
```

---

## Görev 2: Eksen ve Kapı Yardımcıları

**Dosyalar:**
- Değiştir: `src/engines/base.py`
- Test: `tests/test_engine_base.py`

K15'i koda çeviren yer burası: kapılar **çarpılır**, toplanmaz.

- [x] **Adım 1: Başarısız testi yaz**

```python
from engines.base import apply_gates


def test_gates_multiply_rather_than_add():
    score, applied, status = apply_gates(0.80, {"a": 0.5, "b": 0.5})
    assert score == pytest.approx(0.20)
    assert status == "OK"


def test_a_zero_gate_marks_the_result_gated():
    score, applied, status = apply_gates(0.90, {"G_muhasebe": 0.0})
    assert score == pytest.approx(0.0)
    assert status == "GATED"


def test_no_gates_leaves_the_score_untouched():
    score, applied, status = apply_gates(0.65, {})
    assert score == pytest.approx(0.65)
    assert applied == {}
    assert status == "OK"


def test_a_cheap_value_cannot_buy_its_way_past_a_veto():
    # K15: the value-trap guard.  A vetoed company does not get compensated
    # for being cheap, which addition would have allowed.
    cheap_and_vetoed, _, _ = apply_gates(1.00, {"G_muhasebe": 0.0})
    dear_and_clean, _, _ = apply_gates(0.40, {"G_muhasebe": 1.0})
    assert cheap_and_vetoed < dear_and_clean
```

- [x] **Adım 2: Testi koş, başarısız olduğunu gör**

Çalıştır: `python -m pytest tests/test_engine_base.py -q -k gate`

Beklenen: FAIL — `ImportError: cannot import name 'apply_gates'`

- [x] **Adım 3: Asgari uygulamayı yaz**

```python
GATED_BELOW = 1e-9


def apply_gates(
    score: float, gates: Mapping[str, float]
) -> tuple[float, dict[str, float], str]:
    """Multiply the axis score by every gate (K15).

    Gates multiply because a company that is cheap and about to default should
    not be compensated for the first by the second.  Addition allows exactly
    that, and it is how value traps get to the top of a list.
    """
    applied = {name: float(g) for name, g in gates.items()}
    out = float(score)
    for g in applied.values():
        out *= g
    status = STATUS_GATED if out <= GATED_BELOW and applied else STATUS_OK
    return out, applied, status
```

Eksen ağırlıklandırıcı:

```python
def weigh_axes(axes: Mapping[str, float], weights: Mapping[str, float]) -> float:
    """Weighted sum of axis scores.  Weights must cover exactly the axes given.

    No renormalisation over whatever happens to be present: an engine whose
    axis is unavailable must say so, not quietly redistribute that axis's
    weight onto the others.
    """
    missing = set(weights) ^ set(axes)
    if missing:
        raise EngineError(f"eksen/agirlik uyusmuyor: {sorted(missing)}")
    return sum(axes[k] * weights[k] for k in weights)
```

- [x] **Adım 4: Testi koş, geçtiğini gör**

Çalıştır: `python -m pytest tests/test_engine_base.py -q`

Beklenen: 10 passed

- [x] **Adım 5: Commit**

```bash
git add src/engines/base.py tests/test_engine_base.py
git commit -m "feat(engines): multiply gates, refuse to renormalise axes"
```

---

## Görev 3: Saf Değer Motoru

**Dosyalar:**
- Oluştur: `src/engines/saf_deger.py`
- Test: `tests/test_engines.py`

Tek eksen: `value` kompoziti. Kapı: `G_muhasebe`. Ucuzluğun muhasebe kalitesiyle
kesişmesi bu motorun tüm tezi — ucuz ama tahakkuku şişkin şirket değer tuzağıdır.

- [x] **Adım 1: Fikstürü yaz**

`tests/_fixtures.py` sonuna: `TickerResult`/`CompositeResult` üreten
`universe_of(...)` yardımcısı. Gerçek `score_universe` çıktısının şeklini
taklit etmeli — `composites` sözlüğü `quality`/`growth`/`value` anahtarlarını,
`ratio_scores` ise rasyo adı → skor eşlemesini taşır.

- [x] **Adım 2: Başarısız testi yaz**

```python
def test_cheapest_company_scores_highest():
    ...

def test_a_company_without_a_value_composite_is_missing_not_zero():
    ...

def test_bad_accruals_gate_the_result():
    ...

def test_an_unmeasurable_accruals_ratio_passes_the_gate_but_is_noted():
    # K22: the gate cannot be applied, so it is 1.0 - and `notes` says so.
    ...
```

- [x] **Adım 3: Testi koş, başarısız olduğunu gör**

- [x] **Adım 4: Motoru yaz**

Eşik kararı — **K23:** `ACCRUALS_TO_ASSETS` skoru `0.20`'nin altındaysa
`G_muhasebe = 0.0`, üstündeyse `1.0`. Sert kapı, yumuşak geçiş yok.
Doğrulanmamış sabit; DEVIR.md bölüm 7 listesine aynı statüde eklenir.
**Reddedilen:** kapıyı sürekli bir çarpana (ör. skorun kendisi) çevirmek — o
zaman kapı olmaktan çıkıp beşinci bir eksen olurdu ve K13'ün çift sayma
itirazı burada da geçerlidir.

- [x] **Adım 5: Testi koş, geçtiğini gör**

- [x] **Adım 6: Commit**

---

## Görev 4: Kalite Bileşik Motoru

**Dosyalar:**
- Oluştur: `src/engines/kalite_bilesik.py`
- Test: `tests/test_engines.py`

İki eksen: `quality` kompoziti (0.70) ve **marj istikrarı** (0.30) — Faz 1'in
`compute_trend`'i buraya bağlanır. K8'in "istikrar bir rasyo değil, skorlama
katmanının türettiği üçlünün üçüncü bileşenidir" kararının ilk gerçek tüketicisi
budur.

- [x] **Adım 1: Başarısız testi yaz**

```python
def test_steady_margins_beat_erratic_ones_at_equal_level():
    # Two companies with identical quality composites; the one whose CFO_MARGIN
    # trend has the smaller residual MAD must rank higher.
    ...

def test_a_company_without_enough_quarters_loses_only_the_stability_axis():
    # K24 below: too few quarters is MISSING for the axis, and the engine then
    # returns MISSING rather than scoring on quality alone.
    ...
```

- [x] **Adım 2–3: Koş, motoru yaz**

**K24 — Eksen ölçülemiyorsa motor `MISSING` döner, kalan eksene kaçmaz.**
`weigh_axes` zaten eksen/ağırlık uyuşmazlığında hata veriyor; motor bunu
yakalayıp `MISSING` üretir. **Reddedilen:** istikrar ölçülemediğinde ağırlığı
kaliteye devretmek. O zaman iki farklı şirket farklı tanımlı skorlarla yan yana
sıralanır ve sıralamanın anlamı kaybolur (K14 sıralamaya dayanıyor).

**K25 — İstikrar ekseni hangi rasyodan okunur: `CFO_MARGIN`.**
Marj ailesinden, nakit temelli olduğu için tahakkuk oyunlarına en az açık olanı.
Doğrulanmamış seçim. **Reddedilen:** tüm PROFIT rasyolarının istikrarını
ortalamak — aralarında yüksek korelasyon var, ortalamanın taşıdığı ek bilgi az.

- [x] **Adım 4–5: Testi geçir, commit**

---

## Görev 5: Karşılaştırma — Sıralama

**Dosyalar:**
- Oluştur: `src/board/__init__.py`, `src/board/comparison.py`
- Test: `tests/test_comparison.py`

- [x] **Adım 1: Başarısız testi yaz**

```python
def test_each_engine_ranks_independently():
    ...

def test_missing_results_are_unranked_not_ranked_last():
    # A company nobody could measure is not the worst company.
    ...

def test_gated_results_are_ranked_last_among_the_scored():
    # A measured veto IS a verdict, so it ranks - at the bottom.
    ...

def test_ties_break_deterministically_by_ticker():
    ...
```

**K26 — `MISSING` sıralanmaz, `GATED` en sona sıralanır.**
Ölçülememiş şirket "en kötü" değildir; ölçülüp veto yemiş şirket kötüdür. v1'in
hatası ikisini aynı kovaya atmaktı ve bu projenin kuruluş gerekçesi tam olarak
bu ayrımdı.

- [x] **Adım 2–5: Koş, yaz, geçir, commit**

---

## Görev 6: Karşılaştırma — Uzlaşma ve Ayrışma

**Dosyalar:**
- Değiştir: `src/board/comparison.py`
- Test: `tests/test_comparison.py`

Kullanıcının asıl istediği iki liste.

- [x] **Adım 1: Başarısız testi yaz**

```python
def test_consensus_lists_names_every_engine_ranks_highly():
    ...

def test_divergence_lists_names_the_engines_disagree_about():
    ...

def test_a_name_only_one_engine_could_score_is_in_neither_list():
    # Agreement needs at least two opinions; one opinion is not consensus.
    ...

def test_divergence_is_measured_on_rank_not_score():
    # K14: scores are not comparable across engines, ranks are.
    ...
```

**K27 — Uzlaşma ve ayrışma sıra üzerinden ölçülür, skor üzerinden değil.**
İki motorun skorları farklı tanımlı; 0.80 ile 0.80 aynı şeyi söylemiyor.
Sıralar aynı evrende tanımlı. **Reddedilen:** skor farkı eşiği.

**K28 — Uzlaşma en az iki motor gerektirir.** Tek motorun skorlayabildiği
şirket ne uzlaşmadır ne ayrışma; ayrı bir "tek görüş" kovasına düşer.

- [x] **Adım 2–5: Koş, yaz, geçir, commit**

---

## Görev 7: Rapor Yüzeyi

**Dosyalar:**
- Oluştur: `src/board/report.py`
- Test: `tests/test_comparison.py`

Terminal tablosu ve CSV. Tek satır = tek hisse; motor sıraları + ham oranlar
(F/K, PD/DD, EV/FAVÖK, net borç/FAVÖK, temettü) yan yana.

- [x] **Adım 1: Başarısız testi yaz**

```python
def test_report_row_carries_ranks_and_raw_ratios_side_by_side():
    ...

def test_unapplied_gates_are_visible_in_the_output():
    # K22: the screen must be able to say "scored without an FX risk check".
    ...

def test_csv_and_terminal_render_the_same_rows():
    ...
```

- [x] **Adım 2–5: Koş, yaz, geçir, commit**

---

## Görev 8: Uçtan Uca Duman Testi ve Mutasyon Kontrolü

**Dosyalar:**
- Test: `tests/test_comparison.py`

- [x] **Adım 1: Uçtan uca test yaz**

Sentetik bir evreni `load_ratio_set` → `compute_ratios_for_ticker` →
`score_universe` → iki motor → `comparison` → `report` zincirinden geçir ve
sonunda gerçek bir tablo çıktığını doğrula. Bu, sözleşmelerin birbirine
gerçekten oturduğunun tek kanıtıdır.

- [x] **Adım 2: Beş mutasyonu koş**

| # | Mutasyon | Kırmalı |
|---|---|---|
| 1 | Kapılar çarpılacağına toplanıyor | `test_a_cheap_value_cannot_buy_its_way_past_a_veto` |
| 2 | `MISSING` sonuçlar en sona sıralanıyor | `test_missing_results_are_unranked_not_ranked_last` |
| 3 | Ayrışma skor farkından ölçülüyor | `test_divergence_is_measured_on_rank_not_score` |
| 4 | Eksik eksenin ağırlığı kalana dağıtılıyor | `test_a_company_without_enough_quarters_loses_only_the_stability_axis` |
| 5 | Uygulanamayan kapı sessizce 1.0 geçiyor (`notes` yazılmıyor) | `test_unapplied_gates_are_visible_in_the_output` |

Her biri: uygula → `pytest -q` → FAIL gör → `git checkout --` ile geri al.
**Kaçan mutasyon varsa kod değil test eksiktir** — Faz 1'de M3 tam olarak bunu
gösterdi.

- [x] **Adım 3: Faz sonu commit**

---

## Bitiş Ölçütü

1. `python -m pytest -q` → tamamı geçiyor, 0 failed.
2. Beş mutasyonun beşi de en az bir testi kırıyor.
3. Uçtan uca duman testi sentetik evrenden gerçek bir karşılaştırma tablosu
   üretiyor.
4. `import ratio_engine` hâlâ üçüncü parti hiçbir modül çekmiyor.

## Faz 2'nin Bilerek Yapmadıkları

- **Total Rasyo v2 ve Momentum/Revizyon motorları.** Fiyat geçmişi yok; bkz.
  Kapsam Kararı.
- **`G_likidite` ve `G_risk`.** Girdileri gelmiyor; K22 uyarınca 1.0 geçilir ve
  `notes`'ta görünür.
- **Ağırlıkların doğrulanması.** K23/K25 ve eksen ağırlıkları iddiadır. IC
  ölçümü ve walk-forward Faz 4'ün işi; DEVIR.md bölüm 8 madde 8 bunu "projenin
  en eksik parçası" diye işaretliyor ve öyle kalıyor.
- **Gerçek BIST verisi.** Bu repoda veri yok; motorlar ve ekran kendilerine
  verilen satırlarla çalışır. İki repoyu buluşturmak ayrı bir karar.


---

## Uygulama Notu (2026-09-23, tamamlandı)

Faz 2 koşuldu. **105 test geçiyor**, beş mutasyonun beşi de en az bir testi
kırdı, uçtan uca zincir testi (`test_the_whole_chain_produces_a_board`) spec →
calc → scoring → iki motor → tahta yolunu bir arada doğruluyor.

Tahta gerçek BIST verisiyle çalıştırıldı (`research/board_run.py`, mali yıl
2025-12-31, skor tarihi 2026-03-16, 89 hisse):

- **Uzlaşma:** PGSUS (iki motorda da 1. sıra), MGROS.
- **Ayrışma:** ASELS 74 sıra farkı, SAYAS 66, ECILC 61.
- İstikrar ekseni 89 hissenin 74'ünde okunabildi; kalanı `MISSING`, çünkü
  K24 uyarınca eksik eksenin ağırlığı kaliteye devredilmiyor.
- `G_muhasebe` çoğu hissede uygulanamadı (`ACCRUALS_TO_ASSETS` ölçülemiyor) ve
  bu K22 uyarınca tablonun UYARILAR bölümünde görünüyor.

Plandan iki sapma:

1. **İstikrar ekseni geçici olarak sürücüde skorlanıyor.** `board_run.py`
   içindeki `stability_scores()` artık MAD'larını düz sıra tersine çeviriyor.
   Üçlüyü `score_universe`'e düzgün bağlamak — yani medyan/MAD makinesinden
   geçirmek — Faz 3'e kaldı; sözleşme hazır, kablolama değil.
2. **Mali yıl seçimi.** İlk koşuda tahta tek hisseye düştü: MAVI'nin hesap
   dönemi 31 Ocak'ta bitiyor ve `max()` onu seçiyordu. Sürücü artık en yaygın
   yıl sonunu seçiyor.

**Sıradaki (Faz 3):** Total Rasyo v2 ve Momentum/Revizyon motorları,
`G_likidite` ve `G_risk` kapıları, üçlünün skorlamaya kablolanması. Üçü de
fiyat/hacim ingest'ine bağlı ve o iş bu repoda yapılamaz.

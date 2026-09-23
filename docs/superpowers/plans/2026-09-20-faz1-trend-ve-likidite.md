# Faz 1 — Trend ve Likidite Primitifleri: Uygulama Planı

> **Ajan çalışanlar için:** GEREKLİ ALT SKILL: Bu planı görev görev uygulamak
> için superpowers:subagent-driven-development (önerilen) veya
> superpowers:executing-plans kullan. Adımlar takip için checkbox (`- [ ]`)
> sözdizimi kullanır.

**Hedef:** `ratio_engine`'e iki saf-stdlib primitif eklemek — 8 çeyrek üzerinden
`(seviye, eğim, istikrar)` üçlüsü ve 60 günlük ortalama TL hacim — böylece
Faz 2'deki dört motorun ve `G_likidite` kapısının girdileri hazır olsun.

**Mimari:** Her iki modül de **ham istatistik döndürür, normalize etmez**.
Karşılaştırılabilirliği mevcut skorlama katmanı üretir (winsorize + medyan/MAD
+ yönelim, bkz. K7). Böylece bu fazda tek bir uydurulmuş ölçek sabiti doğmaz.
Her iki modül de mevcut beş-sonuç sözleşmesine uyar: veri yetersizse `MISSING`
döner, asla sessiz `0.0` ya da `NaN`.

**Teknoloji:** Python 3.10+, yalnız standart kütüphane, pytest.
`pytest.ini` → `pythonpath = src .`

---

## Kapsam Kararı — Bu Plan Neden Yol Haritasının 1. Maddesiyle Başlamıyor

DEVIR.md bölüm 8 sırayı "1. Hacim ingest, 2. Üçlü, 3. Motorlar" diye veriyor.
Bu plan 1. maddeyi **ikiye bölüyor** ve sırayı değiştiriyor. Gerekçe:

1. maddenin kendisi bu repoda **yapılamaz**. `adv_60d_try` üretimi
`core.prices_daily.volume` kolonuna ve yfinance ingest'ine bağlı; ikisi de ana
projenin altyapısı. Bu repo sıfır üçüncü-parti bağımlılıkla duruyor (K10) ve
yfinance'ı buraya sokmak o özelliği bitirir.

Bölünme:
- **Saf hesap** (`close × volume` serisinden 60g ortalama) → burada, Görev 5.
- **Ingest** (yfinance → DB kolonu) → ana projede, bu planın dışında.

Sıra bu yüzden: üçlü önce (Faz 2'deki kalite motorunu doğrudan açar, hiçbir dış
veri istemez), likidite hesabı sonra (ingest gelene kadar çağıranı yok ama
sözleşmesi hazır olur).

**Bu plan Faz 1'dir.** Faz 2 (motor sözleşmesi + dört motor) ve Faz 3
(karşılaştırma yüzeyi) kendi planlarını alacak; her fazın sonunda çalışan,
test edilmiş yazılım vardır.

---

## Dosya Yapısı

| Dosya | Sorumluluk |
|---|---|
| `src/ratio_engine/trend.py` | YENİ. Bir tickerın bir rasyosu için çeyrek serisinden `(seviye, eğim, istikrar)` üçlüsü ve durum. |
| `src/ratio_engine/liquidity.py` | YENİ. Günlük fiyat/hacim satırlarından `adv_try` ve durum. |
| `src/ratio_engine/__init__.py` | DEĞİŞTİR. İki yeni modülün genel adlarını dışa aç. |
| `tests/test_trend.py` | YENİ. |
| `tests/test_liquidity.py` | YENİ. |
| `tests/_fixtures.py` | DEĞİŞTİR. Çeyrek serisi fikstürü ekle. |
| `README.md` | DEĞİŞTİR. Modül listesine iki satır. |

`trend.py` çeyrek aritmetiğini yeniden yazmaz; `evaluator._quarter_end`
fonksiyonunu kullanır.

---

## Yeni Kararlar (K18–K21)

Bu fazda verilen kararlar. Hepsi DEVIR.md bölüm 7'deki "doğrulanmamış sabitler"
listesiyle **aynı statüde**: makul seçim, BIST verisiyle kalibre edilmedi.
Faz 4'teki IC ölçümüne kadar iddia olarak kalırlar.

### K18 — Eğim ham birimde, normalize edilmez

Eğim, çeyrek başına rasyo birimi olarak döner (ör. ROE için "çeyrek başına
0.004 ROE"). Medyan seviyeye bölerek ölçeksizleştirmek denenmeyecek.

**Reddedilen:** `eğim / |medyan seviye|`. Medyan sıfıra yaklaştığında patlar ve
tam da marjı sıfır civarında gezinen şirketlerde — yani trendin en çok önem
taşıdığı yerde — sonsuza gider. Kesitsel karşılaştırılabilirliği zaten
`scoring._winsorize` + medyan/MAD üretiyor; iki kez normalize etmek gereksiz.

### K19 — İstikrar, artık MAD'ı olarak raporlanır (LOWER_BETTER)

İstikrar bileşeni, doğruya uydurulmuş regresyondan artıkların MAD'ı olarak
**ham birimde** döner. `0..1` arası bir "istikrar skoru"na çevrilmez.

**Reddedilen:** `1 / (1 + artık_mad / |medyan|)` gibi sınırlayıcı dönüşümler.
Hepsi uydurulmuş bir ölçek sabiti gerektirir ve DEVIR.md'nin "uydurulmuş çapa
çapasızlıktan kötüdür" (K6) ilkesine aykırıdır. Yön bilgisi skorlama
katmanının işi: düşük artık MAD'ı iyidir, yani `LOWER_BETTER`.

### K20 — 8 çeyreklik pencere, en az 6 gözlem

Pencere `window=8` çeyrek. En az `min_quarters=6` çeyrekte `OK` değer yoksa
üçlü `MISSING` döner. Eksik çeyrek regresyonda **boşluk bırakır** (x ekseni
çeyrek indeksi, sıra numarası değil) — böylece bir çeyrek atlanınca eğim
yanlış dikleşmez.

**Reddedilen:** Eksik çeyreği interpolasyonla doldurmak. Ölçülmemiş veriyi
ölçülmüş gibi gösterir; motorun tüm varlık sebebine aykırı.

### K21 — `OK` olmayan statüler üçlüye girmez

Üçlü yalnız `OK` gözlemlerden kurulur. `BEST`/`WORST` sayısal değer taşımadığı
için (değerleri `None`) regresyona giremez; `NOT_APPLICABLE` zaten paydadan
çıkmıştır. Bir çeyrek `BEST` ise, o çeyrek trend için **yok** sayılır ve
`min_quarters` eşiğine sayılmaz.

**Reddedilen:** `BEST`'i pencerenin maksimumu, `WORST`'ü minimumu ile
doldurmak. Uydurma sayı üretir.

---

## Görev 1: Üçlü Veri Yapısı ve Durum Sözleşmesi

**Dosyalar:**
- Oluştur: `src/ratio_engine/trend.py`
- Test: `tests/test_trend.py`

- [ ] **Adım 1: Başarısız testi yaz**

`tests/test_trend.py`:

```python
import pytest

from ratio_engine.trend import TrendTriple, TrendError


def test_ok_triple_carries_three_finite_numbers():
    t = TrendTriple(
        ratio_name="ROE", level=0.20, slope=0.004, stability=0.01,
        status="OK", quarters_used=8,
    )
    assert t.level == 0.20
    assert t.slope == 0.004
    assert t.stability == 0.01


def test_missing_triple_carries_no_numbers():
    t = TrendTriple(
        ratio_name="ROE", level=None, slope=None, stability=None,
        status="MISSING", quarters_used=3,
    )
    assert t.level is None


def test_ok_status_with_null_component_is_rejected():
    with pytest.raises(TrendError):
        TrendTriple(
            ratio_name="ROE", level=0.20, slope=None, stability=0.01,
            status="OK", quarters_used=8,
        )


def test_missing_status_with_a_number_is_rejected():
    with pytest.raises(TrendError):
        TrendTriple(
            ratio_name="ROE", level=0.20, slope=0.004, stability=0.01,
            status="MISSING", quarters_used=3,
        )
```

- [ ] **Adım 2: Testi koş, başarısız olduğunu gör**

Çalıştır: `python -m pytest tests/test_trend.py -v`

Beklenen: FAIL — `ModuleNotFoundError: No module named 'ratio_engine.trend'`

- [ ] **Adım 3: Asgari uygulamayı yaz**

`src/ratio_engine/trend.py`:

```python
from __future__ import annotations

"""(level, slope, stability) over a trailing window of quarters.

K8 settled that stability is not a ratio: it is the third component of a
triple the scoring layer derives across quarters.  This module derives all
three and reports them in raw units, because the cross-sectional machinery in
``ratio_engine.scoring`` already winsorises and rescales by median/MAD.  A
second normalisation here would only add a constant nobody has measured.

The five-outcome contract of ``calc`` applies unchanged: too few quarters
means ``MISSING``, never a silent 0.0.
"""

from dataclasses import dataclass

from ratio_engine.evaluator import _is_finite

STATUS_OK = "OK"
STATUS_MISSING = "MISSING"

DEFAULT_WINDOW = 8
DEFAULT_MIN_QUARTERS = 6


class TrendError(ValueError):
    pass


@dataclass(frozen=True)
class TrendTriple:
    ratio_name: str
    level: float | None
    slope: float | None
    stability: float | None
    status: str
    quarters_used: int

    def __post_init__(self) -> None:
        components = (self.level, self.slope, self.stability)
        if self.status == STATUS_OK:
            if not all(_is_finite(c) for c in components):
                raise TrendError(
                    f"{self.ratio_name}: status OK ise uc bilesen de sonlu olmali"
                )
        elif any(c is not None for c in components):
            raise TrendError(
                f"{self.ratio_name}: status {self.status} ise bilesenler None olmali"
            )
```

- [ ] **Adım 4: Testi koş, geçtiğini gör**

Çalıştır: `python -m pytest tests/test_trend.py -v`

Beklenen: 4 passed

- [ ] **Adım 5: Commit**

```bash
git add src/ratio_engine/trend.py tests/test_trend.py
git commit -m "feat(trend): add TrendTriple with fail-closed status contract"
```

---

## Görev 2: Eğim — Çeyrek İndeksi Üzerinde En Küçük Kareler

**Dosyalar:**
- Değiştir: `src/ratio_engine/trend.py`
- Test: `tests/test_trend.py`

- [ ] **Adım 1: Başarısız testi yaz**

`tests/test_trend.py` sonuna ekle:

```python
from ratio_engine.trend import _ols_slope


def test_slope_of_a_perfect_line_is_its_gradient():
    points = [(0, 1.0), (1, 1.5), (2, 2.0), (3, 2.5)]
    assert _ols_slope(points) == pytest.approx(0.5)


def test_slope_of_a_flat_series_is_zero():
    points = [(0, 2.0), (1, 2.0), (2, 2.0), (3, 2.0)]
    assert _ols_slope(points) == pytest.approx(0.0)


def test_gap_in_quarters_does_not_steepen_the_slope():
    # Q0=1.0, Q1=1.5, Q2 missing, Q3=2.5.  Index-aware fitting must read this
    # as the same 0.5/quarter line, not 0.75 across three consecutive points.
    points = [(0, 1.0), (1, 1.5), (3, 2.5)]
    assert _ols_slope(points) == pytest.approx(0.5)


def test_slope_needs_two_distinct_x_values():
    assert _ols_slope([(2, 1.0)]) is None
    assert _ols_slope([(2, 1.0), (2, 3.0)]) is None
```

- [ ] **Adım 2: Testi koş, başarısız olduğunu gör**

Çalıştır: `python -m pytest tests/test_trend.py -v -k slope`

Beklenen: FAIL — `ImportError: cannot import name '_ols_slope'`

- [ ] **Adım 3: Asgari uygulamayı yaz**

Dosya başındaki importa ekle: `from typing import Sequence`

```python
def _ols_slope(points: Sequence[tuple[int, float]]) -> float | None:
    """Least-squares gradient of value against quarter index.

    The x axis is the absolute quarter index, not the position in the list, so
    a missing quarter leaves a real gap (K20) and does not tilt the fit.
    """
    n = len(points)
    if n < 2:
        return None
    mean_x = sum(p[0] for p in points) / n
    mean_y = sum(p[1] for p in points) / n
    sxx = sum((p[0] - mean_x) ** 2 for p in points)
    if sxx <= 0.0:
        return None
    sxy = sum((p[0] - mean_x) * (p[1] - mean_y) for p in points)
    slope = sxy / sxx
    return slope if _is_finite(slope) else None
```

- [ ] **Adım 4: Testi koş, geçtiğini gör**

Çalıştır: `python -m pytest tests/test_trend.py -v`

Beklenen: 8 passed

- [ ] **Adım 5: Commit**

```bash
git add src/ratio_engine/trend.py tests/test_trend.py
git commit -m "feat(trend): fit slope on absolute quarter index"
```

---

## Görev 3: İstikrar — Artıkların MAD'ı

**Dosyalar:**
- Değiştir: `src/ratio_engine/trend.py`
- Test: `tests/test_trend.py`

- [ ] **Adım 1: Başarısız testi yaz**

```python
from ratio_engine.trend import _residual_mad


def test_perfect_line_has_zero_residual_spread():
    points = [(0, 1.0), (1, 1.5), (2, 2.0), (3, 2.5)]
    assert _residual_mad(points, slope=0.5) == pytest.approx(0.0)


def test_noisy_series_has_larger_spread_than_clean_one():
    clean = [(0, 1.0), (1, 1.1), (2, 1.2), (3, 1.3)]
    noisy = [(0, 1.0), (1, 2.0), (2, 0.5), (3, 1.3)]
    assert _residual_mad(noisy, slope=0.1) > _residual_mad(clean, slope=0.1)


def test_residual_spread_is_never_negative():
    points = [(0, -5.0), (1, 3.0), (2, -2.0)]
    assert _residual_mad(points, slope=0.0) >= 0.0
```

- [ ] **Adım 2: Testi koş, başarısız olduğunu gör**

Çalıştır: `python -m pytest tests/test_trend.py -v -k residual`

Beklenen: FAIL — `ImportError: cannot import name '_residual_mad'`

- [ ] **Adım 3: Asgari uygulamayı yaz**

```python
def _median(values: Sequence[float]) -> float:
    ordered = sorted(values)
    n = len(ordered)
    mid = n // 2
    if n % 2 == 1:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2.0


def _residual_mad(points: Sequence[tuple[int, float]], slope: float) -> float:
    """Median absolute deviation of the residuals around the fitted line.

    Median/MAD rather than RMSE, for the same reason scoring uses them (K7):
    one restated quarter should not decide whether a company looks stable.
    Returned in raw ratio units and oriented LOWER_BETTER by the caller (K19).
    """
    n = len(points)
    mean_x = sum(p[0] for p in points) / n
    mean_y = sum(p[1] for p in points) / n
    intercept = mean_y - slope * mean_x
    residuals = [p[1] - (slope * p[0] + intercept) for p in points]
    centre = _median(residuals)
    return _median([abs(r - centre) for r in residuals])
```

**Not:** Gövde `scoring._median` ile aynı. DRY için `scoring`'den import
**etme** — `trend`'in `scoring`'e bağlanması katman yönünü ters çevirir
(`scoring` zaten `spec`'e bakıyor, `trend` ondan bağımsız kalmalı). Ortak bir
`_stats.py`'ye taşıma ayrı bir iş; bu plan onu kapsam dışı bırakıyor.

- [ ] **Adım 4: Testi koş, geçtiğini gör**

Çalıştır: `python -m pytest tests/test_trend.py -v`

Beklenen: 11 passed

- [ ] **Adım 5: Commit**

```bash
git add src/ratio_engine/trend.py tests/test_trend.py
git commit -m "feat(trend): measure stability as residual MAD"
```

---

## Görev 4: `compute_trend` — Üçlüyü Kur, Eksik Veride Kapan

**Dosyalar:**
- Değiştir: `src/ratio_engine/trend.py`
- Değiştir: `tests/_fixtures.py`
- Test: `tests/test_trend.py`

- [ ] **Adım 1: Fikstürü yaz**

`tests/_fixtures.py` sonuna ekle (gerekli importları dosya başına al:
`from datetime import date, timedelta` ve
`from ratio_engine.calc import RatioOutcome`):

```python
def _quarter_end_from_index(q_index):
    year, quarter = divmod(q_index, 4)
    month = quarter * 3 + 3
    if month == 12:
        return date(year, 12, 31)
    return date(year, month + 1, 1) - timedelta(days=1)


def rising_roe_outcomes(ticker="AAA", n=8, start=0.10, step=0.01):
    """n quarters of ROE rising by `step` each quarter, ending 2025-12-31."""
    end_index = 2025 * 4 + 3
    outcomes = []
    for i in range(n):
        outcomes.append(RatioOutcome(
            ticker=ticker,
            period_end=_quarter_end_from_index(end_index - (n - 1 - i)),
            version_tag="ORIGINAL",
            ratio_name="ROE",
            value=start + i * step,
            status="OK",
        ))
    return outcomes
```

- [ ] **Adım 2: Başarısız testi yaz**

```python
from datetime import date

from ratio_engine.calc import RatioOutcome
from ratio_engine.trend import compute_trend
from tests._fixtures import rising_roe_outcomes


def test_rising_series_yields_positive_slope_and_latest_level():
    t = compute_trend(rising_roe_outcomes(), "ROE", date(2025, 12, 31))
    assert t.status == "OK"
    assert t.quarters_used == 8
    assert t.slope == pytest.approx(0.01)
    assert t.level == pytest.approx(0.17)
    assert t.stability == pytest.approx(0.0)


def test_too_few_quarters_is_missing_not_zero():
    t = compute_trend(rising_roe_outcomes(n=5), "ROE", date(2025, 12, 31))
    assert t.status == "MISSING"
    assert t.slope is None
    assert t.quarters_used == 5


def test_non_ok_quarters_do_not_count_toward_the_minimum():
    outcomes = rising_roe_outcomes()
    # Blank three quarters out as BEST: they carry no number, so they are not
    # observations (K21), leaving five - one short of the minimum.
    blanked = [
        RatioOutcome(ticker=o.ticker, period_end=o.period_end,
                     version_tag=o.version_tag, ratio_name=o.ratio_name,
                     value=None, status="BEST")
        for o in outcomes[:3]
    ]
    t = compute_trend(blanked + outcomes[3:], "ROE", date(2025, 12, 31))
    assert t.status == "MISSING"
    assert t.quarters_used == 5


def test_quarters_outside_the_window_are_ignored():
    t = compute_trend(rising_roe_outcomes(n=12), "ROE", date(2025, 12, 31))
    assert t.quarters_used == 8


def test_a_window_without_the_end_quarter_has_no_level():
    outcomes = rising_roe_outcomes(n=9)[:-1]  # ends one quarter short
    t = compute_trend(outcomes, "ROE", date(2025, 12, 31))
    assert t.status == "MISSING"


def test_unknown_ratio_is_missing():
    t = compute_trend(rising_roe_outcomes(), "NO_SUCH_RATIO", date(2025, 12, 31))
    assert t.status == "MISSING"
    assert t.quarters_used == 0
```

- [ ] **Adım 3: Testi koş, başarısız olduğunu gör**

Çalıştır: `python -m pytest tests/test_trend.py -v -k "compute or window or quarter"`

Beklenen: FAIL — `ImportError: cannot import name 'compute_trend'`

- [ ] **Adım 4: Asgari uygulamayı yaz**

Importları tamamla:

```python
from datetime import date
from typing import Iterable, Sequence, TYPE_CHECKING

from ratio_engine.evaluator import _is_finite, _quarter_end

if TYPE_CHECKING:
    from ratio_engine.calc import RatioOutcome
```

```python
def _quarter_index(value: date) -> int:
    anchor = _quarter_end(value)
    return anchor.year * 4 + ((anchor.month - 1) // 3)


def compute_trend(
    outcomes: Iterable["RatioOutcome"],
    ratio_name: str,
    period_end: date,
    *,
    window: int = DEFAULT_WINDOW,
    min_quarters: int = DEFAULT_MIN_QUARTERS,
) -> TrendTriple:
    """Derive (level, slope, stability) for one ratio of one ticker.

    ``level`` is the value at ``period_end`` itself, not the window mean: the
    triple says "where it is, where it is heading, how steadily", and the
    first of those is a point reading.
    """
    end_index = _quarter_index(period_end)
    first_index = end_index - (window - 1)

    points: list[tuple[int, float]] = []
    for o in outcomes:
        if o.ratio_name != ratio_name or o.status != STATUS_OK:
            continue
        if not _is_finite(o.value):
            continue
        idx = _quarter_index(o.period_end)
        if first_index <= idx <= end_index:
            points.append((idx, float(o.value)))

    points.sort()
    used = len(points)

    if used < min_quarters:
        return TrendTriple(ratio_name, None, None, None, STATUS_MISSING, used)

    level = next((v for idx, v in reversed(points) if idx == end_index), None)
    if level is None:
        return TrendTriple(ratio_name, None, None, None, STATUS_MISSING, used)

    slope = _ols_slope(points)
    if slope is None:
        return TrendTriple(ratio_name, None, None, None, STATUS_MISSING, used)

    stability = _residual_mad(points, slope)
    if not _is_finite(stability):
        return TrendTriple(ratio_name, None, None, None, STATUS_MISSING, used)

    return TrendTriple(ratio_name, level, slope, stability, STATUS_OK, used)
```

- [ ] **Adım 5: Tüm testleri koş**

Çalıştır: `python -m pytest -q`

Beklenen: 56 passed (39 mevcut + 17 yeni)

- [ ] **Adım 6: Commit**

```bash
git add src/ratio_engine/trend.py tests/test_trend.py tests/_fixtures.py
git commit -m "feat(trend): assemble the triple, fail closed under the window minimum"
```

---

## Görev 5: `liquidity.py` — Ortalama Günlük TL İşlem Hacmi

**Dosyalar:**
- Oluştur: `src/ratio_engine/liquidity.py`
- Test: `tests/test_liquidity.py`

K13 uyarısı planın içine yazılıyor: bu **işlem** likiditesidir, bilanço
likiditesi değil. LIQ pillar'ındaki cari oran/asit-test bundan ayrıdır ve ikisi
birbirinin yerine kullanılmaz.

- [ ] **Adım 1: Başarısız testi yaz**

`tests/test_liquidity.py`:

```python
from datetime import date, timedelta

import pytest

from ratio_engine.liquidity import adv_try


def _bars(n, close=10.0, volume=1000.0, end=date(2025, 12, 31)):
    return [
        {"trade_date": end - timedelta(days=n - 1 - i),
         "close": close, "volume": volume}
        for i in range(n)
    ]


def test_average_daily_value_is_price_times_volume():
    r = adv_try(_bars(60), date(2025, 12, 31))
    assert r.status == "OK"
    assert r.value == pytest.approx(10_000.0)
    assert r.days_used == 60


def test_short_history_is_missing_not_zero():
    r = adv_try(_bars(30), date(2025, 12, 31))
    assert r.status == "MISSING"
    assert r.value is None
    assert r.days_used == 30


def test_bars_after_the_as_of_date_are_ignored():
    bars = _bars(60) + _bars(5, close=99.0, end=date(2026, 1, 10))
    r = adv_try(bars, date(2025, 12, 31))
    assert r.value == pytest.approx(10_000.0)
    assert r.days_used == 60


def test_a_null_field_drops_that_bar_not_the_whole_window():
    bars = _bars(60)
    bars[0] = dict(bars[0], volume=None)
    r = adv_try(bars, date(2025, 12, 31))
    assert r.days_used == 59
    assert r.status == "OK"


def test_dropping_below_the_minimum_flips_to_missing():
    bars = _bars(60)
    for i in range(25):
        bars[i] = dict(bars[i], close=None)
    r = adv_try(bars, date(2025, 12, 31))
    assert r.status == "MISSING"
    assert r.days_used == 35


def test_window_keeps_the_most_recent_bars():
    old = _bars(40, close=1.0, end=date(2025, 6, 30))
    recent = _bars(60, close=10.0, end=date(2025, 12, 31))
    r = adv_try(old + recent, date(2025, 12, 31))
    assert r.value == pytest.approx(10_000.0)
```

- [ ] **Adım 2: Testi koş, başarısız olduğunu gör**

Çalıştır: `python -m pytest tests/test_liquidity.py -v`

Beklenen: FAIL — `ModuleNotFoundError: No module named 'ratio_engine.liquidity'`

- [ ] **Adım 3: Asgari uygulamayı yaz**

`src/ratio_engine/liquidity.py`:

```python
from __future__ import annotations

"""Traded liquidity: average daily turnover in TRY.

K13 keeps this strictly apart from balance-sheet liquidity.  The current and
quick ratios stay in the LIQ pillar on the quality axis; this number is a hard
gate, because a signal on a stock that trades 200k TRY a day is real and
unusable at the same time.

Only the arithmetic lives here.  Ingesting volume is the upstream project's
job, and pulling it in would cost this package its zero-dependency property
(K10).  The caller hands over rows; this module never fetches anything.
"""

from dataclasses import dataclass
from datetime import date
from typing import Any, Iterable, Mapping

from ratio_engine.evaluator import _is_finite

STATUS_OK = "OK"
STATUS_MISSING = "MISSING"

DEFAULT_WINDOW_DAYS = 60
DEFAULT_MIN_DAYS = 40


@dataclass(frozen=True)
class LiquidityResult:
    value: float | None
    status: str
    days_used: int


def adv_try(
    bars: Iterable[Mapping[str, Any]],
    as_of: date,
    *,
    window_days: int = DEFAULT_WINDOW_DAYS,
    min_days: int = DEFAULT_MIN_DAYS,
) -> LiquidityResult:
    """Mean of close x volume over the trailing `window_days` trading bars.

    Trading bars, not calendar days: the window is the last N rows at or
    before ``as_of``, so holidays and halts shorten the calendar span rather
    than diluting the average with days the stock could not trade.
    """
    usable: list[tuple[date, float]] = []
    for bar in bars:
        td = bar.get("trade_date")
        if not isinstance(td, date) or td > as_of:
            continue
        close, volume = bar.get("close"), bar.get("volume")
        if not (_is_finite(close) and _is_finite(volume)):
            continue
        usable.append((td, float(close) * float(volume)))

    usable.sort()
    window = usable[-window_days:]
    days_used = len(window)

    if days_used < min_days:
        return LiquidityResult(None, STATUS_MISSING, days_used)

    value = sum(v for _, v in window) / days_used
    if not _is_finite(value):
        return LiquidityResult(None, STATUS_MISSING, days_used)
    return LiquidityResult(value, STATUS_OK, days_used)
```

- [ ] **Adım 4: Testi koş, geçtiğini gör**

Çalıştır: `python -m pytest tests/test_liquidity.py -v`

Beklenen: 6 passed

`days_used` eksik durumda da raporlanır: "neden eksik" sorusu kapsam raporu
için gerekli, `MISSING` tek başına onu söylemiyor.

- [ ] **Adım 5: Commit**

```bash
git add src/ratio_engine/liquidity.py tests/test_liquidity.py
git commit -m "feat(liquidity): compute adv_try over trailing trading bars"
```

---

## Görev 6: Paket Yüzeyi ve README

**Dosyalar:**
- Değiştir: `src/ratio_engine/__init__.py`
- Değiştir: `README.md`
- Test: `tests/test_trend.py`

- [ ] **Adım 1: Başarısız testi yaz**

```python
def test_public_surface_exports_the_new_primitives():
    import ratio_engine

    assert ratio_engine.compute_trend is not None
    assert ratio_engine.TrendTriple is not None
    assert ratio_engine.adv_try is not None
    assert "compute_trend" in ratio_engine.__all__
    assert "adv_try" in ratio_engine.__all__
```

- [ ] **Adım 2: Testi koş, başarısız olduğunu gör**

Çalıştır: `python -m pytest tests/test_trend.py -v -k public_surface`

Beklenen: FAIL — `AttributeError: module 'ratio_engine' has no attribute 'compute_trend'`

- [ ] **Adım 3: `__init__.py`'yi güncelle**

Docstring'deki modül listesine iki satır ekle:

```
    trend      (level, slope, stability) across a window of quarters
    liquidity  average daily turnover, the traded-liquidity gate input
```

Import ekle:

```python
from ratio_engine.trend import TrendError, TrendTriple, compute_trend
from ratio_engine.liquidity import LiquidityResult, adv_try
```

`__all__`'a ekle: `"TrendTriple"`, `"TrendError"`, `"compute_trend"`,
`"LiquidityResult"`, `"adv_try"`.

- [ ] **Adım 4: README'yi güncelle**

Modül tablosuna iki satır; K18–K21'e referans ver.

- [ ] **Adım 5: Tüm testleri koş**

Çalıştır: `python -m pytest -q`

Beklenen: 63 passed

- [ ] **Adım 6: Commit**

```bash
git add src/ratio_engine/__init__.py README.md tests/test_trend.py
git commit -m "feat: export trend and liquidity primitives"
```

---

## Görev 7: Mutasyon Kontrolü

DEVIR.md'nin "EK — DOĞRULAMA DURUMU" bölümünde beş mutasyonun beşinin de
yakalandığı raporlanmış. Yeni kod aynı çıtayı karşılamalı: test yoksa davranış
yoktur.

- [ ] **Adım 1: Dört mutasyonu elle uygula, her birinin en az bir testi kırdığını doğrula**

| # | Mutasyon | Dosya | Kırmalı |
|---|---|---|---|
| 1 | `_ols_slope`'ta çeyrek indeksi yerine liste sırası kullan | `trend.py` | `test_gap_in_quarters_does_not_steepen_the_slope` |
| 2 | `min_quarters` altında `MISSING` yerine `0.0` döndür | `trend.py` | `test_too_few_quarters_is_missing_not_zero` |
| 3 | `status != OK` gözlemleri de regresyona al | `trend.py` | `test_non_ok_quarters_do_not_count_toward_the_minimum` |
| 4 | `adv_try`'da `as_of` sonrası barları filtreleme | `liquidity.py` | `test_bars_after_the_as_of_date_are_ignored` |

Her mutasyon için: değişikliği yap → `python -m pytest -q` → **FAIL** gördüğünü
doğrula → `git checkout -- <dosya>` ile geri al.

- [ ] **Adım 2: Son tam koşu**

Çalıştır: `python -m pytest -q`

Beklenen: 63 passed

- [ ] **Adım 3: Faz sonu commit**

```bash
git add -A
git commit -m "test: verify trend and liquidity survive four mutations"
```

---

## Bitiş Ölçütü

Faz 1, şu üçü birden doğrulandığında biter:

1. `python -m pytest -q` → 63 passed, 0 failed.
2. Dört mutasyonun dördü de en az bir testi kırıyor.
3. `python -c "import ratio_engine"` üçüncü parti hiçbir şey import etmeden
   çalışıyor — sıfır bağımlılık özelliği korunuyor (K10).

## Faz 1'in Bilerek Yapmadıkları

Bunlar eksiklik değil, kapsam dışıdır:

- **yfinance/DB ingest.** Ana projenin işi; "Kapsam Kararı" bölümüne bakınız.
- **`G_likidite` eşiğinin sayısal değeri.** Kapı Faz 2'de motorla gelir; eşik
  bugün seçilirse doğrulanmamış bir sabit daha doğar.
- **Üçlünün skorlamaya bağlanması.** `score_universe`'e eğim/istikrar gözlemi
  beslemek Faz 2'nin işi; sözleşmesi burada hazırlanır, kablolaması orada.
- **`_median`'ın `scoring` ile paylaştırılması.** Katman yönü bozulmasın diye
  kopya bırakıldı; ortak `_stats.py` ayrı bir iş.
- **TMS 29 / enflasyon düzeltmesi.** DEVIR.md'de açık yapısal sorun; eğimin
  nominal TL'de olması bu fazda bilinçli kabul.

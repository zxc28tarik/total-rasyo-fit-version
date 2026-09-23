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

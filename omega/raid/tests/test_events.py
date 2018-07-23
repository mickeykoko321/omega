"""Test Events module"""
import datetime as dt
import pandas_market_calendars as pmc
import pytest

import omega.core.chain as occ
import omega.core.instrument as oci
import omega.raid.events as ore


def test_events():
    event = ore.Events.GoldmanRoll
    print(event)
    assert isinstance(event.value[1]([]), ore.GoldmanRoll)


@pytest.mark.parametrize('ticker, last_day, event, days, check', [
    ('LHS2J18', '2018-04-13', ore.Events.GoldmanRoll, 3, dt.date(2018, 3, 9)),
    ('FCS1H18', '2018-03-29', ore.Events.SpotLimit, -1, dt.date(2018, 3, 14)),
    ('KCS2K18', '2018-04-20', ore.Events.SpotLimit, -2, dt.date(2018, 4, 18)),
    ('SBS3N18', '2018-06-29', ore.Events.SpotLimit, 1, dt.date(2018, 6, 20)),
    ('W_S2H18', '2018-02-28', ore.Events.SpotLimit, -1, dt.date(2018, 2, 26)),
    ('LBS2H18', '2018-03-15', 'SpotLimit', -1, dt.date(2018, 2, 28))
])
def test_get_date(ticker, last_day, event, days, check):
    calendar = pmc.get_calendar('CME').valid_days('2018-01-01', '2018-12-31')
    date = ore.get_date(event, calendar, ticker, last_day, days)
    print('Event: {} - Date: {}'.format(event, date))
    assert isinstance(date, dt.date)
    assert date == check


def test_get_dates():
    stem = 'W_'
    fc = occ.FutureChain(stem, oci.FutureType.Spread)
    fc.initialize_contracts(occ.Status.Expired, we_trade=False)
    fc.initialize_data()
    start, end = fc.get_start_end(extra_days=True)
    print('Start: {} - End: {}'.format(start, end))
    calendar = pmc.get_calendar('CME').valid_days(start, end)
    dates = ore.get_dates(ore.Events.SpotLimit, calendar, fc.chain, 2)
    assert isinstance(dates, list)
    assert isinstance(dates[0], dt.date)
    print(dates)

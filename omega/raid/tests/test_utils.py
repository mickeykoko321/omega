"""Test Chain module"""
import datetime as dt
import pandas_market_calendars as pmc
import pytest

import omega.raid.utils as oru


def test_third_friday():
    tf = oru.third_friday(2018, 5)
    print('Third Friday: {}'.format(tf))
    assert tf == dt.date(2018, 5, 18)


def test_business_days():
    calendar = pmc.get_calendar('CME').valid_days('2018-01-01', '2018-12-31')
    number = oru.business_days(calendar, dt.date.today())
    print(number)


@pytest.mark.parametrize('module', [
    'omega.raid.tests.test_strategy', 'alpha.spreading', 'notexisting.notexisting'
])
def test_load_parameters(module):
    try:
        params = oru.load_parameters(module)
        assert isinstance(params, dict)
        print(params)
    except oru.UtilsError:
        print('Parameters file or module not found!')

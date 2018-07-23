"""Test COT module"""
import datetime as dt
import pandas as pd
import pytest

import omega.data.cot as odc


def test_get_release_dates():
    df = odc.get_release_dates()
    assert isinstance(df, pd.DataFrame)
    assert len(df.columns) == 1
    assert set(df.columns) == {'ReleaseDate'}
    assert isinstance(df.iloc[0]['ReleaseDate'], pd.Timestamp)
    print(df.tail())


def test_next_release_date():
    date = odc.next_release_date(dt.datetime.strptime('2018-04-09', '%Y-%m-%d'))
    assert isinstance(date, pd.Timestamp)
    print(date)


@pytest.mark.parametrize('stem', ['CT', 'LB', 'ES'])
def test_get_cot(stem):
    df = odc.get_cot(stem)
    print(df.tail())
    assert isinstance(df, pd.DataFrame)


@pytest.mark.parametrize('stem', ['CT', 'LB', 'ES'])
def test_cot_data(stem):
    df = odc.cot_data(stem)
    print(df.tail())
    assert isinstance(df, pd.DataFrame)

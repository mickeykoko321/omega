"""Test Utils module"""
import datetime as dt
import pandas as pd

import omega.data.cot as odc
import omega.data.utils as odu


def test_business_date_range():
    drng = odu.business_date_range('2018-01-01', '2018-01-31')
    print(drng)
    assert isinstance(drng[0], dt.datetime)


def test_get_market_df():
    df = odu.get_market_df('EDM18')
    assert isinstance(df, pd.DataFrame)
    print(df.head())


def test_roll_yield():
    ticker = 'LBS2H18'
    df = odu.get_market_df(ticker)
    ry = odu.roll_yield(ticker, df)
    assert isinstance(ry, pd.Series)
    ndf = df
    ndf['RollYield'] = ry
    assert isinstance(ndf, pd.DataFrame)
    assert df.index[0] == ndf.index[0]
    assert df.index[-1] == ndf.index[-1]
    print(ndf.head())
    print(ndf.tail())


def test_save_market_df():
    ticker = 'FCF10'
    df = odu.get_market_df(ticker)
    odu.save_market_df(ticker, df)


def test_df_join_check():
    dates = odc.get_release_dates()
    cot = odc.get_cot('LH', 'F')
    df = odu.df_join_check(cot, dates)
    assert isinstance(df, pd.DataFrame)
    print(df.head())

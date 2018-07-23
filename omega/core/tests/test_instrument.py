"""Test Instrument module"""
import pandas as pd
import pytest

import omega.core.instrument as oci


@pytest.mark.parametrize('sector, group', [
    (None, None), ('Commodity', 'Meat'), ('Currency', None), ('Stock', None), ('Yield', None)
])
def test_futures(sector, group):
    ls = oci.futures(sector, group)
    assert isinstance(ls, list)
    print(ls)


@pytest.mark.parametrize('stem, ctr_mth, future_type, next_ctr_mth', [
    ('LB', 20171100, oci.FutureType.Outright, None),
    ('LH', 20180200, oci.FutureType.Spread, 20180400),
    ('FF', 20180300, oci.FutureType.Butterfly, 20180600),
    ('ED', 20180300, oci.FutureType.Condor, 20180600),
    ('ED', 20180300, oci.FutureType.DoubleButterfly, 20180600),
    ('ED', 20180300, oci.FutureType.FlyOfFly, 20180600)
])
def test_create_contracts(stem, ctr_mth, future_type, next_ctr_mth):
    ct = oci.create_contract(stem, ctr_mth, future_type, next_ctr_mth)
    print(ct)
    assert isinstance(ct, str)


def test_previous_month():
    t1 = oci.previous_month('F18')
    print('Previous month: {}'.format(t1))
    assert t1 == 201712
    t2 = oci.previous_month('M10')
    print('Previous month: {}'.format(t2))
    assert t2 == 201005
    t3 = oci.previous_month('Z17')
    print('Previous month: {}'.format(t3))
    assert t3 == 201711


@pytest.mark.parametrize('ticker', [
    'LBH18', 'LBS2H18', 'EDB12M8', 'EDD6M9'
])
def test_get_future_type(ticker):
    ft = oci.get_future_type(ticker)
    print(ft)
    assert isinstance(ft, oci.FutureType)


@pytest.mark.parametrize('stem, we_trade', [('LB', True), ('O_', False)])
def test_ctrmth(stem, we_trade):
    df = oci.ctrmth(stem, we_trade)
    assert isinstance(df, pd.DataFrame)
    print(df.head())


@pytest.mark.parametrize('ticker', [
    'LBH18', 'LBS2H18', 'EDB12M8', 'EDD6M9'
])
def test_lots(ticker):
    nb = oci.lots(ticker)
    print(nb)
    assert isinstance(nb, int)
    if ticker == 'LBH18':
        assert nb == 1
    elif ticker == 'LBS2H18':
        assert nb == 2
    elif ticker == 'EDB12M8':
        assert nb == 4
    elif ticker == 'EDD6M9':
        assert nb == 8

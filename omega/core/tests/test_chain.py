"""Test Chain module"""
import datetime as dt
import pandas as pd
import pytest

import omega.core.chain as occ
import omega.core.instrument as oci
# import core.table as ct


@pytest.mark.parametrize('stem, ctr_mth, future_type, ncb', [
    ('LB', 20171100, oci.FutureType.Outright, 4),
    ('LB', 20171100, oci.FutureType.Spread, 2),
    ('LB', 20171100, oci.FutureType.Spread, 3)
])
def test_generate_contracts(stem, ctr_mth, future_type, ncb):
    df = oci.ctrmth(stem, True)
    lc = occ.generate_contracts(stem, ctr_mth, future_type, df, ncb)
    print(lc)
    # Check if list is returned
    assert isinstance(lc, list)
    # Check if length list is as expected
    if future_type == oci.FutureType.Outright:
        assert len(lc) == 1
    else:
        assert len(lc) == ncb
    # Check if an element is a string (if it is it must be a ticker)
    assert isinstance(lc[0], str)


@pytest.mark.parametrize('stem, future_type, status, ncb', [
    ('LB', oci.FutureType.Outright, occ.Status.Active, 1),
    ('LB', oci.FutureType.Spread, occ.Status.Active, 2),
    ('LB', oci.FutureType.Outright, occ.Status.Expired, 1),
    ('LB', oci.FutureType.Spread, occ.Status.Expired, 1)
])
def test_get_table(stem, future_type, status, ncb):
    date = '2017-12-12'
    df = occ.get_table(date, stem, future_type, status, ncb=ncb)
    print('Status: {}'.format(status))
    print(df.head())
    if status == occ.Status.Expired:
        print(df.tail())
    assert isinstance(df, pd.DataFrame)
    assert len(df.columns) == 2
    assert set(df.columns) == {'Ticker', 'LastDate'}


@pytest.mark.parametrize('stem, future_type', [
    ('LH', oci.FutureType.Outright),
    ('LB', oci.FutureType.Spread)
])
def test_future_chain_contracts(stem, future_type):
    status = occ.Status.Expired
    fc = occ.FutureChain(stem, future_type)
    # Check Contracts
    df = fc.initialize_contracts(status, as_dataframe=True)
    print(df)
    assert isinstance(df, pd.DataFrame)
    assert len(df.columns) == 2
    assert set(df.columns) == {'Ticker', 'LastDate'}
    # Temporary - Check len against old table.py module
    # if future_type == ci.FutureType.Outright:
    #    ot = ct.outright_table(stem, status)
    #    print('Comparison: new: {} - old: {}'.format(len(df), len(ot)))
    # elif future_type == ci.FutureType.Spread:
    #    st = ct.spread_table(stem, status)
    #    print('Comparison: new: {} - old: {}'.format(len(df), len(st)))
    # Check Data
    data = fc.initialize_data()
    first_key = list(data.keys())[0]
    print('First Key: {}'.format(first_key))
    print('Data check:\n{}'.format(data[first_key].head()))
    assert isinstance(data[first_key], pd.DataFrame)


def test_filter_chain_contracts():
    fc = occ.FutureChain('LB', oci.FutureType.Spread)
    odf = fc.initialize_contracts(occ.Status.Expired)
    # All the contracts with a specific letter!
    df = fc.initialize_contracts(occ.Status.Expired, filter='X', as_dataframe=True)
    print(df.head())
    # Check filtering with an incorrect letter works
    df = fc.initialize_contracts(occ.Status.Expired, filter='Z')
    assert len(odf) == len(df)
    # Last number of contracts
    nfilt = 5
    df = fc.initialize_contracts(occ.Status.Expired, filter=nfilt, as_dataframe=True)
    print(df.tail())
    assert len(df) == nfilt
    # Check too high number of contracts ignored
    df = fc.initialize_contracts(occ.Status.Expired, filter=1000)
    assert len(odf) == len(df)


def test_initialize_data():
    fc = occ.FutureChain('LH', oci.FutureType.Outright)
    fc.initialize_contracts(occ.Status.Expired, filter='H', initialize_data=True)
    test = []
    for ct in fc.contracts:
        test.extend(fc.data[ct]['OI'])


def test_get_start_end():
    fc = occ.FutureChain('LH', oci.FutureType.Outright)
    fc.initialize_contracts(occ.Status.Active, initialize_data=True)
    start, end = fc.get_start_end(extra_days=True)
    print('Start: {} - End: {}'.format(start, end))
    assert isinstance(start, str)
    assert isinstance(end, str)
    assert isinstance(dt.datetime.strptime(start, '%Y-%m-%d'), dt.datetime)
    assert isinstance(dt.datetime.strptime(end, '%Y-%m-%d'), dt.datetime)


def test_chain_last__ticker_filter():
    fc = occ.FutureChain('LB', oci.FutureType.Spread)
    fc.initialize_contracts(occ.Status.Active, initialize_data=True)

    print(fc.last_date(0))
    print(fc.ticker(1))
    assert isinstance(fc.last_date(0), dt.datetime)
    import pandas_market_calendars as pmc
    calendar = pmc.get_calendar('CME').valid_days('2018-01-01', '2018-12-31')
    print(calendar.get_loc(fc.last_date(0)))
    assert isinstance(fc.ticker(1), str)
    contracts = fc.contracts[0:2]
    fc.filter_chain(contracts)
    assert len(fc.contracts) == len(contracts)


"""Test Lists module"""
import pandas as pd
import pytest

import omega.core.chain as occ
import omega.core.lists as ocl


def test_create_provider_file():
    tickers = ocl.create_provider_file(occ.Status.Active, 'Reuters', ['LH'])
    print(tickers.head())
    assert isinstance(tickers, pd.DataFrame)
    assert set(tickers.columns) == {'Ticker', 'Provider'}


def test_generate_tickers_df():
    tickers = ocl.generate_tickers_df('CT', occ.Status.ActivePlus)
    assert isinstance(tickers, pd.DataFrame)
    print('Number of tickers: {}'.format(len(tickers)))
    print(tickers)


def test_generate_curvature_list():
    tickers = ocl.generate_curvature_list()
    print(tickers)
    assert isinstance(tickers, list)


def test_generate_tickers_for_curvature():
    tickers = ocl.generate_tickers_for_curvature('M18', 'ED')
    print(tickers)
    assert isinstance(tickers, list)

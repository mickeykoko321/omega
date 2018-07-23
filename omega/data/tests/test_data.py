"""Test Chain module"""
import pytest

import omega.data.utils as odu


def test_create_reference_data():
    start = '2018-01-01'
    end = '2018-01-31'
    df = odu.create_reference_data(start, end)
    print(df.head())
    assert df.index[0].strftime('%Y-%m-%d') == start
    assert df.index[-1].strftime('%Y-%m-%d') == end


@pytest.mark.parametrize('ticker', ['LBS2K18', 'Reference'])
def test_get_file_path(ticker):
    path = odu.get_file_path(ticker)
    print(path)
    assert isinstance(path, str)
